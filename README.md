# AS Video Studio

Convierte **lo que escribas** —unas notas, un artículo pegado, una cronología, o
tu propio guion— en un vídeo de animación narrada, pasando por ocho fases con
revisión humana entre ellas.

```
ingesta → brief → guion → voz → revision_audio → assets → callouts → render
```

Esos son los ids del grafo y **no cambian**: renombrarlos invalidaría los
proyectos guardados. En pantalla son **cinco paradas**, en la barra de abajo:
los estilos, el encargo (con el material y las llamadas a la acción; se vuelve a
él y se corrige también después de generar el guion), el guion, las imágenes y
el vídeo, con el coste delante en todas.

**No es un asistente: es un sistema de build.** Cada paso es una función de sus
entradas, con hash de contenido. Cambiar algo no regenera todo — deja obsoleto
solo lo que dependía de lo que cambió, con granularidad por unidad (una escena,
un asset). Sin eso, cada retoque obligaría a rehacer el vídeo entero y esto no
serviría para nada: **una tanda de imágenes cuesta dinero de verdad**.

**Nada se confirma a mano.** Editar es decidir: lo que se toca se guarda solo al
dejar de teclear, y el paso siguiente usa la última versión. No hay botones de
«guardar cambios» ni de «aprobar»; pasar al paso siguiente ES la aprobación.

---

## Las dos cosas que se crean

**Un ESTILO** es lo que se decide una vez y se repite en todos los vídeos de un
canal: unas imágenes de referencia con sus indicaciones (cómo se dibuja), cómo se
cuenta (el tono), cada cuánto corta el vídeo (el ritmo), quién lo locuta y en qué
idioma. Se escribe una vez y cada vídeo nace con él puesto.

**Un VÍDEO** es lo que cambia cada vez: cómo se llama, cuánto dura, el material
del que salen los hechos, las indicaciones de cómo contarlo, y las llamadas a la
acción de ESE vídeo. Las llamadas a la acción se deciden vídeo por vídeo a
propósito: es lo que más cambia entre dos vídeos del mismo canal, y guardarlas en
el estilo obligaba a acordarse de cambiarlas en cada encargo.

---

## Sincronizar los sonidos de una escena

En la fase **Imágenes**, **Reproducir** usa la toma completa de narración sin
pausarla ni reposicionarla al pasar de una escena a otra. Las imágenes y las
animaciones siguen el reloj del audio. Seleccionar una escena o una posición
del timeline permite cambiar el punto desde el que se reproduce.

En el editor de escena, la pista **Sonidos**, debajo de **Animación**, muestra los
efectos disponibles, incluida la mecanografía de las cartelas. Arrastra un bloque
para cambiar su inicio, o sus extremos para ajustar el tiempo que suena.
Los efectos conservan su velocidad y tono originales: si el bloque es más corto,
se recortan; si es más largo, terminan al acabar el archivo, sin estirarlo.
También puedes introducir los tiempos en la pestaña **Sonidos** o eliminar un
efecto de esa escena.

**Añadir bloque** abre un buscador de **Freesound** con resultados paginados.
Escribe lo que necesitas (por ejemplo, `football kick` o `stadium crowd`), pulsa
**Buscar**, escucha las muestras y pulsa **Añadir** en el efecto elegido. El
popup muestra duración, autor y enlaces a la licencia y al recurso original;
también permite reutilizar los sonidos disponibles en la escena. Se necesita
la clave de Freesound de **Configuración → Bibliotecas, música y efectos** para
buscar y obtener efectos nuevos. Al abrir el buscador se muestran los más
descargados del catálogo.

El efecto seleccionado se incorpora al borrador en la posición del cursor,
limitado al tiempo restante de la escena. Su audio y metadatos se conservan
dentro del proyecto, por lo que viajan al duplicar o exportar el vídeo.

Pulsa **Reproducir** para escuchar los efectos junto a la narración y comprobar su
coordinación con la animación. Pulsa **Guardar** y vuelve a **Montar el vídeo**
para aplicar el ajuste al MP4.

## Llevar un estilo a otro servidor

En **Tus estilos**, abre el menú **⋯** de la tarjeta y pulsa **Exportar**.
Descargarás un ZIP con la configuración del estilo, sus imágenes de referencia,
miniatura, muestras y el taller del que salió, si lo tiene. El taller conserva
sus archivos e histórico para poder seguir editando el estilo en el destino.
Espera a que termine cualquier generación del estilo antes de exportarlo.

En el otro servidor, pulsa **Importar estilo**, junto al título **Tus estilos**,
y selecciona ese ZIP. Se crea un estilo nuevo con el mismo nombre y sus rutas
adaptadas al servidor de destino; los estilos y vídeos existentes se conservan.
Puedes importar el mismo paquete varias veces: cada importación es una copia
independiente. Ambos servidores deben tener esta función instalada.

El traslado no genera contenido ni consume cuota de IA. Las credenciales no
viajan: configura los proveedores en el destino para generar nuevos vídeos.
El límite del paquete es **1 GB descomprimido y 20.000 archivos**. Si faltan
referencias o el paquete está incompleto, se muestra un error sin publicar un
estilo a medias.

## Llevar un vídeo a otro ordenador o servidor

En **Tus vídeos**, pulsa **Exportar** junto al vídeo. Se descarga un archivo
`.video.zip` con el proyecto completo: encargo, guion y correcciones, voz,
imágenes y referencias de estilo, montaje, archivos de publicación y shorts si
los tiene, historial de versiones y trabajo parcial guardado. Espera a que
termine la generación o detenla antes de exportar.
La preparación muestra un panel persistente con porcentaje, archivos procesados
y tiempo transcurrido. Después indica los MiB descargados y el progreso de la
descarga; cualquier error queda visible en el panel. El ZIP preparado se conserva
una hora para poder volver a descargarlo si se interrumpe la conexión.

En la otra instalación, pulsa **Importar vídeo**, junto a **Tus vídeos**, y
selecciona el ZIP. El vídeo se abre como una copia independiente para continuar
desde la fase alcanzada: por ejemplo, montar usando las imágenes y el audio ya
generados. Las rutas y firmas se adaptan al destino, conservando también los
cambios pendientes reales. No se sobrescriben vídeos existentes, aunque se
importe varias veces el mismo paquete.
La importación muestra el mismo panel: primero el porcentaje y los MiB de la
subida; después la descompresión, la comprobación de integridad y la adaptación
de rutas y versiones. El panel permanece visible con el tiempo transcurrido
hasta confirmar el resultado o mostrar el error.

El traslado no genera contenido ni consume cuota de IA. No incluye credenciales
ni ajustes globales del servidor: configura los proveedores en el destino si
vas a generar contenido nuevo. Las referencias del estilo viajan con el vídeo;
para añadir también ese estilo a **Tus estilos**, expórtalo por separado.
Ambas instalaciones deben disponer de esta función y de una versión compatible
del Estudio. El límite es **2 GB de ZIP, 20 GB descomprimidos y 100.000 archivos**.
Se comprueban el inventario y las huellas de los archivos antes de publicar el
proyecto; un paquete incompleto o alterado se rechaza sin dejar un vídeo a medias.

## Ponerlo en un servidor (lo normal)

Una línea en la consola del VPS, cinco minutos, y queda montado con su dirección,
su candado y su contraseña — incluido todo lo que hace falta alrededor (ffmpeg,
el navegador que dibuja los planos, las fuentes, el CLI de Claude):

```bash
curl -fsSL https://raw.githubusercontent.com/NeverBlink/as-video-studio/main/instalar.sh -o instalar.sh && bash instalar.sh
```

Los tres pasos, con qué pulsar y qué hacer si algo falla, están en
**[INSTALAR.md](INSTALAR.md)**. Lo que el instalador hace por dentro, y por qué,
en **[despliegue/LEEME.md](despliegue/LEEME.md)**.

## Arrancar en tu propia máquina

### Linux

En Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y python3-venv ffmpeg
```

En cualquier Linux con Python 3.12 o superior, un solo comando instala el
servicio y el motor opcional de parallax:

```bash
bash instalar_dependencias.sh
.venv/bin/python app.py --puerto 8020
```

`instalar_dependencias.sh` crea `.venv` con las dependencias del servicio y
`.depthflow` con DepthFlow, cada uno en su propio entorno; no borra los que ya
existan y se puede volver a lanzar. Si no quieres el parallax, basta con
instalar el servicio:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

El navegador que rasteriza los planos (**Chromium** o **Microsoft Edge**) y las
fuentes se instalan aparte; `ESTUDIO_EDGE` y `ESTUDIO_FUENTES` permiten fijar
sus rutas.

En Windows, el script equivalente crea el servicio y, salvo que lo omitas, el
motor de parallax:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar_dependencias.ps1
.\.venv\Scripts\python.exe app.py --puerto 8020
```

`-SinDepthflow` instala solo el servicio y `-Python C:\ruta\python.exe` elige el
intérprete. El script no borra los entornos que ya existan y se puede volver a
lanzar. También comprueba ffmpeg/ffprobe, Edge o Chrome y los CLI de Node,
Claude y Codex, y dice qué falta y cómo instalarlo.

Si prefieres hacerlo a mano:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --puerto 8020
```

Y abrir `http://127.0.0.1:8020/`. Con `--host 0.0.0.0` escucha en la red local;
**no lo pongas a la vista de internet sin un login delante**: la API no
autentica nada, a propósito (ver «Quién está dentro» más abajo).

