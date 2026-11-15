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

Desde `stickman-5-editorial-1`, la escena admite `realizacion`, `graficos`,
`efectos_visuales` y `espacio3d`. El adaptador conecta todas las familias de
`ui2d.js` y `fx2d.js`, el rostro grande y atrezzo de `rig2d.js`, y el stage,
constructores, materiales y cámaras de `three-kit.js`. Los escenarios estables,
encuadres y componentes editoriales se componen en los módulos de esta carpeta.
El acabado del player original se adapta al reloj del Estudio; no se arranca
un segundo montaje ni se duplica el sonido.

Desde `stickman-5-editorial-2`, el director prioriza las instrucciones explícitas
de la descripción sobre la paleta y la continuidad. `realizacion.color_fiel:true`
omite la gradación cromática del estilo (conserva viñeta y grano); no cambia los
colores del decorado por sí solo. Las nuevas entregas parten de ese modo. Una
transformación debe mostrar su resultado y retirar los elementos anteriores que
ya no correspondan; no basta con acercar la cámara.

`poblacion` admite `filas`, `columnas`, `color_base`, `color` del destacado,
`indices_destacados` (desde cero, por filas), `atenuacion` (opacidad final del
resto), `inicio_destacado` y `duracion_destacado`. Por ejemplo, cien figuras en
diez filas usan `total:100,filas:10,columnas:10`; el índice 20 está en la tercera
fila. Todas se ven desde el comienzo; después progresa el destacado. Se rechazan
índices duplicados/fuera de rango y cuadrículas sin capacidad suficiente.

El actor admite `vestuario:{ropa,color,secundario}` para prendas explícitas de
esa escena: se aplica sobre una copia del diseño, sin cambiar la identidad ni
el reparto guardado. El director debe conservarlo si continúa la misma acción.

Todos los textos editoriales reciben un contorno claro u oscuro según la
luminancia de la tinta, manteniendo el color solicitado. Los objetos `texto` se
dibujan después del acabado, conservando sus anclas y cámara; los rótulos de
pantalla deben utilizar `graficos` con `capa:pantalla`. El resplandor no tapa el
contorno. Estas correcciones requieren regenerar los clips existentes.

Los encuadres generales, gráficos y detalles
ajustan zoom y posición para que el conjunto explicativo quepa dentro del lienzo,
con un 4% de margen. Los límites incluyen las trayectorias, poses, textos y partes
vectoriales animadas; se calculan para toda la escena para evitar saltos al
aparecer una fila. Los encabezados/pies de pantalla tienen espacio reservado.
Los planos medios y primeros planos mantienen su encuadre narrativo del sujeto.
El factor de detalle de 2,6 queda limitado por el espacio que ocupa el contenido.

Los tiempos locales toleran diferencias de hasta un microsegundo y se ajustan
al límite exacto: `3.803` debe ser válido frente a `3.8029999999999973`.
Un exceso real sigue rechazándose; el diagnóstico indica campo, valor e intervalo.
Estas correcciones de render y validación conservan la versión de firmas para
reutilizar los planes existentes al continuar una tanda.

Instalar `npm ci --prefix motores/stickman` además de Remotion: fija Three.js y
las fuentes originales. El bundle contiene las fuentes sin depender de la red.
Python espera `window.STICKMAN_READY` antes de capturar. Los planes históricos
sin realización conservan el dibujo anterior.

Contrato y mapa completo: [STICKMAN_EDITORIAL.md](../../docs/STICKMAN_EDITORIAL.md).

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
`calendario`, `nube`, `corazon`, `pizarra` (marco, bandeja y tiza) y `tarjeta`
(papel con borde). Su contenido se compone dentro de su caja, con otros objetos.
Los objetos usan `w,h` como dimensiones, también
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

La versión `stickman-4` evita reutilizar planes antiguos al solicitar una nueva
generación. Los clips ya publicados siguen siendo reproducibles; para aplicar
la corrección a ellos hay que regenerar las animaciones.

El guion Stickman entrega `escenas_visuales` por bloque, una entrada por frase
literal (sin SSML), con `texto`, `descripcion_visual` y `personajes_visibles`.
Se comprueban cobertura, orden, reparto y descripciones repetidas antes de TTS.
El montaje selecciona la dirección por la frase narrada, no copia la secuencia
completa del bloque en cada corte. Una frase editada sin actualizar su dirección
utiliza la del catálogo, sin asociarle otra entrada antigua. Los guiones anteriores
sin esta lista conservan su lectura; al regenerar animaciones, el director recibe
la frase anterior y siguiente y debe adaptar la descripción global al corte actual.
Además recibe `continuidad_bloque`: las descripciones visuales de todas las frases
y los planes de animación publicados de la raíz y la escena anterior. Conserva
escenario, geometrías, focos y actores que esperan su turno, partiendo de las
últimas claves de la anterior y adaptando los tiempos al nuevo corte. El contexto
se recupera del disco al continuar una tanda o regenerar una escena suelta, cruza
el reparto Claude/ChatGPT y se reinicia al cambiar de bloque. Las referencias
participan en la firma del encargo; no se modifican clips publicados al leerlos.
Las descripciones nuevas priorizan acciones corporales sencillas y utilería
reconocible frente a metáforas anidadas y cadenas de iconos. El ancla `pecho`
está entre hombros y cadera; no sobre el cuello.
Las claves de actor admiten `mirar: -1|1`: el giro se aplica en ese instante,
sin interpolar un reflejo a través de cero, y las anclas siguen su orientación.

