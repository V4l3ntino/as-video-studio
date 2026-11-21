"""Extensión local para el rig plano RicksClips, no para su renderer 3D.

Se incorpora explícitamente a una corrección geometria/1. Reutiliza _fk/_ik2
de la base fijada; no modifica fuentes selladas ni aplica vestuario humano.
"""
import math
from PIL import Image, ImageDraw


def estado_felino(rig):
    return dict(x=320., y=290., esc=1., dir=1, torso=0., rotacion=0.,
        cadera_dy=0., cabeza_inc=0., cola=0., cola_curva=25., mirada=[0.,0.],
        hombro_i=0., hombro_d=0., codo_i=8., codo_d=8.,
        muslo_i=-12., muslo_d=-12., rodilla_i=26., rodilla_d=26.,
        expresion=dict(ojos=.75, abierta=0.), ik={}, sombra=.35,
        pelaje='#EE9748', rayas='#B95422', hocico='#FFF0CE', iris='#649B46')


def pose_felina(rig, estado, contexto=None):
    e=dict(rig.estado_base(),**(estado or {}))
    s=float(e['esc']); d=1 if e['dir']>=0 else -1
    if s<=0:raise ValueError('el gato necesita esc positivo')
    ang=math.radians(float(e['rotacion'])); cs,sn=math.cos(ang),math.sin(ang)
    def W(p):
        x,y=d*p[0]*s,p[1]*s
        return (e['x']+x*cs-y*sn,e['y']+x*sn+y*cs)
    def local(p):
        x,y=p[0]-e['x'],p[1]-e['y']
        return ((x*cs+y*sn)/(d*s),(-x*sn+y*cs)/s)
    inc=math.radians(float(e['torso']))
    pel=(-68.,-72.+float(e['cadera_dy']))
    hom=(pel[0]+132*math.cos(inc),pel[1]+132*math.sin(inc))
    out={}
    for lado,off in (('i',-9.),('d',9.)):
        for delantero in (True,False):
            origen=hom if delantero else pel
            o=(origen[0]+off,origen[1]+(3 if lado=='i' else 0))
            a=float(e[('hombro_' if delantero else 'muslo_')+lado])
            flex=float(e[('codo_' if delantero else 'rodilla_')+lado])
            b=a+flex if delantero else a-flex
            l1,l2=(34.,38.) if delantero else (36.,40.)
            punta=('mano_' if delantero else 'pie_')+lado
            objetivo=(e.get('ik') or {}).get(punta)
            if objetivo is not None:
                i1,i2=rig._ik2(o,local(objetivo),l1,l2,-1 if delantero else 1)
                peso=max(0.,min(1.,float(objetivo[2]) if len(objetivo)>2 else 1.))
                a+=(i1-a)*peso;b+=(i2-b)*peso
            medio,fin=rig._fk(o,a,b,l1,l2)
            out[('hombro_' if delantero else 'cadera_')+lado]=W(o)
            out[('codo_' if delantero else 'rodilla_')+lado]=W(medio)
            out[punta]=W(fin)
    ca=inc+math.radians(float(e['cabeza_inc']))
    cabeza=(hom[0]+24*math.cos(ca),hom[1]-22+24*math.sin(ca))
    def H(x,y):return W((cabeza[0]+x*math.cos(ca)-y*math.sin(ca),cabeza[1]+x*math.sin(ca)+y*math.cos(ca)))
    out.update(pelvis=W(pel),hombro=W(hom),cabeza=W(cabeza),suelo=W((0,0)),
        pecho=W(((pel[0]+hom[0])/2,(pel[1]+hom[1])/2)),radio_cabeza=32*s)
    for lado,x in (('i',-11),('d',11)):out['ojo_'+lado]=H(x,-4)
    puntos=[];a=math.radians(float(e['cola'])-145)
    for i in range(17):
        u=i/16;curva=math.radians(float(e['cola_curva']))*u
        puntos.append(W((pel[0]+100*u*math.cos(a+curva),pel[1]+100*u*math.sin(a+curva))))
    out['cola_puntos']=puntos;out['cola_base']=puntos[0];out['cola_punta']=puntos[-1]
    # Esquinas de cabeza/cuerpo transformadas: caja conservadora incluso al rotar.
    limites=[v for v in out.values() if isinstance(v,tuple)]+puntos
    limites += [H(x,y) for x in (-53,53) for y in (-54,37)]
    margen=25*s
    out['caja']=(min(p[0] for p in limites)-margen,min(p[1] for p in limites)-margen,
        max(p[0] for p in limites)+margen,max(p[1] for p in limites)+margen)
    out['cabeza_angulo']=math.degrees(ca)*d+float(e['rotacion'])
    out['dir']=d
    return out


