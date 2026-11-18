"""Movimiento local medido; velocidades usan PTS reales, no un FPS supuesto."""
import hashlib
import math
from pathlib import Path
import shutil
import statistics
import sys
import uuid

from nucleo.proyecto import escribir_json, leer_json
from pasos import deteccion_escenas, espacio_estilo

EJECUTOR = deteccion_escenas.RAIZ / 'motores' / 'deteccion_escenas' / 'movimiento.py'


def medir(destino, video, metadatos, frames, escenas, firma_video, avisar):
    from pasos import medios
    destino = Path(destino)
    firma = espacio_estilo.huella([firma_video, hashlib.sha256(EJECUTOR.read_bytes()).hexdigest(),
        deteccion_escenas.contrato(), escenas['cortes'], [f['t'] for f in frames]])
    ruta = destino / 'movimiento.json'
    existente = leer_json(str(ruta), None)
    if existente and existente.get('firma') == firma:
        return existente
    base = deteccion_escenas.preparar_motor(destino, avisar)
    shutil.copyfile(EJECUTOR, base / 'movimiento.py')
    trabajo = base / 'trabajo' / uuid.uuid4().hex
    trabajo.mkdir(parents=True)
    pedido, resultado, progreso = trabajo / 'pedido.json', trabajo / 'resultado.json', trabajo / 'progreso.json'
    escribir_json(str(pedido), dict(video=str(Path(video).resolve()), ffmpeg=medios.ffmpeg(),
        indice_video=metadatos.get('indice_video', 0), resolucion=[320, 180], fotogramas_esperados=len(frames),
        cortes=[c['fotograma'] for c in escenas['cortes']], resultado=str(resultado.resolve()),
        progreso=str(progreso.resolve()), registro=str((trabajo / 'ffmpeg.log').resolve())))
    def avance(*args):
        n = (leer_json(str(progreso), {}) or {}).get('fotogramas', 0)
        avisar(.22, f'OpenCV: midiendo movimiento real · {n}/{len(frames)} fotogramas')
    espacio_estilo.correr([sys.executable, '-I', '-S', '-B', str((base / 'movimiento.py').resolve()),
        str(base.resolve()), str(pedido.resolve())], base, avance, 'No se pudo medir el movimiento con OpenCV',
        segundos=max(180, int(metadatos['duracion_s'] * 6)))
    dato = leer_json(str(resultado), estricto=True)
    if dato.get('fotogramas_procesados') != len(frames) or len(dato.get('medidas', [])) != len(frames):
        raise ValueError('las mediciones de movimiento están incompletas')
    previo = None
    for n, m in enumerate(dato['medidas']):
        if m.get('n') != n:
            raise ValueError('las mediciones de movimiento no siguen el orden de fotogramas')
        m['t'] = frames[n]['t']
        dt = frames[n]['t'] - frames[n - 1]['t'] if n else 0
        if m['valido'] and dt > 0:
            m.update(vx=m['dx'] / dt, vy=m['dy'] / dt, zoom_log_s=math.log(m['escala']) / dt)
            m['velocidad'] = math.hypot(m['vx'], m['vy'])
            if previo:
                m['aceleracion'] = (m['velocidad'] - previo['velocidad']) / dt
            previo = m
        else:
            previo = None
    dato.update(firma=firma, limites='Estimaciones a 320×180: sin seguimiento semántico de personajes, '
        'sin acceso a capas ni alpha. Un flujo global no demuestra cámara y delta de luz no demuestra opacidad.')
    escribir_json(str(ruta), dato)
    return dato


def resumir(medidas, ventana):
    locales = [m for m in medidas if ventana['t_in'] <= m['t'] < ventana['t_out']]
    validas = [m for m in locales if m.get('valido') and 'velocidad' in m]
    def media(clave):
        return statistics.mean(m.get(clave, 0) for m in validas) if validas else 0
    picos = sorted(validas, key=lambda m: m['velocidad'] + abs(m.get('aceleracion', 0)) * .1
                   + abs(m.get('zoom_log_s', 0)) + m.get('residual_px', 0) * .01, reverse=True)[:3]
    return dict(frames_medidos=len(locales), frames_fiables=len(validas),
        velocidad_media_fraccion_s=media('velocidad'), vx_fraccion_s=media('vx'), vy_fraccion_s=media('vy'),
        zoom_log_s=media('zoom_log_s'), residual_px=media('residual_px'), coherencia=media('coherencia'),
        aceleracion_max_fraccion_s2=max((abs(m.get('aceleracion', 0)) for m in validas), default=0),
        cambio_luz_max=max((abs(m.get('delta_luz', 0)) for m in locales), default=0),
        picos=[dict(n=m['n'], t=m['t'], velocidad=m['velocidad'], regiones=m.get('regiones', [])) for m in picos],
        limite='Estimaciones, no identificación de cámara/personajes/opacidad.')


def seleccionar(ventanas, maximo=12):
    """Diversidad temporal y de movimiento, sin favorecer solo el inicio."""
    if len(ventanas) <= maximo:
        return ventanas
    duracion = ventanas[-1]['t_out']
    elegidas = set()
    for fraccion in (0, .2, .4, .6, .8, 1):
        elegidas.add(min(range(len(ventanas)), key=lambda i: abs(
            (ventanas[i]['t_in'] + ventanas[i]['t_out']) / 2 - duracion * fraccion)))
    campos = ('velocidad_media_fraccion_s', 'zoom_log_s', 'residual_px',
              'aceleracion_max_fraccion_s2', 'cambio_luz_max')
    for campo in campos:
        orden = sorted(range(len(ventanas)), key=lambda i: abs(ventanas[i]['movimiento'].get(campo, 0)), reverse=True)
        candidato = next((i for i in orden if i not in elegidas), None)
        if candidato is not None:
            elegidas.add(candidato)
    for i in range(len(ventanas)):
        if len(elegidas) >= maximo:
            break
        elegidas.add(i)
    return [ventanas[i] for i in sorted(elegidas)[:maximo]]


def resumen_global(movimiento):
    """Contexto acotado; las métricas originales completas siguen en el informe."""
    ventanas = movimiento['ventanas']
    duracion = ventanas[-1]['t_out']
    bloques = []
    for b in range(60):
        locales = [v for v in ventanas if min(59, int(v['t_in'] / max(.001, duracion) * 60)) == b]
        if not locales:
            continue
        bloques.append(dict(t_in=locales[0]['t_in'], t_out=locales[-1]['t_out'], intervalos=len(locales),
            frames_fiables=sum(v['medidas']['frames_fiables'] for v in locales),
            velocidad_max=max(v['medidas']['velocidad_media_fraccion_s'] for v in locales),
            zoom_log_s_max=max((v['medidas']['zoom_log_s'] for v in locales), key=abs),
            residual_px_max=max(v['medidas']['residual_px'] for v in locales),
            aceleracion_max=max(v['medidas']['aceleracion_max_fraccion_s2'] for v in locales),
            cambio_luz_max=max(v['medidas']['cambio_luz_max'] for v in locales)))
    return dict(motor=movimiento['motor'], fotogramas_procesados=movimiento['fotogramas_procesados'],
                limites=movimiento['limites'], bloques=bloques)