### Sustituir una escena por una imagen o un clip propio

En **Imágenes**, selecciona la escena y pulsa **↔ Sustituir imagen**, encima del
previsualizador. El botón está siempre visible y sustituye el material de la
escena actual. Elige una imagen **PNG, JPG o WebP**, o un vídeo **MP4, MOV,
WebM, MKV, M4V o AVI** (hasta 200 MiB por archivo).

Los clips deben durar **al menos 2 segundos**. Si superan **15 segundos**, el
Estudio conserva automáticamente solo el tramo **0–15 s**, sin pedir un recorte
manual. El clip se muestra sin su audio original. Al pulsar **Reproducir**,
sigue el reloj de la narración y congela el último
fotograma si termina antes que la escena. Se puede volver a sustituir.
Las imágenes y vídeos se adaptan al lienzo del proyecto, centrando y recortando
lo que sobresale para cubrirlo sin deformaciones.

Al **Montar el vídeo** se mezclan las imágenes y los clips elegidos, conservando
la narración, sus tiempos, los subtítulos, las cartelas y las transiciones. El
audio original del clip no se utiliza. La escena mantiene su duración: si el
clip termina antes, permanece su último fotograma hasta el siguiente corte; si
dura más que la escena, solo se reproduce lo que cabe en ella.

Cada sustitución crea una versión de assets y deja pendientes las capas y el
montaje afectados. Las demás imágenes y la voz se conservan; no se llama a un
generador de IA. El material propio se guarda dentro del proyecto, viaja al
exportarlo o duplicarlo y sigue seleccionado al retomar la generación. Espera
a que termine el trabajo del vídeo o páralo antes de sustituir una escena.

### Combinar bibliotecas e imágenes con IA

En los **estilos** y en el **encargo del vídeo**, justo encima de **Subtítulos**,
aparece **Obtener recursos visuales**:

- Elige el origen principal: **Bibliotecas (Pixabay/Pexels)** o
  **Inteligencia artificial**. El slider reparte los recursos en incrementos del
  10 %; el origen principal representa al menos el 50 %. Al cambiar de origen,
  el porcentaje se invierte si hace falta para conservar esa mayoría.
- Selecciona **Pixabay**, **Pexels** o ambas, e **Imágenes** y/o **Vídeo**.
- Puedes complementar **según el porcentaje configurado** o **cada N escenas**
  (inicialmente 5). Son opciones excluyentes: la cadencia sustituye al porcentaje
  y desactiva su slider. Si priorizas bibliotecas, cada N escenas se genera una
  imagen IA; si priorizas IA, cada N escenas se busca un recurso de biblioteca.
  Cada origen conserva su modalidad e intervalo al alternar entre ambos.
- En **Repartir carga de trabajo**, el porcentaje indica cuántas escenas buscará
  **Claude**; el resto las buscará **ChatGPT/OpenAI**, usando Codex o la API key
  según la prioridad de **Configuración → Imágenes**. Si el principal no está
  disponible, se intenta el otro método. La API usa `gpt-4.1-mini` para preparar
  consultas y elegir recursos, con facturación por tokens; Codex usa tu sesión.
  Por ejemplo, 70% reparte aproximadamente siete de cada diez escenas a Claude;
  0% encarga todas a ChatGPT y 100% todas a Claude, en incrementos del 10 %.
  Se reparten tanto la preparación
  de la consulta como la elección del recurso. El reparto se redondea a escenas
  completas, excluyendo las reservadas para IA y los medios propios.
  Los vídeos nuevos parten de 50/50; los anteriores mantienen Claude hasta que
  cambies el control. También puedes configurarlo en un estilo para vídeos nuevos.

En la modalidad porcentual se reserva una proporción estable y equilibrada de
escenas para cada origen, redondeada a escenas completas. En **cada N escenas**,
las escenas ilustradas N, 2N, 3N… usan el origen complementario y las demás el
principal. La generación de imágenes usa siempre el método principal y el
respaldo ordenados en Configuración. Las cartelas de
fondo sólido, los componentes
ya construidos y las sustituciones manuales conservan su tratamiento propio.
El selector prepara búsquedas para la escena y elige entre los resultados;
si ninguno encaja o el archivo no es utilizable, se genera una imagen con IA
y se indica en el progreso. Los vídeos se descargan y normalizan **sin audio**.
Con 100 % bibliotecas y reparto porcentual, todas las escenas buscan primero en
las bibliotecas seleccionadas; la IA solo interviene si no hay un recurso adecuado.
Con 100 % IA y reparto porcentual, las bibliotecas no se consultan ni requieren
clave, aunque conserves su selección para volver a combinarlas después.
Sin bibliotecas visuales seleccionadas, las escenas se ilustran con IA.
Los proyectos anteriores conservan su reparto y cadencia de IA al abrirse;
solo adoptan el nuevo reparto al editar los controles de origen o bibliotecas.

Configura las claves de los proveedores elegidos en **⚙ Configuración →
Bibliotecas, música y efectos** y los métodos de generación para las imágenes de IA.
Las claves también admiten `PIXABAY_API_KEY` y `PEXELS_API_KEY` por entorno.
Una biblioteca visual sin clave detiene la tarea con el motivo, antes de generar
los recursos.

Los estilos transmiten estas opciones a los vídeos nuevos. Las búsquedas se
cachean 24 horas; los recursos elegidos y su procedencia se guardan en el
proyecto y viajan al duplicarlo o exportarlo. Al retomar se conserva lo obtenido.
Cambiar las opciones de bibliotecas no sustituye escenas ya generadas: para
pedir otra imagen se regenera explícitamente la escena elegida.
Las imágenes muestran su autor y un enlace a la biblioteca en la revisión.
Sin proveedores seleccionados, se mantiene la generación habitual con IA.

En **Estilos → Personajes**, desmarca **Generar personajes** si no necesitas
hojas de referencia para las imágenes con IA. Los vídeos nuevos heredan esa
decisión: no se dibujan hojas de reparto ni se adjuntan a sus planos, aunque el
catálogo visual identifique personas en el relato. Los vídeos anteriores siguen
con su configuración; las imágenes ya creadas no se borran.

### Personalizar personajes de un vídeo

Con **Generar personajes** activado en el estilo, **Crear/editar vídeo** muestra
**Personalizar personajes**, debajo de Voz y encima de Incorporar avatar IA.
Activa su casilla para abrir el editor y las tarjetas de personajes añadidos.

- Elige **Personaje** o **Narrador**, escribe su nombre y descripción y pulsa
  **Generar personaje**. La imagen se genera de cuerpo entero con el método de
  imágenes configurado y su respaldo. También puedes subir una imagen propia.
  **+ Agregar** se habilita cuando hay imagen, nombre y descripción.
- **Editar** recupera el personaje en el editor. Puedes cambiar sus datos o
  regenerar la imagen; **Guardar** actualiza la misma tarjeta y conserva su ID.
  **Cancelar** descarta el borrador. **Eliminar** pide confirmación.
  Antes de crear el vídeo, los personajes agregados se conservan como borrador
  en este navegador; al crearlo pasan a guardarse dentro del proyecto.
- Los personajes pueden tener una voz opcional. **Incorporar voz** abre un
  selector con búsqueda y muestras; confirma con **Usar esta voz** y guarda el
  personaje. Sin voz propia, sus intervenciones usan la voz general del vídeo.
- Solo puede haber **un narrador**. Su voz siempre es la general; cambiarla en
  Voz actualiza su asociación. Sin Incorporar voz, Narrador no se ofrece para
  crear otro, y el narrador ya guardado se conserva inactivo para la locución.
- Tanto **Personaje** como **Narrador** muestran **Activar primera persona** debajo
  de su descripción. Solo uno puede tenerla activada: su tarjeta destaca con la
  etiqueta **Primera persona** y la casilla de los demás queda deshabilitada hasta
  desactivarla en esa tarjeta o eliminarla. Al marcarla, Claude adapta el guion y las descripciones visuales y
  todas las imágenes de escenas se generan desde los ojos del personaje elegido (POV),
  también durante los diálogos de otros personajes. Pueden verse partes de su
  cuerpo, ropa, objetos o reflejos cuando corresponda, sin mostrarlo desde una
  cámara externa. Su tarjeta y su imagen de referencia de cuerpo entero,
  incluido el rostro, se mantienen. La opción se conserva al editar; desmarcarla
  permite volver a los encuadres habituales en las nuevas generaciones.

Al generar el guion, Claude utiliza las identidades personalizadas antes que
las automáticas y distingue cada intervención de su descripción visual. Con
voz puede combinar narración y diálogos; al desactivar **Incorporar voz**, con
**Generar personajes** activo, escribe una historia basada en conversaciones y
se locutan únicamente las voces propias de los personajes, sin narrador ni voz
general de respaldo. Antes de generar el guion debes activar Personalizar
personajes, agregar al menos un personaje y asignar voz a todos los personajes
de categoría Personaje. Si falta alguna voz, se bloquea la generación y se
indican los nombres pendientes. El narrador guardado se conserva inactivo;
los personajes automáticos adicionales solo pueden aparecer visualmente.
Las voces se sintetizan en el orden del guion, con marcas temporales
para las escenas y referencias de imagen para mantener la apariencia.

