"""Imágenes inmutables para tarjetas de animación; no sustituyen el plano."""
import io
import os
import re
import uuid

from PIL import Image, ImageOps

MAX_BYTES = 20 * 1024 * 1024
CARPETA = "medios_usuario/animaciones"
_RUTA = re.compile(r"medios_usuario/animaciones/[a-f0-9]{32}\.png")


def validar_referencias(referencias):
    if not isinstance(referencias, dict) or set(referencias) - {"propia", "otra"}:
        raise ValueError("las imágenes de las tarjetas deben ser izquierda y derecha")
    for ruta in referencias.values():
        if not isinstance(ruta, str) or not _RUTA.fullmatch(ruta):
            raise ValueError("elige una imagen subida desde el editor de animación")
    return dict(referencias)


def ruta_de(proyecto, referencia):
    validar_referencias({"propia": referencia})
    ruta = proyecto.ruta(*referencia.split("/"))
    if not os.path.isfile(ruta):
        raise ValueError("no se encuentra una imagen de las tarjetas; vuelve a subirla")
    return ruta


def guardar(proyecto, contenido, nombre):
    """Valida, orienta y normaliza a PNG sin recortar ni deformar la fotografía."""
    if os.path.splitext(nombre or "")[1].lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("elige una imagen PNG, JPG o WebP")
    if len(contenido) > MAX_BYTES:
        raise ValueError("la imagen supera el límite de 20 MiB")
    try:
        with Image.open(io.BytesIO(contenido)) as original:
            if original.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("elige una imagen PNG, JPG o WebP")
            if original.width * original.height > 40_000_000:
                raise ValueError("la imagen supera los 40 megapíxeles")
            original.load()
            imagen = ImageOps.exif_transpose(original).convert("RGBA" if "A" in original.getbands()
                                                              or "transparency" in original.info else "RGB")
            imagen.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
    except (OSError, ValueError, Image.DecompressionBombError) as fallo:
        raise ValueError(f"no se puede usar esa imagen: {fallo}") from fallo
    referencia = f"{CARPETA}/{uuid.uuid4().hex}.png"
    destino = proyecto.ruta(*referencia.split("/"))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    try:
        imagen.save(destino, "PNG")
    except BaseException:
        if os.path.isfile(destino):
            os.remove(destino)
        raise
    finally:
        imagen.close()
    return referencia
