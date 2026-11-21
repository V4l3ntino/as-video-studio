"""Runtime externo opt-in y reproducible. No cambia Python ni Blender globales."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import shutil
import subprocess
import urllib.request
import uuid
import zipfile

from nucleo.proyecto import lock_de,escribir_json

VERSION='4.5.16'
DISTRIBUCION=dict(plataforma='windows-x64',
    url='https://download.blender.org/release/Blender4.5/blender-4.5.16-windows-x64.zip',
    sha256='e258e90a1ebc14798ad65b3426bc5f11f5e0e013541c61cc7c3ee9bbf4ca0ce6',
    licencia='GPL-3.0-or-later')


def requisito(servidor):
    return dict(version=VERSION,servidor=servidor,distribucion=dict(DISTRIBUCION))


def validar(dato,archivos):
    if not isinstance(dato,dict) or set(dato)!={'version','servidor','distribucion'}:
        raise ValueError('requisito Blender incompleto')
    server=dato['servidor'];p=PurePosixPath(server) if isinstance(server,str) else None
    if (dato['version']!=VERSION or dato['distribucion']!=DISTRIBUCION or p is None
            or len(p.parts)!=2 or p.parts[0]!='herramientas' or p.suffix!='.py'
            or not p.stem.isidentifier() or '\\' in server or server not in archivos):
        raise ValueError('Blender requiere versión/distribución fijadas y servidor Python dentro del paquete')
    return requisito(server)


def _sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def verificar_instalacion(folder):
    folder=Path(folder)
    receipt=json.loads((folder/'_estudio_runtime.json').read_text(encoding='utf8'))
    if receipt.get('distribucion')!=DISTRIBUCION:raise ValueError('distribución Blender diferente')
    archivos=receipt.get('archivos')
    if not isinstance(archivos,dict) or 'blender-4.5.16-windows-x64/blender.exe' not in archivos:
        raise ValueError('inventario Blender incompleto')
    presentes={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='_estudio_runtime.json'}
    if presentes!=set(archivos):raise ValueError('el inventario de la distribución Blender ha cambiado')
    for name,sha in receipt['archivos'].items():
        file=(folder/name).resolve()
        if (folder/name).is_symlink() or not file.is_relative_to(folder.resolve()) or not file.is_file() or _sha(file)!=sha:
            raise ValueError('runtime Blender ausente o alterado: '+name)
    return folder/'blender-4.5.16-windows-x64/blender.exe'


def resolver(requisito_blender,avisar):
    """El requisito viaja; la ubicación del ejecutable es configuración de máquina.

    Binarios comunes inmutables por contenido; preferencias y cachés de cada render
    permanecen privadas. Una instalación alterada no se borra ni repara a escondidas.
    """
    if not isinstance(requisito_blender,dict) or requisito_blender!=requisito(requisito_blender.get('servidor')):
        raise ValueError('requisito Blender no validado')
    explicit=os.environ.get('ESTUDIO_BLENDER')
    if explicit:
        exe=Path(os.path.realpath(explicit))
        if not exe.is_file():raise ValueError('ESTUDIO_BLENDER no apunta a un ejecutable')
        result=subprocess.run([str(exe),'--version'],capture_output=True,text=True,timeout=30)
        if result.returncode or not result.stdout.splitlines() or result.stdout.splitlines()[0]!='Blender '+VERSION+' LTS':
            raise ValueError('ESTUDIO_BLENDER debe ser Blender '+VERSION+' LTS')
        return dict(ejecutable=str(exe),version=VERSION,sha256_ejecutable=_sha(exe),origen='configuracion_explicita')
    if os.name!='nt' or platform.machine().lower() not in ('amd64','x86_64'):
        raise ValueError('este requisito automático solo está probado en Windows x64; configura ESTUDIO_BLENDER 4.5.16')
    root=Path(os.environ.get('ESTUDIO_RUNTIMES',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'as-video-studio/herramientas')))
    folder=root/'blender'/DISTRIBUCION['sha256'][:20]
    with lock_de(str(folder)):
        if folder.exists():exe=verificar_instalacion(folder)
        else:
            temporary=folder.parent/('preparando_'+uuid.uuid4().hex);temporary.mkdir(parents=True)
            archive=temporary/'distribucion.zip'
            source=os.environ.get('ESTUDIO_BLENDER_ARCHIVO')
            if source:
                shutil.copyfile(source,archive)
            else:
                avisar(None,'Descargando Blender '+VERSION+' oficial, únicamente en su runtime aislado')
                with urllib.request.urlopen(DISTRIBUCION['url'],timeout=60) as response,archive.open('wb') as dest:
                    total=0
                    while block:=response.read(1024*1024):
                        total+=len(block)
                        if total>600*1024*1024:raise ValueError('la distribución Blender excede el tamaño permitido')
                        dest.write(block);avisar(None,'Obteniendo Blender portable: '+str(total//1048576)+' MiB')
            if _sha(archive)!=DISTRIBUCION['sha256']:raise ValueError('la distribución Blender no coincide con su SHA256')
            with zipfile.ZipFile(archive) as z:
                infos=z.infolist()
                if len(infos)>30000 or sum(i.file_size for i in infos)>3*1024**3:raise ValueError('distribución Blender demasiado grande')
                for info in infos:
                    p=PurePosixPath(info.filename)
                    if p.is_absolute() or '..' in p.parts or '\\' in info.filename or ':' in info.filename or (info.external_attr>>16)&0o170000==0o120000:
                        raise ValueError('ruta no válida en la distribución Blender')
                z.extractall(temporary)
            # Inventario del ejecutable Y DLL/Python/licencias, no solo blender.exe.
            inventory={p.relative_to(temporary).as_posix():_sha(p) for p in temporary.rglob('*') if p.is_file() and p!=archive}
            escribir_json(str(temporary/'_estudio_runtime.json'),dict(distribucion=DISTRIBUCION,archivos=inventory))
            archive.unlink()  # copia temporal propia, verificada y ya extraída
            temporary.rename(folder);exe=verificar_instalacion(folder)
    return dict(ejecutable=str(exe.resolve()),version=VERSION,sha256_ejecutable=_sha(exe),origen='distribucion_sellada')
