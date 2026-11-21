"""Assets de código inmutables: personajes previos y utilería ampliable por escena.

Nunca importa código generado en el servidor. Las escenas siguen siendo programas
libres. El catálogo compartido solo ofrece recursos del mismo paquete de estilo;
cada vídeo guarda las fuentes utilizadas para no depender de otra instalación.
"""
import ast
import json
import os
from pathlib import Path
import re
import sys

from nucleo.proyecto import escribir_json, leer_json, lock_de, ruta_contenida
from pasos import espacio_estilo

VERSION = 1
BASE = Path(__file__).resolve().parents[1]/'motores/estilo_ia/recursos_base.py'
SOPORTE = BASE.with_name('soporte_rigs.py')
APARIENCIAS = BASE.with_name('apariencias.py')
PERSONAS = BASE.with_name('personas.py')
# Adaptador de geometría comprobado; nunca aplicarlo por parecido de nombres.
RIG_HUMANO = '29a56e0438a6685153aa168974dc04dbc11f6859fbad6b5bb78239e52bba4476'
MODULO = re.compile(r'^[a-z][a-z0-9_]{0,60}$')
HUELLA = re.compile(r'^[a-f0-9]{64}$')


def carpeta_catalogo():
    if os.environ.get('ESTUDIO_RECURSOS_ANIMACION'):
        return Path(os.environ['ESTUDIO_RECURSOS_ANIMACION']).resolve()
    programa = Path(__file__).resolve().parents[1]
    for variable in ('ESTUDIO_BANCO','ESTUDIO_PROYECTOS'):
        if os.environ.get(variable):
            candidata = Path(os.environ[variable]).resolve().parent/'recursos_animacion'
            if not candidata.is_relative_to(programa):
                return candidata
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local') if os.name == 'nt' else Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share')
    return base/'as-video-studio'/'recursos_animacion'


def raiz(proyecto):
    return Path(proyecto.ruta('estilo_ia','recursos_animacion'))


def validar(dato):
    from pasos import animacion_nativa
    if not isinstance(dato,dict) or dato.get('tipo') not in ('personaje','objeto','escenario','grafico','herramienta'):
        raise ValueError('el asset necesita tipo personaje, objeto, escenario o grafico')
    for k,limite in (('concepto',1000),('nombre',160),('interfaz',6000)):
        if not isinstance(dato.get(k),str) or not dato[k].strip() or len(dato[k]) > limite:
            longitud = len(dato[k]) if isinstance(dato.get(k),str) else 'no textual'
            raise ValueError(f'campo del asset no válido: {k} (longitud {longitud}; máximo {limite})')
    dependencias = dato.get('dependencias') or {}
    if not isinstance(dependencias,dict) or len(dependencias)>20:
        raise ValueError('dependencias de asset no válidas')
    for nombre,ref in dependencias.items():
        if (not espacio_estilo.nombre_modulo_valido(nombre) or nombre in sys.stdlib_module_names
                or not isinstance(ref,dict) or not HUELLA.fullmatch(str(ref.get('huella','')))
                or ref.get('ruta') != f"estilo_ia/recursos_animacion/recursos/{ref['huella']}.json"):
            raise ValueError('dependencia de asset no válida; necesita módulo y referencia inmutable')
    es_soporte = dato.get('tipo') == 'herramienta'
    animacion_nativa.validar_codigo(dato.get('codigo'),
        herramientas=[*dependencias,*(['copy','importlib'] if es_soporte else [])],
        entrada='crear' if es_soporte else 'dibujar')
    muestra = dato.get('muestra')
    if dato['tipo'] == 'personaje' and (not isinstance(muestra,list) or len(muestra) != 2
            or any(not isinstance(e,dict) or not e for e in muestra) or muestra[0] == muestra[1]):
        raise ValueError('el personaje necesita dos estados distintos de muestra de su articulación')
    salida = {k:dato[k] for k in ('tipo','concepto','nombre','interfaz','codigo')}
    if muestra is not None:
        salida['muestra'] = muestra
    if dependencias:
        salida['dependencias'] = dependencias
    # No evaluar objetos arbitrarios ni persistir NaN en los estados de muestra.
    json.dumps(salida,allow_nan=False)
    return salida


def guardar(proyecto,estilo,dato):
    if not HUELLA.fullmatch(str(estilo)):
        raise ValueError('huella de estilo del asset no válida')
    recurso = dict(version=VERSION,estilo=estilo,asset=validar(dato))
    firma = espacio_estilo.huella(recurso)
    ruta = raiz(proyecto)/'recursos'/(firma+'.json')
    with lock_de(str(ruta)):
        if ruta.exists():
            if leer_json(str(ruta),estricto=True) != recurso:
                raise ValueError('un asset inmutable ha cambiado; no se sobrescribe')
        else:
            escribir_json(str(ruta),recurso)
    return dict(huella=firma,ruta=ruta.relative_to(proyecto.raiz).as_posix())


def cargar(proyecto,referencia,_cadena=()):
    if (not isinstance(referencia,dict) or not HUELLA.fullmatch(str(referencia.get('huella','')))
            or not isinstance(referencia.get('ruta'),str)):
        raise ValueError('referencia de asset no válida')
    ruta = Path(ruta_contenida(proyecto.raiz,referencia['ruta']))
    if not ruta.is_relative_to(raiz(proyecto).resolve()):
        raise ValueError('el asset no pertenece a los recursos portátiles del vídeo')
    dato = leer_json(str(ruta),estricto=True)
    if (not dato or dato.get('version') != VERSION or not HUELLA.fullmatch(str(dato.get('estilo','')))
            or espacio_estilo.huella(dato) != referencia['huella']):
        raise ValueError('el asset guardado falta o ha cambiado; no se reconstruirá automáticamente')
    validar(dato['asset'])
    if referencia['huella'] in _cadena or len(_cadena)>12:
        raise ValueError('ciclo o profundidad excesiva en las dependencias de assets')
    for ref in (dato['asset'].get('dependencias') or {}).values():
        dependencia = cargar(proyecto,ref,(*_cadena,referencia['huella']))
        if dependencia['estilo'] != dato['estilo']:
            raise ValueError('dependencia de otro estilo en un asset')
    return dato


def publicar(proyecto,referencias,compartir=True):
    for ref in referencias.values():
        dato = cargar(proyecto,ref)
        publicar(proyecto,dato['asset'].get('dependencias') or {},compartir)
        if compartir:
            ruta = carpeta_catalogo()/dato['estilo']/'recursos'/(ref['huella']+'.json')
            with lock_de(str(ruta)):
                if ruta.exists() and leer_json(str(ruta),estricto=True) != dato:
                    raise ValueError('el catálogo compartido contiene un asset alterado')
                if not ruta.exists():
                    escribir_json(str(ruta),dato)
        escribir_json(str(raiz(proyecto)/'disponibles'/(ref['huella']+'.json')),ref)


def traer(proyecto,estilo,firma,_cadena=()):
    if not HUELLA.fullmatch(str(firma)) or firma in _cadena or len(_cadena)>12:
        raise ValueError('dependencia compartida no válida o cíclica')
    dato = leer_json(str(carpeta_catalogo()/estilo/'recursos'/(firma+'.json')),estricto=True)
    if not dato or espacio_estilo.huella(dato)!=firma or dato.get('estilo')!=estilo:
        raise ValueError('recurso compartido alterado o incompleto; no se regenerará')
    validar(dato['asset'])
    for ref in (dato['asset'].get('dependencias') or {}).values():
        traer(proyecto,estilo,ref['huella'],(*_cadena,firma))
    return guardar(proyecto,estilo,dato['asset'])


