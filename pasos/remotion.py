"""Plantillas Remotion independientes: contratos, biblioteca y recursos locales."""
import copy
import base64
import mimetypes
import hashlib
import io
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid

from nucleo.proyecto import escribir_json, leer_json
from pasos import animaciones

MOTOR = Path(__file__).resolve().parents[1] / 'motores' / 'remotion'
VERSION = '3-remotion-4.0.484'
_LOCK = threading.RLock()
_LOCK_BIBLIOTECA = threading.RLock()


def huella(datos):
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validar_plantilla(datos):
    if not isinstance(datos, dict):
        raise ValueError('la plantilla debe ser un objeto')
    codigo = datos.get('codigo')
    if not isinstance(codigo, str) or not codigo.strip() or len(codigo) > 200_000:
        raise ValueError('introduce un componente React de hasta 200.000 caracteres con export default')
    nombre = datos.get('nombre', 'Nueva plantilla')
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 120:
        raise ValueError('el nombre debe tener entre 1 y 120 caracteres')
    limpio = dict(nombre=nombre.strip(), descripcion=str(datos.get('descripcion', ''))[:1000], codigo=codigo)
    for k, defecto, minimo, maximo in [('ancho', 1920, 64, 4096), ('alto', 1080, 64, 4096), ('fps', 30, 1, 60), ('duracion', 5, .1, 120)]:
        v = datos.get(k, defecto)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not minimo <= v <= maximo or (k != 'duracion' and int(v) != v):
            raise ValueError(f'{k} debe estar entre {minimo} y {maximo}')
        limpio[k] = float(v) if k == 'duracion' else int(v)
    props = datos.get('props', {})
    if not isinstance(props, dict):
        raise ValueError('Props debe ser un objeto JSON')
    try:
        crudo = json.dumps(props, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError('Props debe contener únicamente valores JSON finitos') from exc
    if len(crudo) > 100_000:
        raise ValueError('Props supera 100.000 caracteres')
    limpio['props'] = copy.deepcopy(props)
    if 'modo' in datos:
        if datos['modo'] not in ('superponer', 'sustituir'):
            raise ValueError('modo de aplicación Remotion no válido')
        limpio['modo'] = datos['modo']
    return limpio


def props_recursos(proyecto, props):
    """Referencias portables del proyecto; el navegador recibe imágenes autocontenidas."""
    if isinstance(props, dict):
        return {k: props_recursos(proyecto, v) for k, v in props.items()}
    if isinstance(props, list):
        return [props_recursos(proyecto, v) for v in props]
    if isinstance(props, str) and props.startswith('proyecto://'):
        raiz = Path(proyecto.raiz).resolve()
        ruta = (raiz / props[len('proyecto://'):].replace('\\', '/')).resolve()
        if not ruta.is_relative_to(raiz) or ruta.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif') or not ruta.is_file():
            raise ValueError('el recurso Remotion debe ser una imagen existente del proyecto')
        if ruta.stat().st_size > 20 * 1024 * 1024:
            raise ValueError('la imagen Remotion supera 20 MiB')
        return 'data:' + mimetypes.guess_type(ruta.name)[0] + ';base64,' + base64.b64encode(ruta.read_bytes()).decode()
    return props


def biblioteca(raiz_proyectos):
    return Path(os.environ.get('ESTUDIO_REMOTION') or Path(raiz_proyectos).resolve().parent / 'plantillas_remotion')


def _ejemplos():
    codigo = (MOTOR / 'Plantilla.tsx').read_text(encoding='utf-8')
    tipos = [('titulo', 'Título Cinematográfico', 'La Cordillera', 'Territorio, agua y memoria'),
             ('mapa', 'Mapa Animado', 'Un mundo conectado', 'Rutas y territorios'),
             ('lower', 'Lower Third', 'Elena Ruiz', 'Investigadora'),
             ('fechas', 'Línea de Tiempo', 'Nuestra historia', '1990 — 2020'),
             ('circular', 'Gráfico Circular', 'Los datos', 'Un cambio medible'),
             ('barras', 'Gráfico de Barras', 'Evolución', 'Crecimiento anual'),
             ('subtitulos', 'Subtítulos Animados', 'Una historia', 'de territorio y gente.'),
             ('galeria', 'Galería Animada', 'Instantes', 'Una memoria compartida'),
             ('capitulo', 'Título de Capítulo', 'EL ORIGEN', 'Capítulo 01'),
             ('cita', 'Cita Destacada', 'Todo comienza con una pregunta', 'Una nueva mirada'),
             ('cifra', 'Cifra Destacada', '72 %', 'Del territorio explorado'),
             ('remate', 'Cierre Documental', 'La historia continúa', 'AS Video Studio')]
    ejemplos = [dict(id='ejemplo-' + tipo, tipo=tipo, nombre=nombre,
                     descripcion=('Tres fotografías animadas. Elige las imágenes del proyecto o sube tus fotos desde Props.' if tipo == 'galeria' else
                                  'Título principal animado con tipografía cinematográfica, ideal para documentales y piezas narrativas.' if tipo == 'titulo' else nombre + ' reutilizable. Personaliza el código y sus propiedades.'),
                     codigo=codigo.replace('__VARIANTE__', tipo), ancho=1920, alto=1080, fps=30, duracion=5,
                     props=(dict(imagen1='', imagen2='', imagen3='') if tipo == 'galeria' else
                            dict(valor=72, color='#c4cfec') if tipo == 'circular' else
                            dict(valores=[25, 40, 58, 75, 96], color='#769ec7') if tipo == 'barras' else
                            dict(titulo=titulo, subtitulo=subtitulo, autor='Un documental de AS Video Studio')))
                for tipo, nombre, titulo, subtitulo in tipos]
    return ejemplos


def catalogo(raiz_proyectos):
    with _LOCK_BIBLIOTECA:
        carpeta = biblioteca(raiz_proyectos)
        eliminadas = leer_json(str(carpeta / '_config' / 'eliminadas.json')) or []
        propias = [leer_json(str(p)) for p in sorted(carpeta.glob('*.json'))]
        return [p for p in _ejemplos() if p['id'] not in eliminadas] + [p for p in propias if p]


def guardar(raiz_proyectos, datos):
    plantilla = validar_plantilla(datos)
    plantilla['id'] = huella(plantilla)
    with _LOCK_BIBLIOTECA:
        escribir_json(str(biblioteca(raiz_proyectos) / (plantilla['id'] + '.json')), plantilla)
    return plantilla


def eliminar(raiz_proyectos, referencia):
    """Retira la ficha de la biblioteca; las instantáneas de proyectos son independientes."""
    if not isinstance(referencia, str) or not re.fullmatch(r'ejemplo-[a-z]+|[a-f0-9]{64}', referencia):
        raise ValueError('identificador de plantilla Remotion no válido')
    with _LOCK_BIBLIOTECA:
        carpeta = biblioteca(raiz_proyectos)
        if referencia.startswith('ejemplo-'):
            if referencia not in {p['id'] for p in _ejemplos()}:
                raise ValueError('esa plantilla no está en la biblioteca')
            ruta = carpeta / '_config' / 'eliminadas.json'
            eliminadas = set(leer_json(str(ruta)) or [])
            eliminadas.add(referencia)
            escribir_json(str(ruta), sorted(eliminadas))
        else:
            (carpeta / (referencia + '.json')).unlink(missing_ok=True)


def disponible():
    return bool(shutil.which('node') and (MOTOR / 'node_modules' / '@remotion' / 'renderer').is_dir())


def _correr(pedido, avisar=None):
    if not disponible():
        raise ValueError('Instala el motor local: npm ci --prefix motores/remotion (Node >=22)')
    carpeta = Path(pedido['carpeta'])
    carpeta.mkdir(parents=True, exist_ok=True)
    if pedido['accion'] == 'render':
        from pasos import medios
        pedido = dict(pedido, navegador=os.environ.get('ESTUDIO_REMOTION_BROWSER') or medios.edge())
    solicitud = carpeta / ('pedido-' + uuid.uuid4().hex + '.json')
    escribir_json(str(solicitud), pedido)
    proceso = subprocess.Popen([shutil.which('node'), str(MOTOR / 'motor.mjs'), str(solicitud)],
                               cwd=str(MOTOR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding='utf-8', errors='replace', start_new_session=os.name != 'nt')
    mensajes = queue.Queue()
    def leer():
        for linea in proceso.stdout:
            mensajes.put(linea)
    lector = threading.Thread(target=leer, daemon=True)
    lector.start()
    salida = []
    inicio = time.monotonic()
    progreso = 0
    try:
        while proceso.poll() is None or not mensajes.empty() or lector.is_alive():
            if time.monotonic() - inicio > 600:
                raise ValueError('Remotion ha superado el tiempo máximo de 10 minutos')
            try:
                linea = mensajes.get(timeout=.2)
                salida.append(linea)
                salida = salida[-40:]
                try:
                    dato = json.loads(linea)
                    progreso = dato.get('progreso', progreso)
                except (ValueError, AttributeError):
                    pass
            except queue.Empty:
                pass
            if avisar:
                avisar(progreso, 'Compilando Remotion' if pedido['accion'] == 'compilar' else 'Renderizando Remotion')
        if proceso.returncode:
            raise ValueError('Remotion: ' + ''.join(salida)[-5000:])
    finally:
        if proceso.poll() is None:
            # Los hijos Chromium terminan al cerrarse su proceso Node/control CDP.
            from pasos import medios
            medios._terminar_arbol(proceso)
        proceso.wait()
        lector.join(timeout=2)
        proceso.stdout.close()
        solicitud.unlink(missing_ok=True)


def compilar(proyecto, datos, avisar=None):
    plantilla = validar_plantilla(datos)
    clave = huella(dict(codigo=plantilla['codigo'], ancho=plantilla['ancho'], alto=plantilla['alto'],
                        fps=plantilla['fps'], duracion=plantilla['duracion'], motor=VERSION))
    carpeta = Path(proyecto.ruta('remotion', 'compilados', clave))
    # Cerrojo cooperativo: la espera también comprueba la cancelación.
    while not _LOCK.acquire(timeout=.2):
        if avisar:
            avisar(0, 'Esperando al motor Remotion')
    try:
        if not (carpeta / 'listo.json').is_file():
            _correr(dict(accion='compilar', carpeta=str(carpeta), plantilla=plantilla), avisar)
            escribir_json(str(carpeta / 'listo.json'), {'motor': VERSION})
        # Instantánea independiente del nombre, los props y de la biblioteca global.
        referencia = huella(plantilla)
        escribir_json(proyecto.ruta('remotion', 'plantillas', referencia + '.json'), plantilla)
        return dict(plantilla=referencia, compilado=clave, **dict(plantilla, props=props_recursos(proyecto, plantilla['props'])))
    finally:
        _LOCK.release()


def resolver(proyecto, referencia):
    if not isinstance(referencia, str) or not re.fullmatch('[a-f0-9]{64}', referencia):
        raise ValueError('referencia de plantilla no válida')
    p = leer_json(proyecto.ruta('remotion', 'plantillas', referencia + '.json'))
    if not p or huella(validar_plantilla(p)) != referencia:
        raise ValueError('falta la versión de la plantilla Remotion en este proyecto')
    return p


def validar_edicion(datos, escena):
    if not isinstance(datos, dict) or set(datos) != {'ancla', 'bloques'} or datos['ancla'] != animaciones.ancla_de(escena):
        raise ValueError('las animaciones Remotion no corresponden a esta escena')
    bloques = datos['bloques']
    duracion = float(escena['t_out']) - float(escena['t_in'])
    if not isinstance(bloques, list) or len(bloques) > 16:
        raise ValueError('utiliza como máximo 16 bloques Remotion por escena')
    limpios = []
    for b in bloques:
        if not isinstance(b, dict) or set(b) - {'plantilla', 'nombre', 'props', 'inicio', 'fin', 'modo', 'origen', 'posicion'} or not {'plantilla', 'nombre', 'props', 'inicio', 'fin'} <= set(b):
            raise ValueError('bloque Remotion no válido')
        if 'posicion' in b:
            posicion = b['posicion']
            if (not isinstance(posicion, dict) or set(posicion) != {'x', 'y'} or
                    any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1 for v in posicion.values())):
                raise ValueError('la posición Remotion debe contener desplazamientos x/y entre -1 y 1')
        if b.get('modo', 'superponer') not in ('superponer', 'sustituir'):
            raise ValueError('modo de aplicación Remotion no válido')
        if not isinstance(b['plantilla'], str) or not re.fullmatch('[a-f0-9]{64}', b['plantilla']):
            raise ValueError('elige una versión de plantilla guardada')
        if not isinstance(b['nombre'], str) or len(b['nombre']) > 120 or not isinstance(b['props'], dict):
            raise ValueError('nombre o props no válidos')
        for k in ('inicio', 'fin'):
            if isinstance(b[k], bool) or not isinstance(b[k], (int, float)) or not math.isfinite(b[k]):
                raise ValueError('los tiempos deben ser números finitos')
        libre = 'origen' in b
        if libre and (isinstance(b['origen'], bool) or not isinstance(b['origen'], (int, float)) or not math.isfinite(b['origen']) or b['origen'] != float(escena['t_in'])):
            raise ValueError('el origen del bloque Remotion no corresponde al timeline')
        minimo = -b['origen'] if libre else 0
        maximo = float(escena.get('timeline_fin', escena['t_out'])) - b['origen'] if libre else duracion
        if not minimo <= b['inicio'] < b['fin'] <= maximo + 1e-6 or b['fin'] - b['inicio'] < .1 - 1e-6 or (libre and b['fin'] - b['inicio'] > 120 + 1e-6):
            raise ValueError('el bloque Remotion debe quedar dentro del timeline y durar entre 0,1 y 120 s' if libre else 'el bloque Remotion debe quedar dentro de la escena y durar al menos 0,1 s')
        if not libre and b.get('modo') == 'sustituir' and (b['inicio'] != 0 or abs(b['fin'] - duracion) > 1e-6):
            raise ValueError('la composición completa debe cubrir toda la escena')
        validar_plantilla(dict(codigo='export default () => null', props=b['props']))
        limpios.append(copy.deepcopy(b))
    if sum(b.get('modo') == 'sustituir' and 'origen' not in b for b in limpios) > 1:
        raise ValueError('solo puede haber una sustitución Remotion por escena')
    return dict(ancla=datos['ancla'], bloques=limpios)


def bloques_de(params, escena, propios=False):
    ficha = ((params or {}).get('unidades') or {}).get('escena:' + escena['id'], {}).get('remotion')
    locales = []
    if ficha:
        # Los bloques libres conservan su reloj absoluto aunque cambie la narración.
        locales = [copy.deepcopy(b) for b in ficha['bloques'] if 'origen' in b or ficha.get('ancla') == animaciones.ancla_de(escena)]
    if propios:
        return [dict(b, origen=float(escena['t_in']),
                     inicio=b['inicio'] + b['origen'] - float(escena['t_in']),
                     fin=b['fin'] + b['origen'] - float(escena['t_in'])) if 'origen' in b else b for b in locales]
    resultado = [b for b in locales if 'origen' not in b]
    for _, unidad in sorted(((params or {}).get('unidades') or {}).items()):
        for bloque in (unidad.get('remotion') or {}).get('bloques', []):
            if 'origen' not in bloque:
                continue
            inicio = bloque['origen'] + bloque['inicio'] - float(escena['t_in'])
            fin = bloque['origen'] + bloque['fin'] - float(escena['t_in'])
            if inicio < float(escena['t_out']) - float(escena['t_in']) and fin > 0:
                resultado.append(dict(bloque, inicio=inicio, fin=fin))
    return resultado


def dependencias(params, escenas):
    """Sella también las escenas atravesadas, incluida la retirada de un bloque."""
    return {e['id']: [b for b in bloques_de(params, e) if 'origen' in b] for e in escenas}


def pedido_de(proyecto, bloque, resolucion, fps):
    plantilla = resolver(proyecto, bloque['plantilla'])
    plantilla['props'] = props_recursos(proyecto, bloque['props'])
    if bloque.get('modo') != 'sustituir' or 'origen' in bloque:
        plantilla.update(fps=int(fps), duracion=round(bloque['fin'] - bloque['inicio'], 9))
    modo = bloque.get('modo', 'superponer')
    if modo == 'sustituir' and 'origen' in bloque:
        modo = 'sustituir-timeline'
    clave = huella(dict(plantilla=plantilla, salida=list(resolucion), motor=VERSION, modo=modo))
    carpeta = Path(proyecto.ruta('remotion', 'renders', clave))
    return plantilla, carpeta


def capas_guardadas(proyecto, bloques, resolucion, fps):
    capas = []
    for bloque in bloques:
        _, carpeta = pedido_de(proyecto, bloque, resolucion, fps)
        ficha = leer_json(str(carpeta / 'listo.json'))
        if bloque.get('modo') == 'sustituir' and 'origen' not in bloque:
            if ficha and (carpeta / 'video.mp4').is_file():
                capas.append(dict(modo='sustituir', inicio=0, fin=bloque['fin'], clip=os.path.relpath(carpeta / 'video.mp4', proyecto.raiz).replace('\\', '/')))
            continue
        if ficha and all((carpeta / n).is_file() for n in ficha['frames']):
            capas.append(dict(inicio=bloque['inicio'], fin=bloque['fin'], fps=fps, posicion=bloque.get('posicion', {}), libre='origen' in bloque, opaca=bloque.get('modo') == 'sustituir',
                              fotogramas=[os.path.relpath(carpeta / n, proyecto.raiz).replace('\\', '/') for n in ficha['frames']]))
    return capas


def preparar(proyecto, bloque, resolucion, fps, avisar=None):
    plantilla, carpeta = pedido_de(proyecto, bloque, resolucion, fps)
    while not _LOCK.acquire(timeout=.2):
        if avisar:
            avisar(0, 'Esperando al motor Remotion')
    try:
        if bloque.get('modo') == 'sustituir' and 'origen' not in bloque:
            if not (carpeta / 'listo.json').is_file() or not (carpeta / 'video.mp4').is_file():
                compilado = compilar(proyecto, resolver(proyecto, bloque['plantilla']), avisar)
                _correr(dict(accion='render', formato='mp4', carpeta=str(carpeta), plantilla=plantilla,
                             compilado=proyecto.ruta('remotion', 'compilados', compilado['compilado'])), avisar)
                if not (carpeta / 'video.mp4').is_file():
                    raise ValueError('Remotion no entregó el vídeo MP4')
                escribir_json(str(carpeta / 'listo.json'), {'video': 'video.mp4'})
            if not (carpeta / 'fondo.png').is_file():
                from PIL import Image
                Image.new('RGB', tuple(resolucion), 'black').save(carpeta / 'fondo.png')
            return dict(modo='sustituir', inicio=0, fin=bloque['fin'], clip=str(carpeta / 'video.mp4'))
        if not (carpeta / 'listo.json').is_file():
            compilado = compilar(proyecto, resolver(proyecto, bloque['plantilla']), avisar)
            _correr(dict(accion='render', carpeta=str(carpeta), plantilla=plantilla,
                         escala=min(resolucion[0] / plantilla['ancho'], resolucion[1] / plantilla['alto']),
                         compilado=proyecto.ruta('remotion', 'compilados', compilado['compilado'])), avisar)
            marcos = sorted(carpeta.glob('f*.png'))
            if len(marcos) != max(1, int(math.floor(plantilla['duracion'] * fps + .5))):
                raise ValueError('Remotion no entregó todos los fotogramas')
            escribir_json(str(carpeta / 'listo.json'), {'frames': [p.name for p in marcos]})
        nombres = leer_json(str(carpeta / 'listo.json'))['frames']
        marcos = [str(carpeta / n) for n in nombres]
        if not all(Path(p).is_file() for p in marcos):
            raise ValueError('faltan fotogramas del render Remotion; elimina su caché para prepararlo de nuevo')
        return dict(inicio=bloque['inicio'], fin=bloque['fin'], fps=fps, fotogramas=marcos, posicion=bloque.get('posicion', {}), libre='origen' in bloque, opaca=bloque.get('modo') == 'sustituir')
    finally:
        _LOCK.release()


def superponer(png, capas, tiempo):
    from PIL import Image, ImageOps
    base = None
    for capa in capas:
        if not capa['inicio'] <= tiempo < capa['fin']:
            continue
        if base is None:
            base = Image.open(io.BytesIO(png)).convert('RGBA')
        if capa.get('opaca'):
            base.paste((0, 0, 0, 255), (0, 0, base.width, base.height))
        numero = min(len(capa['fotogramas']) - 1, max(0, int((tiempo - capa['inicio']) * capa['fps'] + 1e-7)))
        with Image.open(capa['fotogramas'][numero]) as imagen:
            imagen = ImageOps.contain(imagen.convert('RGBA'), base.size, Image.Resampling.LANCZOS)
            posicion = capa.get('posicion') or {}
            base.alpha_composite(imagen, ((base.width - imagen.width) // 2 + round(posicion.get('x', 0) * base.width),
                                          (base.height - imagen.height) // 2 + round(posicion.get('y', 0) * base.height)))
    if base is None:
        return png
    salida = io.BytesIO()
    base.save(salida, format='PNG')
    return salida.getvalue()
