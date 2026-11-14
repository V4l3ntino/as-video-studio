"""Dirección visual editable por frase, independiente del texto y de la voz.

Las correcciones viven en params de la unidad de assets, ancladas a su frase.
No se reescribe guion.json ni se altera la firma de guion/voz al dirigir un plano.
"""
import copy
import json
import os

from nucleo.estado import Estado
from pasos import comun, medios, personajes, p4_voz


def _clave(bloque, texto, indice):
    return bloque, medios.normalizar_texto(texto), indice


def listar(proyecto):
    from pasos import p6_assets, marcas_tts
    documento = comun.leer_salida(proyecto, 'guion', 'guion.json', obligatorio=False) or {}
    bloques = p4_voz.ediciones_a_mano(proyecto, copy.deepcopy(documento.get('guion') or []))
    plan = p6_assets.plan_actual(proyecto, 'assets') or {}
    anteriores = {}
    for e in plan.get('escenas', []):
        clave = ((e.get('origen') or {}).get('bloque'), medios.normalizar_texto(e.get('narracion') or ''))
        anteriores.setdefault(clave, []).append(e)
    params = personajes.params_de(proyecto, 'assets')
    guardadas = [u['descripcion_escena'] for u in (params.get('unidades') or {}).values()
                 if isinstance(u, dict) and isinstance(u.get('descripcion_escena'), dict)]
    por_ancla = {_clave(v['bloque'], v['texto'], v['indice']): v for v in guardadas}
    resultado, ocurrencias = [], {}
    for b in bloques:
        texto = marcas_tts.limpiar(b['texto'])
        try:
            frases = medios.motor('guion/segmentar.py').frases_del_texto(texto)
        except ValueError:
            # El editor debe seguir abriendo mientras se corrige una frase.
            frases = [texto] if texto.strip() else []
        for indice, frase in enumerate(frases):
            clave = (b['id'], medios.normalizar_texto(frase))
            repeticion = ocurrencias.get(clave, 0)
            ocurrencias[clave] = repeticion + 1
            candidatos = anteriores.get(clave, [])
            anterior = candidatos[repeticion] if repeticion < len(candidatos) else {}
            # Igual que p6_assets._heredar_ids: el ID es la posición actual,
            # incluso cuando una frase se ha editado o cambiado de sitio.
            sid = f'S{len(resultado) + 1:03d}'
            visuales = [v for v in b.get('escenas_visuales') or []
                        if medios.normalizar_texto(v.get('texto') or '') == clave[1]]
            visual = visuales[repeticion] if repeticion < len(visuales) else {}
            descripcion = visual.get('descripcion_visual') or b.get('descripcion_visual') or anterior.get('descripcion_visual') or ''
            guardada = por_ancla.get(_clave(b['id'], frase, indice))
            if guardada:
                descripcion = guardada['descripcion_visual']
            resultado.append(dict(id=sid, bloque=b['id'], indice=indice, texto=frase,
                                  descripcion_visual=descripcion))
    return resultado


def validar(cambios, actuales, completa=False):
    if not isinstance(cambios, list) or not cambios:
        raise ValueError('envía una lista de descripciones de escenas')
    por_clave = {(e['bloque'], e['indice']): e for e in actuales}
    salida, vistos, descripciones = [], set(), set()
    for c in cambios:
        if not isinstance(c, dict) or type(c.get('indice')) is not int or not isinstance(c.get('bloque'), str):
            raise ValueError('cada descripción necesita bloque e índice de frase')
        clave = (c['bloque'], c['indice'])
        actual = por_clave.get(clave)
        if not actual or c.get('texto') != actual['texto']:
            raise ValueError('el guion ha cambiado; recarga las descripciones antes de guardarlas')
        if clave in vistos:
            raise ValueError('hay descripciones de escenas duplicadas')
        descripcion = c.get('descripcion_visual')
        if not isinstance(descripcion, str) or not descripcion.strip() or len(descripcion) > 8000:
            raise ValueError('la descripción debe tener entre 1 y 8000 caracteres')
        visual = (c['bloque'], medios.normalizar_texto(descripcion))
        if completa and visual in descripciones:
            raise ValueError('las escenas del bloque necesitan acciones diferentes, sin repetir su descripción')
        descripciones.add(visual)
        vistos.add(clave)
        salida.append(dict(actual, descripcion_visual=descripcion.strip()))
    if completa and vistos != set(por_clave):
        raise ValueError('falta una descripción por cada frase del guion')
    return salida