Mientras **Generar personajes** esté activado, **Obtener recursos visuales**
queda bloqueado en **100 % imágenes IA y 0 % bibliotecas**, también sin
personajes personalizados. El motor no busca stock ni lo utiliza como respaldo
si fallan los generadores. La preferencia anterior de bibliotecas e IA se
conserva y reaparece al desactivar Generar personajes. Desactivar Personalizar
personajes o Incorporar voz conserva las fichas, las imágenes y las voces
guardadas; los archivos viajan al duplicar o exportar el vídeo.

En **Estilos → Voz** y en el **encargo del vídeo** puedes desmarcar **Incorporar
voz**. El estilo transmite su selección a los vídeos nuevos y cada encargo puede
cambiarla. Con Generar personajes activo, desactivar Incorporar voz elimina
solo la voz general del narrador: los personajes deben tener voces propias y
sus diálogos sí se locutan. Sin generación de personajes, no se llama a Cartesia:
se crea una pista muda con tiempos estimados para sincronizar planos, cartelas y
subtítulos. En ese caso el vídeo no lleva locución, aunque conserva la música y
los efectos si están configurados. En el
estilo, los campos de voz quedan desactivados hasta volver a marcar la casilla.

En **Imágenes**, el botón **Regenerar imagen** de un apunte genera una imagen
con IA para esa escena usando la nota, aunque antes tuviera un recurso de
biblioteca o una sustitución manual. El medio anterior deja de estar seleccionado;
las demás escenas se conservan. Puedes volver a elegir un archivo con **Sustituir**.

### Incorporar un avatar IA

En **crear/editar vídeo**, activa **Incorporar avatar IA**. Arrastra una imagen
a la zona **4:3** o pulsa para subirla (PNG, JPG o WebP, hasta 10 MiB). A su lado,
el chat **Generar imagen con IA** permite describir al presentador y generar su
retrato antes de montar. La imagen aparece en el mismo lugar de la zona de
subida. Puedes pedir cambios en el chat conservando el retrato como referencia;
**Sustituir** aparece al pasar el cursor sobre la imagen (siempre visible en
pantallas táctiles). Usa un rostro de frente, con los labios visibles.

Introduce la clave en **Configuración → Boson AI**. Al abrir **Imágenes**, el Estudio elige
automáticamente las explicaciones centrales del relato (aproximadamente una
aparición por cada ocho escenas, hasta ocho) y envía a **Higgs Avatar** la misma
imagen y el fragmento real de narración de cada escena. Requiere **Incorporar voz**.
El avatar se puede incorporar sobre imágenes, cartelas y clips de vídeo,
incluidas las sustituciones manuales y los recursos de bibliotecas. El único
límite de duración del avatar es de 60 segundos por escena; necesita su narración.
El presentador aparece en un recuadro superior derecho
sobre la ilustración, conservando la narración y los subtítulos.

En el **previsualizador de Imágenes** se preparan los clips y aparece el mismo
avatar que se utilizará al montar. **Reproducir** sincroniza sus
labios con el reloj de la narración; **Parar** detiene también el avatar. Durante
la preparación se muestra el progreso y se puede parar o continuar tras un error.
Los clips completados se conservan y el montaje los reutiliza sin volver a
solicitarlos a Boson. La consulta de la previsualización no genera contenido:
la preparación se solicita como un trabajo aparte desde la pantalla.

En la pestaña **Avatar** del editor puedes añadir apariciones del avatar,
aunque la escena no esté entre las elegidas automáticamente. **Eliminar bloque**
quita la aparición seleccionada; eliminar todas quita el avatar de esa escena.
Requiere tener configurado el retrato y la voz en el encargo. Las cartelas y los
clips no bloquean el avatar: conservan sus animaciones y movimiento mientras el
presentador se superpone con sus propios intervalos y posición.

A la izquierda elige su entrada: **Sin animación**, **Fundido suave**, **Desde la
izquierda**, **Desde la derecha** o **Desde abajo**. El selector **Animación de
salida** permite elegir independientemente **Sin animación**, **Fundido suave**,
**Hacia la izquierda**, **Hacia la derecha** o **Hacia abajo**. Arrastra el avatar sobre la
imagen para **cambiar su posición**. Debajo aparece la **línea de tiempo**, con la
forma de onda y la voz de la escena: mueve el bloque del avatar o sus extremos
para elegir cuándo aparece y desaparece. También puedes escribir los segundos
de inicio y final. **Reproducir** permite comprobarlo con la narración. Los labios
siguen el tiempo real de la frase, aunque el avatar aparezca a mitad de ella.

Si su clip aún no está preparado, **Generar avatar con Boson** lo prepara para
el borrador. Pulsa **Guardar** para aplicar la posición, la entrada, la salida y el intervalo
a esta escena y al montaje final; **Deshacer** permite recuperar los ajustes anteriores.
Editar estos ajustes reutiliza el clip: no vuelve a solicitarlo a Boson ni
modifica las imágenes, la voz o los tiempos de la escena.

**Aplicar posición a escenas posteriores** copia la posición actual del avatar a
todos los avatares existentes en las escenas siguientes. La escena actual y las
anteriores se conservan; las escenas sin avatar se ignoran. Solo cambia la
posición, manteniendo la imagen, el tamaño, las animaciones y los intervalos de
cada avatar. Pulsa **Guardar cambios** para conservar el resultado; también
puedes deshacer o descartar los cambios desde el editor.

Boson AI factura estas animaciones por uso; generar el retrato consume también
el método de imágenes elegido. Los MP4 y los identificadores de trabajo remoto
se guardan en `avatar/` para retomar sin volver a encargar clips completados.
Cambiar la imagen o la voz genera los clips correspondientes de nuevo. El avatar
viaja al duplicar o exportar el vídeo. Abrir proyectos anteriores no lo activa.

### Elegir las cartelas animadas del montaje

En **Motion animation**, tanto en el estilo como en el encargo, puedes elegir
también las diez **cartelas sobre imagen**: La cifra, La cita, La frase que cae,
La lista, Lo uno contra lo otro, La pregunta, La palabra, La portada de capítulo,
Las fechas y El remate. Cada tarjeta muestra una vista previa animada; púlsala
para pasarla entre **Disponibles** y **Se usarán al montar**.

Los vídeos nuevos parten sin cartelas, salvo las que elijas o hereden del estilo.
Solo se planifican las elegidas cuando la narración ofrece contenido adecuado.
Los vídeos anteriores conservan su selección histórica al abrirse; puedes quitar
las cartelas que no quieras y **volver a montar** para aplicar el cambio.
Esto solo rehace las capas y el montaje, sin regenerar guion, voz ni imágenes.
En el mismo recuadro, **Color de acento** abre una paleta para elegir el color de
líneas, etiquetas y detalles de animaciones y cartelas. Sin elección se conserva
el color anterior. El estilo lo transmite a vídeos nuevos; en uno existente,
cambiarlo solo requiere volver a montar las capas y el vídeo, sin regenerar
guion, voz ni imágenes.
En un vídeo ya generado, volver a activar una cartela recupera las escenas que
tenían ese contenido planificado. Las animaciones del guion conservan su selección
independiente dentro de la misma sección.

### Taller de Remotion: plantillas React adicionales

En **Imágenes → Plantillas Remotion**, el editor muestra tres columnas: la
biblioteca de plantillas, el previsualizador con el timeline y el taller de código
y propiedades. El taller empieza contraído: pulsa **Taller de Remotion** para
desplegarlo o contraerlo. Seleccionar plantillas o bloques no lo abre automáticamente.
Incluye doce ejemplos editables, como Título Cinematográfico,
Lower Third, Línea de Tiempo y gráficos. Este taller es adicional al catálogo de
Motion animation.

Instala su motor local con **Node >=22** desde la raíz del programa:

```bash
npm ci --prefix motores/remotion
```

Los instaladores `instalar_dependencias.sh` y `instalar_dependencias.ps1`
también instalan estas dependencias si Node >=22 y npm ya están disponibles.
Si acabas de instalar Node, abre una consola nueva antes de ejecutarlos.

El frontend principal no necesita build. Las dependencias de React/Remotion
pertenecen únicamente al motor de `motores/remotion/`. Remotion reutiliza el
navegador local del estudio; `ESTUDIO_REMOTION_BROWSER` permite elegir otro.
El render se ejecuta en la máquina del servicio Python: si abres un servidor
desde otro ordenador, renderiza ese servidor.

1. Selecciona un ejemplo o pulsa **Nueva plantilla**.
2. Introduce un componente JSX/TSX con **`export default`**. Están disponibles
   `react` y `remotion`; los imports de ficheros propios y de otros paquetes
   requieren ampliar el motor. Usa `useCurrentFrame`, `interpolate` o `spring`
   para que el movimiento siga los fotogramas, y pasa los datos mediante props.
3. Ajusta **Props**, duración, resolución y FPS. Puedes editar las propiedades
   existentes o introducir un objeto JSON completo.
4. Elige **Modo de aplicación**, debajo del código: **Superponer animación**
   añade una capa transparente; **Sustituir contenido visual** crea
   una composición completa, sin necesitar una imagen de fondo.
   **Compilar** prepara el reproductor y **Previsualizar** reproduce el componente.
   Los errores se muestran en el taller.
5. **Guardar plantilla** conserva una versión reutilizable en la biblioteca.
   Cada tarjeta tiene un menú **⋯** en la esquina superior derecha con **Eliminar
   plantilla**. La quita de la biblioteca, también si es uno de los ejemplos;
   los bloques ya insertados en vídeos conservan su copia y siguen funcionando.
   El menú también permite elegir **Superponer Animación** (por defecto) o
   **Sustituir contenido**. Una marca indica la selección: **Insertar en la línea
   de tiempo** aplica ese modo, también con el taller contraído. El selector del
   taller y el menú de la tarjeta se mantienen sincronizados.
