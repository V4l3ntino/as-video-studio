# AS Video Studio — lo que hay que saber antes de tocarlo

## Entrega y espera del guion

La redaccion usa **Opus/medium** por defecto; los params explicitos siguen
mandando. El 15-11-2026, Opus/xhigh gasto 122.569 tokens de razonamiento y
22 minutos antes de devolver un mensaje que empezaba a mitad del guion.
`p3_guion._llamar_claude` conserva su firma para el medidor de coste, pero
entrega mediante `cli_claude.escribiendo(entrega_cruda=True)`: el guion va al
fichero temporal y el sobre conserva tokens/consumo antes de validar. No
vuelvas a transportar guiones largos en el mensaje final del CLI.

El umbral automatico de reintento tiene techo de cinco minutos; un fallo largo
no debe desencadenar otros veinte minutos de generacion. La prevision usa
`redaccion_guion`, separada del historial antiguo por palabras de transcript,
y cuenta la longitud solicitada y la direccion visual Stickman. El mensaje
publico del guion conserva intento y reloj: el porcentaje es estimado, no una
observacion de que Claude este escribiendo el cierre. Contrato sin proveedores:
`python pasos/prueba_p3.py` y `python pasos/prueba_ajustes.py`.

## Escaleta y redaccion editorial

Las redacciones nuevas pasan por escaleta, narracion y direccion visual posterior
si hay personajes, dentro del MISMO paso `guion`. Los guiones propios y las
correcciones locales siguen el camino anterior; `escaleta_previa:false` permite
compararlo sin cambiar de modelo. `editorial_guion.py` valida reparto de palabras,
cobertura de tramos y la inmutabilidad de texto, orden y hablantes al dirigir.
El mapa de bloques sale de la escaleta previa, no de una justificacion posterior.
No uses la direccion para corregir una narracion: debe fallar si intenta cambiarla.
Las estadisticas de escaleta/narracion/direccion son distintas; conserva el
enganche `_llamar_claude` del medidor de coste para todas las llamadas.

Una auditoria real encontro 22 palabras de tema para 2.261 palabras de guion,
sin dosier ni referencia inglesa, y una guia que exigia anunciar una revelacion
y reservarla para el ultimo tercio. No atribuyas el resultado solo al modelo.
Con material escaso el plan registra limites y evita fabricar estudios concretos.
`escaleta.json` y `narracion.json` son auditoria, no cache para retomar: el paso
limpia trabajo al empezar. Comparacion opt-in y aislada del original:
`herramientas/evaluar_guion_editorial.py --help`. Contrato sin proveedores:
`python pasos/prueba_editorial_guion.py`.

## Proveedores de voz

`voz.params.proveedor` elige `cartesia` (ausencia = contrato histórico) o
`elevenlabs`. No escribas ese defecto al abrir proyectos. El catálogo usa
`/api/voces?proveedor=...`; la clave de ElevenLabs se conserva en secretos y
se espeja como `ELEVENLABS_API_KEY`. `motores/voz_elevenlabs/voz.py` devuelve
PCM mono a 44.100 Hz y marcas por palabra a partir de la alineación por carácter.
Solicita PCM a 24 kHz y lo remuestrea con ffmpeg: 44,1 kHz directo requiere Pro.
Multilingual v2 limita cada petición a 10.000 caracteres; las tomas usan 9.000
y contexto anterior/posterior. No introduzcas fallback a Cartesia ni repitas
automáticamente una síntesis pagada. Los fonemas `<< >>` son de Sonic, no de
ElevenLabs: solo admite aquí aliases escritos. Los costes se distinguen por
proveedor y no se les aplica la tarifa de Cartesia. Prueba aislada, incluida
regrabación y navegador sin proveedores: `python pasos/prueba_elevenlabs.py --real`.

## Pronunciaciones de voz

`voz.params.pronunciaciones` es texto editable «Nombre = lectura», una entrada
por línea, heredado desde el estilo solo al crear vídeos. `pasos/pronunciaciones.py`
aplica el diccionario DESPUÉS de sanear SSML y solo en las peticiones TTS (SSE y
contextos WS): el guion guardado nunca lleva la grafía fonética. Sonic 3/3.5
aceptan fonemas `<<ˈ|w|ɪ|l|j|ə|m>>`; no los pases otra vez por `marcas_tts.sanear`,
ni descartes sus marcas por contener ángulos. Antes de repartir escenas, se
restauran las palabras originales conservando las anclas temporales. Las lecturas
con distinto número de palabras reparten solo el tramo sustituido.
La muestra de voz lee los nombres del diccionario cuando lo hay; su caché también
depende de las pronunciaciones. En revisión, quitar el diccionario debe impedir
sellar una toma que todavía lo usaba: comparar solo las claves del cfg nuevo
ignora esa eliminación. Regresión aislada y navegador:
`python pasos/prueba_pronunciaciones.py --real` (sin proveedores).

## Stickman 2D

Un tachado con `linea` independiente quedaba azul hielo y detrás de las letras,
porque los rótulos se pintan después del acabado. Los objetos `texto` admiten
`tachado:{inicio,fin}`: `texto.js` pinta rojo sobre la tinta, mide la fuente ya
ajustada y cruza el centro de los glifos; comparte posición, escala, rotación y
opacidad del rótulo. La dirección cromática reserva rojo para tachados incluso
en Arctic Glass; el director debe usar este campo, no un conector independiente.
Es opcional: no lo infieras al abrir planes históricos ni cambies VERSION.
Contrato y superposición comprobada con píxeles: `prueba_stickman_editorial.py --real`.

Las líneas de reacción son `graficos[].tipo:enfasis`, no objetos permanentes ni
un efecto inferido de la expresión base. `enfasis.js` dibuja sorpresa/sobresalto/
descubrimiento/enfado/confusion/impacto con pulso de .2–.4 s, subida rápida,
crecimiento leve y salida amortiguada. Se valida capa pantalla sin desfase/ciclo:
personaje presente para reacciones, punto normalizado de mundo para impacto.
`editorial.js` proyecta el ancla con la cámara, también en planos cortos; si no
cabe encima del rostro, usa el lateral. La dirección los pide solo ante una
reacción/acción concreta y evita duplicar el impacto de puerta nativa. No se
inyectan al leer planes, ni se cambia VERSION. Contratos y doce renders en
`prueba_stickman_editorial.py [--real]`.

Rascarse la cabeza no es `handsOnHead` ni alternar saludos: `scratchHead` en
`actuacion.js` mueve solo una mano tangencialmente sobre la sien, compensando
cabeza/cuerpo, con el otro brazo en la cadera. Las claves se resuelven antes de
mezclar y respirar, también para anclas y límites. El ciclo acaba al cambiar de
pose; no muta POSES del kit ni añade expresiones. La mirada usa actuacion.mirada.
Contrato geométrico y renders de las cuatro familias en `prueba_stickman_editorial.py`.

Los portazos no deben encoger/agrandar un vector. `puerta.js` implementa el objeto
nativo `puerta` con marco fijo, bisagra izquierda/derecha y proyección de la hoja,
paneles y pomo. `cierre:{inicio,fin}` acelera el giro, marca el impacto y amortigua
la vibración del borde libre en .55 s; la amplitud se convierte a píxeles de salida.
`pushReady`/`push` son poses locales: la dirección debe colocar la mano y coordinar
soltar/bajar el brazo y caminar después. La puerta se pinta por defecto en fondo
al mismo plano de los actores, para no ocultarlos, y cuenta en el encuadre seguro.
No conviertas utilería ni planes históricos al leer, ni cambies VERSION. Regresión
offline y Canvas de ambas bisagras: `prueba_stickman_editorial.py [--real]`.

S012 tapaba psicópata/sociópata: el gráfico documento opaco de pantalla se pintaba
después de los objetos, y sus renglones eran guiones de texto. El documento nuevo
usa opciones.estilo:neon y excluidos:[...], hasta dos términos: `documento.js`
compone hoja, título, trazos y términos/cruces exteriores juntos. La generación
asigna el estilo y rechaza rótulos independientes que invaden la hoja mediante
`preparar_documentos_nuevos`; no conviertas planes históricos al leerlos.
`realizacion.resplandor:true` se activa en entregas nuevas: neón selectivo en
rótulos, gráficos y acentos pequeños, respetando neon:0. `neon.js` combina halo
local y núcleo, sin ampliar el blur hasta contaminar los colores de elementos
vecinos. Las auras explícitas usan actuacion.aura:{color,intensidad}; `conAura`
genera la máscara de la figura en su pose/cámara actuales. Figura y busto deben
usar el contexto recibido, no el canvas global, para aislar bien esa máscara.
No infieras auras a partir de cualquier círculo ni cambies VERSION. Contrato,
composición, colores interiores y resplandor: `prueba_stickman_editorial.py --real`.

Una interacción de grito/defensa salía erguida con gestos de explicación y dos
textos pequeños apilados. Las poses locales `shout` y `recoil` viven en
`motores/stickman/actuacion.js`, sin mutar POSES del kit; se usan también al
calcular los límites de cámara. `etiqueta` dibuja marco y Fredoka multilínea
como un único objeto animable con halo opcional. `objetos[].transito:true`
excluye su trayectoria del encuadre seguro para permitir salidas reales, igual
que en actores. No lo inyectes al abrir planes ni cambies VERSION. Contrato,
actuación y salida comprobados en `prueba_stickman_editorial.py --real`.

El vecino tenía angry y la oficinista pasaba a determined sin que su descripción
pidiera esas caras. Además, rig2d dibuja las pendientes angry/worried invertidas:
angry parecía preocupado. Las entregas nuevas usan expresiones_fieles:true;
`motores/stickman/expresiones.js` corrige localmente cejas y hace neutral sin
sonrisa impuesta en Classic, familias y bustos. No mutes EXPR ni el kit original.
`pasos/expresiones_stickman.py` pide neutral si la descripción actual no motiva
otra cara, con motivo_expresion literal por actor/cambio no neutro; valida las
citas solo al generar con descripcion_visual. No infieras emoción del perfil,
los colores o teclear/gesticular ni la contagies entre actores por continuidad.
La cita no cuenta como cambio temporal. La lectura histórica conserva su ruta;
no cambies VERSION. Regresión offline y pendientes Canvas en
`prueba_stickman_editorial.py --real`, sin proveedores.

S004 editada quedó con angry en base y cuatro claves, pero sin expresiones_fieles:
la corrección anterior solo se activaba al generar desde cero y la IA omitió la
marca al editar. `validar_entrega` y el cierre de `generar_escena` fuerzan ahora
`realizacion.cejas_fieles:true` en toda edición, aunque el proveedor lo omita o
envíe false. Corrige las cejas en las tres rutas del renderer sin convertir las
bocas neutras históricas a smallFlat ni activar otros acabados. No dependas de
que el prompt/modelo recuerde esta corrección del motor ni cambies EXPR original.

Los textos normales usaban sans-serif aunque Fredoka estuviera cargada: describir
letras redondeadas no cambiaba ese render. Las entregas nuevas reciben
`realizacion.tipografia:redondeada` en `validar_entrega`; `escena.js` aplica
Fredoka 700 con volumen interior (`texto.js`) y admite fuente hasta 160.
El halo sigue siendo local/selectivo mediante neon; no desenfoques los glifos.
No inyectes el campo al abrir ni en retoques históricos de cámara/actuación;
`clasica` o ausencia conserva su ruta. No cambies VERSION ni invalides recibos.
Contrato y fusión animada sin proveedores: `prueba_stickman_editorial.py --real`.

