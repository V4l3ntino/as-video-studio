"""Genera las tarjetas de Efectos con los mismos shaders que el montaje.

    python herramientas/gifs_transiciones.py [id ...]

Solo usa el navegador local y Pillow, sin proveedores ni ffmpeg.
Los GIF planos en web/ funcionan también detrás del prefijo del proxy.
"""
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "pasos"))

from PIL import Image  # noqa: E402

import p8_render  # noqa: E402
import transiciones  # noqa: E402
from gifs_animaciones import _paisaje  # noqa: E402

ANCHO, ALTO = 360, 202
FPS = 20


def main(argv):
    catalogo = [tid for tid in transiciones.CATALOGO if tid != "corte"]
    ids = argv or catalogo
    if any(tid not in catalogo for tid in ids):
        raise ValueError("Transición desconocida")
    carpeta = os.path.realpath(tempfile.mkdtemp(prefix="gifs_transiciones_"))
    navegador = p8_render.Navegador(ANCHO, ALTO)
    try:
        desde = _paisaje(os.path.join(carpeta, "desde.png"))
        hasta = _paisaje(os.path.join(carpeta, "hasta.png"), cielo=(40, 90, 95),
                         sol=(230, 245, 210), lomas=((35, 85, 60), (16, 48, 40)))
        # Cambiar también la composición para hacer visibles giros y barridos.
        with Image.open(hasta) as imagen:
            imagen.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(hasta)
        pagina = transiciones.pagina(os.path.join(carpeta, "muestra.html"), ANCHO, ALTO)
        navegador.abrir(pagina)
        for tid in ids:
            cuadros = []
            for n in range(FPS + 1):
                destino = os.path.join(carpeta, "fotograma.png")
                transiciones.componer(navegador, desde, hasta, n / FPS,
                                      transiciones.frag_de(tid), destino)
                with Image.open(destino) as imagen:
                    cuadros.append(imagen.convert("RGB").quantize(
                        colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
            destino = os.path.join(RAIZ, "web", f"transicion_{tid}.gif")
            cuadros[0].save(destino, save_all=True, append_images=cuadros[1:],
                            duration=[650] + [round(1000 / FPS)] * (FPS - 1) + [650],
                            loop=0, optimize=True, disposal=1)
            print(f"{tid}: {os.path.getsize(destino) // 1024} KB")
    finally:
        navegador.cerrar()
        shutil.rmtree(carpeta, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
