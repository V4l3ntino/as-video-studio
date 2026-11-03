"""Material para publicar en YouTube; nunca forma parte de la firma del MP4."""
import io
import json
import os
import threading
import uuid

from PIL import Image, ImageOps

from . import cli_claude, comun, medios

_LOCK = threading.RLock()
CARPETA = "publicacion"
VERSION_DISENO = 2


def _ruta(proyecto):
    return proyecto.ruta(CARPETA, "youtube.json")


def fuentes(proyecto, estado):
    from . import p6_assets

    guion = comun.leer_salida(proyecto, "guion", "guion.json", obligatorio=False) or {}
    plan = p6_assets.plan_actual(proyecto, "assets", estado=estado) or {}
    escenas = [{"id": e["id"], "narracion": e.get("narracion", ""),
                "bloque": (e.get("origen") or {}).get("bloque", ""),
                "t_in": e.get("t_in", 0), "t_out": e.get("t_out", 0)}
               for e in plan.get("escenas", []) if e.get("id")]
    estilo = (estado.params("assets") or {}).get("estilo") or {}
    refs = medios.reubicar_todas(estilo.get("referencias"))
    refs = [r for r in refs if os.path.isfile(r)][:2]
    firma = medios.huella({"guion": guion, "escenas": escenas})
    firma_miniatura = medios.huella({"texto": firma, "guia": estilo.get("guia"),
                                   "refs": [medios.huella_fichero(r) for r in refs]})
    return {"guion": guion, "escenas": escenas, "refs": refs,
            "guia": estilo.get("guia"), "firma": firma,
            "firma_miniatura": firma_miniatura}


def leer(proyecto, estado):
    datos = medios.leer_json(_ruta(proyecto), {}) or {}
    fuente = fuentes(proyecto, estado)
    ruta = datos.get("miniatura")
    if ruta and not os.path.isfile(proyecto.ruta(ruta)):
        datos["miniatura"] = None
    datos["texto_obsoleto"] = bool(datos.get("titulo") and
                                   datos.get("firma_texto") != fuente["firma"])
    datos["miniatura_obsoleta"] = bool(datos.get("miniatura") and
                                       datos.get("firma_miniatura") != fuente["firma_miniatura"])
    datos["disponible"] = bool(fuente["guion"].get("guion") and fuente["escenas"])
    datos["completo"] = bool(datos.get("titulo") and datos.get("descripcion")
                             and datos.get("miniatura"))
    return datos


def _guardar(proyecto, cambios):
    with _LOCK:
        datos = medios.leer_json(_ruta(proyecto), {}) or {}
        datos.update(cambios)
        medios.escribir_json(_ruta(proyecto), datos)
    return datos


def editar(proyecto, estado, cambios):
    limpios = {}
    for clave, limite in (("titulo", 100), ("descripcion", 5000)):
        if clave not in cambios:
            continue
        texto = str(cambios[clave] or "").strip()
        if not texto or len(texto) > limite or "<" in texto or ">" in texto:
            raise ValueError(f"{clave}: escribe entre 1 y {limite} caracteres, sin < ni >")
        limpios[clave] = texto
    if limpios:
        limpios["firma_texto"] = fuentes(proyecto, estado)["firma"]
        _guardar(proyecto, limpios)
    return leer(proyecto, estado)


def _llamar_claude(instruccion, cwd):
    return cli_claude.ejecutar(
        instruccion, modelo="sonnet", esfuerzo="medium", cwd=cwd,
        sistema="Redactas material de publicación fiel al vídeo. Devuelve solo JSON, sin usar herramientas.",
        para="el título, la descripción y la miniatura de YouTube")


def _capitulos(propuestos, escenas):
    """Los tiempos salen del montaje, nunca de una cifra inventada por el modelo."""
    bloques = {}
    for e in escenas:
        bloques.setdefault(e["bloque"], float(e["t_in"]))
    salida = []
    for c in propuestos if isinstance(propuestos, list) else []:
        if not isinstance(c, dict) or c.get("bloque") not in bloques:
            continue
        titulo = " ".join(str(c.get("titulo") or "").replace("<", "").replace(">", "").split())[:100]
        t = int(bloques[c["bloque"]])
        if titulo and (not salida or t - salida[-1][0] >= 10):
            salida.append((t, titulo))
    if len(salida) < 3 or salida[0][0] != 0:
        return ""
    if float(escenas[-1]["t_out"]) - salida[-1][0] < 10:
        salida.pop()
    if len(salida) < 3:
        return ""
    def reloj(t):
        return f"{t // 3600}:{t // 60 % 60:02}:{t % 60:02}" if t >= 3600 else f"{t // 60}:{t % 60:02}"
    return "\n".join(f"{reloj(t)} {titulo}" for t, titulo in salida)


