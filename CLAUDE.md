# AS Video Studio — lo que hay que saber antes de tocarlo

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
de la API. Las claves existentes conservan el camino anterior hasta activar
«Usar ChatGPT». El adaptador es `motores/imagen_openai/codex.py`; ver el setup en
`README.md` y `python pasos/prueba_codex_imagen.py`. No se pasan los tokens de
login a `/v1/images` ni se hace fallback de pago. Las reglas de firmas, caché y
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

Collage, pantalla dividida con vídeos propios, paralaje real y avatar de la guía
NO están: piden varios recursos por escena o capas de profundidad que el plan no
modela. Lo que no se deduce del código:

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
`requiere_imagenes`): usan la imagen de su escena y la de la de al lado (la
siguiente, o la anterior si no hay; `elementos` en la asignación). NO se genera una
imagen extra: sería gasto y tocaría el motor de imágenes. `p8` pasa `imagenes`
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
render. El botón «✦ Animación» la apaga para ver el dibujo solo (preferencia en
`localStorage`). `aplicarFondo` de `app.js` es COPIA de `animaciones.JS_FONDO`
(`prueba_animaciones` compara las dos). Las URL de otras imágenes viajan como
`proyecto://ruta`: solo el navegador sabe el prefijo del proxy.

**La pantalla** (sección «Motion animation» en estilo, encargo y detalle del
estilo): dos recuadros, disponibles a la izquierda y elegidas a la derecha, con
tarjetas de GIF que cambian de lado al pulsarlas. Los recuadros miden SIEMPRE 506 px
de alto y hacen scroll por dentro (`.anim-recuadro`). Los GIF son `web/anim_<id>.gif`
(planos: `fichero_web` no sirve subcarpetas) y salen del mismo dibujo que el render:
si cambias una animación, `python herramientas/gifs_animaciones.py` los regenera
(por PowerShell: Edge headless; no usa ffmpeg, escribe Pillow).

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
