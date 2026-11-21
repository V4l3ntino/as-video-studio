# RicksClips: integración Blender local y verificación

**v6 Blender publicada y comprobada en el estilo local RicksClips**, preset
`pr1a1fa348c8f`. «Crear vídeo» congela y ejecuta esa versión; los proyectos ya
existentes conservan su motor. Huella:
`ef3fa82f527c6424643ef6fdec9c5105002afde1f17c6ce0a3cd772ecf02b17a`.

No se ha alcanzado el acabado del original. La evidencia final vive en
`comprobaciones/blender_publicacion_03/` del estilo local. Las secciones iniciales
conservan el historial del piloto y sus límites; no describen la publicación actual.

## Arquitectura implementada

- `herramientas/probar_ricksclips_blender.py` lee el paquete v5 sin modificar sus
  fuentes, exporta mallas con normales/materiales y rasteriza el rig real por
  fotograma. La cámara mantiene posición, objetivo y FOV vertical de v5.
- `motores/ricksclips/blender/renderizar.py` ejecuta `bpy` fuera del servicio,
  con Eevee. Convierte `(x,y,z)` del motor en `(x,-z,y)` de Blender. Los sprites
  son geometría 3D con alfa, no composición de un PNG sobre el render terminado.
- `artesania.py` contiene recursos reutilizables: superficies de cañón, primitivas
  biseladas, torno hueco, carpintería, locomotora con ruedas y bielas ligadas a la
  distancia, vapor volumétrico procedural y olla con agarre de mundo.
- El punto de agarre se resuelve **después del IK** del rig. La transformación
  del recipiente conserva ese punto durante la inclinación. Se limita el giro
  contra el plano superior de la mesa usando los límites del recipiente. La
  primera prueba con una apariencia baja reveló penetración y se conservó como
  fallo; la restricción posterior mantiene la holgura en las tres apariencias
  examinadas (165 estados). No es un solucionador general de colisiones ni una
  simulación de líquidos; un agarre imposible produce un error explícito.
- Los programas siguen siendo Python; las opciones de plano de la herramienta
  son diagnósticos, no un contrato nuevo de escenas del Estudio. `--programa-bpy`
  permite añadir código libre con `preparar(contexto)` y `actualizar(contexto,t)`
  para mallas, luz, cámara y actuación espacial. Se copia con las fuentes y solo
  se importa en el proceso de Blender, nunca en el servidor.

## Ejecución aislada

Se descargó el ZIP oficial de Blender **4.5.16 LTS**, Windows x64, de
`https://download.blender.org/release/Blender4.5/`. Se comprobó contra el archivo
SHA256 oficial antes de extraerlo. Blender se distribuye bajo GPL; se conservan
sus licencias dentro de la distribución. No se cambiaron asociaciones ni paquetes
Python globales.

La instalación de prueba está en
`%LOCALAPPDATA%/Temp/opencode/blender-portable/blender-4.5.16-windows-x64/`.
Esa ubicación **no es una dependencia portable de un proyecto publicado**.
El ejecutable se pasa explícitamente con `--blender`.

```powershell
python herramientas/probar_ricksclips_blender.py --help
python herramientas/reproducir_ricksclips_blender.py --help
```

Las salidas deben ser nuevas. Se conservan fuentes de la ejecución, intercambio,
fotogramas, MP4, logs y tiempos por frame. Las ejecuciones nuevas usan las fuentes
copiadas de esa prueba y configuración/temporales locales; no las preferencias
personales de Blender. El inventario del intercambio permite repetirlo en otra
ruta con `reproducir_ricksclips_blender.py`; **esto no equivale a duplicación
nativa de un vídeo del Estudio**.

## Dispositivo realmente comprobado

La sonda headless detectó OpenGL sobre **NVIDIA GeForce RTX 4060 Laptop GPU**,
controlador OpenGL `4.6.0 NVIDIA 610.62`, no la Iris Xe histórica. Eevee completó
un render de 1080×1920, 16 muestras, en 17,94 s en el primer arranque. Ese tiempo
incluye compilación inicial y no se extrapola a una secuencia. Las medidas de
escenas se conservan por fotograma en `medidas.json` y por proceso en
`proceso.json`. La memoria interna indicada por Blender no equivale a VRAM.

