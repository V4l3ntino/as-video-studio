"""Guiones portátiles: narración y dirección visual por frase, sin proveedores."""
import copy
import os

from nucleo import Estado
from pasos import comun, descripciones_escenas, marcas_tts, medios, p4_voz


FORMATO = 'as-video-studio/guion-v1'


def importar(proyecto, documento):
    if not isinstance(documento, dict) or documento.get('formato') != FORMATO:
        raise ValueError('formato de guion desconocido; utiliza un JSON exportado desde Guion')
    entradas = documento.get('bloques')
    if not isinstance(entradas, list) or not entradas:
        raise ValueError('el guion necesita al menos un bloque')
    anterior = comun.leer_salida(proyecto, 'guion', 'guion.json', obligatorio=True)
    originales = p4_voz.ediciones_a_mano(proyecto, copy.deepcopy(anterior['guion']))
    segmentar = medios.motor('guion/segmentar.py').frases_del_texto
    bloques, escenas = [], []
    ids = {b['id'] for b in originales}
    # Valida TODO antes de persistir narración o descripciones.
    for i, entrada in enumerate(entradas):
        if not isinstance(entrada, dict) or not isinstance(entrada.get('texto'), str) or not entrada['texto'].strip():
            raise ValueError(f'el bloque {i + 1} necesita texto narrado')
        texto = ' '.join(entrada['texto'].split())
        base = originales[i] if i < len(originales) else {}
        bid = base.get('id') or f'IMPORTADO_{i + 1:03d}'
        if not base:
            while bid in ids:
                bid += '_nuevo'
            ids.add(bid)
        bloque = dict(base, id=bid, texto=texto)
        if texto == ' '.join(marcas_tts.limpiar(base.get('texto', '')).split()):
            bloque['texto'] = base['texto']  # Conserva pausas y marcas de voz.
        visuales = entrada.get('escenas')
        frases = segmentar(marcas_tts.limpiar(texto))
        if not isinstance(visuales, list) or len(visuales) != len(frases):
            raise ValueError(f'el bloque {i + 1} necesita una descripción por frase ({len(frases)})')
        for indice, (visual, frase) in enumerate(zip(visuales, frases)):
            if not isinstance(visual, dict) or visual.get('texto') != frase:
                raise ValueError(f'el bloque {i + 1}, escena {indice + 1}, debe incluir su frase literal en texto')
            descripcion = visual.get('descripcion_visual')
            if not isinstance(descripcion, str) or len(descripcion) > 8000:
                raise ValueError('cada descripción debe ser texto de hasta 8000 caracteres')
            # Los guiones históricos pueden no tener aún dirección visual.
            escenas.append(dict(bloque=bid, indice=indice, texto=frase,
                                descripcion_visual=descripcion.strip()))
        bloques.append(bloque)
    estado = Estado(proyecto)
    actuales = descripciones_escenas.listar(proyecto)
    por_ancla = {(e['bloque'], e['indice'], e['texto']): e for e in actuales}
    unidades = copy.deepcopy(estado.params('assets').get('unidades') or {})
    textos_cambiados = bloques != originales
    if textos_cambiados:
        # Las posiciones globales pueden moverse al añadir o quitar frases.
        # Evita que una ancla vieja duplicada prevalezca desde una unidad sobrante.
        for unidad in unidades.values():
            if isinstance(unidad, dict):
                unidad.pop('descripcion_escena', None)
    visuales_cambiadas = 0
    for numero, escena in enumerate(escenas, 1):
        previa = por_ancla.get((escena['bloque'], escena['indice'], escena['texto']))
        igual = previa and previa['descripcion_visual'] == escena['descripcion_visual']
        if igual and not textos_cambiados:
            continue
        uid = f'escena:S{numero:03d}'
        unidad = dict(unidades.get(uid) or {})
        unidad['descripcion_escena'] = escena
        unidades[uid] = unidad
        visuales_cambiadas += int(not igual)
    if textos_cambiados and len(bloques) == len(originales):
        ediciones = copy.deepcopy(estado.params('guion').get('bloques') or {})
        for bloque, original in zip(bloques, originales):
            if bloque['texto'] != original['texto']:
                ficha = ediciones.get(bloque['id'])
                ediciones[bloque['id']] = dict(ficha if isinstance(ficha, dict) else {}, texto=bloque['texto'])
        estado.actualizar_params('guion', {'bloques': ediciones})
    elif textos_cambiados:
        # Una estructura nueva es una versión real; conserva el histórico.
        nuevo = copy.deepcopy(anterior)
        for campo in ('plan_narrativo', 'escaleta_editorial', 'fases_guion', 'flujo_redaccion'):
            nuevo.pop(campo, None)
        nuevo.update(guion=bloques, escenas_por_frase=True,
                     palabras=sum(len(marcas_tts.limpiar(b['texto']).split()) for b in bloques))
        trabajo = comun.preparar_trabajo(proyecto, 'guion')
        comun.escribir_json(os.path.join(trabajo, 'guion.json'), nuevo)
        comun.escribir_texto(os.path.join(trabajo, 'guion.txt'), '\n\n'.join(b['texto'] for b in bloques))
        estado.actualizar_params('guion', {'bloques': {}})
        estado.completar('guion', dict(guion_fichero='guion.json', titulo=nuevo.get('titulo', ''),
            bloques=len(bloques), palabras=nuevo['palabras']))
    if visuales_cambiadas or textos_cambiados:
        estado.actualizar_params('assets', {'unidades': unidades})
    return dict(bloques=len(bloques), texto_cambiado=textos_cambiados, descripciones_cambiadas=visuales_cambiadas)