6. **Aplicar al timeline** o **Insertar en la línea de tiempo** abre un popup con
      las props específicas de la animación y su duración. Ajusta sus valores y
      pulsa **Guardar** para preparar sus fotogramas y añadir un bloque libre en
      la pista **Remotion**, desde el cursor. **Cancelar** descarta los ajustes
      del popup sin insertar la animación.
     Conserva la duración de la plantilla hasta el final del vídeo: puede atravesar
     varias escenas sin cortarse ni reiniciar su animación.
     El progreso, por ejemplo **Renderizando Remotion · 53 %**, aparece también
     junto a Insertar, aunque el taller esté contraído.
7. Ajusta los tiempos arrastrando el bloque o sus extremos. Moverlo conserva la
   previsualización y adapta su reloj al nuevo inicio, sin volver a renderizar.
   Al cambiar su duración desde los extremos, la muestra se prepara automáticamente.
   Pulsa un bloque
    para recuperar su código y props en el taller. Haz doble clic sobre el bloque
    para abrir el popup y editar sus props; **Guardar** actualiza ese mismo bloque.
    Al pasar el cursor por el bloque se muestra la indicación de doble clic.
8. **Guardar cambios** conserva los bloques del vídeo; **Montar el vídeo** los
     compone con las capas actuales. **Parar Remotion** cancela un trabajo local.

Pincha sobre la animación Remotion en el previsualizador y arrástrala para cambiar
su posición desde cualquier pestaña del editor. Con la reproducción parada,
un recuadro discontinuo **↔ Arrastrar** muestra la zona de agarre: puedes pinchar
en cualquier punto de su interior, incluidos los huecos entre letras o formas.
La zona incluye un margen alrededor y un tamaño mínimo para elementos pequeños.
Se mueve el conjunto de
la plantilla; **Deshacer** recupera la posición anterior y **Guardar cambios**
la conserva para la previsualización y el montaje, también si atraviesa varias
escenas. Moverla reutiliza los fotogramas preparados.

Para eliminar un bloque, arrástralo a la **papelera de la esquina superior derecha
del timeline** y suéltalo cuando se ilumine. **Deshacer** permite recuperarlo;
**Guardar cambios** conserva la eliminación. Los tiempos se ajustan directamente
en la pista, sin un panel adicional de bloques.

En el modo de sustitución, **Salida y renderizado** parte de la resolución y FPS
del proyecto y conserva la duración de la plantilla. Puedes ajustar ancho, alto, FPS y
duración, y pulsar **Renderizar vídeo (MP4)**. El porcentaje y **Parar Remotion**
permiten seguir y cancelar el trabajo. El MP4 queda guardado en `remotion/renders/`
del proyecto. **Aplicar al timeline** prepara los fotogramas de la animación y la
incorpora al borrador; **Guardar cambios** la conserva en el montaje.

Los bloques azules de **Sustitución** y los morados de **Superposición** tienen
intervalos ajustables en el timeline completo. Arrástralos a cualquier posición,
incluso a escenas anteriores o posteriores, y ajusta la duración desde sus extremos.
Una sustitución reemplaza la imagen durante su intervalo;
fuera de él reaparece el contenido original. Las sustituciones guardadas con el
formato anterior conservan su MP4 de escena hasta que edites su intervalo.
Seleccionar el bloque recupera código, propiedades y modo.
Eliminarlo recupera el contenido visual anterior, sin borrar imágenes ni vídeos.
La animación sigue el reloj de narración y termina al alcanzar el final de su
bloque. Cambiar código, props o salida crea otro recurso por
huella al renderizar/aplicar; el montaje prepara automáticamente los recursos pendientes.

Para usar imágenes existentes, introduce en Props referencias relativas como
`{"imagen":"proyecto://pasos/assets/v1/escenas/S001.png"}` y muestra esa propiedad
con `<Img src={imagen} />` (importa `Img` desde `remotion`). Se admiten PNG, JPEG,
WebP y GIF de hasta 20 MiB por imagen, también en listas y objetos de props.
La previa y el render reciben los mismos recursos; sus contenidos participan en
la caché. Las plantillas guardan también el modo elegido para reutilizarlo.

**Galería Animada** recibe tres imágenes (`imagen1`, `imagen2`, `imagen3`). En
**Props**, cada **Foto** permite elegir una imagen del proyecto o subir un PNG,
JPG o WebP, y muestra su miniatura. Compila para ver las fotografías dentro de
los tres marcos animados; las subidas se conservan dentro del proyecto.

Las composiciones se incorporan sin audio propio: narración, música y efectos
siguen usando sus pistas del editor. El recurso conserva el orden de los bloques,
en modo superposición se pinta sobre las capas gráficas de la escena y debajo del avatar, antes de las
transiciones. Conserva la proporción y el tamaño relativo de su composición al
adaptarse al formato de la escena. El montaje prepara automáticamente los
fotogramas que falten.

La biblioteca vive junto a la carpeta de proyectos, en `plantillas_remotion/`, o
en **`ESTUDIO_REMOTION`** si está definido. Cada vídeo guarda una instantánea
inmutable del código utilizado dentro de `remotion/`: editar la biblioteca no
cambia los vídeos anteriores. Esa carpeta viaja al duplicar o exportar el vídeo.
Compilaciones y fotogramas se reutilizan por huella de contenido; guardar estos
bloques solo afecta al render de las escenas correspondientes, incluidas todas
las que atraviesa su intervalo anterior o nuevo.

Verificación aislada: `python pasos/prueba_remotion.py`; con `--real` comprueba
el taller en Chromium, compila React, prepara PNG con transparencia y genera un
clip real con el motor actual. Requiere Playwright, navegador y ffmpeg.

### Editar o crear una animación en una escena

En **Imágenes** se abre directamente el **editor global del vídeo**. El panel
izquierdo reúne **Imágenes**, **Animación**, **Sonidos**, **Efecto Parallax**,
**Transición** y **Avatar**. A la derecha están el previsualizador y el timeline
de todas las escenas consecutivas, con siete pistas: **Bloques**, **Audio**,
**Remotion**, **Animación**, **Sonidos**, **Avatar** y **Transición**.

Seleccionar una miniatura lleva el cursor a su escena; seleccionar un bloque
del timeline abre su escena y la pestaña correspondiente. Puedes buscar un
instante en las pistas y ampliar el timeline con su control de zoom. El botón
**Reproducir** continúa por las escenas siguientes con narración, música y los
sonidos del borrador. Ya no hacen falta «Editar escena», «Oírla», «Todo seguido»
ni los botones de anterior y siguiente. **Montar el vídeo** está en la cabecera,
debajo de **Guardar cambios**, con un punto rojo a su izquierda.

**Añadir bloque** incorpora un elemento a la pista seleccionada. Puedes tener
varios bloques independientes: pulsa uno para editarlo en el panel izquierdo,
arrástralo para desplazarlo o tira de sus extremos para ajustar su intervalo.
También puedes escribir el inicio, el final y la duración en segundos. Los
bloques quedan dentro de la escena, excepto **Remotion**, que puede atravesar
cualquier número de escenas; si se solapan se muestran en carriles dentro
de su pista. La narración conserva su reloj y su duración originales.

Cada escena conserva su borrador al seleccionar otra. **Guardar cambios** y
**Ctrl/Cmd+S** aplican las escenas modificadas; **Deshacer** y **Ctrl/Cmd+Z**
recuperan cambios entre escenas y pestañas. Guarda antes de montar el vídeo.
**Descartar cambios** recupera los ajustes guardados de todas las escenas.
Abrir el editor no escribe parámetros ni genera contenido. La regresión de
navegador se ejecuta con `python pasos/prueba_editor_global.py --real`.

Las escenas cargadas y los borradores sin guardar se conservan automáticamente
en **este navegador**, mediante IndexedDB. Al recargar la página o volver a
**Imágenes**, se recuperan las escenas locales y solo se solicitan las pendientes
o las que hayan cambiado. La previsualización general se consulta para comprobar
las revisiones; las imágenes, los clips y el audio mantienen su carga habitual.
Guardar sigue siendo necesario para aplicar los cambios al proyecto y al montaje.
Si una escena cambió en el servidor, el borrador anterior se conserva aparte:
puedes descargarlo y, si mantiene el mismo texto y tiempos, recuperar sus cambios.
Si borras los datos del sitio o usas otro navegador, esa copia local no estará disponible.

En la pestaña **Animación** puedes
corregir sus textos y cambiar el tipo por cualquiera de las **18 opciones** del
catálogo: las ocho animaciones del guion y las diez cartelas sobre imagen.
Los campos se adaptan al tipo: cifra y etiqueta, fecha y contexto,
título y explicación, frase, comparación, lista o cronología. En **La lista** y
**Las fechas**, escribe entre dos y cuatro entradas, una por renglón.
El editor reconoce también las cartelas automáticas que ya tenga la escena;
puedes corregirlas, sustituirlas o quitarlas con **Eliminar bloque**.

