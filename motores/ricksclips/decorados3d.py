"""Escenografía original parametrizable. Toda arquitectura/agua/utilería es malla 3D.
X lateral, Y arriba, cámara mira hacia -Z. Sin fondos fotografiados ni generados.
"""
import math
import random
import numpy as np
from espacio3d import Malla,normal,Renderer
from artesania3d import detalle,rotulo,cuenco


def mesa(m,x,y,z,w=2,d=1):
    m.caja((x,y,z),(w,.16,d),'#AD6D35')
    for dx in (-w*.4,w*.4):
        for dz in (-d*.35,d*.35):m.caja((x+dx,y/2,z+dz),(.12,y,.12),'#563021')


def barril(m,x,y,z,r=.4):
    m.material=1
    m.torno((x,y,z),[(0,0),(r*.8,0),(r,.2),(r*1.06,.5),(r,.8),(r*.8,1),(0,1)],'#A46A36',24)
    m.material=3
    for dy,rr in ((.12,.94),(.48,1.08),(.85,.94)):
        m.torno((x,y+dy,z),[(r*rr,0),(r*rr,.06)],'#45404A',24)
    m.material=0


def silla(m,x,y,z):
    m.caja((x,y+.6,z),(.65,.12,.65),'#9A572C')
    for dx in (-.25,.25):
        for dz in (-.25,.25):m.caja((x+dx,y+.3,z+dz),(.09,.6,.09),'#522B25')
    m.caja((x,y+1.15,z-.28),(.65,.75,.1),'#9A572C')


def edificio(m,x,z,w=4,h=5,d=5,color='#AF5849',cartel=True,variante=0):
    m.material=1
    m.caja((x,h/2,z),(w,h,d),color)
    front=z+d/2
    # Falsa fachada, cornisa, tablones y porche con pilares/voladizo.
    m.caja((x,h+.35,front-.12),(w+.3,.7,.3),color)
    for yy in [i*.3 for i in range(int(h/.3))]:
        m.caja((x,yy,front+.015),(w,.025,.03),'#774B48')
    m.caja((x,h,front+.05),(w+.55,.18,.45),'#EBC688')
    if variante%3==1:
        # Remate escalonado y pilastras, distinto de la cornisa corrida.
        for width,yy in ((w*.70,h+.78),(w*.42,h+1.03)):
            m.caja((x,yy,front-.12),(width,.36,.36),color)
            m.caja((x,yy+.19,front-.08),(width+.14,.08,.48),'#E3BC80')
    elif variante%3==2:
        m.triangulo((x-w*.52,h+.65,front+.06),(x+w*.52,h+.65,front+.06),(x,h+1.5,front+.06),color)
        for side in (-1,1):m.barra((x+side*w*.52,h+.65,front+.09),(x,h+1.5,front+.09),.055,'#E4C18D',6)
    if variante%2:
        for side in (-1,1):m.caja((x+side*w*.48,h*.5,front+.09),(.16,h,.18),'#D1AC78')
    m.caja((x,2.65,front+.8),(w+.5,.16,1.9),'#CBA15F')
    m.caja((x,.15,front+.65),(w+.45,.3,1.9),'#AA754A')
    for xx in (-w*.43,w*.43):
        m.caja((x+xx,1.45,front+1.35),(.16,2.7,.16),'#E0B67A')
        m.barra((x+xx,2.1,front+1.35),(x+xx+(.5 if xx<0 else -.5),2.6,front+1.35),.065,'#E0B67A')
    m.caja((x,.95,front+.04),(.85,1.9,.06),'#382A37')
    for xx in (-w*.3,w*.3):
        for yy in (1.3,3.65):
            m.caja((x+xx,yy,front+.05),(.85,1.05,.08),'#E4BA7C')
            m.caja((x+xx,yy,front+.10),(.64,.85,.06),'#304E65')
            m.caja((x+xx,yy,front+.15),(.045,.85,.04),'#D9A873')
            m.caja((x+xx,yy,front+.15),(.64,.04,.04),'#D9A873')
    # Porche entablado, balaustrada, contraventanas y molduras con relieve.
    for j in range(int(w/.23)):
        m.caja((x-w/2+j*.23,.315,front+.65),(.215,.025,1.85),'#BF915A')
    for dx in (-w*.43,w*.43):
        m.caja((x+dx,1.0,front+.75),(.09,.09,1.1),'#D1AC77')
        for dz in (.4,.7,1):m.caja((x+dx,.65,front+dz),(.05,.7,.05),'#99744C')
    for xx in (-w*.3,w*.3):
        for yy in (1.3,3.65):
            for sx in (-.52,.52):
                m.caja((x+xx+sx,yy,front+.12),(.17,1.1,.08),'#BEA072')
                for j in range(6):m.caja((x+xx+sx,yy-.45+j*.17,front+.18),(.16,.025,.04),'#715747')
            m.caja((x+xx,yy-.58,front+.18),(1.25,.10,.24),'#E2BD83')
    m.caja((x,2.52,front+1.78),(w+.6,.17,.15),'#E1BF8A')
    if cartel:
        m.caja((x,3.,front+.14),(w*.8,.64,.14),'#402E39')
        rotulo(m,'SALOON' if color=='#AB5048' else ('GENERAL' if color=='#5A8C81' else 'POST'),
            (x,2.81,front+.23),w*.7,.38)
    m.material=0


