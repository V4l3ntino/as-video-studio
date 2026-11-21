"""Puerta de publicación: evidencia local legible y ligada a fuentes y clips.

No certifica equivalencia artística ni acepta las evidencias del piloto/v5.
"""
import hashlib
import json
from pathlib import Path
import subprocess

PLANOS={'general','medio','rostro','movil','cocina','cuenco','tormenta','calma','canon','torcida',
    'puente','explosion','pupila','expresiones','whip_mirilla','tren_frente','tren_lateral','tren_atras'}


def leer(path):return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def comprobar(evidencias,fuentes):
    from pasos import medios
    archivo=Path(evidencias)/'blender_publicacion.json'
    if not archivo.is_file():raise ValueError('Blender no publicable: falta blender_publicacion.json con comprobaciones completas')
    prueba=leer(archivo)
    if prueba.get('fuentes')!=fuentes:raise ValueError('la evidencia de publicación Blender corresponde a otras fuentes')
    for nombre,campos in {
            'integracion':['copia_sellada','pixeles_identicos','guarda_procesos','cierre_en_error'],
            'proyecto':['congelar','duplicado_portable','poster_duplicado_identico','reconstruccion_dependencias',
                'subtitulos_p7_reales','p6_nativo_real','recuperacion_p6_sin_regenerar','clips_portables'],
            }.items():
        dato=leer(prueba[nombre])
        if dato.get('fuentes')!=fuentes or not all(dato.get(k) is True for k in campos):
            raise ValueError('incompleta o desfasada la prueba Blender de '+nombre)
        if nombre=='proyecto' and (not dato.get('preparacion_real') or not dato.get('montaje_p8_real')):
            raise ValueError('falta preparación o montaje real de proyecto Blender')
    gpu=leer(Path(evidencias)/'muestra/pruebas_gpu.json')
    if (gpu.get('backend')!='blender' or gpu.get('fuentes')!=fuentes
            or not all(gpu.get(k) is True for k in ('oclusion','profundidad','camara','volumen','determinismo','normales'))
            or gpu.get('sombra_sprite_pixeles',0)<=30
            or gpu.get('runtime',{}).get('version')!='4.5.16'
            or gpu.get('runtime',{}).get('motor')!='BLENDER_EEVEE_NEXT'):
        raise ValueError('falta sonda Blender real de GPU, alfa/Z, sombras y volumen')
    recuperacion=leer(prueba['recuperacion'])
    if recuperacion.get('fuentes')!=fuentes:raise ValueError('recuperación comprobada sobre otras fuentes')
    for caso in ('parar','timeout','error_bpy'):
        if not all(recuperacion[caso].get(k) is True for k in ('sin_huerfanos','entradas_conservadas')):
            raise ValueError('falta recuperación Blender: '+caso)
    hd=Path(prueba['hd']);renders=leer(hd/'renders.json')
    if leer(hd/'fuentes.json')!=fuentes:raise ValueError('HD renderizado con otras fuentes')
    if not PLANOS.issubset({r['plano'] for r in renders}):raise ValueError('faltan secuencias HD Blender')
    revision=leer(prueba['revision_visual'])
    if revision.get('fuentes')!=fuentes or revision.get('calidad_equivalente_verificada') is not False:
        raise ValueError('falta revisión visual explícita del candidato, sin equivalencia inventada')
    revisados=revision.get('planos',{})
    reproduccion={r['plano']:r for r in leer(prueba['reproduccion'])['secuencias']}
    for render in renders:
        name=render['plano'];clip=Path(render['clip'])
        visto=revisados.get(name,{})
        if (not visto.get('observaciones') or visto.get('sha256_clip')!=sha(clip)
                or visto.get('revisado') is not True or visto.get('fallos_bloqueantes')!=[]):
            raise ValueError('clip sin revisión visual correspondiente: '+name)
        reproducido=reproduccion.get(name,{})
        if reproducido.get('fin') is not True or reproducido.get('sha256_clip')!=sha(clip):
            raise ValueError('clip sin reproducción real correspondiente: '+name)
        raw=subprocess.check_output([medios.ffprobe(),'-v','error','-select_streams','v:0',
            '-show_entries','stream=width,height,avg_frame_rate,nb_frames','-of','json',str(clip)])
        stream=json.loads(raw)['streams'][0]
        if (stream['width'],stream['height'],stream['avg_frame_rate'])!=(1080,1920,'25/1') or int(stream['nb_frames'])<55:
            raise ValueError('secuencia HD insuficiente: '+name)
    return prueba
