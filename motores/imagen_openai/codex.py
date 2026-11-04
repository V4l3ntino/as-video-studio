"""Imágenes con la sesión ChatGPT del CLI oficial, sin convertirla en API key.

Contrato: app-server por stdio; solo se aceptan imágenes del evento nativo
imageGeneration y turn/completed. Los tokens los renueva el propio CLI.
"""
import io
import atexit
import contextlib
import base64
import hashlib
import math
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from collections import deque

from PIL import Image, ImageOps, ImageDraw

_POOL = threading.Condition()
_LIBRES = []
_ACTIVAS = 0
_SESION_VERSION = 0
_LOGIN_LOCK = threading.RLock()
_LOGIN = None
_ESTADO_LOGIN = {}
MAX_REFERENCIAS = 5


def concurrencia():
    """Tope conservador dentro de UNA tanda, sin romper las cadenas de continuidad."""
    try:
        return max(1, min(2, int(os.environ.get("ESTUDIO_CODEX_CONCURRENCIA", "2"))))
    except ValueError:
        return 2


def _clave_pool():
    env = entorno()
    return (env.get("CODEX_HOME") or os.path.expanduser("~/.codex"),
            os.environ.get("ESTUDIO_CODEX") or shutil.which("codex"), _SESION_VERSION)


def cerrar_conexiones():
    """Cierra solo conexiones ociosas; las activas se descartan al devolverlas."""
    global _SESION_VERSION
    with _POOL:
        _SESION_VERSION += 1
        ociosas = list(_LIBRES)
        _LIBRES.clear()
    for conexion, _ in ociosas:
        conexion.cerrar()


@contextlib.contextmanager
def _prestar_conexion():
    global _ACTIVAS
    sobrantes = []
    conexion = None
    with _POOL:
        while _ACTIVAS >= concurrencia():
            _POOL.wait()
        clave = _clave_pool()
        _ACTIVAS += 1
        while _LIBRES:
            candidata, origen = _LIBRES.pop()
            if origen == clave and candidata.proceso.poll() is None:
                conexion = candidata
                break
            sobrantes.append(candidata)
    reutilizada = conexion is not None
    correcta = False
    try:
        for vieja in sobrantes:
            vieja.cerrar()
        if conexion is None:
            conexion = Conexion()
        yield conexion, reutilizada
        correcta = True
    finally:
        conservar = (correcta and conexion is not None and not getattr(conexion, "descartar", False)
                     and conexion.proceso.poll() is None and clave == _clave_pool())
        with _POOL:
            if conservar:
                _LIBRES.append((conexion, clave))
            _ACTIVAS -= 1
            _POOL.notify_all()
        if conexion is not None and not conservar:
            conexion.cerrar()


atexit.register(cerrar_conexiones)


def entorno():
    salida = dict(os.environ)
    # Nunca pasar de la suscripción al pago por uso por una variable heredada.
    for clave in list(salida):
        if clave.startswith("OPENAI_API_KEY") or clave in (
                "CODEX_API_KEY", "OPENAI_BASE_URL", "OPENAI_ORG_ID",
                "OPENAI_ORGANIZATION", "OPENAI_PROJECT_ID"):
            salida.pop(clave, None)
    if salida.get("ESTUDIO_CODEX_HOME"):
        salida["CODEX_HOME"] = salida["ESTUDIO_CODEX_HOME"]
    return salida


class ErrorCodex(RuntimeError):
    """Mensaje mostrable, sin credenciales ni salida cruda del proceso."""

    def __init__(self, mensaje, tipo="desconocido", diagnostico=None):
        super().__init__(mensaje)
        self.tipo = tipo
        self.diagnostico = diagnostico


def _limpiar(texto, limite=2000):
    texto = str(texto or "")
    texto = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", texto)
    texto = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[oculto]", texto)
    texto = re.sub(r"\b(?:sk-[\w-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+)\b", "[oculto]", texto)
    texto = re.sub(r'(?i)([\"\']?(?:access_token|refresh_token|id_token|api_key|client_secret)[\"\']?\s*[:=]\s*[\"\']?)[^\s,\"\'}]+',
                   r"\1[oculto]", texto)
    return texto[:limite]


