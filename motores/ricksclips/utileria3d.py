"""Utilería extensible original: las escenas eligen objetos/acciones en metros."""
import math
from decorados3d import mesa,tren,barco,barril,silla
from artesania3d import cuenco


def objeto(m,tipo,pos=(0,0,0),t=0,**datos):
    x,y,z=pos
    if tipo=='revolver':
        m.barra((x,y,z),(x,y,z-.6),.075,'#748394',8)
        m.barra((x,y,z+.05),(x,y-.32,z+.16),.09,'#6A3F29',6)
        m.barra((x-.1,y,z-.12),(x+.1,y,z-.12),.12,'#5C6473',10)
    elif tipo=='pistolera':
        m.caja((x,y,z),(.22,.5,.13),'#6B3E2C')
        objeto(m,'revolver',(x,y+.24,z),t)
    elif tipo=='olla':
        m.material=3
        m.torno((x,y,z),[(0,0),(.4,0),(.5,.08),(.5,.6),(.46,.63),(.45,.10),(0,.08)],'#B77941',32)
        for dx in (-.6,.6):m.barra((x+dx,y+.4,z),(x+dx*.8,y+.4,z),.07,'#303543')
        m.torno((x,y,z),[(.44,.50),(0,.50)],'#D2AC31',32)
        m.material=0
    elif tipo=='lata':
        m.caja((x,y+.4,z),(.55,.8,.4),'#B94E38')
        m.caja((x,y+.45,z+.21),(.45,.35,.02),'#D5C497')
        m.barra((x,y+.8,z),(x,y+.88,z),.07,'#C8B989')
    elif tipo=='gancho':
        for i in range(9):
            a=i/8*math.pi;b=(i+1)/8*math.pi
            m.barra((x+math.cos(a)*.35,y+math.sin(a)*.35,z),
                (x+math.cos(b)*.35,y+math.sin(b)*.35,z),.045,'#92A6B8')
        m.barra((x+.35,y,z),(x+.35,y+1.5,z),.035,'#A88C55')
    elif tipo=='vagon':
        m.caja((x,y+1,z),(1.8,1.8,4),'#88533A')
        m.caja((x,y+2,z),(2,.2,4.2),'#293849')
        for dz in (-1.2,0,1.2):
            for dx in (-.92,.92):m.caja((x+dx,y+1.3,z+dz),(.04,.7,.65),'#6DADBF')
        for dz in (-1.2,1.2):
            for dx in (-.9,.9):m.barra((x+dx-.05,y+.2,z+dz),(x+dx+.05,y+.2,z+dz),.3,'#262F3B')
    elif tipo=='cuenco':
        cuenco(m,x,y,z,t)
    elif tipo=='bala':m.barra((x,y,z),(x,y,z-.3),.07,'#D8AB4D',10)
    else:raise ValueError('Utilería no disponible: '+tipo)
