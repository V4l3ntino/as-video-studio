"""Contrato editorial del kit: solo datos acotados, nunca código del proveedor.

Opcional en planes históricos. Se conecta al director y al renderer Stickman;
los nombres de componentes corresponden a las funciones originales del kit.
"""
import json
import math
import re
from pathlib import Path
from pasos.tiempos_stickman import tiempo
from pasos.capitulos_guion import ESTILOS as ESTILOS_CAPITULO

ENCUADRES = ('general', 'conjunto', 'medio', 'primer_plano', 'detalle', 'grafico', 'dividido', 'cierre')
ESCENARIOS = ('vacio', 'fiesta', 'salon', 'oficina', 'laboratorio', 'barrio', 'parque', 'cocina', 'teatro', 'aula')
PALETAS = json.loads((Path(__file__).resolve().parents[1] / 'motores/stickman/paletas.json').read_text(encoding='utf-8'))

# Esquemas pequeños compartidos por validación e instrucciones al modelo.
N = ('numero', -10000, 10000)
U = ('numero', 0, 1)
POS = ('numero', 0, 10000)
TEXTO = ('texto', 240)
COLOR = ('color',)
BOOL = ('booleano',)
PUNTO = ('lista', N, 2, 2)
VECTOR = ('lista', N, 3, 3)


def opciones(**campos):
    return ('objeto', campos)


FILA = opciones(label=TEXTO, v=U, color=COLOR)
GRAFICOS = {
    'capitulo': dict(numero=('numero', 1, 99), titulo=('texto', 120),
        estilo=('elegir', *ESTILOS_CAPITULO), color=COLOR, particulas=BOOL),
    'titleCard': dict(lines=('lista', TEXTO, 1, 3), sub=TEXTO, y=N),
    'bigLine': dict(str=TEXTO, y=N, size=('numero', 24, 160), color=COLOR),
    'badge': dict(str=TEXTO, x=N, y=N, size=('numero', 24, 96), color=COLOR),
    'readout': dict(label=TEXTO, value=TEXTO, x=N, y=N, size=('numero', 24, 100), color=COLOR,
                    align=('elegir', 'left', 'center', 'right')),
    'callout': dict(at=PUNTO, to=PUNTO, str=TEXTO, color=COLOR, size=('numero', 24, 72)),
    'dimension': dict(x1=N, y1=N, x2=N, y2=N, str=TEXTO, color=COLOR),
    'dataCard': dict(title=TEXTO, subtitle=TEXTO, **{'from': N}, to=N, decimals=('numero', 0, 3),
                     unit=('texto', 20), shape=('numero', .1, 6), arrow=BOOL),
    'compareBars': dict(rows=('lista', FILA, 1, 6), x=N, y=N, w=POS, color=COLOR),
    'meter': dict(x=N, y=N, w=POS, ticks=('numero', 1, 100), label=TEXTO, color=COLOR, speed=('numero', .01, 5)),
    'blueprint': dict(grid=('numero', 20, 200), a=U),
    'lineFigure': dict(x=N, y=N, s=('numero', .1, 8), color=COLOR, facing=('elegir', -1, 1)),
    'bubble': dict(x=N, y=N, w=POS, h=POS, color=COLOR, dots=BOOL, str=('texto', 100)),
    'bocadillo': dict(personaje=('texto', 120), modo=('elegir', 'dialogo', 'pensamiento'),
        texto=('texto', 160), x=N, y=N, w=('numero', 180, 1200), h=('numero', 90, 400),
        color=COLOR, tinta=COLOR, size=('numero', 24, 64)),
    'endScreen': dict(question=TEXTO, personajes=('lista', ('texto', 120), 0, 8), suscribir=('texto', 40)),
    'captions': dict(y=N, size=('numero', 28, 100), max=('numero', 1, 8), color=COLOR, hi=COLOR),
    # Componentes semánticos del adaptador, construidos con el dibujo del kit.
    'lista': dict(titulo=TEXTO, filas=('lista', TEXTO, 1, 6), intervalo=('numero', .15, 10),
                  color=COLOR, x=N, y=N, w=POS, estilo=('elegir', 'tarjetas', 'texto'),
                  numerada=BOOL, colores_numeros=('lista', COLOR, 0, 6), size=('numero', 24, 120)),
    'barras': dict(titulo=TEXTO, filas=('lista', FILA, 1, 5), color=COLOR),
    'poblacion': dict(titulo=TEXTO, total=('numero', 1, 300), destacados=('numero', 0, 300), color=COLOR,
        filas=('numero', 1, 300), columnas=('numero', 1, 300), color_base=COLOR,
        indices_destacados=('lista', ('numero', 0, 299), 0, 300), atenuacion=U,
        inicio_destacado=('numero', 0, 120), duracion_destacado=('numero', .01, 120), neon_destacados=U),
    'cronologia': dict(titulo=TEXTO, etiquetas=('lista', ('texto', 60), 2, 8), color=COLOR),
    'documento': dict(titulo=TEXTO, filas=('lista', TEXTO, 1, 8), destacar=('numero', 0, 7), sello=('texto', 40),
        estilo=('elegir', 'papel', 'neon'), excluidos=('lista', ('texto', 40), 0, 2), color=COLOR),
    'comparacion': dict(titulo=('texto', 120), izquierda=TEXTO, derecha=TEXTO,
        detalle_izquierdo=TEXTO, detalle_derecho=TEXTO,
        rasgos_izquierdos=('lista', ('texto', 60), 0, 3), rasgos_derechos=('lista', ('texto', 60), 0, 3)),
    'interruptor': dict(titulo=TEXTO, activo=BOOL, cambio=('numero', 0, 120)),
    'dial': dict(titulo=TEXTO, valor=POS, maximo=('numero', .001, 100000), unidad=('texto', 20)),
}

