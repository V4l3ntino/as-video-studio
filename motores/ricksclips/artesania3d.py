"""Recursos originales de detalle, reutilizables en cualquier escena libre.

Geometría en metros. Ninguna textura/fondo procede del vídeo de referencia.
"""
import math
import random


def rotulo(m,texto,p,ancho=2.5,alto=.5,color='#F2D9A1'):
    """Letras de cartel construidas con trazos 3D, sin fuentes ni imágenes externas."""
    # Alfabeto de segmentos: diseñado para letreros breves, no para subtítulos.
    glyphs={'A':(0,1,2,3,4,5),'B':(1,2,3,4,5,6,7),'C':(0,3,4,6),
        'D':(1,2,3,4,6,7),'E':(0,3,4,5,6),'F':(0,4,5),
        'G':(0,2,3,4,6),'H':(1,2,4,5,7),'I':(0,3,8),'L':(3,4,7),
        'M':(1,2,4,7,9,10),'N':(1,2,4,7,11),'O':(0,1,2,3,4,7),
        'P':(0,1,4,5,7),'R':(0,1,4,5,7,12),'S':(0,2,3,4,5),
        'T':(0,8),'U':(1,2,3,4,7),'W':(1,2,4,7,12,13),'Y':(9,10,14)}
    segments=[((0,1),(1,1)),((1,1),(1,.5)),((1,.5),(1,0)),((0,0),(1,0)),
        ((0,1),(0,.5)),((0,.5),(1,.5)),((0,1),(0,0)),((0,.5),(0,0)),
        ((.5,0),(.5,1)),((0,1),(.5,.5)),((1,1),(.5,.5)),((0,1),(1,0)),
        ((.5,.5),(1,0)),((0,0),(.5,.5)),((.5,.5),(.5,0))]
    x,y,z=p;cell=ancho/max(1,len(texto));m.material=0
    for i,ch in enumerate(texto.upper()):
        for seg in glyphs.get(ch,()):
            a,b=segments[seg]
            m.barra((x-ancho/2+(i+a[0]*.72)*cell,y+a[1]*alto,z),
                (x-ancho/2+(i+b[0]*.72)*cell,y+b[1]*alto,z),.017,color,4)


def farol(m,x,y,z):
    m.material=3
    m.barra((x,y+.45,z),(x,y+.9,z),.026,'#302B39',8)
    m.torno((x,y,z),[(.20,0),(.24,.06),(.16,.10),(.16,.37),(.26,.40),(0,.54)],'#3C3439',16)
    m.esfera((x,y+.23,z),(.12,.19,.12),'#FFE3A1',em=.75)
    for dx in (-.14,.14):
        for dz in (-.14,.14):m.barra((x+dx,y+.07,z+dz),(x+dx,y+.4,z+dz),.018,'#453B37',6)


def botella(m,x,y,z,color):
    m.material=3
    m.torno((x,y,z),[(0,0),(.10,0),(.11,.04),(.11,.36),(.05,.43),(.04,.58),(0,.58)],color,12)
    m.material=0
    m.torno((x,y,z),[(.112,.12),(.112,.27)],'#D9BF88',12)
    m.barra((x,y+.58,z),(x,y+.62,z),.045,'#AC8757',8)


def cuenco(m,x,y,z,t=0):
    m.material=0
    m.torno((x,y,z),[(0,0),(.24,0),(.34,.06),(.52,.29),(.55,.32),(.51,.34),(.47,.29),(.28,.07),(0,.07)],'#F0DEC1',40)
    m.material=3
    m.torno((x,y,z),[(.46,.26),(0,.26)],'#E5AE34',40)
    m.material=0
    for j in range(4):
        r=(t*.09+j*.115)%.44
        m.torno((x,y+.265,z),[(r+.009,0),(r,0)],'#FFDF72',40)
    for j in range(12):
        a=j*2.399;r=.08+.3*(j%4)/4
        m.torno((x+math.cos(a)*r,y+.27,z+math.sin(a)*r),[(.025,0),(.04,.007),(.03,.01)],'#F7D96E',12)


