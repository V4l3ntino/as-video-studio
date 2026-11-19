"""Instancias independientes de un rig compartido, solo en el renderer aislado.

No impone geometría ni poses. Un personaje aporta materiales, valores iniciales
y funciones de dibujo adicionales, sin copiar la cinemática del rig original.
"""
import copy
import importlib.util
from functools import partial
from pathlib import Path


def crear(base, paletas=None, inicial=None, extensiones=None):
    """Carga una instancia privada: nunca cambia globals del módulo compartido.

    paletas: {nombre_global: {slot:valor}}, p.ej. {'PAL':{'piel':(r,g,b)}}.
    inicial: claves por defecto superpuestas a estado_base(), si existe.
    extensiones: {nombre_funcion: funcion(rig,*args)}. Puede sustituir o añadir
    cualquier función, incluso cabeza/ropa/geometría; recibe el rig para llamar
    sus helpers. Las funciones originales siguen en rig.originales.
    """
    ruta = Path(base.__file__).resolve()
    # El ejecutor proporciona exclusivamente módulos copiados en herramientas/.
    # No es una VM: es la misma frontera organizativa que el código por escena.
    if ruta.parent.name != 'herramientas' or ruta.suffix != '.py':
        raise ValueError('la base del rig debe ser un módulo de recursos de esta salida')
    spec = importlib.util.spec_from_file_location(base.__name__+'_instancia',ruta)
    rig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rig)
    for nombre,cambios in (paletas or {}).items():
        actual = getattr(rig,nombre,None)
        if not isinstance(actual,dict) or not isinstance(cambios,dict):
            raise ValueError('la paleta no corresponde a un diccionario del rig: '+nombre)
        setattr(rig,nombre,dict(actual,**copy.deepcopy(cambios)))
    rig.originales = {k:v for k,v in vars(rig).items() if callable(v)}
    if inicial:
        original = getattr(rig,'estado_base',None)
        if not callable(original):
            raise ValueError('este rig no tiene estado_base; personaliza dibujar con una extensión')
        def estado_base():
            return dict(original(),**copy.deepcopy(inicial))
        rig.estado_base = estado_base
    for nombre,funcion in (extensiones or {}).items():
        if not isinstance(nombre,str) or not nombre.isidentifier() or not callable(funcion):
            raise ValueError('extensión del rig no válida')
        setattr(rig,nombre,partial(funcion,rig))
    return rig