El teatro antiguo era franjas verticales, suelo genérico y `FX.crowd` diminuto:
el fallo era construcción/escala del decorado, no solo falta de partículas.
`escenografia_detallada:true` activa `escenografia.js` en entregas nuevas:
arquitectura al fondo, suelo/muebles a profundidad 1 y cortinas/público delante.
No metas otra vez el suelo dentro del blur/paralaje .65 del fondo: se separa
del apoyo de los pies al mover la cámara. El foco usa `draw.estado` del sujeto;
su reflejo debe coincidir con los pies en pantalla. El público del teatro son
siluetas cercanas; `publico:false` permite teatro vacío/público personalizado.
`atril` es opcional y `atril_x`/id/semilla mantienen su ubicación, no lo arrastres
con cada gesto del actor. Materiales y luz local no mutan identidades guardadas.
La generación rechaza paneles/blueprint que tapan el escenario y crowd duplicado;
la lectura histórica y un retoque local sin este campo conservan el dibujo anterior.
`heredar_escenografia` recupera semilla/atril/público/luz del mismo id/tipo si se
omiten. La continuidad antigua sin campo de detalle conserva acabado false al
continuar un bloque. Rehacer explícitamente pasa `renovar_escenografia:true`
solo como contexto del ejecutor, para no impedir que se actualice esa escena;
un retoque de zoom/actuación no debe recibirlo ni cambiar el acabado por defecto.
No cambies VERSION ni persistas defaults al abrir. Regresión y nueve decorados:
`python pasos/prueba_stickman_editorial.py --real`, sin proveedores.

Los capítulos de guiones Stickman nuevos se deciden en `escaleta.capitulos`
antes de escribir: numero/titulo/estilo y tramos contiguos, sin huecos en el
desarrollo. `capitulos_guion.asignar` los enlaza a bloques reales; no inventes
un capítulo por escena ni locutes títulos para justificar una portada. La
dirección no puede cambiar ese metadato, y una corrección hereda la estructura
del guion anterior si el proveedor omite sus campos. El propio del usuario y
los guiones históricos no reciben numeración al abrirse.
`descripciones_escenas` transmite el capítulo efectivo y P6 marca solo su
primera escena con `apertura_capitulo`, calculada al reloj de la voz actual.
El render `capitulo.js` es local y autoritativo: una frase <=3 s puede ser
portada completa sin llamada al CLI; en una larga ocupa 1,8–2,8 s y el director
reserva el resto. No añadas escenas o pausas al audio ya generado ni arrastres
portadas por continuidad. Suprime solo las cabeceras SVG antiguas que duplican
estos capítulos estructurados, no las de planes históricos sin metadato.
Exportar/importar conserva capitulo por bloque. Los cambios solo visuales de
capítulos van a assets.unidades.descripcion_escena, no a params guion/voz;
guardar después una descripción debe conservar también ese capítulo efectivo.
La UI inserta encabezados sin reemplazar los campos al refrescar por tandas.
No cambies VERSION. Pruebas: `prueba_editorial_guion.py`,
`prueba_descripciones_escenas.py --real` y `prueba_stickman_editorial.py --real`.

Una comparación plana real usaba encuadre conjunto,
dos rectángulos opacos azul/rojo, bandas grises y una línea blanca manual:
tapaba el escenario, no era solo falta de bloom. `realizacion.comparacion`
activa `comparacion.js`: luz fría/cálida, reflejos, partículas y borde de neón.
Los planes nuevos dividido/comparacion lo reciben en `validar_entrega`;
`preparar_comparacion_nueva` pide eliminar los paneles que lo cubren, sin
borrarlos silenciosamente ni mutar proyectos al abrir. Los retoques históricos
no se convierten por defecto; un retoque que elige comparacion sí se valida.
El clip de cada panel se fija en pantalla antes de volver a la cámara: si se
recorta en coordenadas de mundo, el borde se separa del neón con zoom/paneo.
Los contornos locales no mutan las identidades. Los títulos/rasgos comparativos
usan Fredoka grande con borde fino; los textos de otros planos conservan su ruta.
Regresión: `prueba_stickman_editorial.py --real` (fondos no planos, movimiento,
recorte con cámara y comparación de objetos sin actores). No cambies VERSION.

Las referencias visuales se transmiten a descripciones (`direccion_color`) y
dirección de animación (`realizacion_stickman`). Las generaciones nuevas añaden
`particulas:true`, `desfase_ambiente:t_in` y malla en gráficos Arctic Glass;
no los inyectes al leer planes históricos ni al editar solo zoom/actuación de
un clip previo. `ambiente.js` pinta una malla transparente y partículas detrás
de actores/rótulos, sin tapar fondos explícitos ni duplicar blueprint/dust.
`bocadillo` requiere un personaje presente y capa pantalla: proyecta su cabeza
con la cámara real y une cola triangular o círculos según diálogo/pensamiento.
El texto se ajusta dentro de una caja lateral, después de la gradación. No uses
`bubble` genérico como sustituto de ese vínculo. `neon_destacados` en población
se limita a los índices elegidos. No cambies VERSION por estos campos optativos.
Contrato, movimiento de partículas, malla tenue, nitidez y ancla de bocadillos:
`python pasos/prueba_stickman_editorial.py --real`, sin proveedores.

`realizacion.paleta` selecciona ember/arctic/sakura/retro para grafismos; los
colores compartidos de prompt/render viven en `motores/stickman/paletas.json`.
No uses esa paleta para sustituir los materiales ni la piel. `neon:0–1` en
objetos/gráficos es un halo alfa local detrás del original nítido (`neon.js`),
no `filter:blur` sobre el elemento o el fotograma completo. La capa aislada
protege los textos con contorno fino; el contorno habitual conserva su grosor.
Los planes históricos sin esos campos siguen el camino anterior; no cambies
VERSION para invalidar tandas al continuar. Regresión de cuatro paletas,
halo, determinismo y fidelidad interior: `prueba_stickman_editorial.py --real`.

Las entregas nuevas pasan por `utileria_stickman.validar_colores` después de la
puesta en escena: cada vector debe declarar todos los slots `$` usados por su
recurso. Fachadas, tejados y cunas heredaban el verde/azul del personaje y los
rasgos del bebé el contorno de marca. El índice expone rellenos/trazos por parte
para elegir materiales coherentes; los dibujos nuevos prefieren hex propios.
No impongas esa validación a la lectura de planes históricos ni cambies VERSION:
los clips publicados se corrigen al regenerar su animación. Contrato y píxeles:
`python pasos/prueba_stickman.py --real`, sin proveedores.

`stickman.consultar` distingue `ErrorValidacion` tras agotar sus tres entregas.
Durante una tanda, `ejecutar` deja esa escena pendiente y recorre las restantes;
al final lanza `ErrorEscenas` con IDs y motivos, sin completar assets con huecos.
Los recibos de clips terminados quedan en trabajo y se ven en la previa. El
reintento selectivo con `unidades` conserva las demás, incluidas las posteriores
al hueco. No captures excepciones genéricas en ese punto: cancelación, cuota y
fallos del servicio/motor deben detener el trabajo. Regresión offline en
`python pasos/prueba_stickman.py`.

La locomoción del rig se limita a tramos con desplazamiento x/y en
`motores/stickman/movimiento.js`; un `movimiento:caminar` global no puede seguir
sustituyendo las poses cuando el actor ya llegó. Las claves admiten movimiento
para caminar/esperar/correr por tramos. `transito:true` permite solo la excepción
horizontal (-.5–1.5), conservando tamaños y límites verticales; el encuadre seguro
excluye ese actor y su utilería anclada para no seguirlo fuera de pantalla.
El director pide general/conjunto y destino con cuerpo entero fuera. No cambies
VERSION para invalidar tandas terminadas: los clips se corrigen al regenerarlos.
Contrato, locomoción Node y píxeles Canvas: `prueba_stickman_editorial.py [--real]`.

`pasos/edicion_stickman.py` conversa sin generar y prepara retoques de una sola
escena desde su `.animacion.json` publicado, comprobando firma y narración del
recibo. El encargo completo vive en `assets.params.unidades[uid].edicion_stickman`;
solo «Aplicar cambios» lo guarda y ejecuta assets con esa unidad y `rehacer`.
El contenido anterior es la base, no una referencia para recrearla. Dos botones
excluyentes bajo «Editor del vídeo» eligen Claude (por defecto) o ChatGPT tanto
para conversar como para aplicar los cambios; la elección se comparte entre escenas y
el cliente envía respectivamente 0 o 100 en el contrato `porcentaje` existente.
Los chats viven en `stickman/chats` del proyecto y viajan también al duplicar.
Las imágenes opcionales del chat usan la subida normalizada de `imagenes_animacion`
y rutas relativas `medios_usuario/animaciones` en `mensajes[].imagen`. Valida su
existencia antes de lanzar; conversa y aplica con esas mismas referencias, resueltas
contra el proyecto actual (también tras duplicar/importar). No guardes rutas absolutas
en el encargo. El adaptador de texto Codex agrupa más de cinco imágenes conservando
su numeración, sin pedir una ilustración como respuesta.

`POST /escenas/{sid}/stickman/regenerar` valida el id contra la previsualización
actual y lanza assets con SOLO esa unidad y `rehacer:true`. La IA seleccionada
en la cabecera viaja como opción de ejecución `proveedor_stickman`, admitida por
`p6_assets` y transmitida al motor, sin cambiar el reparto global del vídeo. Quita antes su
`edicion_stickman` y `medio_usuario`: si queda el encargo de edición, rehacer
vuelve a retocar el plan previo en lugar de dirigirlo desde cero. Conserva la
descripción y los params de las demás escenas. La UI pone «Regenerando
animación…» en la previa y recarga el clip al terminar; Parar cancela el trabajo.

En entregas nuevas, `dividido` completa los `panel` omitidos solo si hay exactamente
dos protagonistas, cada uno permanece en una mitad distinta (base y claves x) y
ninguna etiqueta explícita contradice su posición. No mueve actores ni inventa
reparto. Las composiciones ambiguas siguen pasando por la corrección del proveedor,
con IDs, roles y paneles en el diagnóstico; para comparar objetos/magnitudes se pide
`grafico`, no dos actores obligatorios. No cambies VERSION por esta normalización:
continuar debe reutilizar los clips terminados. Regresión offline en ambas suites.

El encuadre seguro limita el zoom y recoloca la cámara contra los límites
de los objetos y articulaciones de toda la escena, con un margen del 4% y espacio
para encabezados/pies de pantalla. `detalle` multiplicaba por 2,6 sin comprobar
el contenido y cortaba fichas, diales y últimas filas. `encuadre.js` ajusta el
conjunto; `escena.js` cachea sus límites muestreando claves, poses y partes
vectoriales. Medio/primer plano conservan su recorte narrativo y 3D su cámara.
En S008, DIFÍCIL sí estaba animado, pero el zoom a la cara dejaba su caja fuera.
`planos_cortos.js` trata texto/etiqueta SIN ancla como rótulos de pantalla en
medio/primer_plano, conservando tamaño, claves y halo sin multiplicarlos por el
zoom. Reserva su posición final de lectura al lado de la cara, no la trayectoria
de entrada: la cámara no debe perseguir el texto ni convertir el plano en uno
de cuerpo entero. Las anclas y los demás objetos conservan sus coordenadas de
mundo; los planos sin rótulos conservan su cámara. No cambies VERSION ni planes
publicados al leerlos. Regresión de entrada, legibilidad, separación y tamaño
del rostro para texto/etiqueta en ambos encuadres: `prueba_stickman_editorial.py --real`.
Los tiempos se validan con `tiempos_stickman.tiempo`: tolera solo 1 microsegundo
y ajusta al límite exacto, sin relajar coordenadas ni excedentes reales. Un fin
3.803 era rechazado contra una duración 3.8029999999999973. Los errores incluyen
campo y valor. Pruebas offline y renders en ambas suites Stickman.
La corrección es de render/validación: no cambia VERSION para invalidar planes
ya pagados al continuar una tanda. Los clips existentes se renuevan al regenerarlos.

`stickman-5-editorial-2` da prioridad a colores, cantidades, posiciones y cambios
de escenario explícitos sobre estilo/continuidad. `realizacion.color_fiel:true`
omite la gradación cromática; no neutraliza los colores propios del decorado.
`poblacion` permite filas/columnas, color base, índices destacados desde cero y
tiempo/atenuación del destacado. `vestuario` es una copia local del diseño del
actor, nunca una mutación del reparto. Los objetos texto se pintan tras el acabado
con sus anclas/cámara; `texto.js` protege también los textos del kit con contorno
opuesto a la luminancia de la tinta. No vuelvas a aplicar un glow encima del
contorno: lo oscurece hasta hacerlo ilegible. Regresión visual y de píxeles en
`python pasos/prueba_stickman_editorial.py --real` (sin proveedores).

