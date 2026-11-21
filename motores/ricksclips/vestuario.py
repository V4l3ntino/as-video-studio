"""Vestuario original ligado a anclas del rig; conserva FK/IK y apariencias.

Accesorios 2D explícitos, no se presentan como geometría 3D. La capa gira con
la cabeza. Se aplica también al rig que se congela para los vídeos nuevos.
"""
import math
from PIL import Image,ImageDraw


def dibujar(im,e,p,colores,ropa):
    s=p['esc'];r=p['radio_cabeza'];cx,cy=p['cabeza'];d=p['d']
    negro='#211B28';acento=colores.get('acento','#E8BF62')
    # Costuras y botones ajustados al eje del torso, no a la pantalla.
    pelvis,hombro=p['pelvis'],p['hombro']
    dx,dy=pelvis[0]-hombro[0],pelvis[1]-hombro[1]
    n=max(.01,math.hypot(dx,dy));nx,ny=-dy/n,dx/n
    draw=ImageDraw.Draw(im)
    def pt(u,off):return (hombro[0]+u*dx+nx*off*s,hombro[1]+u*dy+ny*off*s)
    if ropa in ('chaqueta','camisa'):
        for off in (-14,14):
            draw.line([pt(.18,off),pt(.78,off)],fill=acento,width=max(1,round(s*1.3)))
        for u in (.30,.47,.64,.80):
            x,y=pt(u,7);q=1.8*s
            draw.ellipse((x-q,y-q,x+q,y+q),fill=acento,outline=negro,width=max(1,round(s*.5)))
        x,y=pt(.56,-11)
        draw.line([(x-4*s,y-5*s),(x+4*s,y-5*s),(x+4*s,y+7*s),(x-4*s,y+7*s),(x-4*s,y-5*s)],fill=negro,width=max(1,round(s)))
    if e.get('cinturon',ropa=='chaqueta'):
        a,b=pt(.87,-22),pt(.87,22)
        draw.line((a,b),fill='#533B30',width=max(2,round(7*s)))
        x,y=pt(.87,0)
        draw.rounded_rectangle((x-6*s,y-5*s,x+6*s,y+5*s),radius=2*s,fill=acento,outline=negro,width=max(1,round(s)))
        for k in (-1,1):
            x,y=pt(.90,k*14)
            draw.ellipse((x-1.2*s,y-1.2*s,x+1.2*s,y+1.2*s),fill='#D2B883')
    hat=e.get('sombrero')
    if not hat:return
    # Local head layer at enough resolution; no hard-coded y offset from canvas.
    size=max(24,round(r*4.6));layer=Image.new('RGBA',(size,size));dr=ImageDraw.Draw(layer)
    c=size/2
    def box(x0,y0,x1,y1):return (c+x0*r,c+y0*r,c+x1*r,c+y1*r)
    lw=max(1,round(r*.055));tipo=str(hat)
    if tipo=='chef':
        dr.polygon([(c-.75*r,c-.9*r),(c-.94*r,c-2*r),(c+.94*r,c-2*r),(c+.75*r,c-.9*r)],fill='#F6F0E5',outline=negro,width=lw)
        for off in (-.65,-.4,-.15,.15,.4,.65):dr.line((c+off*r,c-1.0*r,c+off*1.2*r,c-1.95*r),fill='#C2BFCA',width=max(1,lw//3))
        for x,y,rx,ry in ((-.65,-1.97,.47,.27),(0,-2.07,.63,.38),(.65,-1.98,.47,.28)):
            dr.ellipse(box(x-rx,y-ry,x+rx,y+ry),fill='#FFF9EB',outline=negro,width=lw)
        dr.rectangle(box(-.76,-1.13,.76,-.90),fill='#E4DFDF',outline=negro,width=lw)
    elif tipo=='gorra':
        dr.ellipse(box(-1.04,-1.55,1.02,-.90),fill='#518085',outline=negro,width=lw)
        for j in range(11):
            x=-.85+j*.17;dr.line((c+x*r,c-1.44*r,c+x*.7*r,c-1.02*r),fill='#E4D9C3',width=max(1,lw//2))
        dr.ellipse(box(-.9,-1.04,1.28,-.86),fill='#304A50',outline=negro,width=lw)
    else:
        tan=tipo=='oeste';base='#BC8F52' if tan else '#30303C';hi='#DDBA7B' if tan else '#535262'
        top=-1.8 if tipo=='chistera' else -1.46
        dr.polygon([(c-.74*r,c-.93*r),(c-.64*r,c+top*r),(c-.25*r,c+(top+.12)*r),(c+.24*r,c+(top+.10)*r),(c+.64*r,c+top*r),(c+.77*r,c-.93*r)],fill=base,outline=negro,width=lw)
        dr.polygon([(c-.57*r,c+(top+.13)*r),(c-.37*r,c+(top+.24)*r),(c-.38*r,c-.99*r),(c-.61*r,c-.99*r)],fill=hi)
        dr.rectangle(box(-.69,-1.06,.72,-.94),fill='#694932' if tan else '#9F4F36')
        dr.ellipse(box(-1.5,-1.0,1.5,-.80),fill=base,outline=negro,width=lw)
        dr.arc(box(-1.4,-1.06,1.4,-.81),0,175,fill=hi,width=max(1,lw//2))
    if e.get('bigote'):
        for k in (-1,1):
            dr.polygon([(c+.12*r,c+.20*r),(c+k*.55*r,c+.28*r),(c+k*.39*r,c+.46*r),(c+.05*r,c+.33*r)],fill=negro)
    ang=-(float(e.get('cabeza_inc',0))+p['inc'])
    layer=layer.rotate(ang,resample=Image.Resampling.BICUBIC)
    if d<0:layer=layer.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    im.alpha_composite(layer,(round(cx-size/2),round(cy-size/2))) if im.mode=='RGBA' else im.paste(layer,(round(cx-size/2),round(cy-size/2)),layer)
