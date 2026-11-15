"""Conversación de retoque sobre el plan publicado de una sola escena."""
import copy
import json

from pasos import medios, stickman


def ruta(proyecto, sid):
    return proyecto.ruta('stickman', 'chats', sid + '.json')


def fuente(proyecto, plan, sid):
    escena = next((e for e in plan.get('escenas', []) if e['id'] == sid), None)
    if not escena:
        raise ValueError('esa escena ya no existe')
    version = proyecto.version_activa('assets')
    carpeta = proyecto.ruta_paso('assets', version) if version else ''
    ficha = medios.leer_json(carpeta + '/escenas/' + sid + '.json', {}) or {}
    animacion = medios.leer_json(carpeta + '/escenas/' + sid + '.animacion.json', {}) or {}
    if (ficha.get('origen') != 'stickman' or not animacion.get('contenido')
            or animacion.get('firma') != ficha.get('firma_stickman')
            or ficha.get('narracion') != escena.get('narracion')):
        raise ValueError('genera primero la animación actual de esta escena para poder editarla')
    return escena, animacion['contenido']


def leer(proyecto, escena):
    charla = medios.leer_json(ruta(proyecto, escena['id']), {}) or {}
    if charla.get('ancla') != escena.get('narracion'):
        return dict(ancla=escena.get('narracion'), mensajes=[])
    return charla


def conversar(proyecto, escena, contenido, mensaje, avisar):
    charla = leer(proyecto, escena)
    mensajes = charla['mensajes'] + [dict(autor='usuario', texto=mensaje)]
    # Conservar también el encargo si la consulta falla o se cancela.
    charla['mensajes'] = mensajes
    medios.escribir_json(ruta(proyecto, escena['id']), charla)
    respuesta = stickman.consultar(
        'Eres Claude, editor de escenas Stickman 2D. Habla en español. '
        'Este turno SOLO conversa, no genera ni aplica animaciones. Ayuda a concretar '
        'cambios puntuales sobre la animación existente, conservando todo lo demás. '
        'No cambies narración, voces ni duración. Si falta una decisión, pregunta. '
        'Devuelve {"mensaje":"respuesta al usuario"}. Datos de contexto:\n'
        + json.dumps(dict(escena=escena, animacion_actual=contenido, mensajes=mensajes), ensure_ascii=False),
        proyecto, avisar=avisar, validar=_respuesta)
    mensajes.append(dict(autor='claude', texto=respuesta['mensaje']))
    medios.escribir_json(ruta(proyecto, escena['id']), charla)
    return charla


def _respuesta(datos):
    if not isinstance(datos, dict) or not isinstance(datos.get('mensaje'), str) or not datos['mensaje'].strip():
        raise ValueError('falta la respuesta de Claude')
    return datos


def encargo(proyecto, escena, contenido, mensaje, porcentaje):
    charla = leer(proyecto, escena)
    mensajes = copy.deepcopy(charla['mensajes'])
    if mensaje:
        mensajes.append(dict(autor='usuario', texto=mensaje))
    if not any(m['autor'] == 'usuario' for m in mensajes):
        raise ValueError('describe los cambios que quieres aplicar')
    return dict(ancla=escena.get('narracion'), contenido=copy.deepcopy(contenido),
        mensajes=mensajes, proveedor='ChatGPT' if porcentaje >= 50 else 'Claude')