Si la escena no tiene animación, pulsa **Añadir bloque**. Elige un tipo,
edita su contenido y pulsa **Guardar cambios**. La vista previa muestra el borrador mientras editas.
Cambiar de escena conserva los cambios que todavía no hayas guardado.
Haz clic sobre cualquier parte de la animación y **arrástrala** para cambiar
su posición: el recuadro, los textos, las imágenes y las formas se mueven juntos
como una única unidad. El botón **↶ Deshacer** o **Ctrl+Z** (**Cmd+Z** en Mac)
recupera progresivamente los estados anteriores del editor: posiciones, textos,
duración, tipo e imágenes. Cada arrastre completo cuenta como un solo cambio.
El historial dura durante la sesión del editor; deshacer también permite
recuperar un estado anterior a Guardar, que debe guardarse de nuevo para aplicarlo.
El campo
**Duración (segundos)** permite ajustar el tiempo total de la animación, incluidas
sus entradas y salidas, entre **0,1 s** y la duración de la escena; vacío conserva
el tiempo automático. No cambia la duración de la escena ni de la narración.
Las posiciones y la duración se aplican al pulsar **Guardar**, se conservan al
reabrir el editor y se utilizan en el montaje final.
Debajo del visualizador, la **línea de tiempo** muestra la forma de onda de la
voz y el bloque de la animación. Pulsa **Reproducir** para oír la narración y
seguir el cabezal, o pulsa sobre la pista para elegir un instante y ver ese
fotograma. Arrastra el bloque para cambiar su inicio y tira de sus extremos para
ajustar el comienzo o el final; se muestran los tiempos de inicio, fin y duración.
El bloque no puede salir de la escena. Estos ajustes forman parte del borrador:
**Guardar cambios** los aplica a la previsualización y al montaje.
Para quitarla, pulsa **Eliminar bloque** y **Guardar**. Si eliminas todas, la escena queda
sin animación también al volver a montar, aunque antes tuviera una automática.
En **Tipografía cinética**, el campo **Subrayado**, debajo de **Frase**, permite
elegir las palabras resaltadas. Sepáralas con espacios o comas: se resaltan todas
las coincidencias de palabras completas, sin distinguir mayúsculas y sin que la
puntuación afecte. Las palabras que no estén en la frase se ignoran; vacío no
resalta ninguna. Los proyectos anteriores conservan su resaltado al abrirse.
Si unes dos palabras con un guion en **Subrayado** (por ejemplo, `Canis-lupus`),
una sola banda resalta ambas palabras consecutivas, incluido el espacio entre ellas.
En **Comparación de tarjetas**, encima de cada etiqueta aparecen **Imagen izquierda**
e **Imagen derecha**. Arrastra una imagen o pulsa en la zona para elegirla. El
**Collage con título** ofrece las mismas dos zonas encima del título. Se admiten
**PNG, JPG y WebP**, hasta **20 MiB** por imagen; se muestra una miniatura antes
de guardar. Puedes sustituir una o ambas tarjetas y volver con **Usar imagen
automática**. Las sustituciones se aplican al pulsar **Guardar**.

Las escenas con **Collage con título** o **Comparación de tarjetas** obtienen
**dos imágenes propias y exclusivas**, en lugar de una. Ninguna tarjeta toma
la imagen de una escena anterior o posterior, y la imagen adicional no se usa
como plano en otro momento del vídeo. La comparación prepara cada imagen para
el elemento de su etiqueta; el collage prepara dos composiciones complementarias.
Las dos se conservan al retomar una tanda y cuentan en el progreso de imágenes.
Si asignas una de estas animaciones a una escena que aún solo tiene una imagen,
genera las imágenes de esa escena antes de montar, o sube la segunda tarjeta.
Estas subidas no sustituyen el fondo de la escena ni regeneran recursos; se
conservan al duplicar, exportar e importar el vídeo.

Los cambios de texto y las subidas se conservan al reabrir el vídeo y se aplican
al **volver a montarlo**, sin regenerar narración ni imágenes. Abrir el editor
no modifica el proyecto.
La asignación manual queda vinculada al texto de la escena para no reutilizarla
por error si ese identificador pasa a representar otra frase.

### Incluir o quitar los subtítulos

Al crear o editar un **estilo**, debajo de **Ritmo** aparecen **Subtítulos** y
**Efectos**. Sus selecciones se guardan en el estilo y se copian al encargo de
cada vídeo nuevo que crees con él. Puedes ajustarlas después para ese vídeo.
Por ejemplo, un estilo sin subtítulos y con solo **Fundido** dará vídeos nuevos
con esas mismas opciones. Los cambios del estilo se aplican a los vídeos futuros.

En **Encargo → Subtítulos**, encima de **Efectos**, marca o desmarca
**Incorporar subtítulos al vídeo**. Están activados por defecto. La selección se
guarda por vídeo y se aplica al montar de nuevo, sin regenerar el guion, la voz
ni las imágenes. Las cartelas se conservan.

### Efecto parallax en imágenes estáticas

En crear/editar **estilos** y en el **encargo del vídeo**, activa **Efecto
parallax en imágenes estáticas**. El panel permite marcar **uno o varios movimientos**:
zoom hacia delante o atrás, paneo lateral, movimiento vertical, diagonal, órbita
suave o combinado. Se alternan de forma equilibrada entre las imágenes animadas,
usando solo los movimientos marcados y conservando el reparto al remontar.
Los ajustes antiguos de movimiento único siguen funcionando; el antiguo
«Movimiento aleatorio» aparece como todos los movimientos seleccionados al editarlo.
Puedes animar todas las imágenes, cada N imágenes (3, 6, 9… inicialmente)
o una selección aleatoria; e intensidad suave, media o alta en **Configuración
avanzada**. La selección aleatoria es reproducible y anima aproximadamente la
mitad de las imágenes. Los clips de vídeo y las cartelas sin imagen no cuentan.

Los estilos transmiten estas opciones a los vídeos nuevos. En un vídeo existente,
cambiarlas solo requiere **volver a montar**, conservando narración e imágenes.
DepthFlow estima la profundidad localmente y crea clips sin audio. Al abrir
**Imágenes**, prepara automáticamente los clips de las escenas seleccionadas:
se muestra el progreso y **Parar**, y cada imagen pasa a reproducirse como vídeo
en cuanto está lista. **Reproducir** sincroniza el movimiento con la narración.
Si hay otra generación activa, espera a que termine antes de preparar el parallax.
Puedes continuar una preparación detenida o reintentar un error desde esa pantalla.
Los clips se cachean en `parallax/` dentro del proyecto; el montaje reutiliza esos
mismos clips antes de componer las capas y transiciones habituales. Cambiar la
imagen, el movimiento o los tiempos prepara el clip correspondiente de nuevo.

En el panel izquierdo, pulsa **Efecto Parallax**
para configurar solo esa imagen. La pestaña permite activar o quitar el efecto,
elegir su **Movimiento de cámara** y cambiar la intensidad en **Configuración
avanzada**. Pulsa **Guardar cambios** para aplicarlo; cambiar de escena conserva el borrador.
La previsualización prepara el clip actualizado y el montaje usa esos mismos
ajustes. Quitar el efecto de una escena se conserva aunque el vídeo anime todas
las imágenes; también puedes activarlo solo en una imagen con la opción global
apagada. Las demás escenas, sus animaciones y la narración se conservan.

El motor es opcional y se instala en un entorno **separado** del servicio. En
Linux/macOS, `bash instalar_dependencias.sh` ya lo deja en `.depthflow`; en
Windows, `instalar_dependencias.ps1` hace lo mismo. A mano:

```bash
python3 -m venv .depthflow
.depthflow/bin/pip install -r requirements-depthflow.txt
export ESTUDIO_DEPTHFLOW_PYTHON="$PWD/.depthflow/bin/python"   # opcional
.venv/bin/python app.py --puerto 8020
```

En Windows:

```powershell
python -m venv .depthflow
.\.depthflow\Scripts\python.exe -m pip install -r requirements-depthflow.txt
$env:ESTUDIO_DEPTHFLOW_PYTHON = (Resolve-Path .depthflow\Scripts\python.exe).Path
.\.venv\Scripts\python.exe app.py --puerto 8020
```

El Estudio detecta automáticamente `.depthflow`; `ESTUDIO_DEPTHFLOW_PYTHON`
permite situarlo fuera del programa. Instalar DepthFlow descarga torch/CUDA y
ocupa varios GB; el servicio no lo necesita para arrancar. Requiere FFmpeg y un
contexto OpenGL headless funcional; la primera animación descarga el modelo de
profundidad y tarda más. Si falta el motor o falla, el montaje muestra el motivo
y puede reintentarse tras corregirlo. No se sustituye por un zoom plano.
Verificación offline: `python pasos/prueba_parallax.py`; prueba del motor con
estimación real y MP4: `python pasos/prueba_parallax.py --real`.

### Elegir las transiciones del vídeo

En **Efectos**, tanto en el estilo como en el encargo, pulsa las tarjetas para
mover las transiciones entre **Disponibles** y **Se usarán al montar**. Cada
tarjeta muestra un GIF del efecto, su nombre y descripción. Hay quince efectos. Los vídeos
nuevos parten de seis: fundido, destello blanco, fuga de luz, iris, zoom
desenfocado y latigazo. Puedes quitarlos y elegir cualquier combinación.

Si quitas todos, las imágenes se muestran secuencialmente con cortes directos,
sin transiciones. La selección se guarda por vídeo; cambiarla solo deja pendiente
el montaje, sin regenerar el guion, la voz ni las imágenes. En los vídeos existentes
se guarda automáticamente al mover las tarjetas.