# Toda la familia fx2d se expone por lista blanca; sin callbacks del modelo.
FX = {
    'rain': 'seed count angle speed len color a w timeScale',
    'drops': 'seed count rMin rMax color drift',
    'dust': 'seed count color size speed a', 'snow': 'seed count color speed',
    'stars': 'seed count color', 'fog': 'y h color a',
    'sun': 'x y r color glowColor glowR', 'moon': 'x y r color',
    'godRays': 'x y count angle spread len color a width',
    'lightCone': 'x y angle spread len color a', 'pool': 'x y rx ry color a',
    'lensStreak': 'x y w color a h', 'sparkle': 'x y s color a',
    'lightning': 'seed x1 y1 x2 y2 color w branches a jag',
    'speedLines': 'cx cy count color a inner seed', 'rings': 'x y count r0 r1 color a speed w',
    'skyline': 'seed x y w minH maxH color windowColor lit minW maxW',
    'hills': 'seed y amp color freq', 'clouds': 'seed count y h color a',
    'tree': 'x y s color', 'pine': 'x y s color',
    'lampPost': 'x y h color light on a',
    'windowFrame': 'x y w h cols rows frame bar blinds arch',
    'facade': 'x y w h color win dark cols rows lit seed door',
    'door': 'x y w h color open light', 'chair': 'x y s color', 'stool': 'x y s color',
    'counter': 'x y w h color top doors', 'screen': 'x y w h frame bg glowC a',
    'bed': 'x y w color frame pillow', 'clock': 'x y r face ink red speed',
    'floorLines': 'y0 y1 color spacing', 'crowd': 'seed x y w rows rowH size color flags wave cheer',
}
COLORES = {'color', 'glowColor', 'windowColor', 'light', 'frame', 'win', 'dark', 'top', 'bg', 'glowC', 'pillow', 'face', 'ink', 'red'}
POSITIVOS = {'w', 'h', 'r', 's', 'rx', 'ry', 'rMin', 'rMax', 'r0', 'r1', 'len', 'glowR', 'size', 'minH', 'maxH', 'minW', 'maxW', 'bar', 'rowH'}
CONTEOS = {'count', 'rows', 'cols', 'doors', 'ticks', 'branches', 'blinds'}


def _campo_fx(k):
    if k in COLORES:
        return COLOR
    if k in {'on', 'arch', 'door'}:
        return BOOL
    if k in CONTEOS:
        return ('numero', 0 if k in {'count', 'branches', 'blinds'} else 1, 300 if k == 'count' else 30)
    if k in {'a', 'lit', 'open', 'flags'}:
        return U
    if k in POSITIVOS:
        return ('numero', .01, 10000)
    return N


EFECTOS = {tipo: {k: _campo_fx(k) for k in campos.split()} for tipo, campos in FX.items()}
TIPOS3D = {
    'box': dict(w=POS, h=POS, d=POS), 'cyl': dict(rt=POS, rb=POS, h=POS),
    'cone': dict(r=POS, h=POS), 'sphere': dict(r=POS), 'plane': dict(w=POS, h=POS),
    'ground': dict(w=POS, d=POS, textura=('elegir', 'ninguna', 'planks', 'tiles')),
    'building': dict(w=POS, h=POS, d=POS, lit=U, seed=POS),
    'tree3D': dict(s=('numero', .1, 10)), 'pine3D': dict(s=('numero', .1, 10)),
    'crowd3D': dict(rows=('numero', 1, 15), perRow=('numero', 1, 80), width=('numero', 1, 100), seed=POS),
    'windowPane': dict(w=POS, h=POS, cols=('numero', 1, 20), rows=('numero', 1, 20), lit=BOOL, interior=BOOL),
    'shaft': dict(w=POS, len=POS, opacity=U),
    'figure3D': dict(personaje=('texto', 120)),
}


def validar(v, regla, ruta):
    tipo, *args = regla
    if tipo == 'tiempo':
        return tiempo(v, *args, ruta)
    elif tipo == 'numero':
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not args[0] <= v <= args[1]:
            raise ValueError(f'{ruta}: número fuera de {args[0]}–{args[1]}')
    elif tipo == 'texto':
        if not isinstance(v, str) or len(v) > args[0]:
            raise ValueError(f'{ruta}: texto demasiado largo o no válido')
    elif tipo == 'color':
        if not isinstance(v, str) or not re.fullmatch('#[a-fA-F0-9]{6}', v):
            raise ValueError(f'{ruta}: color #RRGGBB requerido')
    elif tipo == 'booleano':
        if type(v) is not bool:
            raise ValueError(f'{ruta}: booleano requerido')
    elif tipo == 'elegir':
        if v not in args or isinstance(v, bool):
            raise ValueError(f'{ruta}: elige {args}')
    elif tipo == 'lista':
        regla_item, minimo, maximo = args
        if not isinstance(v, list) or not minimo <= len(v) <= maximo:
            raise ValueError(f'{ruta}: lista de {minimo}–{maximo} elementos requerida')
        return [validar(item, regla_item, f'{ruta}[{i}]') for i, item in enumerate(v)]
    elif tipo == 'objeto':
        campos = args[0]
        if not isinstance(v, dict) or set(v) - campos.keys():
            raise ValueError(f'{ruta}: campos desconocidos; admite {", ".join(campos)}')
        return {k: validar(item, campos[k], ruta + '.' + k) for k, item in v.items()}
    return v