def catalogo(proyecto,estilo):
    for ruta in sorted((carpeta_catalogo()/estilo/'recursos').glob('*.json')):
        dato = leer_json(str(ruta),estricto=True)
        if espacio_estilo.huella(dato) != ruta.stem or dato.get('estilo') != estilo:
            raise ValueError('recurso compartido alterado; no se omitirá ni regenerará a ciegas')
        ref = traer(proyecto,estilo,ruta.stem)
        publicar(proyecto,{'asset_'+ref['huella'][:24]:ref},compartir=False)
    salida = {}
    for ruta in sorted((raiz(proyecto)/'disponibles').glob('*.json')):
        ref = leer_json(str(ruta),estricto=True)
        if cargar(proyecto,ref)['estilo'] == estilo:
            salida['asset_'+ref['huella'][:24]] = ref
    return salida


def _fuente_compatible(proyecto,asset):
    """Expone helpers heredados de wrappers antiguos, solo en la copia del render.

    Algunas identidades pagadas delegan dibujar pero olvidan exportar los demás
    controles del rig que prometen en su interfaz. No se reescribe su asset SHA.
    Solo reconocer una instancia inequívoca del soporte inmutable conocido.
    """
    codigo = asset['codigo']
    if asset['tipo']!='personaje' or not asset.get('dependencias'):
        return codigo
    arbol = ast.parse(codigo)
    if any(isinstance(n,ast.FunctionDef) and n.name=='__getattr__' for n in arbol.body):
        return codigo
    soportes = set()
    for nombre,ref in asset['dependencias'].items():
        dependencia = cargar(proyecto,ref)['asset']
        if dependencia['tipo']=='herramienta' and dependencia['concepto']=='instancias_de_rig':
            soportes.add(nombre)
    modulos,funciones = set(),set()
    for n in arbol.body:
        if isinstance(n,ast.Import):
            modulos.update(a.asname or a.name for a in n.names if a.name in soportes)
        elif isinstance(n,ast.ImportFrom) and n.module in soportes:
            funciones.update(a.asname or a.name for a in n.names if a.name=='crear')
    instancias = []
    for n in arbol.body:
        if not isinstance(n,ast.Assign) or len(n.targets)!=1 or not isinstance(n.targets[0],ast.Name) or not isinstance(n.value,ast.Call):
            continue
        f = n.value.func
        if ((isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name) and f.value.id in modulos and f.attr=='crear')
                or (isinstance(f,ast.Name) and f.id in funciones)):
            instancias.append(n.targets[0].id)
    if len(instancias)!=1:
        return codigo
    instancia = instancias[0]
    escrituras = [n for n in ast.walk(arbol) if isinstance(n,ast.Name)
        and n.id==instancia and isinstance(n.ctx,(ast.Store,ast.Del))]
    if len(escrituras)!=1:
        return codigo
    return codigo+f'\n\n# Compatibilidad de exportación; fuente original conservada por SHA.\ndef __getattr__(nombre):\n    return getattr({instancia},nombre)\n'


def fuentes(proyecto,referencias):
    """Cierre transitivo y nombres fijos; no resolver contra versiones recientes."""
    salida = {}
    for modulo,ref in referencias.items():
        dato = cargar(proyecto,ref)['asset']
        codigo = _fuente_compatible(proyecto,dato)
        for nombre,codigo_dependencia in fuentes(proyecto,dato.get('dependencias') or {}).items():
            if nombre in salida and salida[nombre]!=codigo_dependencia:
                raise ValueError('colisión entre dependencias de assets')
            salida[nombre] = codigo_dependencia
        if modulo in salida and salida[modulo]!=codigo:
            raise ValueError('colisión entre módulos de assets')
        salida[modulo] = codigo
    return salida


def soporte(proyecto,estilo):
    return guardar(proyecto,estilo,dict(tipo='herramienta',concepto='instancias_de_rig',
        nombre='Instancias independientes de mecánica compartida',codigo=SOPORTE.read_text(encoding='utf-8'),
        interfaz='crear(base,paletas=None,inicial=None,extensiones=None) devuelve rig privado. paletas={global_dict:{slot:valor}}; inicial actualiza estado_base; extensiones={nombre:funcion(rig,*args)} permite reemplazar o añadir CUALQUIER función de geometría/dibujo sin copiar IK, interpolación ni renderer. rig.originales[nombre] conserva función original. No muta globals de otro personaje.'))


def perfil_apariencia(base):
    import hashlib
    codigo = base['asset']['codigo']
    if hashlib.sha256(codigo.encode()).hexdigest()==RIG_HUMANO:
        return 'humano_v1'
    arbol = ast.parse(codigo)
    funciones = {n.name for n in arbol.body if isinstance(n,ast.FunctionDef)}
    for n in arbol.body:
        if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APARIENCIA_VERSION' for t in n.targets)
                and isinstance(n.value,ast.Constant) and type(n.value.value) is int and n.value.value==1
                and 'aplicar_apariencia' in funciones):
            return 'nativo_v1'
    return None


def soporte_apariencias(proyecto,estilo):
    return guardar(proyecto,estilo,dict(tipo='herramienta',concepto='apariencias_de_rig',
        nombre='Dibujo compartido de ropa, pelo y rasgos por datos',
        codigo=APARIENCIAS.read_text(encoding='utf-8'),
        interfaz='crear(base,soporte,apariencia,perfil,extensiones=None) devuelve rig privado. Identidad apariencia/1, sin generar funciones de pelo/ropa/cara por personaje. Las extensiones excepcionales reciben rig como primer argumento; todas las funciones articuladas siguen disponibles.'))


def personas_del_estilo(proyecto,estilo,ref_base,ref_soporte):
    """Fábrica local e inmutable, preparada sin IA para extras y multitudes."""
    perfil = perfil_apariencia(cargar(proyecto,ref_base))
    apariencias = soporte_apariencias(proyecto,estilo)
    util = guardar(proyecto,estilo,dict(tipo='herramienta',concepto='variantes_personas_soporte',
        nombre='Instancias anónimas y siluetas del mismo rig',codigo=PERSONAS.read_text(encoding='utf-8'),
        interfaz='crear(base,soporte,apariencias,perfil,apariencia=None,silueta=None,extensiones=None) devuelve rig.'))
    refs = {'asset_'+r['huella'][:24]:r for r in (ref_base,ref_soporte,apariencias,util)}
    mb,ms,ma,mu = ('asset_'+r['huella'][:24] for r in (ref_base,ref_soporte,apariencias,util))
    codigo = f'''import {mb} as _base
import {ms} as _soporte
import {ma} as _apariencias
import {mu} as _personas
def crear(apariencia=None,silueta=None,extensiones=None):
    return _personas.crear(_base,_soporte,_apariencias,{perfil!r},apariencia,silueta,extensiones)
'''
    return guardar(proyecto,estilo,dict(tipo='herramienta',concepto='personas_anonimas_del_estilo',
        nombre='Personas anónimas, parejas, extras y siluetas DEL estilo',codigo=codigo,dependencias=refs,
        interfaz='crear(apariencia=None,silueta=None,extensiones=None) devuelve UNA instancia privada del rig del estilo. Crea cada identidad UNA vez fuera de pintar; usa persona.dibujar(lienzo,estado,contexto) y los controles/unidades de la base. apariencia usa esquema apariencia/1 para pelo, ropa, colores y proporciones. silueta="#RRGGBB" SOLO si la descripción pide siluetas; conserva geometría y articulaciones del rig. No llama a IA. extensiones={nombre:funcion(rig,*args)} permite ampliar detalles; rig.dibujo_compartido conserva dibujo del estilo. Perfil de apariencia: '+str(perfil)))