def roca(m,x,z,w,h,d,seed=0):
    rng=random.Random(seed); levels=18; sides=18
    rings=[]
    for j in range(levels):
        taper=1-j/(levels-1)*.27
        shelf=1+.055*math.sin(j*2.2)+.035*math.sin(j*4.3)
        rings.append([(x+math.cos(i*math.tau/sides)*w*taper*shelf*(1+.04*math.sin(i*3+seed)),
            -.4+h*j/(levels-1)+.10*math.sin(i*1.4+j*.6),z+math.sin(i*math.tau/sides)*d*taper*shelf) for i in range(sides)])
    colors=['#D57C42','#DC8549','#D5743E','#C76A39','#E79351','#E69A58']
    m.material=2
    for j in range(levels-1):
        for i in range(sides):
            m.quad(rings[j+1][i],rings[j+1][(i+1)%sides],rings[j][(i+1)%sides],rings[j][i],colors[j%len(colors)])
    for i in range(sides):m.triangulo((x,h-.4,z),rings[-1][i],rings[-1][(i+1)%sides],'#E99458')
    m.material=0


def vias(m,t=0,x=0,y=0,inicio=8,fin=-32,torcido=0,hueco=.08):
    n=int((inicio-fin)/.65)
    def off(z):return math.sin(z*.65+t*2)*torcido*.7
    for i in range(n):
        z=inicio-i*.65
        m.material=1
        m.caja_girada((x+off(z),y+.05,z),(2.1,.14,.23),'#69452F',math.atan((off(z+.02)-off(z-.02))/.04))
        for dx in (-.65,.65):
            m.material=3
            # Perfil en I: patín, alma y cabeza, juntas visibles, no tubos.
            for yy,rr in ((.12,.09),(.20,.035),(.28,.065)):
                m.barra((x+dx+off(z),y+yy,z),(x+dx+off(z-.65),y+yy,z-.65+hueco),rr,'#A8A4A0',4)
            m.caja((x+dx+off(z),y+.14,z),(.18,.04,.32),'#3D3B44')
    m.material=0


