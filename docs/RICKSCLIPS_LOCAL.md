# RicksClips — preparación local

La tarjeta está publicada en **v5**, conservando el preset `pr1a1fa348c8f`.
Huella: `c13b07a752ef9c1039e6315515151fd70b8eaae451243a90afcb3bfed76deb1d`.
V1–v4 y los proyectos anteriores se conservan, sin migración.

Hay un **piloto Blender separado, no publicado** en
[RICKSCLIPS_BLENDER.md](RICKSCLIPS_BLENDER.md). No cambia la tarjeta v5 ni permite
afirmar que Blender ya esté conectado al ejecutor nativo del Estudio.

## Iteración local v5

Fuentes nuevas/completadas: `decorados3d.pared_canon` construye macizos continuos
con cárcavas y contrafuertes, en vez de torres de anillos. La locomotora tiene
cabina abierta por detrás, techo abovedado, estribos, pasamanos y frente de caja
de humos. El puente añade arriostramiento transversal y apoyos; las fachadas
admiten remates distintos. La luz compartida separa ambiente frío y clave cálida,
con rebote ocre aproximado; los ellipsoides tienen normales analíticas.

`contactos.py` ofrece `centro_por_agarre` y `transformar`: contacto rígido en el
plano articulado del actor, resuelto desde la mano real después del IK. La captura
del móvil lo utiliza y los dedos respetan la tinta de piel de cada apariencia.
**No es un constraint 3D para la olla** ni resuelve colisiones con muebles.

Las evidencias nuevas viven en `comprobaciones/mejora_v5/`, sin sobrescribir v4:
`INFORME_VISUAL.md`, `comparacion_final/`, `gpu_final/`, `contacto_final/` y las
secuencias HD. Se conserva también el fallo de encuadre de las primeras vistas
del tren y su repetición separada. `correccion_piel.diff` registra el único cambio
entre los dos candidatos; se repitió la validación GPU completa antes de publicar.

Entrega: `entrega/indice.html` enlaza comparaciones y **18 secuencias finales**
(39,6 s, 1080×1920/25 fps). Hay 18 pruebas de subtítulos reales sobre vídeo,
con marcas sintéticas: en el zoom extremo aún se superpone texto al borde del iris.
La muestra publicada sigue siendo 18 s, 720×1280/25 fps. Navegador real: una
tarjeta, reproducción v5 y formulario con esa huella/vertical, sin errores JS.
Congelado del preset, render nativo con identidad independiente y duplicado
portable comprobados en `integracion_nativa_ruta_corta/`.

El primer intento nativo se conserva en `integracion_nativa/`: Pillow no cargaba
su DLL por la longitud de ruta de Windows. La herramienta admite ahora `--trabajo`
para una raíz temporal NUEVA y corta; no se cambió Pillow ni el sistema global.
La repetición usó `%LOCALAPPDATA%/Temp/opencode/rc5`, conservada para investigar.

Integridad: 2.690 ficheros previos del estilo idénticos y actualización autorizada
únicamente de `espacio` en su `estilo.json`; 487 ficheros de proyectos intactos.
Sellos v1–v4 y ajustes del preset conservados. Servicio sin reiniciar y sin trabajos
activos al cierre. Los detalles verificables están en `entrega/integridad.json`,
`publicacion_verificada.json`, `app/navegador.json` y el informe visual.

Las herramientas de comparación y cierre ya no fijan rótulos/conteos de v4.
`muestra_subtitulos_ricksclips.py` acepta también un MP4: decodifica y superpone
la capa REAL de p7 fotograma a fotograma, en vez de evaluar solo un fondo fijo.
`auditar_contactos_ricksclips.py --help` reproduce las tres apariencias y mide el
contacto sostenido; eso no certifica actuación ni calidad artística.

Pruebas: contratos locales (8), biblioteca (18), animación nativa (31), recursos
(49), subtítulos/formato (7), estilos con navegador (31), manifiestos y analizadores
Python. SciPy y Playwright reutilizados desde sus carpetas aisladas; sin proveedores.

