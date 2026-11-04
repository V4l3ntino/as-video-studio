# AS Video Studio — instrucciones para agentes

## Fuentes que importan

- Lee `README.md` y `CLAUDE.md` antes de cambiar código: este último conserva las causas de fallos costosos y las restricciones de compatibilidad. Para despliegue, consulta `despliegue/LEEME.md`.
- `docs/RETOMAR.md`, si existe, son notas locales de continuidad; está ignorado y no debe publicarse.

## Arranque y verificación

- Servicio: `python app.py --puerto 8020`. Dependencias Python fijadas en `requirements.txt`; el entorno documentado es Python 3.12. Cambiar versiones exige pruebas y una instalación limpia, no solo actualizar el fichero.
- Tanda completa desde la raíz: `powershell -NoProfile -File pruebas.ps1` (intérprete alternativo: `-Python <ruta>`). Ejecuta 26 suites y siete analizadores propios. Revisa también sus salidas `ANAL`: el script no cuenta sus hallazgos como fallos de la tanda.
- Las suites son scripts, no una colección de pytest. Verificación acotada: `python nucleo/prueba_manifiestos.py`, `python pasos/prueba_regresiones.py` o `python prueba_api.py`. Esta última arranca su propio servidor; `--conservar` retiene sus proyectos temporales para investigar.
- La suite visual necesita navegador, ffmpeg/ffprobe y fuentes. El runner PowerShell evita el fallo conocido de Edge que devuelve 0 sin escribir el PNG desde un shell sandboxeado y limpia `%TEMP%/estudio_prueba_visual`; una ejecución interrumpida puede dejar ese estado sucio.
- No supongas que toda prueba es offline: `pasos/prueba_pasos_voz.py` usa Cartesia si hay clave; `pasos/prueba_login.py` llama al CLI real. El runner trata el código 3 como falta de cupo, no como prueba superada ni fallo de código.
- Login de Claude atascado en «comprobando»: en Windows, el CLI 2.1.123 generaba el enlace pero no respondía al código por stdin y agotaba los 120 s. Actualizar con `claude update`, reiniciar el servicio y abrir un intento nuevo resolvió el acceso, confirmado por el usuario. El contrato está documentado con 2.1.241; no presupongas que es la versión mínima. Comprueba `claude --version` antes de atribuirlo al token.
- Cancelar el login compite con la petición que comprueba el código: `Intento.matar()` deja `self.proceso` en `None`. Conserva la referencia local al proceso y comprueba que el intento siga activo; una petición cancelada debe terminar con `ErrorLogin`, sin consultar `None.poll()` ni confirmar después la cuenta. Las regresiones aisladas (cancelación durante la espera y durante `situacion`) están en `pasos/prueba_ajustes.py`; `pasos/prueba_login.py` verifica el contrato con el CLI real.
- En pruebas nuevas, desvía los datos antes de cargar módulos que los lean: `ESTUDIO_ESTADISTICAS` evita expulsar medidas reales; `ESTUDIO_SECRETOS` aísla claves, salud del CLI y límites aprendidos; `ESTUDIO_AJUSTES` aísla configuración y onboarding. No uses `ESTUDIO_SIMULAR=1` como garantía universal contra llamadas reales: cada camino debe implementarlo o usar dobles.

## Límites y flujo

- `app.py` conecta HTTP y ejecutores; `pasos/recetas.py` declara tareas, dependencias y opcionalidad. Una función nueva no entra en la generación hasta estar conectada a la receta y al ejecutor.
- `nucleo/` es el grafo genérico, sin conocimiento de vídeo; `pasos/` no depende de HTTP; `motores/` consume contratos de ficheros sin importar la aplicación.
- El grafo persistido es `ingesta → brief → guion → voz → revision_audio → assets → callouts → render`. No renombres ni elimines ids: incluso quitar `brief` invalida proyectos guardados en cascada.
- `despliegue/login/` es un servicio Node aparte (Node >=20), no el frontend del estudio. La autenticación vive delante del servicio Python. En local, la ausencia de `/api/me` y `/api/logout` es esperada.
- Al cambiar endpoints, regenera `docs/API.md` con `python generar_api.py`; `prueba_api.py` comprueba la correspondencia con las rutas. No edites esa referencia a mano.

## Estado y generación: los errores cuestan dinero

