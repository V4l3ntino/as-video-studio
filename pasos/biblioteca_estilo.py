"""Biblioteca procedural preparada y sellada con el estilo, antes de los vídeos.

No importa ni ejecuta fuentes generadas en el servicio. Los módulos originales
viven en herramientas/ y el vídeo recibe copias de assets por contenido.
"""
import ast
from pathlib import Path
import sys

from nucleo.proyecto import escribir_json, leer_json


PARTES = {'cabeza', 'torso', 'brazos', 'manos', 'piernas', 'pies'}
OBJETOS = {'arbol', 'casa', 'edificio', 'movil'}
MOVIMIENTOS = {'interpolar', 'caminar', 'sentarse', 'saludar'}


def contrato():
    from motores.estilo_ia.apariencias import ESQUEMA
    import json
    return '''
BIBLIOTECA OBLIGATORIA DEL ESTILO, preparada AHORA, NO durante cada vídeo:
Añade al JSON biblioteca:{version:1,rig:"personaje_base",
 partes:["cabeza","torso","brazos","manos","piernas","pies"],
 movimientos:{interpolar:"interpolar",caminar:"caminar",sentarse:"sentarse",saludar:"saludar"},
 recursos:{personaje_base:{tipo:"personaje",concepto,nombre,interfaz,muestra:[estado_a,estado_b]},
 arbol:{tipo:"objeto",concepto,nombre,interfaz,muestra:[estado_a,estado_b]},
 casa:{...},edificio:{...},movil:{...}}}.
Cada entrada n corresponde a archivos["herramientas/"+n+".py"]. NO dupliques
su código dentro de biblioteca. Los módulos de assets son AUTOCONTENIDOS: PIL y
biblioteca estándar, sin importar otros assets ni ficheros externos. Cada uno
implementa dibujar(lienzo,estado,contexto), con PIL.Image, estado libre y contexto
{ancho,alto,t,duracion}. Documenta unidades, valores iniciales y anclas devueltas.
Cada muestra contiene DOS estados distintos y completos que cambien el dibujo;
en el monigote cambia articulaciones, no solo x/y/zoom. En objetos prueba variantes
paramétricas visibles. El motor pintar debe usar estos módulos, no otro dibujo
duplicado de los mismos personajes/objetos.
El rig comparte torso, brazos, manos, piernas, pies y cabeza, articulaciones, IK,
interpolación, mirada y expresión. Declara APARIENCIA_VERSION=1 e implementa
aplicar_apariencia(datos), que modifica SOLO los globals de la instancia privada.
dibujar y estado_base deben leer la apariencia. Implementa una sola vez variantes
de ropa, pelo y proporciones CON EL ACABADO DE ESTE ESTILO, no un monigote genérico.
Esquema de apariencia/1: '''+json.dumps(ESQUEMA,ensure_ascii=False)+'''.
Las funciones de movimientos viven en el módulo del rig: interpolar(a,b,u) devuelve
estado interpolado; caminar(t), sentarse(u) y saludar(t) devuelven ajustes de estado
articulado combinables. No son clips cerrados: las escenas siguen teniendo código
libre para cualquier actuación, y los recursos admiten extensiones excepcionales.
La interfaz del rig debe documentar TODOS esos controles, funciones y unidades.
Árbol/casa/edificio/móvil deben tener materiales y geometría parametrizables con
el acabado observado; no pegues imágenes ni fotogramas de referencia. Incluye
elementos adicionales propios del estilo cuando hagan falta. Los vídeos elegirán
datos de identidad y coreografías, NO reconstruirán esta biblioteca.
'''


def validar(biblioteca,archivos):
    from pasos import recursos_animacion as recursos
    if (not isinstance(biblioteca,dict) or type(biblioteca.get('version')) is not int
            or biblioteca['version']!=1):
        raise ValueError('el estilo necesita biblioteca procedural version 1')
    entradas = biblioteca.get('recursos')
    rig = biblioteca.get('rig')
    if (not isinstance(entradas,dict) or not 5<=len(entradas)<=40
            or not isinstance(rig,str) or rig not in entradas or not OBJETOS.issubset(entradas)):
        raise ValueError('la biblioteca necesita rig, arbol, casa, edificio y movil')
    partes = biblioteca.get('partes')
    if not isinstance(partes,list) or any(not isinstance(p,str) for p in partes) or not PARTES.issubset(partes):
        raise ValueError('el rig debe declarar cabeza, torso, brazos, manos, piernas y pies')
    movimientos = biblioteca.get('movimientos')
    if not isinstance(movimientos,dict) or set(movimientos)!=MOVIMIENTOS:
        raise ValueError('la biblioteca necesita interpolar, caminar, sentarse y saludar')
    salida = {}
    for modulo,ficha in entradas.items():
        if (not isinstance(modulo,str) or not recursos.MODULO.fullmatch(modulo)
                or modulo in sys.stdlib_module_names
                or modulo in ('recurso_muestra','motor_del_estilo','escena_nativa')
                or not isinstance(ficha,dict) or 'codigo' in ficha or 'dependencias' in ficha):
            raise ValueError('entrada de biblioteca no válida; el código va en herramientas/<modulo>.py')
        codigo = archivos.get('herramientas/'+modulo+'.py')
        asset = recursos.validar(dict(ficha,codigo=codigo))
        if asset['tipo']=='herramienta':
            raise ValueError('los assets de biblioteca deben implementar dibujar; los auxiliares van fuera del registro')
        muestra = asset.get('muestra')
        if (not isinstance(muestra,list) or len(muestra)!=2 or muestra[0]==muestra[1]
                or any(not isinstance(e,dict) or not e for e in muestra)):
            raise ValueError('cada recurso de biblioteca necesita dos estados de muestra diferentes')
        if modulo==rig:
            if asset['tipo']!='personaje' or recursos.perfil_apariencia(dict(asset=asset))!='nativo_v1':
                raise ValueError('el rig de biblioteca debe implementar APARIENCIA_VERSION=1 y aplicar_apariencia')
            funciones = {n.name for n in ast.parse(codigo).body if isinstance(n,ast.FunctionDef)}
            if ('estado_base' not in funciones or any(not isinstance(n,str) or n not in funciones
                    for n in movimientos.values())):
                raise ValueError('faltan funciones de estado o movimientos declarados en el rig')
        elif modulo in OBJETOS and asset['tipo']!='objeto':
            raise ValueError('los elementos básicos deben ser assets de tipo objeto')
        salida[modulo] = {k:v for k,v in asset.items() if k!='codigo'}
    return dict(version=1,rig=rig,partes=sorted(set(partes)),movimientos=dict(movimientos),recursos=salida)