def preparar(proyecto, estado, avisar, parte="pendientes"):
    if parte not in ("pendientes", "texto", "miniatura"):
        raise ValueError("parte debe ser pendientes, texto o miniatura")
    fuente = fuentes(proyecto, estado)
    if not fuente["guion"].get("guion") or not fuente["escenas"]:
        raise ValueError("primero hace falta un guion y un plan de escenas")
    datos = leer(proyecto, estado)
    carpeta = proyecto.ruta(CARPETA)
    os.makedirs(carpeta, exist_ok=True)
    fase = "texto"
    try:
        solo_concepto = ((parte == "miniatura" or (parte == "pendientes" and not datos.get("miniatura")))
                         and datos.get("titulo") and datos.get("descripcion")
                         and (datos.get("firma_concepto") != fuente["firma"]
                              or datos.get("version_diseno") != VERSION_DISENO
                              or not datos.get("miniatura_texto")))
        if parte == "texto" or solo_concepto or not (datos.get("titulo") and datos.get("descripcion")):
            avisar(0.05, "preparando el título y la descripción")
            instruccion = (
                "Prepara los detalles de YouTube en el idioma del guion. Sé concreto y atractivo, "
                "sin promesas falsas ni hechos, enlaces, fuentes o duraciones inventadas. "
                "Título de 1 a 100 caracteres, descripción de 1 a 4000; sin < ni >. "
                "La descripción resume el contenido; no escribas marcas de tiempo en ella. "
                "Propón capítulos solo si el relato tiene secciones claras: indica el id de bloque "
                "donde comienza cada uno; el primero debe ser el primer bloque. "
                "Diseña una MINIATURA EDITORIAL de YouTube, 16:9: debe incluir ilustración Y TEXTO "
                "como una portada, no una imagen sola ni un fotograma. Estructura: un personaje "
                "expresivo en primer plano a un lado, un objeto o situación intrigante al otro "
                "y un titular muy grande integrado sobre una banda, cartela o zona limpia. "
                "El titular se divide en una o dos líneas, con una palabra clave de mayor tamaño. "
                "Elige una pregunta o gancho fiel al vídeo, corto (idealmente 3-8 palabras, "
                "máximo 80 caracteres), no copies necesariamente el título completo del vídeo. "
                "Puedes añadir una segunda línea breve de apoyo (máximo 70 caracteres) si aporta "
                "contexto; si no, déjala vacía. Todo el texto en el idioma del guion. "
                "Ilustración cuidada, dibujo nítido, expresiones claras, profundidad y luz que "
                "dirija la mirada, contraste fuerte entre tipografía y fondo y pocos elementos. "
                "Debe resultar atractiva y leerse al reducirla al tamaño de una tarjeta de YouTube. "
                "Conserva la identidad y técnica de dibujo del canal, pero diseña una composición "
                "nueva para atraer al espectador. No añadas duración, controles ni interfaz de YouTube. "
                "Devuelve {titulo, descripcion, capitulos:[{bloque,titulo}], miniatura_prompt, "
                "miniatura_texto, miniatura_subtitulo, "
                "escenas_referencia:[ids de hasta 3 escenas que muestren al protagonista y el tema]}. "
                "miniatura_texto es obligatorio. El prompt describe la ilustración y la distribución "
                "tipográfica, dejando aire para ambos textos y evitando tapar caras u objetos clave.\n"
                + json.dumps({"guion": fuente["guion"], "escenas": fuente["escenas"]}, ensure_ascii=False))
            if os.environ.get("ESTUDIO_SIMULAR") == "1":
                propuesta = {"titulo": fuente["guion"].get("titulo") or "El vídeo",
                             "descripcion": "Resumen del vídeo de prueba.",
                             "miniatura_texto": "UN VIAJE INESPERADO", "miniatura_subtitulo": "",
                             "miniatura_prompt": "Una composición de prueba", "escenas_referencia": []}
            else:
                texto, _sobre = _llamar_claude(instruccion, carpeta)
                propuesta = comun.extraer_json(texto, "la publicación de YouTube")
            titulo = str(propuesta.get("titulo") or "").strip()
            descripcion = str(propuesta.get("descripcion") or "").strip()
            if not titulo or len(titulo) > 100 or not descripcion or len(descripcion) > 4000:
                raise ValueError("el modelo devolvió un título o una descripción fuera de los límites")
            if any(c in titulo + descripcion for c in "<>"):
                raise ValueError("el texto de YouTube no puede contener < ni >")
            capitulos = _capitulos(propuesta.get("capitulos"), fuente["escenas"])
            if capitulos and len(descripcion + "\n\n" + capitulos) <= 5000:
                descripcion += "\n\n" + capitulos
            prompt = str(propuesta.get("miniatura_prompt") or "").strip()
            if not prompt:
                raise ValueError("falta la propuesta de miniatura")
            titular = " ".join(str(propuesta.get("miniatura_texto") or "").split())
            apoyo = " ".join(str(propuesta.get("miniatura_subtitulo") or "").split())
            if not titular or len(titular) > 80 or len(apoyo) > 70:
                raise ValueError("la miniatura necesita un titular de 1-80 caracteres y un apoyo de hasta 70")
            ids = {e["id"] for e in fuente["escenas"]}
            seleccion = propuesta.get("escenas_referencia") or []
            if not isinstance(seleccion, list):
                raise ValueError("las referencias de miniatura no son una lista")
            cambios = {"miniatura_prompt": prompt,
                "miniatura_texto": titular, "miniatura_subtitulo": apoyo,
                "version_diseno": VERSION_DISENO,
                "escenas_referencia": [s for s in seleccion if isinstance(s, str) and s in ids][:3],
                "firma_concepto": fuente["firma"]}
            if not solo_concepto:
                cambios.update({"titulo": titulo, "descripcion": descripcion,
                                "firma_texto": fuente["firma"], "error_texto": ""})
            datos = _guardar(proyecto, cambios)
        if parte == "miniatura" or (parte == "pendientes" and not datos.get("miniatura")):
            fase = "miniatura"
            avisar(0.4, "dibujando la miniatura de YouTube")
            from . import p6_assets
            hechos = p6_assets.planos_hechos(proyecto)
            refs = list(fuente["refs"])
            for sid in datos.get("escenas_referencia", []):
                ficha = hechos.get(sid) or {}
                ruta = ficha.get("ruta")
                actual = next((e for e in fuente["escenas"] if e["id"] == sid), {})
                coincide = p6_assets._mismo_dicho(p6_assets._texto_clave(ficha),
                                                 p6_assets._texto_clave(actual))
                if coincide and ruta and os.path.isfile(proyecto.ruta(ruta)):
                    refs.append(proyecto.ruta(ruta))
            if os.environ.get("ESTUDIO_SIMULAR") == "1":
                imagen = Image.new("RGB", (1280, 720), "#63758a")
            else:
                motor = medios.motor("imagen_openai/imagen.py")
                prompt = (
                    "Create a finished editorial YouTube thumbnail, landscape 16:9: a polished "
                    "illustration WITH LARGE DESIGNED TYPOGRAPHY, not just an image or a video frame. "
                    "Match the drawing technique and character identity in the references. "
                    "Use a strong visual hook: expressive foreground character, intriguing focal "
                    "object or action, clear silhouettes, rich detail at the focal points, directed "
                    "lighting and strong readable contrast. Compose the headline in one or two "
                    "large lines on a banner, cartouche or uncluttered area, emphasizing the key "
                    "word with scale. Keep faces and the key object visible. Make the lettering "
                    "beautiful and instantly readable at 320x180. Keep all lettering well inside "
                    "the frame with a 6% safe margin, including after a centered 16:9 crop. "
                    "No timestamps, playback icons, logos or YouTube interface.\n"
                    "REQUIRED HEADLINE, render this exact text with correct spelling and accents: "
                    + json.dumps(datos["miniatura_texto"], ensure_ascii=False)
                    + "\nSECONDARY LINE, smaller but readable (omit if empty): "
                    + json.dumps(datos.get("miniatura_subtitulo") or "", ensure_ascii=False)
                    + "\nDo not add any other text. The required lettering takes precedence over "
                    "any no-text rules in the style guide or scene references.\nComposition: "
                    + datos["miniatura_prompt"] + "\nStyle guide: " + str(fuente["guia"] or ""))
                png, _meta = motor.generar(prompt, refs[:5], quality="medium", tamano="apaisado")
                imagen = Image.open(io.BytesIO(png)).convert("RGB")
            imagen = ImageOps.fit(imagen, (1280, 720), method=Image.Resampling.LANCZOS)
            nombre = "miniatura-" + uuid.uuid4().hex + ".jpg"
            imagen.save(os.path.join(carpeta, nombre), "JPEG", quality=88, optimize=True)
            _guardar(proyecto, {"miniatura": CARPETA + "/" + nombre,
                                "firma_miniatura": fuente["firma_miniatura"], "error_miniatura": ""})
    except Exception as fallo:
        _guardar(proyecto, {"error_" + fase: str(fallo)[:2000]})
        raise
    avisar(1.0, "material de YouTube preparado")
    return leer(proyecto, estado)