def _error_de(detalle, defecto="Codex no ha completado la imagen"):
    """Clasifica evidencias explícitas; una imagen ausente no prueba falta de cuota."""
    texto = _limpiar(json.dumps(detalle, ensure_ascii=False) if isinstance(detalle, dict) else detalle)
    bajo = texto.lower()
    if ("referenc" in bajo and re.search(r"(?:máximo|max(?:imum)?|at most)\D{0,15}\d", bajo)):
        tipo, mensaje = "referencias", "El encargo supera el límite de referencias de la herramienta de imágenes."
    elif "model_not_found" in bajo or ("model" in bajo and "not supported" in bajo):
        tipo, mensaje = "modelo", "Codex ha solicitado un modelo no compatible con esta cuenta. Revisa su configuración y reinicia el servicio."
    elif any(p in bajo for p in ("usagelimitexceeded", "usage_limit", "quota_exceeded",
                               "quota exceeded", "usage limit", "rate_limit_reached",
                               "rate limit", "limit reached", "cuota agotada")):
        tipo, mensaje = "cuota", "Codex ha comunicado un límite de uso. Retoma cuando se renueve."
    elif any(p in bajo for p in ("unauthorized", "token_expired", "not authenticated",
                                 "not logged in", "authentication", "sesión caducada")):
        tipo, mensaje = "sesion", "La sesión de ChatGPT no es válida. Conéctala de nuevo en Configuración."
    elif any(p in bajo for p in ("content_policy", "content_filter", "moderation_blocked",
                                 "safety", "refusal", "can't help", "cannot help",
                                 "no puedo ayudar", "rechazo", "filtro de seguridad",
                                 "política de contenido", "politica de contenido")):
        tipo, mensaje = "rechazo", "Codex ha rechazado este encargo de imagen. Revisa su descripción."
    elif any(p in bajo for p in ("serveroverloaded", "at capacity", "overloaded")):
        tipo, mensaje = "saturacion", "El servicio de imágenes está saturado temporalmente."
    elif any(p in bajo for p in ("timeout", "timed out", "tiempo de espera")):
        tipo, mensaje = "tiempo", "El servicio agotó el tiempo de espera de esta imagen."
    elif any(p in bajo for p in ("service unavailable", "temporarily unavailable", "http 500", "http 502", "http 503", "http 504")):
        tipo, mensaje = "servicio", "El servicio de imágenes no está disponible temporalmente."
    elif any(p in bajo for p in ("connection", "network", "stream disconnected", "transport")):
        tipo, mensaje = "conexion", "Se interrumpió la conexión con Codex. Lo ya generado se conserva."
    else:
        tipo, mensaje = "respuesta_incompleta", defecto + ". La causa no está confirmada; no se atribuye a la cuota."
    if isinstance(detalle, dict) and isinstance(detalle.get("resetsAt"), (int, float)):
        mensaje += " Reinicio indicado: " + time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(detalle["resetsAt"])) + "."
    if texto:
        mensaje += " Detalle: " + texto[:700]
    return ErrorCodex(mensaje, tipo)


