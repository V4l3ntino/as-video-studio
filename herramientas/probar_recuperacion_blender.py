"""Parar, timeout y error bpy reales sobre un candidato local, sin proveedores.

No usar un espacio publicado: la prueba conserva sus logs en trabajo/. Las salidas
son acumulativas y deben ser nuevas. No instala ni modifica dependencias globales.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import espacio_estilo as e

CUELGUE='''import time
from espacio3d import Malla,Renderer
def pintar(p,t):
    r=Renderer(p['ancho'],p['alto']);m=Malla()
    m.caja((0,0,0),(1,1,1),'#AA3322')
    im=r.render(m,dict(eye=(3,2,4),target=(0,0,0),fov=48))
    while True:time.sleep(1)
'''
ERROR_BPY='''from espacio3d import Malla,Renderer
def pintar(p,t):
    # El cliente acepta el pedido; el constraint dentro de bpy debe rechazarlo.
    return Renderer(p['ancho'],p['alto']).render(Malla(),
        dict(eye=(3,2,4),target=(0,0,0),fov=48),
        ambiente={'blender':{'cocina':True,'ollas':[{'piel':'#FFFFFF','mano':[0,.1,0]}]}})
'''


def terminado(pid):
    if os.name=='nt':
        import ctypes
        k=ctypes.windll.kernel32
        k.OpenProcess.restype=ctypes.c_void_p
        handle=k.OpenProcess(0x1000,False,pid)
        if not handle:return True
        try:
            code=ctypes.c_ulong()
            if not k.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)):raise OSError('GetExitCodeProcess')
            return code.value!=259
        finally:k.CloseHandle(ctypes.c_void_p(handle))
    try:os.kill(pid,0)
    except ProcessLookupError:return True
    return False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--espacio',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();a.salida.mkdir(parents=True,exist_ok=False)
    paquete=json.loads((a.espacio/'paquete.json').read_text(encoding='utf8'))
    assert paquete.get('blender'),'requiere candidato Blender'
    pedido=dict(ancho=192,alto=320,fps=1,duracion=1,parametros={})
    resultados={}
    class Parado(Exception):pass
    for nombre,codigo in [('parar',CUELGUE),('timeout',CUELGUE),('error_bpy',ERROR_BPY)]:
        salida=a.salida/nombre
        def avisar(v,m):
            if nombre=='parar' and (salida/'blender/intercambio/000000/frame.png').is_file():
                raise Parado('Parar solicitado tras render bpy real')
        correr=e.correr
        def corto(orden,carpeta,avisar,mensaje,segundos=600):
            return correr(orden,carpeta,avisar,mensaje,segundos=20 if nombre=='timeout' else segundos)
        try:
            with patch.object(e,'correr',side_effect=corto):
                e.renderizar(a.espacio,pedido,salida,avisar,codigo_escena=codigo)
        except (Parado,ValueError) as error:
            texto=str(error)
            esperado={'parar':'Parar solicitado','timeout':'tiempo de espera agotado','error_bpy':'sin penetrar la mesa'}[nombre]
            assert esperado in texto,texto
        else:raise AssertionError(nombre+' no falló')
        sesion=json.loads((salida/'blender/sesion.json').read_text(encoding='utf8'))
        assert terminado(sesion['pid']),sesion
        assert terminado(sesion['coordinador']),sesion
        assert (salida/'pedido.json').is_file() and (salida/'escena_nativa.py').is_file()
        assert (salida/'blender/blender.log').is_file()
        resultados[nombre]=dict(error=texto,sesion=sesion,sin_huerfanos=True,entradas_conservadas=True)
    # Después de los fallos el mismo paquete vuelve a renderizar sin reparación.
    codigo=CUELGUE.replace('    while True:time.sleep(1)','    return im')
    bien=e.renderizar(a.espacio,pedido,a.salida/'recuperado',lambda *a:None,codigo_escena=codigo)
    resultados['recuperado']=bien
    import hashlib
    resultados['fuentes']={p.relative_to(a.espacio).as_posix():hashlib.sha256(p.read_text(encoding='utf8').encode('utf8')).hexdigest()
        for carpeta in ('motores','herramientas') for p in (a.espacio/carpeta).glob('*.py')}
    resultados['fuentes']['ejecutor.py']=hashlib.sha256((a.espacio/'ejecutor.py').read_text(encoding='utf8').encode('utf8')).hexdigest()
    (a.salida/'recuperacion.json').write_text(json.dumps(resultados,indent=2),encoding='utf8')
    print(json.dumps(resultados,ensure_ascii=False))


if __name__=='__main__':main()
