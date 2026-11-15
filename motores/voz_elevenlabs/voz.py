"""ElevenLabs con alineación por carácter. Contrato PCM mono de 44.100 Hz.

No importa la aplicación. Las claves se leen por el mismo contrato de fichero
que los demás motores; nunca se pasan por argumentos de procesos.
"""
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import time
from urllib.parse import quote

import requests

API = 'https://api.elevenlabs.io/v1'
MODELO = 'eleven_multilingual_v2'
SR = 44100
MAX_CARACTERES = 9000  # Multilingual v2 admite 10.000; margen para el contexto.


def cargar_api_key():
    clave = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if clave:
        return clave
    carpeta = os.environ.get('ESTUDIO_SECRETOS') or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'secretos')
    try:
        with open(os.path.join(carpeta, 'claves.json'), encoding='utf-8-sig') as f:
            ficha = json.load(f).get('elevenlabs') or {}
            clave = (ficha.get('clave') if isinstance(ficha, dict) else ficha) or ''
            if clave.strip():
                return clave.strip()
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(carpeta, '.env'), encoding='utf-8-sig') as f:
            for linea in f:
                if linea.strip().startswith('ELEVENLABS_API_KEY='):
                    clave = linea.strip().partition('=')[2].strip()
                    if clave:
                        return clave
    except OSError:
        pass
    raise RuntimeError('Introduce la API key de ElevenLabs en Configuración → Voz.')


def comprobar(respuesta):
    if respuesta.status_code == 200:
        return
    try:
        detalle = respuesta.json().get('detail') or {}
        mensaje = detalle.get('message') if isinstance(detalle, dict) else str(detalle)
    except (ValueError, AttributeError):
        mensaje = ''
    raise RuntimeError(f'ElevenLabs HTTP {respuesta.status_code}: {mensaje or respuesta.text[:300]}')


def ficha_voz(v):
    etiquetas = v.get('labels') or {}
    idiomas = v.get('verified_languages') or []
    return {'id': v['voice_id'], 'nombre': v.get('name') or v['voice_id'],
        'descripcion': v.get('description') or '',
        'idioma': etiquetas.get('language') or (idiomas[0].get('language') if idiomas else '') or '',
        'genero': etiquetas.get('gender') or '', 'pais': etiquetas.get('accent') or '',
        'publica': (v.get('is_owner') is False
                    or (v.get('is_owner') is not True and bool((v.get('sharing') or {}).get('public_owner_id')))
                    or v.get('category') not in ('cloned', 'professional')),
        'nativa': True}


def obtener_voz(voz_id, cache=None):
    clave = cargar_api_key()
    with requests.get(API + '/voices/' + quote(voz_id, safe=''),
                      headers={'xi-api-key': clave}, timeout=30) as respuesta:
        if respuesta.status_code == 404:
            raise ValueError('ElevenLabs no encuentra esa voz o tu cuenta no tiene acceso a ella.')
        comprobar(respuesta)
        datos = respuesta.json()
    if datos.get('voice_id') != voz_id:
        raise RuntimeError('ElevenLabs devolvió un ID de voz distinto del solicitado.')
    ficha = ficha_voz(datos)
    # Conserva la voz consultada en el catálogo ya descargado sin renovarle la
    # fecha: buscar una voz no debe ocultar las demás ni retrasar su refresco.
    if cache:
        try:
            with open(cache, encoding='utf-8') as f:
                guardado = json.load(f)
            if guardado.get('clave') == hashlib.sha256(clave.encode()).hexdigest()[:12]:
                guardado['voces'] = [v for v in guardado.get('voces', []) if v['id'] != voz_id] + [ficha]
                with open(cache, 'w', encoding='utf-8') as f:
                    json.dump(guardado, f, ensure_ascii=False)
        except (OSError, ValueError, KeyError, TypeError):
            pass  # la consulta sigue siendo utilizable aunque no haya caché
    return ficha


def listar_voces(cache, refrescar=False):
    clave = cargar_api_key()
    huella = hashlib.sha256(clave.encode()).hexdigest()[:12]
    try:
        with open(cache, encoding='utf-8') as f:
            guardado = json.load(f)
        if (not refrescar and guardado.get('clave') == huella
                and time.time() - guardado['epoch'] < 86400):
            return guardado['voces']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    voces, cursor, vistos = [], None, set()
    while True:
        params = {'page_size': 100}
        if cursor:
            params['next_page_token'] = cursor
        with requests.get('https://api.elevenlabs.io/v2/voices', headers={'xi-api-key': clave},
                          params=params, timeout=30) as respuesta:
            comprobar(respuesta)
            datos = respuesta.json()
        for v in datos.get('voices', []):
            if not v.get('voice_id') or v['voice_id'] in vistos:
                continue
            vistos.add(v['voice_id'])
            voces.append(ficha_voz(v))
        siguiente = datos.get('next_page_token')
        if not datos.get('has_more') or not siguiente:
            break
        if siguiente == cursor:
            raise RuntimeError('ElevenLabs repitió el cursor del catálogo de voces.')
        cursor = siguiente
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump({'epoch': time.time(), 'clave': huella, 'voces': voces}, f, ensure_ascii=False)
    return voces


