"""Apariencias declarativas; código compartido, no un renderer por identidad.

El adaptador humano corresponde al contrato del rig recuperado, no a cualquier
estilo. Otros rigs optan explícitamente por apariencia/1 e implementan su dibujo.
Este fichero se congela como dependencia de cada personaje, igual que su base.
"""
import copy
import math


ESQUEMA = {
    'pelo': ['corto', 'largo', 'coleta', 'trenzas', 'rizado', 'calvo'],
    'ropa': ['sudadera', 'camiseta', 'camisa', 'chaqueta', 'vestido'],
    'barba': ['ninguna', 'corta', 'larga'],
    'gafas': 'booleano', 'pecas': 'booleano', 'movil': 'booleano',
    'altura': 'factor 0.65..1.35', 'cuerpo': 'anchura 0.65..1.5',
    'cabeza': 'factor 0.75..1.3', 'edad': 'años 5..100',
    'colores': {k: '#RRGGBB' for k in ('piel', 'pelo', 'ropa', 'pantalon', 'zapatos', 'acento')},
}
DEFECTO = dict(pelo='corto', ropa='camiseta', barba='ninguna', gafas=False,
    pecas=False, movil=False, altura=1., cuerpo=1., cabeza=1., edad=28,
    colores=dict(piel='#f6e5d8', pelo='#62422e', ropa='#828791',
        pantalon='#262c44', zapatos='#f6f8fc', acento='#e8eaf0'))


def validar(datos):
    if not isinstance(datos,dict) or set(datos)-set(ESQUEMA):
        raise ValueError('apariencia: campos desconocidos; usar codigo_extra para geometría excepcional')
    salida = copy.deepcopy(DEFECTO)
    for clave,valor in datos.items():
        if clave == 'colores':
            if not isinstance(valor,dict) or set(valor)-set(DEFECTO['colores']):
                raise ValueError('apariencia: colores no válidos')
            for nombre,color in valor.items():
                if (not isinstance(color,str) or len(color)!=7 or color[0]!='#'
                        or any(c not in '0123456789abcdefABCDEF' for c in color[1:])):
                    raise ValueError('apariencia: el color debe ser #RRGGBB')
                salida['colores'][nombre] = color
        elif isinstance(ESQUEMA[clave],list):
            if valor not in ESQUEMA[clave]:
                raise ValueError('apariencia: opción no válida: '+clave)
            salida[clave] = valor
        elif clave in ('gafas','pecas','movil'):
            if type(valor) is not bool:
                raise ValueError('apariencia: se requiere booleano: '+clave)
            salida[clave] = valor
        else:
            limites = dict(altura=(.65,1.35),cuerpo=(.65,1.5),cabeza=(.75,1.3),edad=(5,100))
            minimo,maximo = limites[clave]
            if type(valor) not in (int,float) or not minimo<=valor<=maximo:
                raise ValueError('apariencia: proporción o edad fuera de rango: '+clave)
            salida[clave] = valor
    return salida


def _rgb(hexadecimal):
    return tuple(int(hexadecimal[i:i+2],16) for i in (1,3,5))


def _tono(color,factor):
    return tuple(max(0,min(255,round(c*factor))) for c in color)


def crear(base,soporte,apariencia,perfil='humano_v1',extensiones=None):
    datos = validar(apariencia)
    rig = soporte.crear(base)
    if perfil == 'nativo_v1':
        if getattr(rig,'APARIENCIA_VERSION',None)!=1:
            raise ValueError('el rig no declara el contrato apariencia/1')
        rig.aplicar_apariencia(copy.deepcopy(datos))
    elif perfil == 'humano_v1':
        _configurar_humano(rig,datos)
    else:
        raise ValueError('perfil de apariencia no compatible')
    rig.dibujo_compartido = rig.dibujar
    # Las excepciones siguen siendo funciones libres. No reconstruir el motor.
    from functools import partial
    for nombre,funcion in (extensiones or {}).items():
        if not isinstance(nombre,str) or not nombre.isidentifier() or not callable(funcion):
            raise ValueError('extensión de apariencia no válida')
        setattr(rig,nombre,partial(funcion,rig))
    rig.apariencia = copy.deepcopy(datos)
    return rig


