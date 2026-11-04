"""Recuperación por petición de imagen: nunca repite las escenas ya resueltas."""
import os
import threading
import time
import traceback
import uuid

from nucleo.proyecto import ahora, escribir_json
from nucleo.trabajos import Cancelado
try:
    from . import avisos
except ImportError:
    import avisos


def clasificar(fallo):
    """Reintenta fallos de entrega, no rechazos explicitos ni errores de acceso."""
    cadena, vistos = [], set()
    actual = fallo
    while actual is not None and id(actual) not in vistos:
        vistos.add(id(actual))
        cadena.append(actual)
        actual = actual.__cause__ or actual.__context__
    tipos = {str(getattr(f, "tipo", "")) for f in cadena}
    clases = {type(f).__name__.lower() for f in cadena}
    texto = " ".join(str(f) for f in cadena).lower()
    for error in cadena:
        tipo = str(getattr(error, "tipo", ""))
        if tipo in {"cuota", "sesion", "referencias", "rechazo", "respuesta_ambigua", "modelo"}:
            return False
        if tipo in {"saturacion", "tiempo", "conexion", "servicio", "respuesta_incompleta", "interrumpido"}:
            return True
    if any(t in texto for t in ("quota_exceeded", "usage_limit", "insufficient_quota", "unauthorized",
                               "authentication", "token_expired", "content_policy", "invalid api key")):
        return False
    return bool(tipos & {"saturacion", "tiempo", "conexion", "servicio"}
        or clases & {"connectionerror", "connecttimeout", "readtimeout", "timeout", "timeouterror"}
        or any(t in texto for t in ("serveroverloaded", "at capacity", "service unavailable",
            "temporarily unavailable", "connection reset", "connection refused", "connection aborted",
            "connectionerror", "network error", "stream disconnected", "timed out", "timeout",
            "tiempo de espera", "se ha cerrado la conexión", "http 500", "http 502", "http 503", "http 504")))


def notificar_detencion(proyecto, fallo):
    """Incluye fallos fuera de la petición (disco, plan, guardián), sin duplicar avisos."""
    actual, vistos = fallo, set()
    while actual is not None and id(actual) not in vistos:
        vistos.add(id(actual))
        if getattr(actual, "_incidencia_imagen", None):
            return
        actual = actual.__cause__ or actual.__context__
    sesion = Recuperacion(proyecto, lambda *_a: None)
    sesion._registrar(fallo, "tanda de imágenes", False, 1, 0)