def dividir(texto, maximo=MAX_CARACTERES):
    """Cortes por frase, después por espacio; nunca descarta texto."""
    partes = []
    while len(texto) > maximo:
        finales = list(re.finditer(r'[.!?][”\"\']?\s+', texto[:maximo + 1]))
        corte = finales[-1].end() if finales else texto.rfind(' ', 0, maximo + 1)
        if corte <= 0:
            raise ValueError('El texto contiene una palabra demasiado larga para ElevenLabs.')
        partes.append(texto[:corte])
        texto = texto[corte:]
    if texto:
        partes.append(texto)
    return partes


def palabras_de(alineacion):
    caracteres = alineacion.get('characters') or []
    inicios = alineacion.get('character_start_times_seconds') or []
    finales = alineacion.get('character_end_times_seconds') or []
    if not caracteres or len(caracteres) != len(inicios) or len(caracteres) != len(finales):
        raise RuntimeError('ElevenLabs devolvió una alineación incompleta; no se puede sincronizar.')
    palabras, actual, inicio, fin = [], '', None, None
    for c, s, e in zip(caracteres, inicios, finales):
        if not isinstance(c, str) or not math.isfinite(s) or not math.isfinite(e) or s < 0 or e < s:
            raise RuntimeError('ElevenLabs devolvió tiempos de carácter inválidos.')
        if c.isspace():
            if actual:
                palabras.append({'w': actual, 's': round(inicio, 3), 'e': round(fin, 3)})
            actual, inicio, fin = '', None, None
        else:
            actual += c
            inicio = s if inicio is None else inicio
            fin = e
    if actual:
        palabras.append({'w': actual, 's': round(inicio, 3), 'e': round(fin, 3)})
    if not palabras:
        raise RuntimeError('ElevenLabs devolvió audio sin marcas de palabra.')
    return palabras


def sintetizar(texto, cfg, ffmpeg, progreso):
    clave = cargar_api_key()
    partes = dividir(texto)
    pcm, palabras, posicion = [], [], 0.0
    for i, parte in enumerate(partes):
        progreso(i / len(partes), f'ElevenLabs: toma {i + 1} de {len(partes)}')
        cuerpo = {'text': parte, 'model_id': MODELO,
                  'voice_settings': {'speed': cfg.get('speed', 1.0)}}
        if i:
            cuerpo['previous_text'] = partes[i - 1][-1000:]
        if i + 1 < len(partes):
            cuerpo['next_text'] = partes[i + 1][:1000]
        # PCM 24 kHz no exige el plan Pro de la salida 44,1 kHz.
        with requests.post(API + '/text-to-speech/' + quote(cfg['voz_id'], safe='') + '/with-timestamps',
                headers={'xi-api-key': clave, 'Content-Type': 'application/json'},
                params={'output_format': 'pcm_24000'}, json=cuerpo,
                timeout=(30, 600)) as respuesta:
            comprobar(respuesta)
            datos = respuesta.json()
        marcas = palabras_de(datos.get('alignment') or datos.get('normalized_alignment') or {})
        audio = base64.b64decode(datos.get('audio_base64') or '', validate=True)
        if not audio or len(audio) % 2:
            raise RuntimeError('ElevenLabs devolvió una toma sin PCM válido.')
        convertido = subprocess.run([ffmpeg, '-v', 'error', '-f', 's16le', '-ar', '24000',
            '-ac', '1', '-i', 'pipe:0', '-f', 's16le', '-ar', str(SR), '-ac', '1', 'pipe:1'],
            input=audio, capture_output=True, timeout=120)
        if convertido.returncode or not convertido.stdout:
            raise RuntimeError('No se pudo convertir el audio de ElevenLabs: '
                               + convertido.stderr.decode('utf-8', errors='replace')[:300])
        duracion = len(convertido.stdout) / (SR * 2)
        if marcas[-1]['e'] > duracion + 0.15:
            raise RuntimeError('Las marcas de ElevenLabs exceden la duración de la toma.')
        pcm.append(convertido.stdout)
        palabras.extend(dict(p, s=round(p['s'] + posicion, 3), e=round(p['e'] + posicion, 3)) for p in marcas)
        posicion += duracion
    progreso(1, 'ElevenLabs: audio y sincronización listos')
    return b''.join(pcm), posicion, palabras