## Bloqueos del piloto inicial (histórico; integración nativa más abajo)

El ejecutor nativo actual solo permite lanzar FFmpeg desde el motor. No se ha
relajado esa guarda para permitir subprocess arbitrarios. La coordinación de
Blender existe en la herramienta piloto, **no en el ejecutor del Estudio**.
Integrarlo necesita un requisito de herramienta externa versionado, instalación
aislada reproducible y autorización exacta desde el coordinador, junto a sellado,
congelado y duplicación. Los paquetes actuales no admiten `.blend` en `archivos`;
este piloto evita ese binario monolítico y conserva código procedural.

No se deben mezclar estas pruebas con las pruebas nativas de v5 ni anunciar una
v6 preparada editando un estado. No se migran los restantes escenarios mientras
la comparación de los dos pilotos no justifique el acabado global y sus contactos.

## Cierre comprobado de la prueba

`comprobaciones/blender_piloto_01/entrega/indice.html` reúne ocho secuencias
seleccionadas, **17,6 s a 1080×1920/25 fps**, comparaciones y fallos conservados.
Mejoran materiales, sombras, carpintería, mecanismos del tren y agarre/vertido;
el cañón y la dirección artística siguen lejos del original. Los dedos 3D usan
la piel de cada apariencia; la restricción de mesa pasó 165 estados. Se corrigió
también el recorte del cuenco tras revisar el HD, no retirando subtítulos.

Eevee tardó **63,35–77,89 s de proceso Blender por clip de 2,2 s** en esta tanda,
sin contar exportación/FFmpeg ni extrapolar a vídeos completos. Hubo reproducción
local real del MP4, p7 real, alfa/sombra/Z, comprobación de encuadres y repetición
de un frame en otra ruta con píxeles idénticos. Esto NO es render nativo Blender
desde la aplicación ni duplicación de un paquete Blender publicado.

La aplicación conserva v5 y su preset/huella; navegador real comprobó reproducción
y formulario vertical sin errores JS. **5.326 archivos previos del estilo y 487
de proyectos intactos**, con las exclusiones de caché/dependencias documentadas
en el informe. No hubo proveedores ni reinicio del servicio.

## Primera integración nativa: candidato separado (histórico)

La primera fase añadió `preparar_ricksclips.py --backend blender`: incluye y
sella servidor bpy, utilidades, cliente IPC y `requisitos/blender.json`. El valor
por defecto sigue siendo `opengl`; las versiones publicadas no se reescriben.
Entonces la publicación del candidato quedó bloqueada hasta completar sus
pruebas y revisión artística; no hereda la certificación visual del piloto.

`pasos/runtime_blender.py` fija Blender 4.5.16 LTS y el ZIP/SHA oficial. Resuelve
`ESTUDIO_BLENDER` si se configura expresamente; en Windows x64 puede reconstruir
una distribución aislada a partir del ZIP verificado. `ESTUDIO_BLENDER_ARCHIVO`
permite suministrarlo sin red y `ESTUDIO_RUNTIMES` cambia su ubicación. El
inventario incluye DLL, Python y licencias; un cambio o archivo añadido falla
sin borrar la instalación. El requisito viaja, no la ruta local del ejecutable.

El ejecutor arranca un único proceso Blender antes de importar la escena y de
instalar la guarda de procesos. El motor sigue sin poder lanzar órdenes propias.
stdin/stdout transportan solicitudes; cada render devuelve PIL RGB y Z reales,
de modo que siguen disponibles varios renders por frame y postprocesos libres.
Preferencias, cachés, imágenes y logs son privados de cada render. Se cierra el
proceso también si falla el motor; se conservan los intercambios fallidos.

La primera comprobación real (`rc7_native_03`, en la carpeta temporal aprobada)
pasó `espacio_estilo.renderizar`, dos renders por frame, postprocesado PIL y copia
sellada a otra ruta con píxeles idénticos. **Es una prueba técnica de 192×320,
no una nueva comprobación artística HD ni la duplicación completa de un proyecto.**
Los intentos anteriores se conservan: detectaron una consulta GPU antes de que
existiera contexto headless y eliminación prematura de materiales reutilizados.

