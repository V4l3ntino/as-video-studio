"""Dirección cromática compartida por descripciones y animaciones Stickman."""
import json

from pasos.realizacion_stickman import PALETAS


def normalizar(colores):
    if not isinstance(colores, str) or len(colores) > 500:
        raise ValueError('colores debe ser texto de hasta 500 caracteres, con nombres separados por comas')
    return ', '.join(dict.fromkeys(c.strip() for c in colores.split(',') if c.strip()))


def instruccion(estilo=None):
    return '''== DIRECCIÓN DE COLOR POR ESCENA ==
Decide los colores al describir la escena, no los dejes para la animación.
Usa estas familias compartidas con el motor: ''' + json.dumps(PALETAS, ensure_ascii=False) + '''.
Ember Forge: negro, rojo intenso, cobre y naranja para drama y tensión.
Arctic Glass: azules fríos, turquesas y blanco hielo para ciencia y tecnología;
incorpora amarillo cálido #ffcb52 para títulos, cifras, etiquetas, umbrales o el foco explicativo.
Mantén ejes, estructura y datos de contexto azules/turquesas sobre fondo azul oscuro.
Sakura Bloom: rosa, violeta, ciruela y melocotón para emoción e intimidad.
Retro Print: verde azulado apagado, mostaza, sepia y naranja para historia y memoria.
Respeta la familia del acabado elegido si es una de estas cuatro. Con Editorial Cinema,
elige por el tono del encargo y conserva la paleta al continuar la misma secuencia.
Estas paletas dirigen fondos, diagramas, palabras clave y luz; no sustituyen los materiales.
Casas: yeso crema/blanco roto, piedra o ladrillo, tejado terracota/pizarra y puertas plausibles.
Cunas: madera o lacado blanco, sábanas claras, mantas suaves; piel de tonos humanos naturales
y diversos, ojos y boca legibles oscuros. No heredes para estos materiales el color del personaje.
Respeta colores explícitos del encargo y la identidad de personajes ya establecidos.
Fondo oscuro profundo en explicaciones gráficas, texto auxiliar claro y un foco en color de acento.
Puedes describir un halo leve de neón en 1–3 palabras clave o siluetas focales: copia desenfocada
detrás del original NÍTIDO. No desenfoques el texto, la piel, el mobiliario ni toda la escena.
ACABADO VISUAL DE LAS REFERENCIAS: partículas de fondo flotantes, escasas, pequeñas y suaves,
que se mueven despacio para dar profundidad sin competir con los personajes, datos ni palabras.
En las explicaciones azuladas/Arctic Glass describe una malla fina y tenuemente visible de fondo.
Mantén los diagramas limpios: población con figuras azul grisáceo y solo los casos destacados con
halo azul; cronologías con acciones repetidas y etiquetas legibles; comparaciones con jerarquía clara.
Las comparaciones simultáneas deben tener acabado luminoso: luz fría azul a un lado y cálida
ámbar/naranja o roja al otro según el relato, fondos oscuros con degradados y focos de luz,
suelo con reflejos suaves, partículas distintas por lado y separador quebrado o diagonal de neón.
Nunca describas dos mitades planas de azul/rojo saturados, una franja gris y una raya blanca.
Describe títulos grandes, redondeados y legibles (Fredoka/Nunito), un título dorado claro y
etiquetas breves bien jerarquizadas junto a personajes u objetos, sin amontonar rótulos pequeños.
Mantén el significado de los colores pedidos y los materiales propios de cada elemento.
No inventes cifras, edades, porcentajes ni ejemplos históricos para justificar estos recursos.
En escenas de personajes alterna generales y primeros planos del rostro con fondo desenfocado.
Si el personaje pronuncia una frase relevante, describe un bocadillo breve con cola hacia su rostro;
para un pensamiento explícito o una idea ilustrativa clara, usa bocadillo de pensamiento con círculos.
No atribuyas al personaje palabras del narrador ni pensamientos inventados como hechos reales.
El bocadillo queda en un lateral sin tapar ojos o boca, con fondo claro y tinta oscura nítida.
No pongas un bocadillo en cada frase: úsalo cuando el diálogo, la intención o la reacción sean el foco.
Mantén continuidad de escenario, luz, actores y partículas entre frases de la misma secuencia.
ESCENOGRAFÍA RECONOCIBLE: describe el espacio construido con materiales, profundidad y luz,
no solo "un teatro" o bloques planos. En teatro: terciopelo burdeos con pliegues y sombras,
cortinas laterales, tarima de madera con juntas, candilejas y un foco cálido suave sobre el
protagonista, con partículas y destellos discretos en el haz. Público como siluetas cercanas
en el borde inferior, no muñecos diminutos repetidos. Atril únicamente si participa en la acción;
si el teatro está vacío, indícalo y no inventes espectadores. Mantén claros los planos de profundidad.
Aplica el mismo criterio a otros espacios: sofá/cojines, ventana y lámparas en un salón;
escritorio y silla en oficina; banco, cristalería y microscopio en laboratorio; azulejos,
armarios, fregadero y frigorífico en cocina; pizarra enmarcada y pupitres en aula; fachadas,
vegetación y caminos con escala y distancia en exteriores. Los materiales conservan sus colores.
El decorado apoya la acción y no añade una lista de cosas que deban animarse dentro de la frase.
Las peticiones explícitas de fondo liso, ausencia de partículas o de cuadrícula tienen prioridad.
OBLIGATORIO: cada entrada de escenas_visuales y cada escena regenerada incluye
colores como CADENA de nombres separados por comas, por ejemplo:
"colores":"azules fríos, turquesas, amarillo cálido".
Declara los colores principales realmente elegidos para ESA escena (incluidos los materiales
dominantes si importan), no todos los de la biblioteca. La descripcion_visual concreta dónde
se usa cada color y qué elemento lleva halo, si lo hay. No cambies el texto narrado.
Estilo del vídeo para esta dirección: ''' + json.dumps(estilo or {}, ensure_ascii=False) + '\n'
