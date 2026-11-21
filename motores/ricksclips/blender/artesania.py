"""Recursos bpy originales y parametrizables. No utiliza imágenes de referencia.

Funciones independientes de los planos de prueba. Y arriba en sus argumentos.
La locomotora se anima por distancia recorrida; vapor es volumen procedural,
no una simulación física. El contacto se resuelve en coordenadas de mundo.
"""
import bpy
import math
import random
from mathutils import Vector,Matrix


def xyz(v): return Vector((v[0],-v[2],v[1]))


def mate(nombre,color,metal=0,rug=.5):
    m=bpy.data.materials.new(nombre);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    c=tuple(((v+.055)/1.055)**2.4 if v>.04045 else v/12.92 for v in color)
    p.inputs['Base Color'].default_value=(*c,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rug
    return m


def caja(nombre,pos,size,mat,bisel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(pos));o=bpy.context.object;o.name=nombre
    o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bisel:
        mod=o.modifiers.new('cantos_construidos','BEVEL');mod.width=bisel;mod.segments=3
        mod=o.modifiers.new('normales','WEIGHTED_NORMAL')
    return o


def barra(nombre,a,b,r,mat,lados=32):
    a,b=xyz(a),xyz(b);d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=lados,radius=r,depth=d.length,location=(a+b)/2)
    o=bpy.context.object;o.name=nombre;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    mod=o.modifiers.new('borde_mecanizado','BEVEL');mod.width=min(.012,r*.1);mod.segments=2
    o.modifiers.new('normales','WEIGHTED_NORMAL')
    return o


def torno(nombre,pos,perfil,mat,n=64):
    verts=[];faces=[]
    for r,h in perfil:
        for j in range(n):
            a=j*math.tau/n;verts.append(xyz((pos[0]+r*math.cos(a),pos[1]+h,pos[2]+r*math.sin(a))))
    for i in range(len(perfil)-1):
        for j in range(n):
            k=i*n+j;l=i*n+(j+1)%n;faces.append((k,k+n,l+n,l))
    me=bpy.data.meshes.new(nombre);me.from_pydata(verts,[],faces);me.materials.append(mat)
    for p in me.polygons:p.use_smooth=True
    o=bpy.data.objects.new(nombre,me);bpy.context.collection.objects.link(o);return o


def curva(nombre,puntos,radio,mat):
    cu=bpy.data.curves.new(nombre,'CURVE');cu.dimensions='3D';cu.bevel_depth=radio;cu.bevel_resolution=3
    sp=cu.splines.new('POLY');sp.points.add(len(puntos)-1)
    for p,v in zip(sp.points,puntos):p.co=(*xyz(v),1)
    ob=bpy.data.objects.new(nombre,cu);bpy.context.collection.objects.link(ob);cu.materials.append(mat);return ob