**El acabado del original sigue sin alcanzarse.** Las paredes ganan continuidad,
pero siguen facetadas y poco erosionadas; el paisaje es demasiado vacío y el tren
todavía simplificado. Agua, explosión, interiores y ritmo no muestran una mejora
artística sustancial frente a v4. La vista cenital HD revela además una abertura
heredada en proa. Siguen pendientes contacto 3D de la olla, coreografía de vertido,
riqueza pictórica, fuente original y composición segura para programas arbitrarios.

## Histórico: mejora visual v4 y sus evidencias

**No alcanza el acabado de la referencia.** Mejoran realmente el casco/aparejo del
barco, el agua sin damero, carpintería/utilería de los seis escenarios, cuenco
hueco, perfiles/balasto de vías, siluetas finas y vestuario anclado. Se corrigieron
pies flotantes, cámara dentro de una roca, lata delante del rostro, agarre/vertido
aproximados y subtítulos que tapaban la boca en el primer plano.

Fuentes adicionales: `artesania3d.py`, `vestuario.py` y `planos_revision.py` en
`motores/ricksclips/`. `preparar_ricksclips.compilar_rig` conserva el esqueleto,
anclas/FK/IK/apariencias y compila el vestuario de forma autocontenida para cada
identidad. No introduce una dependencia mutable compartida entre personajes.

En la carpeta local del estilo, `comprobaciones/mejora_v4/` contiene:

- `entrega/indice.html`: índice de comparaciones y clips.
- `entrega/revision_hd.mp4`: 14 secuencias finales, 30,8 s, 1080×1920/25 fps.
- `comparacion_definitiva/`: referencia / v3 / nueva versión con cámara, pose,
  tiempo y resolución idénticos entre ambos motores.
- `hd_final/` y `hd_ajuste_subtitulos/`: clips y láminas temporales realmente
  decodificados; los dos planos ajustados sustituyen rostro/pupila anteriores.
- `INFORME_VISUAL.md`: funciones reales, imágenes inspeccionadas, correcciones y
  separación entre comprobado, no equivalente y pendiente.
- `entrega/integridad.json`: 1.045 archivos anteriores del estilo y 487 archivos
  de estados/manifiestos/fuentes de proyectos, sin alteraciones. Conservación de
  ajustes del preset, exceptuando sus dos punteros versionados de procedencia/motor.
- `app/`: reproducción de la muestra v4 y formulario vertical en la aplicación
  real, sin errores JS ni peticiones a proveedores.

La muestra de la tarjeta es ahora **18 s a 720×1280/25 fps**. Se comprobó además
el congelado del preset real, código nativo sobre el rig copiado y duplicación
portable en un proyecto temporal separado, sin proveedores. El programa nativo
de prueba se reencuadró tras inspeccionar su primer render: pasar un control de
movimiento no garantiza que el actor esté bien colocado.

Pruebas: biblioteca (18), estilos con navegador (31), animación nativa (31),
recursos (49), subtítulos/formato (7), contratos nuevos RicksClips (5), manifiestos
y analizadores Python. La primera pasada nativa necesitó repetir con el SciPy
aislado ya existente; no se instaló nada globalmente. No se ejecutó la tanda que
incluye login real o voces de pago.

Siguen pendientes riqueza pictórica, variedad arquitectónica, grandes paredes
del cañón, acabado de locomotora, iluminación y sombras más convincentes,
explosión/escombros, restricciones generales de contacto y actuación/cámara con
el ritmo del original. No se ha identificado su fuente ni producido voz/música.

Herramientas nuevas: `estudiar_ricksclips.py`, `comparar_ricksclips.py`,
`revisar_ricksclips_hd.py`, `prueba_ricksclips.py` y `cerrar_revision_ricksclips.py`.
Todas las evidencias se generan fuera del repositorio, sin fondos de referencia
en el motor y sin consultas a CLI/proveedores. No fue necesario reiniciar el servicio.

## Histórico de v2/v3 (no describe la muestra actual)

## Motor y contratos

- `motores/ricksclips/espacio3d.py`: OpenGL 3.3, geometría/normales, perspectiva,
  z-buffer, shadow map PCF, iluminación direccional/puntual, profundidad de campo
  guiada por profundidad y humo procedural integrado por raymarch.
