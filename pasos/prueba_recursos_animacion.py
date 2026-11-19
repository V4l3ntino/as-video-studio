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