Desde `stickman-5-editorial-1`, las entregas nuevas incorporan `realizacion` y
pueden incluir `graficos`, `efectos_visuales` y `espacio3d`. El contrato por lista
blanca vive en `pasos/realizacion_stickman.py`; el renderer se divide en
`motores/stickman/{editorial,kit,decorados,acabado,espacio3d,fuentes,estilo}.js`.
No evalúes datos del modelo como código. Los planes sin estos campos mantienen
el camino histórico; no añadas realización ni params al abrir proyectos.

El adaptador expone ui2d, fx2d, rig2d y three-kit. `player.js` no se ejecuta:
el Estudio conserva montaje, reloj, voz y transiciones; su acabado se adapta en
`acabado.js`. `drawProp` se exporta del rig sin cambiar su dibujo, para reutilizarlo
también en familias personalizadas. Las fuentes originales viajan como data URI
en el bundle. Espera `STICKMAN_READY` antes de capturar. Dependencias fijadas:
`npm ci --prefix motores/stickman`, además de Remotion/esbuild. Los instaladores
y el actualizador deben preparar ambas carpetas.

`realizacion.escenario` tiene id/tipo/semilla estables; `escenarios_video` recupera
localizaciones de planes publicados también entre bloques, sin anidar contextos.
Los componentes tienen segundos locales y `desfase`/`duracion_total` opcionales
para continuar sus entradas y ciclos entre frases. `capa:fondo|frente|pantalla`
debe respetarse: los gráficos de pantalla no reciben cámara y se pintan tras la
gradación para conservar contraste. No pintes un blueprint de fondo después de
los actores. El desenfoque requiere respaldo opaco o aclara los bordes con el
blanco de la página. `primer_plano` usa el rostro grande del kit en Classic y
continúa el busto fuera de cuadro; `medio` y `detalle` reencuadran el sujeto/foco.

El validador distingue protagonistas, figurantes, comparación dividida y cierre.
No relajes todos los mínimos de tamaño por añadir figurantes. Las marcas de voz,
intervención y FPS participan en la firma: ahora alimentan también el reloj del
kit. Pruebas: `python pasos/prueba_stickman.py --real` y
`python pasos/prueba_stickman_editorial.py --real` (sin proveedores). La segunda
renderiza todas las familias gráficas/FX y el módulo 3D; inspeccionar sus PNG
además de comprobar los contratos.

La continuidad de animaciones se transmite explícitamente en `continuidad_bloque`:
direcciones visuales de todas sus frases y planes reales de la raíz y la anterior
(con sus claves finales y geometrías). Las frases vecinas narradas no bastan para
conservar telón, focos o actores no mencionados de nuevo. Recupera esos planes de
`<sid>.animacion.json` también al retomar o regenerar una escena suelta, comprobando
que su firma coincide con el recibo publicado. No encadenes sesiones de proveedor:
la continuidad debe cruzar Claude/Codex y no saltar a otro bloque. Los planes de
referencia entran en la firma del nuevo encargo, sin anidar contextos anteriores.

Desde `stickman-4`, el guion incluye `escenas_visuales` por frase literal, con
descripción y reparto propios. Conserva ese campo al normalizar y guardar los
bloques. Copiar `descripcion_visual` del bloque a cada frase reiniciaba la misma
secuencia a velocidades distintas. Los guiones históricos sin lista se leen como
antes; las entregas nuevas la validan antes de TTS. `personajes.aplicar_a_escenas`
elige por texto, para no anclar una descripción antigua a una voz editada.

Las descripciones editadas o regeneradas desde Guion viven en
`assets.params.unidades["escena:<sid>"].descripcion_escena`, con bloque, índice y
texto de ancla. `pasos/descripciones_escenas.py` las aplica al plan por frase;
no las guardes en params de guion ni reescribas su versión: eso invalidaría la
voz sin haber cambiado ninguna palabra. La regeneración es un trabajo aparte,
con validación de cobertura y comprobación de cambios antes de publicar cada tanda.
Regresión offline y navegador: `python pasos/prueba_descripciones_escenas.py --real`.

La dirección cromática de descripciones vive en `pasos/direccion_color.py` y
consume las mismas `PALETAS` del renderer. `escenas_visuales[].colores` es una
cadena de nombres separados por comas (hasta 500 caracteres), no un array.
La redacción Stickman exige ese campo solo en entregas nuevas; la lectura de
guiones históricos no inventa paletas ni persiste defaults. `estilo_visual` y
`_exigir_colores_escena` son contexto interno de redacción, no params nuevos.
Las correcciones de color se guardan con `descripcion_escena` en assets; compara
también colores al detectar cambios, importar y refrescar etiquetas. P6 transmite
colores aun sin generación de personajes y los incorpora al prompt (y su firma).
Exportar/importar conserva `colores` por frase; omitirlo en un JSON antiguo no
borra la dirección existente. Las etiquetas de cabecera son la unión sin
duplicados de los colores de las escenas del bloque. La actualización por tandas
renueva esas etiquetas sin reemplazar los campos de descripción ni su scroll.

La dirección visual necesita el tiempo de CADA frase: `descripciones_escenas.listar`
incluye `duracion_s` y `duracion_estimada`. Con audio, recalcula los cortes con
`p6_assets.planificar` y las marcas de la voz actual (lectura pura), no toma los
tiempos de un plan de assets anterior a una regrabación. Sin tiempos disponibles,
estima con `cadencia` y la velocidad/idioma de voz. Estos campos viajan en cada
tanda y en su contexto, no se persisten en `descripcion_escena`. El contrato
temporal compartido de `personajes.instruccion_tiempo_visual` limita acciones en
planos cortos y reparte el desarrollo en los largos; lo reciben guion Stickman,
regeneración visual y director de animación. No intentes medir complejidad por
número de caracteres ni aceleres una secuencia larga para encajarla en 2 s.

La regeneración visual puede incluir cientos de frases (209 en un caso real).
Genera y guarda tandas de hasta seis escenas con `cli_claude.escribiendo`;
esperar a la lista completa ocultaba todo el trabajo y perdía las terminadas
al cancelar. El callback de publicación compara contra la última foto guardada,
no contra la foto inicial. Valida también duplicados entre tandas de un bloque.
Envía bloque, índice, texto y presupuesto temporal por escena; las descripciones anteriores de
guiones históricos repiten el bloque entero y engordan el encargo sin aportar.
La barra cuenta escenas publicadas; el latido de espera no aumenta el porcentaje.
El seguimiento web relee las descripciones al avanzar y también al terminar con
error o cancelación, actualizando los campos sin reconstruir el guion ni su audio.

`assets.params.estilo.stickman` selecciona el motor de `pasos/stickman.py` sin
cambiar los ocho ids del grafo. Sus variantes y personajes son datos animables,
no imágenes de IA ni código arbitrario del modelo. El adaptador Canvas vive en
`motores/stickman/` y reutiliza el kit original `GrowKaz_Stickman/`; conservar esa
carpeta al distribuir. Claude diseña variantes/personajes; Claude y Codex se
reparten escenas según `bibliotecas.carga_claude`.

La ficha de escena se publica tras terminar MP4, póster y WAV de efectos. Sus
rutas son relativas a la versión; `aplicar_recursos` las resuelve en lectura.
No guardar esas rutas absolutas transitorias en el plan. Los sonidos se mezclan
por la pista Sonidos (`stickman:<índice>`), no dentro del clip, para no duplicar
el audio. Los personajes generados tienen un recibo junto al PNG inmutable;
conservarlo al copiar, duplicar o exportar. Stickman no admite fotos ni POV.
Prueba aislada y render real sin cuota: `python pasos/prueba_stickman.py --real`.

El contrato `stickman-2` añade utilería reconocible y anclas a mano/cabeza/pecho.
En los objetos `w,h` son dimensiones, nunca tamaño de fuente; `fuente` y `grosor`
son independientes. En los actores `x,y` sitúan los pies (rig de ~240 unidades
por escala). No vuelvas a dar al modelo solo primitivas sin estas convenciones:
producía calendarios irreconocibles, vínculos como barras y textos gigantes que
tapaban la acción. Las primeras claves tardías deben interpolar desde el valor
base, no anticipar la posición final. La puesta en escena de entregas nuevas
se valida antes de renderizar; no se aplica esa validación retroactivamente al
abrir proyectos. Contrato detallado en `motores/stickman/README.md`.

`stickman-3` permite crear utilería vectorial arbitraria y reutilizarla entre
vídeos. El catálogo de `pasos/utileria_stickman.py` va fuera del árbol del
programa (`ESTUDIO_UTILERIA_STICKMAN`, datos externos banco/proyectos o datos
del usuario). En despliegue, HOME está protegido: conserva la detección de los
datos externos, no lo fuerces a `~/.local/share`. Las definiciones son datos
numéricos, nunca JS ni SVG ejecutable. Se guardan por huella, se incluyen en
el plan de escena y en `pasos/assets/<versión>/utileria_stickman/`; no reemplaces
una referencia por huella por otra del mismo concepto. El catálogo completo
no entra en firmas: añadir un avión no debe invalidar escenas terminadas.

Lee primero [README.md](README.md): qué es, cómo se arranca y cómo está montado.
Y si vienes a retomar sin contexto, `docs/RETOMAR.md`: el estado al cerrar, qué
está desplegado y **los fallos que se encontraron con su causa** — el sitio
donde mirar antes de volver a tocar algo. **Es un fichero LOCAL**: está en el
`.gitignore` porque son notas internas (despliegues, cuentas), así que solo
existe en la máquina de quien lo desarrolla, no en el repositorio público.

Esto es lo otro — lo que no se deduce leyendo el código y cuesta dinero o una
tarde averiguar.

---

## LO PRIMERO: aquí se paga por generar

**Actualización: imágenes con ChatGPT / Codex.** Las instalaciones nuevas sin
clave usan la sesión de ChatGPT del CLI oficial, con la cuota de Codex, no cargos
de la API. Configuración y guía muestran Codex y OpenAI API Key en dos tarjetas:
su orden (guardado en `secretos/imagenes.json`) determina principal y
respaldo automático ante errores, falta de sesión o cuota. El adaptador es
`motores/imagen_openai/codex.py`; ver el setup en
`README.md` y `python pasos/prueba_codex_imagen.py`. No se pasan los tokens de
login a `/v1/images`; la API usa su propia clave y factura por uso, también como
respaldo. Un rechazo de contenido no pasa a otro proveedor. Las reglas de firmas, caché y
orden de generación de abajo siguen siendo necesarias: la cuota también se agota.

Una tanda de imágenes de un vídeo de cuatro minutos son ~126 imágenes y ~4,4 $.
No es un detalle de producto: es la razón de la mitad de las decisiones de este
repo, y de estas tres reglas.

**1. No escribas params «por defecto» al abrir una pantalla.** La firma de un
paso se calcula sobre los params GUARDADOS. Escribir un valor que ese proyecto
nunca tuvo mueve la firma, deja obsoleto el paso y todo lo que cuelga, y la
pantalla ofrece regenerar el vídeo entero sin que nadie haya pedido nada. Las
pantallas editan una copia y solo guardan cuando alguien toca algo.

**2. Las tandas de imágenes se lanzan DE UNA EN UNA.** Dos a la vez tardan el
doble por imagen y pierden el registro del gasto.

**3. Un guardián calibrado sobre un fallo aprende a dar por bueno ese fallo.**
`p6_assets._planos_repetidos` tumba la tanda si dos planos acaban con la MISMA
imagen. Tiene dos excepciones —la cartela y la continuación de un plano largo—
y las dos están explicadas en su docstring. Si añades una tercera, comprueba
antes que lo que la justifica no es un bug.

---

## El grafo, y por qué no se toca

```
ingesta → brief → guion → voz → revision_audio → assets → callouts → render
```

Los ids **no se renombran** y **no se quita ninguno**, ni el que parezca que no
hace nada. `brief` es una cuenta determinista de dos segundos que no llama a
ningún modelo, y aun así sigue en el grafo: su firma encadena la del guion, así
que sacarlo dejaría obsoleto el guion de todos los proyectos guardados, en
cascada hasta el render. Mover su PANTALLA no cuesta nada; mover el PASO es una
migración.

### Lo que hay que saber de `nucleo/estado.py`

