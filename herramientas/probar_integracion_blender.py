"""Prueba local del puente nativo Blender; no publica ni consulta proveedores.

Reutiliza una copia de dependencias ya preparadas. Todas las salidas y fallos se
conservan en una carpeta nueva; no escribe en el estilo de origen.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from herramientas.preparar_ricksclips import construir,huellas_fuentes
from pasos import espacio_estilo

ESCENA='''from espacio3d import Malla, Renderer
from PIL import ImageDraw, Image
import numpy as np
R=None
def pintar(p,t):
    global R
    if R is None:R=Renderer(p['ancho'],p['alto'])
    m=Malla()
    m.caja((0,0,0),(2,.2,2),'#CCA060')
    m.caja((t,.7,0),(.6,1,.6),'#CC3322')
    cam=dict(eye=(3,2.5,4),target=(0,.5,0),fov=48,apertura=0)
    im=R.render(m,cam)
    z=R.last_depth.copy()
    assert np.isfinite(z).all() and z.min()<.999 and z.max()<=1
    # Segundo render y postproceso arbitrario sobre RGB verdadero.
    otro=R.render(m,cam)
    assert np.asarray(otro).std()>5
    im=Image.blend(im,otro,.5)
    ImageDraw.Draw(im).rectangle((4,4,20,20),fill='#12EF34')
    assert im.getpixel((8,8))==(18,239,52)
    return im
'''

PROFUNDIDAD='''from espacio3d import Malla, Renderer
import numpy as np
import json
from pathlib import Path
def pintar(p,t):
    r=Renderer(p['ancho'],p['alto']);m=Malla()
    m.caja((0,0,0),(20,20,.02),'#AAAAAA')
    im=r.render(m,dict(eye=(0,0,5),target=(0,0,0),fov=48,apertura=0))
    z=r.last_depth
    esperado=180/179.9-18/(179.9*4.99)
    error=float(np.max(np.abs(z-esperado)))
    (Path(p['salida'])/'calibracion.json').write_text(json.dumps(dict(error_maximo=error,z_esperado=esperado)))
    assert error<.00001, 'Z no coincide con el z-buffer axial histórico'
    return im
'''

FALLO='''import subprocess, sys
def pintar(p,t):
    try:subprocess.run([sys.executable,'-c','raise Exception("NO DEBE EJECUTARSE")'])
    except PermissionError:pass
    else:raise AssertionError('Se abrió la guarda de procesos')
    raise RuntimeError('FALLO_CONTROLADO_TRAS_GUARDA')
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--estilo',type=Path,required=True)
    p.add_argument('--blender',type=Path,help='ejecutable explícito; omitir para comprobar resolución automática')
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--solo-ruta-larga',action='store_true',help='sonda rápida de intercambio Windows de más de 300 caracteres')
    a=p.parse_args();a.salida.mkdir(parents=True,exist_ok=False)
    if a.blender:os.environ['ESTUDIO_BLENDER']=str(a.blender.resolve())
    else:os.environ.pop('ESTUDIO_BLENDER',None)
    paquete=construir(a.estilo,backend='blender')
    dest=a.salida/'paquete';espacio_estilo.materializar(dest,paquete,[])
    shutil.copytree(a.estilo/'versiones/v5/dependencias',dest/'dependencias',dirs_exist_ok=True)
    marca=espacio_estilo.huella(espacio_estilo.inventario(dest))
    ultimo=['']
    def avisar(v,m):
        if m!=ultimo[0]:print(m,flush=True);ultimo[0]=m
    pedido=dict(ancho=192,alto=320,fps=2,duracion=1,parametros={})
    if a.solo_ruta_larga:
        salida=dest/'trabajo'/('nativa_'+'a'*160)/'salida_dentro_del_proyecto'
        assert len(str(salida/'blender/intercambio/000000/escena.json'))>300
        archivos=espacio_estilo.renderizar(dest,pedido,salida,avisar,codigo_escena=ESCENA)
        espacio_estilo.verificar(dest,marca)
        print(json.dumps(dict(ruta_larga=True,archivos=archivos,fuentes=huellas_fuentes(paquete))))
        return
    resultado=espacio_estilo.renderizar(dest,pedido,a.salida/'render',avisar,codigo_escena=ESCENA)
    espacio_estilo.verificar(dest,marca)
    congelado=a.salida/'congelado'
    espacio_estilo.copiar(dest,congelado,marca)
    espacio_estilo.verificar(congelado,marca)
    shutil.copytree(dest/'dependencias',congelado/'dependencias')
    repetido=espacio_estilo.renderizar(congelado,pedido,a.salida/'repetido',avisar,codigo_escena=ESCENA)
    from PIL import Image
    import numpy as np
    with Image.open(resultado['poster']) as im,Image.open(repetido['poster']) as other:
        assert np.array_equal(np.asarray(im),np.asarray(other))
    # El mismo puente ejecuta la escena RicksClips libre y su rig, no solo cubos.
    cocina=espacio_estilo.renderizar(congelado,dict(pedido,duracion=2.2,fps=5,parametros={'escenario':'cocina'}),
        a.salida/'cocina',avisar)
    medidas=json.loads((a.salida/'cocina/blender/ejecucion.json').read_text(encoding='utf8'))
    contactos=[c for r in medidas['renders'] for c in r['contacto']]
    assert len(contactos)==11 and any(c['chorro'] for c in contactos)
    assert all(c['error_agarre_m']<1e-6 and c['cota_minima_constraint']>=1.45999 for c in contactos)
    escenarios={}
    for tipo in ('oeste','taberna','mar','canon','puente'):
        archivos=espacio_estilo.renderizar(congelado,dict(pedido,duracion=.5,parametros={'escenario':tipo}),
            a.salida/tipo,avisar)
        with Image.open(archivos['poster']) as im:
            pixels=np.asarray(im.convert('RGB'))
            assert float(pixels.mean())>15,'escenario indebidamente negro: '+tipo
        escenarios[tipo]=archivos
    profundidad=espacio_estilo.renderizar(congelado,dict(pedido,duracion=.5),
        a.salida/'profundidad',avisar,codigo_escena=PROFUNDIDAD)
    try:
        espacio_estilo.renderizar(congelado,dict(pedido,duracion=.5),a.salida/'fallo',avisar,codigo_escena=FALLO)
    except ValueError as error:
        assert 'FALLO_CONTROLADO_TRAS_GUARDA' in str(error),error
    else:raise AssertionError('La escena de fallo no debe completar')
    for nombre in ('render','repetido','cocina','profundidad','fallo'):
        cierre=json.loads((a.salida/nombre/'blender/cierre.json').read_text(encoding='utf8'))
        assert cierre['proceso_terminado'] and cierre['retorno']==0,cierre
    recibo=dict(huella=marca,render=resultado,repetido=repetido,copia_sellada=True,
        pixeles_identicos=True,cocina=cocina,profundidad=profundidad,guarda_procesos=True,
        cierre_en_error=True,proveedores=0,
        fuentes=huellas_fuentes(paquete),contactos_olla=contactos,
        escenarios=escenarios,
        limite='Prueba técnica pequeña, no certificación artística ni publicación')
    (a.salida/'integracion.json').write_text(json.dumps(recibo,indent=2),encoding='utf8')
    print(json.dumps(recibo,indent=2))


if __name__=='__main__':main()
