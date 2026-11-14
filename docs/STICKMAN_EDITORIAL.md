# Stickman: realización editorial y mapa del kit

## Uso

El modo Stickman mantiene el flujo habitual de Estilos → Encargo → Guion →
Generar animaciones → Montar. La dirección visual nueva selecciona el tipo de
representación y el motor la dibuja con componentes locales.

Al describir el estilo o regenerar las descripciones se pueden pedir, por
ejemplo, «ejemplos cotidianos alternados con comparaciones y documentos; primeros
planos para las reacciones; azul y naranja para las dos condiciones». La dirección
debe ajustarse a la duración real de cada frase y a las identidades del reparto.

Las imágenes publicadas no se sustituyen al abrir el vídeo. Una nueva generación
utiliza el contrato nuevo. Los estilos guardados mantienen sus variantes; los
estilos nuevos parten del acabado neutro Editorial Cinema.

## Dependencias y verificación

```bash
npm ci --prefix motores/remotion
npm ci --prefix motores/stickman
python pasos/prueba_stickman.py --real
python pasos/prueba_stickman_editorial.py --real
```

El segundo paquete fija las mismas versiones de Three.js y fuentes que el kit.
El bundle incluye las fuentes; renderizar no las descarga de internet. Las dos
suites son locales y no solicitan contenido a proveedores. La prueba editorial
comprueba todos los adaptadores de ui2d/fx2d, fuentes, estados, determinismo al
buscar hacia atrás y cámaras/constructores 3D.

Para conservar las capturas de la prueba editorial, definir
`ESTUDIO_PRUEBA_STICKMAN_MUESTRAS` con una carpeta de salida. Es una opción de la
suite, no un ajuste de los proyectos.

## Qué se aprovecha del kit

| Módulo original | Integración |
|---|---|
| `core.js` | Reloj, interpolación/curvas, paleta, ambientes, composición, capas con profundidad, desenfoque, texto, gradientes y utilidades |
| `rig2d.js` | Poses y sus mezclas, ciclos, respiración, expresiones, mirada, ropa, accesorios, atrezzo, balón y rostro grande para primeros planos Classic |
| `ui2d.js` | Todas sus funciones de dibujo: títulos, preguntas, badges, lectura de cifras, llamadas, dimensiones, tarjetas de datos, barras, medidores, blueprint, figuras lineales, burbujas, pantalla final y captions |
| `fx2d.js` | Todas sus familias: lluvia, gotas, polvo, nieve, estrellas, niebla, sol/luna, rayos de luz, focos, pools, estelas de luz, destellos, relámpagos, velocidad, ondas y todos los constructores de decorado/público |
| `styles.js` | Los cinco estilos, sus ambientes y tokens; perfil editorial neutro adicional en el adaptador |
| `three-kit.js` | Stage, sombras, bloom, materiales, geometrías, texturas, edificios, ventanas, vegetación, público, figura articulada, órbita y dolly |
| `player.js` | Su gradación, viñeta y grano se adaptan al render del Estudio; el montaje y las transiciones los conserva el Estudio |
| `audio/sfx.py`, `audio/dsp.py` | Catálogo procedural completo por la pista Sonidos, con tiempos, recorte y ganancia, sin duplicación en el clip visual |
| Herramientas de voz/render del kit | Sus funciones de producción se cubren con voz, marcas, navegador, ffmpeg y montaje del Estudio; no se arranca otro pipeline paralelo |

Los proveedores entregan datos validados, no JS/SVG ejecutable ni callbacks.
La integración utiliza las funciones originales; los componentes editoriales
adicionales resuelven layouts frecuentes con las primitivas del mismo kit.

## Contrato de escena

Los campos anteriores —ambiente, decorado, atmósfera, cámara, actores, objetos,
utilería y sonidos— siguen disponibles. Se añaden:

```json
{
  "realizacion": {
    "encuadre": "conjunto",
    "objetivo": "Mostrar la reacción de una persona ante la otra",
    "escenario": {"id": "fiesta_principal", "tipo": "fiesta", "semilla": 7},
    "acabado": true,
    "desenfoque": 0,
    "profundidad": 0.65,
    "grano": 0.018,
    "vineta": 0.32,
    "bandas": 0
  },
  "graficos": [],
  "efectos_visuales": []
}
```

`realizacion` es opcional en los planes anteriores. Los campos nuevos activan la
composición editorial. La resolución lógica mantiene el ancho 1920 y adapta la
altura a la proporción de salida, como el contrato histórico.

### Encuadres

- `general`, `conjunto`: actuación contextual.
- `medio`, `primer_plano`: requieren `sujeto` presente en el reparto de la escena.
  El motor calcula el centro a partir del rig; el modelo conserva pies y escala
  habituales. En Classic se usa el rostro grande original del kit.
