"""Sonda real local: 3D Blender + rig 2D, horizontal/vertical, rechazo de Pillow.

No consulta IA ni modifica escenas existentes. Usa un paquete ya instalado.
"""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

CODIGO='''from espacio3d import Malla, Renderer
from PIL import Image
import personaje_base as rig
R=None
def preparar(p):
    global R
    R=Renderer(p['ancho'],p['alto'])
def pintar(p,t):
    m=Malla()
    m.caja((0,-.15,0),(12,.3,12),'#A98765')
    m.caja((-2,1,-2),(.6,2,.6),'#8B658C')
    m.caja((2,1,-2),(.6,2,.6),'#8B658C')
    actor=Image.new('RGBA',(400,560))
    estado=rig.estado_base()
    estado.update(x=200,y=530,esc=1.2,sombra=0)
    estado.update(rig.saludar(t))
    rig.dibujar(actor,estado,dict(ancho=400,alto=560,t=t,duracion=p['duracion']))
    return R.render(m,dict(eye=(4,3,7),target=(0,1,0),fov=48,apertura=0),
        [(actor,(t*.3,0,0),2.5)])
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paquete',type=Path,required=True)
    parser.add_argument('--salida',type=Path,required=True)
    args=parser.parse_args()
    args.salida.mkdir(parents=True,exist_ok=False)
    for clave in ('ESTUDIO_SECRETOS','ESTUDIO_AJUSTES','ESTUDIO_ESTADISTICAS'):
        os.environ[clave]=str(args.salida/clave)
    from pasos import espacio_estilo
    from PIL import Image
    inventario=espacio_estilo.inventario(args.paquete)
    resultados={}
    for nombre,w,h in (('horizontal',320,180),('vertical',180,320)):
        contrato=dict(version=1,motor='blender',resolucion=[w,h])
        pedido=dict(ancho=w,alto=h,fps=2,duracion=1,parametros={},contrato_render=contrato)
        salida=args.salida/nombre
        archivos=espacio_estilo.renderizar(args.paquete,pedido,salida,lambda *a:None,codigo_escena=CODIGO)
        evidencia=json.loads((salida/'contrato_render.json').read_text(encoding='utf-8'))
        assert evidencia['fotogramas']==2 and len(evidencia['renders'])==2
        assert all(r['vertices']>0 and r['sprites']==1 for r in evidencia['renders'])
        with Image.open(archivos['poster']) as imagen:
            assert imagen.size==(w,h)
        resultados[nombre]=evidencia
    pillow="from PIL import Image\ndef pintar(p,t): return Image.new('RGB',(p['ancho'],p['alto']),'red')"
    bandas=CODIGO.replace('    return R.render(', '    imagen=R.render(')+'''
    salida=Image.new('RGB',(p['ancho'],p['alto']))
    salida.paste(imagen.resize((56,p['alto'])),((p['ancho']-56)//2,0))
    return salida
'''
    pedido=dict(ancho=320,alto=180,fps=2,duracion=1,parametros={},
        contrato_render=dict(version=1,motor='blender',resolucion=[320,180]))
    for nombre,codigo,error in (('pillow',pillow,'render Blender real por fotograma'),
            ('bandas',bandas,'bandas negras')):
        try:
            espacio_estilo.renderizar(args.paquete,pedido,args.salida/nombre,lambda *a:None,codigo_escena=codigo)
        except ValueError as exc:
            assert error in str(exc),str(exc)
        else:
            raise AssertionError('se aceptó '+nombre)
        assert not (args.salida/nombre/'contrato_render.json').exists()
        resultados[nombre]='rechazado correctamente'
    assert espacio_estilo.inventario(args.paquete)==inventario,'se modificó el paquete sellado'
    (args.salida/'resultado.json').write_text(json.dumps(resultados,indent=2),encoding='utf-8')
    print('OK: híbrido 3D/2D horizontal y vertical; Pillow y bandas rechazados; paquete intacto; sin IA.')


if __name__=='__main__':
    main()