def _configurar_humano(rig,a):
    pal = rig.PAL
    grupos = dict(piel=('piel','piel_s'),pelo=('pelo','pelo_s','pelo_l','ceja'),
        ropa=('sud','sud_s','sud_l'),pantalon=('jean','jean_s','jean_l'),
        zapatos=('zap','zap_s','suela'),acento=('cuerda','cord'))
    for color,slots in grupos.items():
        rgb = _rgb(a['colores'][color])
        for slot in slots:
            pal[slot] = _tono(rgb,.8 if slot.endswith('_s') else 1.16 if slot.endswith('_l') else 1.)
    original_estado = rig.estado_base
    original_fk = rig._fk
    original_dibujar = rig.dibujar

    def estado_base():
        return dict(original_estado(),movil_visible=a['movil'],movil_mano='d' if a['movil'] else None,
            brazo_d=7.,codo_d=14.,sonrisa=.1,ceja_i_incl=0.,ceja_d_incl=0.)

    def fk(*args,**kwargs):
        resultado = original_fk(*args,**kwargs)
        # Anchura local sobre las mismas articulaciones, sin otra cinemática.
        centro = resultado['pel'][0]
        factor = a['cuerpo']
        def punto(p): return (centro+(p[0]-centro)*factor,p[1])
        for clave in ('pel','C','Hc','Nb','Sd','Si','Pc'):
            resultado[clave] = punto(resultado[clave])
        for lado in (-1,1):
            for clave in ('S','E','W','Hm'):
                resultado['arm'][lado][clave] = punto(resultado['arm'][lado][clave])
            for clave in ('H','K','A'):
                resultado['leg'][lado][clave] = punto(resultado['leg'][lado][clave])
        resultado['R'] *= a['cabeza']
        resultado['pts'] = [punto(p) for p in resultado['pts']]
        return resultado

    def dibujar(lienzo,estado,contexto):
        e = dict(estado or {})
        altura = e.get('altura')
        e['altura'] = (lienzo.height*.62 if altura is None else float(altura))*a['altura']
        return original_dibujar(lienzo,e,contexto)

    rig.estado_base = estado_base
    rig._fk = fk
    rig.dibujar = dibujar
    rig._cabeza = lambda P,e,f: _cabeza(rig,a,P,e,f)
    rig._torso = lambda P,e,f: _torso(rig,a,P,e,f)
    rig._brazo = lambda P,e,f,lado: _brazo(rig,a,P,e,f,lado)


def _brazo(rig,a,P,e,fk,lado):
    if a['ropa'] not in ('camiseta','vestido'):
        return rig.originales['_brazo'](P,e,fk,lado)
    u,pal = fk['u'],rig.PAL
    brazo = fk['arm'][lado]
    S,E,W = brazo['S'],brazo['E'],brazo['W']
    P.chain([S,E,W],[.27*u,.23*u,.19*u],pal['piel'])
    borde = ((S[0]+E[0])/2,(S[1]+E[1])/2)
    P.chain([S,borde],[.3*u,.28*u],pal['sud'])
    # El helper de manos tiene un puño: en manga corta debe ser piel.
    anterior = pal['sud_s']
    try:
        pal['sud_s'] = pal['piel']
        rig._mano(P,e,fk,lado)
    finally:
        pal['sud_s'] = anterior


