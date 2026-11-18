"""Mediciones OpenCV sobre todos los frames; no identifica técnicas ni personajes."""
import json
import math
from pathlib import Path
import subprocess
import sys


def medir_par(anterior, actual):
    import cv2
    import numpy as np
    alto, ancho = actual.shape
    cambio = float(np.mean(cv2.absdiff(anterior, actual)))
    dato = dict(cambio_px=cambio, luminosidad=float(np.mean(actual)),
                delta_luz=float(np.mean(actual.astype(np.float32) - anterior)),
                valido=False, puntos=0, coherencia=0., dx=0., dy=0., escala=1., rotacion_grados=0.,
                residual_px=0., fraccion_movil=0., regiones=[])
    puntos = cv2.goodFeaturesToTrack(anterior, maxCorners=160, qualityLevel=.015, minDistance=5)
    if puntos is None or len(puntos) < 6:
        return dato
    nuevos, estado, _ = cv2.calcOpticalFlowPyrLK(anterior, actual, puntos, None,
        winSize=(21, 21), maxLevel=2)
    if nuevos is None:
        return dato
    retorno, estado_vuelta, _ = cv2.calcOpticalFlowPyrLK(actual, anterior, nuevos, None,
        winSize=(21, 21), maxLevel=2)
    if retorno is None:
        return dato
    correctos = ((estado.ravel() == 1) & (estado_vuelta.ravel() == 1)
                 & (np.linalg.norm(retorno - puntos, axis=2).ravel() < 1.5))
    origen, fin = puntos[correctos].reshape(-1, 2), nuevos[correctos].reshape(-1, 2)
    dato['puntos'] = len(origen)
    if len(origen) < 6:
        return dato
    matriz, mascara = cv2.estimateAffinePartial2D(origen, fin, method=cv2.RANSAC,
        ransacReprojThreshold=1.5, maxIters=500)
    if matriz is None or mascara is None:
        return dato
    coherencia = float(np.mean(mascara))
    escala = float(math.hypot(matriz[0, 0], matriz[1, 0]))
    if not .8 <= escala <= 1.25:
        return dato  # No convertir un corte/mal seguimiento en un zoom enorme.
    predichos = origen @ matriz[:, :2].T + matriz[:, 2]
    residual = np.linalg.norm(fin - predichos, axis=1)
    # Desplazamiento del centro, no el término de traslación que depende del
    # origen de coordenadas y cambia también con un zoom centrado.
    centro = np.array([ancho / 2, alto / 2])
    desplazamiento = matriz[:, :2] @ centro + matriz[:, 2] - centro
    regiones = []
    for fila in range(3):
        for columna in range(3):
            dentro = ((origen[:, 0] >= columna * ancho / 3) & (origen[:, 0] < (columna + 1) * ancho / 3)
                      & (origen[:, 1] >= fila * alto / 3) & (origen[:, 1] < (fila + 1) * alto / 3))
            if np.sum(dentro) >= 3:
                flujo = np.median(fin[dentro] - origen[dentro], axis=0)
                regiones.append(dict(celda=f'{fila},{columna}', puntos=int(np.sum(dentro)),
                    dx=float(flujo[0] / ancho), dy=float(flujo[1] / alto),
                    residual_px=float(np.median(residual[dentro]))))
    dato.update(valido=coherencia >= .5, coherencia=coherencia,
        dx=float(desplazamiento[0] / ancho), dy=float(desplazamiento[1] / alto), escala=escala,
        rotacion_grados=float(math.degrees(math.atan2(matriz[1, 0], matriz[0, 0]))),
        residual_px=float(np.percentile(residual, 90)), fraccion_movil=float(np.mean(residual > 1.5)), regiones=regiones)
    return dato


def main():
    base, entrada = map(Path, sys.argv[1:3])
    sys.path.insert(0, str(base / 'dependencias'))
    sys.path.insert(0, str(base))
    from detectar import guardar
    import numpy as np
    pedido = json.loads(entrada.read_text(encoding='utf-8'))
    ancho, alto = pedido['resolucion']
    cortes = set(pedido['cortes'])
    orden = [pedido['ffmpeg'], '-nostdin', '-v', 'error', '-xerror', '-protocol_whitelist', 'file,pipe',
        '-i', pedido['video'], '-map', f"0:{pedido['indice_video']}", '-an', '-vf', f'scale={ancho}:{alto},format=gray',
        '-fps_mode', 'passthrough', '-pix_fmt', 'gray', '-f', 'rawvideo', 'pipe:1']
    anterior = None
    medidas = []
    with Path(pedido['registro']).open('wb') as registro:
        proceso = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=registro,
            **(dict(creationflags=subprocess.CREATE_NO_WINDOW) if sys.platform == 'win32' else {}))
        try:
            while bloque := proceso.stdout.read(ancho * alto):
                if len(bloque) != ancho * alto:
                    raise ValueError('fotograma incompleto durante las mediciones de movimiento')
                actual = np.frombuffer(bloque, dtype=np.uint8).reshape(alto, ancho)
                n = len(medidas)
                dato = medir_par(anterior, actual) if anterior is not None and n not in cortes else dict(
                    valido=False, corte=n in cortes, luminosidad=float(np.mean(actual)))
                medidas.append(dict(n=n, **dato))
                anterior = actual
                if len(medidas) % 60 == 0:
                    guardar(Path(pedido['progreso']), dict(fotogramas=len(medidas)))
            if proceso.wait():
                raise ValueError('FFmpeg no pudo decodificar toda la referencia para OpenCV')
        finally:
            proceso.stdout.close()
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait()
    if len(medidas) != pedido['fotogramas_esperados']:
        raise ValueError('las mediciones OpenCV no cubren todos los fotogramas esperados')
    guardar(Path(pedido['resultado']), dict(motor='OpenCV Lucas-Kanade + RANSAC',
        resolucion=pedido['resolucion'], fotogramas_procesados=len(medidas), medidas=medidas))


if __name__ == '__main__':
    main()
