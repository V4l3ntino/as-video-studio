"""PySceneDetect aislado; FFmpeg entrega todos los frames sin imponer un FPS."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def guardar(ruta, dato):
    temporal = ruta.with_suffix('.tmp')
    temporal.write_text(json.dumps(dato, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    for intento in range(20):
        try:
            os.replace(temporal, ruta)
            break
        except PermissionError:
            if intento == 19:
                raise
            time.sleep(.025)


def detectar(pedido):
    import numpy as np
    import scenedetect
    from scenedetect import StatsManager
    from scenedetect.detectors import AdaptiveDetector, ContentDetector, ThresholdDetector
    configuracion = pedido['configuracion']
    estadisticas = StatsManager()
    adaptativo = AdaptiveDetector(**configuracion['adaptativo'])
    contenido = ContentDetector(**configuracion['contenido_bordes'])
    negro = ThresholdDetector(**configuracion['fundido_negro'], add_final_scene=True)
    # FLOOR sobre imagen invertida evita la inicialización asimétrica de
    # CEILING en 0.6.7. Sus métricas no comparten average_rgb con las de negro.
    blanco = ThresholdDetector(**configuracion['fundido_blanco'], add_final_scene=True)
    detectores = [('adaptativo', adaptativo), ('contenido_bordes', contenido),
                  ('fundido_negro', negro), ('fundido_blanco', blanco)]
    for _, detector in detectores:
        if detector is not blanco:
            detector.stats_manager = estadisticas
            estadisticas.register_metrics(detector.get_metrics())
    eventos = {}
    def registrar(nombre, cortes):
        for n in cortes:
            eventos.setdefault(int(n), set()).add(nombre)
    ancho, alto = configuracion['resolucion']
    tamano = ancho * alto * 3
    orden = [pedido['ffmpeg'], '-nostdin', '-v', 'error', '-xerror', '-protocol_whitelist', 'file,pipe',
        '-i', pedido['video'], '-map', f"0:{pedido['indice_video']}", '-an', '-vf', f'scale={ancho}:{alto}',
        '-fps_mode', 'passthrough', '-pix_fmt', 'bgr24', '-f', 'rawvideo', 'pipe:1']
    total = 0
    progreso = Path(pedido['progreso'])
    guardar(progreso, dict(fotogramas=0))
    with Path(pedido['registro_ffmpeg']).open('wb') as registro:
        proceso = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=registro,
            **(dict(creationflags=subprocess.CREATE_NO_WINDOW) if os.name == 'nt' else {}))
        try:
            while bloque := proceso.stdout.read(tamano):
                if len(bloque) != tamano:
                    raise ValueError('FFmpeg entregó un fotograma incompleto a PySceneDetect')
                imagen = np.frombuffer(bloque, dtype=np.uint8).reshape((alto, ancho, 3))
                for nombre, detector in detectores:
                    registrar(nombre, detector.process_frame(total, 255 - imagen if detector is blanco else imagen))
                total += 1
                if total % 60 == 0:
                    guardar(progreso, dict(fotogramas=total))
            if proceso.wait():
                raise ValueError('FFmpeg no pudo decodificar toda la referencia para PySceneDetect')
        finally:
            proceso.stdout.close()
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait()
    if total != pedido['fotogramas_esperados']:
        raise ValueError(f'PySceneDetect recibió {total} frames; el barrido esperaba {pedido["fotogramas_esperados"]}')
    for nombre, detector in detectores:
        registrar(nombre, detector.post_process(total - 1))
    # AdaptiveDetector necesita vecinos a ambos lados. ContentDetector cubre
    # únicamente los extremos sin vecinos, no anula el filtro adaptativo central.
    eventos = {n: {origen for origen in origenes if origen != 'contenido_bordes' or n <= 2 or n >= total - 2}
               for n, origenes in eventos.items() if 0 < n < total}
    metricas = sorted(estadisticas.metric_keys)
    with Path(pedido['metricas']).open('w', newline='', encoding='utf-8') as archivo:
        csv_salida = csv.writer(archivo)
        csv_salida.writerow(['fotograma', *metricas])
        for n in range(total):
            csv_salida.writerow([n, *[None if v is None else float(v)
                                     for v in estadisticas.get_metrics(n, metricas)]])
    cortes = []
    for n, origenes in sorted(eventos.items()):
        if origenes:
            valores = estadisticas.get_metrics(n, metricas)
            cortes.append(dict(fotograma=n, detectores=sorted(origenes),
                metricas={k: float(v) for k, v in zip(metricas, valores) if v is not None}))
    guardar(progreso, dict(fotogramas=total))
    return dict(motor='PySceneDetect', version=scenedetect.__version__, completo=True,
                fotogramas_procesados=total, configuracion=configuracion, cortes=cortes)


def main():
    base, entrada = map(Path, sys.argv[1:3])
    sys.path.insert(0, str(base / 'dependencias'))
    pedido = json.loads(entrada.read_text(encoding='utf-8'))
    guardar(Path(pedido['resultado']), detectar(pedido))


if __name__ == '__main__':
    main()