def arenisca():
    m=mate('arenisca_erosionada',(.86,.37,.16),rug=.86)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    coord=n.new('ShaderNodeTexCoord');sep=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Generated'],sep.inputs[0])
    ramp=n.new('ShaderNodeValToRGB')
    r=ramp.color_ramp;r.elements.remove(r.elements[1])
    for i,(pos,col) in enumerate([(0,(.25,.045,.028,1)),(.22,(.46,.09,.035,1)),(.38,(.7,.20,.065,1)),(.47,(.47,.07,.025,1)),(.63,(.74,.26,.095,1)),(.78,(.88,.38,.16,1)),(1,(.54,.16,.06,1))]):
        e=r.elements[0] if i==0 else r.elements.new(pos)
        # Las tintas de dirección son sRGB; la rampa de Blender espera lineal.
        e.color=(*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in col[:3]),1)
    l.new(sep.outputs['Z'],ramp.inputs[0]);l.new(ramp.outputs[0],p.inputs['Base Color'])
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.5;noise.inputs['Detail'].default_value=3.5
    l.new(coord.outputs['Object'],noise.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.24;bump.inputs['Distance'].default_value=.09
    l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    return m


def pared(lado=1,distancia=8.4,altura=25,inicio=18,fin=-65,seed=9):
    """Pared continua con erosión correlacionada, cornisas y fracturas métricas."""
    from mathutils.noise import noise_vector
    verts=[];faces=[];nz=280;ny=110
    for i in range(nz+1):
        z=inicio+(fin-inicio)*i/nz
        for j in range(ny+1):
            u=j/ny;y=-9+u*(altura+2.2*math.sin(z*.19+seed)+math.sin(z*.53))
            broad=1.5*math.sin(z*.25+seed)+.7*math.sin(z*.61+seed)
            warp=noise_vector(Vector((z*.12,y*.07,seed)))[0]
            groove=max(0,math.cos(z*.93+seed+u*.8+warp))**16
            n=noise_vector(Vector((z*.8,y*.55,seed)))[0]
            erosion=noise_vector(Vector((z*.31,y*.64,seed+4)))[0]
            breakup=max(0,noise_vector(Vector((z*.25,y*.09,seed+2)))[0]+.2)
            ledge=(.10*math.sin(y*1.8+warp)+.055*math.sin(y*5.7+z*.3))*breakup
            x=distancia+2.6*u+broad*(.5+.5*u)+groove*(.4+u*.8)+n*.20+erosion*.48+ledge
            x-=1.4*math.exp(-u*12)
            verts.append(xyz((lado*x,y,z)))
    for i in range(nz):
        for j in range(ny):
            k=i*(ny+1)+j;quad=(k,k+ny+1,k+ny+2,k+1)
            faces.append(quad if lado<0 else quad[::-1])
    # Cierra cresta, trasdós, base y extremos. Una superficie abierta mostraba
    # pequeños reversos oscuros al mirar la cresta desde el plano vertical.
    back=[];foot=[]
    for i in range(nz+1):
        top=verts[i*(ny+1)+ny];bottom=verts[i*(ny+1)]
        back.append(len(verts));verts.append(Vector((top.x+lado*4,top.y,top.z-.8)))
        foot.append(len(verts));verts.append(Vector((top.x+lado*4,top.y,bottom.z)))
    def cara(ids):faces.append(ids if lado<0 else tuple(reversed(ids)))
    for i in range(nz):
        a=i*(ny+1);b=(i+1)*(ny+1)
        cara((a+ny,b+ny,back[i+1],back[i]))
        cara((back[i],back[i+1],foot[i+1],foot[i]))
        cara((a,foot[i],foot[i+1],b))
    cara((0,ny,back[0],foot[0]))
    end=nz*(ny+1);cara((end,foot[-1],back[-1],end+ny))
    me=bpy.data.meshes.new('macizo_continuo');me.from_pydata(verts,[],faces);me.materials.append(arenisca())
    for p in me.polygons:p.use_smooth=True
    ob=bpy.data.objects.new('pared_erosionada',me);bpy.context.collection.objects.link(ob);return ob


class Locomotora:
    """Modelo separado del plano, ruedas/bielas ligadas a distancia sin patinar."""
    def __init__(self,x=0,y=.195,z=-14,escala=1):
        self.origen=(x,y,z);self.ruedas=[];self.bielas=[];self.principales=[];self.correderas=[]
        before=set(bpy.data.objects)
        green=mate('esmalte_verde',(.13,.35,.29),.55,.27)
        dark=mate('hierro_azulado',(.09,.13,.18),.72,.36)
        brass=mate('laton',(.68,.48,.22),.75,.25)
        steel=mate('acero_mecanismos',(.58,.61,.64),.82,.22)
        wood=mate('piso_cabina',(.32,.16,.08),0,.65)
        caja('bastidor',(0,.65,0),(1.28,.26,3.8),dark,.045)
        barra('caldera',(0,1.2,.42),(0,1.2,-1.35),.52,green,64)
        barra('caja_humos',(0,1.2,-1.3),(0,1.2,-1.55),.53,dark)
        barra('aro_latón',(0,1.2,-1.555),(0,1.2,-1.58),.475,brass)
        barra('puerta_humos',(0,1.2,-1.58),(0,1.2,-1.61),.425,dark)
        barra('cierre_humos',(-.13,1.2,-1.63),(.13,1.2,-1.63),.022,steel)
        for zz in (-1.05,-.5,.05,.48):
            pts=[(.532*math.cos(j*math.tau/80),1.2+.532*math.sin(j*math.tau/80),zz) for j in range(81)]
            curva('cincha_caldera',pts,.016,brass)
        for zz in (-.45,.12):torno('domo_vapor',(0,1.61,zz),[(.19,0),(.22,.08),(.20,.25),(.14,.30),(0,.32)],brass)
        torno('chimenea',(0,1.6,-.94),[(.16,0),(.13,.16),(.17,.62),(.23,.68),(.23,.73),(.15,.73),(.11,.20)],dark)
        caja('suelo_cabina',(0,.91,1.03),(1.35,.12,1.46),wood)
        caja('mamparo_frontal',(0,1.40,.34),(1.27,1.01,.09),green,.025)
        caja('hogar',(0,1.19,.45),(.64,.54,.17),dark,.045)
        barra('puerta_hogar',(0,1.18,.55),(0,1.18,.58),.20,brass)
        barra('registro_hogar',(0,1.18,.585),(0,1.18,.60),.15,dark)
        barra('maneta_hogar',(-.08,1.18,.62),(.08,1.18,.62),.017,steel)
        for xx in (-.40,.40):
            barra('manometro',(xx,1.73,.40),(xx,1.73,.45),.09,brass)
            barra('esfera_manometro',(xx,1.73,.455),(xx,1.73,.46),.072,steel)
            barra('aguja_manometro',(xx,1.73,.47),(xx+.03,1.78,.47),.007,dark,8)
        for side in (-1,1):
            sx=side*.66
            caja('panel_cabina',(sx,1.16,1.03),(.07,.48,1.45),green)
            for zz in (.35,1.69):caja('montante',(sx,1.78,zz),(.075,.84,.075),brass)
            caja('dintel',(sx,2.17,1.02),(.09,.12,1.52),green)
            caja('antepecho',(sx,1.43,1.02),(.09,.07,1.52),brass)
            for zz in (.4,1.65):barra('pasamanos',(sx+side*.08,.95,zz),(sx+side*.08,1.45,zz),.022,brass)
            for yy in (.49,.70):caja('estribo',(sx+side*.09,yy,1.50),(.35,.06,.40),dark)
            barra('tuberia_lateral',(sx,1.48,-1.2),(sx,1.48,.3),.025,brass)
            barra('cilindro_piston',(sx,.86,-1.18),(sx,.86,-.65),.13,dark)
            caja('guia_corredera',(side*.86,.86,-.68),(.055,.10,.72),dark,.01)
            for zz in (.37,1.65):
                for yy in (1.05,1.21):barra('remache_cabina',(sx,yy,zz),(sx+side*.025,yy,zz),.014,brass,12)
        # Techo abovedado continuo con espesor, abierto detrás.
        verts=[];faces=[]
        for zz in (.17,1.86):
            for j in range(33):
                ang=-math.pi/2+j*math.pi/32;verts.append(xyz((.82*math.sin(ang),2.18+.21*math.cos(ang),zz)))
        for j in range(32):faces.append((j,j+33,j+34,j+1))
        me=bpy.data.meshes.new('techo_curvado');me.from_pydata(verts,[],faces);me.materials.append(dark)
        roof=bpy.data.objects.new('techo',me);bpy.context.collection.objects.link(roof)
        roof.modifiers.new('chapa','SOLIDIFY').thickness=.035
        barra('frente_tope',(-.61,.69,-1.8),(.61,.69,-1.8),.065,brass)
        for xx in (-.46,.46):barra('amortiguador',(xx,.65,-1.8),(xx,.65,-2.02),.12,dark)
        for j in range(11):
            xx=(j-5)*.105;barra('rastrillo',(xx,.70,-1.72),(xx,.30,-2.12+abs(xx)*.3),.022,brass,12)
        for side in (-1,1):
            for zz in (-1.05,0,1.05):
                bpy.ops.object.empty_add(location=xyz((side*.73,.51,zz)))
                pivot=bpy.context.object;pivot.name='eje_rueda';self.ruedas.append(pivot)
                first=set(bpy.data.objects)
                barra('llanta',(side*.70,.51,zz),(side*.80,.51,zz),.36,dark,48)
                barra('cubo',(side*.69,.51,zz),(side*.83,.51,zz),.09,brass)
                barra('manivela',(side*.83,.51,zz),(side*.83,.73,zz),.035,steel,16)
                barra('bulon_manivela',(side*.82,.73,zz),(side*.89,.73,zz),.052,brass,16)
                for j in range(10):
                    ang=j*math.tau/10;barra('radio',(side*.81,.51,zz),(side*.81,.51+.31*math.cos(ang),zz+.31*math.sin(ang)),.023,brass,12)
                for ob in set(bpy.data.objects)-first:
                    ob.parent=pivot;ob.matrix_parent_inverse=pivot.matrix_world.inverted()
            # La biela une las tres manivelas con la misma fase.
            rod=barra('biela_acoplamiento',(side*.85,.51,-1.05),(side*.85,.51,1.05),.04,steel)
            self.bielas.append(rod)
            main=barra('biela_motriz',(side*.90,.51,0),(side*.90,.86,-.8),.035,steel)
            self.principales.append((side,main,.85))
            slide=caja('cruceta',(side*.90,.86,-.8),(.10,.12,.15),steel,.015)
            self.correderas.append(slide)
        # Pernos de la caja de humos: dimensión pequeña, no manchas pintadas.
        for j in range(16):
            ang=j*math.tau/16;xx=.445*math.cos(ang);yy=1.2+.445*math.sin(ang)
            barra('perno_humos',(xx,yy,-1.60),(xx,yy,-1.63),.018,brass,12)
        lamp=mate('faro',(.98,.81,.43),.3,.2)
        lp=lamp.node_tree.nodes.get('Principled BSDF');lp.inputs['Emission Color'].default_value=(1,.65,.2,1);lp.inputs['Emission Strength'].default_value=3
        barra('faro_carcasa',(0,1.67,-1.45),(0,1.67,-1.66),.17,dark)
        barra('faro_lente',(0,1.67,-1.665),(0,1.67,-1.68),.13,lamp)
        self.objetos=set(bpy.data.objects)-before
        bpy.ops.object.empty_add();self.raiz=bpy.context.object;self.raiz.name='locomotora_parametrizable'
        for ob in self.objetos:
            if ob.parent is None:ob.parent=self.raiz
        self.raiz.scale=(escala,)*3
        self.vapor=[]
        steam=bpy.data.materials.new('vapor_volumetrico');steam.use_nodes=True
        nodes=steam.node_tree.nodes;links=steam.node_tree.links;nodes.clear()
        out=nodes.new('ShaderNodeOutputMaterial');vol=nodes.new('ShaderNodeVolumePrincipled')
        vol.inputs['Color'].default_value=(.53,.60,.72,1)
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3;noise.inputs['Detail'].default_value=2
        mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=1.25
        links.new(noise.outputs['Fac'],mul.inputs[0]);links.new(mul.outputs[0],vol.inputs['Density']);links.new(vol.outputs[0],out.inputs['Volume'])
        for i in range(8):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
            ob=bpy.context.object;ob.name='vapor_procedural';ob.data.materials.append(steam);self.vapor.append(ob)
        self.actualizar(0)

    def actualizar(self,t,velocidad=1.7):
        x,y,z=self.origen;self.raiz.location=xyz((x,y,z+t*velocidad))
        # +Z del intercambio es -Y en Blender: omega +X evita deslizar
        # el punto inferior de la rueda durante ese recorrido (marcha atrás).
        phase=t*velocidad/.36
        for pivot in self.ruedas:pivot.rotation_euler.x=phase
        for rod in self.bielas:
            # Desplazamiento circular idéntico en los tres apoyos.
            rod.location.z=.51+.22*math.cos(phase)
            rod.location.y=-.22*math.sin(phase)
        for index,(side,rod,length) in enumerate(self.principales):
            cy=.51+.22*math.cos(phase);cz=.22*math.sin(phase)
            pz=cz-math.sqrt(max(.001,length*length-(.86-cy)**2))
            start=xyz((side*.90,cy,cz));end=xyz((side*.90,.86,pz));delta=end-start
            rod.location=(start+end)/2;rod.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
            # El cilindro original de barra conserva su longitud inicial.
            rod.scale.z=delta.length/math.sqrt(.35**2+.8**2)
            self.correderas[index].location=xyz((side*.90,.86,pz))
        for i,ob in enumerate(self.vapor):
            age=(t+i*.23)%1.84
            ob.location=xyz((x+.12*math.sin(i*4+age),y+2.35+age*1.0,z+t*velocidad-.94+age*.8))
            r=.12+age*.23;ob.scale=(r,r*1.2,r*.85)


class Olla:
    def __init__(self,piel='#FFF0DB'):
        copper=mate('cobre_olla',(.65,.27,.10),.72,.3);handle=mate('asa_madera',(.18,.09,.055),0,.52)
        before=set(bpy.data.objects)
        torno('olla_hueca',(0,0,0),[(0,0),(.25,0),(.30,.06),(.31,.43),(.32,.46),(.29,.48),(.275,.44),(.27,.08),(0,.06)],copper)
        curva('asa_cerrada',[(-.29,.30,0),(-.46,.33,0),(-.59,.27,0),(-.59,.16,0),(-.46,.11,0),(-.29,.16,0)],.032,handle)
        skin=mate('piel_dedos_agarre',tuple(int(piel[j:j+2],16)/255 for j in (1,3,5)),0,.8)
        for yy in (.21,.235,.26):
            points=[]
            for j in range(13):
                angle=-1.2+2.4*j/12
                points.append((-.59+.04*math.sin(angle),yy,.04*math.cos(angle)))
            curva('dedo_sobre_asa',points,.010,skin)
        barra('pulgar_agarre',(-.555,.20,.018),(-.555,.255,.025),.014,skin,16)
        self.objetos=set(bpy.data.objects)-before
        bpy.ops.object.empty_add();self.raiz=bpy.context.object;self.raiz.name='olla_constraint'
        for o in self.objetos:o.parent=self.raiz
        self.agarre=xyz((-.59,.23,0));self.borde=xyz((.30,.46,0))
        bpy.context.view_layer.update()
        self.limites=[Vector(v) for ob in self.objetos for v in ob.bound_box]
        self.chorro=None
        self.aceite=mate('aceite',(.95,.63,.11),.05,.18)

    def actualizar(self,mano,t,destino=(1.8,1.66,-5),altura_mesa=1.43):
        # Giro respecto al asa real: su punto permanece en la mano tras IK.
        pedido=-.65*max(0,min(1,(t-.45)/.65))*max(0,min(1,(2.15-t)/.45))
        hand=xyz(mano);clearance=altura_mesa+.02
        def minimo(angle):
            rot=Matrix.Rotation(-angle,3,'Y')
            return hand.z+min((rot@(v-self.agarre)).z for v in self.limites)
        angle=pedido
        if minimo(angle)<clearance:
            # Constraint unilateral contra el plano superior real. No desplaza
            # la mano ni modifica el reloj: limita el giro alcanzable del objeto.
            if minimo(0)<clearance:
                raise ValueError('El agarre resuelto no permite apoyar la olla sin penetrar la mesa')
            lo,hi=0,abs(pedido)
            for _ in range(24):
                mid=(lo+hi)/2
                if minimo(-mid)>=clearance:lo=mid
                else:hi=mid
            angle=-lo
        self.raiz.rotation_euler.y=-angle
        rot=self.raiz.rotation_euler.to_matrix();self.raiz.location=xyz(mano)-rot@self.agarre
        origen=self.raiz.location+rot@self.borde
        if self.chorro:
            cu=self.chorro.data;bpy.data.objects.remove(self.chorro,do_unlink=True);bpy.data.curves.remove(cu);self.chorro=None
        if angle<-.35:
            end=xyz(destino);pts=[]
            for j in range(25):
                u=j/24;p=origen.lerp(end,u);p.z+=(end.z-origen.z)*(-u*(1-u))
                pts.append((p.x,p.z,-p.y))
            self.chorro=curva('vertido_procedural',pts,.012,self.aceite)
        return dict(error_agarre_m=(self.raiz.location+rot@self.agarre-xyz(mano)).length,
            angulo=angle,angulo_solicitado=pedido,ajustado_por_mesa=abs(angle-pedido)>1e-6,
            cota_minima_constraint=minimo(angle),chorro=self.chorro is not None)


def armario_cocina(x=1.5,z=-5,ancho=3):
    """Carpintería de trabajo con encastres y tiradores, independiente de cámara."""
    wood=mate('roble_encerado',(.48,.24,.10),0,.43)
    panel=mate('panel_ocre',(.62,.32,.14),0,.5)
    dark=mate('uniones_armario',(.17,.075,.035),0,.68)
    brass=mate('herrajes_cocina',(.72,.48,.19),.7,.28)
    caja('cuerpo_armario',(x,.66,z),(ancho,1.25,1.42),wood,.035)
    for i in range(3):
        xx=x-ancho/2+(i+.5)*ancho/3
        caja('junta_puerta',(xx,.57,z+.725),(ancho/3-.035,1.04,.045),dark,.008)
        caja('bastidor_puerta',(xx,.57,z+.758),(ancho/3-.07,1.0,.055),wood,.012)
        caja('panel_hundido',(xx,.57,z+.793),(ancho/3-.24,.78,.018),panel,.008)
        barra('tirador',(xx-.18,1.0,z+.84),(xx+.18,1.0,z+.84),.023,brass,24)
        for dx in (-.18,.18):barra('soporte_tirador',(xx+dx,1,z+.79),(xx+dx,1,z+.84),.017,brass,16)
    caja('zócalo',(x,.10,z+.73),(ancho+.02,.15,.07),dark)


def encimera_y_cuenco(x=1.0,z=-5,ancho=3.8,cuenco_x=1.65):
    wood=mate('encimera_trabajo',(.69,.42,.21),0,.51)
    for j in range(9):
        caja('tabla_encimera',(x-ancho/2+(j+.5)*ancho/9,1.365,z),(ancho/9-.012,.15,1.53),wood,.012)
    ceramic=mate('ceramica_cuenco',(.89,.80,.64),0,.29)
    torno('cuenco_hueco',(cuenco_x,1.44,-5),[(0,0),(.20,0),(.28,.08),(.36,.24),(.365,.27),(.335,.275),(.25,.09),(0,.06)],ceramic)
    soup=mate('sopa',(.88,.53,.10),0,.28)
    torno('liquido_recepcion',(cuenco_x,1.44,-5),[(.315,.21),(0,.21)],soup)
