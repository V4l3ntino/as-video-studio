"""Contrato Higgs Avatar: imagen + audio → trabajo asíncrono → MP4.

El id remoto se conserva antes de sondear: detener o reiniciar no vuelve a
encargar un vídeo ya pagado. No se reintenta automáticamente el POST.
"""
import os
import time
from urllib.parse import quote

import requests

BASE = "https://api.boson.ai/v1/videos"


def generar(imagen, audio, destino, clave, leer_trabajo, guardar_trabajo, latido):
    cabeceras = {"Authorization": "Bearer " + clave}

    def solicitar(metodo, url, **opciones):
        try:
            respuesta = requests.request(metodo, url, headers=cabeceras,
                                         timeout=(15, 120), **opciones)
        except requests.RequestException:
            raise RuntimeError("Boson AI: conexión interrumpida; vuelve a intentar para consultar el trabajo guardado") from None
        if not respuesta.ok:
            # Nunca volcar cabeceras, petición ni claves al diagnóstico.
            raise RuntimeError(f"Boson AI respondió HTTP {respuesta.status_code}; revisa la clave, el saldo y los límites del servicio")
        return respuesta

    trabajo = leer_trabajo() or {}
    # Un nuevo montaje explícito puede reintentar un fallo terminal. Durante
    # esta invocación nunca se vuelve a crear un trabajo que acaba de fallar.
    if trabajo.get("status") == "failed":
        trabajo = {}
    if not trabajo.get("id"):
        latido("enviando imagen y audio a Boson AI")
        with open(imagen, "rb") as foto, open(audio, "rb") as voz:
            trabajo = solicitar("POST", BASE,
                data={"model": "higgs-avatar", "size": "640x640"},
                files={"ref_image": ("avatar.png", foto, "image/png"),
                       "input": ("escena.wav", voz, "audio/wav")}).json()
        if not isinstance(trabajo.get("id"), str) or not trabajo["id"]:
            raise RuntimeError("Boson AI no devolvió el identificador del vídeo")
        guardar_trabajo(trabajo)
    url = BASE + "/" + quote(trabajo["id"], safe="")
    limite = time.monotonic() + 1800
    while trabajo.get("status") != "completed":
        if trabajo.get("status") == "failed":
            raise RuntimeError("Boson AI no pudo generar el avatar; trabajo " + trabajo["id"])
        if time.monotonic() >= limite:
            raise RuntimeError("Boson AI sigue procesando el avatar; vuelve a montar para consultar el mismo trabajo")
        for _ in range(3):
            latido("esperando el avatar de Boson AI")
            time.sleep(1)
        trabajo = solicitar("GET", url).json()
        guardar_trabajo(trabajo)
    latido("descargando el avatar de Boson AI")
    temporal = destino + ".tmp"
    try:
        with solicitar("GET", url + "/content", stream=True) as respuesta:
            with open(temporal, "wb") as fh:
                for bloque in respuesta.iter_content(1024 * 1024):
                    latido("descargando el avatar de Boson AI")
                    fh.write(bloque)
        if os.path.getsize(temporal) < 32:
            raise RuntimeError("Boson AI devolvió un vídeo vacío")
        os.replace(temporal, destino)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)
    return destino