def lista_componentes(datos, catalogo, duracion, nombre, maximo):
    if not isinstance(datos, list) or len(datos) > maximo:
        raise ValueError(f'{nombre}: demasiados componentes')
    resultado = []
    for d in datos:
        if not isinstance(d, dict) or not isinstance(d.get('tipo'), str) or d['tipo'] not in catalogo or set(d) - {'tipo', 'inicio', 'fin', 'opciones', 'capa', 'desfase', 'duracion_total', 'neon'}:
            raise ValueError(f'{nombre}: componente desconocido')
        ruta = f'{nombre}[{len(resultado)}]'
        inicio = tiempo(d.get('inicio', 0), 0, duracion, ruta + '.inicio')
        fin = tiempo(d.get('fin', duracion), inicio + .001, duracion, ruta + '.fin')
        ops = validar(d.get('opciones', {}), opciones(**catalogo[d['tipo']]), nombre + '.' + d['tipo'])
        if 'neon' in d and nombre != 'graficos':
            raise ValueError('neon se aplica a graficos u objetos, no a efectos_visuales')
        for k in ('count', 'rows', 'cols', 'doors', 'ticks', 'branches', 'blinds', 'max', 'total', 'destacados', 'destacar', 'decimals', 'perRow', 'columnas', 'numero'):
            if k in ops and isinstance(ops[k], (int, float)) and int(ops[k]) != ops[k]:
                raise ValueError(f'{nombre}.{k}: entero requerido')
        if d['tipo'] in ('lista', 'barras', 'documento') and not ops.get('filas'):
            raise ValueError(f'{nombre}: {d["tipo"]} necesita filas')
        if d['tipo'] == 'documento' and ops.get('excluidos'):
            if ops.get('estilo') != 'neon' or any(not s.strip() for s in ops['excluidos']):
                raise ValueError('documento.excluidos necesita estilo neon y términos no vacíos')
        if d['tipo'] == 'comparacion' and not all(ops.get(k) for k in ('izquierda', 'derecha')):
            raise ValueError('comparacion necesita izquierda y derecha')
        if d['tipo'] == 'poblacion' and ops.get('destacados', 0) > ops.get('total', 100):
            raise ValueError('poblacion: destacados supera total')
        if d['tipo'] == 'poblacion':
            total = ops.get('total', 100)
            filas, columnas = ops.get('filas'), ops.get('columnas')
            if filas is not None and int(filas) != filas:
                raise ValueError('poblacion.filas: entero requerido')
            if filas and columnas and filas * columnas < total:
                raise ValueError('poblacion: filas y columnas no alojan total')
            indices = ops.get('indices_destacados', [])
            if any(int(i) != i or i >= total for i in indices) or len(set(indices)) != len(indices):
                raise ValueError('poblacion: índices repetidos, no enteros o fuera de total')
            if 'indices_destacados' in ops and 'destacados' in ops and len(indices) != ops['destacados']:
                raise ValueError('poblacion: destacados no coincide con índices')
            if ops.get('inicio_destacado', 0) > d.get('duracion_total', fin - inicio + d.get('desfase', 0)):
                raise ValueError('poblacion: inicio_destacado fuera del intervalo')
        if d['tipo'] == 'dial' and ops.get('valor', 0) > ops.get('maximo', 100):
            raise ValueError('dial: valor supera maximo')
        if d['tipo'] == 'interruptor' and ops.get('cambio', 0) > fin - inicio:
            raise ValueError('interruptor: cambio fuera del intervalo')
        componente = dict(tipo=d['tipo'], inicio=inicio, fin=fin, opciones=ops,
            capa=validar(d.get('capa', 'pantalla' if nombre == 'graficos' else 'fondo'),
                ('elegir', 'fondo', 'frente', 'pantalla'), nombre + '.capa'))
        if d['tipo'] == 'bocadillo':
            if not ops.get('personaje') or not ops.get('texto', '').strip():
                raise ValueError('bocadillo necesita personaje y texto no vacío')
            if componente['capa'] != 'pantalla':
                raise ValueError('bocadillo debe usar capa pantalla para seguir el rostro sin ampliar su texto')
        if d['tipo'] == 'capitulo':
            if 'numero' not in ops or not ops.get('titulo', '').strip() or componente['capa'] != 'pantalla':
                raise ValueError('capitulo necesita numero, titulo y capa pantalla')
        if 'neon' in d:
            componente['neon'] = validar(d['neon'], U, ruta + '.neon')
        if 'desfase' in d:
            componente['desfase'] = validar(d['desfase'], ('numero', 0, 600), nombre + '.desfase')
        if 'duracion_total' in d:
            componente['duracion_total'] = validar(d['duracion_total'], ('numero',
                componente.get('desfase', 0) + fin - inicio, 1200), nombre + '.duracion_total')
        resultado.append(componente)
    return resultado


def preparar_documentos_nuevos(datos, resolucion):
    """Composición óptica nueva; jamás se ejecuta al abrir planes históricos."""
    alto = 1920 * resolucion[1] / resolucion[0]
    for g in datos.get('graficos', []):
        if g['tipo'] != 'documento':
            continue
        o = g['opciones']
        o.setdefault('estilo', 'neon')
        if o['estilo'] != 'neon' or g['capa'] != 'pantalla':
            continue
        izquierda, derecha = (.32, .68) if o.get('excluidos') else (.23, .77)
        for objeto in datos.get('objetos', []):
            if objeto['tipo'] not in ('texto', 'etiqueta') or objeto.get('ancla'):
                continue
            if objeto['fin'] <= g['inicio'] or objeto['inicio'] >= g['fin']:
                continue
            actual = dict(objeto)
            for k in objeto['claves']:
                actual.update(k)
            x, y, s = actual['x'], actual['y'], actual['escala']
            if actual['opacidad'] <= .001:
                continue
            if (x+objeto['w']*s/3840 > izquierda and x-objeto['w']*s/3840 < derecha
                    and y+objeto['h']*s/(2*alto) > .12 and y-objeto['h']*s/(2*alto) < .88):
                raise ValueError(f'documento: el rótulo «{objeto["texto"]}» invade la hoja; '
                    'usa opciones.excluidos para términos fuera del documento, o colócalo fuera de sus márgenes')