- `detalle`: requiere `foco:[x,y]` normalizado de 0 a 1.
- `grafico`: permite composición explicativa sin actores.
- `dividido`: dos protagonistas con `panel:izquierda|derecha`, normalmente en
  x=.25/.75. Mantener condiciones comparables.
- `cierre`: admite elencos más pequeños y permanencias de lectura.

Los actores de fondo pueden usar `rol:figurante`. Su tamaño se valida con otro
mínimo y se atenúan visualmente. Un protagonista pequeño no se acepta solo por
añadir figurantes a la escena.

### Escenarios

`vacio`, `fiesta`, `salon`, `oficina`, `laboratorio`, `barrio`, `parque`, `cocina`,
`teatro`, `aula`. Los cuatro decorados anteriores siguen disponibles.

El id/tipo/semilla determina el lugar estable. El contexto `escenarios_video`
recupera localizaciones de los planes publicados; la continuidad del bloque
conserva además actores, geometrías y estados finales. Al retomar no depende de
la sesión de un proveedor.

### Componentes gráficos

Cada componente tiene `tipo`, `inicio`, `fin`, `capa` y `opciones`.

```json
{
  "tipo": "lista",
  "inicio": 0,
  "fin": 6,
  "capa": "pantalla",
  "opciones": {
    "titulo": "UNA IDEA A LA VEZ",
    "filas": ["Situación", "Acción", "Resultado"],
    "intervalo": 1
  }
}
```

Funciones originales: `titleCard`, `bigLine`, `badge`, `readout`, `callout`,
`dimension`, `dataCard`, `compareBars`, `meter`, `blueprint`, `lineFigure`,
`bubble`, `endScreen`, `captions`.

Componentes semánticos adicionales:

- `lista`: título, filas y activación escalonada.
- `barras`: título y filas `{label,v,color?}` con magnitudes normalizadas 0–1.
- `poblacion`: total, destacados y título.
- `cronologia`: título y etiquetas.
- `documento`: título, filas, índice destacado y sello opcional.
- `comparacion`: dos títulos y sus detalles.
- `interruptor`: título, estado inicial y segundo de cambio opcional.
- `dial`: título, valor, máximo y unidad.

El esquema exacto de opciones y límites está en `pasos/realizacion_stickman.py`
y se envía al director. `captions` utiliza las marcas reales cuando coinciden
con las palabras de la frase; los subtítulos del montaje siguen teniendo su
control habitual. Usar texto selectivo evita duplicación y saturación.

### Capas y continuidad temporal

- `fondo`: detrás de actores, con profundidad de escenario.
- `frente`: delante de actores, bajo acabado de imagen.
- `pantalla`: no recibe cámara; los textos conservan contraste tras la gradación.

Los intervalos son locales a la escena. Para continuar un componente entre
frases, repetir sus opciones con `desfase` igual al tiempo transcurrido y
`duracion_total` igual a la duración de la secuencia. Esto conserva entradas,
trazos, selecciones y ciclos sin reiniciarlos. También se admite en los efectos.

### Actuación

Las claves admiten `curva:linear|in|out|inOut|sine|outBack|outElastic`. Se aplica
al tramo que termina en esa clave. Los datos medidos deben estabilizarse: no
usar rebotes para aparentar variación en una magnitud.

`actor.actuacion` admite mirada, duración de mezcla de pose, amplitud de
respiración, atrezzo original con mano F/B, gafas, guantes, pantalón y rastro.
El atrezzo original se reutiliza también en las familias de dibujo personalizadas.
La utilería vectorial por piezas y anclas sigue siendo la opción para objetos
específicos del relato.

### Espacio 3D

`espacio3d` contiene cámara, objetos, bloom y niebla. La cámara admite órbita o
recorrido entre posiciones; los objetos usan metros y radianes.

Constructores: `box`, `cyl`, `cone`, `sphere`, `plane`, `ground`, `building`,
`tree3D`, `pine3D`, `crowd3D`, `windowPane`, `shaft`, `figure3D`. El suelo admite
textura procedural de tablas o baldosas. Las figuras referencian actores
presentes y comparten sus poses con el rig 2D. Los gráficos pueden superponerse.

Se usa WebGL del navegador de render. El kit no se ejecuta en el navegador del
usuario ni contacta un proveedor de vídeo. Los clips finales siguen siendo MP4
del proyecto y viajan al duplicar o exportar.

## Persistencia

La versión del motor, reparto, dirección, contexto, marcas de voz y FPS forman
parte de la firma de generación. Los planes JSON guardan las decisiones. Los
clips publicados permanecen reproducibles; regenerar utiliza el motor nuevo.

El grafo y sus ids se conservan. Las referencias de utilería siguen siendo
inmutables. No se escriben parámetros nuevos al abrir un proyecto. Los efectos
sonoros permanecen en su pista y no se muxean además dentro de cada clip.
