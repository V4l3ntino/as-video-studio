"""Programas libres con assets reutilizables; FFmpeg real, IA y datos aislados."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='recursos_animacion_')
for k in ('ESTUDIO_SECRETOS','ESTUDIO_AJUSTES','ESTUDIO_ESTADISTICAS','ESTUDIO_RECURSOS_ANIMACION'):
    os.environ[k] = str(Path(_DATOS.name)/k)

from nucleo.proyecto import Proyecto, escribir_json, leer_json
from pasos import recursos_animacion as recursos, animacion_nativa as nativa, espacio_estilo as espacio, p6_assets
from nucleo.trabajos import Cancelado

CODIGO = '''import math
from PIL import Image, ImageDraw
def pintar(pedido,t):
    w,h=pedido['ancho'],pedido['alto']; im=Image.new('RGB',(w,h),'#182039'); d=ImageDraw.Draw(im)
    a=1.2-2.4*min(1,t/pedido['duracion'])
    d.ellipse((w*.4,h*.1,w*.6,h*.3),fill='white')
    d.line([(w*.5,h*.3),(w*.5,h*.8)],fill='white',width=5)
    d.line([(w*.5,h*.4),(w*(.5+.2*math.cos(a)),h*(.4+.3*math.sin(a)))],fill='white',width=5)
    return im
'''
ACTOR = dict(tipo='personaje',concepto='persona',nombre='Persona articulada',interfaz='dibujar(im,estado,contexto): x,y pies normalizados; brazo en radianes. Devuelve mano en píxeles.',
    codigo='''import math
from PIL import ImageDraw
def dibujar(im,estado,contexto):
    W,H=im.size; x=estado.get('x',.5)*W; y=estado.get('y',.9)*H
    d=ImageDraw.Draw(im); a=estado.get('brazo',1.2)
    d.ellipse((x-.06*W,y-.65*H,x+.06*W,y-.45*H),fill='white')
    d.line([(x,y-.45*H),(x,y-.12*H)],fill='white',width=5)
    mano=(x+.18*W*math.cos(a),y-.35*H+.24*H*math.sin(a))
    d.line([(x,y-.35*H),mano],fill='white',width=5)
    d.line([(x-.08*W,y),(x,y-.12*H),(x+.08*W,y)],fill='white',width=4)
    return {'mano':mano}
''',muestra=[dict(x=.5,y=.9,brazo=1.2),dict(x=.5,y=.9,brazo=-1.2)])
ARBOL = dict(tipo='objeto',concepto='arbol_azul',nombre='Árbol especial azul',interfaz='dibujar(im,estado,contexto): x,y centro normalizado; copa azul, tronco marrón.',codigo='''from PIL import ImageDraw
def dibujar(im,estado,contexto):
    W,H=im.size; x=estado.get('x',.8)*W; y=estado.get('y',.5)*H; d=ImageDraw.Draw(im)
    d.rectangle((x-.01*W,y,x+.01*W,y+.3*H),fill='#906844')
    d.ellipse((x-.1*W,y-.2*H,x+.1*W,y+.12*H),fill='#35a5ff')
''')


def entrega(codigo=CODIGO,**campos):
    return dict(codigo=codigo,acciones=[dict(tipo='personaje',objetivo='actor',accion='Levanta el brazo',
        claves=[dict(t=0,estado={'brazo':1.2}),dict(t=2,estado={'brazo':-1.2})])],
        edicion='Plano general con actuación, corte directo.',**campos)


def datos_prompt(prompt):
    return json.loads(prompt[prompt.index('{"escena":'):])


def programa_personajes(modulos):
    codigo='from PIL import Image\n'
    for i,modulo in enumerate(modulos):
        codigo+=f'from {modulo} import dibujar as actor_{i}\n'
    codigo+="def pintar(pedido,t):\n    im=Image.new('RGB',(pedido['ancho'],pedido['alto']),'#182039')\n"
    for i,_ in enumerate(modulos):
        codigo+=f"    actor_{i}(im,dict(x={.3+.35*i},y=.9,brazo=1.2-2.4*t/pedido['duracion']),dict(t=t,ancho=im.width,alto=im.height,duracion=pedido['duracion']))\n"
    return codigo+'    return im\n'


def diseno_personaje(prompt):
    datos=json.loads(prompt.rsplit('\n',1)[1])
    if 'DISEÑA LA IDENTIDAD' not in prompt:
        return dict(copy.deepcopy(ACTOR),nombre=datos['id'],concepto=datos['id'])
    base,soporte=datos['base']['modulo'],datos['soporte']['modulo']
    return dict(copy.deepcopy(ACTOR),nombre=datos['id'],concepto=datos['id'],codigo=f'''import {base} as base
from {soporte} import crear
rig=crear(base)
def dibujar(im,estado,contexto):
    return rig.dibujar(im,estado,contexto)
''')


class Recursos(unittest.TestCase):
    def preparar_anonimos(self):
        self.base_parametrica()
        escena=dict(id='S001',personajes_visibles=[],descripcion_visual='Dos personas anónimas desayunan; otra silueta al fondo.')
        preparados=recursos.preparar(self.proyecto,self.marca,self.espacio,{}, {},{'escenas':[escena]},
            lambda *a,**k:self.fail('Las personas anónimas no deben pedir otro rig a IA'),lambda *a:None)
        return preparados,escena

    def test_personas_anonimas_parejas_y_siluetas_usan_mismo_rig_sin_ia(self):
        from PIL import Image
        preparados,escena=self.preparar_anonimos()
        modulo=preparados['personas_anonimas']
        ctx=recursos.contexto(self.proyecto,preparados,escena)
        self.assertEqual(ctx['personas_anonimas'],modulo)
        codigo=f'''from PIL import Image
import {modulo} as personas
pareja=[personas.crear({{'colores':{{'ropa':'#ff0000'}}}}),personas.crear({{'colores':{{'ropa':'#0000ff'}}}})]
sombra=personas.crear(silueta='#00ff00')
def pintar(pedido,t):
    im=Image.new('RGB',(480,180),'black')
    for persona,x in zip(pareja,(.2,.5)):
        persona.dibujar(im,dict(x=x,y=.9,brazo=1.2-t),dict(t=t))
    sombra.dibujar(im,dict(x=.8,y=.9,brazo=1.2-t),dict(t=t))
    return im
'''
        dato=dict(respuesta=entrega(codigo),recursos_disponibles=preparados['recursos'],
            personajes_recursos=preparados['personajes'],contrato_estilo=recursos.contrato_estilo(preparados,escena))
        modulos,refs=recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)
        archivos=espacio.renderizar(self.espacio,dict(ancho=480,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'anonimos',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
        nativa.comprobar_movimiento(archivos['clip'],self.raiz/'anonimos',12)
        with Image.open(archivos['poster']) as im:
            self.assertEqual(im.getpixel((96,63)),(255,0,0))
            self.assertEqual(im.getpixel((240,63)),(0,0,255))
            self.assertEqual(im.getpixel((384,63)),(0,255,0))
            # La máscara conserva la geometría de cabeza del mismo rig.
            self.assertEqual(im.getpixel((384,25)),(0,0,0))
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Anónimos portátiles')
        self.assertEqual(recursos.fuentes(copia,refs),modulos)

    def test_s109_append_cache_diccionario_zip_recupera_entrega_pagada(self):
        preparados,escena=self.preparar_anonimos()
        modulo=preparados['personas_anonimas']
        # Estructura de rehacer_eeceaa949fde4722bb1b66d5ce6e253c.json:
        # _prep crea con append, guarda en _C['p']; pintar recorre con zip.
        codigo=f'''from PIL import Image
import {modulo} as personas
_C = {{}}
def _prep():
 if 'bg' in _C:
  return
 _C['bg'] = Image.new('RGB', (320, 180), 'black')
 cols = [('#2a2e46', 'largo', '#171a2a'), ('#33304a', 'coleta', '#171a2a')]
 ps = []
 for sil, pelo, _x in cols:
  ps.append(personas.crear(apariencia={{'pelo': pelo, 'ropa': 'vestido', 'altura': 1.0, 'movil': False}}, silueta=sil))
 _C['p'] = ps
def pintar(pedido, t):
 _prep()
 img = _C['bg'].convert('RGBA')
 ctx = {{'t': t}}
 ests = [dict(x=.3,y=.9,brazo=1.2-t),dict(x=.7,y=.9,brazo=t)]
 layers = []
 for p, e in zip(_C['p'], ests):
  L = Image.new('RGBA', (320, 180), (0, 0, 0, 0))
  p.dibujar(L, e, ctx)
  layers.append(L)
 for L in layers:
  img.alpha_composite(L)
 return img.convert('RGB')
'''
        self.plan['escenas']=self.plan['escenas'][:1]
        e=self.plan['escenas'][0]
        e.update(id='S109',personajes_visibles=[],descripcion_visual='Siluetas femeninas frente a espejos.')
        firma=espacio.huella([nativa.VERSION,self.marca,e,self.plan['resolucion'],12,None])
        carpeta=Path(self.proyecto.ruta('estilo_ia','escenas_nativas','S109',firma))
        dato=dict(respuesta=entrega(codigo),proveedor='Claude',formato='programa-recursos/1',
            recursos_disponibles=preparados['recursos'],contrato_estilo=recursos.contrato_estilo(preparados,e))
        fuente=carpeta/'rehacer_s109.json'
        pendiente=carpeta/'regeneracion_pendiente.json'
        escribir_json(str(fuente),dato)
        escribir_json(str(pendiente),dict(fuente=fuente.name))
        original=fuente.read_bytes()
        with patch.object(nativa,'consultar',side_effect=AssertionError('No repetir entrega pagada')), \
                patch.object(recursos,'preparar',side_effect=AssertionError('No preparar otros recursos')):
            resultado=self.generar(unidades=['escena:S109'],rehacer=True)
        recibo=resultado['todas']['escena:S109']['animacion_estilo']
        self.assertTrue(recibo['comprobacion']['movimiento_detectado'])
        self.assertEqual(fuente.read_bytes(),original)
        self.assertFalse(pendiente.exists())
        # También admite dibujar por índice, pero no otra clave ni una llamada
        # arbitraria que simplemente recibe la lista como argumento.
        for llamada in ("_C['p'][0].dibujar(img, ests[0], ctx)",):
            variante=codigo.replace('p.dibujar(L, e, ctx)',llamada)
            recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(variante)),{},e)
        for llamada in ("_C['otro'].dibujar(img, ests[0], ctx)",
                "inventar(_C['p']).dibujar(img, ests[0], ctx)"):
            variante=codigo.replace('p.dibujar(L, e, ctx)',llamada)
            with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
                recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(variante)),{},e)

    def test_s104_import_auxiliar_fabrica_y_parametros_conservan_rig(self):
        preparados,escena=self.preparar_anonimos()
        modulo=preparados['personas_anonimas']
        # Estructura real de rehacer_a2f03bbdb91e4444a22b3ba5f54ca6fd.json.
        codigo=f'''from PIL import Image
def _imp(n):
    try:
        return __import__(n)
    except Exception:
        return None
personas = _imp('{modulo}')
def _mk(ap, sil=None):
    try:
        if sil:
            return personas.crear(apariencia=ap, silueta=sil)
        return personas.crear(apariencia=ap)
    except Exception:
        return None
RA = _mk({{'pelo':'largo'}})
RB = _mk({{'pelo':'corto'}})
SAv = _mk({{}}, '#9a6be0')
SBv = _mk({{}}, '#9a6be0')
def personas_dib(img, ra, rb, t):
    ctx = {{'t':t}}
    for who, rig in (('A', ra), ('B', rb)):
        if rig is None:
            continue
        est = dict(x=.3 if who=='A' else .7,y=.9,brazo=1.2-t)
        try:
            rig.dibujar(img, est, ctx)
        except Exception:
            pass
def marco_sil(t, ra, rb):
    im = Image.new('RGB',(320,180),'black')
    personas_dib(im, ra, rb, t)
    return im
def pintar(pedido,t):
    return marco_sil(t, SAv, SBv)
'''
        dato=dict(respuesta=entrega(codigo),recursos_disponibles=preparados['recursos'],
            contrato_estilo=recursos.contrato_estilo(preparados,escena))
        with patch.object(nativa,'consultar',side_effect=AssertionError('No consultar proveedores')):
            modulos,refs=recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)
            self.assertIn(modulo,refs)  # No basta aceptar el AST: debe viajar al renderer.
            archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
                self.raiz/'s104',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
            nativa.comprobar_movimiento(archivos['clip'],self.raiz/'s104',12)
        for variante in (
                codigo.replace('return personas.crear(apariencia=ap)', 'return inventar(ap)'),
                codigo.replace('rig.dibujar(img, est, ctx)', 'pass')+'''
def sin_relacion(rig):
    rig.dibujar(None, {}, {})
sin_relacion(otro_monigote)
'''):
            with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
                recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(variante)),{},escena)

    def test_imports_agrupados_y_elenco_condicional_s110_s115_s117(self):
        preparados,escena=self.preparar_anonimos()
        modulo=preparados['personas_anonimas']
        codigo=f'''from PIL import Image
from recursos_animacion import {modulo} as personas
from recursos_animacion import objeto_prueba as objeto
DEPORTISTAS = (personas.crear(silueta='#ff0000'), personas.crear(silueta='#0000ff'))
EJECUTIVOS = (personas.crear(), personas.crear())
def pintar(pedido,t):
    im = Image.new('RGB',(320,180),'black')
    elenco = EJECUTIVOS if t > .5 else DEPORTISTAS
    for n, persona in enumerate(elenco):
        persona.dibujar(im,dict(x=.3+.4*n,y=.9,brazo=1.2-t),dict(t=t))
    # S117 dibuja también directamente por índice.
    DEPORTISTAS[0].dibujar(im,dict(x=.3,y=.9,brazo=1.2-t),dict(t=t))
    objeto.dibujar(im,dict(x=.8,y=.5),dict(t=t))
    return im
'''
        dato=dict(respuesta=entrega(codigo,recursos_nuevos={'objeto_prueba':ARBOL}),
            recursos_disponibles=preparados['recursos'],contrato_estilo=recursos.contrato_estilo(preparados,escena))
        modulos,refs=recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)
        self.assertEqual(set(refs),{modulo,'objeto_prueba'})
        self.assertIn('recursos_animacion',modulos)
        nativa.validar(dato['respuesta'],2,list(modulos))
        antes=espacio.inventario(self.espacio)
        archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'agrupados',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
        nativa.comprobar_movimiento(archivos['clip'],self.raiz/'agrupados',12)
        self.assertEqual(espacio.inventario(self.espacio),antes)
        # No aceptar la fachada como permiso para importar módulos arbitrarios.
        for nombre in ('modulo_inexistente','subprocess','*'):
            variante=f'from recursos_animacion import {nombre}\n'+codigo
            with self.assertRaisesRegex(ValueError,'recurso importado no disponible'):
                recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(variante)),{},escena)
        # Un import agrupado sin usar la geometría sigue rechazándose.
        codigo_sin_rig=f'from recursos_animacion import {modulo} as personas\n'+CODIGO
        with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
            recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(codigo_sin_rig)),{},escena)

    def test_s173_lista_de_modulos_preparados_dibuja_por_indice(self):
        preparados,escena=self.preparar_anonimos()
        base=leer_json(str(recursos.raiz(self.proyecto)/'rig_base.json'),estricto=True)
        modulo='asset_'+base['huella'][:24]
        preparados['personajes']['actor']=modulo
        codigo=f'''from PIL import Image
from recursos_animacion import {modulo} as protagonista
RIGS = (protagonista, protagonista)
def pintar(pedido,t):
    im = Image.new('RGB',(320,180),'black')
    for i in (0,1):
        RIGS[i].dibujar(im,dict(x=.3+.4*i,y=.9,brazo=1.2-t),dict(t=t))
    return im
'''
        dato=dict(respuesta=entrega(codigo),recursos_disponibles=preparados['recursos'],
            contrato_estilo=recursos.contrato_estilo(preparados,escena))
        modulos,_=recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)
        archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'s173',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
        nativa.comprobar_movimiento(archivos['clip'],self.raiz/'s173',12)
        for variante in (codigo.replace('RIGS = (protagonista, protagonista)','RIGS = (otro, otro)'),
                codigo.replace('RIGS[i].dibujar','otro.dibujar')):
            with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
                recursos.vincular(self.proyecto,self.marca['huella'],dict(dato,respuesta=entrega(variante)),{},escena)

    def test_recurso_s059_sintaxis_invalida_se_corrige_sin_sobrescribir_entrega(self):
        self.plan['escenas']=self.plan['escenas'][:1]
        dato=entrega('import nave\n'+CODIGO,recursos_nuevos={'nave':dict(ARBOL,
            codigo='from random import Random\nrng = Random(059) if False else Random(59)\n'+ARBOL['codigo'])})
        with patch.object(nativa,'consultar',return_value=dato) as ia:
            with self.assertRaisesRegex(ValueError,'leading zeros'):self.generar()
        self.assertEqual(ia.call_count,1)
        fuente=next(Path(self.proyecto.ruta('estilo_ia/escenas_nativas')).glob('*/*/fuente.json'))
        original=fuente.read_bytes();pagada=leer_json(str(fuente),estricto=True)
        corregida=copy.deepcopy(pagada)
        asset=corregida['respuesta']['recursos_nuevos']['nave']
        asset['codigo']=asset['codigo'].replace('Random(059) if False else Random(59)','Random(59)')
        escribir_json(str(fuente.with_suffix('.correccion.json')),dict(huella_original=espacio.huella(pagada),
            motivo='Conservar la semilla efectiva 59, quitar literal inválido de rama muerta.',entrega=corregida))
        with patch.object(nativa,'consultar',side_effect=AssertionError('No pagar otro intento')):
            resultado=self.generar()
        self.assertEqual(fuente.read_bytes(),original)
        recibo=resultado['unidades']['escena:S001']['animacion_estilo']
        self.assertTrue(recibo['correccion_local'].endswith('fuente.correccion.json'))
        self.assertEqual(recibo['huella_correccion'],espacio.huella(corregida))

    def test_s096_foto_de_personaje_declara_presencia_sin_inventar_movimiento(self):
        self.plan['escenas']=self.plan['escenas'][:1]
        escena=self.plan['escenas'][0]
        escena.update(personajes_visibles=['auto_protagonista','auto_ella'],
            descripcion_visual='El protagonista mira una foto de Ella.')
        refs={}
        for ident in escena['personajes_visibles']:
            ref=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,nombre=ident))
            refs['asset_'+ref['huella'][:24]]=ref
        personajes=dict(zip(escena['personajes_visibles'],refs))
        codigo=programa_personajes(refs)
        codigo='\n'.join(linea.replace("1.2-2.4*t/pedido['duracion']",'.4')
            if 'actor_1(' in linea else linea for linea in codigo.splitlines())+'\n'
        respuesta=entrega(codigo)
        respuesta['acciones'][0]['objetivo']='auto_protagonista'
        dato=dict(respuesta=respuesta,formato='programa-recursos/1',proveedor='Claude',
            recursos_disponibles=refs,personajes_recursos=personajes,
            contrato_visual=dict(descripcion=escena['descripcion_visual'],personajes_visibles=escena['personajes_visibles']))
        firma=espacio.huella([nativa.VERSION,self.marca,escena,self.plan['resolucion'],12,None])
        fuente=Path(self.proyecto.ruta('estilo_ia','escenas_nativas','S001',firma,'fuente.json'))
        escribir_json(str(fuente),dato);original=fuente.read_bytes()
        with patch.object(nativa,'consultar',side_effect=AssertionError('No IA')):
            with self.assertRaisesRegex(ValueError,'descripción: auto_ella'):self.generar()
        corregida=copy.deepcopy(dato)
        corregida['respuesta']['acciones'].append(dict(tipo='personaje',objetivo='auto_ella',
            accion='Aparece como fotografía, sin actuación corporal adicional.',
            claves=[dict(t=t,estado={'representacion':'foto','visible':True}) for t in (0,2)]))
        escribir_json(str(fuente.with_suffix('.correccion.json')),dict(huella_original=espacio.huella(dato),
            motivo='Declarar el personaje representado en la foto.',entrega=corregida))
        with patch.object(nativa,'consultar',side_effect=AssertionError('No IA')):
            resultado=self.generar()
        self.assertEqual(fuente.read_bytes(),original)
        self.assertTrue(resultado['unidades']['escena:S001']['animacion_estilo']['comprobacion']['movimiento_detectado'])

    def test_contrato_estilo_rechaza_redibujar_o_importar_sin_usar_rig(self):
        preparados,escena=self.preparar_anonimos()
        modulo=preparados['personas_anonimas']
        for codigo in (CODIGO,f'import {modulo} as personas\n'+CODIGO):
            dato=dict(respuesta=entrega(codigo),recursos_disponibles=preparados['recursos'],
                contrato_estilo=recursos.contrato_estilo(preparados,escena))
            with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
                recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)
        # Una entrega histórica no se invalida al leerla por añadir esta guarda.
        dato.pop('contrato_estilo')
        recursos.vincular(self.proyecto,self.marca['huella'],dato,{},escena)

    def test_siluetas_no_eluden_estilo_etiquetandose_como_objeto(self):
        preparados,escena=self.preparar_anonimos()
        escena['descripcion_visual']='Siluetas femeninas frente a espejos.'
        respuesta=entrega();respuesta['acciones'][0]['tipo']='objeto'
        contrato=recursos.contrato_estilo(preparados,escena)
        self.assertTrue(contrato['requiere_personas'])
        with self.assertRaisesRegex(ValueError,'anónimos y siluetas'):
            recursos.vincular(self.proyecto,self.marca['huella'],dict(respuesta=respuesta,
                recursos_disponibles=preparados['recursos'],contrato_estilo=contrato),{},escena)
        escena['descripcion_visual']='Una ciudad de noche sin personas.'
        self.assertFalse(recursos.contrato_estilo(preparados,escena)['requiere_personas'])

    def test_ambos_proveedores_reciben_y_cumplen_reutilizacion_anonima(self):
        self.base_parametrica()
        self.plan['escenas']=self.plan['escenas'][:1]
        self.plan['escenas'][0].update(personajes_visibles=[],descripcion_visual='Dos personas desayunan.')
        proveedores=[]
        def ia(proveedor,prompt,*a,**kw):
            proveedores.append(proveedor)
            datos=datos_prompt(prompt);modulo=datos['recursos_animacion']['personas_anonimas']
            self.assertTrue(modulo)
            self.assertIn('CONSISTENCIA DE ESTILO OBLIGATORIA',prompt)
            codigo=f'''from PIL import Image
from {modulo} import crear
persona=crear()
def pintar(pedido,t):
    im=Image.new('RGB',(320,180),'black')
    persona.dibujar(im,dict(x=.5,y=.9,brazo=1.2-t),dict(t=t))
    return im
'''
            return entrega(codigo)
        with patch.object(nativa,'consultar',side_effect=ia):
            self.params['reparto_animaciones']['carga_claude']=100
            self.generar()
            self.params['reparto_animaciones']['carga_claude']=0
            resultado=self.generar(unidades=['escena:S001'],rehacer=True)
        self.assertEqual(proveedores,['Claude','ChatGPT'])
        recibo=resultado['todas']['escena:S001']['animacion_estilo']
        fuente=leer_json(self.proyecto.ruta(recibo['fuente']),estricto=True)
        self.assertTrue(fuente['contrato_estilo']['requiere_personas'])
        with patch.object(nativa,'consultar',side_effect=AssertionError('No invalidar clips')), \
                patch.object(espacio,'renderizar',side_effect=AssertionError('No reanimar')):
            self.generar()

    def test_descripcion_exige_actor_aunque_direccion_antigua_decia_sin_personas(self):
        self.base_parametrica()
        self.params['catalogo']['reparto']={'auto_protagonista':{'descripcion':'Protagonista'}}
        self.plan['escenas']=self.plan['escenas'][:1]
        escena=self.plan['escenas'][0]
        escena.update(descripcion_visual='El protagonista cocina tranquilo en su casa.',
            direccion='Lantern at a night market. No people.',set='mercado_nocturno',personajes_visibles=[])
        antes=copy.deepcopy(self.plan);llamadas=[]
        def ia(proveedor,prompt,*a,**kw):
            if 'DEFINE SOLO LOS DATOS DE APARIENCIA' in prompt:
                llamadas.append('apariencia')
                return dict(formato='apariencia/1',nombre='Protagonista',concepto='protagonista',apariencia={})
            datos=datos_prompt(prompt);llamadas.append('escena')
            self.assertEqual(datos['escena']['personajes_visibles'],['auto_protagonista'])
            self.assertNotIn('direccion',datos['escena'])
            self.assertNotIn('set',datos['escena'])
            self.assertEqual(list(datos['recursos_animacion']['personajes']),['auto_protagonista'])
            respuesta=entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
            respuesta['acciones'][0]['objetivo']='auto_protagonista'
            return respuesta
        with patch.object(nativa,'consultar',side_effect=ia):resultado=self.generar()
        self.assertEqual(llamadas,['apariencia','escena'])
        self.assertEqual(self.plan,antes)
        recibo=resultado['todas']['escena:S001']['animacion_estilo']
        fuente=leer_json(self.proyecto.ruta(recibo['fuente']),estricto=True)
        self.assertEqual(fuente['contrato_visual']['descripcion'],escena['descripcion_visual'])
        with patch.object(nativa,'consultar',side_effect=AssertionError('No regenerar clips existentes')), \
                patch.object(espacio,'renderizar',side_effect=AssertionError('No reanimar')):
            self.generar()

    def test_accion_de_objeto_no_sustituye_a_personaje_exigido_por_descripcion(self):
        self.base_parametrica()
        self.params['catalogo']['reparto']={'auto_protagonista':{'descripcion':'Protagonista'}}
        self.plan['escenas']=self.plan['escenas'][:1]
        self.plan['escenas'][0].update(descripcion_visual='El protagonista levanta la mano.',personajes_visibles=[])
        def ia(proveedor,prompt,*a,**kw):
            if 'DEFINE SOLO LOS DATOS DE APARIENCIA' in prompt:
                return dict(formato='apariencia/1',nombre='Protagonista',concepto='protagonista',apariencia={})
            datos=datos_prompt(prompt)
            respuesta=entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
            respuesta['acciones'][0].update(tipo='objeto',objetivo='Cartel cerrado')
            return respuesta
        with patch.object(nativa,'consultar',side_effect=ia):
            with self.assertRaisesRegex(ValueError,'personajes exigidos'):self.generar()
        self.assertFalse(Path(self.proyecto.ruta_trabajo('assets'),'escenas/S001.estilo_ia.json').exists())

    def test_recursos_con_tildes_son_modulos_python_validos_y_portables(self):
        nombre='puerta_petr\u00f3leo_bisagra'
        dato=dict(ARBOL,concepto='puerta_de_prueba')
        entrega_escena=dict(respuesta=dict(codigo=f'import {nombre}\n'+CODIGO,
            recursos_nuevos={nombre:dato}),recursos_disponibles={})
        modulos,refs=recursos.vincular(self.proyecto,self.marca['huella'],entrega_escena,{}, {})
        self.assertEqual(modulos[nombre],dato['codigo'])
        # Repetir exactamente un asset ya disponible es idempotente, no colisión.
        entrega_escena['recursos_disponibles']=refs
        self.assertEqual(recursos.vincular(self.proyecto,self.marca['huella'],entrega_escena,{}, {})[1],refs)
        # Nunca sustituir otro contenido bajo un nombre existente.
        entrega_escena['respuesta']['recursos_nuevos'][nombre]=dict(dato,nombre='Otra puerta')
        with self.assertRaisesRegex(ValueError,'sustituir otro recurso'):
            recursos.vincular(self.proyecto,self.marca['huella'],entrega_escena,{}, {})
        codigo=f'from {nombre} import dibujar\n'+CODIGO.replace('    return im',"    dibujar(im,dict(x=.8,y=.5),dict(t=t))\n    return im")
        espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'unicode_modulo',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Con tildes')
        self.assertEqual(recursos.fuentes(copia,refs),modulos)
        for invalido in ('../puerta','class','a-b','_privado','\u212a'):
            self.assertFalse(espacio.nombre_modulo_valido(invalido))

    def test_wrapper_pagado_expone_helpers_heredados_sin_modificar_asset(self):
        codigo_base=ACTOR['codigo']+'''
def estado_base():return dict(x=.5,y=.9,brazo=1.2)
def plantar_pies(estado,separacion=1.1,di=0,dd=0,li=0,ld=0):
    return dict(estado,brazo=di-dd)
def alcanzar_px(estado,lado,px,py,contexto):
    return dict(estado,brazo=px)
'''
        base=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,codigo=codigo_base))
        soporte=recursos.soporte(self.proyecto,self.marca['huella'])
        mb,ms='asset_'+base['huella'][:24],'asset_'+soporte['huella'][:24]
        codigo=f'''import {mb} as base
import {ms} as soporte
_inst=soporte.crear(base)
def dibujar(lienzo,estado,contexto):
    return _inst.dibujar(lienzo,estado,contexto)
'''
        ref=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,codigo=codigo,dependencias={mb:base,ms:soporte}))
        modulos=recursos.fuentes(self.proyecto,{'rival':ref})
        self.assertIn('return getattr(_inst,nombre)',modulos['rival'])
        escena='''from PIL import Image
import rival
def pintar(pedido,t):
    assert not hasattr(rival,'helper_que_no_existe')
    estado=rival.estado_base()
    estado=rival.plantar_pies(estado,.78,1.2,0,0,0)
    estado=rival.alcanzar_px(estado,'d',1.2-t,0,dict(t=t))
    im=Image.new('RGB',(320,180),'black')
    rival.dibujar(im,estado,dict(t=t))
    return im
'''
        archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'helpers',lambda *a:None,codigo_escena=escena,herramientas_escena=modulos)
        nativa.comprobar_movimiento(archivos['clip'],self.raiz/'helpers',12)
        self.assertEqual(recursos.cargar(self.proyecto,ref)['asset']['codigo'],codigo)
        # No sustituir delegadores explícitos ni adivinar una instancia ambigua.
        propio=dict(ACTOR,codigo=codigo+"\ndef __getattr__(nombre):\n    raise AttributeError(nombre)\n",dependencias={mb:base,ms:soporte})
        self.assertEqual(recursos._fuente_compatible(self.proyecto,propio),propio['codigo'])
        ambiguo=dict(ACTOR,codigo=codigo+"\notra=soporte.crear(base)\n",dependencias={mb:base,ms:soporte})
        self.assertEqual(recursos._fuente_compatible(self.proyecto,ambiguo),ambiguo['codigo'])

    def test_cien_chatgpt_tambien_prepara_personajes_sin_llamar_claude(self):
        self.reparto();self.base_parametrica()
        self.params['reparto_animaciones']['carga_claude']=0
        llamadas=[]
        def ia(proveedor,prompt,*a,**kw):
            self.assertEqual(proveedor,'ChatGPT')
            if 'DEFINE SOLO LOS DATOS DE APARIENCIA' in prompt:
                datos=json.loads(prompt.rsplit('\n',1)[1]);llamadas.append('personaje:'+datos['id'])
                return dict(formato='apariencia/1',nombre=datos['id'],concepto=datos['id'],apariencia={})
            datos=datos_prompt(prompt);llamadas.append(datos['escena']['id'])
            return entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=ia):self.generar()
        self.assertEqual(llamadas,['personaje:ana','personaje:bob','S001','S002'])

    def test_reparto_mixto_tambien_se_aplica_al_reparto_de_personajes(self):
        self.reparto();self.params['reparto_animaciones']['carga_claude']=50
        llamadas=[]
        def ia(proveedor,prompt,*a,**kw):
            if 'DISEÑA SOLO ESTE PERSONAJE' in prompt or 'DISEÑA LA IDENTIDAD' in prompt:
                ident=json.loads(prompt.rsplit('\n',1)[1])['id'];llamadas.append((ident,proveedor))
                return diseno_personaje(prompt)
            datos=datos_prompt(prompt);llamadas.append((datos['escena']['id'],proveedor))
            return entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=ia):self.generar()
        self.assertEqual(llamadas,[('ana','Claude'),('bob','ChatGPT'),('S001','Claude'),('S002','ChatGPT')])

    def test_cupo_chatgpt_en_personajes_no_hace_fallback_a_claude(self):
        self.reparto();self.params['reparto_animaciones']['carga_claude']=0
        with patch.object(nativa,'consultar',side_effect=RuntimeError('cupo ChatGPT')) as ia:
            with self.assertRaisesRegex(RuntimeError,'cupo ChatGPT'):self.generar()
        self.assertEqual(ia.call_count,1)
        self.assertEqual(ia.call_args.args[0],'ChatGPT')

    def base_parametrica(self):
        codigo="APARIENCIA_VERSION=1\nPAL={'cuerpo':'#ffffff'}\n"+ACTOR['codigo'].replace("fill='white'","fill=PAL['cuerpo']")
        codigo+="\ndef aplicar_apariencia(datos):\n    PAL['cuerpo']=datos['colores']['ropa']\n"
        ref=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,codigo=codigo))
        escribir_json(str(recursos.raiz(self.proyecto)/'rig_base.json'),ref)
        recursos.publicar(self.proyecto,{'base':ref})
        return ref

    def test_apariencias_solo_datos_render_aislado_y_portabilidad(self):
        from PIL import Image
        base=self.base_parametrica();llamadas=[]
        reparto={'ana':{'descripcion':'Rojo'},'bob':{'descripcion':'Azul'}}
        plan={'escenas':[{'personajes_visibles':['ana','bob']}]}
        def ia(proveedor,prompt,*a,**kw):
            self.assertIn('DEFINE SOLO LOS DATOS DE APARIENCIA',prompt)
            self.assertNotIn('def _',prompt)
            ident=json.loads(prompt.rsplit('\n',1)[1])['id'];llamadas.append(ident)
            return dict(formato='apariencia/1',nombre=ident,concepto=ident,
                apariencia=dict(pelo='trenzas' if ident=='ana' else 'calvo',
                    colores={'ropa':'#ff0000' if ident=='ana' else '#0000ff'}))
        preparados=recursos.preparar(self.proyecto,self.marca,self.espacio,{},reparto,plan,ia,lambda *a:None)
        self.assertEqual(llamadas,['ana','bob'])
        referencias={ident:preparados['recursos'][modulo] for ident,modulo in preparados['personajes'].items()}
        modulos=recursos.fuentes(self.proyecto,referencias)
        codigo='''from PIL import Image
import ana,bob
def pintar(pedido,t):
    im=Image.new('RGB',(320,180),'black')
    ana.dibujar(im,dict(x=.25,y=.9,brazo=t),dict(t=t))
    bob.dibujar(im,dict(x=.75,y=.9,brazo=-t),dict(t=t))
    return im
'''
        archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            self.raiz/'apariencias',lambda *a:None,codigo_escena=codigo,herramientas_escena=modulos)
        with Image.open(archivos['poster']) as im:
            self.assertEqual(im.getpixel((80,63)),(255,0,0))
            self.assertEqual(im.getpixel((240,63)),(0,0,255))
        # Ninguna identidad reconstruye funciones de dibujo; wrapper mecánico.
        for ref in referencias.values():
            dato=recursos.cargar(self.proyecto,ref)['asset']
            self.assertEqual(len(dato['dependencias']),3)
            self.assertNotIn('def _cabeza',dato['codigo'])
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Datos portátiles')
        self.assertEqual(recursos.fuentes(copia,referencias),modulos)
        otro=Proyecto.crear(str(self.raiz/'otros'),'Otro vídeo')
        recursos.catalogo(otro,self.marca['huella'])
        self.assertEqual(recursos.fuentes(otro,referencias),modulos)
        def prohibida(*a,**k):self.fail('No repetir apariencias pagadas')
        recursos.preparar(self.proyecto,self.marca,self.espacio,{},reparto,plan,prohibida,lambda *a:None)
        self.assertEqual(recursos.cargar(self.proyecto,base)['asset']['codigo'].count("PAL={'cuerpo':'#ffffff'}"),1)

    def test_apariencia_fallida_se_recupera_sin_reconsultar(self):
        self.base_parametrica()
        respuesta=dict(formato='apariencia/1',nombre='Ana',concepto='ana',apariencia=dict(pelo='largo'))
        args=(self.proyecto,self.marca,self.espacio,{}, {'ana':{}},{'escenas':[{'personajes_visibles':['ana']}]})
        with patch.object(recursos,'comprobar_personaje',side_effect=ValueError('fallo local')):
            with self.assertRaisesRegex(ValueError,'fallo local'):
                recursos.preparar(*args,lambda *a,**k:respuesta,lambda *a:None)
        cruda=next((recursos.raiz(self.proyecto)/'personajes').glob('*.entrega.json'))
        self.assertEqual(leer_json(str(cruda),estricto=True),respuesta)
        recursos.preparar(*args,lambda *a,**k:self.fail('No consultar IA'),lambda *a:None)
        self.assertEqual(leer_json(str(cruda),estricto=True),respuesta)

    def test_apariencia_admite_detalle_excepcional_sin_reconstruir_el_dibujo(self):
        base=self.base_parametrica()
        soporte=recursos.soporte(self.proyecto,self.marca['huella'])
        apariencia=recursos.soporte_apariencias(self.proyecto,self.marca['huella'])
        refs={'asset_'+r['huella'][:24]:r for r in (base,soporte,apariencia)}
        config=dict(perfil='nativo_v1',base='asset_'+base['huella'][:24],
            soporte='asset_'+soporte['huella'][:24],apariencias='asset_'+apariencia['huella'][:24])
        extra='''from PIL import ImageDraw
def detalle(rig,lienzo,estado,contexto):
    anclas=rig.dibujo_compartido(lienzo,estado,contexto)
    ImageDraw.Draw(lienzo).ellipse((10,10,20,20),fill='yellow')
    return anclas
EXTENSIONES={'dibujar':detalle}
'''
        dato=recursos.compilar_apariencia(dict(formato='apariencia/1',nombre='Con detalle',concepto='detalle',
            apariencia={},codigo_extra=extra),recursos.cargar(self.proyecto,base),config,refs)
        ref=recursos.guardar(self.proyecto,self.marca['huella'],dato)
        recursos.comprobar_personaje(self.proyecto,self.espacio,ref,self.raiz/'detalle',lambda *a:None)
        self.assertIn(extra,dato['codigo'])

    def test_esquema_apariencia_no_admite_opciones_perdidas_ni_valores_invalidos(self):
        from motores.estilo_ia.apariencias import validar,DEFECTO
        for datos in ({'alas':True},{'pelo':'otra geometria'},{'altura':float('nan')},
                {'cuerpo':True},{'edad':101},{'gafas':1},{'colores':{'ropa':'rojo'}}):
            with self.assertRaises(ValueError):validar(datos)
        datos=validar({'pelo':'largo'});datos['colores']['ropa']='#123456'
        self.assertNotEqual(DEFECTO['colores']['ropa'],'#123456')
        self.assertIsNone(recursos.perfil_apariencia(dict(asset=ACTOR)))
        self.assertIn('APARIENCIA_VERSION=1',recursos.encargo_personaje(dict(id='ana',diseno={}),{}))

    def test_geometria_excepcional_recupera_sin_aplicar_apariencia_humana(self):
        base=self.base_parametrica()
        reparto={'gato':{'descripcion':'Gato cuadrúpedo sin ropa'}}
        plan={'escenas':[{'personajes_visibles':['gato']}]}
        original=dict(formato='apariencia/1',nombre='Gato',concepto='gato',apariencia={'ropa':None})
        args=(self.proyecto,self.marca,self.espacio,{},reparto,plan)
        with self.assertRaisesRegex(ValueError,'ropa'):
            recursos.preparar(*args,lambda *a,**k:original,lambda *a:None)
        cruda=next((recursos.raiz(self.proyecto)/'personajes').glob('*.entrega.json'))
        extra='''from PIL import ImageDraw
def inicial(rig):return dict(x=160,y=130,angulo=0)
def anclas(rig,estado,contexto=None):return {'cabeza':(estado['x'],estado['y'])}
def animal(rig,im,estado,contexto):
    assert rig.PAL['cuerpo']=='#ffffff', 'No aplicar colores/ropa humanos'
    d=ImageDraw.Draw(im);x=estado['x'];y=estado['y'];a=estado['angulo']
    d.ellipse((x-50,y-30,x+50,y),fill='orange')
    d.line((x,y,x+a,y-50),fill='white',width=4)
    return rig.pose(estado,contexto)
EXTENSIONES={'estado_base':inicial,'pose':anclas,'dibujar':animal}
'''
        nuevo=dict(formato='geometria/1',nombre='Gato',concepto='gato',codigo_extra=extra,
            interfaz='x,y píxeles; angulo control libre; pose devuelve cabeza.',
            muestra=[dict(x=160,y=130,angulo=-30),dict(x=160,y=130,angulo=30)])
        escribir_json(str(cruda.with_name(cruda.name.replace('.entrega.json','.correccion.json'))),
            dict(huella_original=espacio.huella(original),entrega=nuevo,motivo='Anatomía no humana'))
        preparados=recursos.preparar(*args,lambda *a,**k:self.fail('No consultar'),lambda *a:None)
        ref=preparados['recursos'][preparados['personajes']['gato']]
        self.assertEqual(leer_json(str(cruda),estricto=True),original)
        asset=recursos.cargar(self.proyecto,ref)['asset']
        self.assertEqual(asset['muestra'],nuevo['muestra'])
        self.assertEqual(asset['interfaz'],nuevo['interfaz'])
        self.assertNotIn('_apariencias.crear(',asset['codigo'])
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Geometría portable')
        self.assertEqual(recursos.fuentes(copia,{'gato':ref}),recursos.fuentes(self.proyecto,{'gato':ref}))
        config=leer_json(str(cruda.with_name(cruda.name.replace('.entrega.json','.apariencia.json'))),estricto=True)
        refs=leer_json(str(cruda.with_name(cruda.name.replace('.entrega.json','.base.json'))),estricto=True)
        for invalido in (dict(nuevo,apariencia={}),dict(nuevo,codigo_extra='EXTENSIONES={}'),
                dict(nuevo,muestra=[{}]),dict(nuevo,codigo_extra=extra+'\nrig=None')):
            with self.assertRaises(ValueError):
                recursos.compilar_apariencia(invalido,recursos.cargar(self.proyecto,base),config,refs)

    def test_correccion_local_recupera_entrega_sin_reconsultar_ni_sobrescribirla(self):
        reparto={'ana':{'descripcion':'Ana'}}
        plan={'escenas':[{'personajes_visibles':['ana']}]}
        original=dict(ACTOR,codigo="def dibujar(im,estado,contexto):\n    raise TypeError('radios')\n")
        with self.assertRaisesRegex(ValueError,'radios'):
            recursos.preparar(self.proyecto,self.marca,self.espacio,{},reparto,plan,
                lambda *a,**k:original,lambda *a:None)
        cruda=next((recursos.raiz(self.proyecto)/'personajes').glob('*.entrega.json'))
        ruta=cruda.with_name(cruda.name.replace('.entrega.json','.correccion.json'))
        correccion=dict(huella_original=espacio.huella(original),entrega=ACTOR,motivo='Corrección local de radios')
        escribir_json(str(ruta),correccion)
        def prohibida(*a,**k):raise AssertionError('No reconsultar IA')
        preparados=recursos.preparar(self.proyecto,self.marca,self.espacio,{},reparto,plan,prohibida,lambda *a:None)
        self.assertIn('ana',preparados['personajes'])
        self.assertEqual(leer_json(str(cruda),estricto=True),original)

    def test_correccion_de_otra_entrega_se_rechaza_sin_consultar(self):
        encargo=dict(id='ana',diseno={},analisis=None,observaciones=[])
        clave=espacio.huella([recursos.VERSION,self.marca['huella'],encargo])
        ruta=recursos.raiz(self.proyecto)/'personajes'/clave
        escribir_json(str(ruta.with_suffix('.entrega.json')),ACTOR)
        escribir_json(str(ruta.with_suffix('.correccion.json')),dict(huella_original='0'*64,entrega=ACTOR))
        with self.assertRaisesRegex(ValueError,'no corresponde'):
            recursos.preparar(self.proyecto,self.marca,self.espacio,{}, {'ana':{}},
                {'escenas':[{'personajes_visibles':['ana']}]},
                lambda *a,**k:self.fail('No consultar IA'),lambda *a:None)

    def test_identidad_conserva_evidencia_visual_y_rechaza_exceso_antes_de_ia(self):
        manifiesto=dict(analisis=dict(guia_visual='ACABADO',areas=dict(visual='MATERIALES',animacion='MECANICA_OMITIDA')),
            inspeccion_visual=dict(lotes=[dict(ventanas=[dict(id='V1',areas=dict(personajes='ROSTRO_COMPLETO',
                materiales_luz_color='TELA_COMPLETA',camara_animacion='CAMARA_OMITIDA'),
                evidencias=['F1'],incertidumbres='DUDA_VISUAL')])]))
        base=dict(asset=ACTOR,modulo='base')
        ayuda=dict(asset=dict(interfaz='crear(base)'),modulo='soporte')
        prompt=recursos.encargo_identidad(dict(id='ana',diseno={'descripcion':'IDENTIDAD'}),manifiesto,base,ayuda)
        for texto in ('ROSTRO_COMPLETO','TELA_COMPLETA','F1','DUDA_VISUAL','IDENTIDAD'):
            self.assertIn(texto,prompt)
        for texto in ('CAMARA_OMITIDA','MECANICA_OMITIDA'):
            self.assertNotIn(texto,prompt)
        with self.assertRaisesRegex(ValueError,'40000'):
            recursos.encargo_identidad(dict(id='ana',diseno={'descripcion':'x'*40000}),manifiesto,base,ayuda)

    def test_identidades_reutilizan_mecanica_sin_reenviar_codigo_completo(self):
        self.reparto();prompts=[]
        def ia(proveedor,prompt,*a,**kw):
            if 'DISEÑA SOLO ESTE PERSONAJE' in prompt or 'DISEÑA LA IDENTIDAD' in prompt:
                prompts.append(prompt)
                return diseno_personaje(prompt)
            return entrega(programa_personajes(datos_prompt(prompt)['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=ia):self.generar()
        self.assertEqual(len(prompts),2)
        self.assertIn('DISEÑA SOLO ESTE PERSONAJE',prompts[0])
        self.assertIn('DISEÑA LA IDENTIDAD',prompts[1])
        self.assertNotIn(ACTOR['codigo'],prompts[1])
        self.assertIn('NO vuelvas a programar cinemática',prompts[1])
        disponibles=recursos.catalogo(self.proyecto,self.marca['huella'])
        variantes=[r for r in disponibles.values() if recursos.cargar(self.proyecto,r)['asset'].get('dependencias')]
        self.assertEqual(len(variantes),1)
        self.assertLess(len(recursos.cargar(self.proyecto,variantes[0])['asset']['codigo']),len(ACTOR['codigo']))

    def test_instancias_no_comparten_paleta_y_se_pueden_extender_sin_copiar_rig(self):
        from PIL import Image
        fuente="PAL={'cuerpo':'#ffffff'}\n"+ACTOR['codigo'].replace("fill='white'","fill=PAL['cuerpo']")
        base=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,codigo=fuente))
        ayuda=recursos.soporte(self.proyecto,self.marca['huella'])
        mb,ma='asset_'+base['huella'][:24],'asset_'+ayuda['huella'][:24]
        refs={}
        for nombre,color in (('rojo','#ff0000'),('azul','#0000ff')):
            code=f'''import {mb} as base
from PIL import ImageDraw
from {ma} import crear
def extension(rig,im,estado,contexto):
    anclas=rig.originales['dibujar'](im,estado,contexto)
    x=estado['x']*im.width
    ImageDraw.Draw(im).rectangle((x-10,20,x+10,35),fill=rig.PAL['cuerpo'])
    return anclas
rig=crear(base,paletas={{'PAL':{{'cuerpo':'{color}'}}}},extensiones={{'dibujar':extension}})
def dibujar(im,estado,contexto):
    return rig.dibujar(im,estado,contexto)
'''
            refs[nombre]=recursos.guardar(self.proyecto,self.marca['huella'],dict(ACTOR,codigo=code,dependencias={mb:base,ma:ayuda}))
        # Dibuja ambas identidades y el original en la misma imagen. La tercera
        # figura debe seguir blanca: ni la paleta ni las extensiones se filtran.
        code=f'''from PIL import Image
import rojo, azul
import {mb} as original
def pintar(pedido,t):
    im=Image.new('RGB',(320,180),'black')
    for modulo,x in ((rojo,.2),(azul,.5),(original,.8)):
        modulo.dibujar(im,dict(x=x,y=.9,brazo=1.2-t),dict(t=t))
    return im
'''
        modulos=recursos.fuentes(self.proyecto,refs)
        carpeta=self.raiz/'instancias'
        archivos=espacio.renderizar(self.espacio,dict(ancho=320,alto=180,fps=12,duracion=1,escena={},parametros={}),
            carpeta,lambda *a:None,codigo_escena=code,herramientas_escena=modulos)
        with Image.open(archivos['poster']) as im:
            self.assertEqual(im.getpixel((64,63)),(255,0,0))
            self.assertEqual(im.getpixel((160,63)),(0,0,255))
            self.assertEqual(im.getpixel((256,63)),(255,255,255))
            self.assertEqual(im.getpixel((64,25)),(255,0,0))
            self.assertEqual(im.getpixel((160,25)),(0,0,255))
            self.assertEqual(im.getpixel((256,25)),(0,0,0))
        # Las dependencias originales viajan con un vídeo duplicado.
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Con dependencias')
        self.assertEqual(recursos.fuentes(copia,refs),modulos)
        recursos.publicar(self.proyecto,refs)
        otro=Proyecto.crear(str(self.raiz/'otros'),'Importado')
        recursos.catalogo(otro,self.marca['huella'])
        self.assertEqual(recursos.fuentes(otro,refs),modulos)

    def test_dependencia_ausente_o_de_otro_estilo_no_se_regenera(self):
        base=recursos.guardar(self.proyecto,self.marca['huella'],ACTOR)
        ayuda=recursos.soporte(self.proyecto,self.marca['huella'])
        mb,ma='asset_'+base['huella'][:24],'asset_'+ayuda['huella'][:24]
        prompt=recursos.encargo_identidad(dict(id='bob',diseno={}),{},
            dict(recursos.cargar(self.proyecto,base),modulo=mb),dict(recursos.cargar(self.proyecto,ayuda),modulo=ma))
        dato=recursos.fijar_dependencias(diseno_personaje(prompt),{mb:base,ma:ayuda})
        ref=recursos.guardar(self.proyecto,self.marca['huella'],dato)
        Path(self.proyecto.ruta(base['ruta'])).rename(self.raiz/'base_apartada.json')
        with self.assertRaisesRegex(ValueError,'falta o ha cambiado'):
            recursos.fuentes(self.proyecto,{'personaje':ref})
        with self.assertRaisesRegex(ValueError,'no reconstruir otro rig'):
            recursos.fijar_dependencias(ACTOR,{mb:base,ma:ayuda})

    def test_mecanica_compartida_se_ofrece_a_otro_video_con_reparto_nuevo(self):
        self.reparto()
        def primero(proveedor,prompt,*a,**kw):
            if 'DISEÑA SOLO' in prompt or 'DISEÑA LA IDENTIDAD' in prompt:return diseno_personaje(prompt)
            return entrega(programa_personajes(datos_prompt(prompt)['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=primero):self.generar()
        otro=Proyecto.crear(str(self.raiz/'otros'),'Reparto nuevo')
        llamadas=[]
        def identidad(proveedor,prompt,*a,**kw):
            llamadas.append(prompt)
            self.assertIn('DISEÑA LA IDENTIDAD',prompt)
            return diseno_personaje(prompt)
        preparados=recursos.preparar(otro,self.marca,self.espacio,{}, {'nueva':{'descripcion':'Identidad diferente'}},
            {'escenas':[{'personajes_visibles':['nueva']}]},identidad,lambda *a:None)
        self.assertEqual(len(llamadas),1)
        self.assertEqual(list(preparados['personajes']),['nueva'])

    def test_concepto_descriptivo_pagado_no_se_recorta_ni_reconsulta(self):
        dato=dict(copy.deepcopy(ACTOR),concepto='x'*209)
        self.assertEqual(recursos.validar(dato)['concepto'],dato['concepto'])
        with self.assertRaisesRegex(ValueError,'1001; máximo 1000'):
            recursos.validar(dict(dato,concepto='x'*1001))

    def test_encargo_de_rig_no_repite_tareas_ajenas_ni_recorta_evidencia(self):
        observacion='DETALLE_ARTICULACION_'+'x'*1000
        manifiesto=dict(analisis=dict(guia_visual='ACABADO_COMPLETO',guia_guion='GUION_AJENO'*5000,
            areas=dict(visual='VISUAL',animacion='MOVIMIENTO',voz='VOZ_AJENA'*5000)),
            inspeccion_visual=dict(cobertura={'parcial':True},lotes=[dict(conclusiones='RESUMEN_REDUNDANTE',
                ventanas=[dict(id='V001',areas=dict(personajes=observacion,materiales_luz_color='MATERIALES',
                    camara_animacion='GESTO',sincronizacion_guion='TEXTO_AJENO'*5000),
                    evidencias=['F001'],incertidumbres='Rig no recuperado del vídeo.')])]))
        encargo=dict(id='ana',diseno={'descripcion':'IDENTIDAD_COMPLETA'})
        prompt=recursos.encargo_personaje(encargo,manifiesto)
        self.assertIn(observacion,prompt)
        for texto in ('ACABADO_COMPLETO','IDENTIDAD_COMPLETA','F001','Rig no recuperado','GESTO','MATERIALES'):
            self.assertIn(texto,prompt)
        for texto in ('GUION_AJENO','VOZ_AJENA','TEXTO_AJENO','RESUMEN_REDUNDANTE'):
            self.assertNotIn(texto,prompt)
        with self.assertRaisesRegex(ValueError,'30000'):
            recursos.encargo_personaje(dict(encargo,diseno={'descripcion':'x'*31000}),manifiesto)

    def setUp(self):
        import PIL
        self.tmp=tempfile.TemporaryDirectory(prefix='assets_programa_');self.addCleanup(self.tmp.cleanup)
        self.raiz=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'ESTUDIO_RECURSOS_ANIMACION':str(self.raiz/'compartidos')})
        self.env.start();self.addCleanup(self.env.stop)
        self.proyecto=Proyecto.crear(str(self.raiz/'proyectos'),'Con recursos')
        self.espacio=self.raiz/'espacio'
        espacio.materializar(self.espacio,espacio.validar(dict(codigo=CODIGO,dependencias=[],archivos={},parametros={},direccion='',descargas=[])),[])
        espacio.instalar(self.espacio,lambda *a:None)
        shutil.copytree(Path(PIL.__file__).parent,self.espacio/'dependencias/PIL')
        self.marca=dict(id='a'*32,version=1,huella='b'*64)
        self.params=dict(estilo=dict(espacio_ia=self.marca),animacion_nativa=True,
            catalogo=dict(reparto={}),reparto_animaciones=dict(carga_claude=100))
        self.plan=dict(estilo=self.params['estilo'],resolucion=[320,180],fps=12,duracion_total=4,assets={},dependencias={},
            escenas=[dict(id=f'S{i:03}',narracion='Acción propia.',prompt='Un personaje levanta el brazo.',t_in=(i-1)*2,t_out=i*2) for i in (1,2)])
        escribir_json(self.proyecto.ruta('estilo_ia','manifiesto.json'),dict(analisis={'resumen':'Actuación articulada.'}))
        for parche in (patch.object(espacio,'espacio_del_video',return_value=self.espacio),
                patch.object(p6_assets,'planificar',side_effect=lambda *a,**k:copy.deepcopy(self.plan)),
                patch.object(p6_assets,'plan_actual',return_value={}),
                patch.object(p6_assets,'_ejecutar_base',side_effect=AssertionError('NO generar imágenes'))):
            parche.start();self.addCleanup(parche.stop)

    def generar(self,**opciones):
        return nativa.ejecutar(self.proyecto,self.params,lambda *a:None,**opciones)

    def reparto(self):
        self.params['catalogo']['reparto']={'ana':{'descripcion':'Ana con coleta.'},'bob':{'descripcion':'Bob con gorro.'}}
        self.plan['escenas'][0]['personajes_visibles']=['ana']
        self.plan['escenas'][1]['personajes_visibles']=['ana','bob']

    def test_personajes_se_preparan_todos_antes_del_primer_programa_y_se_reutilizan(self):
        self.reparto();llamadas=[]
        def ia(proveedor,prompt,*args,**kwargs):
            if 'DISEÑA SOLO ESTE PERSONAJE' in prompt or 'DISEÑA LA IDENTIDAD' in prompt:
                ident=json.loads(prompt.rsplit('\n',1)[1])['id'];llamadas.append(ident)
                return diseno_personaje(prompt)
            datos=datos_prompt(prompt);llamadas.append(datos['escena']['id'])
            self.assertEqual(llamadas[:2],['ana','bob'])
            self.assertEqual(set(datos['reparto']),{'ana','bob'})
            self.assertIn('fuente Python completa',prompt)
            return entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=ia):
            resultado=self.generar()
        self.assertEqual(llamadas,['ana','bob','S001','S002'])
        refs=[]
        for ficha in resultado['todas'].values():
            recibo=ficha['animacion_estilo'];fuente=leer_json(self.proyecto.ruta(recibo['fuente']))
            self.assertEqual(fuente['formato'],'programa-recursos/1')
            self.assertIn('def pintar',fuente['respuesta']['codigo'])
            refs.append(recibo['recursos_animacion'])
        self.assertTrue(set(refs[0]).issubset(refs[1]))
        with patch.object(nativa,'consultar',side_effect=AssertionError('no repetir')):
            self.generar()

    def test_nuevo_objeto_se_reutiliza_en_siguiente_escena_y_otro_video(self):
        contador=0;firma_objeto=[]
        def ia(proveedor,prompt,*args,**kwargs):
            nonlocal contador
            contador+=1;datos=datos_prompt(prompt)
            catalogo=datos['recursos_animacion']['catalogo']
            self.assertTrue(any(c['concepto']=='utileria_base' for c in catalogo))
            if contador==1:
                modulo='arbol_especial';nuevos={modulo:copy.deepcopy(ARBOL)}
            else:
                modulo=next(c['modulo'] for c in catalogo if c['concepto']=='arbol_azul');nuevos={}
            codigo=f'from {modulo} import dibujar\n'+CODIGO.replace('    return im',"    dibujar(im,dict(x=.8,y=.5),dict(t=t))\n    return im")
            return entrega(codigo,recursos_nuevos=nuevos)
        with patch.object(nativa,'consultar',side_effect=ia):
            resultado=self.generar()
        for ficha in resultado['todas'].values():
            firma_objeto.extend(r['huella'] for r in ficha['animacion_estilo']['recursos_animacion'].values())
        self.assertEqual(len(set(firma_objeto)),1)
        otro=Proyecto.crear(str(self.raiz/'otros'),'Otro vídeo')
        catalogo=recursos.catalogo(otro,self.marca['huella'])
        self.assertTrue(any(r['huella']==firma_objeto[0] for r in catalogo.values()))
        # Nunca se mezcla automáticamente con un acabado distinto.
        self.assertEqual(recursos.catalogo(otro,'c'*64),{})

    def test_asset_nuevo_y_programa_se_conservan_si_falla_render_sin_compartirlo(self):
        codigo='from mi_arbol import dibujar\n'+CODIGO
        with patch.object(nativa,'consultar',return_value=entrega(codigo,recursos_nuevos={'mi_arbol':ARBOL})) as ia:
            with patch.object(espacio,'renderizar',side_effect=ValueError('render fallido')):
                with self.assertRaisesRegex(ValueError,'render fallido'):self.generar(unidades=['escena:S001'])
            self.assertFalse(list((self.raiz/'compartidos').rglob('*.json')))
            self.generar(unidades=['escena:S001'])
            self.assertEqual(ia.call_count,1)

    def test_preparacion_invalida_no_se_vuelve_a_pagar_ni_arranca_escenas(self):
        self.reparto()
        with patch.object(nativa,'consultar',return_value=dict(ACTOR,codigo='def otro(): pass')) as ia:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'dibujar'):self.generar()
            self.assertEqual(ia.call_count,1)
        self.assertFalse(list((Path(self.proyecto.ruta_trabajo('assets'))/'escenas').glob('*.estilo_ia.json')))

    def test_personaje_estatico_no_se_comparte_y_conserva_entrega(self):
        self.reparto();dato=dict(copy.deepcopy(ACTOR),codigo=ACTOR['codigo'].replace("a=estado.get('brazo',1.2)",'a=1.2'))
        with patch.object(nativa,'consultar',return_value=dato) as ia:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'estática'):self.generar()
            self.assertEqual(ia.call_count,1)
        self.assertFalse(list((self.raiz/'compartidos').rglob('*.json')))

    def test_no_reemplaza_un_personaje_por_otro_dibujo_en_la_escena(self):
        self.reparto()
        def ia(proveedor,prompt,*args,**kwargs):
            return diseno_personaje(prompt) if 'DISEÑA SOLO ESTE PERSONAJE' in prompt or 'DISEÑA LA IDENTIDAD' in prompt else entrega()
        with patch.object(nativa,'consultar',side_effect=ia):
            with self.assertRaisesRegex(ValueError,'reutilizar el rig'):self.generar()

    def test_codigo_historico_pagado_no_necesita_preparar_personajes(self):
        self.reparto();escena=self.plan['escenas'][0]
        firma=espacio.huella([nativa.VERSION,self.marca,escena,self.plan['resolucion'],12,None])
        escribir_json(self.proyecto.ruta('estilo_ia','escenas_nativas','S001',firma,'fuente.json'),dict(respuesta=entrega(),proveedor='Claude'))
        with patch.object(nativa,'consultar',side_effect=AssertionError('no IA')), \
                patch.object(recursos,'preparar',side_effect=AssertionError('no preparar')):
            self.generar(unidades=['escena:S001'])

    def test_fuentes_y_assets_viajan_con_el_video_y_no_dependen_del_catalogo(self):
        def ia(proveedor,prompt,*args,**kwargs):
            return entrega('from mi_arbol import dibujar\n'+CODIGO,recursos_nuevos={'mi_arbol':ARBOL})
        with patch.object(nativa,'consultar',side_effect=ia):
            resultado=self.generar(unidades=['escena:S001'])
        recibo=resultado['todas']['escena:S001']['animacion_estilo']
        copia=self.proyecto.duplicar(str(self.raiz/'copias'),'Portátil')
        for ref in recibo['recursos_animacion'].values():
            self.assertEqual(recursos.cargar(copia,ref)['asset']['codigo'],ARBOL['codigo'])
        # Un proyecto sin versión publicada puede no copiar trabajo/. Las
        # fuentes y assets sí deben bastar para reconstruirlo sin proveedores.
        clip=Path(copia.ruta_trabajo('assets'))/recibo['clip']
        clip.unlink(missing_ok=True)
        with patch.object(nativa,'consultar',side_effect=AssertionError('no IA')), \
                patch.object(recursos,'preparar',side_effect=AssertionError('no catálogo')):
            nativa.ejecutar(copia,self.params,lambda *a:None,unidades=['escena:S001'])

    def test_asset_modificado_falla_sin_regenerar_ni_sobrescribirlo(self):
        ref=recursos.guardar(self.proyecto,self.marca['huella'],ARBOL)
        ruta=Path(self.proyecto.ruta(ref['ruta']));dato=leer_json(str(ruta));dato['asset']['nombre']='Alterado'
        escribir_json(str(ruta),dato)
        with self.assertRaisesRegex(ValueError,'ha cambiado'):recursos.cargar(self.proyecto,ref)
        with self.assertRaisesRegex(ValueError,'no se sobrescribe'):
            recursos.guardar(self.proyecto,self.marca['huella'],ARBOL)

    def test_no_sobrescribe_paquete_publicado_al_copiar_modulos(self):
        antes=espacio.inventario(self.espacio)
        with patch.object(nativa,'consultar',return_value=entrega('from mi_arbol import dibujar\n'+CODIGO,recursos_nuevos={'mi_arbol':ARBOL})):
            self.generar(unidades=['escena:S001'])
        self.assertEqual(espacio.inventario(self.espacio),antes)

    def test_modulos_no_admiten_dependencias_de_otros_assets_ni_proveedores(self):
        for modulo in ('requests','subprocess','otro_asset'):
            with self.subTest(modulo=modulo),self.assertRaises(ValueError):
                recursos.validar(dict(ARBOL,codigo=f'import {modulo}\n'+ARBOL['codigo']))

    def test_personajes_se_reutilizan_en_otro_video_sin_nueva_consulta(self):
        self.reparto()
        def ia(proveedor,prompt,*args,**kwargs):
            if 'DISEÑA SOLO ESTE PERSONAJE' in prompt or 'DISEÑA LA IDENTIDAD' in prompt:return diseno_personaje(prompt)
            datos=datos_prompt(prompt)
            return entrega(programa_personajes(datos['recursos_animacion']['personajes'].values()))
        with patch.object(nativa,'consultar',side_effect=ia):self.generar(unidades=['escena:S001'])
        otro=Proyecto.crear(str(self.raiz/'otros'),'Mismo reparto')
        with patch.object(nativa,'consultar',side_effect=AssertionError('no volver a diseñar')):
            preparados=recursos.preparar(otro,self.marca,self.espacio,
                leer_json(self.proyecto.ruta('estilo_ia','manifiesto.json')),self.params['catalogo']['reparto'],
                self.plan,nativa.consultar,lambda *a:None)
        self.assertEqual(set(preparados['personajes']),{'ana','bob'})

    def test_no_puede_ocultar_modulos_de_python_con_un_asset(self):
        envio=dict(respuesta=entrega(recursos_nuevos={'math':ARBOL}))
        with self.assertRaisesRegex(ValueError,'nombre de recurso'):
            recursos.vincular(self.proyecto,self.marca['huella'],envio,{},self.plan['escenas'][0])

    def test_parar_interrumpe_la_espera_real_sin_iniciar_otra_consulta(self):
        import threading
        from pasos import cli_claude,estadisticas
        iniciado,terminado=threading.Event(),threading.Event()
        avance_original=estadisticas.Avance
        def avisar(*args):
            if iniciado.is_set():raise Cancelado('Parar')
        def cli(*args,**kwargs):
            kwargs['avance'].al_cancelar=terminado.set
            iniciado.set()
            self.assertTrue(terminado.wait(timeout=2))
            raise RuntimeError('CLI terminado')
        def rapido(*args,**kwargs):return avance_original(*args,**dict(kwargs,cadencia=.01))
        with patch.object(estadisticas,'Avance',side_effect=rapido),patch.object(cli_claude,'escribiendo',side_effect=cli) as ia:
            with self.assertRaises(Cancelado):nativa.consultar('Claude','encargo',[],avisar)
        self.assertEqual(ia.call_count,1)

    def test_estilo_ia_no_admite_ruta_imagenes_aunque_flag_antiguo_false(self):
        for flag in ({},dict(animacion_nativa=False)):
            params=dict(estilo=self.params['estilo'],**flag)
            self.assertTrue(nativa.activa(params))
            with self.assertRaisesRegex(ValueError,'imágenes prohibida'):
                p6_assets._producir_imagen('S001','prompt',[],str(self.raiz/'no.png'),params)

    def test_claude_medium_con_techo_cancelacion_y_entrega_durable(self):
        from pasos import cli_claude
        def cli(instruccion,**kwargs):
            (Path(kwargs['cwd'])/'salida.json').write_text(json.dumps(ARBOL),encoding='utf-8')
            raise cli_claude.TiempoAgotado('espera agotada')
        carpeta=self.raiz/'recuperacion'
        with patch.object(cli_claude,'ejecutar',side_effect=cli) as ia:
            with self.assertRaises(cli_claude.TiempoAgotado):nativa.consultar('Claude','encargo',[],lambda *a:None,recuperacion=carpeta)
        self.assertEqual(ia.call_args.kwargs['esfuerzo'],'medium')
        self.assertEqual(ia.call_args.kwargs['tiempo_max_s'],-1)
        self.assertIsNone(cli_claude.tiempo_max('medium',pedido_s=-1))
        self.assertIn('sin corte automático',ia.call_args.kwargs['avance'].texto())
        self.assertFalse(ia.call_args.kwargs['reintentar_cuentas'])
        self.assertFalse(ia.call_args.kwargs['avance']._hilo.is_alive())
        with patch.object(cli_claude,'ejecutar',side_effect=AssertionError('no repetir IA')):
            self.assertEqual(nativa.consultar('Claude','encargo',[],lambda *a:None,recuperacion=carpeta),ARBOL)

    def test_control_de_clip_corto_no_busca_despues_del_ultimo_frame(self):
        self.plan['escenas'][0]['t_out']=1
        dato=entrega();dato['acciones'][0]['claves'][-1]['t']=1
        with patch.object(nativa,'consultar',return_value=dato):
            resultado=self.generar(unidades=['escena:S001'])
        self.assertTrue(resultado['unidades']['escena:S001']['animacion_estilo']['comprobacion']['movimiento_detectado'])

    def test_utileria_base_dibuja_casas_edificios_arboles_y_moviles(self):
        from PIL import Image
        from motores.estilo_ia.recursos_base import dibujar
        for tipo in ('casa','edificio','arbol','movil'):
            im=Image.new('RGB',(320,180),'black')
            anclas=dibujar(im,dict(tipo=tipo,x=.5,y=.5,w=.4,h=.8),dict(t=0))
            self.assertIsNotNone(im.getbbox(),tipo)
            self.assertEqual(anclas['centro'],(160,90))

    def test_regeneracion_fallida_retoma_programa_sin_pagar_otra_vez(self):
        with patch.object(nativa,'consultar',return_value=entrega()) as ia:
            anterior=self.generar(unidades=['escena:S001'])['unidades']['escena:S001']['animacion_estilo']
            with patch.object(espacio,'renderizar',side_effect=ValueError('interrumpido')):
                with self.assertRaisesRegex(ValueError,'interrumpido'):
                    self.generar(unidades=['escena:S001'],rehacer=True)
            self.assertEqual(ia.call_count,2)
            recibo=leer_json(self.proyecto.ruta_trabajo('assets')+'/escenas/S001.estilo_ia.json')
            self.assertEqual(recibo['clip'],anterior['clip'])
            self.generar(unidades=['escena:S001'],rehacer=True)
            self.assertEqual(ia.call_count,2)
            self.generar(unidades=['escena:S001'],rehacer=True)
            self.assertEqual(ia.call_count,3)


if __name__ == '__main__':
    unittest.main()