- **El manifiesto de cada versión vive fuera de `estado.json`**, en
  `pasos/<paso>/_versiones/v<N>.json`. Antes iba dentro y crecía como versiones
  × unidades: un vídeo de 300 planos llegó a 320 MB de `estado.json` y 9 s por
  petición. `Estado.manifiesto_version` **lanza** si el fichero falta o trae
  menos unidades de las que dice la versión: devolver `{}` vaciaría el mapa vivo
  y la pantalla ofrecería regenerar el vídeo entero. Se sigue leyendo el formato
  antiguo, y eso es permanente: un proyecto que llegue de fuera funciona sin
  migrar.
- **`completar()` escribe el manifiesto ANTES de tocar `datos`.** No es estilo:
  al revés, un fallo dejaría en disco `activa: N` con `versiones` sin la N, y
  «Revertir» enseñaría las imágenes de la versión anterior como si fueran las
  recién pagadas.
- **La carpeta de versiones va FUERA de `v<N>/`**: `sembrar_trabajo` copia la
  carpeta de la versión activa a `trabajo/` y `_recoger_trabajo` la vuelca en la
  SIGUIENTE, así que un manifiesto dentro de `v21` acabaría dentro de `v22` con
  pinta de correcto.
- **No caches el manifiesto en el documento.** `_guardar` filtra las claves con
  guion bajo SOLO en la raíz, así que una cache anidada se escribiría dentro de
  `estado.json` y el fichero recuperaría sus 320 MB en silencio.

---

## Copiar un proyecto o un estilo a otra máquina

**No basta con copiar la carpeta.** Un proyecto guarda rutas absolutas en tres
sitios: las salidas de cada unidad, los manifiestos de cada versión y las
referencias de estilo — y ese último entra en la firma del paso. Copiar y ya
deja `assets`, `callouts` y `render` en obsoleto: la pantalla ofrece regenerar
todos los planos ya pagados.

Hay que **mudar las rutas y volver a sellar las firmas**, y el sellado tiene dos
trampas:

1. **No se re-sella todo, solo lo que la mudanza movió.** `guion` guarda a
   propósito una `firma` que no cuadra con la calculada (cuando alguien corrige
   el guion a mano manda `firma_propia` y la otra se queda atrás). «Arreglarla»
   mueve el sello de salida del guion, que entra en la firma de la voz, y la
   cascada deja obsoleto todo lo de abajo. La regla es comparar contra la firma
   **calculada ANTES de mudar**.
2. **Los manifiestos del histórico también llevan firmas de unidad.** Sin
   re-sellarlos el estado vivo queda perfecto y cada «Revertir» enseña todas las
   unidades en obsoleto.

Y la comprobación es la mitad del trabajo: hay que contar **cuántos de los
ficheros que el estado dice haber producido están de verdad en disco**, en las
dos máquinas, y comparar. Una mudanza a medias no da ningún error al abrir el
proyecto; se ve al pedir una miniatura.

Al validar un paquete de vídeo, no compruebes literalmente todas las rutas de
`salidas`: voz conserva `pista=.../trabajo/narracion.wav` y las escenas sus
referencias `trabajo/_refs`, aunque `completar()` ya haya recogido esos ficheros
en `v<N>/`. Hay que resolverlos en **la versión que se está comprobando**,
también para los manifiestos históricos, sin reescribir los metadatos ni las
firmas. `pasos/paquete_video.py` comprueba además `archivo` y `png` relativos;
un audio definitivo o una imagen que de verdad falta sigue siendo un error.
También viajan rutas **relativas** con barras de Windows, por ejemplo
`assets\reparto\ali_baba.png`. Normalízalas por contrato de fichero en estado,
manifiestos y fichas de `trabajo/`, no solo al comprobar que existen: si quedan
sin adaptar, retomar la tanda o revertir vuelve a perderlas. Hazlo después de
fotografiar las firmas originales y antes del sellado selectivo, sin sustituir
barras en narraciones ni prompts. Un proyecto interrumpido conserva las imágenes
pagadas en `trabajo/` y las unidades pendientes siguen pendientes.

---

## La interfaz: una pantalla, y sin dependencias

`web/app.js` son ~10.000 líneas de JavaScript a pelo — sin framework y sin
`npm install`. Se sirve con `?v=<sello>` calculado del propio fichero, así que
**no hay ningún número que subir a mano** al cambiarlo.

**HAY UNA SOLA PANTALLA.** Hubo dos modos (uno guiado y uno desglosado en
pestañas) y aquí solo está el guiado. Si te encuentras algo que parece del otro
—una tabla de pestañas, un panel por paso— comprueba antes si lo alcanza
alguien:

```bash
python herramientas/alcanzables_js.py            # qué está vivo y qué no
python herramientas/alcanzables_js.py --quien X  # quién nombra a X
python herramientas/alcanzables_js.py --borrar   # una vuelta, y vuelve a correrla
```

**Dos funciones con el mismo nombre es un fallo silencioso.** En JavaScript la
segunda se lleva la primera por delante, sin un solo error, y la de arriba deja
de ejecutarse leyéndose como si funcionara. Pasó: el coste que se enseña antes
de generar compartía nombre con el medidor del vídeo ya empezado, y el hueco de
al lado del botón llevaba vacío desde el día que se escribió. Lo canta
`sin_llamar_js.py`.

Y por la CSP del proxy, **no se pueden usar atributos `style=""` en el HTML**:
el navegador los bloquea. Todo estilo va en `estilo.css`.

**El login vive DELANTE, y no es de aquí.** La interfaz le pregunta quién ha
entrado (`/api/me`) y le pide salir (`/api/logout`) a un servicio aparte; en
local esas rutas no existen, la pastilla de la cuenta se queda oculta y no pasa
nada. Lo único a tener en cuenta si se despliega detrás de él: **al salir se va
a `${BASE}/login`**, no a donde diga la respuesta. Ese servicio contesta
`/login` a secas porque atiende a dos versiones del estudio y no sabe por cuál
se le está llamando; quien sí lo sabe es esta página. Con la respuesta a pelo,
salir desde `/v2/` te dejaba en el login de la otra versión.

---

## El asistente y la guía de inicio

La burbuja de abajo a la derecha es `pasos/asistente.py` más las rutas
`/api/asistente/*` de `app.py`; la guía de la primera vez son las tarjetas de
`abrirInicio` en `web/app.js`. Lo que no se ve leyendo el código:

- **El asistente corre el CLI con `Read`, `Grep` y `Glob` sobre la carpeta del
  Estudio, y con las HERRAMIENTAS DEL ESTUDIO** (`pasos/mcp_estudio.py`, un
  servidor MCP mínimo que el CLI carga con `--mcp-config` y que van
  pre-autorizadas como `mcp__estudio__*`): probar las claves de verdad, ver el
  estado, los trabajos, la bitácora, cancelar un trabajo. Cada herramienta
  habla con la API del Estudio por HTTP (`ESTUDIO_API`, que pone `app.py` al
  arrancar), nunca importando código: lo que hace es lo que haría la
  pantalla. Sin Bash, sin escribir, sin internet. `secretos/` queda
  fuera por REGLA DE PERMISO del CLI (`Read(./secretos/**)`, en
  `asistente.vetos_de_lectura`), y está medido: pedirle que lo abra devuelve
  «File is in a directory that is denied by your permission settings». El
  prompt de sistema también se lo dice, pero la regla es la que manda. Si
  alguna vez las claves se guardan en otra carpeta DENTRO del repo, se añade a
  `CARPETAS_VETADAS` antes que nada.
- **Contesta con sonnet/medium a propósito**, no con el defecto del canal
  (opus/xhigh): un chat pide segundos. No pasa por `cli_claude.por_defecto_de`,
  que subiría al defecto del canal. Se cambia con `ESTUDIO_ASISTENTE_MODELO` y
  `ESTUDIO_ASISTENTE_ESFUERZO`.
- **Una charla es una sesión del CLI** (`--resume` con el `session_id` del
  sobre). Vive en memoria: recargar la página la reencuentra, reiniciar el
  servicio la pierde y la pantalla abre otra sin ruido. Si reanudar falla se
  vuelve a empezar con los últimos turnos pegados; un cupo agotado o un plazo
  vencido NO se reintentan.
- **La respuesta se sigue preguntando, no con una petición larga**: detrás del
  proxy una petición de un minuto se corta a los sesenta segundos. Un turno por
  charla; el segundo a la vez es un 409.
- **`_asistente_listo` tiene que decir lo mismo que `cli_claude.cuentas()`**:
  sin ninguna cuenta con `entrada`, el motor habla con la sesión por defecto
  del CLI, y el asistente también. Una cuenta añadida y nunca logueada no
  cuenta en ninguno de los dos sitios.
- **«Con sesión» no es «funciona».** `pasos/salud_cli.py` apunta cómo
  respondió cada cuenta la última vez (ok, cupo, sesión, tiempo, error) y lo
  escribe `cli_claude._una_pasada`, el único sitio por el que pasa toda
  llamada. La pantalla lo enseña al lado de la sesión (burbuja, Configuración,
  guía) y «Probar» le habla con haiku y una palabra. Un estado malo se queda
  hasta que una llamada vuelve a salir bien: nadie adivina cuándo se renueva
  un cupo, el mensaje del CLI ya trae la fecha. Toda suite que doble el CLI
  redirige `ESTUDIO_SECRETOS`, o la salud de sus dobles acaba en el almacén.
- **Las claves se prueban contra su servicio** (`pasos/comprobar_claves.py`)
  con llamadas que no cuestan dinero. Lo único que no puede saber es si OpenAI
  tiene saldo, y lo dice. FreeSound va con el token de la columna «Client
  secret/Api key», no con el Client id.
- **En la guía hay UNA cuenta de Claude** y el acceso arranca solo al abrir la
  tarjeta; el código se envía al pegarlo. La cadena de cuentas de respaldo
  sigue en Configuración, que es donde se necesita.
- **La foto del estado la hace `app.py`** (`_foto_para_asistente`) y se puede
  mirar en `GET /api/asistente/foto`. No lleva ninguna clave; lo comprueba
  `prueba_api`.
- **La marca de la guía (`onboarding_visto`) es un ajuste del servidor.** Toda
  suite que la toque redirige `ESTUDIO_AJUSTES`, o la marca acaba en el
  `ajustes.json` de verdad.
- **Configuración y la guía comparten estado** (`estadoConfig()`): quien
  guarde una clave llama a `repintarClaves()`, no a `pintarConfig()`, y las dos
  pantallas se enteran.
- **En `app.js`, un acento grave dentro de una expresión regular** parte por la
  mitad los tokenizadores de `herramientas/` (se creen que empieza una
  plantilla) y dan por muerto todo lo que venga detrás. Se escribe `\x60`.

---

## Lo que NO hay, y no es un olvido

Este producto sale de uno más grande, y estas piezas se quitaron a propósito.
Si echas una en falta, esto es por qué no está:

| Qué | Por qué no está |
|---|---|
| El modo editor, con sus pestañas por paso | una sola pantalla; lo demás era el mismo motor visto en detalle |
| Vídeos de YouTube como material | el material es lo que se escribe, y vive en `ingesta.texto` |
| El documentalista (buscar en internet) | con una sola vía para el material no hay nada que decidir |
| Los personajes fijos del canal | el **reparto** de cada vídeo sí está: es lo que sostiene la consistencia visual |
| Las menciones ilustradas de un producto | con ellas se fue todo lo que llevaba el nombre de un patrocinador |
| El dictado por voz | pedía un modelo aparte y su propio entorno |
| El bloc de enlaces, la bitácora, el monitor | notas y telemetría que no hacen un vídeo |

**Y no vuelvas a meter ninguna sin mirar `pasos/recetas.py`:** una tarea que no
está en la receta no corre, y una pantalla que la ofrece llama a una ruta que ya
no existe. Es exactamente lo que había que arreglar aquí — la interfaz seguía
pintando el micrófono y el mapa después de que el motor dejara de servirlos.

**Y lo que se quitó deja piezas colgando que ninguna prueba ve.** En octubre de
2026 una auditoría encontró que el catálogo visual seguía pidiendo `{fijos}` en
su plantilla (los personajes fijos ya no existían): `KeyError` en TODO vídeo
nuevo, y nadie lo vio porque crear un estilo fallaba antes. Si quitas algo,
busca su nombre en las plantillas de texto (`.format`), no solo en el código.