class Recuperacion:
    def __init__(self, proyecto, avisar):
        self.proyecto = proyecto
        self.avisar = avisar
        self._lock = threading.RLock()
        self._sondeo = threading.Lock()
        self._parar = threading.Event()
        self._cancelado = False
        self._error = None
        self._incidente = None
        self._esperando = set()
        self._reintentos = {}

    def avisar_progreso(self, valor, mensaje="", unidades=None):
        """Mantiene visible la incidencia aunque otra cadena siga resolviendo planos.

        La fraccion y el recuento siguen siendo los reales: esperar o volver a
        pedir la misma imagen no cuenta como una imagen resuelta.
        """
        with self._lock:
            esperas = list(self._reintentos.items())
        if esperas:
            unidad, datos = min(esperas, key=lambda par: par[1]["proximo"])
            faltan = max(0, int(datos["proximo"] - time.monotonic()))
            accion = (f"Solicitando de nuevo la imagen (intento {datos['intento']})."
                      if datos["solicitando"] else
                      f"Nuevo intento automático en {faltan} s (intento {datos['intento']}).")
            mensaje = (f"Esperando al servicio de imágenes: {unidad}. Tanda activa; "
                       f"{accion} Las imágenes hechas se conservan; puedes parar la tanda.")
        if unidades is None:
            return self.avisar(valor, mensaje)
        return self.avisar(valor, mensaje, unidades)

    def _guardar(self, datos=None):
        datos = datos if datos is not None else self._incidente
        if datos:
            escribir_json(self.proyecto.ruta("incidencias_imagenes", datos["id"] + ".json"), datos)

    def _progreso(self):
        try:
            from . import medios
        except ImportError:
            import medios
        base = self.proyecto.ruta_trabajo("assets", crear=False)
        plan = medios.leer_json(os.path.join(base, "plan.json"), {}) or {}
        if not isinstance(plan, dict):
            return {"total": 0, "con_imagen": 0}
        ids = [str(e["id"]) for e in plan.get("escenas", []) if e.get("id")]
        return {"total": len(ids), "con_imagen": sum(os.path.isfile(os.path.join(base, "escenas", i + ".png"))
                                                     for i in ids)}

    def _correo(self, datos, recuperado=False):
        identificador = getattr(self.proyecto, "id", os.path.basename(self.proyecto.raiz))
        nombre = (getattr(self.proyecto, "config", {}) or {}).get("nombre") or identificador
        progreso = datos["progreso"]
        cuerpo = (f"Proyecto: {nombre} ({identificador})\n"
            f"Incidencia: {datos['id']}\nInicio: {datos['inicio']}\nEstado: {datos['estado']}\n"
            f"Tipo: {datos['tipo_error']} ({datos['clase_error']})\n"
            f"Imágenes afectadas: {', '.join(datos['unidades'])}\n"
            f"Progreso conservado: {progreso['con_imagen']} de {progreso['total']} escenas con imagen\n"
            f"Intentos fallidos: {datos['intentos']}\nPróximo intento: {datos.get('proximo') or 'no programado'}\n"
            f"Error: {datos['error']}\nDiagnóstico: {datos.get('diagnostico') or 'no disponible'}\n\n"
            + ("El servicio ha vuelto a responder y la tanda continúa automáticamente.\n" if recuperado else
               "Se conservan las imágenes ya generadas. " +
               ("La tanda reintentará las peticiones pendientes automáticamente; puedes cancelarla en el Estudio.\n"
                if datos['estado'] == 'esperando' else "Esta incidencia requiere revisión antes de continuar.\n"))
            + "\nDetalle técnico:\n" + datos["detalle"])
        try:
            return avisos.enviar(f"AS Video Studio — {'recuperado' if recuperado else 'incidencia de imágenes'}: {nombre}", cuerpo)
        except Exception as fallo:
            return {"estado": "error", "mensaje": avisos.limpiar(fallo), "fecha": ahora()}

    def _registrar(self, fallo, unidad, recuperable, intento, espera):
        with self._lock:
            nuevo = self._incidente is None
            if nuevo:
                self._incidente = {"id": uuid.uuid4().hex, "inicio": ahora(), "unidades": [],
                    "progreso": self._progreso(), "intentos": 0}
            datos = self._incidente
            fallo._incidencia_imagen = datos["id"]
            detencion = not nuevo and not recuperable and datos.get("estado") != "detenida"
            if unidad not in datos["unidades"]:
                datos["unidades"].append(unidad)
            datos.update({"estado": "esperando" if recuperable else "detenida",
                "tipo_error": str(getattr(fallo, "tipo", "sin_clasificar")),
                "clase_error": type(fallo).__name__, "recuperable": recuperable,
                "error": avisos.limpiar(fallo), "detalle": avisos.limpiar("".join(
                    traceback.format_exception(type(fallo), fallo, fallo.__traceback__, limit=8))),
                "diagnostico": getattr(fallo, "diagnostico", None), "intentos": datos["intentos"] + 1,
                "ultimo_intento_unidad": intento,
                "proximo": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + espera)) if recuperable else None})
            self._esperando.add(unidad)
            if recuperable:
                self._reintentos[unidad] = {"intento": intento + 1,
                    "proximo": time.monotonic() + espera, "solicitando": False}
            self._guardar()
        if nuevo or detencion:
            resultado = self._correo(dict(datos))
            with self._lock:
                datos["correo_incidencia" if nuevo else "correo_detencion"] = resultado
                self._guardar(datos)

    def _comprobar(self):
        if self._parar.is_set():
            if self._cancelado:
                raise Cancelado("generación cancelada")
            raise RuntimeError("La tanda se detuvo por otra incidencia: " + str(self._error)) from self._error

    def _esperar(self, segundos, unidad):
        fin = time.monotonic() + segundos
        aviso = 0.0
        while True:
            self._comprobar()
            ahora_mono = time.monotonic()
            faltan = fin - ahora_mono
            if ahora_mono >= aviso:
                if not avisos.leer()["reintentos"]:
                    self._error = RuntimeError("los reintentos automáticos se han desactivado")
                    self._parar.set()
                    with self._lock:
                        self._incidente["estado"] = "detenida"
                        self._guardar()
                    raise self._error
                self.avisar_progreso(None)
                aviso = ahora_mono + 5
            if faltan <= 0:
                return
            time.sleep(min(1.0, faltan))

    def ejecutar(self, funcion, unidad):
        intento = 0
        while True:
            self._comprobar()
            try:
                if intento:
                    with self._sondeo:
                        self._comprobar()
                        with self._lock:
                            self._reintentos[unidad]["solicitando"] = True
                        self.avisar_progreso(None)
                        resultado = funcion()
                else:
                    resultado = funcion()
            except Cancelado:
                self._cancelado = True
                self._parar.set()
                with self._lock:
                    if self._incidente:
                        self._incidente["estado"] = "cancelada"
                        self._guardar()
                raise
            except (Exception, SystemExit) as fallo:
                cfg = avisos.leer()
                recuperable = cfg["reintentos"] and clasificar(fallo)
                espera = min(cfg["intervalo_maximo"], cfg["intervalo"] * 2 ** min(intento, 10))
                proximo = time.monotonic() + espera
                self._registrar(fallo, unidad, recuperable, intento + 1, espera)
                if not recuperable:
                    self._error = fallo
                    self._parar.set()
                    raise
                intento += 1
                try:
                    self._esperar(max(0.0, proximo - time.monotonic()), unidad)
                except Cancelado:
                    with self._lock:
                        self._incidente["estado"] = "cancelada"
                        self._guardar()
                    self._cancelado = True
                    self._parar.set()
                    raise
            else:
                with self._lock:
                    self._esperando.discard(unidad)
                    self._reintentos.pop(unidad, None)
                    recuperado = bool(self._incidente and not self._esperando)
                    if recuperado:
                        self._incidente.update(estado="recuperada", fin=ahora(), proximo=None)
                        self._guardar()
                        incidente = self._incidente
                        self._incidente = None
                if recuperado:
                    correo = self._correo(dict(incidente), recuperado=True)
                    with self._lock:
                        incidente["correo_recuperacion"] = correo
                        self._guardar(incidente)
                return resultado
