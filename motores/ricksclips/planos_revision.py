"""Puesta en escena de revisión. Datos de ejemplo, no límites del código libre."""


def plano(nombre,backend=None):
    blender=backend=='blender'
    actor=dict(pos=(0,0,-1.2),alto=2.8,accion='quieto',sombrero='oeste',bigote=True,
        apariencia=dict(pelo='calvo',ropa='chaqueta',colores=dict(ropa='#348F7C',acento='#CDA45F')))
    base=dict(escenario='oeste',actores=[actor],demostracion=False)
    cams={
        'general':dict(eye=(.9,2.25,6.8),target=(0,1.55,-2),fov=46,apertura=.25),
        'medio':dict(eye=(.35,2.2,2.4),target=(0,1.9,-1.2),fov=46,apertura=.8),
        # Rostro arriba: reserva el 70-74% para la capa real de subtítulos p7.
        'rostro':dict(eye=(.1,2.05,.3),target=(0,1.72,-1.2),fov=42,apertura=1.2),
    }
    if nombre in cams:base['camara']=cams[nombre]
    elif nombre=='movil':
        base.update(escenario='taberna',actores=[dict(actor,accion='atrapar',bigote=False)],
            camara=dict(eye=(1,2.5,2.5),target=(0,1.8,-1.2),fov=47,apertura=.5))
    elif nombre=='cocina':
        base.update(escenario='cocina',actores=[dict(actor,pos=(0,0,-5.8),sombrero='chef',bigote=False,accion='verter',
            apariencia=dict(pelo='calvo',ropa='camisa',colores=dict(ropa='#E7E2CF',acento='#A44634')))],
            camara=dict(eye=(.6,2.65,-1),target=(.65,1.9,-5.5),fov=48,apertura=.35))
        if blender:
            base['actores'][0].update(alto=3.25,pos=(.15,0,-5.8))
            base['camara']=dict(eye=(.75,2.45,-.2),target=(.75,1.65,-5.6),fov=54,apertura=0)
    elif nombre=='cuenco':
        base.update(escenario='cocina',actores=[],camara=dict(eye=(1.8,3.3,-4.6),target=(1.8,1.65,-5),fov=45,apertura=.08))
        if blender:base['camara']=dict(eye=(1.65,3.3,-4.4),target=(1.65,1.65,-5),fov=45,apertura=.08)
    elif nombre in ('tormenta','calma'):
        base.update(escenario='mar',actores=[],decorado=dict(calma=1 if nombre=='calma' else 0),
            camara=dict(eye=(8,5,10),target=(-1,2,-8),fov=57,apertura=.12))
        if nombre=='calma':base['camara']=dict(eye=(5,11,4),target=(-1,0,-4),fov=50,apertura=.12)
    elif nombre in ('canon','torcida'):
        base.update(escenario='canon',actores=[dict(actor,pos=(2.3,0,-1.5),sombrero='gorra',bigote=False)],
            decorado=dict(torcido=.8 if nombre=='torcida' else 0),
            camara=dict(eye=(3,2.0,5),target=(1.3,1.2,-5),fov=54,apertura=.2))
    elif nombre in ('puente','explosion'):
        base.update(escenario='puente',actores=[],explosion=nombre=='explosion',
            camara=dict(eye=(4,3.8,9),target=(0,1,-9),fov=55,apertura=.15))
    else:raise ValueError(nombre)
    return base