- En Windows, `TEMP` puede contener el alias 8.3 `VALENT~1`. Claude CLI 2.1.317 deniega `Write` en esas rutas incluso con `acceptEdits`; en headless termina sin `salida.json`. Usa `os.path.realpath` para el directorio temporal, `cwd` y `--add-dir`, y da la ruta completa de entrega. No desactives los permisos. `cli_claude.escribiendo` conserva el motivo del agente y los nombres de `permission_denials` si falta el fichero; no vuelques `tool_input`. Regresión aislada en `pasos/prueba_ajustes.py`.
- Nunca persistas params por defecto al abrir una pantalla: las firmas usan los params guardados. Edita una copia y guarda solo cambios del usuario. Los valores iniciales de vídeos nuevos no deben aplicarse retroactivamente.
- Las tandas de imágenes van de una en una. Conserva el orden de recetas: cartelas antes de planos, rótulos después. No relajes `p6_assets._planos_repetidos` para esconder un fallo; sus excepciones están documentadas en la función.
- En `nucleo/estado.py`, los manifiestos viven en `pasos/<paso>/_versiones/v<N>.json`, fuera de `v<N>/` y de `estado.json`. Conserva la lectura del formato antiguo; un manifiesto ausente o incompleto debe lanzar, nunca convertirse en `{}`. `completar()` debe escribirlo antes de mutar `datos`; no lo caches dentro del documento.
- Mudar proyectos requiere rutas y firmas, incluido el histórico: usa `herramientas/mudar_proyecto.py` (simula sin `--aplicar`). No «arregles» todas las firmas: un guion editado puede tenerlas desparejadas a propósito. Comprueba también que las salidas referenciadas existen en disco.
- Los ficheros de un preset son acumulativos; no renombres ni borres referencias anteriores al guardarlo. Los vídeos nuevos copian sus referencias a `estilo/referencias`.
- El actualizador reemplaza el árbol del programa: guarda datos aprendidos fuera de él. Conserva el nombre `motores/reglas/reglas_casa.json`; instalaciones antiguas excluyen `reglas.json` al actualizar.
- Imágenes nuevas sin clave usan Codex con sesión ChatGPT (`motores/imagen_openai/codex.py`, CLI probado: 0.165.0). No pases tokens OAuth a `/v1/images`, ni introduzcas respaldo de pago. `ESTUDIO_CODEX_HOME` aísla la sesión; `python pasos/prueba_codex_imagen.py` verifica el contrato sin consumir cuota. La preferencia vive en secretos, no en params de proyectos.
- Codex admite cinco adjuntos: agrupa el exceso sin perder referencias ni su numeración lógica. No deduzcas falta de cuota de una imagen ausente: usa el diagnóstico de `secretos/codex_imagenes`. La concurrencia es interna a una tanda (máximo dos), con hilo nuevo por imagen; el contador avanza al resolver el plano, no al iniciarlo.
- Los límites renovables de ChatGPT/Codex (`ErrorCodex.cuota_renovable`) mantienen la tanda activa en `recuperacion_imagenes`: se comprueban periódicamente con los intervalos configurados. Mientras `ordinaryUsageAllowed` sea falso, no abras `thread/start` ni `turn/start`; la generación continúa al volver el uso permitido. No extiendas esto a saldo/facturación de API. Mantén la barra y Parar durante la espera; no ofrezcas otra tanda hasta que el trabajo sea terminal. Contrato aislado en `pasos/prueba_codex_imagen.py` y cancelación en `pasos/prueba_recuperacion_imagenes.py`.
- Ante un rechazo de Codex de una escena, `corrector.alternativa_visual` propone una sola sustitución inocua de la acción, nunca una paráfrasis para eludir el filtro. `p6_assets` guarda la decisión en `<plano>.alternativa.json` antes de solicitarla, y conserva `alternativa_visual` con el prompt efectivo en ficha, caché y plan. No reinicies la adaptación por timeout, cuota o al retomar. Si también se rechaza, requiere revisión; cambiar el encargo cambia su firma. Es guion visual: no modifica narración, audio, tiempos ni params del grafo. Pruebas aisladas en `pasos/prueba_recuperacion_imagenes.py`.

## Interfaz sin build

- Hay una sola pantalla guiada, en JavaScript sin framework ni npm. Los assets se sellan por contenido automáticamente; no subas una versión de caché a mano.
- Todo estilo va en `web/estilo.css`: la CSP del proxy bloquea atributos HTML `style=""`. Tras tocar la interfaz, ábrela y comprueba lo visible; las suites no detectan bloques que no se pintan.
- Antes de tocar supuestos paneles antiguos, comprueba alcance con `python herramientas/alcanzables_js.py --quien <nombre>`. Usa también `python herramientas/sin_llamar_js.py` para detectar funciones duplicadas que JavaScript sobrescribe silenciosamente.
- Los tokenizadores de `herramientas/` confunden un acento grave literal dentro de una regex con una plantilla; escribe `\x60` en su lugar.
- Al salir de una instalación con prefijo, redirige a `${BASE}/login`: el servicio de acceso devuelve `/login` sin conocer el prefijo del estudio.