---

## Lo que se arregló en octubre de 2026 y no se deduce del código

Las incidencias de GitHub (crear un estilo fallaba siempre) destaparon una
tanda de fallos. Lo que hay que saber para no deshacerlo:

- **Las láminas de un estilo se dibujan con las imágenes del canal delante**
  (`moodboard.dibujar_desde_guia`, montadas en una hoja por
  `_montar_aportadas`). Antes iban sin adjuntos «a propósito», el motor de
  imagen lo rechazaba y crear un estilo fallaba siempre. El motor ya sabe
  dibujar sin adjuntos (`/v1/images/generations`), pero un estilo siempre tiene
  imágenes: que no vuelvan a quedarse fuera.
- **La carpeta de un estilo (`banco/presets/<id>`) solo crece.** Cada guardado
  la rehacía con otro prefijo (`00_cara.png` → `00_00_cara.png`) y borraba la
  anterior, y los vídeos hechos con él se quedaban sin referencias. Y cada vídeo
  NUEVO copia las láminas a su propia carpeta (`estilo/referencias`): lo que le
  pase al estilo después ya no le toca.
- **Las reglas de dibujo se llaman `motores/reglas/reglas_casa.json`**, y el
  nombre es a propósito: el `asvs actualizar` de las instalaciones anteriores
  excluye `reglas.json`, así que con el nombre viejo ninguna regla nueva llegaría
  nunca a esos estudios. No lo vuelvas a llamar `reglas.json`.
- **Lo que el motor de imagen aprende del ritmo de cada cuenta** va en
  `<ESTUDIO_SECRETOS>/limites_aprendidos.json` (por la huella de la clave), no
  junto al motor: `asvs actualizar` borra lo que haya en el árbol del programa.
- **La música y los efectos son opcionales de verdad**: sin su clave, sus tareas
  cuentan como hechas y el MP4 sale sin ellos (`app._falta_clave_de_sonido`).
- **«Regenerar Vídeo» no redibuja nunca**: en la tanda `render`, la pestaña de
  imágenes va siempre en `pendientes` (`app._modo_de_la_pestana`).
- **Una cola de «regenerar con nota» por vídeo, y una tanda de cola a la vez**
  (`COLAS`, `otraColaEnMarcha` en `web/app.js`); y **un solo montaje a la vez**
  entre vídeos (`app._exigir_sin_otro_montaje`, 409).
- **Los lotes del render caben en la memoria TOTAL y en la LIBRE**
  (`p8_render._tope_por_memoria`, 2,4 GB por lote). Si en tu ordenador monta
  con menos procesos de los que esperas, es eso: con la total a secas, una
  máquina de 30 GB con 12 libres pedía once lotes y Edge dejaba de arrancar a
  media tanda («The paging file is too small»).
- **El plan de un estilo mide la guía con las imágenes del encargo**, no con
  las 24 que caben (`presets_light.tareas_de`): con el tope, retomar un estilo
  de una imagen prometía tres cuartos de hora.
- **`docs/RETOMAR.md` ya no está en el repositorio**: son notas internas y viven
  solo en la máquina de quien desarrolla (ver arriba).

---

## Las medidas que hay, para no volver a medirlas

**El render** (`pasos/medir_render.py --reparto`), en 8 vCPU:

| Procesos | fotogramas/s |
|---|---|
| 1 | 1,98 |
| 4 (lo que elige `cpu_count()//2`) | 6,75 |
| **8 (`ESTUDIO_LOTES=8`)** | **10,40** |
| 16 | 10,85 — ya no escala |

La regla automática pide 4 y deja media máquina parada: en un servidor de ocho
hilos, `ESTUDIO_LOTES=8`.

**Lo que cuesta una imagen** no es el precio de OpenAI: es la factura. A cada
imagen se le adjuntan sus referencias de estilo, reparto y continuidad, y esas
se pagan como tokens de entrada — el 87 % del gasto en calidad baja. Medido
sobre 1.439 imágenes (mediana 5.114 tokens de entrada por imagen):

| Calidad | Imagen | Referencias | Total | Real | Aparente |
|---|---|---|---|---|---|
| low | 0,006 $ | 0,041 $ | **0,047 $** | — | — |
| medium | 0,041 $ | 0,041 $ | **0,082 $** | **1,7×** | 6,8× |
| high | 0,165 $ | 0,041 $ | **0,206 $** | **4,4×** | 27,5× |

El número de tokens vive en `pasos/ajustes.py:TOKENS_ENTRADA_POR_IMAGEN`. Si
cambia cuántas referencias se adjuntan, se vuelve a medir con el campo
`tokens.entrada` de las operaciones `imagen` de `coste_global.jsonl`.

**La calidad se elige en Configuración y es el punto de partida de los vídeos
NUEVOS**: se escribe en el param `calidad` de `assets` al crear el proyecto y no
se lee al generar. A propósito — `calidad` entra en la firma de cada imagen, así
que un defecto retroactivo dejaría obsoletas las imágenes de todos los proyectos
que nunca la fijaron, y regenerarlas se paga.

---

## Motion animation (`pasos/animaciones.py`)

### Taller Remotion adicional (`pasos/remotion.py`, `motores/remotion/`)

La entrada visible ahora es **Animaciones con IA**. El panel derecho muestra
únicamente el chat a toda altura, sin pestañas técnicas ni cabecera de plantilla;
las props de aplicación se configuran en su popup. `pasos/animaciones_ia.py`
normaliza el prompt de sistema a una sola línea antes de llamar al CLI: los
saltos en `--append-system-prompt` se rechazan localmente por compatibilidad con
`claude.cmd`, y pueden marcar la salud de la cuenta como «Falla» sin haber
contactado con Claude. No atribuyas ese error al login. La regresión construye
la orden con el adaptador real, sin ejecutar el proveedor.
`pasos/animaciones_ia.py`
coordina tres contextos separados: escenas, creación reutilizable y edición por
referencia/categoría. Los chats y el historial global se guardan bajo
`remotion.biblioteca(...)/_ia`, fuera de cada proyecto; las imágenes en props se
congelan como data URI antes de publicar. No quites esa congelación: borrar el
proyecto original no debe romper el historial. Cada generación compila y ejecuta
`renderStill` para comprobar el componente y generar su miniatura. Las ediciones
publican otra versión al confirmar, sin sobrescribir ni retirar la anterior.
Los cambios manuales de Código/Props se revalidan antes de confirmar.
ChatGPT reutiliza `codex.texto` con adjuntos y cancelación cooperativa; Claude
coordina conceptos incluso al asignar el 100% a ChatGPT. El slider permanece
visible en los tres modos y se aplica también a crear y editar plantillas. El
reparto se redondea al número de tareas (una al crear/editar una plantilla) y no
implica respaldo automático de proveedor.
El envío junto al campo de texto conversa sin generar; **Empezar a generar**
inicia el trabajo. `necesita_aclaracion` detiene la generación si faltan decisiones.
`eventos` conserva respuestas y actividad real, con ids para evitar duplicados al
consultar `/remotion/chat/{sesion}/actividad`. Los comandos mostrados proceden
del arranque real de Node en `remotion._correr`, sin volcar el pedido ni credenciales.
El editor distingue la escena visual (`esActual`) de la del panel fijado
(`esPanelActual`). Reproducir y desplazar el cabezal solo posicionan la vista
previa: no llaman a `seleccionarPestaña` ni reconstruyen el catálogo o el chat.
Los atributos `data-panel-activo` y `data-visual-activo` permiten mostrar partes
de dos editores sin mover sus nodos ni duplicar sus controles. No bases la
visibilidad del panel en `PREVIA.i`. Las tarjetas de ejemplo no usan la imagen
de la escena como fondo. Insertar un bloque Remotion libre sigue usando el cursor
global, aunque la escena del inspector permanezca fijada.
Regresión aislada: `python pasos/prueba_animaciones_ia.py`; `--real` comprueba
los tres modos en navegador, miniaturas y aplicación real sin llamadas a IA.

El taller es opcional y no modifica `animaciones.CATALOGO` ni el grafo. React vive
en un Player dentro de un iframe sandbox, con una CSP propia que admite sus estilos.
El servicio Python coordina procesos Node >=22 por JSON, con progreso, timeout y
cancelación de su grupo de procesos. Instalar con `npm ci --prefix motores/remotion`.
Los componentes son un solo TSX con export default e imports de React/Remotion.

La biblioteca global vive en `ESTUDIO_REMOTION` o junto a proyectos, nunca como
datos dentro de motores. Aplicar guarda una instantánea por hash en el proyecto,
`remotion/plantillas/<hash>.json`; params de `render.unidades[escena:<sid>].remotion`
solo guardan ancla, referencia inmutable, props e intervalo. No escribir params al
abrir. Compilar/preparar son trabajos sin paso del grafo; los GET solo leen.
El código y los props entran en la huella de caché junto a versión del motor,
resolución, FPS y duración. Cambiar dependencias o el motor requiere cambiar VERSION.

P8 prepara PNG RGBA y los superpone al reloj de cada escena antes del avatar y las
transiciones, también para el primer fotograma del destino en enlaces de salida.
Sin bloques, conserva el camino anterior de captura. La carpeta `remotion` viaja
al duplicar/exportar. `pasos/prueba_remotion.py --real` comprueba el taller, la
compilación, el canal alpha y un clip codificado; sin flag verifica contratos.

Los bloques Remotion admiten `modo: superponer|sustituir`; ausencia mantiene la
superposición histórica. En el formato anterior, una sustitución es única y cubre toda la escena, mientras
la instantánea de plantilla conserva resolución, FPS y duración propios del MP4.
El motor usa `renderMedia` con H.264 sin audio y publica la caché solo al terminar.
P8 lo decodifica como fondo con ventana completa, antes de las capas independientes,
sin generar parallax ni requerir el hyperframe original. Nunca pases ese bloque a
`superponer`: la previa y p8 separan clips y capas explícitamente. Eliminarlo restaura
el medio anterior. Props puede referenciar imágenes con `proyecto://ruta`: se validan
dentro del proyecto y se resuelven como data URI para Player/render; no persistas
esas URI en params ni instantáneas. Los contenidos entran en la huella de caché.

Los nuevos bloques incluyen `origen` (segundo absoluto de la escena que conserva
su borrador), con `inicio`/`fin` relativos a ese origen, que admiten valores negativos
y sobrepasar el corte. Su intervalo absoluto es libre dentro del vídeo (0,1–120 s).
`remotion.bloques_de` proyecta todos los bloques libres sobre cada escena sin
recortar su intervalo: el inicio negativo conserva el reloj y la misma caché de
fotogramas. `propios=True` devuelve solo los editables de ese controlador.
Guardar recalcula `remotion_timeline` en las unidades atravesadas, también al
mover o eliminar, para invalidar sus clips sin tocar voz/assets/callouts. Los
bloques libres de sustitución usan fotogramas con fondo negro durante su intervalo;
los antiguos sin `origen` siguen usando el MP4 de escena. El editor comparte las
capas preparadas entre controladores y dibuja bloques continuos entre columnas.
`capasActualesRemotion` reutiliza cada recurso por plantilla, props, modo y duración,
sin incluir inicio/fin/origen en su identidad: mover un bloque retima su capa sin
invalidar los PNG ni ocultar otros bloques. La ficha local guardada conserva esas
capas retimadas. El taller empieza contraído y su botón controla un estado del editor
global; seleccionar plantillas o bloques no cambia ese estado.
No hay panel de intervalos/eliminación de Remotion: los extremos del bloque
retiman y preparan automáticamente la muestra al soltar. La papelera está en la
cabecera derecha del timeline y comprueba coordenadas del puntero capturado;
solo `pointerup` sobre ella elimina, nunca `pointercancel`/`lostpointercapture`.
Cancelar restaura el borrador previo y la eliminación se puede deshacer. Biblioteca
y taller comparten el texto de progreso y errores; Insertar lo muestra con el taller
contraído. `remotion_previa` conserva firma y capas preparadas en la caché local,
también tras redimensionar sin guardar.
El menú ⋯ de cada tarjeta elimina mediante `DELETE /api/remotion/plantillas/{referencia}`.
Las propias se retiran de la biblioteca global; los ejemplos incluidos se ocultan
persistentemente en `plantillas_remotion/_config/eliminadas.json` (respetando
`ESTUDIO_REMOTION`). Nunca borres las instantáneas de `proyecto/remotion/plantillas`:
los vídeos existentes dependen de ellas. La notificación del navegador retira la
tarjeta también de los controladores de otras escenas ya cargadas. La biblioteca
vacía permite crear una plantilla nueva sin reponer los ejemplos eliminados.
El menú incluye `menuitemradio` para Superponer Animación/Sustituir contenido:
ausencia de modo selecciona Superponer. `cambiarModoRemotion` sincroniza la tarjeta
y el taller e invalida la compilación anterior antes de insertar. La selección
solo modifica el borrador de la plantilla; el modo efectivo viaja en la instantánea
y en el bloque al insertarlo, sin cambiar los bloques existentes al abrir el menú.

