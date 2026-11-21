"""Vista previa editorial independiente del motor publicado y sus versiones."""
import hashlib
import json
from pathlib import Path
import re
import shutil

from nucleo.proyecto import escribir_json,lock_de


def sha(ruta):
    with Path(ruta).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def leer(carpeta,marca):
    carpeta=Path(carpeta)
    archivo=carpeta/'muestra_tarjeta.json'
    if not archivo.is_file():return None
    dato=json.loads(archivo.read_text(encoding='utf8'))
    # Una publicación posterior vuelve automáticamente a la muestra de su motor.
    if dato.get('espacio')!=marca:return None
    sello=dato.get('sha256','')
    if not isinstance(sello,str) or not re.fullmatch('[a-f0-9]{64}',sello):
        raise ValueError('sello de muestra de tarjeta no válido')
    ruta=f'muestras_tarjeta/{sello}/clip.mp4'
    etiqueta=dato.get('etiqueta')
    if dato.get('ruta')!=ruta or not isinstance(etiqueta,str) or not 1<=len(etiqueta)<=300:
        raise ValueError('muestra de tarjeta incompleta')
    archivo=(carpeta/ruta).resolve()
    if not archivo.is_relative_to(carpeta.resolve()) or not archivo.is_file() or sha(archivo)!=sello:
        raise ValueError('la muestra de tarjeta falta o ha cambiado')
    return dato


def instalar(carpeta,origen,etiqueta):
    from pasos import medios_escena
    carpeta=Path(carpeta);origen=Path(origen)
    if not isinstance(etiqueta,str) or not 1<=len(etiqueta)<=300:raise ValueError('etiqueta no válida')
    if origen.suffix.lower()!='.mp4':raise ValueError('la muestra debe ser MP4')
    info=medios_escena.informacion_video(str(origen))
    sello=sha(origen)
    with lock_de(str(carpeta)):
        ficha=json.loads((carpeta/'estilo.json').read_text(encoding='utf8'))
        if not ficha.get('espacio'):raise ValueError('el estilo no tiene motor publicado')
        destino=carpeta/'muestras_tarjeta'/sello
        destino.mkdir(parents=True,exist_ok=True)
        clip=destino/'clip.mp4'
        if clip.exists():
            if sha(clip)!=sello:raise ValueError('la muestra existente ha cambiado')
        else:shutil.copyfile(origen,clip)
        dato=dict(espacio=ficha['espacio'],sha256=sello,ruta=clip.relative_to(carpeta).as_posix(),
            etiqueta=etiqueta,**info)
        # Historial acumulativo de muestras; no se sobrescriben las publicadas.
        escribir_json(str(destino/'muestra.json'),dato)
        escribir_json(str(carpeta/'muestra_tarjeta.json'),dato)
        return leer(carpeta,ficha['espacio'])


def limpiar_derivada(carpeta):
    """Retira solo el campo de presentación que preparar persistió por error.

    No publica, no cambia estado/marca ni toca el descriptor o los clips. Permite
    reparar una ficha afectada sin volver a preparar el motor ni fingir éxito.
    """
    carpeta=Path(carpeta)
    with lock_de(str(carpeta)):
        ruta=carpeta/'estilo.json'
        ficha=json.loads(ruta.read_text(encoding='utf8'))
        if not isinstance(ficha,dict):raise ValueError('ficha de estilo no válida')
        if 'muestra_tarjeta' not in ficha:return None
        retirada=ficha.pop('muestra_tarjeta')
        escribir_json(str(ruta),ficha)
        return retirada