def pared_canon(m,lado=1,inicio=18,fin=-65,base=-9,altura=25,distancia=9,seed=0):
    """Macizo continuo: contrafuertes verticales, cárcavas y cornisas discontinuas.

    La misma superficie conecta todas las muestras longitudinales; no son torres
    superpuestas. El relieve tiene escala métrica y las grietas son hendiduras de
    la malla, no líneas de pantalla ni una textura tomada de la referencia.
    """
    nz=100;ny=36
    def punto(i,j):
        z=inicio+(fin-inicio)*i/nz;u=j/ny
        crest=altura+2.2*math.sin(z*.19+seed)+1.1*math.sin(z*.53+seed*.3)
        buttress=1.6*math.sin(z*.25+seed)+.65*math.sin(z*.61+seed)
        groove=max(0,math.cos(z*.92+seed+u*.8))**18
        ledge=.27*math.sin(u*19+math.sin(z*.22))*math.sin(z*.37+seed)**2
        x=distancia+2.6*u+buttress*(.5+.5*u)+groove*(.35+u*.8)+ledge
        # Talus joins the wall to its foot instead of hovering above the floor.
        x-=1.4*math.exp(-u*12)
        return (lado*x,base+u*crest,z)
    m.material=2
    for i in range(nz):
        for j in range(ny):
            a,b,c,d=punto(i,j),punto(i+1,j),punto(i+1,j+1),punto(i,j+1)
            u=(j+.5)/ny;z=(a[2]+b[2])/2
            # Broad mineral beds, with gradual shifts rather than alternating rings.
            bed=.5+.5*math.sin(u*10+math.sin(z*.12)*.7)
            col=(.76+.12*bed,.30+.14*bed,.12+.08*bed)
            if lado>0:m.quad(a,d,c,b,col)
            else:m.quad(a,b,c,d,col)
    m.material=0


def tren(m,x,y,z):
    m.material=3
    m.caja((x,y+.65,z),(1.25,.35,3.6),'#263240')
    m.barra((x,y+1.15,z+.5),(x,y+1.15,z-1.3),.55,'#367565',12)
    # Cabina hueca: ventanas entre montantes, antepecho y entrada posterior.
    # También se modela detrás; no esconder una caja mediante la cámara.
    for side in (-1,1):
        xx=x+side*.66
        m.caja((xx,y+1.03,z+1),(.09,.65,1.25),'#317562')
        for zz in (.4,1.6):m.caja((xx,y+1.73,z+zz),(.09,.85,.10),'#BDA16A')
        m.caja((xx,y+2.12,z+1),(.10,.12,1.3),'#317562')
        m.caja((xx,y+1.72,z+.92),(.035,.62,.90),'#416879')
        m.barra((xx+side*.06,y+1.35,z+.43),(xx+side*.06,y+1.35,z+1.55),.025,'#D3AE6C',8)
        # Rear quarter panels leave a genuinely open central doorway.
        m.caja((x+side*.49,y+1.6,z+1.64),(.32,1.1,.09),'#317562')
        m.caja((x+side*.49,y+1.78,z+1.7),(.22,.45,.025),'#7395A1')
        m.barra((x+side*.29,y+1.05,z+1.76),(x+side*.29,y+2.03,z+1.76),.026,'#D2B275',8)
        for sy in (.55,.78):m.caja((x+side*.69,y+sy,z+1.7),(.32,.08,.4),'#343641')
    m.caja((x,y+.94,z+1), (1.15,.12,1.1),'#574239')
    m.caja((x,y+1.3,z+.5),(.7,.9,.15),'#34333B')
    # Vaulted roof with rolled eaves, not a rectangular lid.
    for i in range(16):
        a=-math.pi/2+i*math.pi/16;b=-math.pi/2+(i+1)*math.pi/16
        def roof(v,zz):return (x+.84*math.sin(v),y+2.14+.24*math.cos(v),z+zz)
        m.quad(roof(a,.22),roof(a,1.82),roof(b,1.82),roof(b,.22),'#263744')
    for side in (-1,1):m.barra((x+side*.84,y+2.14,z+.22),(x+side*.84,y+2.14,z+1.82),.035,'#B69D70',8)
    m.barra((x,y+1.5,z-.9),(x,y+2.35,z-.9),.18,'#343644')
    m.esfera((x,y+1.46,z-1.62),.15,'#FFD893',em=1)
    # Smokebox face, brass rim, buffers, cowcatcher and boiler fittings.
    m.barra((x,y+1.15,z-1.32),(x,y+1.15,z-1.43),.53,'#202F39',32)
    m.barra((x,y+1.15,z-1.44),(x,y+1.15,z-1.48),.40,'#AB8A54',32)
    m.barra((x,y+1.15,z-1.49),(x,y+1.15,z-1.51),.35,'#283845',32)
    m.barra((x-.13,y+1.15,z-1.53),(x+.13,y+1.15,z-1.53),.023,'#D8B979',8)
    for zz,rr,hh in ((-.85,.21,.25),(-.12,.24,.27),(.35,.16,.2)):
        m.torno((x,y+1.6,z+zz),[(rr,0),(rr,hh*.7),(rr*.72,hh),(0,hh+.03)],'#B39151',24)
    for side in (-1,1):
        m.barra((x+side*.56,y+.91,z-.95),(x+side*.56,y+.91,z+.25),.12,'#314E50',16)
        m.barra((x+side*.57,y+1.42,z-1.2),(x+side*.57,y+1.42,z+.38),.026,'#D1AD6D',8)
        m.barra((x+side*.46,y+.65,z-1.8),(x+side*.46,y+.65,z-1.93),.12,'#3C3C45',16)
        for j in range(6):
            xx=x+side*j*.12
            m.barra((xx,y+.7,z-1.58),(xx,y+.25,z-2.12+abs(xx-x)*.4),.025,'#9C8060',6)
    for dz in (-1.05,0,1.05):
        for dx in (-.72,.72):
            m.barra((x+dx-.05,y+.5,z+dz),(x+dx+.05,y+.5,z+dz),.35,'#292D3B',20)
            for j in range(8):
                a=j*math.tau/8
                m.barra((x+dx*1.09,y+.5,z+dz),(x+dx*1.09,y+.5+.29*math.cos(a),z+dz+.29*math.sin(a)),.022,'#B69768',6)
            m.barra((x+dx*1.1,y+.43,z-1.1),(x+dx*1.1,y+.43,z+1.1),.035,'#BDAD8D',6)
    for dz in (-1,-.5,0,.5):
        for j in range(24):
            a=j*math.tau/24;b=(j+1)*math.tau/24
            m.barra((x+.56*math.cos(a),y+1.15+.56*math.sin(a),z+dz),
                (x+.56*math.cos(b),y+1.15+.56*math.sin(b),z+dz),.022,'#B8A374',6)
    m.barra((x-.5,y+.8,z-1.5),(x+.5,y+.8,z-1.5),.04,'#BAA174',8)
    m.material=0


