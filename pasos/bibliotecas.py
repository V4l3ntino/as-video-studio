"""Recursos por escena: API oficiales, selección semántica y copias locales."""
import copy
import json
import os
import re
import threading
import time
from urllib.parse import urlsplit

import requests

try:
    from . import claves, cli_claude, medios, medios_escena, sonido
except ImportError:
    import claves
    import cli_claude
    import medios
    import medios_escena
    import sonido

DEFECTOS = {"proveedores": [], "imagenes": True, "video": True,
            "audio": False, "incorporar_ia": False, "ia_cada": 5}
OPCIONES_REPARTO = {"origen_principal", "porcentaje_bibliotecas", "modo_bibliotecas",
                    "modo_ia", "bibliotecas_cada"}


def normalizar(crudo):
    if not isinstance(crudo, dict):
        raise ValueError("bibliotecas debe ser un objeto")
    if set(crudo) - (set(DEFECTOS) | {"carga_claude"} | OPCIONES_REPARTO):
        raise ValueError("bibliotecas contiene opciones desconocidas")
    p = dict(DEFECTOS, **copy.deepcopy(crudo))
    # Los proyectos anteriores tenían la cadencia activada implícitamente.
    if "incorporar_ia" not in crudo and crudo.get("proveedores"):
        p["incorporar_ia"] = True
    if not isinstance(p["proveedores"], list) or any(
            v not in ("pixabay", "pexels") for v in p["proveedores"]):
        raise ValueError("elige Pixabay, Pexels o ambas bibliotecas")
    p["proveedores"] = list(dict.fromkeys(p["proveedores"]))
    for campo in ("imagenes", "video", "audio", "incorporar_ia"):
        if not isinstance(p[campo], bool):
            raise ValueError(f"bibliotecas.{campo} debe ser un booleano")
    if type(p["ia_cada"]) is not int or not 1 <= p["ia_cada"] <= 1000:
        raise ValueError("la frecuencia de IA debe ser un entero entre 1 y 1000 escenas")
    carga = p.get("carga_claude", 100)
    if type(carga) is not int or not 0 <= carga <= 100:
        raise ValueError("la carga de Claude debe ser un entero entre 0 y 100")
    if OPCIONES_REPARTO.intersection(crudo):
        origen = p.get("origen_principal")
        if origen not in ("bibliotecas", "ia"):
            raise ValueError("elige bibliotecas o ia como origen principal")
        porcentaje = p.get("porcentaje_bibliotecas")
        if type(porcentaje) is not int or not 0 <= porcentaje <= 100 or porcentaje % 10:
            raise ValueError("el porcentaje de bibliotecas debe avanzar de 10 en 10 entre 0 y 100")
        if (origen == "bibliotecas" and porcentaje < 50) or (origen == "ia" and porcentaje > 50):
            raise ValueError("el origen principal debe representar al menos el 50 %")
        for campo in ("modo_bibliotecas", "modo_ia"):
            if p.get(campo, "porcentaje") not in ("porcentaje", "cada"):
                raise ValueError("el reparto debe ser porcentaje o cada N escenas")
        cada = p.get("bibliotecas_cada", 5)
        if type(cada) is not int or not 1 <= cada <= 1000:
            raise ValueError("la frecuencia de bibliotecas debe ser un entero entre 1 y 1000 escenas")
    return p


def activa(params):
    p = (params or {}).get("bibliotecas") or {}
    return bool((p.get("proveedores") and (params or {}).get("generar_personajes") is not True) or p.get("audio"))


def _json(texto):
    bloque = re.search(r"\{[\s\S]*\}", texto or "")
    if not bloque:
        raise RuntimeError("el selector de bibliotecas no devolvió un objeto JSON")
    return json.loads(bloque.group())


def _agente(instruccion):
    texto, _ = cli_claude.ejecutar(instruccion, modelo="sonnet", esfuerzo="low")
    return _json(texto)