def encargo_apariencia(encargo,manifiesto,base=None,ayuda=None):
    from motores.estilo_ia.apariencias import ESQUEMA, DEFECTO
    datos = _datos_personaje(encargo,manifiesto)
    datos['tecnicas'] = {k:v for k,v in datos['tecnicas'].items() if k=='visual'}
    for ventana in datos['observaciones']:
        ventana['areas'] = {k:v for k,v in ventana['areas'].items() if k in ('personajes','materiales_luz_color')}
    datos['alcance'] = 'Solo seleccionar identidad visual. La mecánica y el dibujo de rasgos habituales ya existen.'
    datos['esquema_apariencia'] = ESQUEMA
    datos['valores_iniciales'] = DEFECTO
    prompt = '''DEFINE SOLO LOS DATOS DE APARIENCIA de este personaje.
El monigote, articulaciones, expresiones y dibujo de ropa/pelo ya están programados.
NO escribas otro dibujar, rostro, pelo, ropa, IK ni interpolación. Devuelve SOLO JSON:
{formato:"apariencia/1",nombre,concepto,apariencia:{...}}.
apariencia usa las claves del esquema; colores #RRGGBB; altura/cuerpo/cabeza son
factores, edad son años. Conserva identidad, acabado, proporciones y accesorios.
Selecciona datos, no informes ni código equivalente a esos datos. No heredes barba,
sudadera o móvil del protagonista si no corresponden. No envíes código habitual.
Si un detalle visual NO puede representarse con los datos, puedes incluir
codigo_extra: un módulo con funciones SOLO para ese detalle y un diccionario
EXTENSIONES={nombre_funcion:funcion(rig,*args)}. Es opcional: no lo incluyas para
ropa/pelo/colores/proporciones ya cubiertos. No inventes APIs del rig: para una
geometría excepcional puedes definir detalle(rig,lienzo,estado,contexto), llamar
rig.dibujo_compartido(lienzo,estado,contexto), añadir geometría Pillow anclada a las
anclas devueltas y declarar EXTENSIONES={'dibujar':detalle}.
Biblioteca estándar/PIL, sin proveedores, imágenes, red ni procesos. No ejecutes.
DATOS:\n'''+json.dumps(datos,ensure_ascii=False,separators=(',',':'))
    if base is not None and ayuda is not None:
        # Una especie distinta no es ropa sobre un esqueleto humano. Ofrecer la
        # mecánica fijada sin imponer ese esquema a anatomías incompatibles.
        tecnico = json.loads(encargo_identidad(encargo,{},base,ayuda).rsplit('DATOS:\n',1)[1])
        datos['geometria_base'] = tecnico['base']
        datos['soporte'] = tecnico['soporte']
        prompt = prompt[:prompt.index('DATOS:\n')]+'''EXCEPCIÓN ANATÓMICA EXPLÍCITA: el esquema anterior es HUMANO. Para un animal,
cuadrúpedo u otra anatomía incompatible NO elijas ropa=null ni lo disfraces de humano.
Devuelve {formato:"geometria/1",nombre,concepto,codigo_extra,interfaz,muestra:[a,b]}.
No incluyas apariencia. codigo_extra define EXTENSIONES con dibujar, pose y
estado_base, y las funciones adicionales necesarias (incluidos movimientos de esa
anatomía). Cada función recibe rig primero. El wrapper crea una instancia privada
de la base sin aplicar la apariencia humana. Reutiliza FK/IK/interpolación de la
base cuando sean compatibles; no copies el motor. La geometría y los controles
articulados son libres, no un catálogo de poses. Documenta unidades, articulaciones,
anclas, cabeza, extremidades y cola si procede; muestra dos poses articuladas.
Sin sustituir nombres del wrapper; puedes usar rig.originales y helpers de la base.
No dibujes el humano debajo de un animal. Conserva acabado del estilo y anatomía
del encargo. Esta excepción NO es necesaria para ropa, pelo o colores humanos.
DATOS:\n'''+json.dumps(datos,ensure_ascii=False,separators=(',',':'))
    limite = 40000 if base is not None and ayuda is not None else 30000
    if len(prompt)>limite:
        raise ValueError(f'el encargo de apariencia supera {limite} caracteres; revisar sin truncar ni consumir IA')
    return prompt


def compilar_apariencia(dato,base,configuracion,referencias):
    """Wrapper mecánico local. La IA entrega datos, no repite el renderer."""
    from motores.estilo_ia.apariencias import validar as validar_apariencia
    if not isinstance(dato,dict) or dato.get('formato') not in ('apariencia/1','geometria/1'):
        raise ValueError('se esperaban datos apariencia/1; entrega conservada, no se repetirá IA')
    geometria = dato['formato']=='geometria/1'
    campos = {'interfaz','muestra'} if geometria else {'apariencia'}
    if set(dato)-({'formato','nombre','concepto','codigo_extra'}|campos):
        raise ValueError('la apariencia debe entregar datos, no otro rig; entrega conservada')
    apariencia = None if geometria else validar_apariencia(dato.get('apariencia'))
    extra = dato.get('codigo_extra','')
    if not isinstance(extra,str):
        raise ValueError('codigo_extra de apariencia debe ser texto')
    if geometria:
        # Contrato estático: nunca ejecutar una entrega dentro del servicio.
        extensiones = []
        for n in ast.parse(extra).body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTENSIONES' for t in n.targets):
                if isinstance(n.value,ast.Dict):
                    extensiones = [k.value for k in n.value.keys if isinstance(k,ast.Constant)]
        if not {'dibujar','pose','estado_base'}<=set(extensiones):
            raise ValueError('geometria/1 necesita EXTENSIONES explícitas: dibujar, pose y estado_base')
    reservados = {'rig','_base','_soporte','_apariencias','dibujar','__getattr__'}
    for n in ast.parse(extra).body:
        nombres = {n.name} if isinstance(n,(ast.FunctionDef,ast.ClassDef)) else {
            t.id for t in ast.walk(n) if isinstance(t,ast.Name) and isinstance(t.ctx,ast.Store)}
        if nombres & reservados:
            raise ValueError('codigo_extra no puede sustituir el wrapper de apariencia')
    mb,ms,ma = (configuracion[k] for k in ('base','soporte','apariencias'))
    crear = ('_soporte.crear(_base,extensiones=EXTENSIONES)' if geometria else
        f"_apariencias.crear(_base,_soporte,{apariencia!r},perfil={configuracion['perfil']!r},extensiones=EXTENSIONES)")
    codigo = f'''import {mb} as _base
import {ms} as _soporte
import {ma} as _apariencias
EXTENSIONES = {{}}
{extra}
rig = {crear}
def dibujar(lienzo,estado,contexto):
    return rig.dibujar(lienzo,estado,contexto)
def __getattr__(nombre):
    return getattr(rig,nombre)
'''
    muestra = json.loads(json.dumps(dato.get('muestra') if geometria else base['asset']['muestra']))
    if not geometria:
        for e in muestra:
            e['movil_visible'] = apariencia['movil']
            e['movil_mano'] = 'd' if apariencia['movil'] else None
    asset = dict(tipo='personaje',nombre=dato.get('nombre'),concepto=dato.get('concepto'),
        codigo=codigo,interfaz=dato.get('interfaz') if geometria else base['asset']['interfaz'],muestra=muestra)
    return validar(fijar_dependencias(asset,referencias))