def barco(m,t,x=0,z=-8):
    y=.7+math.sin(t*1.6)*.25
    m.material=1
    # Coque à couples effilés, virures et pont fermé (géométrie originale).
    def pt(side,j,k):
        zz=-3.8+j*6.6/16;beam=1.35*max(.025,math.sin(math.pi*j/16))**.45
        return (x+side*beam*(.55+k*.15),y-.7+k*.29,z+zz)
    for side in (-1,1):
        for j in range(16):
            for k in range(4):m.quad(pt(side,j,k),pt(side,j+1,k),pt(side,j+1,k+1),pt(side,j,k+1),
                ('#4B3028','#733E28','#B24D31','#E5BD78')[k])
            a,b=pt(side,j,4),pt(side,j+1,4)
            m.quad((x,a[1],a[2]),a,b,(x,b[1],b[2]),'#BC8C51')
            m.barra(a,b,.045,'#D7B273',6)
            if j%2==0:m.barra(a,(a[0],a[1]+.5,a[2]),.035,'#BB9259',6)
        for j in range(3,14,3):
            p=pt(side,j,2);m.esfera(p,(.045,.13,.13),'#E2C673',5,12)
    for zz in (-1.5,1.3):
        m.barra((x,y+.3,z+zz),(x,y+5.8,z+zz),.10,'#86562F',12)
        for sy in (2.3,4.2):
            m.barra((x-1.5,y+sy,z+zz),(x+1.5,y+sy,z+zz),.055,'#6C452A',8)
            for j in range(12):
                for k in range(8):
                    def sail(a,b):return (x-1.45+a*2.9/12,y+sy-b*1.5/8,z+zz+.30*math.sin(a*math.pi/12)*math.sin(b*math.pi/8)+.06*math.sin(t*2+a*.2))
                    m.quad(sail(j,k),sail(j+1,k),sail(j+1,k+1),sail(j,k+1),'#F1DFB6' if j%4<2 else '#AE4434')
        for dx in (-1.2,1.2):
            for dz in (-2.5,2):m.barra((x,y+5.5,z+zz),(x+dx,y+.6,z+dz),.014,'#413A39',4)
    m.caja((x,y+5.7,z-1.5),(.7,.38,.025),'#243349')
    m.material=0