def _torso(rig,a,P,e,fk):
    if a['ropa']=='sudadera':
        return rig.originales['_torso'](P,e,fk)
    u,pal = fk['u'],rig.PAL
    centro,pel,ex,ld = fk['C'],fk['pel'],fk['ex'],fk['Ld']
    def T(x,y):
        return (centro[0]+(ex[0]*x-ld[0]*y)*u,centro[1]+(ex[1]*x-ld[1]*y)*u)
    izq,der = fk['Si'],fk['Sd']
    largo = 1.65 if a['ropa']=='vestido' else .3
    ancho = (1.05 if a['ropa']=='vestido' else .72)*a['cuerpo']
    bi = (pel[0]-ex[0]*ancho*u-ld[0]*largo*u,pel[1]-ex[1]*ancho*u-ld[1]*largo*u)
    bd = (pel[0]+ex[0]*ancho*u-ld[0]*largo*u,pel[1]+ex[1]*ancho*u-ld[1]*largo*u)
    P.hull([der,bd,bi,izq],[.35*u]*4,pal['sud'])
    P.stroke([T(-.63,.2),T(-.6,1.8)],.08*u,pal['sud_l'])
    P.stroke([T(.63,.3),T(.63,1.8)],.07*u,pal['sud_s'])
    P.chain([fk['Nb'],rig._hq(fk)(0,.8)],[.24*u]*2,pal['piel_s'])
    P.stroke([T(-.4,0),T(0,.3),T(.4,0)],.09*u,pal['sud_s'])
    if a['ropa'] in ('camisa','chaqueta'):
        P.poly([T(-.5,-.1),T(0,.55),T(-.1,-.05)],pal['sud_l'])
        P.poly([T(.5,-.1),T(0,.55),T(.1,-.05)],pal['sud_l'])
        P.stroke([T(0,.5),T(0,2.)],.045*u,pal['sud_s'])
        for y in (.7,1.1,1.5,1.9):
            P.circ(T(.06,y),.045*u,pal['cuerda'])
    if a['ropa']=='chaqueta':
        for lado in (-1,1):
            P.stroke([T(lado*.2,1.35),T(lado*.55,1.35)],.055*u,pal['sud_l'])