def contrato():
    return '''Un asset es un módulo Python AUTOCONTENIDO, sin proveedores, imágenes,
red, procesos ni instalaciones. Puede usar Pillow y biblioteca estándar, NO otros
assets ni ficheros externos.
La tipografía por defecto del renderer admite tildes, ñ y ¿¡. Conserva texto Unicode
y mide/dibuja con la misma fuente, sin sustituir acentos ni conversiones de bytes.
Implementa dibujar(lienzo,estado,contexto): pinta sobre la PIL.Image recibida.
contexto contiene ancho,alto,t y duracion; estado es un dict
LIBRE: define y documenta las propiedades que necesite tu dibujo (articulaciones,
mirada, manos, expresiones, materiales, etc.). Puede devolver anclas en píxeles.
No encierres el personaje en poses fijas: ofrece controles de sus articulaciones
y funciones auxiliares para nuevas actuaciones. En personajes documenta controles
de torso, cabeza, hombros/codos/manos, caderas/rodillas/pies, mirada y expresión;
no solo una animación de saludo ni el movimiento global del cuerpo. Conserva
proporciones, vestuario y materiales de la identidad. La escena sigue programándose.
Puedes ofrecer preparar(contexto) para precalcular geometría, fuentes y capas
estáticas en memoria; dibujar actualiza solo lo temporal. No rebajes detalle ni
actuación para ahorrar código, ni recrees decorados enteros en cada fotograma.
Devuelve JSON {tipo:personaje|objeto|escenario|grafico,concepto,nombre,codigo,
interfaz:documentación de funciones y propiedades con unidades y valores iniciales,
muestra:[estado_inicial,estado_final]}. Para personajes, muestra DOS estados de
actuación articulada, no solo desplazamiento/zoom/opacidad. No ejecutes el código.
'''


def visibles(escena):
    ids = escena.get('personajes_visibles') if escena.get('personajes_visibles') is not None else escena.get('personajes') or []
    if not isinstance(ids,list) or any(not isinstance(i,str) or not i for i in ids):
        raise ValueError('los personajes visibles deben ser IDs del reparto')
    return ids


def _datos_personaje(encargo,manifiesto):
    """Selección por tarea, sin resumir ni truncar las evidencias de personaje.

    No enviar voz, música, narración, grafismos o edición para construir un rig.
    Todas las observaciones de personajes/materiales/movimiento se conservan.
    La firma histórica del recurso no cambia por compactar su transporte.
    """
    analisis = manifiesto.get('analisis') or {}
    areas = analisis.get('areas') or {}
    observaciones = []
    for lote in (manifiesto.get('inspeccion_visual') or {}).get('lotes',[])[:24]:
        for ventana in lote.get('ventanas',[]):
            observaciones.append(dict(id=ventana.get('id'),
                areas={k:v for k,v in (ventana.get('areas') or {}).items()
                    if k in ('personajes','materiales_luz_color','camara_animacion')},
                evidencias=ventana.get('evidencias'),incertidumbres=ventana.get('incertidumbres')))
    return dict(id=encargo['id'],diseno=encargo['diseno'],
        guia_visual=analisis.get('guia_visual'),
        tecnicas={k:areas[k] for k in ('visual','animacion') if k in areas},
        observaciones=observaciones,
        cobertura=(manifiesto.get('inspeccion_visual') or {}).get('cobertura'),
        alcance='Solo construcción del personaje. Se omiten narración, voz, música, grafismos y montaje; no se recortan las observaciones seleccionadas.')


def encargo_personaje(encargo,manifiesto):
    datos = _datos_personaje(encargo,manifiesto)
    prompt = contrato()+'''\nDISEÑA SOLO ESTE PERSONAJE, conservando identidad y acabado del estilo.
No construyas un motor ni una biblioteca completa. No redactes análisis, informes
ni ejemplos de escenas. Implementa una sola vez su geometría y controles
articulados; el código de cada escena aportará la coreografía y los tiempos.
No implementes decorados, cámara, partículas, tipografía ni música en este asset.
Conserva el detalle del personaje: reduce trabajo ajeno al rig, no su calidad.
Como es el PRIMER rig de este estilo, parametriza también su APARIENCIA compartida:
declara APARIENCIA_VERSION=1 e implementa aplicar_apariencia(datos), que actualiza
SOLO los globals de esta instancia. Tanto dibujar como estado_base deben leer esos
datos. Esquema estable: pelo=corto|largo|coleta|trenzas|rizado|calvo;
ropa=sudadera|camiseta|camisa|chaqueta|vestido; barba=ninguna|corta|larga;
gafas,pecas,movil booleanos; altura,cuerpo,cabeza factores; edad en años;
colores={piel,pelo,ropa,pantalon,zapatos,acento}, todos #RRGGBB.
Implementa una vez las variantes habituales conservando el acabado de ESTE estilo.
Las próximas identidades solo elegirán datos; no reconstruirán su dibujo.
DATOS:\n'''+json.dumps(datos,ensure_ascii=False,separators=(',',':'))
    if len(prompt)>30000:
        raise ValueError('el encargo del personaje supera 30000 caracteres; requiere revisar su contexto antes de consumir IA, no truncarlo ni ampliar el tiempo')
    return prompt