- `decorados3d.py` y `utileria3d.py`: escenarios/objetos originales parametrizables.
  Calle del Oeste, taberna, cocina, mar de tormenta, cañón y puente ferroviario.
- `escena.py`: personajes 2D sobre billboards con alfa, sombras y oclusión real;
  conserva el rig/apariencias v1. Rasterización adaptativa en planos cortos.
- `realizacion.py`: interpolación, cámara, fundido/whip/mirilla y SFX originales
  en WAV separado, sin voz ni música añadida.
- `pasos/p7_callouts.py`: perfil opt-in `ricksclips_v1`, una palabra por marca,
  texto blanco con contorno negro, sin caja, posición escalonada en capa fija.
- El preset parte de 9:16; no cambia el formato de los proyectos anteriores.

Dependencias probadas en Python 3.12, instaladas exclusivamente con el mecanismo
local del paquete: Pillow 12.3.0, NumPy 2.5.2, ModernGL 5.12.0 y glcontext 3.0.0.
El contexto comprobado fue OpenGL 3.3 sobre Intel Iris Xe. Sin fallback a dibujo
plano cuando no hay un contexto OpenGL compatible.

## Evidencias

En la carpeta del estilo, `versiones/v3/recursos/` contiene:

- `analisis_existente.json` y `observaciones_existentes.json`: análisis e
  intervalos originales, sin repetir el análisis.
- `cumplimiento.json`: relación de los requisitos con fuentes reales.
- `pruebas_gpu.json`: comprobaciones y SHA256 de las fuentes ejecutadas.
- `integracion_estudio.json`: contratos con guion/voz/subtítulos/montaje.
- `revision_visual.txt`: revisión y diferencias constatadas frente a referencia.

`versiones/v3/muestra/clip.mp4` es la muestra visible de la tarjeta: 18 s,
360×640, 12 fps. `comprobaciones/local_8c1c11ed8e86804b/` conserva además
láminas de escenarios/articulación, aceite/vías, oclusión y sombras, secuencias
de zoom/efectos, el SVG real de subtítulos y los MP4 de prueba adicionales.

Se comprobaron en la aplicación real una sola tarjeta, reproducción de la muestra,
botón de crear vídeo, paquete v3 y selección inicial vertical; sin errores JS.
En un proyecto temporal separado se congeló el preset, se renderizó código nativo
usando el rig copiado y se verificó su duplicación portable, sin proveedores.

Pruebas ejecutadas correctamente: biblioteca (18), estilos con navegador (31),
animación nativa (31), recursos (49), perfil/formato (7); presets (122
comprobaciones) y regresiones acotadas de callouts/subtítulos (259). También los
analizadores de indefinidos/atributos Python y de indefinidos/duplicados JS.
La ejecución completa adicional de `prueba_piezas.py` se interrumpió por falta
de `OPENAI_API_KEY` en una prueba del motor de imagen: no se aportó una clave ni
se llamó a ese proveedor; el subconjunto pertinente sí pasó íntegro. No se ha
ejecutado la tanda completa que incluye login real y posibles voces de pago.

Se contrastaron 104 archivos previos (fuentes/paquete/muestra v1, respuestas
pagadas, referencias e informes, y estados/manifiestos de proyectos) sin cambios.

## Límites pendientes

El acabado **low-poly/cel-shaded es más sencillo que la referencia**. No se
certifica riqueza pictórica equivalente ni fidelidad de futuras escenas por
haber pasado controles técnicos. La fuente original no se identificó: se usa
Arial Bold instalada. No se produjo locución ni se verificó timbre equivalente.
La música no era verificable en el análisis y la política del Estudio la excluye.
No se han solicitado guiones, dirección ni generaciones reales a proveedores.

Herramientas reproducibles, todas con `--help`:
`preparar_ricksclips.py`, `verificar_ricksclips.py`,
`muestra_subtitulos_ricksclips.py`, `comprobar_ricksclips_video.py` y
`comprobar_ricksclips_app.py`, dentro de `herramientas/`.
