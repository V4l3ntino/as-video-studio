"""Motor híbrido RicksClips: escena OpenGL real con el rig 2D del paquete v1.

La escena nativa puede importar decorados3d/espacio3d y construir cualquier malla;
estos parámetros son una interfaz de muestra, no un catálogo cerrado de actuación.
"""
import math
import copy
import random
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import personaje_base as rig
import auxiliar as fx
import movil
import realizacion
from contactos import centro_por_agarre
from espacio3d import Renderer,Malla
from decorados3d import escena, mesa

_render=None
_aspecto={k:copy.deepcopy(getattr(rig,k)) for k in
    ('PELO','ROPA','BARBA','GAFAS','PECAS','MOVIL','ALTURA','CUERPO','CABEZA','EDAD','COLORES')}


def preparar(pedido):
    global _render
    _render=Renderer(pedido['ancho'],pedido['alto'])


def sprite(t,actor,detalle=1,con_anclas=False):
    detalle=max(1,min(4,detalle))
    im=Image.new('RGBA',(round(400*detalle),round(560*detalle)))
    for k,v in _aspecto.items():setattr(rig,k,copy.deepcopy(v))
    rig.aplicar_apariencia(actor.get('apariencia',{}))
    e=rig.estado_base();e.update(x=200*detalle,y=530*detalle,esc=1.45*detalle,sombra=0,dir=actor.get('dir',1))
    accion=actor.get('accion','saludar')
    if accion=='caminar':e.update(rig.caminar(t))
    elif accion=='sentarse':e.update(rig.sentarse(min(1,t)))
    elif accion=='saludar':e.update(rig.saludar(t))
    elif accion=='atrapar':
        u=max(0,min(1,(t-.3)/.65));e.update(hombro_d=30+u*65,codo_d=40*u,cabeza_inc=-u*9,mirada=[.7,-.4+.8*u])
        if t>.3:
            catch_y=220+145*min(1,max(0,(t-.4)/.55))**2
            # Objetivo de muñeca en el borde, no en el centro de la pantalla.
            e['ik']={'mano_d':(266*detalle,(catch_y+8)*detalle,min(1,u*2))}
    elif accion=='verter':
        e.update(cabeza_inc=3,mirada=[.65,.4],ik={'mano_d':(275*detalle,123*detalle,1)})
        if actor.get('contacto_blender'):
            u=max(0,min(1,t/.65));u=u*u*(3-2*u)
            v=max(0,min(1,(t-1.6)/.55));v=v*v*(3-2*v)
            e.update(ik={'mano_d':((270+12*u)*detalle,(185-75*u+75*v)*detalle,1)})
    e.update(actor.get('pose',{}))
    for key in ('sombrero','bigote','cinturon'):
        if key in actor:e[key]=actor[key]
    # Expresiones/parpadeo se mantienen separados de la locomoción.
    blink=max(0,1-abs((t%3.7)-3.52)/.10)
    e['expresion']={**e.get('expresion',{}),'ojos':1-blink*.95,
                       'sorpresa':actor.get('sorpresa',0),**actor.get('expresion',{})}
    anclas=rig.dibujar(im,e,dict(t=t,ancho=im.width,alto=im.height,duracion=10))
    original_size=im.size
    if con_anclas:
        box=im.getbbox()
        if box and (box[1]<=1 or box[0]<=1 or box[2]>=im.width-1):
            dx=round(im.width*.2);dy=round(im.height*.25)
            im=Image.new('RGBA',(im.width+dx*2,im.height+dy))
            e=copy.deepcopy(e);e['x']+=dx;e['y']+=dy
            for key,value in e.get('ik',{}).items():
                e['ik'][key]=(value[0]+dx,value[1]+dy,*value[2:])
            anclas=rig.dibujar(im,e,dict(t=t,ancho=im.width,alto=im.height,duracion=10))
    if accion=='atrapar':
        yy=220+145*min(1,max(0,(t-.4)/.55))**2
        ang=-20+20*min(1,t/.95)
        center=(280*detalle,yy*detalle)
        if t>=.95:
            # El contacto usa la mano REAL después del IK y de la apariencia.
            ang=4*math.exp(-(t-.95)*6)*math.sin((t-.95)*18)
            center=centro_por_agarre(anclas['mano_d'],(-14,8),ang,detalle)
        movil.dibujar(im,dict(x=center[0],y=center[1],alto=57*detalle,ang=ang),dict(t=t))
        if t>=.95:
            # Dedos delante del borde del móvil; deja de atravesar la palma.
            d=ImageDraw.Draw(im);x,y=anclas['mano_d']
            d.ellipse((x-4*detalle,y-3*detalle,x+6*detalle,y+3*detalle),fill=rig.COLORES['piel'],outline='#211B28',width=max(1,round(detalle)))
    # El rig v4 incluye vestuario. Compatibilidad de la herramienta de estudio
    # cuando usa aún el rig v3, sin modificar ese paquete publicado.
    hat=actor.get('sombrero') if not hasattr(rig,'VESTUARIO_VERSION') else None
    if hat:
        # Accesorios ligados a la geometría del rig, no otra figura humana.
        head=anclas.get('cabeza',(200*detalle,150*detalle));x,y=head[:2]
        d=ImageDraw.Draw(im);color='#282534' if hat!='chef' else '#F5F0DB'
        hh=(75 if hat in ('chef','chistera') else 35)*detalle
        d.rounded_rectangle((x-46*detalle,y-72*detalle-hh,x+46*detalle,y-72*detalle),radius=12*detalle,fill=color,outline='#15121C',width=round(5*detalle))
        d.ellipse((x-70*detalle,y-85*detalle,x+70*detalle,y-63*detalle),fill=color,outline='#15121C',width=round(4*detalle))
    if actor.get('aura'):
        mask=im.getchannel('A');expanded=mask.filter(ImageFilter.MaxFilter(2*round(6*detalle)+1))
        border=ImageChops.subtract(expanded,mask)
        flame=Image.new('RGBA',im.size,(255,177,20,0));flame.putalpha(border)
        d=ImageDraw.Draw(flame)
        for i in range(13):
            x=(140+120*(i%2)+12*math.sin(i*4))*detalle
            y=(160+i*23)*detalle
            height=(18+14*math.sin(t*12+i))*detalle
            d.polygon(((x-7*detalle,y),(x+5*detalle,y),(x+3*detalle,y-height)),fill=(255,196,37,180))
        glow=flame.filter(ImageFilter.GaussianBlur(3*detalle))
        im=Image.alpha_composite(Image.alpha_composite(glow,flame),im)
    if con_anclas:return im,anclas,original_size,rig.COLORES['piel']
    return im