def encargo_identidad(encargo,manifiesto,base,ayuda):
    """No volver a solicitar el motor: solo identidad y extensiones necesarias."""
    codigo = base['asset']['codigo']
    arbol = ast.parse(codigo)
    funciones = {n.name:ast.unparse(n.args) for n in arbol.body if isinstance(n,ast.FunctionDef)}
    clases = {n.name:{f.name:ast.unparse(f.args) for f in n.body if isinstance(f,ast.FunctionDef)}
        for n in arbol.body if isinstance(n,ast.ClassDef)}
    primitivas = {n.name:ast.unparse(n) for n in arbol.body
        if isinstance(n,ast.ClassDef) and n.name=='_P'}
    # Solo constantes literales: nunca evaluar ni importar el rig en el servidor.
    paletas = {}
    for n in arbol.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            try:
                valor = ast.literal_eval(n.value)
            except (ValueError,TypeError):
                if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='dict' and not n.value.args:
                    try:valor={k.arg:ast.literal_eval(k.value) for k in n.value.keywords}
                    except (ValueError,TypeError):continue
                else:continue
            if (isinstance(valor,dict) and valor and len(json.dumps(valor))<6000
                    and all(isinstance(v,(str,list,tuple)) for v in valor.values())):
                paletas[n.targets[0].id] = valor
    # Esqueleto/estructura de anclas disponibles para personalizar geometría,
    # no toda la implementación del renderer ni otros personajes del reparto.
    geometria = {n.name:ast.get_source_segment(codigo,n) for n in arbol.body
        if isinstance(n,ast.FunctionDef) and n.name in ('estado_base','_fk','_anclas')}
    identidad = _datos_personaje(encargo,manifiesto)
    # La mecánica ya existe: conservar todas las observaciones de identidad y
    # materiales, pero no reenviar coreografía/cámara ni tablas de expresiones.
    identidad['tecnicas'] = {k:v for k,v in identidad['tecnicas'].items() if k=='visual'}
    for ventana in identidad['observaciones']:
        ventana['areas'] = {k:v for k,v in ventana['areas'].items() if k in ('personajes','materiales_luz_color')}
    identidad['alcance'] = 'Solo identidad visual sobre mecánica existente. Se conservan personajes, materiales, evidencias e incertidumbres; se omiten cámara y movimiento ya implementados en la base.'
    datos = dict(identidad,
        base=dict(modulo=base['modulo'],interfaz=base['asset']['interfaz'],funciones=funciones,
            clases=clases,primitivas=primitivas,paletas=paletas,geometria=geometria),
        soporte=dict(modulo=ayuda['modulo'],interfaz=ayuda['asset']['interfaz']))
    prompt = '''DISEÑA LA IDENTIDAD DE ESTE PERSONAJE sobre el rig YA CONSTRUIDO.
NO vuelvas a programar cinemática, IK, interpolación, parpadeo, respiración,
anclas ni renderer. Impórtalos del módulo base inmutable que se ofrece.
Entrega SOLO JSON {tipo:"personaje",concepto,nombre,interfaz,codigo,
muestra:[estado_inicial,estado_final]}. codigo es un módulo Python con
dibujar(lienzo,estado,contexto). Conserva TODA la identidad indicada: proporciones,
rostro, pelo, edad, cuerpo, ropa y accesorios. No basta recolorear al protagonista.
Importa base y soporte y crea UNA instancia privada con soporte.crear(base,
paletas={...},inicial={...},extensiones={...}); guarda la instancia a nivel de
módulo, no la recrees por fotograma. dibujar llama a instancia.dibujar(...).
Exporta también los controles heredados con def __getattr__(nombre):
return getattr(instancia,nombre). La escena debe poder usar estado_base,
plantar_pies, alcanzar_px y los demás helpers documentados de la instancia.
Cada extensión tiene firma funcion(rig,*args_originales) y puede usar rig.helpers,
rig._P, rig.PAL o rig.originales. Añade o sustituye SOLO el dibujo/geometría
que diferencia a ESTE personaje (pelo, rostro, vestuario, forma corporal, etc.).
No heredes barba, sudadera, móvil ni expresión del original si no corresponden.
Puedes ampliar cualquier función y capacidad: no hay catálogo cerrado de poses.
Documenta tus controles nuevos y conserva los controles articulados de la base.
La escena seguirá programando libremente su actuación. Sin imágenes, red,
proveedores ni instalaciones. No ejecutes código. No dupliques el motor base.
Si falta información de una función de dibujo, puedes implementar esa extensión
con geometría propia usando PIL y las anclas documentadas; no reinventes IK.
DATOS:\n'''+json.dumps(datos,ensure_ascii=False,separators=(',',':'))
    # Identidad visual + interfaz técnica comprobada: presupuesto distinto del
    # encargo inicial, sin recortar evidencias para hacer hueco al contrato del rig.
    if len(prompt)>40000:
        raise ValueError('la identidad y la interfaz de rig superan 40000 caracteres; revisar sin truncar ni consumir IA')
    return prompt


def fijar_dependencias(dato,referencias):
    """Fija solo imports explícitos; no persiste dependencias inventadas por IA."""
    if not isinstance(dato,dict) or not isinstance(dato.get('codigo'),str):
        raise ValueError('la identidad necesita código de dibujo')
    usados = set()
    for n in ast.walk(ast.parse(dato['codigo'])):
        if isinstance(n,ast.Import):usados.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom):usados.add((n.module or '').split('.')[0])
    deps = {n:r for n,r in referencias.items() if n in usados}
    if set(deps)!=set(referencias):
        raise ValueError('la identidad debe importar el rig compartido y su soporte, no reconstruir otro rig')
    return dict(dato,dependencias=deps)