En **Imágenes → Transición**, **Hacia la siguiente escena** configura
la salida de la escena actual hacia la siguiente. Ofrece la lista de
efectos y **Sin transición**. Al elegirla,
la vista previa reproduce el efecto entre el último fotograma de la
escena actual y el primero de la siguiente, con sus imágenes o clips reales.
**Probar transición entre escenas** permite repetirla. Con **Añadir bloque**
puedes incorporar además varias entradas desde negro y salidas a negro, con el
mismo catálogo de efectos, sincronizadas en la pista **Transición**.
La transición hacia la siguiente escena también aparece en esa pista: es el
bloque con la flecha **→**. Púlsalo para cambiar el efecto, ajustar sus segundos o
eliminarlo. Arrastra el bloque para desplazarlo y sus extremos para cambiar la
duración; también puedes escribir inicio, final y duración en el panel. Al
recorrerlo con el cursor o reproducir la narración, el visualizador muestra el
progreso real del efecto. Al terminar, conserva el primer cuadro de la siguiente
escena hasta llegar al corte. Guardar aplica ese mismo intervalo al montaje.
Elegir **Sin transición** retira ese bloque; las entradas y salidas
a negro mantienen sus intervalos independientes.
Pulsa **Guardar cambios** para aplicar la selección; cambiar de escena conserva el borrador.
La última escena no tiene transición de salida. La selección se conserva al
reabrir y se aplica al volver a montar, sin regenerar guion, voz ni imágenes.

### Listo para YouTube

Al terminar la receta de montaje se preparan el **título**, la **descripción**
y una **miniatura específica generada con IA**. En la pantalla **Vídeo**, debajo
del reproductor, se pueden editar los textos (se guardan solos), copiarlos y
descargarlos junto con la miniatura JPEG de 1280 × 720. Los vídeos que ya estaban
montados tienen el botón **Preparar para YouTube**.
La miniatura se diseña como una portada editorial: ilustración protagonista,
titular corto y grande integrado y, cuando aporte contexto, una línea de apoyo.
Conserva el estilo del canal y debe leerse al tamaño de una tarjeta de YouTube.

Los textos usan Claude y la miniatura el motor de imágenes configurado: consume
una imagen adicional, con la previsión de coste o cuota indicada en pantalla.
Los capítulos, cuando el relato los admite, usan los tiempos reales de los
bloques. Los datos viven en `publicacion/youtube.json`, fuera de los params del
montaje: editarlos o regenerar solo la miniatura no vuelve a montar el MP4.
Si cambia el guion, los tiempos o el estilo, se avisa para revisarlos sin
sobrescribir lo editado. Un fallo al preparar YouTube no invalida el vídeo y se
puede reintentar por separado. La subida a YouTube sigue siendo manual.

### Importar y exportar el guion

Los guiones nuevos se montan con **una frase completa por escena**. Cada frase
empieza por mayúscula y termina en punto. Una coma no provoca un cambio de
escena, y dos frases cortas tampoco se unen en una sola imagen. El ritmo se
ajusta escribiendo frases más breves: si una frase resulta larga, el montaje la
conserva entera aunque supere la duración objetivo del plano. Los cortes siguen
las marcas reales de la voz; la narración se mantiene como una pista continua.

La regla se conserva al revisar o regrabar la voz. Los proyectos con un guion
anterior mantienen sus cortes; para adoptar el criterio nuevo hay que regenerar
el guion y sus pasos dependientes.

En la fase **Guion**, **Exportar guion (.txt)** descarga el texto actual,
incluidas las correcciones manuales. Cada bloque ocupa un párrafo, separado del
siguiente por una línea en blanco, sin título ni numeración.

Para revisarlo fuera del Estudio, conserva **el mismo número de párrafos y su
orden**: cada párrafo vuelve al bloque de escenas que ocupaba esa posición.
**Importar guion (.txt)** comprueba esa estructura antes de guardar; si el número
no coincide, muestra el error sin aplicar cambios. Los saltos de línea dentro de
un párrafo se consideran espacios. Usa texto UTF-8.

La importación sustituye solo los textos modificados y conserva los ids de los
bloques. No genera contenido ni consume cuota: el audio se actualiza después
desde los controles habituales. Exportar y volver a importar sin editar conserva
también las pausas de locución originales.

### Shorts del vídeo completo

Con el MP4 montado, **Generar shorts** abre una fase independiente, accesible
también desde **Shorts** en la barra inferior. Elige una duración mínima y una
máxima en segundos (rango técnico 1–180; recomendado 20–60). YouTube admite
Shorts verticales o cuadrados de hasta tres minutos. El rango tiene que permitir
un fragmento central y una apertura y un cierre con sentido; no se cortan frases
ni se añade negro para hacerlo encajar.

Claude elige un fragmento continuo con gancho y adapta solo la primera y la
última escena. El centro conserva su guion y su audio, y se reutilizan las
ilustraciones existentes. Las dos frases nuevas se locutan con la misma voz
de Cartesia (hasta 550 caracteres por selección; coste indicado antes de pulsar).
No se llama al generador de imágenes. El montaje local produce un MP4
**1080 × 1920**, con las ilustraciones completas sobre un fondo adaptado y
subtítulos sincronizados para vertical.

Cada Short queda guardado en `shorts/<id>/`, con el fragmento elegido, su motivo,
la apertura, el cierre y una copia de las fuentes de esa versión del vídeo.
Puedes reproducirlo, descargarlo, generar otros o reintentar uno interrumpido;
la voz ya generada se cachea para no volver a pagarla al reintentar un montaje.
El trabajo continúa con el navegador cerrado. No cambia las firmas, las versiones
ni los archivos del vídeo largo. Al subirlo a YouTube, selecciona el vídeo
completo como **vídeo relacionado** para dar destino a la invitación final.

Si hay cambios pendientes, la fase ofrece **Descartar cambios pendientes y generar
short**. Esta acción explícita recupera los parámetros y las versiones que
corresponden al último MP4, descarta las notas pendientes del repaso y aparta el
trabajo sin completar. Conserva una copia en `shorts/_descartados/<id>/` antes
de restaurar, comprueba que las firmas coinciden con el montaje y genera el
Short sin remontar el vídeo largo. Abrir la pantalla no descarta nada.

### Lo que hace falta tener

| Qué | Para qué | Si falta |
|---|---|---|
| Python 3.12 con `fastapi`, `uvicorn`, `Pillow`, `numpy` | el servicio | no arranca |
| **ffmpeg** y **ffprobe** | la voz, la música y el MP4 | los pasos que los usan lo dicen |
| **Microsoft Edge** (o Chrome) | rasterizar cada plano | igual |
| Las **fuentes** de los subtítulos y las cartelas | medir y dibujar el texto | ver el aviso de `motores/README.md` |
| **DepthFlow** en `.depthflow` *(opcional)* | el efecto parallax | el vídeo sale sin parallax |
| El **CLI de Claude**, con sesión | el guion, el catálogo visual, los rótulos | no hay vídeo |
| **Codex CLI** con sesión de ChatGPT y/o **OpenAI API Key** | imágenes con cuota del plan o API por uso; ordenables como principal y respaldo | hace falta al menos un método disponible para generar imágenes |
| Una **clave de Cartesia** | la voz | no hay vídeo |
| Las de **Jamendo** y **FreeSound** | música y efectos | el vídeo sale sin ellos; son las únicas prescindibles |

#### Claude se queda en «comprobando el código» al entrar

Mantén actualizado el CLI de Claude. En Windows se reprodujo con **2.1.123**
un fallo por el que el CLI mostraba el enlace de acceso, pero no respondía al
código enviado desde el Estudio: la comprobación agotaba los 120 segundos de
espera. El usuario confirmó que el acceso funcionó tras actualizar y reiniciar.
El contrato de este flujo está documentado como probado con **2.1.241**;
no se ha determinado la versión mínima que lo resuelve.

Si ocurre, detén el servidor con **Ctrl+C** y ejecuta:

```powershell
claude update
claude --version
.\.venv\Scripts\python.exe app.py --puerto 8020
```

El último comando usa el entorno virtual local; si arrancas sin él, usa
`python app.py --puerto 8020`. Después pulsa **Entrar** de nuevo en la web y
utiliza el enlace y el código del nuevo intento.

También se corrigió un error del Estudio al pulsar **Dejar** durante la
comprobación: la petición pendiente consultaba un proceso que la cancelación ya
había eliminado (`AttributeError: 'NoneType' object has no attribute 'poll'`).
Ahora esa cancelación devuelve un error de acceso controlado e impide confirmar
la cuenta desde la petición cancelada.

#### Un agente termina sin escribir `salida.json`

En Windows, la carpeta temporal puede usar el nombre abreviado del usuario
(`C:\Users\VALENT~1\...`). Se comprobó con Claude CLI **2.1.317** que su
comprobación de permisos bloqueaba `Write` en esa ruta, aunque el proceso usara
`acceptEdits`. El agente terminaba pidiendo aprobación manual y el Estudio solo
mostraba «no ha escrito salida.json (no dejó nada)». Esto podía detener las
cartelas antes de generar ninguna imagen, independientemente del número de planos.

El Estudio resuelve ahora las rutas completas antes de lanzar el agente y le
indica la ruta absoluta de entrega. Si aun así falta el fichero, el error incluye
la explicación del agente y las herramientas cuyo permiso se denegó. Actualiza
el Estudio y reinicia el servicio para aplicar la corrección; no hace falta
desactivar los permisos del CLI ni volver a generar el guion o la voz.

### Aceleración del montaje local