def guardar(proyecto, cambios, anteriores=None):
    actuales = listar(proyecto)
    if anteriores is not None and actuales != anteriores:
        raise ValueError('el guion o sus descripciones han cambiado durante la generación; vuelve a intentarlo')
    nuevos = validar(cambios, actuales)
    estado = Estado(proyecto)
    unidades = estado.params('assets').get('unidades') or {}
    cambios_unidad = {}
    for e in nuevos:
        actual = next(a for a in actuales if (a['bloque'], a['indice']) == (e['bloque'], e['indice']))
        if actual['descripcion_visual'] == e['descripcion_visual']:
            continue
        uid = 'escena:' + e['id']
        unidad = copy.deepcopy(unidades.get(uid) or {})
        unidad['descripcion_escena'] = {k: e[k] for k in ('bloque', 'indice', 'texto', 'descripcion_visual')}
        cambios_unidad[uid] = unidad
    if cambios_unidad:
        estado.actualizar_params('assets', {'unidades': cambios_unidad})
    return dict(escenas=listar(proyecto), cambiadas=len(cambios_unidad))


def aplicar(escenas, params):
    """Las correcciones del usuario mandan sobre la dirección generada anteriormente."""
    guardadas = [u['descripcion_escena'] for u in (params.get('unidades') or {}).values()
                 if isinstance(u, dict) and isinstance(u.get('descripcion_escena'), dict)]
    por_ancla = {_clave(v['bloque'], v['texto'], v['indice']): v for v in guardadas}
    indices = {}
    for e in escenas:
        bloque = (e.get('origen') or {}).get('bloque')
        indice = (e.get('origen') or {}).get('indice', indices.get(bloque, 0))
        indices[bloque] = indice + 1
        visual = por_ancla.get(_clave(bloque, e.get('narracion') or '', indice))
        if visual:
            e['descripcion_visual'] = visual['descripcion_visual']
            e['redactado'] = visual['descripcion_visual']
            e['accion'] = visual['descripcion_visual']


ESCENAS_POR_TANDA = 6


def regenerar(proyecto, escenas, peticion='', avisar=None, publicar=None):
    """Valida y publica tandas pequeñas; lo ya publicado sobrevive a Parar."""
    avisar = avisar or (lambda *a: None)
    terminadas = []
    contexto = [{k: e[k] for k in ('bloque', 'indice', 'texto')} for e in escenas]
    for inicio in range(0, len(escenas), ESCENAS_POR_TANDA):
        tanda = escenas[inicio:inicio + ESCENAS_POR_TANDA]

        def esperando(valor, mensaje=''):
            avisar(len(terminadas) / len(escenas),
                   f'{len(terminadas)} de {len(escenas)} descripciones guardadas · '
                   f'Preparando escenas {inicio + 1}–{inicio + len(tanda)}. {mensaje}')

        nuevas = _regenerar_tanda(proyecto, tanda, peticion, esperando,
                                   contexto, terminadas[-ESCENAS_POR_TANDA:])
        # Incluye las tandas anteriores: detecta duplicados dentro de un bloque
        # incluso cuando sus frases caen a ambos lados del corte de tanda.
        validar(terminadas + nuevas, escenas[:inicio + len(tanda)], completa=True)
        avisar(None, 'Guardando las nuevas descripciones')  # comprueba Parar
        if publicar:
            publicar(nuevas)
        terminadas.extend(nuevas)
        avisar(len(terminadas) / len(escenas),
               f'{len(terminadas)} de {len(escenas)} descripciones guardadas')
    return terminadas


