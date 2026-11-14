# Motor Stickman 2D

`compilar.mjs` empaqueta `escena.js` con esbuild del motor Remotion. El adaptador
usa `core.js`, `styles.js`, `rig2d.js` y `fx2d.js` del kit original en
`GrowKaz_Stickman/skills/make-2d-video/kit/`. Mantener esa carpeta al distribuir
el programa. No hay build del frontend ni instalación de las dependencias Node
del plugin; el render utiliza el navegador/CDP y el codificador del Estudio.

El contrato de entrada es `window.STICKMAN`:

- `variante`: familia, proporciones, ojos, boca, ropa, accesorios, colores y acabado.
- `escena`: ambiente/decorado, atmósfera, cámara, actores y objetos con claves temporales.
- `duracion`, `ancho`, `alto`, `fps`: salida y reloj del plano.

`window.pintar(t)` dibuja el instante local en Canvas. Poses, respiración,
caminata, expresiones y efectos son deterministas. Claude/Codex producen JSON
validado en `pasos/stickman.py`, nunca programas que se ejecuten desde el modelo.

## Puesta en escena y utilería

El lienzo lógico mide 1920 de ancho y `1920 * alto_salida / ancho_salida` de
alto. Las posiciones son normalizadas. En un actor, `x,y` sitúan sus **pies**;
su altura aproximada es `240 * escala * diseno.altura`. Las entregas nuevas se
comprueban antes de renderizar y vuelven al modelo para corregir personajes
ilegibles/fuera de encuadre y escenas sin desarrollo temporal. La dirección
pide presentación, acción y reacción, priorizando la descripción visual y
evitando títulos sustitutivos de la acción y decoración sin función narrativa.

Además de las primitivas, hay tipos reconocibles `movil`, `mensaje`,
`calendario`, `nube` y `corazon`. Los objetos usan `w,h` como dimensiones, también
el círculo (elipse); `texto` ajusta su letra a esa caja con `fuente` independiente
(16–96). `linea` usa `w,h` como vector desde su origen, admite cero y valores
negativos, y tiene `grosor` independiente. Las claves admiten `opacidad` y
`progreso` (0–1); progreso dibuja la línea o revela las marcas del calendario.

`ancla: {personaje: ID, punto: "mano" | "cabeza" | "pecho"}` hace que el objeto
siga el punto animado del rig. En ese caso `x,y` son desplazamientos normalizados
desde ese punto; el tamaño del objeto sigue expresado en unidades del lienzo.
Sin ancla, los objetos están centrados en `x,y` (salvo el origen de la línea).
Una primera clave tardía interpola desde el valor base, sin anticipar el destino.
La cámara queda fija salvo claves explícitas; sus desplazamientos también son
normalizados. La atmósfera predeterminada no añade partículas.

La versión `stickman-3` evita reutilizar planes antiguos al solicitar una nueva
generación. Los clips ya publicados siguen siendo reproducibles; para aplicar
la corrección a ellos hay que regenerar las animaciones.

## Catálogo extensible de utilería

`pasos/utileria_stickman.py` mantiene fichas vectoriales inmutables, identificadas
por SHA-256 del contenido. No contiene una lista cerrada de conceptos: al dirigir
una escena, el modelo recibe un índice del catálogo (hasta 100 candidatos,
priorizados por el contexto) y puede referenciar un recurso existente o entregar
una definición nueva en `utileria`. La resolución también consulta el catálogo
completo, aunque el concepto no haya entrado en el índice resumido. Ante una
referencia ausente se pide al modelo que la dibuje o elija una existente. Un
concepto conocido se reutiliza aunque el modelo intente volver a definirlo.
Las referencias por huella ya fijadas conservan siempre su dibujo exacto.

Ejemplo de instancia: `{tipo:"vector", recurso:"avion", x:.5, y:.4, w:600, h:300}`.
Al validarla, `recurso` se sustituye por la huella y la definición usada se incluye
en `escena.utileria[huella]`. `w,h` delimitan una caja centrada; el dibujo se
ajusta conservando la proporción. `paleta` opcional permite sustituir colores
sin cambiar el recurso original.