El montaje detecta **H.264 NVENC** con una codificación real y lo utiliza si está
disponible; en las demás máquinas utiliza x264 por CPU. En Windows permite la
aceleración gráfica de Edge para WebGL. El rasterizado de SVG y la composición
de las capas se mantienen por software para que las cartelas y el zoom salgan
iguales en serie y en paralelo.

Las capturas PNG siguen siendo sin pérdida, con compresión rápida y sin una
validación redundante de los datos base64 en la conexión local con el navegador.
Normalmente se entregan a FFmpeg por una tubería: en cortes secos se codifica
mientras se captura; en transiciones solo se guardan los PNG que necesita WebGL
y el resto va a un archivo temporal secuencial. `conservar_frames` mantiene el
camino de diagnóstico con todos los PNG.

El codificador se conserva al rehacer planos sueltos. Un montaje completo puede
elegir NVENC; los planos que se reutilizan de un montaje anterior mantienen su
codificador. Estas mejoras se aplican después de reiniciar el servicio, sin
cambiar los parámetros guardados ni regenerar voz o imágenes.

Para medir con un hyperframe real, sin modificar proyectos ni llamar a IA:

```powershell
python pasos/medir_render.py --fotogramas 60 --reparto --procesos 6,8
```

El informe identifica el dispositivo WebGL efectivo y el codificador. Compara
solo cantidades de procesos que quepan en la memoria libre; el montaje sigue
limitando automáticamente su paralelismo según la RAM. Las mediciones cortas
incluyen arranque de procesos y no son una promesa del tiempo del vídeo entero.

### Fuentes y motores locales

En Linux local, las fuentes se resuelven con **Fontconfig** (`fc-match`) por la
misma familia y peso que utiliza el navegador. `ESTUDIO_FUENTES` sigue teniendo
prioridad para las instalaciones con una carpeta de fuentes preparada; si la
configuras, debe contener los ficheros esperados, no una carpeta vacía.
Para el render se reconoce también el Chrome instalado por Playwright en Linux;
`ESTUDIO_EDGE` permite elegir un ejecutable concreto.

Para **Claude**, instala el CLI oficial:
```bash
npm install -g @anthropic-ai/claude-agent-sdk
```
Luego haz login con tu cuenta de Anthropic:
```bash
claude login
```

Para las imágenes, instala el CLI oficial con `npm install -g @openai/codex`
(probado con **0.165.0**) y conecta ChatGPT en la guía de inicio o en
**Configuración → ChatGPT / Codex CLI**. También reconoce una sesión
ya abierta con `codex login`. El acceso desde la web usa un código de dispositivo:
se introduce en la página de OpenAI, no se pega ningún token en el Estudio.
Si OpenAI lo solicita, activa el acceso por código de dispositivo en la seguridad
de tu cuenta de ChatGPT.

Codex genera las imágenes con `gpt-image-2` y consume los límites de Codex de tu
plan, sin cargos de la API de imágenes. No es una cuota ilimitada. Calidad y
tamaño se solicitan al agente; el PNG se normaliza
al tamaño que espera el motor de vídeo.

Tanto **Configuración** como la **guía de inicio** muestran dos recuadros
verticales: **ChatGPT / Codex CLI** (conectar, cambiar de cuenta y comprobar
sesión) y **OpenAI API Key** (introducir, guardar y validar una clave). La
validación comprueba la autenticación sin generar imágenes; el saldo de API
solo se confirma al generar.

Las flechas **↑ / ↓** intercambian los recuadros y guardan la prioridad al
instante, compartida por toda la instalación. El superior es el principal y
el inferior el respaldo automático: si el primero falla, no está disponible,
agota su cuota/saldo o tiene errores de autenticación, se intenta el segundo
para la misma imagen pendiente. Esto funciona en ambos sentidos. **La API
factura por uso cuando entra en funcionamiento**, también como respaldo de
Codex. Si ninguno puede generar, se conservan ambos diagnósticos y se aplica
la recuperación de incidencias descrita abajo. Las imágenes ya hechas no se repiten.

La herramienta admite **cinco imágenes de referencia por petición**. Si un
plano necesita más, el adaptador conserva las primeras cuatro y agrupa las
restantes en una lámina etiquetada; el encargo explica la correspondencia sin
descartar referencias. Un exceso de adjuntos no es un agotamiento de cuota.

Dentro de una tanda se procesan hasta **dos imágenes independientes a la vez**,
manteniendo el orden de continuidad de cada secuencia. Se reutilizan los
procesos de Codex, pero cada imagen abre un hilo nuevo. Para ir en serie fija
`ESTUDIO_CODEX_CONCURRENCIA=1` (el máximo admitido es 2).

Cada intento guarda un diagnóstico acotado en
`<ESTUDIO_SECRETOS>/codex_imagenes/<id>.json`: motivo, estado del turno,
referencias agrupadas y tiempos, sin el prompt ni credenciales. Ante una
respuesta incompleta se consulta el **mismo turno** para recuperar su imagen,
incluida la salida nativa en base64, sin repetir la generación. Los errores
distinguen cuota, sesión, rechazo, referencias y respuesta incompleta. Los
límites generales que devuelve Codex no garantizan cuota de imágenes.

La sesión se guarda y renueva mediante el propio CLI (`CODEX_HOME` o `~/.codex`).
`ESTUDIO_CODEX_HOME` permite aislarla por instalación y `ESTUDIO_CODEX` indicar
el ejecutable. Usa la misma variable para un login manual y para el servicio.
En instalaciones que ya tenían una clave se conserva la API como principal;
las nuevas sin clave empiezan con Codex. Cambiar el orden o iniciar sesión no
modifica firmas ni regenera imágenes hechas. Cambiar de cuenta no altera el orden.

### Incidencias de imágenes: recuperación y correo

Los fallos temporales de saturación, servicio, conexión o tiempo de espera, y
las entregas incompletas o interrumpidas de Codex, se reintentan automáticamente
**en la imagen pendiente**, conservando las ya
resueltas. La espera predeterminada es 60, 120, 240 y luego 300 segundos entre
intentos, hasta que se recupere el servicio o se pulse **Parar**. La barra
enseña la espera y el nuevo intento sin avanzar el contador de imágenes por
reintentar. El trabajo permanece activo, también entre peticiones, aunque otra
cadena siga generando planos. **Generar imágenes** y **Continuar imágenes** solo
aparecen cuando la tanda ha terminado o se ha detenido de verdad; mientras está
activa se ofrecen el progreso y **Parar**. Durante la incidencia no se muestra
una cuenta atrás de finalización, porque no se sabe cuándo volverá el servicio.
Primero se intenta el otro método configurado; si ninguno resuelve la imagen,
los errores no recuperables se notifican y se detienen para corregir su causa.
No se generan imágenes de prueba. Los rechazos de contenido siguen el circuito
de revisión, sin reenviar el mismo encargo al otro proveedor.
Los límites renovables de **ChatGPT/Codex**, cuando la API tampoco puede generar,
mantienen la tanda en espera: la barra
indica «Uso de ChatGPT no disponible» y el tiempo hasta la siguiente comprobación.
Si Codex indica que el uso general sigue bloqueado, solo se consultan sus límites,
sin abrir un turno de generación. Cuando vuelve a estar permitido, se solicita la
imagen pendiente y continúa la tanda. Esto no reintenta errores de saldo o
facturación de una API de pago.
Los intervalos y la activación se pueden cambiar en **Configuración →
Incidencias de imágenes · reintentos y correo**, sin modificar los proyectos.

Ante un **rechazo de seguridad de Codex en un plano**, el Estudio pide a Claude
una única **alternativa visual segura**: sustituye realmente la acción por otra
inocua que comunique la misma intención general. Por ejemplo, mirar las manos
con asombro en lugar de pellizcarse. No se buscan variantes del mismo contenido
bloqueado para superar el filtro. La barra indica que se está preparando la
alternativa y se solicita una imagen con su nuevo prompt.

Se guardan el motivo, la dirección o **guion visual** y el prompt efectivo junto
a la imagen y en el plan del vídeo. La decisión se conserva también si después
hay un timeout, falta de cuota o se reinicia el servicio; al continuar no se
vuelve al prompt rechazado ni se reescribe el plano otra vez. La caché conserva
la descripción efectiva junto a la imagen. Las demás imágenes se mantienen.

El **texto narrado, la voz y los tiempos no se cambian** automáticamente. Si no
existe una alternativa coherente sin modificarlos, o también se rechaza la nueva
imagen, el plano requiere revisión y la tanda se detiene. No hay un bucle de
reformulaciones. Cambiar la dirección del plano permite partir de un encargo
nuevo. La preparación de la alternativa usa la sesión de Claude y la petición
de imagen usa la cuota de ChatGPT del modo habitual.

En ese mismo bloque se configuran los avisos de **Gmail**: cuenta, contraseña
de aplicación de Google, remitente y destinatario. El servidor predeterminado
es `smtp.gmail.com:465` con SSL; se puede usar otro SMTP con SSL o STARTTLS.
**Enviar correo de prueba** guarda los datos y realiza un envío real. Las
credenciales viven en `<ESTUDIO_SECRETOS>/avisos_correo.json`; la contraseña
nunca se devuelve al navegador.