Los bloques admiten `posicion: {x, y}` como desplazamiento normalizado al lienzo
(-1 a 1; ausencia = centrado). No forma parte de la identidad del recurso PNG:
`capasActualesRemotion` aplica el desplazamiento actual sin preparar fotogramas
nuevos. El previsualizador captura el puntero desde cualquier pestaña y bloquea
el arrastre nativo de imágenes (`draggable="false"` como cadena: `h` omite el
booleano falso). El alpha de una miniatura de cada fotograma delimita el conjunto:
el recuadro de agarre incluye los huecos interiores, 10 px de margen y un mínimo
de 44 px por eje. El mismo cálculo dibuja el recuadro y resuelve el hitbox, de
delante hacia atrás; al reproducir se ocultan las guías y un ResizeObserver las
adapta al tamaño del previsualizador. El arrastre edita su controlador de origen, también al atravesar
escenas. Un gesto añade un recuerdo; cancelar lo restaura. Previa y
`remotion.superponer` desplazan el conjunto conservando escala y reloj; Guardar
persiste la posición y las dependencias del timeline invalidan el montaje afectado.

La sección incluye también las diez cartelas de `cartelas.PLANTILLAS`, con GIF
`anim_cartela-<id>.gif`. Su selección independiente es
`montaje.plantillas_cartela` en estilos y `callouts.params.plantillas_cartela`
en vídeos: ausencia conserva el comportamiento histórico; `[]` apaga todas.
Los formularios nuevos parten de `[]`; abrir un vídeo/estilo antiguo no lo escribe.
`cartelas.proponer` respeta la lista vacía sin llamar a IA, y
`escena_para_montaje` filtra las capas en p7 sin mutar assets, narración ni tiempos.
Cambiar estas tarjetas solo invalida callouts/render. Volver a activar un tipo
en un vídeo existente recupera sus cartelas ya planificadas. Las ocho animaciones
del guion y sus firmas conservan su contrato independiente.
El popup de escena usa `animaciones.CATALOGO_EDITOR`/`CAMPOS_EDITOR`: las ocho
del guion más diez ids `cartela-<plantilla>`. No las añadas a `CATALOGO`, que
reparte huecos antes de escribir el guion. Las listas viajan como texto con
saltos de línea y se validan sin truncar (2–4 entradas). Sus ediciones usan el
mismo param de unidad de render; `svg_de` adapta `cartelas.svg_capa` al cuadro.
Al sustituir una cartela automática, la API guarda en esa unidad de callouts
`omitir_cartela`, anclado a la narración, para regenerar solo su capa y evitar
duplicarla. La previa reconoce las cartelas automáticas y las ediciones manuales
mandan sobre ellas, incluido `sin-animacion`. Las cartelas manuales no llevan
subtítulos debajo: p8 los suprime solo en esa escena.

Animaciones SVG/SMIL tomadas de una guía de motion graphics, que se pintan ENCIMA
de un plano (como el subtítulo, fuera del zoom) y se mueven con `setCurrentTime`:
mismo reloj en previa y en render. Ocho, cada una con su señal en lo que se dice:

| Señal | Animaciones |
|---|---|
| `cifra` (cantidad o %) | `infografia-cifra` |
| `fecha` (año o «5 de mayo») | `editorial-fecha` |
| `contraste` («mientras que», «frente a»…) | `comparacion-tarjetas` |
| `termino` (nombre propio que no abre frase) | `ficha-ui`, `ficha-cristal`, `etiqueta-escrita`, `collage-titulo` |
| `frase` (3 a 9 palabras) | `tipografia-cinetica` |

El parallax real se configura por separado en `render.parallax` y en
`montaje.parallax` de los estilos. `pasos/parallax.py` selecciona solo imágenes
estáticas de forma reproducible. `movimientos` permite varios tipos y los reparte
equilibradamente entre las imágenes animadas, con orden estable por semilla;
se sigue leyendo el antiguo `movimiento` único sin mutar params al abrir.
La interfaz usa `bloqueLight` y casillas `efecto-encargo`, igual que voz/subtítulos.
P8 usa `motores/parallax_depthflow.py` antes de
componer sus capas, por el mismo camino de fotogramas que los clips propios.
`pasos/clips_parallax.py` comparte los clips entre previa y p8 en `parallax/` del
proyecto. GET de previsualización solo lee: publica `clip` si existe y `parallax`
con su estado/firma. El navegador solicita POST `previsualizacion/parallax` para
preparar los pendientes en un trabajo sin paso del grafo (cancelable y deduplicado).
Espera a las otras generaciones, actualiza los clips sin mover escena ni borradores
y muestra los errores sin reintentarlos en bucle. No usar el hyperframe ampliado
como fuente si existe el PNG original: previa y render deben reutilizar el mismo
clip. El motor serializa sus procesos para no competir por la GPU ni el parcial.
El popup «Efecto Parallax» guarda en `render.params.unidades["escena:<sid>"].parallax`
solo al pulsar Guardar, con `ancla` al texto normalizado, `activo`, `movimiento` e
`intensidad`. Ausencia hereda; `activo:false` suprime explícitamente el efecto global.
Las ediciones se aplican después del reparto para no cambiar los movimientos de
las vecinas. No sustituir otros params de la unidad (por ejemplo `animacion`).
GET/PUT de `escenas/<sid>/parallax` validan contra el plan visible. Una edición
cambia la firma solo de esa unidad de render; voz/assets/callouts se conservan.
Los trabajos de previa llevan la firma de los ajustes globales y por escena en
su nombre; si se editan, el anterior se cancela y el navegador espera su cierre
antes de solicitar los clips nuevos, sin confundirlo con la tanda nueva.
El motor opcional DepthFlow 1.0.1 vive en `.depthflow` (o en
`ESTUDIO_DEPTHFLOW_PYTHON`), separado del servicio. ShaderFlow 0.13 necesita cerrar
su `WATCHDOG` al terminar: sin ello Windows espera indefinidamente aunque ya haya
escrito el MP4. La caché incluye contenido, opciones y tiempos.
Prueba offline y real: `pasos/prueba_parallax.py [--real]`. No escribir este param
al abrir vídeos/estilos antiguos. Lo que no se deduce del código de animaciones:

**Dónde se eligen y cómo llegan al vídeo**
- **Se eligen en el estilo** (`montaje.animaciones`, en `presets_canal`, con herencia
  a los vídeos nuevos) **y se guardan como param del GUION** (`guion.animaciones`), no
  del render: el texto tiene que decir lo que cada una necesita. Cambiar la
  selección deja obsoleto el guion y todo lo que cuelga (voz, imágenes pagadas), y
  la pantalla lo dice. No escribas `[]` por defecto al abrir una pantalla (regla 1);
  `animacionesDelEncargo` solo toca `e.animaciones` al pulsar una tarjeta.
- **El plan va ANTES del guion**: `plan_de_huecos` reparte las elegidas por el
  vídeo (cada una, al menos una vez; entre el 2.º bloque y el penúltimo),
  `bloque_para_guion` lo cuenta en la instrucción de `p3_guion._instruccion` (el
  redactor deja en cada hueco la frase que la animación necesita, sin inventar
  datos, y marca el bloque con `"animacion": id`), y `etiquetar_bloques` comprueba
  cada marca contra el texto y RESCATA las que no escribió (aunque quede pegada a
  otra: que salgan todas importa más que el aire). Lo que no cabe se avisa por su
  nombre. Todo queda en `guion.json` (`guion[].animacion`, `animaciones`) y de ahí lo
  leen render y previa (`etiquetas_de`, `pedidas_de`).
- **El texto visible lo elige Claude en el MISMO turno del guion**: por cada bloque
  marcado propone `animacion_texto`, un fragmento literal de lo narrado (un nombre
  completo como «Universidad de Ginebra», no su primera palabra). Se valida
  contra el texto final, se guarda en `guion.json` y se localiza en las marcas de
  voz de la escena; render y previa leen `textos_de`. Si no existe (guiones de
  antes, rescates o seleccion invalida) se mantienen las reglas deterministas,
  que ahora reconocen nombres con «de»/«del». No se llama al CLI en el render.
- **Render y previa reparten con `repartir(etiquetas=...)`**: cada bloque marcado
  lleva su animación en el plano de ese bloque que dice lo que necesita, y las que
  falten se buscan por la señal en cualquier plano libre. Un vídeo de ANTES del
  plan (sin etiquetas) sigue repartiéndose mirando la narración, con
  `render.animaciones` y aire entre dos animadas; sin nada elegido no se pinta
  nada y el MP4 sale byte a byte igual.
- **`cobertura` dice cuáles no han salido** y la cabecera de Imágenes lo enseña
  («✦ 5 de 6 animaciones · faltan: …»).

**Las que enseñan dos elementos** (`collage-titulo`, `comparacion-tarjetas`,
`requiere_imagenes`): usan DOS imágenes exclusivas de SU escena. Nunca toman
prestada una imagen anterior ni posterior. `p6_assets._planificar_tarjetas`
reserva la pareja antes de generar usando el mismo reparto que previa/render.
`_generar_escenas` obtiene el recurso adicional `Sxxx__tarjeta.png` con el mismo
proveedor, caché y recuperación; lo agrupa como `tarjeta` en la salida de la unidad
original, sin añadir una escena al audio o al montaje. `tarjetas_animacion.otra`
del plan apunta al PNG. Los dos recursos pasan el guardián de duplicados y las
fichas extra llevan `tarjeta_extra` para que la recolocación no los intercambie
con imágenes principales con la misma narración. Retomar conserva lo ya pagado;
rehacer una escena rehace únicamente su pareja. Las asignaciones manuales que
necesitan una imagen nueva guardan la reserva en params de ESA unidad de assets.
`p8` pasa `imagenes`
(URL de cada hyperframe) y la página las PRECARGA en `#precarga`: un `<image>`
dentro de un SVG no lo espera `Navegador.abrir` y la primera captura saldría vacía.

**El render** (`p8_render`): capa `#capaanim` con z-index sobre el subtítulo;
`PARAMS_POR_DEFECTO["animaciones"]` es solo el respaldo de los vídeos de antes.
Atenuar o desenfocar el PLANO no lo puede hacer el SVG: `capas` devuelve `fondo` y
la página lo aplica con `animaciones.JS_FONDO`. Un contorno de texto que se
«escribe» se enciende letra a letra (`_tecleo(trazo=)`) o se ve fantasma. Cada
animación declara cuánto necesita para leerse (`tiempo`) y `repartir` la salta si
  la señal cae tarde.
  `collage-titulo` y `comparacion-tarjetas` empiezan al inicio del plano aunque
  la frase que las justifica se diga despues: necesitan tiempo para presentar
  las dos fotografias antes del corte. Permanecen hasta el ultimo fotograma de
  la escena, sin el limite de 4,2 s de los rotulos breves: las salidas SMIL y el
  retorno del fondo empiezan en `duracion`, ya fuera del plano.