def dibujar_felino(rig,lienzo,estado,contexto=None):
    e=dict(rig.estado_base(),**(estado or {}));p=rig.pose(e,contexto)
    # Supersampling local: no recursos externos ni dibujo del humano subyacente.
    bx,by,ex,ey=p['caja'];bx,by=math.floor(bx),math.floor(by)
    ss=2;s=float(e['esc'])*ss
    capa=Image.new('RGBA',(max(1,math.ceil(ex-bx)*ss),max(1,math.ceil(ey-by)*ss)))
    dr=ImageDraw.Draw(capa);negro='#211B28'
    def T(q):return ((q[0]-bx)*ss,(q[1]-by)*ss)
    def linea(pts,w,color,borde=True):
        pts=[T(q) for q in pts];w=max(1,round(w*s));ow=max(1,round(2*s))
        for ancho,col in ([(w+ow*2,negro),(w,color)] if borde else [(w,color)]):
            dr.line(pts,fill=col,width=ancho,joint='curve')
            r=ancho/2
            for x,y in pts:dr.ellipse((x-r,y-r,x+r,y+r),fill=col)
    def elipse(c,rx,ry,color):
        x,y=T(c);dr.ellipse((x-rx*s,y-ry*s,x+rx*s,y+ry*s),fill=color)
    # Cola anillada sigue exactamente su cadena articulada.
    linea(p['cola_puntos'],10,e['pelaje'])
    for i in (3,6,9,12,15):linea(p['cola_puntos'][i:i+2],10,e['rayas'],False)
    def pata(lado,delantera):
        nombres=('hombro_','codo_','mano_') if delantera else ('cadera_','rodilla_','pie_')
        pts=[p[n+lado] for n in nombres]
        linea(pts,6,e['rayas'] if lado=='i' else e['pelaje'])
        elipse(pts[-1],8,4,e['hocico'])
    pata('i',False);pata('i',True)
    linea([p['pelvis'],p['hombro']],43,e['pelaje'])
    # Rayas cortas ligadas al eje dorsal, no al lienzo.
    a,b=p['pelvis'],p['hombro'];dx,dy=b[0]-a[0],b[1]-a[1];n=max(.01,math.hypot(dx,dy))
    nx,ny=-dy/n,dx/n
    for u in (.12,.28,.44,.60,.76):
        q=(a[0]+dx*u,a[1]+dy*u)
        linea([(q[0]-nx*19*e['esc'],q[1]-ny*19*e['esc']),
            (q[0]-nx*3*e['esc']+dx*.025,q[1]-ny*3*e['esc']+dy*.025)],4,e['rayas'],False)
    pata('d',False);pata('d',True)
    # Toda la cara (orejas/ojos/bigotes) gira como una sola geometría.
    h=Image.new('RGBA',(240,220));hd=ImageDraw.Draw(h);k=2.
    def Q(x,y):return (120+x*k,112+y*k)
    def oval(x,y,rx,ry,col,borde=False):
        hd.ellipse((*Q(x-rx,y-ry),*Q(x+rx,y+ry)),fill=col,outline=negro if borde else None,width=4)
    for lado in (-1,1):
        hd.polygon([Q(lado*10,-23),Q(lado*30,-51),Q(lado*32,-12)],fill=e['pelaje'],outline=negro,width=4)
        hd.polygon([Q(lado*18,-25),Q(lado*27,-42),Q(lado*28,-20)],fill='#E9A6A0')
    oval(0,0,33,29,e['pelaje'],True)
    for x in (-14,0,14):hd.line([Q(x,-25),Q(x*.65,-12)],fill=e['rayas'],width=5)
    mirada=e.get('mirada') or [0,0];ojos=max(0.,min(1.,(e.get('expresion') or {}).get('ojos',.75)))
    for lado in (-1,1):
        x=lado*12
        if ojos>.12:
            oval(x,-4,8,9*ojos,e['iris'],True)
            oval(x+float(mirada[0])*3,-4+float(mirada[1])*2,2,7*ojos,negro)
            oval(x-2,-7,1.3,1.3,'white')
        else:hd.line([Q(x-7,-4),Q(x+7,-4)],fill=negro,width=4)
        oval(lado*9,13,13,10,e['hocico'])
        for j in (-1,0,1):hd.line([Q(lado*11,13+j*3),Q(lado*51,11+j*9)],fill='white',width=2)
    hd.polygon([Q(-5,8),Q(5,8),Q(0,14)],fill='#A65E65',outline=negro)
    hd.line([Q(0,14),Q(0,19),Q(-6,22)],fill=negro,width=3)
    hd.line([Q(0,19),Q(6,22)],fill=negro,width=3)
    abierta=max(0.,min(1.,(e.get('expresion') or {}).get('abierta',0)))
    if abierta:oval(0,24,4,7*abierta,'#CE7C85')
    if p['dir']<0:h=h.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    h=h.resize((max(1,round(h.width*s/2)),max(1,round(h.height*s/2))),Image.Resampling.LANCZOS)
    h=h.rotate(-p['cabeza_angulo'],Image.Resampling.BICUBIC,expand=True)
    cx,cy=T(p['cabeza']);capa.alpha_composite(h,(round(cx-h.width/2),round(cy-h.height/2)))
    capa=capa.resize((capa.width//ss,capa.height//ss),Image.Resampling.LANCZOS)
    lienzo.paste(capa,(bx,by),capa)
    return p


def caminar_felino(rig,t,vel=1.,amp=1.):
    fase=2*math.pi*1.5*vel*t
    salida=dict(cadera_dy=-2*amp*abs(math.sin(fase)),cola=6*math.sin(fase*.5))
    for lado,signo in (('i',1),('d',-1)):
        u=math.sin(fase)*signo
        salida.update({ 'hombro_'+lado:24*amp*u,'codo_'+lado:8+30*amp*max(0,-u),
            'muslo_'+lado:-12-24*amp*u,'rodilla_'+lado:26+25*amp*max(0,u)})
    return salida


def sentarse_felino(rig,u):
    k=rig._ease(u)
    return dict(cadera_dy=27*k,torso=-12*k,muslo_i=-65*k,muslo_d=-65*k,
        rodilla_i=75*k,rodilla_d=75*k,cola=30*k)


def saludar_felino(rig,t,freq=2.5):
    return dict(hombro_d=100.,codo_d=35+15*math.sin(2*math.pi*freq*t),cabeza_inc=-12.)


EXTENSIONES={'estado_base':estado_felino,'pose':pose_felina,'dibujar':dibujar_felino,
    'caminar':caminar_felino,'sentarse':sentarse_felino,'saludar':saludar_felino}