def _agente_chatgpt(instruccion):
    return medios.motor("imagen_openai/imagen.py").seleccionar_recursos(instruccion)


def buscar(proveedor, tipo, consulta, vertical, cache):
    """Cache de búsqueda de 24 h. Las credenciales nunca forman parte del fichero."""
    firma = medios.huella([proveedor, tipo, consulta, vertical])
    ruta = os.path.join(cache, firma + ".json")
    anterior = medios.leer_json(ruta, {}) or {}
    if time.time() - anterior.get("fecha", 0) < 86400:
        return anterior.get("resultados") or []
    if os.environ.get("ESTUDIO_SIMULAR") == "1":
        return []
    clave = claves.leer()[proveedor]["clave"] or os.environ.get(
        "PIXABAY_API_KEY" if proveedor == "pixabay" else "PEXELS_API_KEY", "")
    if not clave:
        raise RuntimeError(f"falta la clave de {proveedor.title()}: ponla en Configuración")
    if proveedor == "pixabay":
        url = "https://pixabay.com/api/" + ("videos/" if tipo == "video" else "")
        params = {"key": clave, "q": consulta[:100], "lang": "en", "per_page": 12}
        if tipo == "imagen":
            params["orientation"] = "vertical" if vertical else "horizontal"
        headers = {}
    else:
        url = "https://api.pexels.com/v1/" + ("videos/search" if tipo == "video" else "search")
        params = {"query": consulta[:100], "per_page": 12,
                  "orientation": "portrait" if vertical else "landscape"}
        headers = {"Authorization": clave}
    respuesta = requests.get(url, params=params, headers=headers, timeout=45)
    if respuesta.status_code != 200:
        # requests.HTTPError incluye la URL con la clave de Pixabay: no propagarla.
        raise RuntimeError(f"{proveedor.title()} respondió HTTP {respuesta.status_code}")
    datos = respuesta.json()
    salida = []
    for r in datos.get("hits" if proveedor == "pixabay" else
                       ("videos" if tipo == "video" else "photos"), []):
        if tipo == "video":
            versiones = (list((r.get("videos") or {}).values()) if proveedor == "pixabay"
                         else r.get("video_files") or [])
            versiones = [v for v in versiones if (v.get("url") or v.get("link"))
                         and v.get("width", 0) > 0 and v.get("height", 0) > 0
                         and v.get("file_type", "video/mp4") == "video/mp4"]
            if not versiones or float(r.get("duration") or 0) < 2:
                continue
            version = min(versiones, key=lambda v: abs(v["width"] * v["height"] - 1920 * 1080))
            descarga = version.get("url") or version.get("link")
        else:
            descarga = (r.get("largeImageURL") if proveedor == "pixabay" else
                        (r.get("src") or {}).get("large2x"))
        if not descarga:
            continue
        salida.append({"fuente": proveedor, "id": str(r["id"]), "tipo": tipo,
            "descripcion": r.get("tags") or r.get("alt") or r.get("url") or "",
            "pagina": r.get("pageURL") or r.get("url"),
            "autor": r.get("user") if proveedor == "pixabay" else
                     (r.get("user") or {}).get("name") if tipo == "video" else r.get("photographer"),
            "licencia": "https://pixabay.com/service/license-summary/" if proveedor == "pixabay"
                        else "https://www.pexels.com/license/",
            "descarga": descarga, "duracion": r.get("duration")})
    medios.escribir_json(ruta, {"fecha": time.time(), "resultados": salida})
    return salida


