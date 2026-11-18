"""Reparto explícito de escenas, no de tokens, tiempo ni generación de imágenes."""


def normalizar(valor):
    if valor is None:
        return None
    if not isinstance(valor, dict) or set(valor) != {'carga_claude'}:
        raise ValueError('reparto_animaciones necesita carga_claude, un entero de 0 a 100')
    carga = valor['carga_claude']
    if type(carga) is not int or not 0 <= carga <= 100:
        raise ValueError('carga_claude debe ser un entero de 0 a 100')
    return dict(carga_claude=carga)


def carga_de(params, defecto=100):
    reparto = normalizar(params.get('reparto_animaciones'))
    return reparto['carga_claude'] if reparto is not None else defecto


def proveedores(escenas, params):
    carga = carga_de(params)
    chatgpt = len(escenas) * (100 - carga) // 100
    claude = len(escenas) - chatgpt
    return {e['id']: 'Claude' if i < claude else 'ChatGPT' for i, e in enumerate(escenas)}
