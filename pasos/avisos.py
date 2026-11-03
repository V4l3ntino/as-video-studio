"""Configuración privada y envío SMTP de avisos del Estudio."""
import os
import re
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import parseaddr

from nucleo.proyecto import ahora, escribir_json, leer_json

_LOCK = threading.RLock()
CONSERVAR = "__CONSERVAR__"
DEFECTO = {"activo": False, "host": "smtp.gmail.com", "puerto": 465,
           "seguridad": "ssl", "usuario": "", "remitente": "", "destinatario": "",
           "clave": "", "reintentos": True, "intervalo": 60, "intervalo_maximo": 300}


def ruta():
    base = os.environ.get("ESTUDIO_SECRETOS") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secretos")
    return os.path.join(base, "avisos_correo.json")


def leer():
    with _LOCK:
        return {**DEFECTO, **(leer_json(ruta(), {}) or {})}


def resumen():
    datos = leer()
    salida = {k: datos[k] for k in DEFECTO if k != "clave"}
    if datos.get("ultimo_envio"):
        salida["ultimo_envio"] = datos["ultimo_envio"]
    salida["clave_guardada"] = bool(datos["clave"])
    salida["configurado"] = bool(datos["host"] and datos["remitente"] and datos["destinatario"]
                                and (not datos["usuario"] or datos["clave"]))
    return salida


def _correo(valor):
    texto = str(valor or "").strip()
    nombre, direccion = parseaddr(texto)
    if nombre or direccion != texto or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", texto):
        raise ValueError("introduce una dirección de correo válida, sin nombre ni saltos de línea")
    return texto


def guardar(cambios):
    with _LOCK:
        datos = leer()
        for campo in ("activo", "reintentos"):
            if campo in cambios:
                if not isinstance(cambios[campo], bool):
                    raise ValueError(f"{campo} debe ser booleano")
                datos[campo] = cambios[campo]
        for campo in ("host", "usuario", "remitente", "destinatario", "seguridad"):
            if campo in cambios:
                datos[campo] = str(cambios[campo] or "").strip()
                if any(c in datos[campo] for c in "\r\n\0"):
                    raise ValueError(f"{campo} no admite saltos de línea")
        if "clave" in cambios and cambios["clave"] != CONSERVAR:
            datos["clave"] = str(cambios["clave"] or "")
        for campo, minimo, maximo in (("puerto", 1, 65535), ("intervalo", 10, 3600),
                                      ("intervalo_maximo", 10, 3600)):
            if campo in cambios:
                valor = cambios[campo]
                try:
                    entero = int(valor)
                except (ValueError, TypeError):
                    raise ValueError(f"{campo} debe ser un número entero")
                if isinstance(valor, bool) or str(entero) != str(valor) or not minimo <= entero <= maximo:
                    raise ValueError(f"{campo} debe estar entre {minimo} y {maximo}")
                datos[campo] = entero
        if datos["intervalo_maximo"] < datos["intervalo"]:
            raise ValueError("el intervalo máximo no puede ser menor que el inicial")
        if datos["seguridad"] not in ("ssl", "starttls"):
            raise ValueError("selecciona SSL o STARTTLS")
        for campo in ("remitente", "destinatario"):
            if datos[campo]:
                datos[campo] = _correo(datos[campo])
        if datos["activo"] and not (datos["host"] and datos["remitente"] and datos["destinatario"]
                                    and (not datos["usuario"] or datos["clave"])):
            raise ValueError("para activar el correo completa el servidor, remitente, destinatario y contraseña")
        escribir_json(ruta(), datos)
    return resumen()


def limpiar(texto):
    texto = str(texto or "")
    texto = re.sub(r"(?i)(bearer\s+)\S+", r"\1[oculto]", texto)
    texto = re.sub(r"\b(?:sk-[\w-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+)\b", "[oculto]", texto)
    texto = re.sub(r'(?i)((?:access_token|refresh_token|api_key|client_secret|password|clave)["\s]*[:=]["\s]*)[^\s,\"}]+',
                   r"\1[oculto]", texto)
    clave = leer().get("clave")
    if clave:
        texto = texto.replace(clave, "[oculto]")
    return texto[:12000]


def enviar(asunto, cuerpo, prueba=False):
    """Un fallo de correo nunca interrumpe la generación de imágenes."""
    cfg = leer()
    if not cfg["activo"] and not prueba:
        return {"estado": "desactivado", "fecha": ahora()}
    if not (cfg["host"] and cfg["remitente"] and cfg["destinatario"]
            and (not cfg["usuario"] or cfg["clave"])):
        return {"estado": "sin_configurar", "fecha": ahora(), "mensaje": "Configura el correo en Ajustes."}
    mensaje = EmailMessage()
    mensaje["Subject"] = " ".join(str(asunto).split())[:180]
    mensaje["From"] = cfg["remitente"]
    mensaje["To"] = cfg["destinatario"]
    mensaje.set_content(limpiar(cuerpo))
    try:
        contexto = ssl.create_default_context()
        if cfg["seguridad"] == "ssl":
            conexion = smtplib.SMTP_SSL(cfg["host"], cfg["puerto"], timeout=10, context=contexto)
        else:
            conexion = smtplib.SMTP(cfg["host"], cfg["puerto"], timeout=10)
        with conexion:
            if cfg["seguridad"] == "starttls":
                conexion.ehlo()
                conexion.starttls(context=contexto)
                conexion.ehlo()
            if cfg["usuario"]:
                conexion.login(cfg["usuario"], cfg["clave"])
            rechazados = conexion.send_message(mensaje)
            if rechazados:
                raise RuntimeError("el servidor SMTP rechazó al destinatario")
    except Exception as fallo:
        resultado = {"estado": "error", "fecha": ahora(), "mensaje": limpiar(fallo)}
    else:
        resultado = {"estado": "enviado", "fecha": ahora(), "destinatario": cfg["destinatario"]}
    with _LOCK:
        datos = leer()
        datos["ultimo_envio"] = resultado
        escribir_json(ruta(), datos)
    return resultado


def probar():
    return enviar("AS Video Studio — prueba de avisos",
                  "Este correo confirma que los avisos de AS Video Studio llegan a esta dirección.\n"
                  "Las incidencias de imágenes incluirán el proyecto, la imagen afectada, el error, "
                  "el diagnóstico, el progreso conservado y los reintentos previstos.", prueba=True)