def descargar(url, destino):
    partes = urlsplit(url)
    host = (partes.hostname or "").lower()
    permitidos = ("pixabay.com", "pexels.com", "pexels.video", "vimeo.com", "vimeocdn.com")
    if partes.scheme != "https" or not any(host == h or host.endswith("." + h) for h in permitidos):
        raise ValueError("la biblioteca devolvió una URL de descarga no admitida")
    temporal = destino + ".parcial"
    try:
        with requests.get(url, timeout=120, stream=True) as respuesta:
            if respuesta.status_code != 200:
                raise RuntimeError(f"falló la descarga del recurso: HTTP {respuesta.status_code}")
            total = 0
            with open(temporal, "wb") as fh:
                for bloque in respuesta.iter_content(65536):
                    total += len(bloque)
                    if total > medios_escena.MAX_BYTES:
                        raise ValueError("el recurso supera los 200 MiB")
                    fh.write(bloque)
        os.replace(temporal, destino)
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)


def restaurar(escena, ficha):
    """El medio acompaña a la imagen conservada, también al recalcular el plan."""
    for clave in ("medio_biblioteca", "recurso_biblioteca", "audio_biblioteca"):
        if clave == "audio_biblioteca" and escena.get(clave):
            continue
        if ficha.get(clave) and not escena.get("medio_usuario"):
            escena[clave] = copy.deepcopy(ficha[clave])


