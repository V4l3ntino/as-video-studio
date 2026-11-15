"""Contrato editorial del kit: solo datos acotados, nunca código del proveedor.

Opcional en planes históricos. Se conecta al director y al renderer Stickman;
los nombres de componentes corresponden a las funciones originales del kit.
"""
import json
import math
import re
from pasos.tiempos_stickman import tiempo

ENCUADRES = ('general', 'conjunto', 'medio', 'primer_plano', 'detalle', 'grafico', 'dividido', 'cierre')
ESCENARIOS = ('vacio', 'fiesta', 'salon', 'oficina', 'laboratorio', 'barrio', 'parque', 'cocina', 'teatro', 'aula')

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
    'endScreen': dict(question=TEXTO, personajes=('lista', ('texto', 120), 0, 8), suscribir=('texto', 40)),
    'captions': dict(y=N, size=('numero', 28, 100), max=('numero', 1, 8), color=COLOR, hi=COLOR),
    # Componentes semánticos del adaptador, construidos con el dibujo del kit.
    'lista': dict(titulo=TEXTO, filas=('lista', TEXTO, 1, 6), intervalo=('numero', .15, 10),
                  color=COLOR, x=N, y=N, w=POS),
    'barras': dict(titulo=TEXTO, filas=('lista', FILA, 1, 5), color=COLOR),
    'poblacion': dict(titulo=TEXTO, total=('numero', 1, 300), destacados=('numero', 0, 300), color=COLOR,
        filas=('numero', 1, 300), columnas=('numero', 1, 300), color_base=COLOR,
        indices_destacados=('lista', ('numero', 0, 299), 0, 300), atenuacion=U,
        inicio_destacado=('numero', 0, 120), duracion_destacado=('numero', .01, 120)),
    'cronologia': dict(titulo=TEXTO, etiquetas=('lista', ('texto', 60), 2, 8), color=COLOR),
    'documento': dict(titulo=TEXTO, filas=('lista', TEXTO, 1, 8), destacar=('numero', 0, 7), sello=('texto', 40)),
    'comparacion': dict(izquierda=TEXTO, derecha=TEXTO, detalle_izquierdo=TEXTO, detalle_derecho=TEXTO),
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
        if not isinstance(d, dict) or not isinstance(d.get('tipo'), str) or d['tipo'] not in catalogo or set(d) - {'tipo', 'inicio', 'fin', 'opciones', 'capa', 'desfase', 'duracion_total'}:
            raise ValueError(f'{nombre}: componente desconocido')
        ruta = f'{nombre}[{len(resultado)}]'
        inicio = tiempo(d.get('inicio', 0), 0, duracion, ruta + '.inicio')
        fin = tiempo(d.get('fin', duracion), inicio + .001, duracion, ruta + '.fin')
        ops = validar(d.get('opciones', {}), opciones(**catalogo[d['tipo']]), nombre + '.' + d['tipo'])
        for k in ('count', 'rows', 'cols', 'doors', 'ticks', 'branches', 'blinds', 'max', 'total', 'destacados', 'destacar', 'decimals', 'perRow', 'columnas'):
            if k in ops and isinstance(ops[k], (int, float)) and int(ops[k]) != ops[k]:
                raise ValueError(f'{nombre}.{k}: entero requerido')
        if d['tipo'] in ('lista', 'barras', 'documento') and not ops.get('filas'):
            raise ValueError(f'{nombre}: {d["tipo"]} necesita filas')
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
        if 'desfase' in d:
            componente['desfase'] = validar(d['desfase'], ('numero', 0, 600), nombre + '.desfase')
        if 'duracion_total' in d:
            componente['duracion_total'] = validar(d['duracion_total'], ('numero',
                componente.get('desfase', 0) + fin - inicio, 1200), nombre + '.duracion_total')
        resultado.append(componente)
    return resultado


def normalizar(datos, duracion, reparto):
    """Devuelve solo los campos nuevos presentes; ausencia conserva el dibujo antiguo."""
    resultado = {}
    if 'realizacion' in datos:
        r = validar(datos['realizacion'], opciones(
            encuadre=('elegir', *ENCUADRES), sujeto=('texto', 120), objetivo=('texto', 500),
            escenario=opciones(id=('texto', 120), tipo=('elegir', *ESCENARIOS), semilla=('numero', 0, 100000)),
            fondo=COLOR, desenfoque=('numero', 0, 20), profundidad=('numero', .1, 1),
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


def instruccion():
    return '''
== REALIZACIÓN EDITORIAL STICKMAN (contrato editorial-2) ==
Decide primero el objetivo explicativo. Alterna actuación contextual, primer plano emocional,
detalle, comparación simultánea, documento, diagrama y gráfico según la idea. No fuerces un actor
en un gráfico. No copies toda la voz como texto. Una relación dominante; revela por orden, conserva
el resultado legible. Metáforas simples con transformación clara, nunca símbolos anidados.
Incluye realizacion:{encuadre:general|conjunto|medio|primer_plano|detalle|grafico|dividido|cierre,
sujeto:ID opcional,objetivo:"qué se entiende",escenario:{id:"lugar estable",tipo,semilla:7},
 desenfoque:0–20,profundidad:.1–1,acabado:true,color_fiel:true,grano:0–.08,vineta:0–.7,bandas:0–.12,fondo:"#RRGGBB" opcional}.
Escenarios disponibles: ''' + ', '.join(ESCENARIOS) + '''.
Reutiliza el mismo escenario/id/semilla en reapariciones, consultando escenarios_video y continuidad_bloque.
Cada escenario ya dibuja mobiliario y luces; no lo tapes con rectángulos. Adapta ambiente a la hora.
medio/primer_plano requieren sujeto presente. El motor encuadra su cara automáticamente: escribe
pies y escala normales, no agrandes el rig. detalle admite foco:[x,y] normalizado para centrar la cámara.
Los figurantes usan rol:figurante y escala reducida; no compiten con el protagonista.
dividido: usa dos protagonistas, x~.25/.75, cada uno con panel:izquierda|derecha. No dupliques IDs.
graficos:[{tipo,inicio:0,fin:duracion,capa:"pantalla",opciones:{...}}]. Los grafismos NO se mueven con
la cámara. En un gráfico completo usa decorado vacio y personajes:[]; blueprint como fondo.
Usa lista/barras/documento/comparacion/cronologia/poblacion/dial/interruptor antes que inventar layouts.
Fidelidad: las cantidades, colores, posiciones y transformaciones EXPLÍCITAS del prompt son obligatorias.
El estilo completa lo no especificado; nunca sustituye gris por verde ni recolorea un destacado narrativo.
Usa color_fiel:true para evitar que la gradación tiña los colores de la escena. No añade una paleta nueva:
especifica los colores pedidos en los objetos y gráficos. No añadas blueprint/cuadrícula salvo que se pida.
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
