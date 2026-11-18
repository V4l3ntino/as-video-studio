"""Transcripción automática local de referencias: Whisper, sin API ni credenciales."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import uuid

from nucleo.proyecto import escribir_json, leer_json, ruta_contenida
from pasos import espacio_estilo

RAIZ = Path(__file__).resolve().parents[1]
REQUISITOS = RAIZ / 'requirements-whisper.txt'
EJECUTOR = RAIZ / 'motores' / 'transcripcion_whisper' / 'transcribir.py'
VERSION = 1
MODELOS = ('tiny', 'base', 'small', 'medium', 'large-v3', 'turbo')


def modelo():
    nombre = os.environ.get('ESTUDIO_WHISPER_MODELO', 'small').strip()
    if nombre not in MODELOS:
        raise ValueError('ESTUDIO_WHISPER_MODELO debe ser tiny, base, small, medium, large-v3 o turbo')
    return nombre


def validar(dato):
    if not isinstance(dato, dict) or dato.get('origen') not in ('whisper', 'manual', 'sin_audio'):
        raise ValueError('la transcripción de la referencia está incompleta')
    texto, segmentos = dato.get('texto'), dato.get('segmentos')
    if not isinstance(texto, str) or not isinstance(segmentos, list):
        raise ValueError('Whisper no ha entregado texto y segmentos válidos')
    if dato['origen'] == 'whisper' and (dato.get('motor') != 'faster-whisper' or dato.get('modelo') not in MODELOS
            or dato.get('estado') not in ('transcrito', 'sin_habla')):
        raise ValueError('falta la procedencia o el estado del reconocimiento de voz')
    duracion = dato.get('duracion_s', 0)
    if isinstance(duracion, bool) or not isinstance(duracion, (int, float)) or not math.isfinite(duracion) or duracion < 0:
        raise ValueError('duración de la transcripción no válida')
    anterior = 0
    for segmento in segmentos:
        if not isinstance(segmento, dict) or not isinstance(segmento.get('texto'), str):
            raise ValueError('segmento de transcripción no válido')
        inicio, fin = segmento.get('t_in'), segmento.get('t_out')
        if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) for t in (inicio, fin)) or not (
                0 <= inicio <= fin <= duracion + .25) or inicio < anterior:
            raise ValueError('las marcas de tiempo de Whisper no corresponden al audio')
        anterior = inicio
        palabras = segmento.get('palabras', [])
        if not isinstance(palabras, list):
            raise ValueError('las marcas de palabras deben ser una lista')
        for palabra in palabras:
            if not isinstance(palabra, dict) or not isinstance(palabra.get('texto'), str):
                raise ValueError('palabra de transcripción no válida')
            a, b = palabra.get('t_in'), palabra.get('t_out')
            if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) for t in (a, b)) or not 0 <= a <= b <= duracion + .25:
                raise ValueError('marcas de palabra de Whisper no válidas')
    if dato['origen'] == 'whisper' and texto.strip() != ' '.join(s['texto'].strip() for s in segmentos):
        raise ValueError('el texto de Whisper no corresponde a sus segmentos')
    return dato


def resumen(dato):
    return {k: dato.get(k) for k in ('origen', 'motor', 'modelo', 'idioma', 'estado')} | {
        'palabras': len(dato['texto'].split()), 'segmentos': len(dato['segmentos'])}


def leer(destino):
    ruta = Path(destino) / 'transcripcion' / 'resultado.json'
    if not ruta.is_file():
        return None
    return validar(leer_json(str(ruta), estricto=True))


def _huella_fichero(ruta, avisar):
    sello = hashlib.sha256()
    with Path(ruta).open('rb') as fuente:
        while bloque := fuente.read(1024 * 1024):
            avisar(.44, 'Preparando la transcripción del audio de referencia')
            sello.update(bloque)
    return sello.hexdigest()


def preparar_motor(destino, avisar):
    base = Path(destino) / 'whisper'
    requisitos = base / 'requisitos'
    requisitos.mkdir(parents=True, exist_ok=True)
    solicitado = REQUISITOS.read_bytes()
    marcador = base / 'instalacion.json'
    firma = hashlib.sha256(solicitado + sys.version.encode() + sys.platform.encode()).hexdigest()
    if (leer_json(str(marcador), {}) or {}).get('firma') != firma:
        (requisitos / 'requirements.txt').write_bytes(solicitado)
        espacio_estilo.instalar(base, lambda *args: avisar(.47, 'Preparando Whisper local y sus dependencias en la carpeta del estilo'))
        espacio_estilo.fijar_requisitos(base)
        escribir_json(str(marcador), dict(firma=firma))
    else:
        # Si se ha retirado únicamente dependencias/, se reconstruye desde el lock.
        espacio_estilo.instalar(base, lambda *args: avisar(.47, 'Restaurando las dependencias locales de Whisper'))
    shutil.copyfile(EJECUTOR, base / 'transcribir.py')
    return base


def reconocer(base, audio, nombre_modelo, duracion, avisar):
    trabajo = Path(base) / 'trabajo' / uuid.uuid4().hex
    trabajo.mkdir(parents=True)
    progreso, resultado = trabajo / 'progreso.json', trabajo / 'resultado.json'
    pedido = trabajo / 'pedido.json'
    escribir_json(str(pedido), dict(audio=str(Path(audio).resolve()), modelo=nombre_modelo,
        progreso=str(progreso.resolve()), resultado=str(resultado.resolve())))
    def avance(*args):
        estado = leer_json(str(progreso), {}) or {}
        segundos = min(duracion, max(0, float(estado.get('segundos', 0))))
        mensaje = ('Descargando/cargando el modelo Whisper local (solo se descarga la primera vez)'
                   if estado.get('etapa') == 'modelo' else 'Transcribiendo la voz del vídeo con Whisper')
        avisar(.5 + .12 * segundos / max(1, duracion), mensaje)
    espacio_estilo.correr([sys.executable, '-I', '-S', '-B', str((Path(base) / 'transcribir.py').resolve()),
        str(Path(base).resolve()), str(pedido.resolve())], base, avance,
        'No se pudo transcribir con Whisper local; reintenta el análisis', segundos=max(900, int(duracion * 6)))
    return validar(leer_json(str(resultado), estricto=True))


def obtener(destino, ficha, metadatos, avisar):
    destino = Path(destino)
    carpeta = destino / 'transcripcion'
    carpeta.mkdir(exist_ok=True)
    manual = (ficha.get('transcripcion') or '').strip()
    duracion = float(metadatos['duracion_s'])
    if manual:
        dato = dict(origen='manual', estado='aportada', texto=manual, segmentos=[], duracion_s=duracion, idioma=None)
    elif not metadatos.get('tiene_audio'):
        dato = dict(origen='sin_audio', estado='sin_audio', texto='', segmentos=[], duracion_s=duracion, idioma=None)
    else:
        nombre_modelo = modelo()
        video = Path(ruta_contenida(str(destino), ficha['referencia']))
        firma = espacio_estilo.huella([VERSION, nombre_modelo, _huella_fichero(video, avisar),
            hashlib.sha256(EJECUTOR.read_bytes() + REQUISITOS.read_bytes()).hexdigest()])
        existente = leer(destino)
        if existente and existente.get('firma') == firma and existente['origen'] == 'whisper':
            avisar(.62, 'Reutilizando la transcripción de Whisper ya completada')
            return existente
        from pasos import medios
        audio = carpeta / 'audio.wav'
        parcial = carpeta / 'audio.parcial.wav'
        espacio_estilo.correr([medios.ffmpeg(), '-nostdin', '-v', 'error', '-y',
            '-protocol_whitelist', 'file,pipe', '-i', str(video.resolve()), '-map', '0:a:0', '-vn',
            '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(parcial.resolve())], carpeta,
            lambda *args: avisar(.45, 'Extrayendo el audio del vídeo para Whisper'),
            'No se pudo extraer la pista de audio de referencia', segundos=max(120, int(duracion * 2)))
        os.replace(parcial, audio)
        base = preparar_motor(carpeta, avisar)
        dato = reconocer(base, audio, nombre_modelo, duracion, avisar)
        dato['firma'] = firma
    validar(dato)
    avisar(.62, 'Guardando la transcripción de la referencia')
    escribir_json(str(carpeta / 'resultado.json'), dato)
    return dato