class Biblioteca:
    def __init__(self, proyecto, params, plan, avisar):
        self.p = normalizar(params.get("bibliotecas") or {})
        if params.get("generar_personajes") is True:
            # Restricción del motor, independiente del formulario y de la
            # personalización. Se conserva intacta la preferencia persistida.
            self.p.update(proveedores=[], origen_principal="ia", porcentaje_bibliotecas=0, modo_ia="porcentaje")
        self.proyecto, self.avisar = proyecto, avisar
        self.raiz = os.path.join(proyecto.raiz, "recursos_biblioteca")
        self.cache = os.path.join(self.raiz, "busquedas")
        os.makedirs(self.cache, exist_ok=True)
        self.vertical = plan.get("formato") == "vertical"
        self.tamano = plan.get("resolucion") or [1920, 1080]
        visuales = [e for e in plan["escenas"] if not e.get("medio_usuario")
                    and not e.get("sigue_a") and not e.get("componente")
                    and (not e.get("cartela") or e["cartela"].get("fondo") == "imagen")]
        if "origen_principal" in self.p:
            principal_ia = self.p["origen_principal"] == "ia"
            modo = self.p.get("modo_ia" if principal_ia else "modo_bibliotecas", "porcentaje")
            if modo == "cada":
                cada = self.p.get("bibliotecas_cada", 5) if principal_ia else self.p["ia_cada"]
                self.turnos = {e["id"]: ((i + 1) % cada != 0 if principal_ia else
                                         (i + 1) % cada == 0) for i, e in enumerate(visuales)}
            else:
                cantidad_ia = (len(visuales) * (100 - self.p["porcentaje_bibliotecas"]) + 50) // 100
                self.turnos = {e["id"]: (i + 1) * cantidad_ia // len(visuales) >
                               i * cantidad_ia // len(visuales) for i, e in enumerate(visuales)}
        else:
            # No migrar implícitamente el reparto de los proyectos ya guardados.
            self.turnos = {e["id"]: self.p["incorporar_ia"] and (i + 1) % self.p["ia_cada"] == 0
                           for i, e in enumerate(visuales)}
        # Reparto estable y equilibrado sobre las escenas que buscan stock.
        # Redondear sobre el total limita la desviación a media escena.
        buscables = [e for e in visuales if not self.turnos[e["id"]]]
        cantidad = (len(buscables) * self.p.get("carga_claude", 100) + 50) // 100
        self.agentes = {e["id"]: ("claude" if
            (i + 1) * cantidad // len(buscables) > i * cantidad // len(buscables)
            else "chatgpt") for i, e in enumerate(buscables)}
        self.lock = threading.Lock()
        self.audio_lock = threading.Lock()
        self.usados = set()
        for e in plan["escenas"]:
            ficha = medios.leer_json(os.path.join(proyecto.ruta_trabajo("assets"),
                                     "escenas", e["id"] + ".json"), {}) or {}
            r = e.get("recurso_biblioteca") or ficha.get("recurso_biblioteca") or {}
            if r:
                self.usados.add((r.get("fuente"), r.get("tipo"), r.get("id")))

    def verificar_claves(self):
        if os.environ.get("ESTUDIO_SIMULAR") == "1":
            return
        almacen = claves.leer()
        usa_visuales = bool(self.agentes) and (self.p["imagenes"] or self.p["video"])
        for proveedor in self.p["proveedores"] if usa_visuales else []:
            variable = "PIXABAY_API_KEY" if proveedor == "pixabay" else "PEXELS_API_KEY"
            if not almacen[proveedor]["clave"] and not os.environ.get(variable):
                raise RuntimeError(f"falta la clave de {proveedor.title()}: ponla en Configuración")
        if self.p["audio"] and not sonido.hay_claves()[1]:
            raise RuntimeError("falta la clave de FreeSound para el audio de las escenas")

    def agente(self, escena):
        return self.agentes.get(escena["id"], "claude")

    def seleccionar(self, escena, instruccion):
        if self.agente(escena) == "chatgpt":
            return _agente_chatgpt(instruccion)
        return _agente(instruccion)

    def consulta(self, escena):
        peticion = {k: escena.get(k) for k in ("narracion", "direccion", "prompt")}
        # Conserva las cachés históricas de Claude; no mezcla consultas entre motores.
        if self.agente(escena) == "chatgpt":
            peticion["agente"] = "chatgpt"
        firma = medios.huella(peticion)
        ruta = os.path.join(self.raiz, firma + ".consulta.json")
        datos = medios.leer_json(ruta, None)
        if datos is not None:
            return datos
        if os.environ.get("ESTUDIO_SIMULAR") == "1":
            datos = {"visual": escena.get("narracion", "")[:80], "audio": ""}
        else:
            datos = self.seleccionar(escena, "Prepara búsquedas para ilustrar esta escena con recursos de stock. "
                "Devuelve solo JSON {\"visual\":\"2-6 palabras en inglés\",\"audio\":\"efecto sonoro "
                "concreto en inglés o cadena vacía\"}. Describe objetos y acciones visibles, no "
                "conceptos abstractos. No busques una persona real como sustituto de otra. "
                "Audio solo si hay un sonido diegético pertinente; nunca voz, música o narración. "
                "Escena: " + json.dumps({k: escena.get(k) for k in
                                        ("narracion", "direccion", "prompt")}, ensure_ascii=False))
        datos = {k: str(datos.get(k) or "")[:100] for k in ("visual", "audio")}
        medios.escribir_json(ruta, datos)
        return datos

    def visual(self, escena, destino):
        if (escena["id"] not in self.turnos or self.turnos[escena["id"]]
                or not self.p["proveedores"] or not (self.p["imagenes"] or self.p["video"])):
            return None
        consulta = self.consulta(escena)["visual"]
        self.avisar(0.4, f"{escena['id']}: buscando recursos con "
                    + ("Claude" if self.agente(escena) == "claude" else "ChatGPT"))
        candidatos = []
        for proveedor in self.p["proveedores"]:
            for tipo, marcado in (("imagen", self.p["imagenes"]), ("video", self.p["video"])):
                if tipo == "video" and escena.get("tarjetas_animacion"):
                    continue
                if marcado:
                    candidatos.extend(buscar(proveedor, tipo, consulta, self.vertical, self.cache))
        with self.lock:
            candidatos = [r for r in candidatos if (r["fuente"], r["tipo"], r["id"]) not in self.usados]
            if not candidatos:
                self.avisar(0.4, f"{escena['id']}: sin recursos de biblioteca; se usará Codex")
                return None
            seleccion = self.seleccionar(escena, "Elige el recurso que mejor representa la escena sin inventar "
                "hechos. No confundas personas, lugares ni épocas. Devuelve JSON "
                "{\"indice\":0,\"motivo\":\"...\"}; indice=-1 si ninguno es adecuado. "
                "Escena: " + escena.get("narracion", "") + "\nDirección visual: "
                + str(escena.get("prompt") or "") + "\nCandidatos: " + json.dumps([
                    {"indice": i, **{k: r.get(k) for k in ("tipo", "descripcion", "duracion")}}
                    for i, r in enumerate(candidatos)], ensure_ascii=False))
            indice = seleccion.get("indice", -1)
            if type(indice) is not int or not 0 <= indice < len(candidatos):
                self.avisar(0.4, f"{escena['id']}: ningún recurso adecuado; se usará Codex")
                return None
            recurso = candidatos[indice]
            self.usados.add((recurso["fuente"], recurso["tipo"], recurso["id"]))
        carpeta = os.path.join(self.raiz, medios.huella([recurso, self.tamano]))
        os.makedirs(carpeta, exist_ok=True)
        nombre = "original.mp4" if recurso["tipo"] == "video" else "original.jpg"
        ruta = os.path.join(carpeta, nombre)
        preparado = os.path.join(carpeta, "medio.json")
        medio = medios.leer_json(preparado, None)
        if not medio or not all(os.path.isfile(medio.get(k, "")) for k in ("archivo", "poster")):
            try:
                descargar(recurso["descarga"], ruta)
                medio = medios_escena.preparar(ruta, nombre, carpeta, self.tamano)
                medios.escribir_json(preparado, medio)
            except (ValueError, RuntimeError, requests.RequestException):
                self.avisar(0.4, f"{escena['id']}: recurso no utilizable; se usará Codex")
                return None
        medios.copiar(medio["poster"], destino)
        recurso = {k: v for k, v in recurso.items() if k != "descarga"}
        escena["medio_biblioteca"] = medio
        escena["recurso_biblioteca"] = recurso
        return {"origen": "biblioteca", "coste": 0, "medio_biblioteca": medio,
                "agente_busqueda": self.agente(escena),
                "busqueda_visual": consulta,
                "recurso_biblioteca": recurso, "firma": medios.huella(recurso),
                "bibliotecas_peticion": medios.huella({k: escena.get(k) for k in
                                                       ("narracion", "direccion", "prompt")})}

    def audio(self, escena):
        with self.audio_lock:
            self._audio(escena)

    def _audio(self, escena):
        if not self.p["audio"] or escena.get("audio_biblioteca"):
            return
        consulta = self.consulta(escena)["audio"]
        if not consulta or os.environ.get("ESTUDIO_SIMULAR") == "1":
            return
        ruta = os.path.join(self.raiz, medios.huella(["audio", consulta]) + ".json")
        ficha = medios.leer_json(ruta, None)
        if ficha is None:
            opciones = sonido.buscar_efectos(consulta, dur_max=min(8, max(0.3,
                float(escena.get("t_out", 0)) - float(escena.get("t_in", 0)))), cuantos=5)
            opciones = [r for r in opciones if r.get("descarga")
                        and sonido.clave_de(r) not in sonido.vetados()]
            if opciones:
                elegida = self.seleccionar(escena, "Elige un efecto diegético para esta escena. Nunca voces, "
                    "música ni una acción que no sucede. Devuelve JSON {\"indice\":0}; "
                    "indice=-1 si ninguno encaja. Escena: " + escena.get("narracion", "")
                    + "\nCandidatos: " + json.dumps([
                        {"indice": i, "titulo": r.get("titulo"), "etiquetas": r.get("etiquetas")}
                        for i, r in enumerate(opciones)], ensure_ascii=False))
                indice = elegida.get("indice", -1)
                ficha = opciones[indice] if type(indice) is int and 0 <= indice < len(opciones) else {}
            else:
                ficha = {}
            medios.escribir_json(ruta, ficha)
        if ficha:
            origen = sonido.traer(ficha, "efectos")
            destino = os.path.join(self.raiz, sonido._nombre_de(ficha))
            medios.copiar(origen, destino)
            escena["audio_biblioteca"] = dict(ficha, archivo=destino)
