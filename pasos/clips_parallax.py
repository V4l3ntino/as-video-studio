"""Clips derivados compartidos por la revisión de imágenes y el montaje.

Leer una previa no genera ni modifica el grafo. Los clips y sus índices son
inmutables por firma y viven fuera de las versiones de assets/render.
"""
import hashlib
import json
import os

from PIL import Image
from pasos import medios


def preparar(proyecto, escena, imagen, opciones, fps=30):
    if not imagen:
        return None
    imagen = proyecto.ruta(imagen)
    if not os.path.isfile(imagen):
        return None
    fps = int(fps)
    total = max(1, round(float(escena["t_out"]) * fps) - round(float(escena["t_in"]) * fps))
    stat = os.stat(imagen)
    with Image.open(imagen) as img:
        resolucion = [max(2, n - n % 2) for n in img.size]
    efecto = {k: opciones[k] for k in ("movimiento", "intensidad")}
    firma = dict(imagen=os.path.relpath(imagen, proyecto.raiz), tamano=stat.st_size,
                 fecha=stat.st_mtime_ns, opciones=efecto, frames=total, fps=fps,
                 resolucion=resolucion, version=1)
    clave = hashlib.sha256(json.dumps(firma, sort_keys=True).encode()).hexdigest()
    return dict(clave=clave, imagen=imagen, opciones=efecto, duracion=total / fps,
                fps=fps, resolucion=resolucion,
                indice=proyecto.ruta("parallax", "indices", clave + ".json"))


def disponible(proyecto, pedido):
    if not pedido:
        return None
    ficha = medios.leer_json(pedido["indice"], {}) or {}
    relativo = ficha.get("clip")
    if not relativo:
        return None
    ruta = proyecto.ruta(relativo)
    real = os.path.realpath(ruta)
    base = os.path.realpath(proyecto.ruta("parallax"))
    if os.path.commonpath([base, real]) != base or not os.path.isfile(ruta):
        return None
    return ruta


def generar(proyecto, pedido, latido=None):
    from motores.parallax_depthflow import generar as animar
    ruta = disponible(proyecto, pedido)
    if ruta:
        return ruta
    ruta = animar(pedido["imagen"], proyecto.ruta("parallax", "clips"),
                  pedido["opciones"], pedido["duracion"], pedido["fps"],
                  pedido["resolucion"], latido=latido)
    if os.path.isfile(ruta):
        medios.escribir_json(pedido["indice"], {"clip": os.path.relpath(ruta, proyecto.raiz)})
    return ruta
