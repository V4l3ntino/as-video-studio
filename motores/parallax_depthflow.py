"""Adaptador de fichero: ejecuta DepthFlow en un Python independiente opcional."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading

_MOTOR = threading.Lock()


def generar(imagen, carpeta, opciones, duracion, fps, resolucion, latido=None):
    # Previa y montaje pueden pedir el mismo clip: no escribir dos parciales
    # sobre el mismo destino ni abrir varios contextos/modelos en la GPU.
    while not _MOTOR.acquire(timeout=1):
        if latido:
            latido()
    try:
        return _generar(imagen, carpeta, opciones, duracion, fps, resolucion, latido)
    finally:
        _MOTOR.release()


def _generar(imagen, carpeta, opciones, duracion, fps, resolucion, latido=None):
    os.makedirs(carpeta, exist_ok=True)
    contrato = dict(opciones=opciones, duracion=duracion, fps=fps,
                    resolucion=list(resolucion), version=1)
    sello = hashlib.sha256(json.dumps(contrato, sort_keys=True).encode())
    with open(imagen, "rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            sello.update(bloque)
    destino = os.path.abspath(os.path.join(carpeta, sello.hexdigest() + ".mp4"))
    if os.path.isfile(destino) and os.path.getsize(destino):
        return destino
    contrato.update(imagen=os.path.abspath(imagen), destino=destino + ".parcial.mp4")
    entorno = Path(__file__).resolve().parents[1] / ".depthflow"
    local = entorno / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = os.environ.get("ESTUDIO_DEPTHFLOW_PYTHON") or (str(local) if local.is_file() else sys.executable)
    with tempfile.TemporaryDirectory(prefix="estudio_depthflow_") as tmp:
        pedido = os.path.join(tmp, "pedido.json")
        with open(pedido, "w", encoding="utf-8") as fh:
            json.dump(contrato, fh)
        with open(os.path.join(tmp, "salida.log"), "w+", encoding="utf-8") as log:
            proceso = subprocess.Popen([python, "-X", "utf8", str(Path(__file__).resolve()), pedido],
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                limite = time.monotonic() + max(900, duracion * 60)
                while True:
                    try:
                        codigo = proceso.wait(timeout=1)
                        break
                    except subprocess.TimeoutExpired:
                        if time.monotonic() > limite:
                            raise RuntimeError("DepthFlow ha agotado el tiempo para animar esta imagen")
                        if latido:
                            latido()
                if codigo or not os.path.isfile(contrato["destino"]):
                    log.seek(0)
                    detalle = log.read()[-1800:]
                    raise RuntimeError("DepthFlow no ha podido animar la imagen. Instala el motor "
                        "según README.md y configura ESTUDIO_DEPTHFLOW_PYTHON. " + detalle)
                os.replace(contrato["destino"], destino)
            finally:
                if proceso.poll() is None:
                    proceso.kill()
                    proceso.wait()
                if os.path.isfile(contrato["destino"]):
                    os.remove(contrato["destino"])
    return destino


def ejecutar_pedido(pedido):
    # Solo se importan en el proceso del motor; el servicio no necesita torch.
    import math
    from depthflow.scene import DepthScene

    p = pedido["opciones"]
    amplitud = {"suave": 0.12, "media": 0.24, "alta": 0.4}[p["intensidad"]]

    class ParallaxScene(DepthScene):
        def update(self):
            t = min(1.0, max(0.0, self.tau))
            x = 2 * t - 1
            a = amplitud
            self.state.height = a
            self.state.steady = 0.3
            self.state.focus = 0.3
            self.state.isometric = 0.6
            self.state.zoom = 0.95
            self.state.offset = (0, 0)
            movimiento = p["movimiento"]
            if movimiento in ("zoom_delante", "zoom_atras"):
                self.state.height = a * (t if movimiento == "zoom_delante" else 1 - t)
            elif movimiento == "lateral":
                self.state.offset = (a * x, 0)
            elif movimiento == "vertical":
                self.state.offset = (0, a * x)
            elif movimiento == "diagonal":
                self.state.offset = (a * x, a * x)
            elif movimiento == "orbita":
                self.state.offset = (a * math.cos(t * math.pi), a * math.sin(t * math.pi))
            elif movimiento == "combinado":
                self.state.height = a * (0.5 + t / 2)
                self.state.offset = (a * x, a * math.sin(t * math.pi) / 2)

    scene = ParallaxScene(backend="headless")
    scene.input(image=pedido["imagen"])
    scene.main(output=pedido["destino"], time=pedido["duracion"], fps=pedido["fps"],
               width=pedido["resolucion"][0], height=pedido["resolucion"][1], ssaa=1)


if __name__ == "__main__":
    try:
        with open(sys.argv[1], encoding="utf-8") as archivo:
            ejecutar_pedido(json.load(archivo))
    finally:
        # ShaderFlow 0.13 inicia un observador de shaders no daemon al importar.
        # En un export headless debe cerrarse incluso si falla el modelo/render;
        # de lo contrario Python espera indefinidamente después de escribir el MP4.
        modulo = sys.modules.get("shaderflow.shader")
        observador = getattr(modulo, "WATCHDOG", None)
        if observador is not None:
            observador.stop()
            observador.join(timeout=5)