def preparar(proyecto,marca,espacio,manifiesto,reparto,plan,consultar,avisar,params=None):
    from pasos import reparto_animaciones,biblioteca_estilo
    estilo = marca['huella']
    biblioteca = biblioteca_estilo.sembrar(proyecto,espacio,estilo)
    if biblioteca is None:
        # Compatibilidad con versiones antiguas, sin modificar su paquete sellado.
        base = dict(tipo='objeto',concepto='utileria_base',nombre='Casas, edificios, árboles y móviles parametrizables',
            codigo=BASE.read_text(encoding='utf-8'),interfaz='dibujar(lienzo,estado,contexto). estado: tipo=casa|edificio|arbol|movil; x,y centro normalizado; w,h tamaño normalizado; contorno #hex, trazo fracción de ancho. Casas/edificios: fachada,tejado,cristal,puerta #hex; filas,columnas. Árbol: tronco,follaje #hex. Móvil: carcasa,pantalla,detalle,mensaje #hex y progreso 0..1. Devuelve centro/base en píxeles. Base opcional ampliable: adapta materiales al estilo; si no basta, crea otro recurso detallado, sin simplificar la escena.')
        ref = guardar(proyecto,estilo,base)
        publicar(proyecto,{'base':ref},compartir=False)
    recursos = catalogo(proyecto,estilo)
    ruta_base = raiz(proyecto)/'rig_base.json'
    ref_base = leer_json(str(ruta_base),None,estricto=True)
    base_compartida = carpeta_catalogo()/estilo/'rig_base.json'
    if ref_base is None and base_compartida.exists():
        ref_compartida = leer_json(str(base_compartida),estricto=True)
        if not isinstance(ref_compartida,dict):
            raise ValueError('referencia de rig compartido no válida')
        ref_base = traer(proyecto,estilo,ref_compartida.get('huella'))
        escribir_json(str(ruta_base),ref_base)
    if ref_base:
        if cargar(proyecto,ref_base)['estilo'] != estilo:
            raise ValueError('el rig base pertenece a otro estilo')
    ref_soporte = soporte(proyecto,estilo)
    personajes = {}
    # Orden narrativo, no alfabético. Se preparan TODOS antes de animar, como
    # requiere la identidad estable del reparto, sin personajes secundarios primero.
    ids = list(dict.fromkeys(ident for e in plan.get('escenas',[]) if not e.get('medio_usuario') for ident in visibles(e)))
    proveedores = reparto_animaciones.proveedores([dict(id=ident) for ident in ids],params or {})
    if any(ident not in reparto for ident in ids):
        raise ValueError('faltan las definiciones del reparto para preparar los personajes antes de animar')
    referencias = [str(p) for p in sorted((espacio/'referencias').glob('*.jpg'))]
    for indice,ident in enumerate(ids):
        def avisar_personaje(valor,texto=''):
            avisar(valor,f'Personaje {indice+1} de {len(ids)} · {ident} · {texto}')
        encargo = dict(id=ident,diseno=reparto[ident],analisis=manifiesto.get('analisis'),
            observaciones=[dict(conclusiones=l.get('conclusiones',''),ventanas=l.get('ventanas',[]))
                for l in (manifiesto.get('inspeccion_visual') or {}).get('lotes',[])[:24]])
        clave = espacio_estilo.huella([VERSION,estilo,encargo])
        ruta = raiz(proyecto)/'personajes'/(clave+'.json')
        compartida = carpeta_catalogo()/estilo/'personajes'/(clave+'.json')
        # Dos vídeos del mismo estilo no deben pagar simultáneamente el mismo
        # personaje. Cerrojo acotado: si otro lo prepara, no lanzar otra consulta.
        with lock_de(str(ruta)), lock_de(str(compartida)):
            ref = leer_json(str(ruta),None,estricto=True)
            if ref is None and compartida.exists():
                ref_compartida = leer_json(str(compartida),estricto=True)
                if not isinstance(ref_compartida,dict) or not HUELLA.fullmatch(str(ref_compartida.get('huella',''))):
                    raise ValueError('referencia de personaje compartido no válida')
                dato = leer_json(str(carpeta_catalogo()/estilo/'recursos'/(ref_compartida['huella']+'.json')),estricto=True)
                if not dato or dato.get('estilo') != estilo or espacio_estilo.huella(dato) != ref_compartida['huella']:
                    raise ValueError('personaje compartido incompleto o alterado')
                ref = traer(proyecto,estilo,ref_compartida['huella'])
            if ref is None:
                avisar(None,f'Preparando personaje {indice+1} de {len(ids)}: {ident}; antes de animar escenas')
                cruda = ruta.with_suffix('.entrega.json')
                dato = leer_json(str(cruda),None,estricto=True)
                correccion = leer_json(str(ruta.with_suffix('.correccion.json')),None,estricto=True)
                if correccion is not None:
                    if (dato is None or not isinstance(correccion,dict)
                            or correccion.get('huella_original') != espacio_estilo.huella(dato)):
                        raise ValueError('la corrección local no corresponde a la entrega original; no se consultará IA')
                    dato = correccion['entrega']
                if dato is None:
                    referencias_rig = {}
                    if ref_base:
                        modulo_base='asset_'+ref_base['huella'][:24]
                        modulo_soporte='asset_'+ref_soporte['huella'][:24]
                        referencias_rig={modulo_base:ref_base,modulo_soporte:ref_soporte}
                        base_rig = cargar(proyecto,ref_base)
                        perfil = perfil_apariencia(base_rig)
                        pendiente_legacy = (ruta.with_suffix('.base.json').exists()
                            and not ruta.with_suffix('.apariencia.json').exists())
                        if perfil and not pendiente_legacy:
                            ref_apariencias = soporte_apariencias(proyecto,estilo)
                            modulo_apariencias = 'asset_'+ref_apariencias['huella'][:24]
                            referencias_rig[modulo_apariencias] = ref_apariencias
                            configuracion = dict(perfil=perfil,base=modulo_base,
                                soporte=modulo_soporte,apariencias=modulo_apariencias)
                            escribir_json(str(ruta.with_suffix('.apariencia.json')),configuracion)
                            prompt = encargo_apariencia(encargo,manifiesto,
                                dict(base_rig,modulo=modulo_base),
                                dict(cargar(proyecto,ref_soporte),modulo=modulo_soporte))
                        else:
                            avisar_personaje(None,'Rig antiguo sin contrato de apariencia: se conservan extensiones de identidad')
                            prompt=encargo_identidad(encargo,manifiesto,
                                dict(base_rig,modulo=modulo_base),
                                dict(cargar(proyecto,ref_soporte),modulo=modulo_soporte))
                    else:
                        prompt = encargo_personaje(encargo,manifiesto)
                    if referencias_rig:
                        # También antes de consultar: una interrupción tras la
                        # entrega no debe perder sus imports inmutables.
                        escribir_json(str(ruta.with_suffix('.base.json')),referencias_rig)
                    dato = consultar(proveedores[ident],prompt,referencias,avisar_personaje,recuperacion=ruta.with_suffix('.consulta'))
                    escribir_json(str(cruda),dato)  # antes de validar o ejecutar
                dependencias = leer_json(str(ruta.with_suffix('.base.json')),None,estricto=True)
                configuracion = leer_json(str(ruta.with_suffix('.apariencia.json')),None,estricto=True)
                if configuracion:
                    if not dependencias or configuracion.get('base') not in dependencias:
                        raise ValueError('faltan las dependencias de la apariencia conservada; no se consultará IA')
                    dato = compilar_apariencia(dato,cargar(proyecto,dependencias[configuracion['base']]),configuracion,dependencias)
                elif isinstance(dato,dict) and dato.get('formato')=='apariencia/1':
                    raise ValueError('falta el contrato de la apariencia guardada; no se consultará IA')
                elif dependencias:
                    dato = fijar_dependencias(dato,dependencias)
                if not isinstance(dato,dict) or dato.get('tipo') != 'personaje':
                    raise ValueError('la preparación debe entregar el asset del personaje, no una escena')
                ref = guardar(proyecto,estilo,dato)
                comprobar_personaje(proyecto,espacio,ref,ruta.with_suffix('.muestra'),avisar_personaje)
                publicar(proyecto,{'personaje':ref})
                escribir_json(str(compartida),{'huella':ref['huella']})
            cargar(proyecto,ref)
            escribir_json(str(ruta),ref)
            if ref_base is None:
                # Solo un rig comprobado, nunca un borrador fallido, se ofrece
                # como mecánica común. La fuente original permanece intacta.
                ref_base = ref
                escribir_json(str(ruta_base),ref_base)
            with lock_de(str(base_compartida)):
                if not base_compartida.exists():
                    publicar(proyecto,{'rig_base':ref_base})
                    escribir_json(str(base_compartida),{'huella':ref_base['huella']})
        modulo = 'asset_'+ref['huella'][:24]
        recursos[modulo] = ref
        personajes[ident] = modulo
    anonimos = None
    if ref_base:
        modulo_base = 'asset_'+ref_base['huella'][:24]
        recursos[modulo_base] = ref_base
        ref_personas = personas_del_estilo(proyecto,estilo,ref_base,ref_soporte)
        anonimos = 'asset_'+ref_personas['huella'][:24]
        recursos[anonimos] = ref_personas
    return dict(recursos=recursos,personajes=personajes,personas_anonimas=anonimos)


def comprobar_personaje(proyecto,espacio,ref,salida,avisar):
    from pasos import animacion_nativa
    dato = cargar(proyecto,ref)['asset']
    # Solo geometría local. No se importa el módulo en el proceso del servicio.
    codigo = '''from PIL import Image
import recurso_muestra
def preparar(pedido):
    if hasattr(recurso_muestra,'preparar'):
        recurso_muestra.preparar(dict(ancho=pedido['ancho'],alto=pedido['alto'],duracion=2))
def mezclar(a,b,u):
    if isinstance(a,dict) and isinstance(b,dict):
        return {k:mezclar(v,b.get(k,v),u) for k,v in a.items()} | {k:v for k,v in b.items() if k not in a}
    if type(a) in (int,float) and type(b) in (int,float): return a+(b-a)*u
    return b if u>=1 else a
def pintar(pedido,t):
    im=Image.new('RGB',(pedido['ancho'],pedido['alto']),'#202838')
    a,b=pedido['muestra']
    recurso_muestra.dibujar(im,mezclar(a,b,min(1,t/1.5)),dict(ancho=im.width,alto=im.height,t=t,duracion=2))
    return im
'''
    archivos = espacio_estilo.renderizar(espacio,dict(imagen='',ancho=640,alto=360,fps=12,duracion=2,
        escena={},parametros={},muestra=dato['muestra']),salida,avisar,codigo_escena=codigo,
        herramientas_escena=fuentes(proyecto,{'recurso_muestra':ref}))
    control = animacion_nativa.comprobar_movimiento(archivos['clip'],salida,12)
    escribir_json(str(Path(salida)/'comprobacion.json'),control)