def _cabeza(rig,a,P,e,fk):
    R,rho,pal = fk['R'],fk['rho'],rig.PAL
    hq = rig._hq(fk)
    g = max(-1.,min(1.,rig._n(e,'cabeza_giro')))
    pit = max(-1.,min(1.,rig._n(e,'cabeza_cabeceo')))
    sx = 1-.2*abs(g)
    def hp(x,y):return hq(x*sx+g*.42,y-pit*.26)
    # Pelo largo detrás de la cara: no tapa mirada ni expresión.
    if a['pelo'] in ('largo','coleta','trenzas'):
        for lado in (-1,1):
            if a['pelo']=='coleta' and lado<0:continue
            puntos = [hq(lado*.85,-.55),hq(lado*1.12,.5),hq(lado*1.15,1.85)]
            if a['pelo']=='trenzas':
                for i in range(8):
                    P.circ(hq(lado*(.95+.04*math.sin(i)),.4+i*.2),(.18-.008*i)*R,
                        pal['pelo'] if i%2 else pal['pelo_s'],True)
                P.circ(hq(lado*.98,1.9),.12*R,pal['cuerda'])
            else:P.chain(puntos,[.4*R,.32*R,.16*R],pal['pelo'])
    for lado in (-1,1):
        P.ell(hq(lado*.98+g*.2,.1-pit*.2),.2*R*sx,.27*R,rho,pal['piel'],True)
    P.circ(fk['Hc'],R,pal['piel_s'],True)
    P.circ(hq(-.04,-.05),.95*R,pal['piel'])
    rubor = rig._n(e,'rubor')
    if rubor>.02:
        for lado in (-1,1):
            P.ell(hp(lado*.62,.24),.2*R*sx,.12*R,rho,rig._mix(pal['piel'],pal['rubor'],rubor*.75))
    if a['barba']!='ninguna':
        puntos = [hq(math.cos(t),math.sin(t)) for t in [i*math.pi/16 for i in range(17)]]
        puntos += [hp(-.9,.16),hp(0,.37),hp(.9,.16)]
        P.poly(puntos,rig._mix(pal['piel'],pal['pelo'],.4 if a['barba']=='corta' else .85))
        if a['barba']=='larga':
            P.poly([hq(-.7,.65),hq(0,1.6),hq(.7,.65)],pal['pelo'])
    if a['pecas']:
        for lado in (-1,1):
            for x,y in ((.45,.15),(.6,.21),(.72,.12)):
                P.circ(hp(lado*x,y),.025*R,pal['pelo_s'])
    if a['pelo']!='calvo':
        borde = [hq(1.04*math.cos(t),1.04*math.sin(t)) for t in [math.pi+i*math.pi/20 for i in range(21)]]
        borde += [hq(.95,-.12),hq(.5,-.48),hq(0,-.42),hq(-.5,-.5),hq(-.95,-.12)]
        P.poly(borde,pal['pelo'])
        if a['pelo']=='rizado':
            for i in range(13):
                t = math.pi+i*math.pi/12
                P.circ(hq(math.cos(t),math.sin(t)),.23*R,pal['pelo'],True)
        for x in (-.5,0,.5):
            P.stroke([hq(x,-.55),hq(x-.1,-.85)],.045*R,pal['pelo_l'])
    mx,my = rig._n(e,'mirada_x'),rig._n(e,'mirada_y')
    for lado in (-1,1):
        sufijo = 'i' if lado<0 else 'd'
        abierto = max(0.,min(1.,rig._n(e,'parpado_'+sufijo,1.)))
        x = lado*.38
        if abierto<.12 or rig._n(e,'ojo_feliz')>=.5:
            P.stroke(rig._bez(hp(x-.14,.03),hp(x,-.15),hp(x+.14,.03),8),.06*R,pal['ojo'])
        else:
            if rig._n(e,'esclera')>.5:P.ell(hp(x,-.04),.16*R*sx,.21*R*abierto,rho,(250,250,255),True)
            c = hp(x+mx*.055,-.04-my*.05)
            P.ell(c,.12*R*sx,.18*R*abierto,rho,pal['ojo'])
            P.circ((c[0]-.04*R,c[1]-.06*R),.035*R,(255,255,255))
        al,inc = rig._n(e,'ceja_'+sufijo+'_alt'),rig._n(e,'ceja_'+sufijo+'_incl')
        P.stroke(rig._bez(hp(lado*.12,-.4-al*.14-inc*.12),hp(lado*.4,-.47-al*.14),
            hp(lado*.66,-.36-al*.14+inc*.09),8),.075*R,pal['ceja'])
        if a['gafas']:
            aro = [hp(x+.28*math.cos(t),-.04+.26*math.sin(t)) for t in [i*math.pi/12 for i in range(25)]]
            P.stroke(aro,.045*R,pal['pelo_s'])
        if a['edad']>=55:
            P.stroke([hp(lado*.65,.05),hp(lado*.85,.12)],.025*R,pal['piel_s'])
    if a['gafas']:P.stroke([hp(-.1,-.04),hp(.1,-.04)],.045*R,pal['pelo_s'])
    P.stroke(rig._bez(hp(.03,.06),hp(.12,.22),hp(-.02,.25),6),.035*R,pal['piel_s'])
    sonrisa,abre = rig._n(e,'sonrisa'),rig._n(e,'boca_abre')
    ancho,lado = .14+.26*rig._n(e,'boca_ancho',.45),rig._n(e,'boca_lado')
    izq,der = hp(-ancho,.56-sonrisa*.1+lado*.04),hp(ancho,.56-sonrisa*.1-lado*.08)
    if abre>.04:
        top = rig._bez(izq,hp(lado*.05,.52-sonrisa*.03),der,10)
        bot = rig._bez(der,hp(lado*.05,.66+abre*.7+sonrisa*.05),izq,10)
        P.poly(top+bot,pal['boca'])
        if abre>.35:P.ell(hp(0,.66+abre*.38),ancho*.55*R,abre*.13*R,rho,pal['lengua'])
        if abre>.15 and sonrisa>.4:P.poly(top+[(p[0],p[1]+.085*R) for p in top][::-1],(252,252,255))
    else:P.stroke(rig._bez(izq,hp(lado*.05,.58+sonrisa*.1),der,10),.06*R,pal['boca'])
    sudor = rig._n(e,'sudor')
    if sudor>.02:
        c = hq(1.08,-.35+sudor*.25)
        P.circ(c,.095*R,(150,205,255))
        P.poly([(c[0],c[1]-.24*R),(c[0]-.08*R,c[1]-.04*R),(c[0]+.08*R,c[1]-.04*R)],(150,205,255))