Contratos aislados: `python -B pasos/prueba_runtime_blender.py` (ocho pruebas,
sin red ni Blender) y las 18 pruebas existentes de biblioteca pasaron. El
comprobador real es `herramientas/probar_integracion_blender.py`: requiere estilo,
una carpeta de salida NUEVA y, opcionalmente, `--blender`; sin este argumento
comprueba la resolución automática. Reutiliza una copia de dependencias
ya preparadas y nunca publica ni toca proyectos originales.

Siguen pendientes la conexión completa de los recursos nativos del piloto y sus
anclas a la escena principal, congelado/duplicación completos de proyectos,
recuperación/cancelación y comprobaciones HD/artísticas del nuevo backend. No
confundir el progreso de infraestructura con la resolución de esos pendientes.

### Última comprobación real: rc7_native_06

Se reconstruyó el runtime desde el ZIP oficial ya descargado, sin red. Su
inventario de **5.478 archivos** sigue intacto después de cinco procesos reales.
El intento anterior se conserva: Blender había ignorado la variable de bytecode
y añadido pyc al runtime. La corrección usa `--python-use-system-env` únicamente
con las variables Python heredadas retiradas, user-site desactivado y bytecode
deshabilitado. No se relajó la comprobación de integridad.

La prueba completa pasó: múltiples renders por frame, postproceso PIL, copia
sellada con RGB idéntico, cocina con el rig real, profundidad axial normalizada
(error máximo `5,96e-8`) y cierre también ante error del motor. La escena de fallo
comprueba primero que sigue vetado lanzar un proceso externo. Las cinco sesiones
terminan con retorno 0, incluida la que sirve a esa escena fallida.

Son pruebas pequeñas de **192×320**, no material artístico HD nuevo. La cocina
conserva todavía geometría/acción heredadas; no se atribuyen a esta prueba las
mejoras de olla/agarre del piloto. No se ha publicado v6, reiniciado el servicio
ni modificado proyectos. La comprobación de conservación de esta fase verifica
**12.011 archivos anteriores del estilo y 487 de proyectos**, además de v1–v5.
Los recibos y los fallos viven en `comprobaciones/blender_integracion_02/`.

## Muestra editorial de v5 (histórico)

Antes de publicar v6, la tarjeta mostraba la selección revisada del piloto: 17,6 s,
1080×1920, sin locución, identificada como **vista previa experimental**. Crear vídeo
todavía usaba v5. `muestra_tarjeta.json` selecciona un clip acumulativo por SHA en
`muestras_tarjeta/`; no modifica `estilo.json`, el preset ni `versiones/v5/muestra`.
Una publicación posterior invalida automáticamente esta selección y vuelve a la
muestra del nuevo motor. La ausencia del descriptor conserva el camino anterior.
Pruebas aisladas: `pasos/prueba_muestra_tarjeta.py`. Reproducción y etiqueta
comprobadas en navegador, sin errores JS; evidencia en `comprobaciones/tarjeta_blender_01/`.

## Continuación: recursos conectados al motor principal

La escena principal y `decorados3d.escena` activan las sustituciones nativas al
usar el Renderer Blender, también desde programas libres. OpenGL conserva su
camino anterior. Cocina elimina los dos cuencos heredados y la mesa de actuación
antes de añadir carpintería/encimera/cuenco bpy. Cada actor que vierte proporciona
su mano real tras IK, transformada desde el sprite al mundo, y su piel independiente.
La olla hueca, dedos y chorro siguen esa ancla. Se conserva el material de aceite
entre frames y se retiran los chorros al cambiar de decorado.

Cañón/puente sustituyen paredes y locomotora sin superponer los modelos heredados;
ruedas, bielas, crucetas y vapor usan el reloj de escena. Oeste, taberna, casco,
aparejos, mar y puente mantienen geometría libre transferida a Eevee. Se añade
espuma espacial sobre la cresta. Lluvia, efectos, cámaras, transiciones y
postprocesos Python permanecen disponibles. No es simulación física de fluidos.