**La previa** (`GET /previsualizacion`): cada escena trae `animacion` (svg, fondo,
`pico`, `elementos`) y el resumen `animaciones`. El navegador la pinta encima de la
imagen (`animarPrevia`, un fotograma de pantalla, con el reloj de la voz; parada,
en el `pico`, el instante en que está completa) y la imagen pasa a `cover` como el
render. El botón «✦ Animación» abre el editor de contenido y tipo; sin asignación
aparece «✦ Crear animación». Este editor guarda solo al pulsar **Guardar** (o
Ctrl+S); cerrar descarta el borrador.
La opción «Sin animación» persiste `id: "sin-animacion"` con contenido vacío:
suprime la asignación automática DESPUÉS del reparto; borrar el ajuste manual
haría reaparecer la animación del guion. Las ediciones viven en
`render.params.unidades["escena:<sid>"].animacion`, ancladas a la narración normalizada.
Nunca uses un mapa global indexado por escena: el núcleo lo rechaza cuando las
unidades están declaradas y contaminaría todas sus firmas. Conserva los demás
params de la unidad al guardar. `animaciones.capas` las aplica DESPUÉS del
reparto automático, sin desplazar las animaciones de otras escenas ni tocar guion
o voz. Editar textos o subir tarjetas solo afecta al render; cambiar a un tipo
de dos imágenes sin pareja disponible reserva el recurso en la unidad de assets.
En `p8_render.ejecutar`, `pedidas` contiene ids de UNIDADES: usa
`animaciones_pedidas` para los tipos del catálogo; sobrescribir la primera saltaba
clips ya existentes y sellaba mal las unidades. La regresión del remontaje con
clips previos está en `prueba_animaciones` y la cadena real en `prueba_pasos_visuales`.
El esquema de campos está en `animaciones.CAMPOS`. Tipografía cinética admite
`contenido.subrayado` (texto):
`subrayadas_de` resalta todas las palabras coincidentes, sin distinguir mayúsculas
ni puntuación; vacío = ninguna. Si el campo no existe (guiones o ediciones
anteriores), mantiene la elección automática de una palabra sin mutar params.
El editor muestra esa elección inicial y solo persiste al pulsar Guardar.
GET del editor es solo lectura y PUT valida antes de actualizar params.
El borrador usa POST `escenas/<sid>/animacion/previsualizar`, sin guardar params.
`animacion.posiciones.conjunto` guarda el desplazamiento normalizado (`x`/`y`)
de toda la animación. `ajustar_svg` envuelve su contenido visual en un único
`data-conjunto`, fuera de defs; conserva la lectura de offsets `e<N>` anteriores,
pero el editor solo deja arrastrar el conjunto. El arrastre convierte el puntero
con la matriz inversa del padre. El historial local del popup captura tipo,
contenido, imágenes y ajustes antes de cada cambio (un arrastre = una entrada);
Ctrl/Cmd+Z y ↶ usan la misma restauración, sin persistir hasta Guardar.
`animacion.duracion`, si
existe, escala todos los tiempos SMIL y el fondo a esos segundos (0,1 s hasta
la duración de la escena). Previa y render pasan por el mismo `svg_de`.
En las diez `cartela-*`, usa `svg_capa(reloj_unico=True)`: un SVG anidado crea
otro reloj SMIL y buscar el tiempo en el padre no mueve sus palabras. La variante
con grupos conserva escala, centrado y recorte. Al retimar, ignora los bucles
`repeatCount="indefinite"` al calcular el plazo (el fantasma deriva en 14–18 s).
Una duración manual reserva el fundido final y oculta todo el conjunto al
cumplirse el tiempo; `fill="freeze"` en las palabras por sí solo las deja hasta
el corte. Regresión offline y por fotogramas:
`python pasos/prueba_animaciones.py --real` (navegador en `ESTUDIO_EDGE`).
Comparación y collage permiten subir las imágenes izquierda/derecha antes de
Guardar. `animacion.imagenes` contiene referencias relativas `propia`/`otra` a
`medios_usuario/animaciones/<uuid>.png`; no son las imágenes de fondo del plano.
`imagenes_animacion` valida y normaliza las subidas (PNG/JPG/WebP, 20 MiB, 40 MP,
lado máximo 2048 px), conserva archivos inmutables y comprueba la pertenencia al
proyecto al resolverlos. Subir solo prepara archivos: no cambia params. La carpeta
viaja con `medios_usuario` al duplicar/exportar. No borres imágenes anteriores:
pueden estar referenciadas por versiones históricas. `animaciones.urls_imagenes`
resuelve las referencias para previa y render; `capas` mezcla cada lado con el
respaldo automático y precarga ambas imágenes. Con dos subidas no necesita una
imagen de fondo de la escena. Los borradores se aplican solo con Guardar.
`aplicarFondo` de `app.js` es COPIA de `animaciones.JS_FONDO`
(`prueba_animaciones` compara las dos). Las URL de otras imágenes viajan como
`proyecto://ruta`: solo el navegador sabe el prefijo del proxy.

**La pantalla** (sección «Motion animation» en estilo, encargo y detalle del
estilo): dos recuadros, disponibles a la izquierda y elegidas a la derecha, con
tarjetas de GIF que cambian de lado al pulsarlas. Los recuadros miden SIEMPRE 506 px
de alto y hacen scroll por dentro (`.anim-recuadro`). Los GIF son `web/anim_<id>.gif`
(planos: `fichero_web` no sirve subcarpetas) y salen del mismo dibujo que el render:
si cambias una animación, `python herramientas/gifs_animaciones.py` los regenera
(por PowerShell: Edge headless; no usa ffmpeg, escribe Pillow).

**Transición por escena**: el botón edita la salida de la escena actual hacia
la siguiente, pero `render.params.unidades["escena:<siguiente>"].transicion`
guarda `{tipo, ancla}` porque p8 cuece la transición en el clip que ENTRA.
`transiciones.ancla_de` vincula ids y narraciones de ambos planos; validar usa
`_plan_de_previsualizacion`, igual que la pantalla. `resolver` aplica las
ediciones después del reparto para no cambiar los vecinos, incluso si la
paleta global está vacía. `tipo: "corte"` suprime explícitamente el efecto.
GET del editor y los borradores WebGL son de lectura; solo PUT guarda, conserva
otros params de esa unidad y no cambia assets/callouts. La última escena no
tiene salida. Prueba offline: `python pasos/prueba_transiciones_escena.py`.

El editor admite `inicio`/`fin` en esa edición: el bloque pasa a ser un enlace
temporizado dentro de la escena que sale. La API copia la edición a
`salida_transicion` de esa unidad para invalidar también su clip. `resolver`
conserva el intervalo y `cuece_el_anterior` impide cocerlo de nuevo en la entrada.
P8 compone la salida contra el primer cuadro de la siguiente escena, sin esperar
a su lote, y conserva ese cuadro después del final elegido. Rehacer la siguiente
arrastra la salida anterior si usa ese cuadro. Las ediciones sin intervalo
conservan su montaje histórico. La previa carga el pintor al abrir el editor y
su progreso depende del reloj común, también al buscar y arrastrar. Regresión
de persistencia y píxeles: `python pasos/prueba_editor_escena.py --real`.

La pista **Sonidos**, debajo de Animación, agrupa los eventos automáticos por
papel (mecanografía, retorno, transición y audio de biblioteca). Sus intervalos
manuales viven en `render.params.unidades["escena:<sid>"].sonidos`, con `ancla`
y `bloques: [{id, inicio, fin}]`; ausencia hereda y lista vacía silencia la escena.
`sonido.eventos` retima la posición de las pulsaciones, pero cada muestra mantiene
siempre su velocidad y tono originales, tanto en Web Audio como en la mezcla.
Acortar un bloque recorta el audio; alargarlo no estira ni repite el archivo.
No uses la proporción entre duración de bloque y fuente como `playbackRate` ni
para remuestrear: un sonido añadido cerca del final de la escena se aceleraba
porque el bloque se limitaba al tiempo restante.
El editor reproduce los mismos intervalos con Web Audio junto al reloj de la voz.
Abrir el editor solo lee: nunca persiste los bloques automáticos. Los ajustes de
animación y sonido son independientes; se coordinan manualmente en estas pistas.
«Añadir bloque» abre `abrirBuscadorSonidos`: busca en `GET /api/sonidos/buscar`,
escucha mediante `/api/sonidos/<id>/muestra` (mismo origen, sin depender de la CSP
para medios externos) y prepara con `POST escenas/<sid>/sonidos`. La selección
usa el id de Freesound; el servidor resuelve sus datos, nunca acepta una URL de
descarga del cliente. El recurso inmutable y su ficha se copian a
`medios_usuario/sonidos/<id>.mp3/.json`, sin modificar params hasta Guardar.
Los bloques manuales usan `id: "freesound:<id>"`; `fuente_usuario` resuelve sus
rutas dentro del proyecto tanto al reabrir como al montar. P8 pasa `proyecto`
a `sonido.eventos`; sin él no se pueden resolver estos efectos. La copia no
depende del banco global. `traer` serializa por fichero para evitar que escuchar
y seleccionar a la vez compitan por el mismo `.parcial`. Pruebas offline de
búsqueda, selección, reabrir, validación y audio en `prueba_editor_escena.py`.

**Editor global de Imágenes**: `editorGlobalImagenes` monta `abrirEditorEscena`
en la pantalla principal, con seis pestañas y seis pistas globales. Cada escena
conserva su borrador e historial en un controlador; el árbol DOM se reutiliza al
repintar. Solo Guardar escribe las pestañas modificadas mediante el contrato
existente. La galería y la decodificación de la onda se comparten; los contextos
WebGL se liberan al cambiar de escena y sus canvas se recrean (un contexto
perdido no se reutiliza). El reloj local se convierte con `t_in` al global.
`python pasos/prueba_editor_global.py --real` verifica selección, borradores entre
escenas, deshacer global, guardado/reapertura, arrastre y reproducción continua
en Chromium, con un proyecto sintético y datos aislados.

Las fichas y borradores del timeline persisten en IndexedDB (`estudio.editor`),
separados por `BASE`, proyecto y escena. `editor_revision`, publicado en cada
escena de la previsualización, invalida solo las fichas afectadas; se calcula
sin escribir params ni usar las firmas del grafo. Mantén sus dependencias al
cambiar el contrato del editor. Al guardar, actualiza también la ficha cacheada
y su revisión; al descartar, persiste el borrador limpio. Una revisión distinta
no debe aplicar un borrador antiguo automáticamente: conserva la recuperación
separada, y exige el mismo texto, tiempos y resolución para restaurarlo.
La carga se detiene al salir de Imágenes y se reanuda al volver, priorizando las
escenas que ya están en la caché. Los fallos de IndexedDB no bloquean el editor.
Publicar assets copia los recursos intactos a otra `v<N>`: esa ruta nueva no
es un cambio de contenido. `_revisiones_editor` normaliza las rutas de recursos
existentes de assets/callouts a paso, nombre relativo y sello de fichero (copy2
conserva mtime/tamaño). No elimines las dependencias reales de medios ni de la
escena siguiente, necesarias para las transiciones. El chat y la regeneración
Stickman usan `refrescarLoDibujado` para conservar la previa y actualizar assets;
el editor reutiliza sus controladores y revalida solo las revisiones distintas.

**Contrato del editor de escena**: `abrirEditorEscena` reúne las pestañas y
el reloj de la narración. GET/PUT `escenas/<sid>/editor` validan todas las ediciones
antes de guardar y solo escriben pestañas modificadas. `animacion.bloques` conserva
la primera ficha en la raíz para lectores antiguos; `animaciones.capas` aísla ids
SVG y compone todos los bloques bajo un solo reloj SMIL.
Al extraer el contenido de un SVG, conserva la transformación de su `viewBox`
al lienzo de salida: las cartelas usan 1536×864 (864×1536 en vertical), no los
píxeles del vídeo. `_interior_svg_en_salida` aplica esa escala con precisión
completa y publica el tamaño original para que el arrastre siga normalizado en
ese lienzo. Sin esa transformación, las cartelas quedan pequeñas en la esquina.
La regresión visual de las diez plantillas está en
`python pasos/prueba_editor_escena.py --real` (Chromium de Playwright).
El avatar usa
`presentacion.bloques`: cada aparición sigue el tiempo absoluto del mismo clip,
sin regenerar Boson. `transiciones_escena` pertenece a la unidad actual, anclada
a la narración: son entradas/salidas a negro con tiempos propios y el GLSL del
montaje; la transición hacia la siguiente sigue en su unidad de entrada con su
contrato anterior. P8 captura los frames de escenas con efectos temporales antes
de componerlos. Pruebas aisladas: `python pasos/prueba_editor_escena.py`.