def _guardar_diagnostico(datos):
    carpeta = os.path.join(os.environ.get("ESTUDIO_SECRETOS") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "secretos"), "codex_imagenes")
    try:
        os.makedirs(carpeta, mode=0o700, exist_ok=True)
        ruta = os.path.join(carpeta, datos["id"] + ".json")
        temporal = ruta + ".tmp"
        with open(os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
    except OSError:
        # Un disco sin espacio no debe ocultar el error original del proveedor.
        pass


def _limites(conexion):
    try:
        crudo = conexion.pedir("account/rateLimits/read", segundos=15)
    except ErrorCodex:
        return {"disponibles": False, "nota": "Codex no ha devuelto sus límites."}
    if not isinstance(crudo, dict):
        return {"disponibles": False}
    # Lista blanca: nunca publicar accountId, tokens ni créditos de reinicio.
    return {"disponibles": True, "uso_permitido": crudo.get("ordinaryUsageAllowed"),
            "ventanas": {k: {c: v.get(c) for c in ("limitId", "primary", "secondary", "rateLimitReachedType")}
                         for k, v in (crudo.get("rateLimitsByLimitId") or {
                             "codex": crudo.get("rateLimits") or {}}).items() if isinstance(v, dict)},
            "nota": "Los límites generales de Codex no garantizan cuota de la herramienta de imágenes."}


class Conexion:
    def __init__(self):
        ejecutable = os.environ.get("ESTUDIO_CODEX") or shutil.which("codex")
        if not ejecutable:
            raise ErrorCodex("Falta Codex CLI en el servidor. Instálalo con npm install -g @openai/codex.")
        self.cola = queue.Queue()
        self.pendientes = deque()
        self.errores_cli = deque(maxlen=12)
        self.descartar = False
        self.numero = 0
        try:
            self.proceso = subprocess.Popen(
                [ejecutable, "app-server", "-c", 'model_provider="openai"',
                 "-c", "features.image_generation=true"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=entorno(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as fallo:
            raise ErrorCodex("No se ha podido arrancar Codex CLI en el servidor.") from fallo
        threading.Thread(target=self._leer, daemon=True).start()
        threading.Thread(target=self._leer_errores, daemon=True).start()
        try:
            self.pedir("initialize", {"clientInfo": {
                "name": "as_video_studio", "title": "AS Video Studio", "version": "1.0"}})
            self.enviar({"method": "initialized", "params": {}})
        except Exception:
            self.cerrar()
            raise

    def _leer(self):
        try:
            for linea in self.proceso.stdout:
                try:
                    self.cola.put(json.loads(linea))
                except ValueError:
                    continue
        finally:
            self.cola.put(None)

    def _leer_errores(self):
        for linea in self.proceso.stderr:
            self.errores_cli.append(_limpiar(linea.strip(), 500))

    def enviar(self, datos):
        try:
            self.proceso.stdin.write(json.dumps(datos) + "\n")
            self.proceso.stdin.flush()
        except (OSError, ValueError) as fallo:
            raise ErrorCodex("Se ha cerrado la conexión con Codex.") from fallo

    def recibir(self, plazo):
        try:
            dato = self.pendientes.popleft() if self.pendientes else \
                self.cola.get(timeout=max(0.01, plazo - time.monotonic()))
        except queue.Empty as fallo:
            raise ErrorCodex("Codex ha agotado el tiempo de espera. Retoma la generación; lo ya hecho se conserva.") from fallo
        if dato is None:
            raise ErrorCodex("Codex se ha cerrado antes de terminar. Comprueba su instalación y la sesión de ChatGPT.")
        # No hay aprobaciones interactivas en el motor de imágenes.
        if "method" in dato and "id" in dato:
            self.enviar({"id": dato["id"], "error": {
                "code": -32601, "message": "Esta integración solo admite generación nativa de imágenes."}})
        return dato

    def pedir(self, metodo, params=None, segundos=30):
        self.numero += 1
        numero = self.numero
        self.enviar({"id": numero, "method": metodo, "params": params or {}})
        plazo = time.monotonic() + segundos
        pendientes = []
        try:
            while True:
                dato = self.recibir(plazo)
                if dato.get("id") == numero:
                    if "error" in dato:
                        raise _error_de(dato["error"], "Codex ha rechazado " + metodo)
                    return dato.get("result") or {}
                if "id" not in dato:
                    pendientes.append(dato)
        finally:
            # Una notificación puede adelantarse a la respuesta de su petición.
            self.pendientes.extend(pendientes)

    def cuenta(self):
        return self.pedir("account/read", {"refreshToken": False}).get("account") or {}

    def cerrar(self):
        if self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proceso.kill()
                self.proceso.wait()
        self.proceso.stdin.close()
        self.proceso.stdout.close()
        self.proceso.stderr.close()


def estado():
    with _LOGIN_LOCK:
        intento = dict(_ESTADO_LOGIN)
    try:
        conexion = Conexion()
        try:
            cuenta = conexion.cuenta()
            limites = _limites(conexion) if cuenta.get("type") == "chatgpt" else {}
        finally:
            conexion.cerrar()
        conectada = cuenta.get("type") == "chatgpt"
        return {"conectada": conectada, "email": cuenta.get("email") if conectada else None,
                "plan": cuenta.get("planType") if conectada else None,
                "mensaje": "Sesión de ChatGPT conectada" if conectada else
                    "Conecta tu cuenta de ChatGPT para generar imágenes con Codex.",
                "intento": intento, "limites": limites}
    except ErrorCodex as fallo:
        return {"conectada": False, "mensaje": str(fallo), "intento": intento}


def iniciar_login():
    global _LOGIN, _ESTADO_LOGIN
    with _LOGIN_LOCK:
        if _LOGIN is not None:
            return dict(_ESTADO_LOGIN)
        conexion = Conexion()
        try:
            resultado = conexion.pedir("account/login/start", {"type": "chatgptDeviceCode"}, segundos=60)
        except Exception:
            conexion.cerrar()
            raise
        _LOGIN = conexion
        _ESTADO_LOGIN = {"estado": "esperando", "url": resultado["verificationUrl"],
                         "codigo": resultado["userCode"]}
        threading.Thread(target=_esperar_login, args=(conexion,), daemon=True).start()
        return dict(_ESTADO_LOGIN)


def _esperar_login(conexion):
    global _LOGIN, _ESTADO_LOGIN
    try:
        plazo = time.monotonic() + 15 * 60
        while True:
            evento = conexion.recibir(plazo)
            if evento.get("method") == "account/login/completed":
                bien = (evento.get("params") or {}).get("success") is True
                with _LOGIN_LOCK:
                    _ESTADO_LOGIN = {"estado": "listo" if bien else "error",
                                     "mensaje": "Cuenta conectada" if bien else
                                         "No se ha completado el acceso. Pide otro código."}
                if bien:
                    cerrar_conexiones()
                break
    except ErrorCodex as fallo:
        with _LOGIN_LOCK:
            _ESTADO_LOGIN = {"estado": "error", "mensaje": str(fallo)}
    finally:
        conexion.cerrar()
        with _LOGIN_LOCK:
            _LOGIN = None


def _items_del_turno(conexion, hilo, turno, diagnostico):
    """Solo lectura del MISMO turno; nunca repetir turn/start ni buscar PNG ajenos."""
    if not turno:
        return []
    items, cursor = [], None
    try:
        for _ in range(20):
            pagina = conexion.pedir("thread/items/list", {
                "threadId": hilo, "turnId": turno, "limit": 100, "cursor": cursor})
            for entrada in pagina.get("data") or []:
                if entrada.get("turnId") == turno and isinstance(entrada.get("item"), dict):
                    items.append(entrada["item"])
            cursor = pagina.get("nextCursor")
            if not cursor:
                return items
    except ErrorCodex as fallo:
        diagnostico["consulta_historial"] = _limpiar(fallo, 500)
    # Compatibilidad con versiones que solo ofrecen la lectura antigua.
    try:
        lectura = conexion.pedir("thread/read", {"threadId": hilo, "includeTurns": True})
        for entrada in (lectura.get("thread") or {}).get("turns") or []:
            if entrada.get("id") == turno:
                return entrada.get("items") or []
    except ErrorCodex as fallo:
        diagnostico["consulta_historial_legacy"] = _limpiar(fallo, 500)
    return items


def _disponible(item):
    return (item.get("status") == "completed" and not item.get("failure") and (
        bool(item.get("result")) or os.path.isfile(item.get("savedPath") or "")))


def _preparar_referencias(referencias, carpeta):
    """Como máximo cinco adjuntos, sin descartar ninguna referencia lógica."""
    rutas = []
    individuales = min(len(referencias), MAX_REFERENCIAS if len(referencias) <= MAX_REFERENCIAS else MAX_REFERENCIAS - 1)
    for indice, ruta in enumerate(referencias[:individuales]):
        destino = os.path.join(carpeta, f"referencia_{indice + 1:02d}.png")
        with Image.open(ruta) as imagen:
            imagen.convert("RGB").save(destino, "PNG")
        rutas.append(destino)
    mapa = ""
    restantes = referencias[individuales:]
    if restantes:
        columnas = min(3, math.ceil(math.sqrt(len(restantes))))
        ancho, alto, etiqueta = 640, 480, 28
        filas = math.ceil(len(restantes) / columnas)
        hoja = Image.new("RGB", (columnas * ancho, filas * (alto + etiqueta)), "#eeeeee")
        dibujo = ImageDraw.Draw(hoja)
        posiciones = []
        for indice, ruta in enumerate(restantes):
            col, fila = indice % columnas, indice // columnas
            x, y = col * ancho, fila * (alto + etiqueta)
            numero = individuales + indice + 1
            with Image.open(ruta) as imagen:
                imagen = ImageOps.contain(imagen.convert("RGB"), (ancho, alto))
                hoja.paste(imagen, (x + (ancho - imagen.width) // 2, y + etiqueta + (alto - imagen.height) // 2))
            dibujo.text((x + 8, y + 6), f"REF {numero}", fill="black")
            posiciones.append(f"referencia original {numero}: REF {numero}, fila {fila + 1}, columna {col + 1}")
        destino = os.path.join(carpeta, "referencias_agrupadas.png")
        hoja.save(destino, "PNG")
        rutas.append(destino)
        mapa = (
            f"IMPORTANTE: el encargo usa {len(referencias)} referencias lógicas pero se adjuntan {len(rutas)} imágenes. "
            f"Las referencias 1 a {individuales} son los primeros {individuales} adjuntos, en el mismo orden. "
            f"El adjunto {len(rutas)} es una lámina que contiene las restantes: " + "; ".join(posiciones) + ". "
            "Todos los números de referencia del encargo conservan esta numeración ORIGINAL. "
            "Usa cada recuadro para el papel que le asigna el encargo. No copies la cuadrícula, las etiquetas REF ni los márgenes: "
            "la salida debe ser UNA sola ilustración sin paneles.\n\n")
    return rutas, mapa


def generar(prompt, referencias, quality, tamano):
    """Un encargo, un turno y una imagen nativa; recuperación sin regeneración."""
    with tempfile.TemporaryDirectory(prefix="estudio_codex_") as carpeta, contextlib.ExitStack() as pila:
        t0 = time.monotonic()
        diagnostico = {"id": uuid.uuid4().hex, "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "peticion": hashlib.sha256((prompt + quality + tamano).encode()).hexdigest(),
                       "refs": len(referencias), "estado": "iniciando", "items": []}
        _guardar_diagnostico(diagnostico)
        conexion = None
        try:
            conexion, reutilizada = pila.enter_context(_prestar_conexion())
            diagnostico["conexion_reutilizada"] = reutilizada
            diagnostico["conexion_segundos"] = round(time.monotonic() - t0, 3)
            if conexion.cuenta().get("type") != "chatgpt":
                raise ErrorCodex("Conecta tu cuenta de ChatGPT en Configuración > Imágenes.", "sesion")
            limites = _limites(conexion)
            diagnostico["limites"] = limites
            if limites.get("uso_permitido") is False:
                raise ErrorCodex("Codex indica que el uso incluido no está disponible ahora. No se ha solicitado ninguna imagen.", "cuota")
            rutas, mapa = _preparar_referencias(referencias, carpeta)
            diagnostico["refs_enviadas"] = len(rutas)
            diagnostico["refs_agrupadas"] = bool(mapa)
            instrucciones = (mapa +
                "Genera exactamente una imagen con la herramienta nativa image_gen de Codex. "
                "No uses APIs, scripts, SVG, PIL ni otros sustitutos para dibujar. "
                "Si la herramienta no está disponible o no queda cuota, informa del error y termina. "
                "Usa las referencias adjuntas en el orden indicado por el encargo. "
                f"Calidad solicitada: {quality}. Tamaño solicitado: {tamano}. "
                "No generes variantes ni hagas llamadas adicionales.\n\nEncargo:\n" + prompt)
            hilo = conexion.pedir("thread/start", {
                "cwd": carpeta, "approvalPolicy": "never", "sandbox": "read-only",
                "ephemeral": True, "config": {"features.shell_tool": False,
                    "features.multi_agent": False, "features.apps": False,
                    "features.plugins": False},
                "developerInstructions": "Solo genera la imagen solicitada usando image_gen."})
            diagnostico["hilo"] = hilo["thread"]["id"]
            entradas = [{"type": "text", "text": instrucciones}]
            entradas.extend({"type": "localImage", "path": ruta} for ruta in rutas)
            t_solicitud = time.monotonic()
            respuesta = conexion.pedir("turn/start", {"threadId": diagnostico["hilo"], "input": entradas})
            diagnostico["turno"] = (respuesta.get("turn") or {}).get("id")
            diagnostico["estado"] = "generando"
            _guardar_diagnostico(diagnostico)
            plazo = time.monotonic() + 900
            items, mensajes, fallos, uso = {}, {}, [], {}

            def recoger(item):
                if item.get("type") == "imageGeneration":
                    items[item.get("id") or "imagen"] = item
                elif item.get("type") == "agentMessage" and item.get("text"):
                    mensajes[item.get("id") or hashlib.sha256(item["text"].encode()).hexdigest()] = _limpiar(item["text"])

            while True:
                evento = conexion.recibir(plazo)
                params = evento.get("params") or {}
                if params.get("threadId") and params["threadId"] != diagnostico["hilo"]:
                    continue
                if evento.get("method") == "item/completed":
                    recoger(params.get("item") or {})
                if evento.get("method") == "error":
                    fallos.append(params.get("error") or params)
                if evento.get("method") == "thread/tokenUsage/updated":
                    uso = (params.get("tokenUsage") or {}).get("total") or {}
                if evento.get("method") == "turn/completed":
                    turno = params.get("turn") or {}
                    diagnostico["turno"] = turno.get("id") or diagnostico["turno"]
                    diagnostico["estado_turno"] = turno.get("status")
                    for item in turno.get("items") or []:
                        recoger(item)
                    if turno.get("error"):
                        fallos.append(turno["error"])
                    break
            recuperada = False
            if not any(_disponible(i) for i in items.values()):
                for item in _items_del_turno(conexion, diagnostico["hilo"], diagnostico["turno"], diagnostico):
                    recoger(item)
                recuperada = any(_disponible(i) for i in items.values())
            diagnostico["items"] = [{k: (_limpiar(json.dumps(i[k], ensure_ascii=False)) if k == "failure" else i[k])
                                      for k in ("id", "status", "savedPath", "failure") if k in i}
                                     for i in items.values()]
            diagnostico["respuesta"] = _limpiar("\n".join(mensajes.values()))
            diagnostico["errores"] = [_limpiar(json.dumps(f, ensure_ascii=False)) for f in fallos]
            buenas = [i for i in items.values() if _disponible(i)]
            if len(buenas) != 1:
                explicito = next((i["failure"] for i in items.values() if i.get("failure")), None)
                if explicito:
                    raise _error_de(explicito)
                if len(buenas) > 1:
                    raise ErrorCodex("Codex entregó varias imágenes para un único encargo. No se elegirá una arbitrariamente.", "respuesta_ambigua")
                raise _error_de(fallos[0] if fallos else diagnostico["respuesta"],
                                "Codex terminó sin entregar una imagen nativa verificable")
            if diagnostico["estado_turno"] not in ("completed", "failed"):
                raise ErrorCodex("El turno de Codex fue interrumpido. Su imagen no se dará por terminada.", "interrumpido")
            nativa = buenas[0]
            fuente = nativa.get("savedPath")
            if not fuente or not os.path.isfile(fuente):
                crudo = nativa["result"].split("base64,", 1)[-1]
                fuente = io.BytesIO(base64.b64decode(crudo, validate=True))
                recuperada = True
            with Image.open(fuente) as imagen:
                salida = io.BytesIO()
                ancho, alto = (int(n) for n in tamano.split("x"))
                imagen = ImageOps.fit(imagen.convert("RGB"), (ancho, alto), method=Image.Resampling.LANCZOS)
                imagen.save(salida, "PNG")
            diagnostico["estado"] = "listo"
            diagnostico["recuperada"] = recuperada or diagnostico["estado_turno"] == "failed"
            diagnostico["generacion_segundos"] = round(time.monotonic() - t_solicitud, 3)
            return salida.getvalue(), {"segundos": round(time.monotonic() - t0, 1),
                "quality": quality, "refs": len(referencias), "coste": 0.0,
                "modelo": "gpt-image-2", "tamano": tamano,
                "usage": {"input_tokens": uso.get("inputTokens", 0), "output_tokens": uso.get("outputTokens", 0)},
                "facturacion": "suscripcion_chatgpt", "proveedor": "codex",
                "diagnostico": diagnostico["id"], "recuperada": diagnostico["recuperada"],
                "refs_enviadas": len(rutas), "refs_agrupadas": bool(mapa),
                "conexion_reutilizada": reutilizada,
                "conexion_segundos": diagnostico["conexion_segundos"],
                "generacion_segundos": diagnostico["generacion_segundos"]}
        except Exception as fallo:
            error = fallo if isinstance(fallo, ErrorCodex) else ErrorCodex(
                "No se ha podido leer la imagen entregada por Codex: " + _limpiar(fallo, 500), "recurso")
            diagnostico.update(estado="error", tipo_error=error.tipo, error=_limpiar(error))
            error.diagnostico = diagnostico["id"]
            raise ErrorCodex(str(error) + f" Diagnóstico: {diagnostico['id']}.", error.tipo,
                             diagnostico["id"]) from fallo
        finally:
            diagnostico["segundos"] = round(time.monotonic() - t0, 3)
            if conexion is not None:
                diagnostico["stderr"] = list(getattr(conexion, "errores_cli", ()))
                if diagnostico["estado"] == "listo":
                    try:
                        conexion.pedir("thread/unsubscribe", {"threadId": diagnostico["hilo"]})
                        conexion.pendientes.clear()
                    except ErrorCodex:
                        conexion.descartar = True
            _guardar_diagnostico(diagnostico)