def normalizar(datos, duracion, reparto):
    """Devuelve solo los campos nuevos presentes; ausencia conserva el dibujo antiguo."""
    resultado = {}
    if 'realizacion' in datos:
        r = validar(datos['realizacion'], opciones(
            encuadre=('elegir', *ENCUADRES), sujeto=('texto', 120), objetivo=('texto', 500),
            escenario=opciones(id=('texto', 120), tipo=('elegir', *ESCENARIOS), semilla=('numero', 0, 100000),
                atril=BOOL, publico=BOOL, atril_x=('numero', .15, .85), luz=COLOR),
            fondo=COLOR, paleta=('elegir', *PALETAS), desenfoque=('numero', 0, 20), profundidad=('numero', .1, 1),
            particulas=BOOL, malla=BOOL, desfase_ambiente=('numero', 0, 86400), escenografia_detallada=BOOL,
            tipografia=('elegir', 'redondeada', 'clasica'),
            expresiones_fieles=BOOL, cejas_fieles=BOOL, resplandor=BOOL,
            comparacion=opciones(color_izquierdo=COLOR,color_derecho=COLOR,color_separador=COLOR,
                corte=('elegir', 'quebrado', 'diagonal', 'vertical')),
            acabado=BOOL, color_fiel=BOOL, grano=('numero', 0, .08), vineta=('numero', 0, .7), bandas=('numero', 0, .12),
            foco=('lista', U, 2, 2)), 'realizacion')
        if r.get('sujeto') and r['sujeto'] not in reparto:
            raise ValueError('realizacion.sujeto debe pertenecer al reparto')
        if r.get('encuadre') in ('medio', 'primer_plano') and not r.get('sujeto'):
            raise ValueError('el encuadre requiere sujeto')
        if r.get('escenario') and not all(r['escenario'].get(k) for k in ('id', 'tipo')):
            raise ValueError('el escenario necesita id y tipo estables')
        resultado['realizacion'] = r
    for campo, catalogo, maximo in (('graficos', GRAFICOS, 12), ('efectos_visuales', EFECTOS, 40)):
        if campo in datos:
            resultado[campo] = lista_componentes(datos[campo], catalogo, duracion, campo, maximo)
    if 'realizacion' not in resultado and any(datos.get(k) for k in ('graficos', 'efectos_visuales', 'espacio3d')):
        resultado['realizacion'] = dict(encuadre='general' if datos.get('personajes') else 'grafico', acabado=True)
    for grafico in resultado.get('graficos', []):
        if grafico['tipo'] == 'bocadillo':
            ident = grafico['opciones']['personaje']
            if ident not in reparto or ident not in {p.get('id') for p in datos.get('personajes', [])}:
                raise ValueError('bocadillo: personaje debe estar presente en la escena y pertenecer al reparto')
        for ident in grafico['opciones'].get('personajes', []):
            if ident not in reparto:
                raise ValueError('endScreen: personaje desconocido')
    if 'espacio3d' in datos:
        d = datos['espacio3d']
        if not isinstance(d, dict) or set(d) - {'camara', 'objetos', 'bloom', 'niebla'}:
            raise ValueError('espacio3d no válido')
        camara = validar(d.get('camara', {}), opciones(modo=('elegir', 'orbit', 'dolly'), target=VECTOR,
            radius=('numero', 1, 100), height=('numero', .1, 50), desde=('numero', -7, 7), hasta=('numero', -7, 7),
            posicion=VECTOR, destino=VECTOR), 'espacio3d.camara')
        objetos = d.get('objetos', [])
        if not isinstance(objetos, list) or not 1 <= len(objetos) <= 40:
            raise ValueError('espacio3d necesita 1–40 objetos')
        salida = []
        for o in objetos:
            if not isinstance(o, dict) or o.get('tipo') not in TIPOS3D:
                raise ValueError('objeto 3D desconocido')
            item = validar(o, opciones(tipo=('elegir', *TIPOS3D), posicion=VECTOR, rotacion=VECTOR,
                color=COLOR, opciones=opciones(**TIPOS3D[o['tipo']])), 'espacio3d.objeto')
            for k in ('rows', 'cols', 'perRow'):
                valor = item.get('opciones', {}).get(k)
                if valor is not None and int(valor) != valor:
                    raise ValueError(f'espacio3d.{k}: entero requerido')
            if o['tipo'] == 'figure3D' and (o.get('opciones') or {}).get('personaje') not in reparto:
                raise ValueError('figure3D: personaje desconocido')
            salida.append(item)
        resultado['espacio3d'] = dict(camara=camara, objetos=salida,
            bloom=validar(d.get('bloom', .3), U, 'espacio3d.bloom'),
            niebla=validar(d.get('niebla', True), BOOL, 'espacio3d.niebla'))
    return resultado


def heredar_escenografia(escena, continuidad, renovar=False):
    """Al continuar un lugar, conserva su acabado y sus elementos si no se cambian explícitamente."""
    r = escena.get('realizacion') or {}
    actual = r.get('escenario') or {}
    if not actual.get('id'):
        return
    for clave in ('anterior', 'raiz'):
        referencia = ((continuidad or {}).get(clave) or {}).get('contenido') or {}
        previa = referencia.get('realizacion') or {}
        lugar = previa.get('escenario') or {}
        if lugar.get('id') == actual['id'] and lugar.get('tipo') == actual.get('tipo'):
            # La ausencia en una referencia histórica significa dibujo anterior, no un default retroactivo.
            if not renovar:
                r.setdefault('escenografia_detallada', previa.get('escenografia_detallada', False))
            for campo in ('semilla', 'atril', 'atril_x', 'publico', 'luz'):
                if campo in lugar:
                    actual.setdefault(campo, lugar[campo])
            return