### Desplazamiento, paradas y salidas

`movimiento: caminar|correr` anima las piernas solo en los tramos donde cambian
los pies (`x` o `y`). Al alcanzar el destino, el actor vuelve a su pose y
respiración; no sigue andando sobre el sitio. Las claves admiten también
`movimiento: gesto|caminar|correr` para cambiar de modo por tramos. Para esperar
antes de partir, repite la posición en la clave de partida:

```json
{"id":"ana","x":0.2,"y":0.87,"movimiento":"caminar","transito":true,
 "claves":[{"t":0,"pose":"stand"},{"t":1,"x":0.45,"movimiento":"gesto","pose":"talk"},
           {"t":2,"x":0.45,"movimiento":"caminar"},{"t":3,"x":1.4}]}
```

`transito:true` permite entradas/salidas horizontales entre x=-.5 y 1.5,
conservando los mínimos de tamaño y los límites verticales. El actor y su utilería
anclada no amplían los límites del encuadre automático: la cámara no debe rescatar
a quien abandona la pantalla. Utiliza general/conjunto y lleva todo el cuerpo
fuera, normalmente x=-.4 o 1.4, no solo hasta el borde. Las poses y posiciones
finales se conservan al transmitir continuidad a la siguiente escena. Los MP4
publicados necesitan regenerarse para mostrar esta corrección.

## Paletas editoriales y neón selectivo

`realizacion.paleta: ember|arctic|sakura|retro` selecciona fondo y tintas de
grafismo desde `paletas.json`, compartido con las instrucciones del director.
No recolorea el vestuario ni los materiales de utilería. Un `fondo` o color
explícito tiene prioridad. En escenarios vacíos se usa el fondo profundo de la
paleta; los decorados narrativos conservan su iluminación y materiales.
Arctic Glass incorpora además `detalle:#ffcb52`: amarillo cálido para títulos,
cifras, etiquetas y umbrales explicativos. Se conecta a `ui.accent`; el azul
principal permanece en `ui.gold` y el turquesa en las tintas estructurales.

Los `graficos` y `objetos` admiten `neon:0–1` (normalmente `.2–.4`):
`{tipo:"bigLine",neon:.3,opciones:{str:"GENES",color:"#76ccff"}}`.
En `neon.js` se dibuja el elemento en una capa aislada, se tiñe una máscara
alfa con el color de acento y se compone desenfocada debajo del original nítido.
El texto conserva una protección de contraste fina. No se desenfoca el lienzo
completo ni se extiende el halo a elementos vecinos. En vectores, `color`
define el halo y `paleta` conserva las tintas interiores. Siluetas gráficas
pueden usar `lineFigure`. La ausencia de `paleta`/`neon` conserva el render
histórico. Para aplicar la dirección nueva a clips existentes hay que regenerar.

Pruebas de contrato y píxeles: `python pasos/prueba_stickman_editorial.py --real`.

### Fondos vivos y bocadillos vinculados al rostro

`realizacion.particulas:true` activa partículas suaves y lentas de fondo;
`desfase_ambiente` (segundos) mantiene su reloj entre escenas. `malla:true`
añade una cuadrícula tenue sin relleno opaco. En generación nueva se activan
partículas y, en gráficos Arctic Glass, la malla. Los valores explícitos `false`
se conservan; leer planes históricos y retocar una animación existente no les
inyecta estos valores. No se cambia la versión de firmas de las tandas.

`graficos` admite `bocadillo` con `capa:pantalla` y
`opciones:{personaje:"ID",modo:"dialogo"|"pensamiento",texto:"Frase breve"}`.
El personaje debe estar presente en la escena. La cola triangular de diálogo o
los círculos de pensamiento apuntan al borde del rostro proyectado con la misma
cámara que el actor; el recuadro y el texto mantienen tamaño de pantalla. Se
coloca por defecto en un lateral, con texto oscuro sobre fondo claro, ajuste
multilínea y margen seguro. Admite x,y,w,h,size,color,tinta. `bubble` sigue
disponible para iconos genéricos, sin vínculo con un actor.

`poblacion.opciones.neon_destacados:0–1` ilumina únicamente los índices
seleccionados, conservando intactas las figuras de contexto.

## Comparaciones luminosas

`realizacion.comparacion:{color_izquierdo,color_derecho,color_separador,corte}`
activa el escenario de `comparacion.js`. Sus tintas son opcionales; por defecto
combina luz azul fría y ámbar cálida, reflejos de suelo y partículas diferenciadas.
`corte:quebrado|diagonal|vertical` controla una unión luminosa común al fondo y
al recorte de actores/objetos con `panel:izquierda|derecha`. El recorte se hace
en pantalla antes de restaurar la cámara; no debe desplazarse con zoom o paneo.
La ropa y los materiales conservan sus tintas; solo el contorno recibe luz local.

