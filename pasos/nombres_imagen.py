"""Nombre semántico de un recurso visual, sin cambiar la ruta técnica del plano."""
import os
import re
import unicodedata
import uuid

try:
    from . import cli_claude
except ImportError:
    import cli_claude


def palabras(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    return re.findall(r"[a-z0-9]+", "".join(c for c in texto if not unicodedata.combining(c)))


def nombre(identificador, descripcion, extension=".png"):
    """Pide a Claude un nombre breve que describa el recurso, no su narración."""
    if not descripcion or os.environ.get("ESTUDIO_SIMULAR") == "1":
        return None
    texto, _ = cli_claude.ejecutar(
        "Da un nombre de archivo corto en español para la imagen o vídeo descrito. "
        "Solo el nombre descriptivo, sin extensión, rutas, comillas ni explicación. "
        "Incluye los rasgos que distinguen al sujeto (estado, color, acción). "
        "No inventes detalles que la descripción no indique. Descripción visual: "
        + str(descripcion)[:1800], modelo="sonnet", esfuerzo="low")
    partes = palabras(texto.splitlines()[0] if texto else "")[:8]
    if not partes:
        return None
    return f"{identificador}-{'-'.join(partes)[:80]}{extension}"


def guardar_alias(ruta, nombre_archivo):
    """Un enlace al PNG técnico: las rutas de las versiones siguen siendo válidas."""
    if not nombre_archivo or not os.path.isfile(ruta):
        return
    carpeta = os.path.join(os.path.dirname(ruta), "nombres")
    os.makedirs(carpeta, exist_ok=True)
    alias = os.path.join(carpeta, nombre_archivo)
    temporal = alias + "." + uuid.uuid4().hex
    try:
        os.link(ruta, temporal)
        os.replace(temporal, alias)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)