def preparar_escenografia_nueva(escena, resolucion):
    """Pide corregir planos que ocultan la arquitectura o duplican el decorado."""
    r = escena.setdefault('realizacion', {})
    r.setdefault('encuadre', 'general')
    r.setdefault('escenografia_detallada', True)
    tipo = (r.get('escenario') or {}).get('tipo') or escena.get('decorado')
    if (not r['escenografia_detallada'] or tipo in (None, 'vacio') or 'comparacion' in r
            or r.get('encuadre') == 'dividido' or escena.get('espacio3d')):
        return escena
    alto = 1920 * resolucion[1] / resolucion[0]
    for objeto in escena['objetos']:
        if (objeto['tipo'] == 'rectangulo' and objeto['capa'] == 'fondo' and not objeto.get('ancla')
                and objeto['w'] * objeto['escala'] >= 1920 * .45 and objeto['h'] * objeto['escala'] >= alto * .55):
            raise ValueError('Un rectángulo opaco tapa la escenografía detallada. Usa realizacion.fondo '
                'para el color de la pared/telón y conserva su material, luces y profundidad; '
                'no reconstruyas el escenario con paneles planos.')
    if any(g['tipo'] == 'blueprint' for g in escena.get('graficos', [])):
        raise ValueError('blueprint tapa el escenario real. Para explicar dentro del decorado usa una '
            'pantalla o pizarra; para un gráfico a cuadro completo selecciona escenario vacio.')
    if tipo == 'teatro' and (r.get('escenario') or {}).get('publico') is not False:
        if any(e['tipo'] == 'crowd' for e in escena.get('efectos_visuales', [])):
            raise ValueError('El teatro ya incluye público de primer término: no dupliques filas de '
                'personajes diminutos. Usa escenario.publico:false solo si vas a componer un público propio.')
    return escena


def preparar_comparacion_nueva(escena, resolucion):
    """El escenario luminoso no sirve si el plan vuelve a cubrirlo con paneles planos.

    Se aplica al generar o editar el acabado luminoso, nunca a lectura/caché;
    los retoques de planos antiguos no reciben este acabado automáticamente.
    Las tarjetas, vectores y elementos explicativos conservan su geometría.
    """
    r = escena.get('realizacion') or {}
    if r.get('encuadre') == 'dividido' or any(g['tipo'] == 'comparacion' for g in escena.get('graficos', [])):
        r.setdefault('comparacion', {})
        r.setdefault('color_fiel', True)
        escena['realizacion'] = r
    alto = 1920 * resolucion[1] / resolucion[0]
    paneles = [o for o in escena['objetos'] if o['tipo'] == 'rectangulo' and o['capa'] == 'fondo'
        and not o.get('ancla') and o['w'] * o['escala'] >= 1920 * .45 and o['h'] * o['escala'] >= alto * .8]
    lados = {'izquierda' if o['x'] < .5 else 'derecha' for o in paneles}
    if lados == {'izquierda', 'derecha'} or ('comparacion' in r and paneles):
        raise ValueError('Comparación cubierta con paneles planos: usa realizacion.comparacion con luces '
            'fría/cálida y elimina los rectángulos de fondo. No tapes ese escenario con colores sólidos.')
    if 'comparacion' in r:
        for o in escena['objetos']:
            suelo = (o['tipo'] == 'rectangulo' and o['capa'] == 'fondo' and o['y'] > .75
                and o['w'] * o['escala'] >= 1920 * .45 and o['h'] * o['escala'] >= alto * .12)
            raya = o['tipo'] == 'linea' and abs(o['x'] - .5) < .04 and abs(o['w']) < 5 and abs(o['h']) >= alto * .75
            if suelo or raya:
                raise ValueError('La comparación ya incorpora suelo con reflejos y separador de neón: '
                    'elimina la franja plana de suelo y la línea central manual; configura corte y color_separador.')
        if any(g['tipo'] == 'blueprint' for g in escena.get('graficos', [])):
            raise ValueError('No tapes la comparación con blueprint: usa realizacion.malla si necesita una malla tenue.')
    return escena


