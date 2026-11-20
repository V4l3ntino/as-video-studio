"""Variantes anónimas sobre el rig DEL estilo; nunca otro dibujo de monigote."""
from functools import partial
from PIL import Image, ImageColor


def crear(base,soporte,apariencias,perfil,apariencia=None,silueta=None,extensiones=None):
    if perfil:
        rig = apariencias.crear(base,soporte,apariencia or {},perfil=perfil)
    else:
        if apariencia:
            raise ValueError('este rig antiguo no tiene apariencia parametrizada; usa sus controles o extensiones')
        rig = soporte.crear(base)
    if silueta is not None:
        color = ImageColor.getrgb(silueta)
        if len(color)!=3:
            raise ValueError('el color de silueta debe ser RGB opaco')
        original = rig.dibujar
        def dibujar(lienzo,estado,contexto):
            # La silueta sale de la misma geometría, proporciones y articulaciones.
            # No se sustituye el cuerpo por círculos/triángulos de otro estilo.
            capa = Image.new('RGBA',lienzo.size)
            anclas = original(capa,estado,contexto)
            tinta = Image.new('RGBA',lienzo.size,color+(255,))
            tinta.putalpha(capa.getchannel('A'))
            if lienzo.mode=='RGBA':
                lienzo.alpha_composite(tinta)
            else:
                lienzo.paste(tinta,(0,0),tinta.getchannel('A'))
            return anclas
        rig.dibujar = dibujar
    rig.dibujo_compartido = rig.dibujar
    for nombre,funcion in (extensiones or {}).items():
        if not isinstance(nombre,str) or not nombre.isidentifier() or not callable(funcion):
            raise ValueError('extensión de persona no válida')
        setattr(rig,nombre,partial(funcion,rig))
    return rig
