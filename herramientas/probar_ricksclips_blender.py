"""Piloto Blender aislado: exporta geometría/rig reales, sin publicar ni proveedores.

El programa de escena sigue siendo Python libre; el intercambio no es un catálogo
de acciones. No escribe en el paquete sellado. Requiere sus dependencias locales.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import hashlib
import shutil
import os
import copy

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--espacio',required=True,type=Path)
    p.add_argument('--blender',required=True,type=Path)
    p.add_argument('--salida',required=True,type=Path)
    p.add_argument('--plano',choices=['cocina','canon','tren_frente','tren_lateral','tren_atras'],required=True)
    p.add_argument('--frames',type=int,default=55)
    p.add_argument('--inicio',type=float,default=0)
    p.add_argument('--samples',type=int,default=32)
    p.add_argument('--acabado',choices=['transferencia','dirigido'],default='transferencia')
    p.add_argument('--programa-bpy',type=Path,help='Python libre con preparar(contexto) y actualizar(contexto,t); solo se importa en Blender')
    p.add_argument('--apariencia',type=Path,help='JSON apariencia/1 para el actor de diagnóstico, sin modificar el rig')
    p.add_argument('--solo-exportar',action='store_true',help='conserva intercambio y fuentes sin lanzar Blender')
    p.add_argument('--encuadre-mejorado',action='store_true',help='prueba separada de composición de cocina; ya no es la cámara v5')
    a=p.parse_args()
    if not 1<=a.frames<=250: p.error('--frames debe estar entre 1 y 250')
    a.salida.mkdir(parents=True,exist_ok=False)
    fuentes={}
    for source in [Path(__file__),*sorted((ROOT/'motores/ricksclips/blender').glob('*.py'))]:
        target=a.salida/'fuentes'/source.name;target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source,target);fuentes[source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    (a.salida/'fuentes.json').write_text(json.dumps(fuentes,indent=2),encoding='utf8')
    if a.programa_bpy:
        codigo=a.programa_bpy.read_text(encoding='utf8');compile(codigo,str(a.programa_bpy),'exec')
        target=a.salida/'fuentes/programa_bpy.py';target.write_text(codigo,encoding='utf8')
        fuentes['programa_bpy.py']=hashlib.sha256(target.read_bytes()).hexdigest()
        (a.salida/'fuentes.json').write_text(json.dumps(fuentes,indent=2),encoding='utf8')
    sys.path[:0]=[str(a.espacio/'dependencias'),str(a.espacio/'herramientas'),str(a.espacio/'motores')]
    import numpy as np
    from PIL import Image
    import escena
    import decorados3d
    import artesania3d
    from planos_revision import plano
    from espacio3d import normal
    captura_anclas={};conteo=[None];ultimo_dibujo={};ampliaciones={}
    original_dibujar=escena.rig.dibujar
    def dibujar_con_anclas(im,estado,contexto):
        result=original_dibujar(im,estado,contexto)
        captura_anclas.clear();captura_anclas.update(result)
        ultimo_dibujo.update(estado=copy.deepcopy(estado),contexto=copy.deepcopy(contexto))
        return result
    escena.rig.dibujar=dibujar_con_anclas
    if a.acabado=='dirigido':
        if a.encuadre_mejorado and a.plano=='cocina':
            decorados3d.cuenco=lambda *args,**kwargs:None
            artesania3d.cuenco=lambda *args,**kwargs:None
        if a.plano!='cocina':
            decorados3d.tren=lambda *args,**kwargs:None
            decorados3d.pared_canon=lambda *args,**kwargs:None
        original_escena=escena.escena
        def decorado_sin_olla(*args,**kwargs):
            m,cam,amb=original_escena(*args,**kwargs);conteo[0]=len(m.vertices)
            return m,cam,amb
        escena.escena=decorado_sin_olla
        original_sprite=escena.sprite
        def sprite_contacto(t,actor,detalle=1):
            if actor.get('accion')=='verter':
                u=max(0,min(1,t/.65));u=u*u*(3-2*u)
                v=max(0,min(1,(t-1.6)/.55));v=v*v*(3-2*v)
                actor=dict(actor,pose=dict(ik={'mano_d':((270+12*u)*detalle,(185-75*u+75*v)*detalle,1)},
                    cabeza_inc=3,mirada=[.6,.25]))
            im=original_sprite(t,actor,detalle)
            box=im.getbbox()
            if actor.get('accion')=='verter' and box and (box[1]<=1 or box[0]<=1 or box[2]>=im.width-1):
                # Las proporciones grandes podían cortar el gorro en el lienzo
                # fijo heredado. Añadir espacio, no encoger la identidad.
                dx=round(im.width*.2);dy=round(im.height*.25)
                expanded=Image.new('RGBA',(im.width+dx*2,im.height+dy))
                state=copy.deepcopy(ultimo_dibujo['estado']);ctx=dict(ultimo_dibujo['contexto'])
                state['x']+=dx;state['y']+=dy
                for key,value in state.get('ik',{}).items():
                    state['ik'][key]=(value[0]+dx,value[1]+dy,*value[2:])
                ctx.update(ancho=expanded.width,alto=expanded.height)
                anchors=original_dibujar(expanded,state,ctx)
                captura_anclas.clear();captura_anclas.update(anchors)
                ampliaciones[id(expanded)]=im.size
                return expanded
            return im
        escena.sprite=sprite_contacto
    class Captura:
        def __init__(self,w,h): self.w,self.h=w,h;self.frame=0
        def render(self,m,cam,sprites,amb,volume):
            folder=a.salida/'intercambio'/f'{self.frame:04}'
            folder.mkdir(parents=True,exist_ok=False)
            verts=m.vertices[:conteo[0]] if a.acabado=='dirigido' and a.plano=='cocina' else m.vertices
            np.save(folder/'malla.npy',np.asarray(verts,dtype='f4'),allow_pickle=False)
            items=[]
            right=normal(np.cross(normal(np.subtract(cam['target'],cam['eye'])),(0,1,0)))
            for i,(im,pos,height) in enumerate(sprites):
                original=ampliaciones.pop(id(im),None)
                if original:height*=im.height/original[1]
                im.save(folder/f'actor_{i}.png')
                width=height*im.width/im.height
                bl=np.array(pos)-right*width/2;br=np.array(pos)+right*width/2
                corners=[bl,br,br+(0,height,0),bl+(0,height,0)]
                items.append(dict(imagen=f'actor_{i}.png',vertices=np.asarray(corners).tolist()))
                items[-1]['piel']=escena.rig.COLORES['piel']
                if 'mano_d' in captura_anclas:
                    ax,ay=captura_anclas['mano_d'][:2]
                    hand=bl+right*(ax/im.width*width)+np.array((0,(1-ay/im.height)*height,0))
                    items[-1]['mano_d']=hand.tolist()
            (folder/'escena.json').write_text(json.dumps(dict(camara=cam,ambiente=amb,sprites=items,
                volumen=volume,t=a.inicio+self.frame/25,plano=a.plano,
                composicion='cocina_reencuadrada' if a.encuadre_mejorado else 'v5')),encoding='utf8')
            self.frame+=1
            return Image.new('RGB',(self.w,self.h))
    # Solo intercepta esta copia del motor dentro del proceso piloto.
    escena.Renderer=Captura
    pedido=dict(ancho=1080,alto=1920,fps=25,duracion=a.frames/25,parametros={})
    escena.preparar(pedido)
    for frame in range(a.frames):
        t=a.inicio+frame/25
        if a.plano.startswith('tren_'):
            views={'tren_frente':((5.8,3.2,-22),(0,1.3,-14)),
                'tren_lateral':((9.5,3,-13),(0,1.25,-14)),
                'tren_atras':((5,3,-5.5),(0,1.3,-13.5))}
            eye,target=views[a.plano]
            pedido['parametros']=dict(escenario='canon',actores=[],demostracion=False,
                camara=dict(eye=(eye[0],eye[1],eye[2]+t*1.7),
                target=(target[0],target[1],target[2]+t*1.7),fov=52,apertura=.1))
        else: pedido['parametros']=plano(a.plano)
        if a.encuadre_mejorado and a.plano=='cocina':
            pedido['parametros']['camara']=dict(eye=(.75,2.45,-.2-t*.035),target=(.75,1.65,-5.6),fov=54,apertura=0)
            for actor in pedido['parametros']['actores']:actor.update(alto=3.25,pos=(.15,0,-5.8))
        if a.apariencia:
            apariencia=json.loads(a.apariencia.read_text(encoding='utf8'))
            for actor in pedido['parametros'].get('actores',[]):actor['apariencia']=apariencia
        escena.pintar(pedido,t)
    inventory={str(file.relative_to(a.salida)).replace('\\','/'):hashlib.sha256(file.read_bytes()).hexdigest()
        for folder in ('intercambio','fuentes') for file in sorted((a.salida/folder).rglob('*')) if file.is_file()}
    (a.salida/'inventario_entrada.json').write_text(json.dumps(inventory,indent=2),encoding='utf8')
    if a.solo_exportar:
        print('Intercambio exportado sin render: '+str(a.salida),flush=True);return
    script=a.salida.resolve()/'fuentes/renderizar.py'
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in
        ('TOKEN','API_KEY','SECRET','ANTHROPIC','OPENAI','CARTESIA','ELEVENLABS'))}
    runtime=a.salida.resolve()/'runtime';runtime.mkdir()
    for key,name in [('BLENDER_USER_CONFIG','config'),('BLENDER_USER_SCRIPTS','scripts'),
            ('BLENDER_USER_DATAFILES','data'),('TEMP','temp'),('TMP','temp')]:
        local=runtime/name;local.mkdir(exist_ok=True);env[key]=str(local)
    start=time.perf_counter()
    with (a.salida/'blender.log').open('w',encoding='utf8') as log:
        result=subprocess.run([str(a.blender),'--background','--factory-startup','--python-exit-code','1',
            '--python',str(script),'--',str(a.salida.resolve()),str(a.samples),a.acabado],
            stdout=log,stderr=subprocess.STDOUT,env=env,cwd=str(a.salida.resolve()))
    (a.salida/'proceso.json').write_text(json.dumps(dict(retorno=result.returncode,
        segundos_proceso=time.perf_counter()-start,plano=a.plano,frames=a.frames,
        acabado=a.acabado,espacio_solo_lectura=str(a.espacio)),indent=2),encoding='utf8')
    if result.returncode: raise RuntimeError('Blender falló; consultar '+str(a.salida/'blender.log'))
    sys.path.insert(0,str(ROOT))
    from pasos import medios
    subprocess.run([medios.ffmpeg(),'-v','error','-framerate','25','-i',str(a.salida/'frames/%04d.png'),
        '-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(a.salida/'clip.mp4')],check=True)
    subprocess.run([medios.ffmpeg(),'-v','error','-i',str(a.salida/'clip.mp4'),'-vf',
        'fps=3,scale=270:480,tile=7x1','-frames:v','1',str(a.salida/'tiempo.png')],check=True)
    print(a.salida,flush=True)


if __name__=='__main__': main()