def oceano(m,t,calma=0,ola=1,espuma=False):
    step=.6;n=74
    def point(i,j):
        x=(i-n/2)*step;z=10-j*step
        patch=math.exp(-((x+1)**2+(z+3)**2)/22)*calma
        h=(math.sin(x*.7+z*.4+t*1.8)*.65+math.sin(z*1.1-t*2)*.28)*(1-patch*.98)
        h+=ola*5.7*math.exp(-((z+15-math.sin(x*.22)*1.5-t*.35)**2)/7)*(1+.06*math.sin(x*.8+t))
        z+=ola*.9*math.exp(-((z+15-t*.35)**2)/9)
        return (x,h,z)
    points={(i,j):point(i,j) for i in range(n+1) for j in range(n+1)}
    normals={}
    for i in range(n+1):
        for j in range(n+1):
            nn=normal(np.cross(np.subtract(point(i+.03,j),point(i-.03,j)),np.subtract(point(i,j+.03),point(i,j-.03))))
            normals[i,j]=nn if nn[1]>0 else -nn
    m.material=4
    for i in range(n):
        for j in range(n):
            a,b,c,d=points[i,j],points[i+1,j],points[i+1,j+1],points[i,j+1]
            crest=max(a[1],b[1],c[1],d[1])
            col='#1355A0'
            # Normales interpolées, suppression des carreaux de couleur arbitraires.
            start=len(m.vertices);m.quad(a,b,c,d,col)
            for k,key in enumerate(((i,j),(i+1,j),(i+1,j+1),(i,j),(i+1,j+1),(i,j+1))):
                v=m.vertices[start+k]
                patch=math.exp(-((v[0]+1)**2+(v[2]+3)**2)/22)*calma
                tint=tuple(v[6+q]*(1-patch*.6)+(.17,.37,.56)[q]*patch*.6 for q in range(3))
                m.vertices[start+k]=(*v[:3],*normals[key],*tint,v[-1])
    m.material=0
    if espuma and ola:
        # Cresta espacial que sigue la misma superficie animada. Espuma
        # procedural, no simulación de fluidos ni un overlay de pantalla.
        for i in range(n):
            for j in range(n):
                a,b=points[i,j],points[i+1,j]
                if min(a[1],b[1])<4.6:continue
                if math.sin(i*2.7+j*.9+t*3)<-.15:continue
                m.barra((a[0],a[1]+.025,a[2]),(b[0],b[1]+.025,b[2]),.024,'#BDD6DD',5)


