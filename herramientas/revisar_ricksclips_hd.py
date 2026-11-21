"""Renderiza planos 1080x1920/25fps y hojas temporales sin proveedores.

Usa un espacio previamente materializado e instalado por verificar_ricksclips.
Salidas siempre nuevas. Referencias: solo se leen para láminas comparativas,
nunca entran al proceso que dibuja el motor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import espacio_estilo,medios,animacion_nativa


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--espacio',type=Path,required=True)
    p.add_argument('--paquete',type=Path,help='materializa e instala un espacio NUEVO antes del render HD')
    p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--referencias',type=Path,required=True)
    p.add_argument('--planos',nargs='+',default=['general','medio','rostro','movil','cocina','cuenco','tormenta','calma','canon','torcida','puente','explosion','pupila','expresiones'])
    a=p.parse_args()
    if not a.referencias.is_dir():raise ValueError('la carpeta de referencias para comparar no existe')
    a.salida.mkdir(parents=True,exist_ok=False)
    if a.paquete:
        if a.espacio.exists():raise ValueError('el espacio para --paquete debe ser nuevo')
        paquete=espacio_estilo.validar(json.loads(a.paquete.read_text(encoding='utf8')),exigir_biblioteca=True)
        espacio_estilo.materializar(a.espacio,paquete,[])
        espacio_estilo.instalar(a.espacio,lambda v,msg:print(msg,flush=True))
    sys.path[:0]=[str(a.espacio/'dependencias'),str(a.espacio/'herramientas')]
    backend='blender' if json.loads((a.espacio/'paquete.json').read_text(encoding='utf8')).get('blender') else None
    from planos_revision import plano
    from PIL import Image,ImageDraw
    resultados=[]
    fuentes={p.relative_to(a.espacio).as_posix():hashlib.sha256(p.read_text(encoding='utf8').encode('utf8')).hexdigest()
        for base in ('motores','herramientas') for p in (a.espacio/base).glob('*.py')}
    if backend:fuentes['ejecutor.py']=hashlib.sha256((a.espacio/'ejecutor.py').read_text(encoding='utf8').encode('utf8')).hexdigest()
    (a.salida/'fuentes.json').write_text(json.dumps(fuentes,indent=2),encoding='utf8')
    for name in a.planos:
        inicio=time.monotonic()
        tren=name in ('tren_frente','tren_lateral','tren_atras')
        parametros=plano(name,backend=backend) if name not in ('pupila','expresiones','whip_mirilla','efectos','proa','caminar') and not tren else {}
        codigo=None
        if name=='efectos':
            parametros=dict(escenario='oeste',bala=True,aura=True,efectos=[
                dict(tipo='lineas_velocidad',t0=0,t1=1,x=.5,y=.45,n=20),
                dict(tipo='gotas_sudor',t0=0,t1=2.2,x=.4,y=.4),
                dict(tipo='chispas',t0=1,t1=2.2,x=.6,y=.5)],
                sfx=[dict(name='disparo',at=0,dur=.4),dict(name='whoosh',at=.5,dur=1)])
        elif name=='proa':
            parametros=plano('tormenta',backend=backend)
            # Detalle del casco sobre mar local tranquilo; la tormenta completa
            # se comprueba aparte. La primera cámara quedaba dentro de la ola.
            parametros['decorado']=dict(ola=0,calma=1)
            parametros['camara']=dict(eye=(2,3.2,-13),target=(-1,1.3,-8.5),fov=50,apertura=0)
        elif name=='caminar':
            parametros=plano('general',backend=backend)
            parametros['actores'][0]['accion']='caminar'
        elif tren:
            # Lienzo vertical: distancia suficiente para ver toda la locomotora,
            # no cortar morro/ruedas y aparentar detalle con un recorte involuntario.
            vistas={'tren_frente':((5.8,3.2,-22),(0,1.3,-14)),
                'tren_lateral':((9.5,3,-13),(0,1.25,-14)),
                'tren_atras':((5,3,-5.5),(0,1.3,-13.5))}
            eye,target=vistas[name]
            parametros=dict(escenario='canon',actores=[],demostracion=False,
                camara_claves=[dict(t=t,eye=[eye[0],eye[1],eye[2]+t*1.7],
                    target=[target[0],target[1],target[2]+t*1.7],fov=52,apertura=.1) for t in (0,2.2)])
        elif name=='whip_mirilla':
            codigo='''import escena as motor
import realizacion
from planos_revision import plano
def preparar(p):motor.preparar(p)
def pintar(p,t):
    q=dict(p)
    if t<.7:
        q['parametros']=plano('medio')
        a=motor.pintar(q,t)
        q['parametros']=plano('canon')
        b=motor.pintar(q,t)
        return realizacion.transicion(a,b,t/.7,'whip')
    q['parametros']=plano('tormenta')
    b=motor.pintar(q,t)
    if t>=1.5:return b
    q['parametros']=plano('canon')
    a=motor.pintar(q,t)
    return realizacion.transicion(a,b,(t-.7)/.8,'mirilla')
'''
        elif name=='pupila':
            codigo='''import escena as motor
import realizacion
from planos_revision import plano
def preparar(p):motor.preparar(p)
def pintar(p,t):
    q=dict(p);q['parametros']=plano('rostro')
    q['parametros']['camara_claves']=[dict(t=0,eye=[.1,2.05,.3],target=[0,1.72,-1.2],fov=42,apertura=0),dict(t=1.25,eye=[.135,1.932,-.96],target=[.135,1.932,-1.2],fov=22,apertura=0)]
    q['parametros'].pop('camara',None)
    front=motor.pintar(q,min(t,1.25))
    if t<1.25:return front
    q['parametros']=plano('tormenta')
    back=motor.pintar(q,t-1.25)
    return realizacion.transicion(front,back,min(1,(t-1.25)/.75),'pupila')
'''
        elif name=='expresiones':
            codigo='''import escena as motor
from planos_revision import plano
def preparar(p):motor.preparar(p)
def pintar(p,t):
    q=dict(p);q['parametros']=plano('medio')
    a=q['parametros']['actores'][0]
    a['pose']=dict(mirada=[-.8 if t<1 else .8,.2],cabeza_inc=5)
    a['expresion']=dict(enfado=-.7 if t<1 else .8,boca=-.3,abierta=.4 if t<1 else 0,ojos=.08 if .8<t<.96 else 1)
    return motor.pintar(q,t)
'''
        pedido=dict(ancho=1080,alto=1920,fps=25,duracion=2.2,escena={},parametros=parametros)
        def avisar(v,msg):
            if isinstance(v,(int,float)) and v>=1:print(name,msg,flush=True)
        files=espacio_estilo.renderizar(a.espacio,pedido,a.salida/name,avisar,codigo_escena=codigo)
        control=animacion_nativa.comprobar_movimiento(files['clip'],a.salida/name,25) if tren or name in ('movil','cocina','tormenta','calma','torcida','explosion','pupila','expresiones','whip_mirilla','efectos','proa','caminar') else {'nota':'Plano estático deliberado; no se presenta como animación.'}
        video=Path(files['clip'])
        subprocess.run([medios.ffmpeg(),'-v','error','-i',str(video),'-vf','fps=3,scale=270:480,tile=7x1',
            '-frames:v','1',str(a.salida/(name+'_tiempo.jpg'))],check=True)
        subprocess.run([medios.ffmpeg(),'-v','error','-ss','1.3','-i',str(video),'-frames:v','1',str(a.salida/(name+'.png'))],check=True)
        resultados.append(dict(plano=name,clip=str(video),ancho=1080,alto=1920,fps=25,duracion=2.2,
            segundos_render=round(time.monotonic()-inicio,2),movimiento=control))
        (a.salida/'renders.json').write_text(json.dumps(resultados,indent=2),encoding='utf8')
        print('TERMINADO',name,flush=True)
    # Misma altura y aspecto, sin ampliar la referencia por encima de su original.
    comparaciones=[('general','ref_01_5.png'),('medio','ref_04_33.png'),('movil','ref_05_42.png'),
        ('cocina','ref_09_99.64.png'),('cuenco','ref_11_108.png'),('tormenta','ref_12_117.5.png'),
        ('canon','ref_13_123.png'),('torcida','ref_16_177.4.png'),('explosion','ref_17_185.png')]
    for name,ref in comparaciones:
        if not (a.salida/(name+'.png')).is_file():continue
        sheet=Image.new('RGB',(720,660),'#20202A');d=ImageDraw.Draw(sheet)
        for i,path in enumerate((a.referencias/ref,a.salida/(name+'.png'))):
            im=Image.open(path);im.thumbnail((360,640));sheet.paste(im,(i*360,20))
        d.text((10,2),'REFERENCIA',fill='white');d.text((370,2),'MOTOR LOCAL',fill='white')
        sheet.save(a.salida/('comparacion_'+name+'.jpg'))


if __name__=='__main__':main()