Se envía un aviso por incidencia y otro al recuperarse, no uno por cada sondeo;
si durante la espera aparece un error que exige intervención, se avisa de la detención.
Con el mismo correo activado se envían también dos avisos de finalización:
**imágenes listas para montar el vídeo**, cuando termina la tanda completa, y
**vídeo disponible**, en cuanto se ha guardado el MP4, sin esperar a preparar
los datos de YouTube. No se avisa por generar solo personajes o retocar una
imagen aislada. Cada fase y versión se notifica una sola vez; el resultado se
registra en `avisos_finalizacion.json` y un fallo SMTP no invalida el trabajo.
El correo incluye el proyecto, las imágenes afectadas, el progreso conservado,
la fecha, los intentos fallidos, el próximo intento, el error y el diagnóstico
técnico, sin credenciales. Un fallo del correo no impide reintentar las imágenes.
El registro se conserva en `incidencias_imagenes/<id>.json` dentro del proyecto,
incluido el resultado del envío. Funciona con el navegador cerrado mientras el
servicio y el equipo sigan en marcha.

Las claves de los otros servicios se ponen en **Configuración** (el engranaje de arriba a la derecha) y
se guardan en `secretos/claves.json`, fuera del control de versiones. Ninguna
clave baja entera al navegador: la pantalla ve la etiqueta, los cuatro últimos
caracteres y el estado.

El botón **Guardar configuración**, siempre visible al pie del panel, guarda las
claves introducidas y los ajustes de correo pendientes. Al terminar muestra
**Configuración guardada correctamente**; si falla, indica el error y conserva
las claves pendientes para poder reintentar.

**La primera vez, una guía de inicio** las pide de una en una —Claude la
primera, porque es un login y no una clave— con los pasos y el enlace de donde
se consigue cada una. Incluye las claves opcionales de **Pixabay** y **Pexels**
para imágenes y vídeos, y **FreeSound** para los efectos de sonido.
Se ve una vez por instalación (la marca vive en los
ajustes del servidor, no en el navegador) y se vuelve a abrir desde
Configuración.

**Y abajo a la derecha hay un asistente.** Es un chat que contesta con tu propia
cuenta de Claude —la misma con la que se escribe el guion— y que tiene delante
la documentación del producto, el código (sólo lectura: Read, Grep y Glob) y una
foto del estado del Estudio en el momento de cada pregunta: qué claves hay, qué
vídeo está abierto, qué paso está parado y con qué error. Y tiene manos:
prueba las claves contra su servicio, mira los trabajos y la bitácora, y para
un trabajo colgado, sin pedir permisos (`pasos/mcp_estudio.py`). Sin sesión de
Claude lo dice y manda a entrar; con el cupo agotado, dice hasta cuándo. Lo
que puede y no puede leer —`secretos/` no, por regla de permiso del CLI— está
en `pasos/asistente.py`.

**«Puesta» no es «funciona».** Configuración tiene «Probar todas las claves»
(cada una contra su servicio, sin gastar) y cada cuenta de Claude enseña, al
lado de la sesión, cómo respondió la última vez: funciona, sin cupo, sesión
caducada. Lo apunta cada llamada al CLI (`pasos/salud_cli.py`).

---

## Cómo está montado

```
app.py            el servicio HTTP. Una ruta por cosa que sabe hacer el núcleo.
nucleo/           el grafo de estado: versiones, firmas, obsolescencia, trabajos
pasos/            los ocho pasos y lo que deciden (prompts, params, presets)
motores/          el trabajo pesado: voz, imagen, mapas, movimiento, montaje
web/              la interfaz: index.html + app.js + estilo.css, sin dependencias
herramientas/     análisis estático propio (ver más abajo)
docs/API.md       los 147 endpoints, generados del código
```

**`nucleo/` no sabe de vídeo.** Es un grafo de pasos con versiones y firmas: se
le podría poner otra cosa encima. **`pasos/` no sabe de HTTP** y **`motores/` no
importa código de la aplicación** — leen lo que necesitan por contrato (una ruta
y una forma de fichero), que es lo que permite recargarlos sin reiniciar.

### La firma, que es la pieza que hay que entender

Cada paso guarda la **huella** de sus params y de las salidas de los pasos de
los que depende. Si la huella calculada no cuadra con la guardada, el paso está
**obsoleto** — y lo están, en cascada, los que dependen de él.

De ahí salen dos reglas que parecen arbitrarias y no lo son:

- **Escribir un param «por defecto» al abrir una pantalla mueve la firma.** Un
  proyecto que nunca tuvo ese param pasaría a estar obsoleto entero sin que
  nadie pidiera nada, y eso son imágenes que se vuelven a pagar. Por eso las
  pantallas editan una copia y solo guardan cuando alguien toca algo.
- **Las rutas absolutas están DENTRO de las firmas.** Copiar la carpeta de un
  proyecto a otra máquina no basta: hay que mudar las rutas y volver a sellar
  las firmas, o el vídeo entero aparece obsoleto.

---

## Las pruebas

```bash
powershell -NoProfile -File pruebas.ps1
```

Veintiséis suites, y **por PowerShell y no por bash**: Edge headless devuelve
código 0 y no escribe el PNG cuando se lanza desde un shell sandboxeado, así que
`prueba_pasos_visuales` falla con «Edge no generó ...png» sin que nada esté roto.

Lo que se comprueba de verdad, y no es humo:

- `prueba_api.py` (~990) levanta el servicio y recorre la API entera.
- `prueba_pasos_visuales.py` (229) monta un proyecto de verdad sobre el núcleo y
  ejecuta la cadena de imágenes, rótulos y montaje **hasta el MP4**. Se fabrica
  su propio material: no depende de ningún proyecto.
- `prueba_piezas.py` (1217) las piezas una a una. **No puede pagar una imagen**:
  deja el motor sin `generar` antes de empezar, así que una firma de cache que
  deje de acertar sale como un fallo con su traza y no como una factura.
- `pasos/prueba_regresiones.py` los fallos de octubre de 2026, uno por sección:
  crear un estilo, el catálogo visual, guardar un estilo sin romper sus vídeos,
  la captura del navegador, la previa, los lotes de render, el precio.
- `python pasos/prueba_codex_imagen.py` comprueba imágenes nativas, referencias,
  fallos de cuota y facturación de suscripción con dobles, sin red ni consumo.
- `nucleo/prueba_adversarial.py` mata el proceso a mitad de una escritura, cruza
  hilos y procesos, y prueba a salirse de la carpeta con `../`.

`pruebas.ps1` corre además las **herramientas de análisis**, que cantan lo que
ninguna prueba ve porque nadie ejecuta esa línea:

| Herramienta | Qué encuentra |
|---|---|
| `indefinidos_py.py` / `indefinidos_js.py` | un nombre que no está declarado |
| `atributos_py.py` | `modulo.algo()` donde `algo` ya no existe en ese módulo |
| `huerfanas_js.py` | una llamada a una función que ya no está |
| `sin_llamar_js.py` | una función que nadie nombra, y dos con el MISMO nombre |
| `alcanzables_js.py` | funciones y tablas que no se pueden alcanzar desde ningún sitio |
| `css_sin_usar.py` | reglas de CSS de pantallas que ya no existen |

---

## Quién está dentro

**Este servicio no sabe de cuentas, y es deliberado.** No hay usuarios, ni
sesiones, ni permisos: se sirve a quien llame. El aislamiento, cuando hace
falta, va **por proceso**: un `app.py` por cuenta, cada uno con sus variables de
entorno apuntando a sus datos, y un proxy con login delante que decide a cuál
enruta.

Se hace así porque la alternativa —enseñarle al código lo que es un usuario— es
un concepto nuevo en las ocho fases, en las firmas y en cada ruta, para resolver
algo que un proceso aparte resuelve sin tocar nada. Si el proxy contesta
`/api/me`, la interfaz enseña el nombre de la cuenta; si no contesta, no pasa
nada y no se enseña.

### Dónde viven los datos

Todo se puede mover con variables de entorno, y es lo que hace posible el
aislamiento por proceso:

| Variable | Qué mueve |
|---|---|
| `ESTUDIO_PROYECTOS` | los vídeos |
| `ESTUDIO_PRESETS` | los estilos |
| `ESTUDIO_BANCO`, `ESTUDIO_BANCO_PRESETS` | las imágenes y el audio de stock |
| `ESTUDIO_SECRETOS` | las claves de API |
| `ESTUDIO_AJUSTES`, `ESTUDIO_RECETAS`, `ESTUDIO_TARIFAS` | la configuración |
| `ESTUDIO_ESTADISTICAS`, `ESTUDIO_COSTE_GLOBAL`, `ESTUDIO_BITACORA_GLOBAL` | lo medido y lo gastado |
| `ESTUDIO_MOTORES`, `ESTUDIO_FUENTES` | los motores y las tipografías |
| `ESTUDIO_EDGE`, `ESTUDIO_FFMPEG`, `ESTUDIO_FFPROBE` | los ejecutables |
| `ESTUDIO_LOTES` | cuántos planos se renderizan a la vez |
| `ESTUDIO_RENDER_GPU` | `auto`: GPU en Windows; `0`: desactivarla; `1`: permitirla también en otros sistemas |
| `ESTUDIO_SIMULAR=1` | no sale a ninguna API de pago: lo usan las pruebas |

**`ESTUDIO_ESTADISTICAS` importa más de lo que parece.** El histórico guarda 30
muestras por paso, y de ahí sale lo que promete la barra de progreso. Una suite
que escriba en el de verdad expulsa las medidas reales por antigüedad, y la
barra empieza a prometer la mitad del tiempo. Por eso todas las suites lo
redirigen, y `pruebas.ps1` lo redirige otra vez por si alguna se olvida.
