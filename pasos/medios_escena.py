"""Material del usuario para un plano: entradas inmutables, sin generadores IA."""
import copy
import json
import math
import os
import subprocess

from PIL import Image, ImageOps
from nucleo.proyecto import ruta_contenida
try:
    from . import medios
except ImportError:
    import medios

MIN_VIDEO_S = 2.0
MAX_VIDEO_S = 15.0
MAX_BYTES = 200 * 1024 * 1024
IMAGENES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEOS = {".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"}


def _correr(orden):
    try:
        resultado = subprocess.run(orden, capture_output=True, timeout=180,
                                   **medios.SIN_VENTANA)
    except (OSError, subprocess.TimeoutExpired) as fallo:
        raise ValueError(f"no se ha podido procesar el clip: {fallo}") from fallo
    if resultado.returncode:
        raise ValueError("el archivo de vídeo no se puede procesar: "
                         + resultado.stderr.decode("utf-8", errors="replace")[-400:])
    return resultado.stdout


def informacion_video(ruta):
    datos = json.loads(_correr([medios.ffprobe(), "-v", "error", "-protocol_whitelist", "file,pipe",
        "-show_entries", "format=duration:stream=codec_type,duration,width,height", "-of", "json", ruta]))
    video = next((s for s in datos.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video or not video.get("width") or not video.get("height"):
        raise ValueError("el archivo no contiene una pista de vídeo válida")
    duracion = float(video.get("duration") or (datos.get("format") or {}).get("duration") or 0)
    if not math.isfinite(duracion) or duracion <= 0:
        raise ValueError("no se puede determinar la duración del vídeo")
    return {"duracion": duracion, "ancho": video["width"], "alto": video["height"]}


def preparar(origen, nombre, carpeta, tamano):
    """Normaliza la imagen o los primeros 15 s de un clip; descarta su audio."""
    extension = os.path.splitext(nombre or "")[1].lower()
    os.makedirs(carpeta, exist_ok=True)
    ancho, alto = map(int, tamano)
    poster = os.path.join(carpeta, "imagen.png")
    if extension in IMAGENES:
        try:
            with Image.open(origen) as imagen:
                ImageOps.fit(ImageOps.exif_transpose(imagen).convert("RGB"), (ancho, alto),
                             method=Image.Resampling.LANCZOS).save(poster, "PNG")
        except (OSError, ValueError, Image.DecompressionBombError) as fallo:
            raise ValueError("no se puede abrir esa imagen") from fallo
        return {"tipo": "imagen", "archivo": poster, "poster": poster}
    if extension not in VIDEOS:
        raise ValueError("elige una imagen PNG, JPG o WebP, o un vídeo MP4, MOV, WebM, MKV, M4V o AVI")
    info = informacion_video(origen)
    if info["duracion"] < MIN_VIDEO_S:
        raise ValueError(f"el vídeo dura {info['duracion']:.3f} s; el mínimo son 2 segundos")
    duracion = min(MAX_VIDEO_S, info["duracion"])
    destino = os.path.join(carpeta, "video.mp4")
    filtro = (f"scale={ancho}:{alto}:force_original_aspect_ratio=increase,"
              f"crop={ancho}:{alto},setsar=1,fps=30")
    _correr([medios.ffmpeg(), "-nostdin", "-y", "-v", "error", "-protocol_whitelist", "file,pipe",
        "-i", origen, "-map", "0:v:0", "-t", str(duracion), "-vf", filtro,
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", destino])
    _correr([medios.ffmpeg(), "-nostdin", "-y", "-v", "error", "-i", destino,
             "-frames:v", "1", poster])
    return {"tipo": "video", "archivo": destino, "poster": poster,
            "duracion": informacion_video(destino)["duracion"],
            "duracion_original": info["duracion"], "recortado": info["duracion"] > MAX_VIDEO_S}


def aplicar_al_plan(plan, params):
    """Solo el plano cuyo texto se eligió; un id reutilizado no hereda el medio."""
    unidades = (params or {}).get("unidades") or {}
    por_texto = {}
    for unidad in unidades.values():
        if (unidad or {}).get("generar_ia"):
            continue
        medio = (unidad or {}).get("medio_usuario")
        if medio:
            por_texto.setdefault(medios.normalizar_texto(medio.get("ancla") or ""), []).append(medio)
    for escena in plan.get("escenas") or []:
        if (unidades.get("escena:" + escena["id"]) or {}).get("generar_ia"):
            escena.pop("medio_usuario", None)
            continue
        medio = (unidades.get("escena:" + escena["id"]) or {}).get("medio_usuario")
        texto = medios.normalizar_texto(escena.get("narracion") or "")
        if not medio or medios.normalizar_texto(medio.get("ancla") or "") != texto:
            candidatos = por_texto.get(texto) or []
            medio = candidatos[0] if len(candidatos) == 1 and texto else None
        if medio:
            escena["medio_usuario"] = copy.deepcopy(medio)
            escena.pop("medio_biblioteca", None)
            escena.pop("recurso_biblioteca", None)
            if escena.get("cartela"):
                escena["cartela"] = dict(escena["cartela"], fondo="imagen")
    return plan


def materializar(proyecto, escena, trabajo):
    """Deja el poster que usan continuidad, subtitulos y versiones de assets."""
    medio = escena["medio_usuario"]
    for clave in ("archivo", "poster"):
        ruta = ruta_contenida(proyecto.raiz, medio[clave])
        if not os.path.isfile(ruta):
            raise ValueError(f"falta el material elegido para {escena['id']}")
    destino = os.path.join(trabajo, "escenas", escena["id"] + ".png")
    medios.copiar(medio["poster"], destino)
    ficha = {"tipo": "escena", "id": escena["id"], "origen": "usuario", "coste": 0,
        "png": os.path.relpath(destino, trabajo), "medio_usuario": copy.deepcopy(medio),
        "narracion": escena.get("narracion") or "", "t_in": escena["t_in"], "t_out": escena["t_out"],
        "personajes": escena.get("personajes") or [], "set": escena.get("set"), "prompt": "",
        "firma": medios.huella(medio), "obsoleta": False}
    medios.escribir_json(os.path.splitext(destino)[0] + ".json", ficha)
    return ficha


def sustituir(proyecto, estado, plan, sid, medio):
    """Versiona SOLO el plano sustituido, conservando las otras unidades."""
    escena = next((e for e in plan.get("escenas", []) if e["id"] == sid), None)
    if not escena:
        raise ValueError("la escena ya no está en el plan del vídeo")
    uid = "escena:" + sid
    medio = dict(medio, ancla=escena.get("narracion") or "")
    params = estado.params("assets") or {}
    unidad = dict((params.get("unidades") or {}).get(uid) or {})
    unidad["medio_usuario"] = medio
    unidad.pop("generar_ia", None)
    estado.actualizar_params("assets", {"unidades": {uid: unidad}})
    # Las otras escenas todavia pendientes se declaran, no se dan por hechas.
    faltantes = {"escena:" + e["id"]: {} for e in plan["escenas"]
                 if "escena:" + e["id"] not in (estado.params("assets").get("unidades") or {})}
    if faltantes:
        estado.actualizar_params("assets", {"unidades": faltantes}, del_propio_paso=True)
    trabajo = medios.sembrar_trabajo(proyecto, "assets")
    escena["medio_usuario"] = medio
    escena.pop("medio_biblioteca", None)
    escena.pop("recurso_biblioteca", None)
    if escena.get("cartela"):
        escena["cartela"] = dict(escena["cartela"], fondo="imagen")
    ficha = materializar(proyecto, escena, trabajo)
    medios.escribir_json(os.path.join(trabajo, "plan.json"), plan)
    salidas = dict(estado.salidas("assets") or {}, plan="plan.json")
    # El gestor arranca antes de conocer el archivo validado. Versionamos las
    # entradas elegidas ahora, no la foto de params anterior a la subida.
    estado.limpiar_marca("assets")
    version = estado.completar("assets", salidas, unidades={uid: ficha})
    return {"id": sid, "version": version, "medio": medio}