def _construir(tipo,t,opciones=None):
    o=opciones or {};m=Malla()
    amb=dict(cielo=(.13,.43,.84),niebla=.006)
    cam=dict(eye=(6,3.4,11),target=(0,1.8,-3),fov=49,apertura=.3)
    if tipo in ('oeste','desierto'):
        m.material=5;m.caja((0,-.22,-12),(65,.4,90),'#DBAE64');m.material=0
        for side in (-1,1):
            for i in range(5):
                local=Malla()
                edificio(local,0,0,5.2+(i%3)*.4,3.9+(i%3)*.85,4.5,
                    ['#AB5048','#5A8C81','#BA8B51'][i%3],variante=i+int(side))
                # La fachada mira hacia la calle, no solo hacia el fondo del mundo.
                for v in local.vertices:
                    x,y,z,nx,ny,nz,*rest=v
                    m.vertices.append((-side*z+side*7,y,side*x-5-i*7.2,-side*nz,ny,side*nx,*rest))
        for x,z in ((-3,-1),(3.2,-5),(-3.4,-12)):barril(m,x,0,z)
        for i in range(9):roca(m,(-1 if i%2 else 1)*(15+i),-28-i*4,5,3+i%4,3,i)
        rng=random.Random(11)
        for i in range(95):
            x=rng.uniform(-5,5);z=rng.uniform(-25,10)
            m.esfera((x,.01,z),(.05,.025,.08),'#AE8855',3,5)
        for x,z in ((-13,-25),(10,-32),(-7,-40)):
            for j in range(7):
                m.esfera((x+(j-3)*.85,12+.4*math.sin(j),z+.3*math.cos(j)),(1.2,.7+.2*(j%3),.8),'#E2EAF0',8,12)
        cam.update(eye=(1.7,2.2,7),target=(0,1.55,-2),fov=46)
    elif tipo in ('taberna','cocina','oficina'):
        cocina=tipo=='cocina'
        for i in range(28):m.caja((-7+i*.5,-.12,-4),(.485,.2,21),'#98592E' if cocina else '#684331')
        m.caja((0,3,-12),(14,6,.35),'#B86E32' if cocina else '#51304E')
        m.caja((-7,3,-3),(.3,6,18),'#714130' if cocina else '#3B2949')
        m.caja((7,3,-3),(.3,6,18),'#714130' if cocina else '#3B2949')
        for x in (-6.7,0,6.7):m.caja((x,3,-11.7),(.26,6,.3),'#C08A4B')
        for yy in (.5,2.5,5):m.caja((0,yy,-11.7),(14,.17,.3),'#9B653E')
        if cocina:
            # Ojo de buey real, aro y vidrio, cocina con fogones y batería.
            m.barra((0,3.6,-11.7),(0,3.6,-11.45),1.1,'#C7A654',20)
            m.barra((0,3.6,-11.43),(0,3.6,-11.40),.84,'#3A84A8',20)
            m.caja((-4,1.1,-8),(3.2,2.2,1.5),'#383747')
            for x in (-4.8,-3.2):
                m.barra((x,2.2,-8),(x,2.25,-8),.5,'#181E2A',16)
                m.barra((x,2.26,-8),(x,2.9,-8),.4,'#B7B9BD',16)
            if not o.get('blender'):mesa(m,1.5,1.35,-5,3,1.5)
            for x in (-5,-3,3,5):barril(m,x,0,-10)
            # Sopa y lata; líquido no se representa como imagen pegada.
            if not o.get('blender'):cuenco(m,1.8,1.45,-5,t)
            m.caja((-1.2,1.85,-5),(.45,.85,.4),'#C8C5AC')
            m.caja((-1.2,1.9,-4.79),(.38,.35,.02),'#467B72')
        else:
            # Barra, estantes, botellas, taburetes, mesa de actuación.
            m.caja((1.5,1.1,-8),(8,2.2,1.2),'#814332')
            m.caja((1.5,2.25,-8),(8.4,.2,1.5),'#BC8651')
            for yy in (2.6,3.8,5):
                m.caja((2,yy,-11.3),(7,.12,.6),'#9E633C')
                for i in range(8):m.barra((-1+i*.85,yy+.06,-11.1),(-1+i*.85,yy+.6,-11.1),.12,
                        ['#3C8D78','#B87736','#664A89'][i%3],8)
            mesa(m,-1,1.3,-2,2.5,1.5);silla(m,-2.8,0,-2.5);silla(m,.7,0,-2.5)
            for x in (-1,1,3,5):silla(m,x,0,-6.3)
        for x in (-4,4):
            m.barra((x,5.7,-5),(x,4.7,-5),.035,'#302B3A')
            m.esfera((x,4.5,-5),(.33,.38,.33),'#FFD385',em=1)
        amb.update(cielo=(.10,.065,.16),sol=(.1,1,.4),lampara=(-2,4.5,-3),potencia=2.5,niebla=.009)
        cam.update(eye=(2,2.9,5.5),target=(0,1.9,-3.5),fov=49)
        if cocina:cam.update(eye=(4.4,3.1,1.3),target=(.4,2,-6.5),fov=48)
    elif tipo=='mar':
        oceano(m,t,o.get('calma',0),o.get('ola',1),espuma=o.get('blender',False))
        barco(m,t,-1,-6);barco(m,t+1.5,7,-19)
        for i in range(9):m.esfera((-14+i*4,9+(i%3),-25), (4,1.8,3),'#26385B')
        amb.update(cielo=(.035,.075,.19),sol=(-.2,1,.4),niebla=.017)
        cam.update(eye=(8,4.8,7),target=(0,2,-9),fov=55,apertura=.15)
    elif tipo in ('canon','puente'):
        m.caja((0,-9,-14),(100,1,110),'#623E67')
        if not o.get('blender'):
            for side in (-1,1):
                pared_canon(m,side,distancia=8.4 if tipo=='canon' else 30,
                    altura=25 if tipo=='canon' else 18,seed=3 if side<0 else 9)
        if tipo=='canon':
            m.material=5;m.caja((0,-.2,-20),(22,.4,95),'#C88B57');m.material=0
            vias(m,t,torcido=o.get('torcido',0),hueco=o.get('hueco',.08))
            vias(m,t,x=3.1,torcido=0)
        else:
            for zz in (11,-30):
                m.material=2
                m.caja((0,-4.5,zz),(5,9,1.7),'#AD795E')
                m.caja((0,-.3,zz),(5.6,.5,2.3),'#DBAA75')
                m.material=0
            for i in range(49):m.caja((0,-.07,10-i*.8),(4,.22,.76),'#A97560')
            vias(m,t,inicio=10,fin=-28,torcido=o.get('torcido',0))
            for side in (-1,1):
                x=side*2
                m.barra((x,.6,10),(x,.6,-29),.065,'#AE875F')
                m.barra((x,-1,10),(x,-1,-29),.13,'#62494C')
                for i in range(10):
                    z=9-i*4
                    m.barra((x,-7,z),(x,.65,z),.09,'#8F5D46')
                    m.barra((x,-4,z),(x,-1,z-4),.08,'#A8754E')
                    m.barra((x,-1,z),(x,-4,z-4),.08,'#A8754E')
                # Arco bajo el tablero y montantes, geometría espacial real.
                for i in range(24):
                    z0=-29+39*i/24;z1=-29+39*(i+1)/24
                    y0=-7+6*math.sin(math.pi*i/24);y1=-7+6*math.sin(math.pi*(i+1)/24)
                    m.barra((x,y0,z0),(x,y1,z1),.16,'#9C7057')
                    if i%3==0:m.barra((x,y0,z0),(x,-.2,z0),.065,'#B78A60')
            # Entretoises transversales: les deux fermes forment une structure spatiale.
            m.material=3
            for i in range(10):
                zz=9-i*4
                m.barra((-2,-1,zz),(2,-1,zz),.11,'#77717B',8)
                m.barra((-2,-1,zz),(2,-1,zz-4),.065,'#A38770',6)
                m.barra((2,-1,zz),(-2,-1,zz-4),.065,'#A38770',6)
            m.material=0
            amb.update(cielo=(.20,.43,.76),sol=(.85,.6,.25),niebla=.007)
        if tipo=='canon':amb.update(sol=(.7,.8,.35),niebla=.004)
        if o.get('tren',True) and not o.get('blender'):tren(m,0,.25,-14+t*1.7)
        cam.update(eye=(5,3.5,10),target=(0,1,-7),fov=53)
    else:
        raise ValueError('Escenario 3D no disponible: '+str(tipo))
    detalle(m,tipo,t,o)
    return m,cam,amb


