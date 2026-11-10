"""Contrato de las pistas temporales del editor; sin dependencias HTTP."""
import math
import re

from pasos import animaciones, avatar, parallax, transiciones


def validar(datos, escena, resolucion):
    if not isinstance(datos, dict) or set(datos) - {'animacion', 'avatar', 'parallax', 'transiciones', 'sonidos'}:
        raise ValueError('opciones de escena desconocidas')
    limpio = {}
    duracion = float(escena.get('duracion') or (float(escena['t_out']) - float(escena['t_in'])))
    if 'animacion' in datos:
        limpio['animacion'] = animaciones.validar_edicion(datos['animacion'], escena)
    if 'sonidos' in datos:
        ficha = datos['sonidos']
        if not isinstance(ficha, dict) or ficha.get('ancla') != animaciones.ancla_de(escena):
            raise ValueError('los sonidos no corresponden a esta escena')
        bloques = ficha.get('bloques')
        if not isinstance(bloques, list) or len(bloques) > 32:
            raise ValueError('utiliza como máximo 32 bloques de sonido')
        for b in bloques:
            if not isinstance(b, dict) or set(b) != {'id', 'inicio', 'fin'} or not isinstance(b['id'], str) or (b['id'] not in ('tecla', 'retorno', 'escena', 'transicion_suave', 'transicion_acento') and not re.fullmatch(r'freesound:[1-9][0-9]{0,11}', b['id'])):
                raise ValueError('bloque de sonido no válido')
            if any(isinstance(b[k], bool) or not isinstance(b[k], (int, float)) or not math.isfinite(b[k]) for k in ('inicio', 'fin')):
                raise ValueError('los tiempos deben ser números finitos')
            if not 0 <= b['inicio'] < b['fin'] <= duracion + 1e-6 or b['fin'] - b['inicio'] < .1 - 1e-6:
                raise ValueError('los sonidos deben quedar dentro de la escena y durar al menos 0,1 s')
        limpio['sonidos'] = dict(ancla=ficha['ancla'], bloques=[dict(b) for b in bloques])
    if 'parallax' in datos:
        limpio['parallax'] = parallax.validar_edicion(datos['parallax'], escena)
    if 'avatar' in datos:
        a = datos['avatar']
        if not isinstance(a, dict) or a.get('ancla') != avatar.ancla_de(escena) or not isinstance(a.get('activo'), bool):
            raise ValueError('el avatar no corresponde a esta escena')
        limpio['avatar'] = dict(ancla=a['ancla'], activo=a['activo'],
            posicion=avatar.validar_posicion(a.get('posicion'), resolucion),
            presentacion=avatar.validar_presentacion(a.get('presentacion'), duracion))
    if 'transiciones' in datos:
        ficha = datos['transiciones']
        if not isinstance(ficha, dict) or ficha.get('ancla') != animaciones.ancla_de(escena):
            raise ValueError('las transiciones no corresponden a esta escena')
        bloques = ficha.get('bloques')
        if not isinstance(bloques, list) or len(bloques) > 32:
            raise ValueError('utiliza como máximo 32 transiciones')
        limpios = []
        for b in bloques:
            if not isinstance(b, dict) or set(b) != {'tipo', 'sentido', 'inicio', 'fin'}:
                raise ValueError('bloque de transición no válido')
            if not isinstance(b['tipo'], str) or b['tipo'] not in transiciones.CATALOGO or b['tipo'] == 'corte' or b['sentido'] not in ('entrada', 'salida'):
                raise ValueError('elige un efecto y su sentido de entrada o salida')
            if any(isinstance(b[k], bool) or not isinstance(b[k], (float, int)) or not math.isfinite(b[k]) for k in ('inicio', 'fin')):
                raise ValueError('los tiempos deben ser números finitos')
            if not 0 <= b['inicio'] < b['fin'] <= duracion + 1e-6 or b['fin'] - b['inicio'] < .1 - 1e-6:
                raise ValueError('las transiciones deben quedar dentro de la escena y durar al menos 0,1 s')
            limpios.append(dict(b))
        limpio['transiciones_escena'] = dict(ancla=ficha['ancla'], bloques=limpios)
    return limpio


def transiciones_de(unidad, escena):
    ficha = (unidad or {}).get('transiciones_escena') or {}
    return ficha.get('bloques', []) if ficha.get('ancla') == animaciones.ancla_de(escena) else []