**Avatar sobre cartelas o vídeos**: `avatar.admite_escena` y la selección editorial
solo exigen texto narrado y un intervalo de hasta 60 s; el medio no lo excluye.
La previa debe publicar a la vez el clip de fondo y el avatar, con este último
por encima de las cartelas. P8 mantiene el vídeo/parallax y sus movimientos:
decodifica el avatar aparte y lo superpone al PNG ya capturado, antes de las
transiciones, tanto en el camino de flujo como al conservar frames. No uses
`avatar.componer` para sustituir el fondo en p8: congela los clips y deja el
avatar debajo del velo de la cartela. El lip-sync pagado se conserva, con su reloj
absoluto y caché existentes. Regresión con vídeo de fondo y avatar que cambian de
color a la vez, y cartela opaca: `python pasos/prueba_editor_escena.py --real`.

**Probar sin pagar**: `pasos/_proyecto_animaciones.py` fabrica un proyecto de
juguete con guion etiquetado, plan e imágenes (lo usa `prueba_animaciones`); para
verlo en la interfaz, arranca un servidor aparte con `--proyectos <carpeta>` y las
tres variables `ESTUDIO_*` desviadas. La redacción REAL del plan por Claude no
tiene prueba automática (gasta cupo): lo que se prueba es la instrucción, el
marcado y el rescate con bloques sintéticos.

**Python no recarga solo**: tras tocar `app.py` o `pasos/`, hay que reiniciar el
servicio; un «Not Found» en `/api/animaciones` es un servidor anterior al cambio.

---

## Instalación del CLI de Claude

El asistente y el motor de generación de guiones necesitan el **Claude Agent SDK CLI**.
Si lo intentas usar sin tenerlo, el error será `AttributeError: 'NoneType' object has no attribute 'poll'`,
que significa que el subprocess no arrancó.

**Instalación:**

```bash
npm install -g @anthropic-ai/claude-agent-sdk
claude login
```

Verifica que funciona:

```bash
echo "hola" | claude -p
```

---

## Debugging cuando el CLI falla

| Error | Causa | Solución |
|---|---|---|
| `AttributeError: 'NoneType' object has no attribute 'poll'` | El CLI no está disponible o no arranca | `claude --version`; si no existe, instala con `npm install -g @anthropic-ai/claude-agent-sdk` |
| `el CLI de claude no ha respondido en X s` | Timeout — el CLI está lento o atascado | Baja `esfuerzo` de la configuración (de `xhigh` a `high` o a `medium`) |
| `se ha agotado el cupo` | La suscripción de Claude no tiene crédito | Comprueba `claude --subscription` o recarga tu cuenta en https://claude.ai |
| `[Errno 2] No such file or directory: 'claude'` | El CLI no está en el PATH | Instala con `npm` en lugar de descargar manualmente, o añade su carpeta al PATH |

**Para probar sin llamar a Claude** (en desarrollo):

```bash
ESTUDIO_SIMULAR=1 python app.py --puerto 8020
```

El asistente contesta con un doble que repite lo que recibió.

---

## Antes de dar algo por terminado

```bash
powershell -NoProfile -File pruebas.ps1
```

Todas las suites de la lista `$suites` de `pruebas.ps1` en verde (34 al escribir
esto; no hay un número fijo), y las herramientas de análisis sin nada que decir
(`huerfanas_js` trae dos sospechosas de siempre, `async` y `fallar`, que no son
llamadas).
Y si has tocado la interfaz, **ábrela**: una regla de CSS de menos o un bloque
que no se pinta no da ningún error en ningún sitio.

**Una sola suite** (son scripts sueltos, no pytest; cada una se corre sin más):

```bash
python nucleo/prueba_manifiestos.py
python pasos/prueba_regresiones.py
python prueba_api.py --conservar     # arranca su propio servidor; conserva los proyectos temporales
```

Si cambias rutas de `app.py`, regenera la referencia con `python generar_api.py`
(`docs/API.md`; `prueba_api` comprueba que cuadra, no se edita a mano).

**Capas:** `nucleo/` es el grafo genérico (no sabe nada de vídeo), `pasos/` no
depende de HTTP, `motores/` solo consume contratos de ficheros, y `app.py` es lo
único que une HTTP con ejecutores. Una tarea nueva no corre hasta entrar en
`pasos/recetas.py` y en el ejecutor de `app.py`.

**Pruebas nuevas:** desvía antes de importar `ESTUDIO_ESTADISTICAS`,
`ESTUDIO_SECRETOS` y `ESTUDIO_AJUSTES`. `ESTUDIO_SIMULAR=1` no garantiza que no
haya llamadas reales: cada camino debe implementarlo o usar dobles.

**Windows:** el `TEMP` puede traer el alias 8.3 (`VALENT~1`) y el CLI de Claude
deniega `Write` en esas rutas; usa `os.path.realpath` para temporales, `cwd` y
`--add-dir`. `AGENTS.md` tiene el resto de reglas finas (Codex, medios de
usuario, recuperación de imágenes) con su prueba aislada.

**ffmpeg y ffprobe tienen que estar en el PATH** (`ESTUDIO_FFMPEG` si no): sin ellos
el estudio no monta ni un MP4 ni un Short, y `prueba_api` falla en las dos
comprobaciones de Shorts y varias suites se saltan solas. En esta máquina se
instalaron con `winget install Gyan.FFmpeg` (9.0.2): un shell abierto ANTES no lo ve
(refresca `$env:Path` desde Machine+User) y un servicio arrancado desde él tampoco.

Tres cosas que ahorran perseguir fallos que no existen:

- `prueba_render_acelerado.test_flujo_y_secuencia_conservan_pixeles_subtitulos_y_transiciones`
  falla con ffmpeg 9.0.2 (compara hashes de dos caminos de codificación). Es
  anterior a las animaciones: se comprobó en el commit previo. Antes se saltaba
  por falta de ffmpeg.

- `prueba_pasos_visuales` reutiliza `%TEMP%\estudio_prueba_visual` entre
  ejecuciones; si una pasada se corta a medias, la siguiente falla por el estado
  sucio. `pruebas.ps1` la borra.
- `prueba_pasos_voz` sale a Cartesia de verdad **si hay clave**; si no, omite esa
  parte y lo dice. No es un fallo.
- `prueba_login` llama al CLI de Claude de verdad. Es la única que comprueba que
  el CLI sigue dejando entrar sin terminal y sin abrir un navegador.

## Respiraciones o letras repetidas en la narración

`voz_cartesia.voz._relleno_de_sala` repetía hasta 200 ms de la pausa, alternados
con su reverso, para alargar el aire entre bloques. Las marcas de Cartesia pueden
incluir una respiración o el remate de una consonante en esa «pausa»: el relleno
los convertía en un tartamudeo. Se confirmó comparando una muestra del MP4 con el
WAV guardado y reconociendo exactamente los bucles y sus fundidos. Ocurre al
preparar la voz, no al concatenar las imágenes.

El relleno ahora genera fondo reproducible, sin copiar muestras de la narración,
limitado a unos -63 dBFS RMS. Conserva la longitud insertada y la toma original.
No vuelvas a usar una pausa como bucle de audio. Regresión con una pausa que
contiene voz en `pasos/prueba_piezas.py::prueba_espaciar`. La corrección no elimina
bucles ya escritos en WAV antiguos; remontar ese mismo WAV tampoco los elimina.

## Una frase completa por escena

Las redacciones nuevas guardan `escenas_por_frase: true` en `guion.json`. Voz y
revisión lo transmiten al `audio_meta.json`; `p6_assets.planificar` usa entonces
`segmentar.segmentar_frases`, no el optimizador por duración ni cortes antiguos.
Cada frase empieza por mayúscula y acaba en punto; la validación ocurre antes de
pedir TTS. Los bloques B siguen siendo grupos editoriales y conservan sus ids.
No partas una frase larga ni unas dos cortas para cumplir la horquilla: ahora es
un objetivo de redacción, no permiso para cortar. Las cartelas tampoco fusionan
escenas marcadas `frase_completa`. Los tiempos se alinean con palabras reales del
TTS, incluso si pierde puntuación; si no coinciden las letras, falla en lugar de
inventar tiempos. Regresión offline: `python pasos/prueba_escenas_frases.py`.
No añadas el indicador como param por defecto ni lo inyectes en guiones antiguos:
abrirlos o retomar sus imágenes debe conservar el corte y los recursos pagados.

## Nombres de los recursos visuales

Los planos usan sus identificadores técnicos (`S001.png`, `S002.png`, etc.). Se
retiró el nombrado descriptivo con Claude y la creación de alias en `nombres/`.
Las animaciones tampoco interpretan esos nombres: usan el orden de las escenas.
Los metadatos `nombre_imagen` de versiones antiguas se ignoran; no es necesario
reescribir proyectos ni regenerar recursos para adoptar este comportamiento.

## Personajes personalizados del vídeo

`guion.params.personajes` guarda `{activo, items}` con IDs persistentes, categoría,
nombre, descripción, imagen relativa inmutable de `medios_usuario/animaciones` y
voz opcional. No copies la voz general dentro del narrador: se resuelve al usarlo.
Desactivar opciones conserva los datos. `pasos/personajes.py` valida el narrador
único y los IDs y conecta las identidades con el catálogo y las escenas.

`guion.params.sistema_personajes` fotografía Generar personajes, Incorporar voz
y la voz general. Solo se sincroniza tras una decisión explícita relacionada o
al crear el vídeo: sincronizarlo al guardar una cartela invalida el guion y todo
lo que cuelga. Nunca se escribe al consultar una pantalla. El guion nuevo lleva
un hablante por bloque y `personaje_id`, `personajes_visibles`,
`descripcion_visual`, nombre, categoría y voz resuelta. Conserva estos campos al
normalizar, editar, revisar o regrabar; los nombres no identifican hablantes.

Las voces distintas se sintetizan por turnos contiguos en p4, con caché en
`medios_usuario/voces_personajes/` y marcas absolutas, antes del espaciado habitual.
No la pongas solo en trabajo: `comun.preparar_trabajo` lo borra al reintentar y
repagaría los turnos ya completados. Con personajes, `incorporar_voz:false`
desactiva SOLO al narrador: exige al menos un personaje personalizado y voz
propia en todos los actores antes de pedir el guion. Solo esos actores pueden
hablar; nunca uses la voz general como respaldo en esta modalidad. La validación
vive en `personajes.validar_voces` y se aplica en UI, API y p3 antes de Claude.
P4 y p5 usan `sin_locucion` para distinguir este modo del vídeo tradicional
sin personajes, que sí mantiene pista muda sin TTS. P6 copia la referencia personalizada como hoja de reparto sin volver a
generarla. Generar personajes bloquea las búsquedas visuales de bibliotecas en
el motor, aunque Personalizar personajes esté apagado; no sobrescribas la
preferencia guardada de bibliotecas para forzar IA. Regresión offline:
`python pasos/prueba_personajes.py`.

La casilla **Incorporar diálogos** vive en
`guion.params.personajes.incorporar_dialogos`. Los formularios nuevos la inician
desactivada; la ausencia en proyectos antiguos conserva su contrato de hablantes
sin escribir defaults al abrir. Activada combina narrador principal y diálogos
si hay voz general, o exige solo diálogos con voces propias si no la hay.
Desactivada permite únicamente narración; sin voz general conserva el guion
habitual y la pista muda. `solo_personajes` y `sin_locucion` distinguen ambos
caminos; la validación de intervenciones rechaza actores hablantes si la casilla
está apagada. No vincules la presencia visual de un personaje a su intervención.

Personaje y Narrador admiten `primera_persona: true` en su ficha (ausencia =
desactivado), pero solo una ficha por vídeo puede activarla. `normalizar` rechaza
duplicados y `personaje_pov` resuelve el observador sin depender de su categoría.
Claude recibe la regla POV en guion, dirección y redacción visual; p6 la aplica
a todas las escenas con `perspectiva_narrador` y la refuerza al final del prompt,
también al corregir o preparar alternativas. La hoja completa sigue siendo una
referencia de identidad obligatoria aunque el personaje elegido no figure en
`personajes_visibles`: `_personajes_referencia` la incluye en inventario,
dependencias y adjuntos, sin forzar su presencia externa. No apliques POV al
generador de la ficha de cuerpo entero ni añadas valores por defecto al abrir.
