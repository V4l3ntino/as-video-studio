"""Cámara en metros y montaje local. Easing, ojo/mirilla, whip, fundido.
Los planos nuevos conservan el reloj y las marcas de voz del Estudio.
"""
import math
import random
import wave
import array
from PIL import Image, ImageDraw, ImageChops


def interpolar(a,b,u):
    if isinstance(a,dict) and isinstance(b,dict):
        return {k:interpolar(a.get(k,v),v,u) for k,v in b.items()} | {k:v for k,v in a.items() if k not in b}
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        return [interpolar(x,y,u) for x,y in zip(a,b)]
    if type(a) in (int,float) and type(b) in (int,float):return a+(b-a)*u
    return b if u>=1 else a


def camara(claves,t):
    if not claves:return {}
    if t<=claves[0]['t']:return {k:v for k,v in claves[0].items() if k!='t'}
    for a,b in zip(claves,claves[1:]):
        if t<=b['t']:
            u=(t-a['t'])/(b['t']-a['t']);u=u*u*(3-2*u)
            return {k:v for k,v in interpolar(a,b,u).items() if k!='t'}
    return {k:v for k,v in claves[-1].items() if k!='t'}


def transicion(origen,destino,u,tipo='fundido',centro=(.5,.5)):
    """Dos fotogramas programados, nunca referencias usadas como decorado."""
    u=max(0,min(1,u));w,h=origen.size
    if tipo=='fundido':return Image.blend(origen,destino,u)
    if tipo in ('pupila','mirilla'):
        mask=Image.new('L',(w,h));d=ImageDraw.Draw(mask)
        r=math.hypot(w,h)*u*u;cx,cy=centro[0]*w,centro[1]*h
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=255)
        return Image.composite(destino,origen,mask)
    if tipo=='whip':
        out=Image.new('RGB',(w,h));cut=int(w*u)
        out.paste(origen,(-cut,0));out.paste(destino,(w-cut,0))
        total=out
        for i in range(1,9):total=Image.blend(total,ImageChops.offset(out,int(math.sin(math.pi*u)*i*3),0),1/(i+1))
        return total
    raise ValueError('transición no disponible: '+tipo)


def audio(pedido,ruta):
    """SFX procedurales originales. SIN locución ni consultas de red.
    La música opcional es una herramienta, nunca se añade por defecto al montaje.
    """
    sr=22050;dur=pedido['duracion'];events=(pedido.get('parametros') or {}).get('sfx',[])
    if not events:return
    samples=[0.] * round(sr*dur)
    for j,ev in enumerate(events):
        start=ev.get('at',0);length=min(ev.get('dur',.7),dur-start)
        if start<0 or length<=0:raise ValueError('SFX fuera de duración')
        rng=random.Random(ev.get('seed',j));gain=min(.7,max(0,ev.get('gain',.2)))
        name=ev.get('name','whoosh');filt=0
        for i in range(round(length*sr)):
            t=i/sr;u=t/length;n=rng.uniform(-1,1);filt=.94*filt+.06*n
            if name in ('explosion','trueno'):v=filt*5*math.exp(-u*4)
            elif name in ('olas','lluvia'):v=n*.35*math.sin(math.pi*u)
            elif name=='tren':v=n*max(0,math.sin(t*math.tau*6))**12
            elif name=='disparo':v=n*math.exp(-u*15)+math.sin(t*math.tau*90)*math.exp(-u*20)
            else:v=n*math.sin(math.pi*u)**2
            k=round(start*sr)+i
            if k<len(samples):samples[k]+=v*gain
    data=array.array('h',(round(max(-1,min(1,v))*32760) for v in samples))
    with wave.open(ruta,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes(data.tobytes())