def contexto(proyecto,preparados,escena):
    from motores.estilo_ia.apariencias import ESQUEMA,DEFECTO
    fichas = []
    for modulo,ref in preparados['recursos'].items():
        dato = cargar(proyecto,ref)['asset']
        fichas.append(dict(modulo=modulo,**{k:dato[k] for k in ('tipo','concepto','nombre','interfaz')}))
    return dict(personajes={i:preparados['personajes'][i] for i in visibles(escena)},catalogo=fichas,contrato_recursos=contrato(),
        personas_anonimas=preparados.get('personas_anonimas'),
        apariencia_personas=dict(esquema=ESQUEMA,valores_iniciales=DEFECTO),
        reglas_estilo='El acabado del catálogo es obligatorio para TODOS los sujetos, también personas sin nombre, parejas, multitudes y siluetas. Si no tienen ID del reparto, usa personas_anonimas.crear y su dibujar con apariencia/1. No dibujes otro monigote desde cero ni simplifiques rostro/cuerpo/ropa por falta de nombre. Las siluetas solicitadas usan la misma geometría del rig con máscara de color. Los recursos nuevos amplían el acabado, no lo sustituyen por otro estilo.',
        instrucciones='El programa de la escena sigue siendo libre. Importa los módulos y usa sus dibujos/rigs; no reescribas las identidades del reparto. Puedes extenderlos con código de actuación, composición y dibujo adicional. La utilería base es solo apoyo geométrico: adapta materiales, luz y detalle al análisis; nunca empobrezcas la escena por ceñirte a esa base. Si falta un recurso o detalle, entrega recursos_nuevos:{nombre_modulo:{tipo,concepto,nombre,codigo,interfaz,muestra opcional}} junto al codigo de la escena, e impórtalo por ese nombre. Cada recurso nuevo es autocontenido y declara dibujar(lienzo,estado,contexto). No generes imágenes ni una biblioteca monolítica. No devuelvas un plan limitado a instancias: devuelve siempre codigo completo para esta escena.')


def contrato_estilo(preparados,escena):
    anonimos = preparados.get('personas_anonimas')
    if not anonimos:
        return None  # Fuente/estilo histórico sin base: no inventar un rig al leer.
    descripcion = str(escena.get('descripcion_visual') or '').casefold()
    # Guardia conservadora para que «siluetas» etiquetadas como objeto/gráfico no
    # eludan el uso del rig. No es un intérprete semántico ni sustituye revisión.
    sujetos = re.findall(r'\b(?:personas?|personajes?|hombres?|mujeres?|parejas?|siluetas?|protagonistas?|vecin[oa]s?|niñ[oa]s?)\b',descripcion)
    sin_personas = bool(re.search(r'\b(?:sin personas|sin personajes|no hay personas)\b',descripcion))
    return dict(version=1,personas=sorted(set(preparados['personajes'].values())|{anonimos}),
        requiere_personas=bool(visibles(escena) or (sujetos and not sin_personas)))


def _imports_recursos(arbol,disponibles):
    """Imports estáticos y wrappers simples de __import__, sin ejecutar código."""
    wrappers = {}
    for n in arbol.body:
        if not isinstance(n,ast.FunctionDef):continue
        retornos = [x.value for x in ast.walk(n) if isinstance(x,ast.Return)
            and x.value is not None and not (isinstance(x.value,ast.Constant) and x.value.value is None)]
        args = [a.arg for a in n.args.posonlyargs+n.args.args]
        if retornos and all(isinstance(x,ast.Call) and isinstance(x.func,ast.Name)
                and x.func.id=='__import__' and len(x.args)==1 and not x.keywords
                and isinstance(x.args[0],ast.Name) and x.args[0].id in args for x in retornos):
            indices = {args.index(x.args[0].id) for x in retornos}
            if len(indices)==1:wrappers[n.name] = indices.pop()
    usados,alias = set(),{}
    for n in ast.walk(arbol):
        if isinstance(n,ast.Import):
            for a in n.names:
                if a.name in disponibles:
                    usados.add(a.name);alias[a.asname or a.name] = a.name
        elif isinstance(n,ast.ImportFrom) and n.module=='recursos_animacion':
            for a in n.names:
                if a.name not in disponibles:
                    raise ValueError('recurso importado no disponible: '+a.name+' (from recursos_animacion)')
                usados.add(a.name);alias[a.asname or a.name] = a.name
        elif isinstance(n,ast.ImportFrom) and n.module in disponibles:
            usados.add(n.module)
        elif isinstance(n,(ast.Assign,ast.AnnAssign)):
            v = n.value
            if not isinstance(v,ast.Call) or not isinstance(v.func,ast.Name):continue
            indice = 0 if v.func.id=='__import__' else wrappers.get(v.func.id)
            if indice is None or len(v.args)<=indice:continue
            nombre = v.args[indice]
            if not isinstance(nombre,ast.Constant) or not isinstance(nombre.value,str) or nombre.value not in disponibles:continue
            usados.add(nombre.value)
            for t in n.targets if isinstance(n,ast.Assign) else [n.target]:
                if isinstance(t,ast.Name):alias[t.id] = nombre.value
    return usados,alias


def vincular(proyecto,estilo,entrega,herramientas,escena):
    disponibles = dict(entrega.get('recursos_disponibles') or {})
    nuevos = entrega['respuesta'].get('recursos_nuevos') or {}
    if not isinstance(nuevos,dict) or len(nuevos) > 20:
        raise ValueError('recursos_nuevos debe ser un objeto de hasta 20 módulos autocontenidos')
    for nombre,dato in nuevos.items():
        if (not espacio_estilo.nombre_modulo_valido(nombre) or nombre in herramientas
                or nombre in sys.stdlib_module_names or nombre in ('recurso_muestra','escena_nativa','motor_del_estilo','recursos_animacion')):
            raise ValueError('nombre de recurso nuevo no válido o reservado: '+str(nombre))
        ref = guardar(proyecto,estilo,dato)
        if nombre in disponibles and disponibles[nombre]!=ref:
            raise ValueError('el recurso nuevo intenta sustituir otro recurso disponible: '+nombre)
        disponibles[nombre] = ref
    arbol = ast.parse(entrega['respuesta'].get('codigo',''))
    usados,_ = _imports_recursos(arbol,disponibles)
    for ident in visibles(escena):
        modulo = (entrega.get('personajes_recursos') or {}).get(ident)
        if not modulo or modulo not in usados:
            raise ValueError('la escena debe reutilizar el rig preparado del personaje: '+str(ident))
    if 'contrato_estilo' in entrega:
        _validar_personas_estilo(proyecto,entrega,disponibles,usados,arbol)
    referencias = {n:disponibles[n] for n in sorted(usados)}
    modulos = fuentes(proyecto,referencias)
    agrupados = {a.name for n in ast.walk(arbol) if isinstance(n,ast.ImportFrom)
        and n.module=='recursos_animacion' for a in n.names}
    if agrupados:
        # Fachada SOLO en las herramientas temporales del renderer. Los módulos
        # reales siguen fijados por SHA; no importar el código de pasos/ allí.
        if 'recursos_animacion' in herramientas or 'recursos_animacion' in modulos:
            raise ValueError('colisión con la fachada de recursos de la escena')
        modulos['recursos_animacion'] = '\n'.join('import '+n for n in sorted(agrupados))+'\n'
    return modulos,referencias