La primera conexión de niebla a un volumen infinito de mundo dejó los exteriores
negros. El fallo HD se conserva; se sustituyó por composición atmosférica a partir
del Z axial real, no por una falsa revisión favorable. El flujo P6 reveló además
MAX_PATH en Windows: bpy necesita rutas extendidas y CreateProcess un cwd corto.
El intercambio sigue dentro del trabajo; no se acortan IDs, huellas ni fuentes.
La sonda `--solo-ruta-larga` comprueba un intercambio de más de 300 caracteres.

### Pruebas y puerta de publicación

- `pasos/prueba_ricksclips_blender.py`: nueve contratos offline de selección de
  backend, ausencia de geometría duplicada y bloqueo ante evidencias incompletas.
- `probar_integracion_blender.py`: seis escenarios, ciclo de vertido y holgura de
  mesa, RGB/Z, múltiples renders, copia sellada y error con guarda de procesos.
- `probar_recuperacion_blender.py`: Parar tras render real, timeout del coordinador,
  error bpy, procesos terminados y render posterior; conserva entradas y logs.
- `comprobar_ricksclips_video.py --paquete-local ... --estilo ...`: preparación real
  sobre copias aisladas, congelado, cierre transitivo de rig, generación nativa P6,
  recuperación sin render repetido, P7/P8 reales y duplicación con clips y fuentes.
  Las dependencias del duplicado se instalan desde requisitos, no se copian binarios.
  Narración y marcas son sintéticas de prueba; no se genera voz.
- `validacion_blender.py` reemplaza el veto incondicional por una puerta que exige
  pruebas correspondientes a las fuentes exactas, preparación/P6/P8/duplicación,
  recuperación, 18 secuencias HD y revisión explícita ligada al SHA de cada clip.
  La mera presencia de una muestra o una bandera no permite publicar.

Las preparaciones locales Blender fallidas conservan `.fallido_<id>` en vez de
borrar las fuentes e intercambios de diagnóstico. No son versiones publicadas.
El presupuesto total de render Blender respeta su límite IPC por frame, no el
presupuesto histórico de OpenGL. Ninguno de estos controles certifica calidad
artística equivalente: siguen siendo necesarias comparación y revisión reales.

## Publicación final comprobada

Se publicaron mediante `estilos_ia.preparar(paquete_local=...)` la muestra real
720×1280/25 fps/18 s y la biblioteca, sin constructor ni proveedores. Después se
creó otro proyecto desde el preset REAL: congeló la marca pública v6, ejecutó P6,
recuperó sin regenerar, montó con P7/P8 y duplicó clip/fuentes. El duplicado
reconstruyó dependencias y produjo un póster idéntico.

Se renderizaron, revisaron y reprodujeron **21 secuencias de 2,2 s, 1080×1920/25 fps**,
con SHA de clips/fuentes. Se conservaron todos los fallos, incluido un encuadre de
proa oculto por la ola, corregido en una toma separada. La evidencia y el índice
están en `comprobaciones/blender_publicacion_03/entrega/indice.html`.

La comprobación de tarjeta encontró un fallo adicional: `preparar` había persistido
el campo DERIVADO `muestra_tarjeta` devuelto por `leer`, manteniendo la previa v5.
Ahora `leer` ignora esa copia persistida y preparar no la guarda; la limpieza
explícita retira solo ese campo, sin cambiar estado/marca ni descriptor/clips.
Siete pruebas de muestra y la regresión de preparación cubren este caso.

El navegador comprobó reproducción y bytes EXACTOS de la muestra publicada:
SHA256 `7567d223ee3f0d5c57ea97f8efb04c8f4bc913692741424d1e396efa94976c85`.
No queda etiqueta experimental ni aviso de generar con v5; el formulario usa v6,
vertical, con cero errores JS. La previa editorial anterior se conserva intacta.

Integridad final: **12.011 archivos anteriores del estilo y 487 de proyectos sin
alteraciones**, ajustes y nombre del preset conservados, versiones anteriores
intactas. Solo cambió la marca publicada en la ficha. No se migraron proyectos,
ni se cambiaron sus narraciones, voces, tiempos, firmas o identificadores.
