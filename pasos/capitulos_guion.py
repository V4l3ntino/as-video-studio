"""Capítulos editoriales y aperturas visuales, sin alterar narración ni reloj."""
import copy

ESTILOS = ('arctic', 'ember', 'mixto', 'sakura', 'retro')


def normalizar(datos):
    if not isinstance(datos, dict) or set(datos) - {'numero', 'titulo', 'estilo'}:
        raise ValueError('capitulo debe contener numero, titulo y estilo')
    numero, titulo, estilo = datos.get('numero'), datos.get('titulo'), datos.get('estilo', 'mixto')
    if type(numero) is not int or not 1 <= numero <= 99:
        raise ValueError('el número de capítulo debe estar entre 1 y 99')
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > 120:
        raise ValueError('cada capítulo necesita un título de hasta 120 caracteres')
    if estilo not in ESTILOS:
        raise ValueError('estilo de capítulo desconocido')
    return dict(numero=numero, titulo=titulo.strip(), estilo=estilo)


def validar_plan(capitulos, tramos):
    if not isinstance(capitulos, list) or not 1 <= len(capitulos) <= 99:
        raise ValueError('la escaleta necesita una lista de capítulos temáticos')
    ids = [t['id'] for t in tramos]
    usados, titulos, posiciones, salida = set(), set(), [], []
    for numero, capitulo in enumerate(capitulos, 1):
        if not isinstance(capitulo, dict):
            raise ValueError('cada capítulo de la escaleta debe ser un objeto')
        limpio = normalizar({k: v for k, v in capitulo.items() if k != 'tramos'})
        if limpio['numero'] != numero or limpio['titulo'].casefold() in titulos:
            raise ValueError('los capítulos necesitan números consecutivos y títulos distintos')
        partes = capitulo.get('tramos')
        if not isinstance(partes, list) or not partes or any(not isinstance(t, str) or t not in ids or t in usados for t in partes):
            raise ValueError('cada capítulo necesita tramos existentes, sin repetir ni compartirlos')
        indices = [ids.index(t) for t in partes]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValueError('los tramos de un capítulo deben ser consecutivos y estar en orden')
        usados.update(partes)
        posiciones.extend(indices)
        titulos.add(limpio['titulo'].casefold())
        salida.append(dict(limpio, tramos=list(partes)))
    if posiciones != sorted(set(posiciones)) or set(ids[1:-1]) - usados:
        raise ValueError('los capítulos deben recorrer el desarrollo en orden; solo gancho y cierre pueden quedar fuera')
    return salida


def asignar(escaleta, bloques):
    """Agrupa los bloques reales por los capítulos decididos ANTES de redactar."""
    capitulos = escaleta.get('capitulos') or []
    if not capitulos:
        return []
    por_tramo = {t: c for c in capitulos for t in c['tramos']}
    salida = [dict(copy.deepcopy(c), bloques=[]) for c in capitulos]
    for bloque in bloques:
        bloque.pop('capitulo', None)
        capitulo = por_tramo.get(bloque.get('tramo'))
        if capitulo:
            bloque['capitulo'] = {k: capitulo[k] for k in ('numero', 'titulo', 'estilo')}
            ficha = salida[capitulo['numero'] - 1]
            if not ficha['bloques']:
                bloque['abre_seccion'] = True
            ficha['bloques'].append(bloque['id'])
    if any(not c['bloques'] for c in salida):
        raise ValueError('todos los capítulos deben corresponder a bloques reales del guion')
    return salida


def validar_orden(capitulos):
    vistos = {}
    ultimo = 0
    for capitulo in capitulos:
        if capitulo is None:
            continue
        capitulo = normalizar(capitulo)
        numero = capitulo['numero']
        if numero in vistos and (numero != ultimo or vistos[numero] != capitulo):
            raise ValueError('los capítulos deben ser contiguos y conservar su título y estilo')
        if numero not in vistos:
            if numero != len(vistos) + 1:
                raise ValueError('los capítulos deben empezar en 1 y avanzar consecutivamente')
            vistos[numero] = capitulo
        ultimo = numero


def de_bloques(bloques):
    validar_orden([b.get('capitulo') for b in bloques])
    salida = {}
    for bloque in bloques:
        if not bloque.get('capitulo'):
            continue
        capitulo = normalizar(bloque['capitulo'])
        bloque['capitulo'] = capitulo
        salida.setdefault(capitulo['numero'], dict(capitulo,bloques=[]))['bloques'].append(bloque['id'])
    return list(salida.values())


def marcar_aperturas(escenas):
    vistos = set()
    for escena in escenas:
        escena.pop('apertura_capitulo', None)
        if not escena.get('capitulo'):
            continue
        capitulo = normalizar(escena['capitulo'])
        escena['capitulo'] = capitulo
        if capitulo['numero'] not in vistos:
            duracion = max(0, float(escena['duracion_s']) if 'duracion_s' in escena
                else float(escena['t_out']) - float(escena['t_in']))
            lectura = .3 + len(capitulo['titulo'].split()) * .28
            fin = duracion if duracion <= 3 else min(2.8, max(1.8, lectura, duracion * .38))
            escena['apertura_capitulo'] = dict(capitulo, duracion_s=round(fin, 6))
            vistos.add(capitulo['numero'])


def componente(apertura):
    return dict(tipo='capitulo', inicio=0, fin=apertura['duracion_s'], capa='pantalla',
        opciones={k: apertura[k] for k in ('numero', 'titulo', 'estilo')})


INSTRUCCION = '''== CAPÍTULOS Y PUNTOS VISUALES ==
Organiza el desarrollo en capítulos temáticos consecutivos, no un capítulo por frase o ejemplo.
Conserva un gancho inicial breve y un cierre útil; pueden quedar fuera de la numeración.
Cada capítulo desarrolla una pregunta o punto distinto con varios bloques y representaciones:
actuación, primeros planos, comparación, diagramas, cronología, listas y detalles según la idea.
No conviertas todo en una presentación de texto ni repitas la tesis con decorados distintos.
capitulo contiene numero, titulo y estilo ya decididos; son estructura, NO palabras locutadas.
Al comenzar un capítulo, su primera escena abre con el número 01/02/03 grande con halo suave,
línea fina y título breve blanco cálido, tipografía redondeada Fredoka y partículas flotantes.
Estilos de apertura: arctic (azul frío), ember (ámbar/naranja), mixto (frío a la izquierda,
cálido a la derecha, número dorado), sakura (rosa/ciruela) y retro (teal/mostaza).
Elige el acabado por el tema y mantén continuidad dentro del capítulo, variando la representación.
El estilo del capítulo orienta su portada y sus luces; la identidad del personaje y los materiales
se conservan. No alternes colores arbitrariamente por cada frase.
La apertura pertenece a la primera frase real de ese capítulo: no añadas frases de relleno,
no locutes números ni títulos solo por mostrarlos, no cambies palabras ni agregues pausas.
En las frases siguientes desarrolla el punto; no vuelvas a mostrar la portada por continuidad.
Si no hay capítulos declarados, no inventes una numeración al regenerar descripciones históricas.
Al corregir un guion que ya tiene capítulos, conserva su número, título y estilo por bloque,
salvo que la petición pida cambiar esa estructura.
'''
