"""Segmentación local con PySceneDetect, sin instalar nada en el servicio."""
import hashlib
import math
from pathlib import Path
import shutil
import sys
import uuid

from nucleo.proyecto import escribir_json, leer_json
from pasos import espacio_estilo

RAIZ = Path(__file__).resolve().parents[1]
REQUISITOS = RAIZ / 'requirements-escenas.txt'
EJECUTOR = RAIZ / 'motores' / 'deteccion_escenas' / 'detectar.py'
CONFIGURACION = dict(resolucion=[320, 180],
    adaptativo=dict(adaptive_threshold=3., min_scene_len=1, window_width=2, min_content_val=15.),
    contenido_bordes=dict(threshold=27., min_scene_len=1),
    fundido_negro=dict(threshold=12., min_scene_len=1),
    fundido_blanco=dict(threshold=12., min_scene_len=1))


def contrato():
    return dict(configuracion=CONFIGURACION,
                codigo=hashlib.sha256(EJECUTOR.read_bytes() + REQUISITOS.read_bytes()).hexdigest())


def preparar_motor(destino, avisar):
    base = Path(destino) / 'pyscenedetect'
    requisitos = base / 'requisitos'
    requisitos.mkdir(parents=True, exist_ok=True)
    solicitado = REQUISITOS.read_bytes()
    firma = hashlib.sha256(solicitado + sys.version.encode() + sys.platform.encode()).hexdigest()
    marcador = base / 'instalacion.json'
    if (leer_json(str(marcador), {}) or {}).get('firma') != firma:
        (requisitos / 'requirements.txt').write_bytes(solicitado)
        espacio_estilo.instalar(base, lambda *a: avisar(.12, 'Preparando PySceneDetect local y OpenCV headless para este estilo'))
        espacio_estilo.fijar_requisitos(base)
        escribir_json(str(marcador), dict(firma=firma))
    else:
        espacio_estilo.instalar(base, lambda *a: avisar(.12, 'Restaurando las dependencias locales de PySceneDetect'))
    shutil.copyfile(EJECUTOR, base / 'detectar.py')
    return base


def validar(dato, total):
    if (not isinstance(dato, dict) or dato.get('motor') != 'PySceneDetect' or dato.get('version') != '0.6.7'
            or dato.get('completo') is not True or dato.get('fotogramas_procesados') != total
            or dato.get('configuracion') != CONFIGURACION or not isinstance(dato.get('cortes'), list)):
        raise ValueError('PySceneDetect no ha analizado todos los fotogramas con el contrato esperado')
    anterior = 0
    for corte in dato['cortes']:
        if not isinstance(corte, dict):
            raise ValueError('corte de PySceneDetect no válido')
        n = corte.get('fotograma')
        origenes = corte.get('detectores')
        if (type(n) is not int or not anterior < n < total or not isinstance(origenes, list) or not origenes
                or any(s not in CONFIGURACION or s == 'resolucion' for s in origenes)
                or not isinstance(corte.get('metricas'), dict)
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in corte['metricas'].values())):
            raise ValueError('los cortes de PySceneDetect no corresponden a la referencia')
        anterior = n
    return dato


def detectar(destino, video, metadatos, medidas, firma_video, avisar):
    from pasos import medios
    destino = Path(destino)
    firma = espacio_estilo.huella([firma_video, contrato(), metadatos.get('indice_video', 0), len(medidas)])
    ruta = destino / 'escenas.json'
    existente = leer_json(str(ruta), None)
    if existente and existente.get('firma') == firma and (destino / 'metricas_escenas.csv').is_file():
        avisar(.21, 'Reutilizando la segmentación completa de PySceneDetect')
        return validar(existente, len(medidas))
    base = preparar_motor(destino, avisar)
    trabajo = base / 'trabajo' / uuid.uuid4().hex
    trabajo.mkdir(parents=True)
    progreso, resultado = trabajo / 'progreso.json', trabajo / 'resultado.json'
    pedido = trabajo / 'pedido.json'
    metricas = trabajo / 'metricas.csv'
    escribir_json(str(pedido), dict(video=str(Path(video).resolve()), ffmpeg=medios.ffmpeg(),
        indice_video=metadatos.get('indice_video', 0), configuracion=CONFIGURACION,
        fotogramas_esperados=len(medidas), progreso=str(progreso.resolve()), resultado=str(resultado.resolve()),
        metricas=str(metricas.resolve()), registro_ffmpeg=str((trabajo / 'ffmpeg.log').resolve())))
    def avance(*args):
        procesados = (leer_json(str(progreso), {}) or {}).get('fotogramas', 0)
        avisar(.12 + .1 * min(1, procesados / len(medidas)),
            f'PySceneDetect: cortes adaptativos y fundidos · {procesados}/{len(medidas)} fotogramas')
    espacio_estilo.correr([sys.executable, '-I', '-S', '-B', str((base / 'detectar.py').resolve()),
        str(base.resolve()), str(pedido.resolve())], base, avance,
        'No se pudo completar la segmentación con PySceneDetect', segundos=max(180, int(metadatos['duracion_s'] * 6)))
    dato = validar(leer_json(str(resultado), estricto=True), len(medidas))
    dato['firma'] = firma
    # Los números de frame se cruzan con los PTS reales de FFmpeg, nunca n/FPS:
    # MKV y referencias de frecuencia variable conservan su reloj original.
    for corte in dato['cortes']:
        corte['t'] = medidas[corte['fotograma']]['t']
    limites = [0] + [c['fotograma'] for c in dato['cortes']] + [len(medidas)]
    dato['escenas'] = [dict(id=f'P{i:04d}', frame_in=a, frame_out=b,
        t_in=medidas[a]['t'], t_out=medidas[b]['t'] if b < len(medidas) else metadatos['duracion_s'])
        for i, (a, b) in enumerate(zip(limites, limites[1:]), 1)]
    shutil.copyfile(metricas, destino / 'metricas_escenas.csv')
    escribir_json(str(ruta), dato)
    return dato