Una definición contiene `concepto`, `nombre`, `descripcion`, `etiquetas`,
`ancho`, `alto` y `partes`. Cada parte agrupa `formas`, tiene un `id` y un
`pivote:[x,y]`. Las formas son trazados numéricos M/L/Q/C/Z, rectángulos o
elipses. No se aceptan código, imágenes externas ni SVG arbitrario. Los
rellenos y trazos admiten colores hexadecimales o `$principal`, `$secundario`,
`$contorno`, `$claro`, `$oscuro`; esas referencias se resuelven contra el estilo
del vídeo y la paleta de la instancia.

`parte.animacion:{duracion,claves}` define un ciclo reutilizable (por ejemplo,
una hélice). Las claves de parte animan desplazamiento local `x,y`, `rot` en
radianes, `escala` y `opacidad`. Una instancia puede añadir
`partes:[{id,claves}]` para acciones propias de la escena: solo sustituye los
campos indicados. Los ciclos usan segundos desde la aparición del objeto; las
claves particulares usan segundos locales de escena. El contrato completo que
reciben ambos modelos está en `utileria_stickman.CONTRATO`.

Persistencia, por orden de preferencia:

1. `ESTUDIO_UTILERIA_STICKMAN`.
2. Carpeta `utileria_stickman` junto al banco o los proyectos, si
   `ESTUDIO_BANCO` o `ESTUDIO_PROYECTOS` apuntan fuera del programa. Así funciona
   también el servicio instalado con HOME protegido y datos en `/opt/.../datos`.
3. Datos del usuario: `$XDG_DATA_HOME/as-video-studio/utileria_stickman` (por defecto
   `~/.local/share/...`) o `%LOCALAPPDATA%/as-video-studio/utileria_stickman`.

La escritura es atómica y usa cerrojo entre procesos. Solo se publican
definiciones válidas que se hayan referenciado en la escena. El catálogo global
no entra en las firmas de escenas ya generadas: agregar un objeto no invalida
vídeos anteriores. El plan de escena incluye las definiciones exactas y cada
versión guarda también `utileria_stickman/<huella>.json` para indexarlas al
retomar, duplicar o importar un vídeo. Al utilizarlas durante una generación
se incorporan también al catálogo del destino. Leer/previsualizar un proyecto
no modifica params ni requiere tener el catálogo original.

El paso `assets` conserva por escena:

- `escenas/<id>.animacion.json`: firma del encargo y plan de acción, reutilizable tras un fallo.
- `escenas/<id>_<huella>.mp4`: animación visual inmutable, sin narración ni efectos embebidos.
- `escenas/<id>.png`: póster.
- `escenas/<id>.json`: recibo de publicación, narración, firma y recursos de sonido.
- `sonidos/<id>_<índice>_<huella>.wav`: sonidos sintetizados por `audio/sfx.py` y `audio/dsp.py` originales.

La ficha se publica después del clip y de sus efectos. Las rutas de la ficha y
el manifiesto son relativas a la versión de assets; `aplicar_recursos` las
resuelve para la previa, el editor y el montaje, también en trabajo parcial.
No persistir las rutas absolutas resueltas dentro de `plan.json`.

Los efectos usan bloques `stickman:<índice>` de la pista Sonidos. La mezcla final
y la previsualización consumen los mismos eventos. No muxearlos además en el
clip visual: sonarían dos veces. Narración y diálogos conservan sus pistas.

Las definiciones de personajes se guardan en `guion.params.personajes` y un
recibo junto a su PNG inmutable en `medios_usuario/animaciones/`. Al guardar se
comprueba que la definición pertenece al personaje generado, sin admitir fotos
subidas o POV como sustitución de un rig.

Pruebas: `python pasos/prueba_stickman.py` (contratos y síntesis) o
`python pasos/prueba_stickman.py --real` (Chromium, ffmpeg, estilos, interrupción,
reanudación, montaje audible y traslado del proyecto). No llaman a proveedores.