_cache={}


def escena(tipo,t,opciones=None):
    """Instancia de escenario; copia de vértices antes de añadir acción libre.

    Solo se cachea arquitectura estática. Agua, vías deformables, barco y tren
    conservan su reloj continuo. No se guarda ninguna caché en paquetes publicados.
    """
    opciones=dict(opciones or {})
    nativo=getattr(Renderer,'backend',None)=='blender'
    if nativo:opciones['blender']=True
    if tipo in ('oeste','desierto','taberna','cocina','oficina'):
        key=(tipo,repr(sorted((opciones or {}).items())))
        if key not in _cache:
            if len(_cache)>12:_cache.clear()
            _cache[key]=_construir(tipo,0,opciones)
        base,cam,amb=_cache[key];m=Malla();m.vertices=list(base.vertices)
        cam,amb=dict(cam),dict(amb)
    else:m,cam,amb=_construir(tipo,t,opciones)
    if nativo:
        extras=dict(t=t)
        if tipo in ('canon','puente'):
            extras.update(paredes=dict(distancia=8.4 if tipo=='canon' else 30,altura=25 if tipo=='canon' else 18),
                tren=opciones.get('tren',True))
        if tipo=='cocina':extras.update(cocina=True,ollas=[])
        amb['blender']=extras
    return m,cam,amb
