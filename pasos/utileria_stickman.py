"""Catálogo compartido e instantáneas portátiles de dibujos vectoriales Stickman.

Solo contiene geometría declarativa. Las fichas son inmutables por contenido;
añadir utilería no cambia las firmas de escenas que ya se han generado.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import unicodedata

from nucleo.proyecto import escribir_json, lock_de

PALETA = ('principal', 'secundario', 'contorno', 'claro', 'oscuro')
CARPETA = 'utileria_stickman'


def carpeta_catalogo():
    if os.environ.get('ESTUDIO_UTILERIA_STICKMAN'):
        return Path(os.environ['ESTUDIO_UTILERIA_STICKMAN']).resolve()
    # Los servicios instalados protegen HOME y ya desvían banco/proyectos a
    # datos/. Usar ese volumen sin exigir cambiar su fichero de entorno antiguo.
    programa = Path(__file__).resolve().parents[1]
    for variable in ('ESTUDIO_BANCO', 'ESTUDIO_PROYECTOS'):
        if os.environ.get(variable):
            candidata = Path(os.environ[variable]).resolve().parent / CARPETA
            if not candidata.is_relative_to(programa):
                return candidata
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local')
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    return base / 'as-video-studio' / CARPETA


def _texto(v, maximo):
    if not isinstance(v, str) or not v.strip() or len(v) > maximo:
        raise ValueError('texto de utilería no válido')
    return v.strip()


def concepto(v):
    v = unicodedata.normalize('NFKD', _texto(v, 120)).encode('ascii', 'ignore').decode().lower()
    v = re.sub(r'[^a-z0-9]+', '-', v).strip('-')
    if not v:
        raise ValueError('el concepto de utilería debe tener letras o números')
    return v


def _numero(v, minimo, maximo):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not minimo <= v <= maximo:
        raise ValueError(f'coordenada de utilería fuera de {minimo}–{maximo}')
    return v


def _color(v):
    if v is None or (isinstance(v, str) and (v in {'$' + c for c in PALETA} or re.fullmatch('#[a-fA-F0-9]{6}', v))):
        return v
    raise ValueError('color de utilería: #RRGGBB, $principal/$secundario/$contorno/$claro/$oscuro o null')


def claves(datos, duracion):
    if not isinstance(datos, list) or len(datos) > 80:
        raise ValueError('claves de parte no válidas')
    salida = []
    for k in datos:
        if not isinstance(k, dict) or set(k) - {'t', 'x', 'y', 'rot', 'escala', 'opacidad'}:
            raise ValueError('una parte solo anima t,x,y,rot,escala,opacidad')
        f = dict(t=_numero(k.get('t'), 0, duracion))
        for campo, limites in dict(x=(-2000, 2000), y=(-2000, 2000), rot=(-1000, 1000), escala=(.01, 10), opacidad=(0, 1)).items():
            if campo in k:
                f[campo] = _numero(k[campo], *limites)
        salida.append(f)
    salida.sort(key=lambda k: k['t'])
    if len({k['t'] for k in salida}) != len(salida):
        raise ValueError('las claves de una parte no pueden repetir tiempo')
    return salida


def definicion(datos):
    if not isinstance(datos, dict) or set(datos) - {'id', 'concepto', 'nombre', 'descripcion', 'etiquetas', 'ancho', 'alto', 'partes'}:
        raise ValueError('definición vectorial de utilería no válida')
    ancho = _numero(datos.get('ancho', 1000), 1, 2000)
    alto = _numero(datos.get('alto', 1000), 1, 2000)
    etiquetas = datos.get('etiquetas', [])
    partes = datos.get('partes')
    if not isinstance(etiquetas, list) or len(etiquetas) > 20:
        raise ValueError('usa hasta 20 etiquetas para encontrar la utilería')
    if not isinstance(partes, list) or not 1 <= len(partes) <= 40:
        raise ValueError('la utilería debe tener de 1 a 40 partes')
    salida = dict(concepto=concepto(datos.get('concepto')), nombre=_texto(datos.get('nombre'), 120),
        descripcion=_texto(datos.get('descripcion'), 1000), etiquetas=sorted(set(_texto(v, 80) for v in etiquetas)),
        ancho=ancho, alto=alto, partes=[])
    total_formas = total_comandos = 0
    ids = set()
    for p in partes:
        if not isinstance(p, dict) or set(p) - {'id', 'pivote', 'formas', 'animacion'}:
            raise ValueError('parte vectorial no válida')
        ident = _texto(p.get('id'), 60)
        if not re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]*', ident) or ident in ids:
            raise ValueError('cada parte necesita un id único de letras, números y guiones')
        ids.add(ident)
        pivote = p.get('pivote', [ancho / 2, alto / 2])
        if not isinstance(pivote, list) or len(pivote) != 2:
            raise ValueError('pivote debe ser [x,y]')
        pivote = [_numero(pivote[0], 0, ancho), _numero(pivote[1], 0, alto)]
        formas = p.get('formas')
        if not isinstance(formas, list) or not 1 <= len(formas) <= 80:
            raise ValueError('cada parte necesita de 1 a 80 formas')
        parte = dict(id=ident, pivote=pivote, formas=[])
        for f in formas:
            if not isinstance(f, dict) or set(f) - {'tipo', 'comandos', 'x', 'y', 'w', 'h', 'radio', 'relleno', 'trazo', 'grosor'}:
                raise ValueError('forma vectorial no válida')
            tipo = f.get('tipo')
            if tipo not in ('trazo', 'elipse', 'rectangulo'):
                raise ValueError('forma: trazo, elipse o rectangulo')
            forma = dict(tipo=tipo, relleno=_color(f.get('relleno', '$principal')),
                trazo=_color(f.get('trazo')), grosor=_numero(f.get('grosor', 3), .1, 100))
            if forma['relleno'] is None and forma['trazo'] is None:
                raise ValueError('una forma necesita relleno o trazo visible')
            if tipo == 'trazo':
                comandos = f.get('comandos')
                if not isinstance(comandos, list) or not 2 <= len(comandos) <= 200:
                    raise ValueError('trazo necesita de 2 a 200 comandos M/L/Q/C/Z')
                forma['comandos'] = []
                for i, cmd in enumerate(comandos):
                    if not isinstance(cmd, list) or not cmd or not isinstance(cmd[0], str) or cmd[0] not in ('M', 'L', 'Q', 'C', 'Z'):
                        raise ValueError('comando de dibujo no válido')
                    if len(cmd) != {'M': 3, 'L': 3, 'Q': 5, 'C': 7, 'Z': 1}[cmd[0]] or (i == 0 and cmd[0] != 'M'):
                        raise ValueError('trazo debe empezar en M y respetar las coordenadas de cada comando')
                    forma['comandos'].append([cmd[0]] + [_numero(n, 0, ancho if j % 2 == 0 else alto) for j, n in enumerate(cmd[1:])])
                total_comandos += len(comandos)
            else:
                x = _numero(f.get('x'), 0, ancho)
                y = _numero(f.get('y'), 0, alto)
                w = _numero(f.get('w'), .1, ancho)
                h = _numero(f.get('h'), .1, alto)
                if x + w > ancho or y + h > alto:
                    raise ValueError('forma fuera de su caja vectorial: x+w<=ancho, y+h<=alto')
                forma.update(x=x, y=y, w=w, h=h, radio=_numero(f.get('radio', 0), 0, min(w, h) / 2))
            parte['formas'].append(forma)
            total_formas += 1
        if p.get('animacion') is not None:
            a = p['animacion']
            if not isinstance(a, dict) or set(a) - {'duracion', 'claves'}:
                raise ValueError('animación de parte no válida')
            dur = _numero(a.get('duracion'), .1, 30)
            parte['animacion'] = dict(duracion=dur, claves=claves(a.get('claves'), dur))
        salida['partes'].append(parte)
    if total_formas > 240 or total_comandos > 4000:
        raise ValueError('utilería demasiado compleja: máximo 240 formas y 4000 comandos')
    ident = hashlib.sha256(json.dumps(salida, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if datos.get('id') is not None and datos['id'] != ident:
        raise ValueError('la huella de la utilería no coincide con su contenido')
    return dict(salida, id=ident)


def _leer(carpeta):
    salida = {}
    for p in sorted(carpeta.glob('*.json')):
        if not re.fullmatch('[a-f0-9]{64}', p.stem):
            continue
        try:
            d = definicion(json.loads(p.read_text(encoding='utf-8')))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f'utilería dañada en {p.name}: {exc}') from exc
        if d['id'] != p.stem:
            raise ValueError('el nombre de ficha no coincide con la huella de utilería: ' + p.name)
        salida[d['id']] = d
    return salida


def catalogo(proyecto=None):
    salida = _leer(carpeta_catalogo())
    if proyecto is not None:
        bases = [Path(proyecto.ruta_trabajo('assets', crear=False))]
        if proyecto.version_activa('assets') is not None:
            bases.insert(0, Path(proyecto.ruta_paso('assets')))
        for base in bases:
            salida.update(_leer(base / CARPETA))
    return salida


def preparar(nuevas, disponibles):
    if not isinstance(nuevas, dict) or len(nuevas) > 40:
        raise ValueError('utileria debe ser un mapa con hasta 40 definiciones vectoriales')
    recursos = dict(disponibles)
    alias = {}
    for d in recursos.values():
        alias.setdefault(d['concepto'], d['id'])
    for ref, datos in nuevas.items():
        _texto(ref, 120)
        d = definicion(datos)
        # Reutilizar el concepto conocido incluso si el modelo lo vuelve a dibujar.
        ident = d['id'] if ref == d['id'] else alias.get(d['concepto'], d['id'])
        if ident == d['id']:
            recursos[ident] = d
        alias[ref] = ident
        alias[d['concepto']] = ident
    return recursos, alias


def resolver(ref, recursos, alias):
    ref = _texto(ref, 120)
    ident = ref if ref in recursos else alias.get(ref) or alias.get(concepto(ref))
    if ident not in recursos:
        raise ValueError(f'falta utilería «{ref}»: crea su definición en utileria o elige un recurso del catálogo')
    return ident


def indice(recursos, contexto, maximo=100):
    # El contexto completo también sirve para buscar una ficha en catálogos grandes.
    normal = unicodedata.normalize('NFKD', str(contexto)).encode('ascii', 'ignore').decode().lower()
    palabras = set(re.findall(r'[a-z0-9]{3,}', normal))
    def relevancia(d):
        tokens = set(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', ' '.join([d['concepto'], d['nombre'], *d['etiquetas']])).encode('ascii', 'ignore').decode().lower()))
        return (-len(palabras & tokens), d['concepto'], d['id'])
    return [dict(id=d['id'], concepto=d['concepto'], nombre=d['nombre'], descripcion=d['descripcion'],
        etiquetas=d['etiquetas'], ancho=d['ancho'], alto=d['alto'], partes=[p['id'] for p in d['partes']])
        for d in sorted(recursos.values(), key=relevancia)[:maximo]]


def guardar(recursos, trabajo=None):
    """Publicación atómica e inmutable, serializada también entre procesos."""
    validados = {ident: definicion(d) for ident, d in recursos.items()}
    if any(ident != d['id'] for ident, d in validados.items()):
        raise ValueError('referencia de utilería distinta de su huella')
    if not validados:
        return
    carpeta = carpeta_catalogo()
    with lock_de(str(carpeta / '_catalogo')):
        for ident, d in validados.items():
            destino = carpeta / (ident + '.json')
            if not destino.exists():
                escribir_json(str(destino), d)
            if trabajo is not None:
                copia = Path(trabajo) / CARPETA / (ident + '.json')
                if not copia.exists():
                    escribir_json(str(copia), d)


CONTRATO = '''
UTILERÍA EXTENSIBLE Y REUTILIZABLE:
Consulta catalogo_utileria y reutiliza sus recursos para cualquier temática. Un objeto compuesto
se instancia con {tipo:"vector",recurso:"ID o concepto",x:.5,y:.4,w:400,h:200,...}; admite las mismas
anclas, claves, opacidad y capas que los demás objetos. Se ajusta a w,h sin deformarse.
Admite paleta:{principal:"#RRGGBB",secundario:"#RRGGBB",...} para personalizar sus colores;
por defecto usa el estilo del vídeo, sin modificar la ficha reutilizable.
Si el concepto necesario NO existe, dibújalo tú y añade en la RAÍZ del JSON:
utileria:{"avion":{concepto:"avion",nombre:"Avión",descripcion:"Avión de pasajeros visto de lado",
etiquetas:["avión","airplane","transporte","viaje"],ancho:1000,alto:500,partes:[
{id:"fuselaje",pivote:[500,250],formas:[{tipo:"trazo",comandos:[["M",100,220],["L",850,220],
["Q",980,240,900,280],["L",100,280],["Z"]],relleno:"$claro",trazo:"$oscuro",grosor:8}]}]}}
Ese fragmento solo ilustra el contrato, NO es un avión completo: crea silueta, alas, cola,
ventanas y detalles distintivos para que el objeto se reconozca sin etiquetas.
No inventes utilería innecesaria ni dibujes de nuevo conceptos disponibles. Puedes referenciar
un concepto por nombre aunque no aparezca en el índice resumido; si falta se te pedirá definirlo.
Las definiciones no contienen posiciones de escena, tiempos de narración, nombres de personajes
ni texto temático: deben servir para otros vídeos. Preferir colores de paleta adaptables al estilo.
Cada definición tiene hasta 40 partes; cada parte agrupa formas con un pivote [x,y] local.
Formas: trazo (M x y; L x y; Q cx cy x y; C c1x c1y c2x c2y x y; Z),
rectangulo o elipse (x,y esquina superior izquierda,w,h,radio opcional para rectangulo).
Coordenadas y controles dentro de ancho/alto (hasta 2000), margen para el contorno.
Relleno/trazo: #RRGGBB, null o $principal,$secundario,$contorno,$claro,$oscuro.
Cada parte admite animacion:{duracion:1,claves:[{t:0,rot:0},{t:1,rot:6.283185}]} que se repite
desde la aparición del objeto. Claves de partes: t,x,y en unidades locales,rot en radianes,
escala,opacidad. Agrupa piezas que se mueven juntas en la misma parte.
Para acciones específicas añade al OBJETO partes:[{id:"ala",claves:[{t:0,rot:0},{t:2,rot:.3}]}];
estos tiempos son locales a la escena, sustituyen solo los campos indicados de la animación base.
Las definiciones válidas usadas se guardarán automáticamente en el catálogo compartido.
'''