def _regenerar_tanda(proyecto, escenas, peticion='', avisar=None, contexto=None, anteriores=None):
    from pasos import cli_claude, p3_guion, estadisticas
    avisar = avisar or (lambda *a: None)
    opciones = personajes.opciones_del_proyecto(proyecto)
    documento = comun.leer_salida(proyecto, 'guion', 'guion.json', obligatorio=False) or {}
    reparto = personajes.activos(opciones) + (documento.get('personajes_automaticos') or [])
    instruccion = ('Regenera SOLO las descripciones visuales de las escenas de esta tanda. '
        'El texto narrado, su puntuación, bloque e índice son INMUTABLES. No devuelvas una reescritura del guion. '
        'Devuelve JSON {"escenas":[{"bloque":"B001","indice":0,"texto":"Frase literal.",'
        '"descripcion_visual":"Lo que se ve durante esa frase."}]}. Una entrada por frase, sin omisiones. '
        'Conserva los personajes y sus identidades; no inventes otros. Cada escena debe ilustrar su propia frase '
        'y avanzar respecto a las vecinas, sin repetir la misma animación. Describe acciones, posturas, '
        'expresiones, objetos y entorno concretos, no el significado abstracto de los símbolos. '
        'Los rótulos solo cuando ayuden a comprender la acción. Mantén el idioma del guion. '
        'guion_contexto contiene el relato completo SOLO para mantener continuidad: NO lo devuelvas. '
        'escenas_anteriores contiene la dirección ya elegida; continúa desde ella sin repetir sus acciones.\n')
    if (opciones.get('sistema_personajes') or {}).get('stickman'):
        instruccion += personajes.instruccion_visual_stickman() + '\nEl formato de entrega de esta petición prevalece: SOLO escenas.\n'
    # Al regenerar no hacen falta las descripciones anteriores (los guiones
    # históricos repiten la del bloque en cada frase y multiplican el encargo).
    entradas = [{k: e[k] for k in ('bloque', 'indice', 'texto')} for e in escenas]
    original = instruccion + json.dumps(dict(escenas=entradas, guion_contexto=contexto or [],
        escenas_anteriores=anteriores or [], reparto=reparto,
        estilo=personajes.params_de(proyecto, 'assets').get('estilo') or {}, indicaciones=peticion), ensure_ascii=False)
    if os.environ.get('ESTUDIO_SIMULAR') == '1':
        return [dict(e, descripcion_visual='Una figura actúa en un espacio sencillo. Representa: ' + e['texto']) for e in escenas]
    ajuste = cli_claude.por_defecto_de('guion')
    prompt = original
    for intento in range(3):
        avisar(.1 + intento * .2, 'Regenerando las descripciones de las escenas')
        with estadisticas.Avance(avisar, .1 + intento * .2, .28 + intento * .2,
                180, f"Esperando las descripciones de Claude · {ajuste['modelo']} / {ajuste['esfuerzo']}") as avance:
            try:
                # Cientos de escenas pueden superar la salida de un mensaje.
                # La entrega larga se escribe en un temporal aislado, nunca en
                # el proyecto, igual que las demás fases con listas extensas.
                respuesta = cli_claude.escribiendo(prompt,
                    modelo=ajuste['modelo'], esfuerzo=ajuste['esfuerzo'],
                    herramientas_vetadas=tuple(h for h in p3_guion.HERRAMIENTAS_VETADAS
                                               if h not in ('Read', 'Write', 'Edit')),
                    avance=avance, para='las descripciones de las escenas')
            finally:
                avance.parar()
                if avance.cancelado:
                    # Propaga Cancelado del gestor, también si matar el CLI hizo
                    # que ejecutar() terminase con un error de proceso.
                    avisar(None, 'Regeneración de descripciones cancelada')
        try:
            return validar(respuesta.get('escenas'), escenas, completa=True)
        except (ValueError, RuntimeError, AttributeError) as exc:
            if intento == 2:
                raise ValueError('No se pudieron validar las descripciones: ' + str(exc)) from exc
            prompt = original + '\nCorrige la entrega anterior. Error: ' + str(exc) + '\n' + json.dumps(respuesta, ensure_ascii=False)[:16000]