def pintar(pedido,t):
    global _render
    if _render is None:preparar(pedido)
    nativo=getattr(_render,'backend',None)=='blender'
    p=pedido.get('parametros') or {};tipo=p.get('escenario','oeste')
    if tipo=='galeria':
        tipos=['oeste','taberna','cocina','mar','canon','puente']
        tipo=tipos[min(5,int(t/3))];local=t%3
    else:local=t
    if p.get('escenario')=='galeria':
        from planos_revision import plano
        names=['general' if local<1 else ('medio' if local<2 else 'rostro'),
            'movil','cocina' if local<2 else 'cuenco','tormenta','canon' if local<1.5 else 'torcida','explosion']
        p={**p,**plano(names[min(5,int(t/3))],backend='blender' if nativo else None)}
    decorado=dict(p.get('decorado') or {})
    if nativo:decorado['blender']=True
    m,cam,amb=escena(tipo,local,decorado)
    opciones=dict(t=local)
    if nativo:
        if tipo in ('canon','puente'):
            opciones.update(paredes=dict(distancia=8.4 if tipo=='canon' else 30,
                altura=25 if tipo=='canon' else 18),tren=decorado.get('tren',True))
        if tipo=='cocina':opciones.update(cocina=True,ollas=[])
        amb['blender']=opciones
    cam.update(p.get('camara',{}))
    cam.update(realizacion.camara(p.get('camara_claves',[]),local))
    # Dolly lateral y empuje con paralaje real, no transformación de una imagen.
    if not p.get('camara_claves') and not p.get('camara'):
        eye=list(cam['eye']);eye[0]+=math.sin(local*.6)*.5;eye[2]-=local*.22;cam['eye']=eye
    actores=p.get('actores')
    if actores is None:
        actores=[] if tipo=='mar' else [dict(pos=(1.3,0,1.3) if tipo in ('canon','puente') else ((.1,0,-5.8) if tipo=='cocina' else (0,0,-1.2)),alto=2.8,accion='caminar' if tipo=='oeste' else ('atrapar' if tipo=='taberna' else ('verter' if tipo=='cocina' else 'quieto')),
            apariencia=dict(ropa='camisa' if tipo=='cocina' else 'chaqueta',
                 pelo='calvo',colores=dict(ropa='#F2EADC' if tipo=='cocina' else '#2E998A',piel='#FFF0DB',pelo='#3B2926')),
             sombrero='chef' if tipo=='cocina' else ('gorra' if tipo in ('canon','puente') else 'oeste'))]
    if nativo and tipo=='cocina' and not p.get('camara') and not p.get('camara_claves'):
        cam.update(eye=(.75,2.45,-.2-local*.035),target=(.75,1.65,-5.6),fov=54,apertura=0)
    sprites=[]
    for actor in actores:
        pos=list(actor.get('pos',(0,0,0)))
        if actor.get('accion')=='caminar':pos[0]+=local*.35
        # Re-rasterizar el rig a densidad del plano corto evita ampliar una
        # textura diminuta al hacer el zoom a la pupila. No se usa una foto.
        dist=max(.2,math.dist(cam['eye'],(pos[0],pos[1]+2,pos[2])))
        detalle=min(4,max(1,pedido['alto']*actor.get('alto',2.6)/(dist*math.tan(math.radians(cam['fov']/2))*1120)))
        alto=actor.get('alto',2.6)
        # La imagen tiene 30 px transparentes BAJO el suelo (y=530 de 560).
        # Descontarlos sitúa los pies en su ancla, no flotando a 0.15 m.
        pos[1]-=alto*30/530
        actor=dict(actor,aura=actor.get('aura',p.get('aura',False)),contacto_blender=nativo)
        if nativo:
            imagen,anclas,tamano,piel=sprite(local,actor,detalle,con_anclas=True)
            altura=alto*560/530*imagen.height/tamano[1]
            # El lienzo ampliado mantiene centro horizontal y pie de mundo.
            sprites.append((imagen,pos,altura))
            if tipo=='cocina' and actor.get('accion')=='verter':
                import numpy as np
                forward=np.asarray(cam['target'],dtype=float)-np.asarray(cam['eye'],dtype=float)
                right=np.cross(forward,(0,1,0));right/=max(float(np.linalg.norm(right)),1e-9)
                ax,ay=anclas['mano_d'][:2];width=altura*imagen.width/imagen.height
                mano=np.asarray(pos)+right*((ax/imagen.width-.5)*width)+(0,(1-ay/imagen.height)*altura,0)
                opciones['ollas'].append(dict(mano=mano.tolist(),piel=piel))
        else:sprites.append((sprite(local,actor,detalle),pos,alto*560/530))
    if tipo=='cocina' and not nativo:
        # Chorro de aceite descendente, posición en mundo y oclusión real.
        m.material=3
        pot=Malla();pot.material=3
        pot.torno((0,0,0),[(0,0),(.24,0),(.30,.09),(.31,.45),(.27,.48),(.26,.10),(0,.07)],'#B97532',24)
        pot.barra((-.28,.15,0),(-.5,.15,0),.045,'#59382C',8)
        angle=-.6+.03*math.sin(local*2);co,si=math.cos(angle),math.sin(angle)
        for x,y,z,nx,ny,nz,*rest in pot.vertices:
            m.vertices.append((.72+co*x-si*y,1.75+si*x+co*y,-5.55+z,co*nx-si*ny,si*nx+co*ny,nz,*rest))
        for i in range(16):
            u=i/16;v=(i+1)/16
            def stream(q):return (1.22+.58*q,1.99-.28*q*q,-5.55+.55*q+.01*math.sin(local*5+q*3))
            m.barra(stream(u),stream(v),.013+.003*math.sin(local*9+i),'#EFC648',8)
        m.material=0
    if p.get('bala'):
        z=4-(local*13)%22
        m.barra((0,1.8,z),(0,1.8,z-.35),.09,'#E6B95B',10)
    volume=None
    if p.get('explosion') or tipo=='puente' and p.get('demostracion',True):
        volume=dict(t=max(0,local-.3),cantidad=min(1,max(0,(local-.3)*2)),pos=(0,0,-7))
    im=_render.render(m,cam,sprites,amb,volume)
    ctx=dict(W=im.width,H=im.height,ancho=im.width,alto=im.height,t=local,duracion=pedido['duracion'])
    for effect in p.get('efectos',[]):fx.efecto(im,effect,local,ctx)
    # Lluvia y streaks originales, coordenadas normalizadas de pantalla.
    if tipo=='mar':
        d=ImageDraw.Draw(im,'RGBA');rng=random.Random(31)
        for i in range(110):
            x=(rng.random()+local*.16)%1*im.width;y=(rng.random()+local*.85)%1*im.height
            d.line((x,y,x-7,y+25),fill=(159,199,245,100),width=1)
    if p.get('whip'):
        strength=math.sin(math.pi*min(1,local/p.get('whip_duracion',.4)))
        im=fx.blur_dir(im,im.width*.12*strength,0)
    if p.get('mirilla'):
        d=ImageDraw.Draw(im);w,h=im.size;mask=Image.new('L',im.size);md=ImageDraw.Draw(mask)
        r=min(w,h)*(.38+local*.08);md.ellipse((w/2-r,h/2-r,w/2+r,h/2+r),fill=255)
        im=Image.composite(im,Image.new('RGB',im.size),mask)
    # Viñeta suave original, sin fingir que aporta geometría 3D.
    return fx.vineta(im,.25)


def crear_audio(pedido,ruta):
    realizacion.audio(pedido,ruta)