def _validar_personas_estilo(proyecto,entrega,disponibles,usados,arbol):
    """Guardas de reutilización, no una certificación semántica de los píxeles."""
    contrato = entrega['contrato_estilo']
    if not isinstance(contrato,dict) or contrato.get('version')!=1:
        raise ValueError('contrato de reutilización del estilo incompleto')
    permitidos = contrato.get('personas')
    if not isinstance(permitidos,list) or any(not isinstance(n,str) or n not in disponibles for n in permitidos):
        raise ValueError('faltan los módulos de personas fijados por el contrato de estilo')
    respuesta = entrega['respuesta']
    acciones = respuesta.get('acciones') or []
    personas = (contrato.get('requiere_personas') is True
        or any(isinstance(a,dict) and a.get('tipo')=='personaje' for a in acciones)
        or any(isinstance(a,dict) and a.get('tipo')=='personaje' for a in (respuesta.get('recursos_nuevos') or {}).values()))
    if not personas:
        return
    # Un import sin una llamada al dibujo no cierra el agujero original.
    _,alias = _imports_recursos(arbol,disponibles)
    modulos,funciones = {a:m for a,m in alias.items() if m in permitidos},{}
    for n in ast.walk(arbol):
        if isinstance(n,ast.Import):
            modulos.update({a.asname or a.name:a.name for a in n.names if a.name in usados and a.name in permitidos})
        elif isinstance(n,ast.ImportFrom) and n.module in usados and n.module in permitidos:
            funciones.update({a.asname or a.name:(n.module,a.name) for a in n.names})
    auxiliares = {n.name:n for n in arbol.body if isinstance(n,ast.FunctionDef)}
    fabricas = set()
    def fabrica(n):
        if not isinstance(n,ast.Call):return False
        f = n.func
        return ((isinstance(f,ast.Attribute) and isinstance(f.value,ast.Name) and f.value.id in modulos and f.attr=='crear')
            or (isinstance(f,ast.Name) and ((f.id in funciones and funciones[f.id][1]=='crear') or f.id in fabricas)))
    # Una auxiliar solo es fábrica si todos sus retornos efectivos proceden
    # del crear permitido (se tolera None como salida de error, no otro rig).
    for _ in range(len(auxiliares)):
        antes = set(fabricas)
        for nombre,funcion in auxiliares.items():
            retornos = [x.value for x in ast.walk(funcion) if isinstance(x,ast.Return)
                and x.value is not None and not (isinstance(x.value,ast.Constant) and x.value.value is None)]
            if retornos and all(fabrica(x) for x in retornos):fabricas.add(nombre)
        if fabricas==antes:break
    instancias = set()
    ambitos = {}
    def ubicar(n,ambito=None):
        if isinstance(n,ast.FunctionDef):ambito = n.name
        ambitos[id(n)] = ambito
        for hijo in ast.iter_child_nodes(n):ubicar(hijo,ambito)
    ubicar(arbol)
    parametros = {nombre:{a.arg for a in f.args.posonlyargs+f.args.args+f.args.kwonlyargs}
        for nombre,f in auxiliares.items()}
    def ruta(n):
        if isinstance(n,ast.Name):
            ambito = ambitos.get(id(n))
            return (ambito if n.id in parametros.get(ambito,set()) else None,n.id)
        if isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Constant):
            base = ruta(n.value)
            if base is not None:return (base,n.slice.value)
        return None
    def deriva(n):
        # Un rig preparado puede usarse como módulo, no solo como crear().
        # S173 guarda esos módulos en RIGS y llama RIGS[i].dibujar.
        if isinstance(n,ast.Name) and n.id in modulos:return True
        clave = ruta(n)
        if clave is not None and clave in instancias:return True
        if fabrica(n):return True
        if isinstance(n,(ast.List,ast.Tuple,ast.Set)):
            return any(deriva(x) for x in n.elts)
        if isinstance(n,ast.IfExp):
            return deriva(n.body) or deriva(n.orelse)
        if isinstance(n,ast.Subscript):
            # Índice de una secuencia de personas; una clave de diccionario
            # fijada se sigue por su ruta, no contamina todas las demás claves.
            return deriva(n.value)
        if isinstance(n,(ast.ListComp,ast.SetComp,ast.GeneratorExp)):
            return deriva(n.elt)
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('zip','enumerate','list','tuple'):
            return any(deriva(x) for x in n.args)
        return False
    nodos = list(ast.walk(arbol))
    # Propaga alias/listas/comprensiones y variables de bucle para parejas y
    # multitudes, sin restringirlas a dos variables de nombre prefijado.
    for _ in range(len(nodos)):
        antes = set(instancias)
        for n in nodos:
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in auxiliares:
                funcion = auxiliares[n.func.id]
                args = funcion.args.posonlyargs+funcion.args.args
                enlaces = [(a.arg,v) for a,v in zip(args,n.args)]
                enlaces += [(k.arg,k.value) for k in n.keywords if k.arg in parametros[n.func.id]]
                for nombre,valor in enlaces:
                    if deriva(valor):instancias.add((n.func.id,nombre))
            if (isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
                    and n.func.attr in ('append','extend') and n.args and deriva(n.args[0])):
                clave = ruta(n.func.value)
                if clave is not None:instancias.add(clave)
            expresion = n.value if isinstance(n,(ast.Assign,ast.AnnAssign)) else n.iter if isinstance(n,(ast.For,ast.comprehension)) else None
            if expresion is None:continue
            if deriva(expresion):
                destinos = n.targets if isinstance(n,ast.Assign) else [n.target]
                def guardar(t):
                    clave = ruta(t)
                    if clave is not None:instancias.add(clave)
                    elif isinstance(t,(ast.Tuple,ast.List)):
                        for x in t.elts:guardar(x)
                for t in destinos:guardar(t)
        if instancias==antes:break
    for n in ast.walk(arbol):
        if not isinstance(n,ast.Call):
            continue
        f = n.func
        if (isinstance(f,ast.Name) and f.id in funciones and funciones[f.id][1]=='dibujar'):
            return
        if (isinstance(f,ast.Attribute) and f.attr=='dibujar'
                and ((isinstance(f.value,ast.Name) and f.value.id in modulos) or deriva(f.value))):
            return
    raise ValueError('los personajes anónimos y siluetas también deben dibujarse con el rig del estilo; importa una persona preparada o usa personas_anonimas.crear(...).dibujar, no otro monigote desde cero')