def instruccion():
    return '''
== REALIZACIÓN EDITORIAL STICKMAN (contrato editorial-2) ==
CAPÍTULOS: escena.capitulo declara su número, título y estilo. escena.apertura_capitulo aparece
SOLO en la primera escena del capítulo. El motor añade una portada numerada durante duracion_s
segundos desde el inicio: número luminoso 01/02/03, línea fina, título grande y partículas.
Ese intervalo ya está dentro del audio; programa la actuación/diagramas principales DESPUÉS
de ese tiempo, con acciones que quepan en el resto, sin acelerar ni añadir segundos o palabras.
No dibujes otra portada, no cambies su título o numeración y no la arrastres a escenas siguientes
por continuidad. Desarrolla los puntos con distintos recursos visuales según su significado.
El componente manual capitulo usa opciones:{numero:1,titulo:"Tema",estilo:arctic|ember|mixto|sakura|retro}
y capa:pantalla. Las portadas no añaden narración ni diálogos.
Decide primero el objetivo explicativo. Alterna actuación contextual, primer plano emocional,
detalle, comparación simultánea, documento, diagrama y gráfico según la idea. No fuerces un actor
en un gráfico. No copies toda la voz como texto. Una relación dominante; revela por orden, conserva
el resultado legible. Metáforas simples con transformación clara, nunca símbolos anidados.
Incluye realizacion:{encuadre:general|conjunto|medio|primer_plano|detalle|grafico|dividido|cierre,
 sujeto:ID opcional,objetivo:"qué se entiende",escenario:{id:"lugar estable",tipo,semilla:7},
 desenfoque:0–20,profundidad:.1–1,acabado:true,color_fiel:true,grano:0–.08,vineta:0–.7,bandas:0–.12,fondo:"#RRGGBB" opcional,
  paleta:ember|arctic|sakura|retro,particulas:true,malla:true|false,desfase_ambiente:segundos,escenografia_detallada:true,tipografia:redondeada,expresiones_fieles:true}.
TIPOGRAFÍA DE REFERENCIA: todos los rótulos usan Fredoka 700, muy gruesa y redondeada,
con volumen suave y núcleo nítido. Usa objetos texto con fuente:110–160 para palabras protagonistas,
cajas w,h suficientes y neon:.25–.4 selectivo en azul hielo, naranja o blanco cálido.
El motor aplica realizacion.tipografia:redondeada; no imites letras con vectores ni uses sans-serif.
No reduzcas un título a una etiqueta pequeña: reserva ancho, alto y margen para sus acentos.
Si dos palabras se deslizan y se funden, anima sus claves x/opacidad con curvas suaves, retira las
originales al aparecer el rótulo final y mantenlo legible al cierre. Conserva el texto literal pedido.
El signo igual puede ser dos barras redondeadas doradas con halo, no un carácter fino de sistema.
En retoques locales conserva la tipografía anterior salvo petición de mejorar los rótulos.
ESCENARIOS CONSTRUIDOS: escenografia_detallada:true separa arquitectura de fondo, suelo y mobiliario
en el plano de los actores, y primer término. Describe materiales, volumen, luz y escala reconocibles,
no una etiqueta del lugar ni rectángulos genéricos. El suelo comparte cámara con los pies: coloca
actores en y~.85–.90; la pared puede quedar suavizada, pero el personaje y su apoyo quedan nítidos.
Teatro: telón de terciopelo burdeos con pliegues y sombras, cortinas laterales, tarima de madera
con juntas en perspectiva, candilejas, haz de foco cálido que sigue al protagonista y partículas
visibles en la luz. El público son siluetas de cabezas en primer término, no filas de muñecos minúsculos.
Conserva el borde del escenario y las candilejas en los planos generales; evita bandas o recortes
que eliminen toda esa profundidad salvo que la indicación pida ese encuadre.
En escenario puedes añadir atril:true solo si la acción lo necesita, atril_x:.61, publico:true|false,
y luz:"#RRGGBB" para una iluminación explícita. No añadas un atril si no interviene ni lo dupliques
con otro vector. En un teatro vacío usa publico:false. sujeto identifica a quien recibe el foco.
Salón/fiesta: ventana con profundidad, cuadros o sofá con cojines y costuras, suelo de madera y luz
de lámparas. Oficina: ventana, escritorio, pantalla y silla reconocibles. Laboratorio: azulejos,
banco metálico, cristalería y microscopio. Cocina: armarios con tiradores, encimera, fregadero y
frigorífico. Aula: pizarra enmarcada, bandeja y pupitres. Barrio/parque: distancia entre planos,
fachadas de materiales naturales, vegetación y caminos; no casas verdes con tejados eléctricos.
El motor construye ese decorado estable. No lo tapes con rectángulos opacos, un blueprint a
pantalla completa o una segunda multitud genérica; usa la utilería adicional para la acción concreta.
Conserva id/semilla y los elementos del escenario al continuar. Los detalles ambientales no inventan
hechos ni cifras y no sustituyen la acción principal. En un retoque local conserva el acabado
anterior salvo que se haya pedido mejorarlo. escenografia_detallada:false conserva el dibujo sencillo.
La continuidad también fija ese acabado: si raíz/anterior del mismo lugar no tiene el campo,
es un plano histórico y se continúa con escenografia_detallada:false, salvo petición de mejorarlo.
renovar_escenografia:true indica una regeneración explícita: usa el acabado detallado actual,
conservando lugar, actuación y elementos; la continuidad no obliga a copiar la simplificación antigua.
Conserva asimismo atril, público, posición y luz del escenario; no los omitas al pasar de frase.
Para retirar atril o público decláralos false explícitamente, en lugar de omitir el campo.
COMPARACIONES LUMINOSAS (referencia fría/cálida): en dividido y en comparaciones gráficas utiliza
realizacion.comparacion:{color_izquierdo:"#83d9f7",color_derecho:"#ff8d38",color_separador:"#ffdb83",corte:"quebrado"}.
También puedes usar esa realización con encuadre grafico para comparar objetos o magnitudes, sin inventar actores.
El motor construye fondos oscuros con degradados y focos radiales, suelo con reflejos, partículas frías
y motas cálidas, luz de contorno por lado y una unión quebrada/diagonal con halo de neón.
NO dibujes rectángulos azules/rojos opacos de media pantalla, una banda gris de suelo ni una raya
blanca central: tapan el acabado. No arrastres esos objetos desde una continuidad antigua.
Conserva identidades, acciones, posiciones y el significado de los colores; azul/rojo describe la
familia de luz, no obliga a rellenar cada mitad con pintura saturada. Para rojo explícito usa
color_derecho rojo, sin convertirlo en naranja. corte admite quebrado, diagonal o vertical luminoso.
Rótulos de comparación: usa graficos tipo comparacion con titulo breve, izquierda, derecha,
rasgos_izquierdos/rasgos_derechos (hasta 3 frases breves por lado) y detalles opcionales.
Tipografía grande Fredoka/Nunito, título dorado claro, etiquetas frías/cálidas y contorno fino legible;
evita texto diminuto disperso. Un título selectivo, no copiar toda la voz. Con rasgos, coloca actores
en x~.16/.84 y deja columnas de texto en .36/.64; sin rasgos pueden estar en .25/.75.
Los objetos vectoriales comparados admiten panel:izquierda|derecha, igual que los actores.
En objetos focales como termómetros usa neon:.2–.35 y color del halo coherente con su lado;
conserva el vidrio, las marcas y el líquido nítidos. No hagas luminosos todos los materiales.
En un retoque local conserva el acabado original salvo que se haya pedido cambiarlo.
ACABADO DE REFERENCIA: incluye partículas de fondo flotantes, pequeñas, escasas, suaves y lentas.
particulas:true las dibuja detrás de actores y textos; no son lluvia, nieve ni confeti. No dupliques
dust si ya utilizas este ambiente. Mantén profundidad con fondo suave, luz de contorno y foco claro.
En explicaciones azuladas/Arctic Glass usa malla:true: cuadrícula fina y tenuemente visible sobre
fondo azul oscuro, nunca por delante de caras ni en un salón realista. No hace falta añadir blueprint:
malla no rellena el lienzo ni tapa el fondo elegido. particulas:false/malla:false respetan una petición sin esos efectos.
desfase_ambiente conserva el reloj global de las partículas al continuar la secuencia.
PATRÓN DE COLOR: elige una familia coherente con el encargo y mantenla durante la secuencia.
Respeta el acabado elegido si es ember/arctic/sakura/retro; si es editorial, elige por el tono:
Ember Forge (drama: negro, rojo intenso, cobre y naranja); Arctic Glass (ciencia/tecnología:
azules fríos, turquesa y blanco hielo, con amarillo cálido de contraste);
Sakura Bloom (emoción: rosa, violeta, ciruela y melocotón);
Retro Print (historia: verde azulado apagado, mostaza, sepia y naranja).
Paletas de referencia, compartidas con el render: ''' + json.dumps(PALETAS, ensure_ascii=False) + '''.
Estas paletas dirigen fondos, diagramas, palabras clave y acentos luminosos, NO sustituyen
los materiales reconocibles de casas, muebles o personas. No mezcles todos los acentos a la vez.
Para explicaciones gráficas parte de fondo oscuro profundo, texto secundario blanco cálido/hielo,
palabra clave grande en el acento y diagramas de líneas finas con puntos claros y jerarquía visual.
En Arctic Glass incorpora el amarillo cálido #ffcb52 (detalle) para títulos, cifras clave,
etiquetas, umbrales o el elemento que explica la conclusión. Mantén ejes, estructura y datos
de contexto en azul/turquesa sobre fondo azul oscuro, y el texto auxiliar blanco hielo.
El amarillo puede tener neon:.2–.4 en el foco; no conviertas todo el diagrama en amarillo.
La malla tenue forma parte del fondo de las explicaciones azuladas; no la extiendas a escenas cotidianas.
NEÓN SELECTIVO: realizacion.resplandor:true ilumina rótulos, gráficos y acentos de color nuevos.
Para focos luminosos visibles añade neon:.6–.85 a un gráfico o a un objeto destacado (texto, vector o silueta).
Reserva neon:.2–.4 para un efecto deliberadamente sutil, no para una luz protagonista.
Ejemplo {tipo:"bigLine",inicio:0,fin:duracion,capa:"pantalla",neon:.65,
opciones:{str:"GENES",color:"#76ccff",size:120}}. Para siluetas sirve lineFigure o un objeto vector.
El halo es una copia suavemente desenfocada detrás del dibujo nítido, no un desenfoque del elemento.
Úsalo en una palabra clave o silueta focal, no en párrafos, todos los objetos, piel ni mobiliario.
Limita el efecto normalmente a 1–3 elementos focales; agrupa una silueta compuesta en un vector,
en lugar de añadir un halo independiente a cada pieza. badge alinea a la derecha de su x;
reserva columnas separadas para ilustración y palabras, sin invadir el diagrama con los rótulos.
En poblacion usa neon_destacados:.2–.4 para iluminar SOLO las figuras seleccionadas, no un halo
en el grupo completo. Mantén las demás azul grisáceo/atenuadas. Las cantidades proceden del relato.
neon:0 desactiva el halo; no se añade por defecto al material histórico. Mantén contraste y contornos.
Escenarios disponibles: ''' + ', '.join(ESCENARIOS) + '''.
Reutiliza el mismo escenario/id/semilla en reapariciones, consultando escenarios_video y continuidad_bloque.
Cada escenario ya dibuja mobiliario y luces; no lo tapes con rectángulos. Adapta ambiente a la hora.
medio/primer_plano requieren sujeto presente. El motor encuadra su cara automáticamente: escribe
pies y escala normales, no agrandes el rig. detalle admite foco:[x,y] normalizado para centrar la cámara.
Para una frase hablada o un pensamiento significativo alterna primer_plano con la actuación general:
realizacion:{encuadre:"primer_plano",sujeto:"ID",desenfoque:6,...}. El rostro es el foco, no un icono flotante.
Añade graficos:[{tipo:"bocadillo",capa:"pantalla",inicio:0,fin:duracion,opciones:{personaje:"ID",
modo:"dialogo"|"pensamiento",texto:"Frase breve pertinente"}}]. El motor coloca el recuadro en un lateral
y une la cola al rostro siguiendo cámara y movimiento. Diálogo lleva cola triangular; pensamiento,
una cadena de círculos. Fondo claro y texto oscuro, sin tapar ojos o boca. No uses bubble genérico
para atribuir palabras: bocadillo conoce al personaje. Puedes ajustar x,y,w,h,size,color,tinta en unidades lógicas.
No inventes una cita ni un pensamiento como hecho: usa palabras pronunciadas por ese personaje,
un pensamiento explícito del guion o una idea ilustrativa inequívoca, nunca diálogo del narrador atribuido a otro.
Los figurantes usan rol:figurante y escala reducida; no compiten con el protagonista.
dividido: requiere exactamente dos protagonistas de IDs distintos del reparto, x~.25/.75.
En personajes, escribe uno con rol:"principal",panel:"izquierda" y el otro con rol:"principal",panel:"derecha".
No pongas panel en realizacion ni graficos. Los extras reales llevan rol:"figurante". No dupliques IDs
ni inventes actores para llenar paneles. Con un solo protagonista usa conjunto/medio; para comparar
objetos o magnitudes usa encuadre grafico y el componente comparacion/barras, sin forzar personajes.
graficos:[{tipo,inicio:0,fin:duracion,capa:"pantalla",opciones:{...}}]. Los grafismos NO se mueven con
la cámara. En un gráfico completo usa decorado vacio y personajes:[]; blueprint como fondo.
Usa lista/barras/documento/comparacion/cronologia/poblacion/dial/interruptor antes que inventar layouts.
Fidelidad: las cantidades, colores, posiciones y transformaciones EXPLÍCITAS del prompt son obligatorias.
escena.colores contiene la dirección cromática ya decidida al describir esa frase: respétala junto
con descripcion_visual. Asigna esas tintas a materiales, objetos y gráficos; no vuelvas a elegir
otra paleta ni sustituyas el amarillo cálido de un destacado por azul al interpretar Arctic Glass.
El estilo completa lo no especificado; nunca sustituye gris por verde ni recolorea un destacado narrativo.
Usa color_fiel:true para evitar que la gradación tiña los colores de la escena. No añade una paleta nueva:
especifica los colores pedidos en los objetos y gráficos. La malla de una explicación azulada es
tenue y subordinada al contenido; evita otras cuadrículas ornamentales y la duplicación con blueprint.
poblacion admite filas/columnas, color_base, color para destacados, indices_destacados (índices desde 0,
por filas de izquierda a derecha), atenuacion (opacidad final del resto), inicio_destacado y duracion_destacado.
Ejemplo: cien figuras grises en diez filas, una roja en la tercera fila:
{total:100,filas:10,columnas:10,color_base:"#888888",color:"#9b2020",indices_destacados:[20],
atenuacion:.3,inicio_destacado:.5,duracion_destacado:.6}. Todas son visibles desde el primer frame;
el destacado y la atenuación progresan después. No inventes otra disposición por estética.
Los rótulos explicativos van en graficos con capa:pantalla y colores legibles sobre su fondo;
los objetos texto conservan cámara/anclas, pero se dibujan después del acabado con protección de contraste.
Las cantidades, escalas y etiquetas deben proceder del relato: no inventes cifras como evidencia.
efectos_visuales:[{tipo,inicio,fin,capa:fondo|frente|pantalla,opciones:{...}}] da acceso a TODO fx2d:
atmósfera, luces, mobiliario, ventanas, público y decorados. Usa solo efectos con función visual.
Opciones gráficas y efectos están en unidades LÓGICAS (ancho 1920, alto indicado), NO normalizadas.
Los intervalos siempre son segundos locales de esta escena. Las opciones omitidas usan el kit.
Al continuar un mismo componente en otra frase, conserva opciones/geometría y añade desfase:segundos
ya transcurridos y duracion_total:duración de toda la secuencia; así no reinicia entradas, trazos ni ciclos.
El desfase también se admite en efectos_visuales para mantener lluvia, público y atmósfera continuos.
Esquemas de opciones (numero,min,max; texto,longitud; elegir,valores; lista,esquema,min,max; objeto,campos):
''' + json.dumps(dict(graficos=GRAFICOS, efectos_visuales=EFECTOS), ensure_ascii=False) + '''
Texto editorial: titleCard líneas breves; callout para señalar; documento para evidencia; lista por etapas.
compareBars usa v en 0–1; barras también. No uses un porcentaje sin base. No dejes valores oscilando.
La geometría libre y sus partes siguen disponibles en utileria. Para cámara 3D solo cuando aporta
espacio (establecimiento, órbita, recorrido), espacio3d:{bloom:.3,niebla:true,camara:{modo:orbit|dolly,
target:[0,1,0],radius:8,height:3,desde:-.4,hasta:.4,posicion:[0,3,8],destino:[2,3,6]},
objetos:[{tipo,posicion:[x,y,z],rotacion:[rx,ry,rz],color:"#RRGGBB",opciones:{...}}]}.
3D usa metros/radianes, personajes figure3D referencian un ID presente en personajes; sus poses vienen del actor normal.
El elenco de endScreen también debe estar presente en personajes (rol figurante o cierre para tamaño pequeño).
Actores admiten actuacion:{mirada:[-1..1,-1..1],mezcla_pose:.05–1,respiracion:0–2,
atrezzo:phone|ball|paper|cup|paddle|pointer|tablet|flashlight,mano:F|B,gafas:none|glasses|sunglasses,
guantes:"#RRGGBB",pantalon:"#RRGGBB",rastro:0–5}. No añadas atrezzo sin función narrativa.
Las claves de actor/objeto/cámara admiten curva:linear|in|out|inOut|sine|outBack|outElastic;
la curva se aplica al trayecto que termina en esa clave. No uses rebotes en datos medidos.
El objeto balon usa el balón original del rig, con w/h y claves rot para girar.
No pidas 3D para gráficos o gestos emocionales. Tipos y opciones: ''' + json.dumps(TIPOS3D) + '\n'