El gráfico `comparacion` admite `titulo`, `izquierda`, `derecha`, hasta tres
`rasgos_izquierdos`/`rasgos_derechos` y detalles opcionales. Con el escenario
luminoso usa tipografía Fredoka grande, títulos claros y halo ligero con contorno
fino. Los objetos de texto de esa comparación utilizan también la fuente del kit.

Solo al generar se añade este acabado a `dividido` y a gráficos `comparacion`.
`preparar_comparacion_nueva` devuelve al proveedor los planes que lo cubren con
paneles opacos, franjas de suelo o separadores manuales. La lectura histórica y
los retoques que conservan el acabado anterior siguen siendo compatibles.
Comparaciones de objetos usan `grafico` y sus paneles, sin exigir dos actores.

## Portadas de capítulo

`capitulos_guion.py` valida los capítulos de la escaleta y asigna sus bloques
reales. `capitulo:{numero,titulo,estilo}` es metadato del bloque; P6 marca
`apertura_capitulo` únicamente en su primera escena, con el tiempo disponible.
El estilo admite arctic, ember, mixto, sakura o retro. Los planes históricos sin
estos campos no reciben capítulos al abrirse ni cambian sus firmas.

`capitulo.js` dibuja el componente `graficos.tipo:capitulo` a pantalla completa,
después de las demás capas: número de dos dígitos con halo, línea, título
multilínea legible y partículas frías/cálidas. Las portadas breves se preparan
localmente sin consultar al proveedor. En escenas largas se añade una apertura
de 1,8–2,8 s dentro de su reloj y el director reserva el resto para el contenido.
No se añade silencio ni se alarga el clip. Las escenas siguientes del capítulo
no heredan la portada desde continuidad. Los retoques locales conservan su base.

El gráfico manual usa `{tipo:"capitulo",capa:"pantalla",opciones:{numero:1,
titulo:"La pregunta",estilo:"mixto"}}`. Se evita generar también la cabecera SVG
antigua del catálogo en escenas con estructura de capítulos Stickman.

## Escenografía detallada

`realizacion.escenografia_detallada:true` activa `escenografia.js` para los
decorados construidos. Las generaciones nuevas lo usan por defecto; los planes
anteriores y los retoques locales conservan su ruta si no solicitan este acabado.
No se cambia la versión de firmas ni se modifican parámetros al leer proyectos.
Al continuar el mismo id/tipo se heredan acabado, semilla, atril, público y luz
si el proveedor los omite. Una referencia histórica sin el campo de detalle
mantiene su dibujo al continuar; una regeneración explícita envía
`renovar_escenografia:true` al director y permite renovar el acabado. Ese indicador
es contexto de ejecución, no un parámetro guardado ni un cambio de firma global.

La arquitectura se pinta en el plano de fondo con su desenfoque; suelo y muebles
comparten cámara con los pies; cortinas laterales y público quedan en primer
término. El foco del teatro utiliza la posición real de `sujeto` o del actor
principal, también con zoom/paneo. Los contornos reciben luz local sobre una
copia del diseño, sin mutar el reparto. Los materiales no heredan el acento de marca.

En `realizacion.escenario`, el teatro admite `atril:true|false`, `atril_x:.15–.85`,
`publico:true|false` y `luz:"#RRGGBB"`. El atril es opcional; el público por
defecto son cabezas en primer término, no figuras diminutas. `particulas:false`
apaga el polvo luminoso del haz. Se evitan duplicados con dust/público explícitos.
`fondo` puede cambiar el tono de pared o telón conservando sus pliegues y volumen.

La validación de entregas nuevas pide retirar rectángulos o blueprints que
tapen el decorado, y un crowd duplicado del teatro. `escenografia_detallada:false`
mantiene el dibujo sencillo. Pruebas de materiales, público, movimiento y ancla
del foco: `python pasos/prueba_stickman_editorial.py --real`.

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

En generaciones nuevas, cada instancia debe declarar en `paleta` todos los slots
`$` utilizados por su dibujo. El validador devuelve los slots ausentes al director
para corregirlos antes de renderizar: la utilería no debe heredar automáticamente
el verde/azul del vestuario ni los contornos de marca. El índice del catálogo
incluye rellenos y trazos por parte para elegir según su material (fachada,
tejado, madera, manta, piel y rasgos), también al reutilizar dibujos antiguos.
Los dibujos nuevos priorizan colores hexadecimales propios de cada material;
las instrucciones explícitas de la escena tienen prioridad. Las fichas y sus
huellas siguen siendo inmutables. La lectura de planes históricos no exige
paletas nuevas ni invalida clips terminados.

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
`python pasos/prueba_stickman_editorial.py --real` comprueba además el catálogo
gráfico/FX completo, fuentes, continuidad de componentes, capas, determinismo y 3D.