def detalle(m,tipo,t,opciones=None):
    rng=random.Random(437)
    if tipo in ('oeste','desierto'):
        # Vías de rueda, matojos, postes/aisladores, travesaños y tendido curvo.
        m.material=5
        for x in (-1.5,1.5):
            for j in range(24):
                z=8-j*1.8;m.caja((x+.06*math.sin(j),-.005,z),(.13,.018,1.65),'#BD965D')
        m.material=1
        for x in (-4.6,4.6):
            for z in (-4,-17,-30):
                m.barra((x,0,z),(x,6,z),.095,'#6C4C35',8)
                m.caja((x,5.6,z),(1.2,.09,.12),'#453B36')
                for dx in (-.45,.45):
                    m.barra((x+dx,5.6,z),(x+dx,5.94,z),.055,'#A0C0C2',8)
                    for j in range(12):
                        za=z-j*13/12;zb=z-(j+1)*13/12
                        ya=5.9-.5*math.sin(math.pi*j/12);yb=5.9-.5*math.sin(math.pi*(j+1)/12)
                        m.barra((x+dx,ya,za),(x+dx,yb,zb),.012,'#353742',4)
        for j in range(48):
            x=rng.uniform(-5,5);z=rng.uniform(-22,8)
            if abs(x)<2.4:continue
            for k in range(5):
                a=k*1.7;m.barra((x,.01,z),(x+.17*math.cos(a),.12+rng.random()*.22,z+.17*math.sin(a)),.012,'#8B8150',4)
    elif tipo in ('taberna','cocina','oficina'):
        m.material=1
        # Planchas y juntas de pared y techo, vigas y marcos, no pared lisa.
        for j in range(19):
            yy=.17+j*.31
            m.caja((0,yy,-11.79),(13.7,.285,.08),'#B87942' if tipo=='cocina' else '#75434B')
        for zz in (-1,-4,-7,-10):
            m.caja((0,6,zz),(14,.28,.28),'#59382F')
            for x in (-6.3,6.3):m.barra((x,4.9,zz),(x*.8,5.9,zz),.11,'#92613B',4)
        for j in range(14):m.caja((-6.5+j,6.2,-5),(.97,.12,19),'#9B623C')
        if tipo=='cocina':
            # Menuiserie de cuisine, panneaux encastrés, boutons et crédence.
            for x in (-4.9,-3.5,-2.1,.2,1.6,3):
                m.caja((x,.65,-6.8),(1.3,1.3,1.45),'#633A29')
                m.caja((x,.68,-6.04),(1.12,1.10,.08),'#A46531')
                m.caja((x,.68,-5.98),(.87,.86,.035),'#7C4227')
                m.barra((x+.36,.82,-5.94),(x+.36,.82,-5.86),.055,'#E7BC63',12)
            m.caja((-.8,1.36,-6.8),(9.7,.16,1.7),'#D8B77D')
            for j in range(32):m.caja((-5.5+j*.30,1.448,-6.8),(.014,.01,1.6),'#93633F')
            for j in range(10):
                a=j*math.tau/10
                m.esfera((math.cos(a),3.6+math.sin(a),-11.25),.055,'#70562C',4,8)
            m.barra((-5,3.8,-11.4),(5,3.8,-11.4),.045,'#4B3435',8)
            for x in (-4,-2,2,4):
                m.barra((x,3.8,-11.3),(x,3.25,-11.3),.024,'#383344',6)
                m.torno((x,2.75,-11.1),[(.25,0),(.34,.05),(.34,.30),(.29,.32),(.29,.08),(0,.06)],'#A15B2E',20)
            if not (opciones or {}).get('blender'):cuenco(m,1.8,1.46,-5,t)
        else:
            for yy in (2.66,3.86,5.06):
                for j in range(8):botella(m,-1+j*.85,yy,-10.98,('#307C64','#B27331','#5B497D')[j%3])
            # Panelado de barra y cajones; vasos y cartas sobre mesa de acción.
            m.material=1
            for x in (-1.7,-.1,1.5,3.1,4.7):
                m.caja((x,1.1,-7.36),(1.4,1.65,.07),'#AE6537')
                m.caja((x,1.1,-7.30),(1.12,1.36,.04),'#69392E')
            for x,z in ((-1.5,-2),(-.4,-1.8)):
                m.torno((x,1.4,z),[(.10,0),(.14,.24),(.12,.25),(.085,.04)],'#B99F75',18)
            for j in range(6):
                m.caja((-1.8+j*.25,1.39,-2.3),(.17,.012,.27),'#E8D6BA')
                m.esfera((-1.8+j*.25,1.40,-2.3),(.025,.007,.035),'#A73F36',3,6)
        for x in (-4,4):farol(m,x,4.3,-5)
    elif tipo in ('canon','puente'):
        # Ballast visible près des rails. Instances déterministes, pas texture photo.
        m.material=2
        if tipo=='canon':
            for j in range(650):
                x=rng.uniform(-1.25,4.3);z=rng.uniform(-30,10)
                r=rng.uniform(.045,.13)
                m.esfera((x,.075,z),(r,r*.55,r*.8),('#A68C81','#BEAE9E','#6D696D','#B2886D')[j%4],3,5)
        else:
            m.material=3
            for z in range(-28,11,2):
                for x in (-1.9,1.9):
                    m.caja((x,.10,z),(.30,.03,.28),'#49434D')
                    for dz in (-.08,.08):m.esfera((x,.13,z+dz),.032,'#D0B380',3,6)
    m.material=0
