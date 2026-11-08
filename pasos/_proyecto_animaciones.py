"""Un proyecto de juguete con guion, plan, imagenes y animaciones, sin generar NADA.

Lo usan `prueba_animaciones` (la previa lleva la animacion de cada escena y dice
cuales faltan) y quien quiera ver la previa con animaciones sin pagar una imagen:

    python pasos/_proyecto_animaciones.py <carpeta_de_proyectos>
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from PIL import Image, ImageDraw  # noqa: E402

from nucleo.estado import Estado  # noqa: E402
from nucleo.proyecto import Proyecto, escribir_json  # noqa: E402

TEXTOS = ["El 45% de los barcos nunca llegó a puerto.",
          "Todo cambió en 1923, cuando cayó el muro.",
          "Entonces llegó Cristóbal Colón con tres naves hacia el oeste.",
          "Las raíces sanas crecen mientras que las raíces atrofiadas mueren.",
          "Nadie volvió a verlos jamás."]

#: Lo que el guion dejaria previsto, bloque a bloque (un bloque por escena).
ETIQUETAS = {"B001": "infografia-cifra", "B002": "editorial-fecha", "B003": "collage-titulo",
             "B004": "comparacion-tarjetas", "B005": "tipografia-cinetica"}

#: Lo que se ELIGIO: una mas de las que caben, para ver como se avisa de la que falta.
ELEGIDAS = list(ETIQUETAS.values()) + ["ficha-ui"]


def _escena(i, texto, t0, duracion=6.0):
    marcas, t = [], t0 + 0.3
    for _ in texto.split():
        marcas.append([round(t, 3), round(t + 0.38, 3)])
        t += 0.42
    return {"id": f"S{i:03d}", "t_in": t0, "t_out": t0 + duracion, "duracion": duracion,
            "narracion": texto, "marcas": marcas, "personajes": [],
            "origen": {"bloque": f"B{i:03d}", "indice": 0}}


def _imagen(destino, i):
    img = Image.new("RGB", (960, 640))
    d = ImageDraw.Draw(img)
    for y in range(640):
        k = y / 640
        d.line([(0, y), (960, y)], fill=(int(40 + 25 * i + 120 * k), int(55 + 60 * k), int(100 - 8 * i + 20 * k)))
    d.ellipse([620, 220, 760, 360], fill=(238, 196, 120))
    d.polygon([(0, 640), (0, 470), (330, 380), (700, 500), (960, 420), (960, 640)], fill=(28, 38, 50))
    img.save(destino)


def construir(carpeta, animaciones=ELEGIDAS, etiquetas=ETIQUETAS):
    """-> (proyecto, estado). Cinco escenas de 6 s, cada una de su bloque, con imagen.

    `animaciones` es lo que se eligio (params del guion) y `etiquetas` lo que el
    guion dejo marcado en cada bloque; con `etiquetas={}` es un video de antes del
    plan, que reparte por lo que se dice.
    """
    proyecto = Proyecto.crear(carpeta, "Previa con animaciones")
    estado = Estado(proyecto)
    escenas = [_escena(i + 1, t, i * 6.0) for i, t in enumerate(TEXTOS)]
    plan = {"generacion": [960, 640], "resolucion": [1280, 720], "formato": "horizontal",
            "idioma": "es", "semilla": 7, "duracion_total": 30.0, "escenas": escenas}
    # el guion: un bloque por escena, con la animacion que lleva
    bloques = [{"id": f"B{i + 1:03d}", "texto": t, "abre_seccion": i == 0,
                **({"animacion": etiquetas[f"B{i + 1:03d}"]} if f"B{i + 1:03d}" in etiquetas else {})}
               for i, t in enumerate(TEXTOS)]
    trabajo_g = proyecto.ruta_trabajo("guion")
    escribir_json(os.path.join(trabajo_g, "guion.json"),
                  {"titulo": "Juguete", "guion": bloques, "idioma": "es",
                   "animaciones": list(animaciones or [])})
    estado.completar("guion", {"guion_fichero": "guion.json"})
    if animaciones:
        estado.actualizar_params("guion", {"animaciones": list(animaciones)})
    trabajo = proyecto.ruta_trabajo("assets")
    os.makedirs(os.path.join(trabajo, "escenas"), exist_ok=True)
    for i, e in enumerate(escenas):
        _imagen(os.path.join(trabajo, "escenas", f"{e['id']}.png"), i)
        e["tarjetas_animacion"] = {"otra": f"escenas/{e['id']}__tarjeta.png"}
        _imagen(os.path.join(trabajo, "escenas", f"{e['id']}__tarjeta.png"), i + 0.4)
        escribir_json(os.path.join(trabajo, "escenas", f"{e['id']}__tarjeta.json"),
                      {"narracion": e["narracion"], "tarjeta_extra": True})
    escribir_json(os.path.join(trabajo, "plan.json"), plan)
    estado.completar("assets", {"plan": "plan.json"})
    return proyecto, estado


if __name__ == "__main__":
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "proyectos_prueba")
    p, _ = construir(destino)
    print(p.id, p.raiz)
