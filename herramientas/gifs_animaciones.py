"""Genera los GIF de muestra de las tarjetas de «Motion animation».

    python herramientas/gifs_animaciones.py            # todas
    python herramientas/gifs_animaciones.py ficha-ui   # solo esa

Cada GIF sale del MISMO dibujo que el render (`pasos/animaciones.svg_de`) puesto
sobre un fondo de muestra y movido con `setCurrentTime`, como hace p8, y con el
mismo efecto de fondo (`animaciones.JS_FONDO`): lo que enseña la tarjeta es lo
que luego se monta, no una maqueta aparte. Salen a `web/anim_<id>.gif`, que es
plano a proposito (ver `fichero_web` en app.py).

No usa ffmpeg: el GIF lo escribe Pillow. Hay que volver a correrlo si cambia el
dibujo de alguna animacion. No gasta nada: ni modelo ni imagenes de pago, solo el
navegador del render. Lanzarlo por PowerShell (Edge headless desde un shell
sandboxeado devuelve 0 sin escribir el PNG).
"""
import json
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "pasos"))

from PIL import Image, ImageDraw  # noqa: E402

import animaciones  # noqa: E402
import medios  # noqa: E402
import p8_render  # noqa: E402

ANCHO, ALTO = 1280, 720
FPS = 12
DURACION = 6.0
ANCHO_GIF = 360

PALETA = {"texto": "#f4f1ea", "tenue": "#cfc8ba", "linea": "#d8a657",
          "sombra": "#12130f", "acento": "#d8785a"}

#: Lo que se «dice» en cada muestra, escogido para que su senal sea inequivoca.
MUESTRAS = {
    "infografia-cifra": "El 45% de los barcos nunca llegó a puerto.",
    "editorial-fecha": "Todo cambió en 1923, cuando cayó el muro.",
    "ficha-ui": "Entonces llegó Cristóbal Colón con tres naves.",
    "tipografia-cinetica": "Nadie volvió a verlos jamás.",
    "ficha-cristal": "Entonces llegó Cristóbal Colón con tres naves.",
    "etiqueta-escrita": "Se conoce como Fertilizante Potásico en todo el sector.",
    "collage-titulo": "Allí nació la Revolución Industrial en Inglaterra.",
    "comparacion-tarjetas": "Las raíces sanas crecen profundas mientras que las raíces atrofiadas apenas avanzan.",
}


def _paisaje(destino, cielo=(38, 52, 92), sol=(238, 196, 120), lomas=((30, 40, 52), (16, 22, 30))):
    """Un paisaje de muestra: cielo en degradado, sol y dos lomas. Neutro y libre."""
    img = Image.new("RGB", (ANCHO, ALTO))
    d = ImageDraw.Draw(img)
    for y in range(ALTO):
        k = y / ALTO
        d.line([(0, y), (ANCHO, y)], fill=(int(cielo[0] + 150 * k), int(cielo[1] + 70 * k),
                                           int(cielo[2] + 20 * k)))
    d.ellipse([ANCHO * 0.68, ALTO * 0.42, ANCHO * 0.68 + 150, ALTO * 0.42 + 150], fill=sol)
    d.polygon([(0, ALTO), (0, ALTO * 0.72), (ANCHO * 0.35, ALTO * 0.6), (ANCHO * 0.7, ALTO * 0.78),
               (ANCHO, ALTO * 0.66), (ANCHO, ALTO)], fill=lomas[0])
    d.polygon([(0, ALTO), (0, ALTO * 0.86), (ANCHO * 0.5, ALTO * 0.74), (ANCHO, ALTO * 0.88),
               (ANCHO, ALTO)], fill=lomas[1])
    img.save(destino)
    return destino


def _escena(sid, texto, t0=0.0):
    palabras, marcas, t = texto.split(), [], t0 + 0.5
    for _ in palabras:
        marcas.append([t, t + 0.38])
        t += 0.42
    return {"id": sid, "narracion": texto, "marcas": marcas,
            "t_in": t0, "t_out": t0 + DURACION}


def _pagina(destino, fondo, svg, fondo_anim, precarga):
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'html,body{{margin:0;background:#000;overflow:hidden}}'
            f'#l{{position:relative;width:{ANCHO}px;height:{ALTO}px;overflow:hidden}}'
            f'#l img.f,#l svg{{position:absolute;left:0;top:0;width:{ANCHO}px;height:{ALTO}px}}'
            f'</style></head><body><div id="l"><img class="f" id="f" src="{p8_render._url_local(fondo)}">'
            f'{svg}</div><div style="display:none">'
            + "".join(f'<img src="{u}">' for u in precarga) +
            f'</div><script>const s=document.querySelector("svg");s.pauseAnimations();'
            f'const FONDO={json.dumps(fondo_anim)};{animaciones.JS_FONDO}'
            f'function pintar(t){{s.setCurrentTime(t);aplicarFondo(document.getElementById("f"),FONDO,t);return 1;}}'
            f'pintar(0);</script></body></html>')
    return medios.escribir_texto(destino, html)


def generar(aid, carpeta, navegador):
    primera = _escena("S001", MUESTRAS[aid])
    fondo = _paisaje(os.path.join(carpeta, "fondo.png"))
    otra = _paisaje(os.path.join(carpeta, "tarjeta.png"), cielo=(70, 40, 60), sol=(250, 235, 200),
                      lomas=((50, 30, 40), (24, 14, 20)))
    imagenes = {"S001": p8_render._url_local(fondo), "S001__tarjeta": p8_render._url_local(otra)}
    capas = animaciones.capas([primera], {"animaciones": [aid]}, "es", PALETA,
                              (ANCHO, ALTO), imagenes=imagenes)
    if "S001" not in capas:
        raise RuntimeError(f"{aid}: la muestra no dispara su animacion")
    capa = capas["S001"]
    pagina = _pagina(os.path.join(carpeta, f"{aid}.html"), fondo, capa["svg"], capa["fondo"],
                     capa["imagenes"])
    marcos = os.path.join(carpeta, aid)
    os.makedirs(marcos, exist_ok=True)
    navegador.abrir(pagina)
    total = int(DURACION * FPS)
    for n in range(total):
        navegador.pintar(n / FPS)
        navegador.capturar(os.path.join(marcos, f"f{n:04d}.png"))
    destino = os.path.join(RAIZ, "web", f"anim_{aid}.gif")
    alto_gif = round(ANCHO_GIF * ALTO / ANCHO)
    cuadros = []
    for n in range(total):
        with Image.open(os.path.join(marcos, f"f{n:04d}.png")) as im:
            cuadros.append(im.convert("RGB").resize((ANCHO_GIF, alto_gif), Image.LANCZOS)
                           .quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE))
    cuadros[0].save(destino, save_all=True, append_images=cuadros[1:], loop=0,
                    duration=round(1000 / FPS), optimize=True, disposal=1)
    return destino


def main(argv):
    ids = argv or list(animaciones.CATALOGO)
    desconocidas = [a for a in ids if a not in animaciones.CATALOGO]
    if desconocidas:
        print("no existen:", ", ".join(desconocidas))
        return 2
    carpeta = tempfile.mkdtemp(prefix="gifs_anim_")
    navegador = p8_render.Navegador(ANCHO, ALTO)
    try:
        for aid in ids:
            ruta = generar(aid, carpeta, navegador)
            print(f"{aid}: {os.path.getsize(ruta) // 1024} KB -> {os.path.relpath(ruta, RAIZ)}")
    finally:
        navegador.cerrar()
        shutil.rmtree(carpeta, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
