"""Genera los GIF de muestra de las tarjetas de «Motion animation».

    python herramientas/gifs_animaciones.py            # todas
    python herramientas/gifs_animaciones.py ficha-ui   # solo esa

Cada GIF sale del MISMO dibujo que el render (`pasos/animaciones.svg_de`) puesto
sobre un fondo de muestra y movido con `setCurrentTime`, como hace p8: lo que
enseña la tarjeta es lo que luego se monta, no una maqueta aparte. Salen a
`web/anim_<id>.gif`, que es plano a proposito (ver `fichero_web` en app.py).
No usa ffmpeg: el GIF lo escribe Pillow.

Hay que volver a correrlo si cambia el dibujo de alguna animacion. No gasta nada:
ni modelo ni imagenes de pago, solo el navegador del render.
"""
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
DURACION = 5.0
ANCHO_GIF = 360

PALETA = {"texto": "#f4f1ea", "tenue": "#cfc8ba", "linea": "#d8a657",
          "sombra": "#12130f", "acento": "#d8785a"}

#: Lo que se «dice» en cada muestra, escogido para que su senal sea inequivoca.
MUESTRAS = {
    "infografia-cifra": "El 45% de los barcos nunca llegó a puerto.",
    "editorial-fecha": "Todo cambió en 1923, cuando cayó el muro.",
    "ficha-ui": "Entonces llegó Cristóbal Colón con tres naves.",
    "tipografia-cinetica": "Nadie volvió a verlos jamás.",
}


def _fondo(destino):
    """Un paisaje de muestra: cielo en degradado, sol y dos lomas. Neutro y libre."""
    img = Image.new("RGB", (ANCHO, ALTO))
    d = ImageDraw.Draw(img)
    for y in range(ALTO):
        k = y / ALTO
        d.line([(0, y), (ANCHO, y)], fill=(int(38 + 150 * k), int(52 + 70 * k), int(92 + 20 * k)))
    d.ellipse([ANCHO * 0.68, ALTO * 0.42, ANCHO * 0.68 + 150, ALTO * 0.42 + 150], fill=(238, 196, 120))
    d.polygon([(0, ALTO), (0, ALTO * 0.72), (ANCHO * 0.35, ALTO * 0.6), (ANCHO * 0.7, ALTO * 0.78),
               (ANCHO, ALTO * 0.66), (ANCHO, ALTO)], fill=(30, 40, 52))
    d.polygon([(0, ALTO), (0, ALTO * 0.86), (ANCHO * 0.5, ALTO * 0.74), (ANCHO, ALTO * 0.88),
               (ANCHO, ALTO)], fill=(16, 22, 30))
    img.save(destino)
    return destino


def _escena(texto):
    palabras, marcas, t = texto.split(), [], 0.5
    for _ in palabras:
        marcas.append([t, t + 0.38])
        t += 0.42
    return {"id": "S001", "narracion": texto, "marcas": marcas,
            "t_in": 0.0, "t_out": DURACION}


def _pagina(destino, fondo, svg):
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'html,body{{margin:0;background:#000;overflow:hidden}}'
            f'#l{{position:relative;width:{ANCHO}px;height:{ALTO}px}}'
            f'#l img,#l svg{{position:absolute;left:0;top:0;width:{ANCHO}px;height:{ALTO}px}}'
            f'</style></head><body><div id="l"><img src="{p8_render._url_local(fondo)}">{svg}</div>'
            f'<script>const s=document.querySelector("svg");s.pauseAnimations();'
            f'function pintar(t){{s.setCurrentTime(t);return 1;}}pintar(0);</script>'
            f'</body></html>')
    return medios.escribir_texto(destino, html)


def generar(aid, carpeta, navegador):
    escena = _escena(MUESTRAS[aid])
    reparto = animaciones.repartir([escena], {"animaciones": [aid]}, "es")
    if "S001" not in reparto:
        raise RuntimeError(f"{aid}: la muestra no dispara su senal")
    svg = animaciones.svg_de(reparto["S001"], DURACION, (ANCHO, ALTO), PALETA)
    if not svg:
        raise RuntimeError(f"{aid}: no se pudo dibujar")
    fondo = _fondo(os.path.join(carpeta, "fondo.png"))
    pagina = _pagina(os.path.join(carpeta, f"{aid}.html"), fondo, svg)
    marcos = os.path.join(carpeta, aid)
    os.makedirs(marcos, exist_ok=True)
    navegador.abrir(pagina)
    total = int(DURACION * FPS)
    for n in range(total):
        navegador.pintar(n / FPS)
        navegador.capturar(os.path.join(marcos, f"f{n:04d}.png"))
    destino = os.path.join(RAIZ, "web", f"anim_{aid}.gif")
    # Pillow y no ffmpeg: un GIF de muestra no necesita mas, y asi la herramienta
    # corre en un equipo sin ffmpeg en el PATH.
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