def leer(espacio):
    paquete = leer_json(str(Path(espacio)/'paquete.json'),estricto=True)
    if 'biblioteca' not in paquete:
        return None  # Versión histórica: no reescribirla ni generar nada al leer.
    biblioteca = validar(paquete['biblioteca'],paquete['archivos'])
    for nombre in biblioteca['recursos']:
        ruta = Path(espacio)/'herramientas'/(nombre+'.py')
        if ruta.read_text(encoding='utf-8')!=paquete['archivos']['herramientas/'+nombre+'.py']:
            raise ValueError('un asset de biblioteca sellado ha cambiado; no se regenerará')
    return biblioteca


def sembrar(proyecto,espacio,estilo):
    """Solo copias y validación estática. Sin proveedor, instalaciones ni renderer."""
    from pasos import recursos_animacion as recursos
    biblioteca = leer(espacio)
    if biblioteca is None:
        return None
    referencias = {}
    for nombre,ficha in biblioteca['recursos'].items():
        codigo = (Path(espacio)/'herramientas'/(nombre+'.py')).read_text(encoding='utf-8')
        ref = recursos.guardar(proyecto,estilo,dict(ficha,codigo=codigo))
        referencias['asset_'+ref['huella'][:24]] = ref
        if nombre==biblioteca['rig']:
            base = ref
    recursos.publicar(proyecto,referencias,compartir=False)
    ruta = recursos.raiz(proyecto)/'rig_base.json'
    previa = leer_json(str(ruta),None,estricto=True)
    if previa is None:
        escribir_json(str(ruta),base)
    elif recursos.cargar(proyecto,previa)['estilo']!=estilo:
        raise ValueError('la base guardada no corresponde al estilo de la biblioteca')
    return referencias


def comprobar(espacio,biblioteca,avisar):
    """Prueba por módulo y movimientos antes de sellar/publicar la versión."""
    from motores.estilo_ia.apariencias import DEFECTO
    from pasos import espacio_estilo,animacion_nativa
    for nombre,ficha in biblioteca['recursos'].items():
        avisar(None,'Comprobando asset básico del estilo: '+nombre)
        es_rig = nombre==biblioteca['rig']
        codigo = f'''from PIL import Image
import {nombre} as recurso
def preparar(pedido):
    if hasattr(recurso,'preparar'):
        recurso.preparar(dict(ancho=pedido['ancho'],alto=pedido['alto'],duracion=2,t=0))
def mezclar(a,b,u):
    if isinstance(a,dict) and isinstance(b,dict):
        return {{k:mezclar(v,b.get(k,v),u) for k,v in a.items()}} | {{k:v for k,v in b.items() if k not in a}}
    if type(a) in (int,float) and type(b) in (int,float):return a+(b-a)*u
    return b if u>=1 else a
def pintar(pedido,t):
    im=Image.new('RGB',(pedido['ancho'],pedido['alto']),'#202838')
    a,b=pedido['muestra']
    estado=mezclar(a,b,min(1,t/1.5))
'''
        if es_rig:
            movimientos = biblioteca['movimientos']
            codigo += f'''    aspecto=dict({DEFECTO!r})
    if t>=1:aspecto.update(pelo='trenzas',ropa='camisa',gafas=True,cuerpo=.85)
    recurso.aplicar_apariencia(aspecto)
    estado=recurso.{movimientos['interpolar']}(a,b,min(1,t/1.5))
    assert isinstance(estado,dict), 'interpolar debe devolver estado'
    for funcion,valor in ((recurso.{movimientos['caminar']},t),(recurso.{movimientos['sentarse']},min(1,t/2)),(recurso.{movimientos['saludar']},t)):
        assert isinstance(funcion(valor),dict), 'los movimientos deben devolver ajustes de estado'
    funciones=(recurso.{movimientos['caminar']},recurso.{movimientos['sentarse']},recurso.{movimientos['saludar']})
    estado.update(funciones[min(2,int(t*1.5))](min(1,t)))
'''
        codigo += '''    recurso.dibujar(im,estado,dict(ancho=im.width,alto=im.height,t=t,duracion=2))
    return im
'''
        salida = Path(espacio)/'muestra'/'biblioteca'/nombre
        archivos = espacio_estilo.renderizar(espacio,dict(ancho=640,alto=360,fps=12,duracion=2,
            escena={},parametros={},muestra=ficha['muestra']),salida,avisar,codigo_escena=codigo)
        control = animacion_nativa.comprobar_movimiento(archivos['clip'],salida,12)
        escribir_json(str(salida/'comprobacion.json'),control)
