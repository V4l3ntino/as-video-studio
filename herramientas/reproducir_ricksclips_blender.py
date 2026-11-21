"""Repite un intercambio piloto sellado en otra ruta; NO duplica un vídeo del Estudio."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import subprocess


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entrada',type=Path,required=True)
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--blender',type=Path,required=True)
    p.add_argument('--frame',type=int,help='repite solo ese índice del intercambio, conservando su tiempo exacto')
    a=p.parse_args();inventario=json.loads((a.entrada/'inventario_entrada.json').read_text(encoding='utf8'))
    for name,digest in inventario.items():
        ruta=PurePosixPath(name)
        if not ruta.parts or ruta.is_absolute() or '..' in ruta.parts or '\\' in name or ':' in name or ruta.parts[0] not in ('fuentes','intercambio'):
            raise ValueError('ruta relativa de inventario inválida: '+name)
        file=(a.entrada/name).resolve()
        if not file.is_relative_to(a.entrada.resolve()) or file.suffix not in ('.npy','.png','.json','.py'):
            raise ValueError('ruta de inventario inválida: '+name)
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise ValueError('entrada alterada: '+name)
    a.salida.mkdir(parents=True,exist_ok=False)
    seleccion={name:digest for name,digest in inventario.items() if a.frame is None or not name.startswith('intercambio/') or name.startswith(f'intercambio/{a.frame:04}/')}
    if not any(n.startswith('intercambio/') for n in seleccion):raise ValueError('el fotograma no existe')
    for name in seleccion:
        target=a.salida/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.entrada/name,target)
    (a.salida/'inventario_entrada.json').write_text(json.dumps(seleccion,indent=2),encoding='utf8')
    original=json.loads((a.entrada/'medidas.json').read_text(encoding='utf8'))
    env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','SECRET','API_KEY'))}
    for key in ('BLENDER_USER_CONFIG','BLENDER_USER_SCRIPTS','BLENDER_USER_DATAFILES','TEMP','TMP'):
        folder=a.salida.resolve()/'runtime'/key;folder.mkdir(parents=True);env[key]=str(folder)
    with (a.salida/'blender.log').open('w',encoding='utf8') as log:
        subprocess.run([str(a.blender.resolve()),'--background','--factory-startup','--python-exit-code','1',
            '--python',str((a.salida/'fuentes/renderizar.py').resolve()),'--',str(a.salida.resolve()),
            str(original['samples']),original['acabado']],check=True,env=env,cwd=a.salida,
            stdout=log,stderr=subprocess.STDOUT)
    result=dict(entradas_verificadas=len(inventario),entradas_copiadas=len(seleccion),frame=a.frame,ruta_distinta=True,proveedores=0,
        nota='Portabilidad del piloto bpy, NO del congelado/render nativo del Estudio')
    (a.salida/'reproduccion.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(result)


if __name__=='__main__':main()
