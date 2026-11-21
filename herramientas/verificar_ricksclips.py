"""Pruebas GPU y muestras reales del paquete local, sin proveedores ni proyectos.
Ejecutar con --paquete <json> --salida <carpeta NUEVA>. Instala solo en esa carpeta.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nucleo.proyecto import escribir_json
from pasos import espacio_estilo,biblioteca_estilo,animacion_nativa


def verificar(destino):
    # Es una herramienta explícita, NO el proceso HTTP. Se importa únicamente el
    # paquete construido por esta sesión, después de instalar su entorno aislado.
    sys.path[:0]=[str(destino/'dependencias'),str(destino/'herramientas'),str(destino/'motores')]
    paquete=json.loads((destino/'paquete.json').read_text(encoding='utf8'))
    blender=None
    if paquete.get('blender'):
        from pasos import runtime_blender
        import blender_cliente_estudio as blender
        sys.modules['rc_blender_cliente']=blender
        blender.iniciar(destino,dict(salida=str(destino/'muestra/sonda'),ancho=320,alto=240,fps=1,
            blender={**paquete['blender'],**runtime_blender.resolver(paquete['blender'],lambda *a:None)}))
    import numpy as np
    from PIL import Image,ImageDraw
    from espacio3d import Renderer,Malla
    import escena
    r=Renderer(320,240)
    cam=dict(eye=(0,2,8),target=(0,1,0),apertura=0)
    def world():
        m=Malla();m.caja((0,-.2,0),(18,.4,18),'#E0B16C');m.caja((0,1,0),(2,2,2),'#2753A9')
        return m
    m=world();im=r.render(m,cam);im.save(destino/'muestra'/'profundidad_base.png')
    assert np.isfinite(r.last_depth).all() and (r.last_depth<.99).sum()>500,'z-buffer ausente'
    red=Image.new('RGBA',(60,120),(255,0,0,255))
    behind=r.render(m,cam,[(red,(0,0,-3),1.8)])
    front=r.render(m,cam,[(red,(0,0,3),1.8)])
    def rojos(im):
        a=np.array(im).astype(int);return int(((a[:,:,0]>a[:,:,1]*2)&(a[:,:,0]>a[:,:,2]*2)&(a[:,:,0]>120)).sum())
    assert rojos(front)>100 and rojos(behind)<rojos(front)*.1,'no hay oclusión de sprites'
    behind.save(destino/'muestra'/'oclusion_detras.png');front.save(destino/'muestra'/'oclusion_delante.png')
    noactor=r.render(m,cam)
    casting=r.render(m,cam,[(red,(-2,0,0),2.8)])
    # Sombra sobre suelo: excluye el sprite rojo y busca oscurecimiento exterior.
    a,b=np.array(noactor).astype(int),np.array(casting).astype(int)
    shadow=int(((a.mean(2)-b.mean(2)>12)&(b[:,:,0]<b[:,:,2]*1.6)).sum())
    assert shadow>30,'sprite no proyecta sombra detectable'
    casting.save(destino/'muestra'/'sombra_sprite.png')
    # Cámara más oblicua: un pequeño desplazamiento de un cubo sobre fondo
    # uniforme no garantiza >5 niveles de media RGB al cambiar la iluminación.
    # Se conserva el umbral y se comprueba además paralaje en profundidad.
    depth_original=r.last_depth.copy()
    cam2=dict(cam,eye=(5,3,6));moved=r.render(m,cam2)
    assert np.abs(np.array(moved).astype(int)-np.array(im).astype(int)).mean()>5,'cámara no modifica geometría'
    assert int((np.abs(r.last_depth-depth_original)>.001).sum())>200,'cámara sin paralaje de profundidad'
    moved.save(destino/'muestra'/'camara_movida.png')
    vol=r.render(m,cam,volumen=dict(t=2,cantidad=1,pos=(2,0,-1)))
    assert np.abs(np.array(vol).astype(int)-np.array(im).astype(int)).mean()>1,'volumen invisible'
    vol.save(destino/'muestra'/'volumen_prueba.png')
    # Determinismo: sin ruido temporal no sembrado ni imágenes externas.
    assert np.array_equal(np.array(r.render(m,cam)),np.array(noactor)),'render no determinista'
    # Normales hacia fuera de primitivas curvas, evita el fallo inicial de iluminación.
    sphere=Malla();sphere.esfera((0,0,0),1,'#FFFFFF')
    dots=[float(np.dot(v[:3],v[3:6])) for v in sphere.vertices if np.linalg.norm(v[3:6])>.5]
    assert min(dots)>.5,'normales esféricas invertidas'
    p=dict(ancho=360,alto=640,fps=12,duracion=3,parametros={})
    escena.preparar(p)
    names=['oeste','taberna','cocina','mar','canon','puente']
    sheet=Image.new('RGB',(360*6,640))
    for i,n in enumerate(names):
        p['parametros']=dict(escenario=n)
        frame=escena.pintar(p,2.7);frame.save(destino/'muestra'/(n+'.png'));sheet.paste(frame,(i*360,0))
    sheet.save(destino/'muestra'/'escenarios.png')
    # Cada acción debe cambiar la silueta del rig, no únicamente cámara/fondo.
    poses=Image.new('RGB',(400*4,560*3),'#423A4D')
    for row,action in enumerate(('caminar','sentarse','atrapar')):
        frames=[]
        for col,t in enumerate((0,.5,1.1,1.8)):
            frame=escena.sprite(t,dict(accion=action));poses.paste(frame,(col*400,row*560),frame)
            frames.append(np.array(frame))
        assert any(not np.array_equal(frames[0],f) for f in frames[1:]),'rig estático: '+action
    poses.save(destino/'muestra'/'articulacion.png')
    import realizacion
    trans=Image.new('RGB',(320*4,240*3))
    for row,kind in enumerate(('fundido','pupila','whip')):
        for col,u in enumerate((0,.3,.7,1)):
            frame=realizacion.transicion(im,moved,u,kind);trans.paste(frame,(col*320,row*240))
            if u==0:assert np.array_equal(np.array(frame),np.array(im))
            if u==1:assert np.array_equal(np.array(frame),np.array(moved))
    trans.save(destino/'muestra'/'transiciones.png')
    comparisons=Image.new('RGB',(360*4,640))
    for i,params in enumerate((dict(escenario='mar',decorado={'calma':0}),
            dict(escenario='mar',decorado={'calma':1}),
            dict(escenario='canon',decorado={'torcido':0}),dict(escenario='canon',decorado={'torcido':1}))):
        p['parametros']=params;comparisons.paste(escena.pintar(p,1.5),(i*360,0))
    comparisons.save(destino/'muestra'/'aceite_y_rieles.png')
    # Identidades independientes: cambiar una apariencia no contamina la siguiente.
    base=escena.sprite(1,{})
    escena.sprite(1,dict(apariencia=dict(pelo='largo',gafas=True,ropa='vestido',colores={'ropa':'#7755BA'})))
    assert np.array_equal(np.array(base),np.array(escena.sprite(1,{}))),'apariencias compartidas entre actores'
    result=dict(gpu=r.ctx.info['GL_RENDERER'],opengl=getattr(r.ctx,'version_code',None),oclusion=True,
        sombra_sprite_pixeles=shadow,profundidad=True,camara=True,volumen=True,determinismo=True,
        normales=True,acciones=['caminar','sentarse','atrapar'],transiciones=['fundido','pupila','whip'],
        escenarios=names,calidad_equivalente_verificada=False)
    result['fuentes_formato']='sha256-utf8-lf'
    result['fuentes']={p.relative_to(destino).as_posix():hashlib.sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        for base in ('motores','herramientas') for p in (destino/base).glob('*.py')}
    if paquete.get('blender'):
        result['backend']='blender'
        result['gpu']=blender._sesion.medidas[-1]['gpu']
        result['runtime']=blender._sesion.info
        result['fuentes']['ejecutor.py']=hashlib.sha256((destino/'ejecutor.py').read_text(encoding='utf8').encode('utf8')).hexdigest()
    escribir_json(str(destino/'muestra'/'pruebas_gpu.json'),result)
    if blender:blender.cerrar()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paquete',required=True,type=Path);parser.add_argument('--salida',required=True,type=Path)
    parser.add_argument('--sonda',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--runtimes',help=argparse.SUPPRESS)
    parser.add_argument('--blender',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.runtimes:os.environ['ESTUDIO_RUNTIMES']=args.runtimes
    if args.blender:os.environ['ESTUDIO_BLENDER']=args.blender
    if args.sonda:
        verificar(args.salida);return
    if args.salida.exists():raise ValueError('la salida debe ser nueva; no se sobreescriben pruebas')
    paquete=espacio_estilo.validar(json.loads(args.paquete.read_text(encoding='utf-8')),exigir_biblioteca=True)
    espacio_estilo.materializar(args.salida,paquete,[])
    last=['']
    def avisar(v,s):
        if last[0]!=s:print(s,flush=True);last[0]=s
    espacio_estilo.instalar(args.salida,avisar);espacio_estilo.fijar_requisitos(args.salida)
    muestra=dict(ancho=360,alto=640,fps=12,duracion=18,escena={},parametros=paquete['parametros'])
    files=espacio_estilo.renderizar(args.salida,muestra,args.salida/'muestra',avisar)
    movimiento=animacion_nativa.comprobar_movimiento(files['clip'],args.salida/'muestra',12)
    biblioteca_estilo.comprobar(args.salida,paquete['biblioteca'],avisar)
    # Transición real desde primerísimo plano 3D del rostro a un mar distinto.
    codigo='''import escena as motor
import realizacion
def preparar(pedido):motor.preparar(pedido)
def pintar(pedido,t):
    p=dict(pedido)
    p['parametros']=dict(escenario='oeste',actores=[dict(pos=[0,0,0],accion='quieto')],
        camara_claves=[dict(t=0,eye=[1,2.5,4],target=[0,1.9,0],fov=48),
             dict(t=1.6,eye=[.126,1.794,.24],target=[.126,1.794,0],fov=19)])
    a=motor.pintar(p,min(t,1.6))
    if t<=1.6:return a
    p['parametros']=dict(escenario='mar',actores=[])
    b=motor.pintar(p,t-1.6)
    return realizacion.transicion(a,b,min(1,(t-1.6)/.8),'pupila')
'''
    extra=dict(ancho=360,alto=640,fps=12,duracion=3,escena={},parametros={})
    espacio_estilo.renderizar(args.salida,extra,args.salida/'muestra'/'zoom_pupila',avisar,codigo_escena=codigo)
    efectos=dict(escenario='oeste',bala=True,aura=True,efectos=[
        dict(tipo='lineas_velocidad',t0=0,t1=1,x=.5,y=.45,n=20),
        dict(tipo='gotas_sudor',t0=0,t1=3,x=.4,y=.4),dict(tipo='chispas',t0=1,t1=2.2,x=.6,y=.5)],
        sfx=[dict(name='disparo',at=0,dur=.4),dict(name='whoosh',at=.5,dur=1)])
    espacio_estilo.renderizar(args.salida,dict(extra,parametros=efectos),args.salida/'muestra'/'efectos',avisar)
    # La sonda también se ejecuta fuera del coordinador; no importa el motor en
    # el intérprete que prepara/publica. El cliente se cierra con atexit si falla.
    orden=[sys.executable,'-B',str(Path(__file__).resolve()),'--paquete',str(args.paquete.resolve()),
        '--salida',str(args.salida.resolve()),'--sonda']
    if os.environ.get('ESTUDIO_RUNTIMES'):orden+=['--runtimes',os.environ['ESTUDIO_RUNTIMES']]
    if paquete.get('blender'):
        from pasos import runtime_blender
        runtime=runtime_blender.resolver(paquete['blender'],avisar)
        orden+=['--blender',runtime['ejecutable']]
    espacio_estilo.correr(orden,args.salida,avisar,'Comprobando GPU, alfa/Z y escenarios',segundos=1200)
    result=json.loads((args.salida/'muestra/pruebas_gpu.json').read_text(encoding='utf8'))
    escribir_json(str(args.salida/'muestra'/'verificacion.json'),dict(gpu=result,movimiento=movimiento))
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
