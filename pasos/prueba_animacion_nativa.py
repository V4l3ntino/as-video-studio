"""Contrato nativo con personajes articulados y FFmpeg real, sin proveedores ni red."""
import copy
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='animacion_nativa_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_RECURSOS_ANIMACION'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import Proyecto, escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import animacion_nativa as nativa, espacio_estilo as espacio, p6_assets

CODIGO = '''import math
from PIL import Image, ImageDraw
def pintar(pedido,t):
    w,h=pedido['ancho'],pedido['alto']
    im=Image.new('RGB',(w,h),'#101b34'); d=ImageDraw.Draw(im)
    def p(x,y): return (int(x*w),int(y*h))
    # Brazo de dos segmentos: hombro, codo y mano cambian de pose.
    fase=min(1,t/pedido['duracion']); u=fase*fase*(3-2*fase)
    hombro=(.43,.45); a=1.2-2.4*u; b=1.8-2.8*u
    codo=(hombro[0]+.13*math.cos(a),hombro[1]+.2*math.sin(a))
    mano=(codo[0]+.13*math.cos(b),codo[1]+.2*math.sin(b))
    d.ellipse((int(.37*w),int(.18*h),int(.49*w),int(.38*h)),fill='white')
    d.line([p(.43,.38),p(.43,.7)],fill='white',width=7)
    d.line([p(.33,.91),p(.43,.7),p(.53,.91)],fill='white',width=6)
    d.line([p(*hombro),p(*codo),p(*mano)],fill='white',width=6)
    d.line([p(.43,.45),p(.31,.63)],fill='white',width=5)
    d.ellipse((int(mano[0]*w)-5,int(mano[1]*h)-5,int(mano[0]*w)+5,int(mano[1]*h)+5),fill='#ffa244')
    return im
'''


def entrega(codigo=CODIGO):
    return dict(codigo=codigo, acciones=[dict(tipo='personaje', objetivo='actor', accion='Levanta el brazo articulando hombro y codo',
        claves=[dict(t=0, estado=dict(hombro=1.2, codo=1.8)), dict(t=2, estado=dict(hombro=-1.2, codo=-1))])],
        edicion='Plano medio fijo; anticipación y elevación del brazo con easing suave.')


class Nativa(unittest.TestCase):
    def test_sonidos_stickman_en_estilo_ia_cache_y_portabilidad(self):
        import wave
        dato = entrega()
        dato['sfx'] = [dict(name='blip', at=.4, dur=.12, gain=-18, seed=3, pitch=1),
                       dict(name='ding', at=1.3, dur=.3, gain=-22)]
        with patch.object(nativa, 'consultar', return_value=dato):
            resultado = self.generar(unidades=['escena:S001'])
        ficha = resultado['unidades']['escena:S001']['animacion_estilo']
        self.assertEqual([s['nombre'] for s in ficha['sonidos']], ['blip', 'ding'])
        from pasos import sonido
        visible = espacio.aplicar_recursos(self.proyecto, copy.deepcopy(self.plan))
        eventos = sonido._eventos_automaticos(visible['escenas'], {}, {})
        self.assertEqual([e['papel'] for e in eventos], ['estilo_ia:sfx:0', 'estilo_ia:sfx:1'])
        self.assertEqual([e['t'] for e in eventos], [.4, 1.3])
        trabajo = Path(self.proyecto.ruta('pasos', 'assets', 'trabajo'))
        for sonido, esperado in zip(ficha['sonidos'], dato['sfx']):
            self.assertTrue(sonido['id'].startswith('estilo_ia:sfx:'))
            self.assertEqual(sonido['inicio'], esperado['at'])
            self.assertAlmostEqual(sonido['ganancia'], 10 ** (esperado['gain'] / 20))
            with wave.open(str(trabajo / sonido['archivo'])) as wav:
                self.assertAlmostEqual(wav.getnframes() / wav.getframerate(), esperado['dur'], places=4)
        # Retomar no dirige, reanima ni sintetiza de nuevo una escena completa.
        with patch.object(nativa, 'consultar', side_effect=AssertionError('No repetir IA')), \
                patch.object(espacio, 'renderizar', side_effect=AssertionError('No reanimar')):
            recuperado = self.generar(unidades=['escena:S001'])
        self.assertEqual(recuperado['unidades']['escena:S001']['animacion_estilo']['sonidos'], ficha['sonidos'])
        copia = self.raiz / 'copia_portatil'
        shutil.copytree(trabajo, copia)
        self.assertTrue(all((copia / s['archivo']).is_file() for s in ficha['sonidos']))
        # Si se pierde un WAV se recupera de la fuente pagada sin otra consulta.
        (trabajo / ficha['sonidos'][0]['archivo']).unlink()
        with patch.object(nativa, 'consultar', side_effect=AssertionError('No repetir IA')):
            reparado = self.generar(unidades=['escena:S001'])
        self.assertTrue(all((trabajo / s['archivo']).is_file()
            for s in reparado['unidades']['escena:S001']['animacion_estilo']['sonidos']))

    def test_contrato_sonidos_estricto_y_fuentes_antiguas(self):
        self.assertNotIn('sfx', nativa.validar(entrega(), 2))
        self.assertEqual(nativa.validar(dict(entrega(), sfx=[]), 2)['sfx'], [])
        for sfx in (None, {}, [dict(name='inventado')], [dict(name='blip', at=2)],
                    [dict(name='pop', at=1.9, dur=.2)], [dict(name='ding', gain=1)],
                    [dict(name='hit', pitch=0)], [dict(name='tick')] * 41):
            with self.subTest(sfx=sfx), self.assertRaises(ValueError):
                nativa.validar(dict(entrega(), sfx=sfx), 2)
        prompt = nativa.encargo(self.plan['escenas'][0], self.plan, {}, None)
        self.assertIn('catalogo_sonidos', prompt)
        self.assertIn('blip', prompt)
        self.assertIn('NO necesitas sintetizarlos', prompt)

    def test_catalogo_y_audio_original_coexisten_fuera_del_clip(self):
        codigo = CODIGO + '''
def crear_audio(pedido,ruta):
    import wave, array
    with wave.open(ruta,'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
        wav.writeframes(array.array('h',[100]*int(48000*pedido['duracion'])).tobytes())
'''
        dato = dict(entrega(codigo), sfx=[dict(name='pop', at=.5, dur=.15)])
        with patch.object(nativa, 'consultar', return_value=dato):
            resultado = self.generar(unidades=['escena:S001'])
        ficha = resultado['unidades']['escena:S001']['animacion_estilo']
        self.assertEqual([s['id'] for s in ficha['sonidos']], ['estilo_ia:sfx:0', 'estilo_ia:0'])
        import json
        import subprocess
        from pasos import medios
        clip = self.proyecto.ruta('pasos', 'assets', 'trabajo', ficha['clip'])
        pistas = subprocess.run([medios.ffprobe(), '-v', 'error', '-show_entries',
            'stream=codec_type', '-of', 'json', clip], capture_output=True, check=True)
        self.assertEqual([s['codec_type'] for s in json.loads(pistas.stdout)['streams']], ['video'])

    def test_regeneraciones_separan_respuestas_y_reintentos_recuperan_la_suya(self):
        import json
        from motores.imagen_openai import codex
        self.plan['escenas'] = self.plan['escenas'][:1]
        llamadas = []
        def responder(*args, **kw):
            llamadas.append(len(llamadas) + 1)
            return json.dumps(entrega(CODIGO + '\n# intento ' + str(llamadas[-1])))
        with patch.object(codex, 'texto', side_effect=responder):
            original = self.generar()
            primera = self.generar(rehacer=True)
            with patch.object(espacio, 'renderizar', side_effect=ValueError('render interrumpido')):
                with self.assertRaisesRegex(ValueError, 'render interrumpido'):
                    self.generar(rehacer=True)
            segunda = self.generar(rehacer=True)
        self.assertEqual(llamadas, [1, 2, 3], 'Rehacer consulta de nuevo; retomar no vuelve a pagar')
        fuentes = [leer_json(self.proyecto.ruta(r['unidades']['escena:S001']['animacion_estilo']['fuente']))
                   for r in (original, primera, segunda)]
        self.assertEqual(len({f['respuesta']['codigo'] for f in fuentes}), 3)

    def test_pendiente_antiguo_conserva_consulta_compartida_sin_pagar(self):
        import json
        import hashlib
        from motores.imagen_openai import codex
        self.plan['escenas'] = self.plan['escenas'][:1]
        with patch.object(nativa, 'consultar', return_value=entrega()):
            inicial = self.generar()
        fuente = Path(self.proyecto.ruta(inicial['unidades']['escena:S001']['animacion_estilo']['fuente']))
        escribir_json(str(fuente.parent/'regeneracion_pendiente.json'), {'fuente': 'rehacer_antiguo.json'})
        def conservada(proveedor, prompt, referencias, avisar, recuperacion=None):
            self.assertEqual(Path(recuperacion), fuente.parent/'consulta')
            firma = espacio.huella([proveedor, prompt, [hashlib.sha256(Path(r).read_bytes()).hexdigest() for r in referencias]])
            salida = Path(recuperacion)/firma/'salida.json'
            salida.parent.mkdir(parents=True, exist_ok=True)
            salida.write_text(json.dumps(entrega()), encoding='utf-8')
            return consultar(proveedor, prompt, referencias, avisar, recuperacion)
        consultar = nativa.consultar
        with patch.object(nativa, 'consultar', side_effect=conservada), \
                patch.object(codex, 'texto', side_effect=AssertionError('No volver a pagar')):
            self.generar(rehacer=True)

    def test_correccion_s090_fusiona_ajuste_parcial_sin_perder_torso(self):
        self.plan['escenas']=self.plan['escenas'][:1]
        # El rig devuelve únicamente el ajuste IK, no la pose completa.
        codigo=CODIGO.replace('    return im', '''    p = {'torso_incl': 9, 'cabeza_giro': .7}
    def alcanzar_px(*args):return {'brazo_d': t}
    p = alcanzar_px(p,'d',10,20,{}) or p
    assert p['torso_incl'] == 9
    return im''')
        with patch.object(nativa,'consultar',return_value=entrega(codigo)):
            with self.assertRaisesRegex(ValueError,'torso_incl'):self.generar()
        fuente=next(Path(self.proyecto.ruta('estilo_ia/escenas_nativas')).glob('*/*/fuente.json'))
        original=fuente.read_bytes();pagada=leer_json(str(fuente),estricto=True)
        corregida=copy.deepcopy(pagada)
        corregida['respuesta']['codigo']=codigo.replace("p = alcanzar_px(p,'d',10,20,{}) or p",
            "ajuste = alcanzar_px(p,'d',10,20,{})\n    if isinstance(ajuste,dict):\n        p.update(ajuste)")
        escribir_json(str(fuente.with_suffix('.correccion.json')),dict(huella_original=espacio.huella(pagada),
            motivo='Fusionar el ajuste parcial del brazo.',entrega=corregida))
        with patch.object(nativa,'consultar',side_effect=AssertionError('No repetir IA')):
            resultado=self.generar()
        self.assertEqual(fuente.read_bytes(),original)
        self.assertIn('correccion_local',resultado['unidades']['escena:S001']['animacion_estilo'])

    def test_correccion_invalida_es_error_local_no_elude_contratos_ni_consulta(self):
        pagada=dict(respuesta=entrega(),proveedor='Claude',contrato_estilo={'version':1},
            contrato_visual={'descripcion':'Una persona','personajes_visibles':['actor']})
        fuente=self.raiz/'fuente.json'
        for cambio in ('huella','contrato_estilo','contrato_visual','proveedor'):
            corregida=copy.deepcopy(pagada)
            correccion=dict(huella_original=espacio.huella(pagada),motivo='Reparación',entrega=corregida)
            if cambio=='huella':correccion['huella_original']='0'*64
            else:corregida.pop(cambio)
            escribir_json(str(fuente.with_suffix('.correccion.json')),correccion)
            with self.subTest(cambio=cambio),self.assertRaises(ValueError):
                nativa.aplicar_correccion_local(fuente,pagada)

    def test_dependencia_desconocida_identifica_modulo_s057(self):
        codigo='import asset_2fbb5a3730e96faea3ed3cf as plano\n'+CODIGO
        with self.assertRaisesRegex(ValueError,'dependencia no admitida: asset_2fbb5a3730e96faea3ed3cf'):
            nativa.validar_codigo(codigo)

    def test_re_y_copy_son_biblioteca_estandar_admitida(self):
        for imports in ('import re, copy', 'from re import sub\nfrom copy import deepcopy'):
            with self.subTest(imports=imports):
                nativa.validar_codigo(imports+'\n'+CODIGO)

    def test_correccion_sin_original_no_consulta_y_continua_siguiente(self):
        escena=self.plan['escenas'][0]
        firma=espacio.huella([nativa.VERSION,self.marca,escena,self.plan['resolucion'],12,None])
        fuente=Path(self.proyecto.ruta('estilo_ia','escenas_nativas','S001',firma,'fuente.json'))
        escribir_json(str(fuente.with_suffix('.correccion.json')),dict(motivo='No reconsultar'))
        with patch.object(nativa,'consultar',return_value=entrega()) as ia:
            with self.assertRaisesRegex(ValueError,'falta la entrega original'):self.generar()
        self.assertEqual(ia.call_count,1)  # Solo S002, nunca la fuente perdida S001.
        self.assertTrue(Path(self.proyecto.ruta_trabajo('assets'),'escenas/S002.estilo_ia.json').is_file())

    def test_descripcion_visual_descarta_direccion_y_decorado_contradictorios(self):
        import json
        casos=[
            ('El protagonista cocina tranquilo en su casa, con música y luz cálida.',
             'Low angle paper lantern in a night market. No people.'),
            ("El protagonista levanta una mano abierta en gesto de hasta aquí.",
             'A stall reads CERRADO. No people.'),
            ('La mano del protagonista gira un termostato de pared de caliente a frío y vuelve a caliente; detrás un chat alterna mensajes cariñosos y días en blanco.',
             'A forest path with a hand lantern.'),
            ('El protagonista sujeta la puerta a una vecina cargada con bolsas.',
             'Close-up of a red mitten on a playground post. No people.')]
        reparto={'auto_protagonista':{'nombre':'Protagonista'},'auto_rival':{'nombre':'Rival'}}
        for descripcion,direccion in casos:
            escena=dict(id='S069',narracion='Frase abstracta.',t_in=0,t_out=2,
                descripcion_visual=descripcion,direccion=direccion,set='mercado_nocturno',
                encuadre='old close-up',luz='old night light',tono='old cold tone',
                personajes_visibles=[],personajes=[],intervencion={'descripcion_visual':'','personajes_visibles':[]})
            antes=copy.deepcopy(escena)
            prompt=nativa.encargo(escena,dict(resolucion=[320,180],catalogo={'reparto':reparto}),{},None)
            datos=json.loads(prompt[prompt.index('{"escena":'):])
            visual=datos['escena']
            self.assertEqual(visual['personajes_visibles'],['auto_protagonista'])
            self.assertEqual(visual['prompt'],descripcion)
            for k in ('direccion','set','encuadre','luz','tono','intervencion'):
                self.assertNotIn(k,visual)
            self.assertNotIn(direccion,prompt)
            self.assertEqual(escena,antes)
        # Sin descripción explícita se conserva el contrato histórico.
        historica=dict(id='S001',direccion='Dirección propia.',personajes_visibles=['auto_rival'])
        self.assertEqual(nativa.escena_del_encargo(historica,reparto),historica)
        # Una lista antigua no impone al protagonista a un escenario sin él.
        actual=dict(historica,descripcion_visual='Dos sillas vacías sobre un escenario.')
        self.assertEqual(nativa.escena_del_encargo(actual,reparto)['personajes_visibles'],[])

    def test_error_local_salta_a_siguiente_y_conserva_recibos_y_entregas(self):
        mensajes=[]
        real=espacio.renderizar
        intentos=[]
        def renderizar(destino,pedido,salida,avisar,**kw):
            sid=pedido['escena']['id'];intentos.append(sid)
            if sid=='S001':raise ValueError('fallo local del dibujo')
            return real(destino,pedido,salida,avisar,**kw)
        with patch.object(nativa,'consultar',return_value=entrega()) as ia, \
                patch.object(espacio,'renderizar',side_effect=renderizar):
            with self.assertRaisesRegex(ValueError,'Tanda recorrida; 1 escena'):
                nativa.ejecutar(self.proyecto,self.params,lambda p,t:mensajes.append(t))
        self.assertEqual(intentos,['S001','S002'])
        self.assertEqual(ia.call_count,2)
        trabajo=Path(self.proyecto.ruta_trabajo('assets'))
        self.assertFalse((trabajo/'escenas/S001.estilo_ia.json').exists())
        recibo=(trabajo/'escenas/S002.estilo_ia.json').read_bytes()
        self.assertIn('fallo local',leer_json(str(trabajo/'errores_escenas.json'))['S001']['error'])
        self.assertTrue(any('continúo con la siguiente' in t for t in mensajes))
        with patch.object(nativa,'consultar',side_effect=AssertionError('No repetir IA')), \
                patch.object(espacio,'renderizar',wraps=real) as render:
            self.generar()
        self.assertEqual(render.call_count,1)
        self.assertEqual((trabajo/'escenas/S002.estilo_ia.json').read_bytes(),recibo)
        self.assertEqual(leer_json(str(trabajo/'errores_escenas.json')), {})

    def test_cupo_y_cancelacion_no_solicitan_otras_escenas(self):
        from pasos.cli_claude import LimiteAgotado
        for fallo in (Cancelado('Parar'),LimiteAgotado('sin cuota')):
            with self.subTest(tipo=type(fallo).__name__), \
                    patch.object(nativa,'consultar',side_effect=fallo) as ia:
                with self.assertRaises(type(fallo)):self.generar()
                self.assertEqual(ia.call_count,1)

    def test_json_invalido_de_una_escena_no_impide_pedir_la_siguiente(self):
        with patch.object(nativa,'consultar',side_effect=[ValueError('JSON de escena inválido'),entrega()]) as ia:
            with self.assertRaisesRegex(ValueError,'S001.*JSON de escena inválido'):self.generar()
        self.assertEqual(ia.call_count,2)
        self.assertTrue(Path(self.proyecto.ruta_trabajo('assets'),'escenas/S002.estilo_ia.json').exists())

    def test_rotulos_unicode_en_renderer_sin_tocar_fuentes_ni_clips_previos(self):
        from PIL import Image,ImageDraw,ImageFont
        from pasos import tipografia
        codigo='''from PIL import Image,ImageDraw,ImageFont
from PIL.ImageFont import load_default as fuente_por_alias
ROTULO='¿POR QUÉ NO BASTÓ? ¡ATRACCIÓN, NIÑEZ Y PINGÜINO!'
FUENTE=fuente_por_alias(size=24)
def pintar(pedido,t):
    im=Image.new('RGB',(960,100),'white')
    d=ImageDraw.Draw(im)
    ausente=FUENTE.getmask(chr(0x10ffff))
    for caracter in '¿¡ÁÉÍÓÚÜÑáéíóúüñ':
        m=FUENTE.getmask(caracter)
        assert (m.size,bytes(m))!=(ausente.size,bytes(ausente))
    assert ImageFont.load_default().getbbox('¿ÉÑ')
    d.text((10,10),ROTULO,font=FUENTE,fill='black')
    return im
'''
        antes=espacio.inventario(self.espacio)
        salida=self.raiz/'texto'
        archivos=espacio.renderizar(self.espacio,dict(ancho=960,alto=100,fps=12,duracion=.2,
            escena={},parametros={}),salida,lambda *a:None,codigo_escena=codigo)
        esperado=Image.new('RGB',(960,100),'white')
        fuente=ImageFont.truetype(tipografia.FUENTES['arial'][0],24)
        ImageDraw.Draw(esperado).text((10,10),'¿POR QUÉ NO BASTÓ? ¡ATRACCIÓN, NIÑEZ Y PINGÜINO!',font=fuente,fill='black')
        with Image.open(archivos['poster']) as imagen:
            self.assertEqual(imagen.convert('RGB').tobytes(),esperado.tobytes())
        self.assertEqual(espacio.inventario(self.espacio),antes)
        # La función global del anfitrión no se sustituye: solo el proceso hijo.
        self.assertEqual(ImageFont.load_default.__module__,'PIL.ImageFont')

    def test_fuente_unicode_ausente_falla_sin_descargar_ni_cambiar_el_texto(self):
        from pasos import tipografia
        with patch.dict(tipografia.FUENTES,{'arial':(str(self.raiz/'falta.ttf'),str(self.raiz/'falta_b.ttf'))}):
            with self.assertRaisesRegex(ValueError,'ESTUDIO_FUENTES'):
                espacio.preparar_fuente_texto(self.raiz/'sin_fuente')

    def test_personaje_animado_puede_interactuar_con_objeto_inmovil(self):
        dato=entrega()
        fijo=dict(tipo='objeto',objetivo='obstaculo',accion='Permanece inmóvil durante el empuje',
            claves=[dict(t=0,estado={'x':100,'rotacion':0}),dict(t=2,estado={'x':100,'rotacion':0})])
        dato['acciones'].append(fijo)
        antes=copy.deepcopy(dato)
        self.assertEqual(nativa.validar(dato,2)['acciones'],antes['acciones'])
        dato['acciones'].reverse()
        self.assertEqual(nativa.validar(dato,2)['acciones'],dato['acciones'])
        # Los elementos estáticos no evitan validar sus claves y tiempos.
        fijo['claves'][1]['t']=3
        with self.assertRaisesRegex(ValueError,'tiempos de la acción'):nativa.validar(dato,2)
        fijo['claves'][1]['t']=2
        fijo['claves'][1]['estado']={}
        with self.assertRaisesRegex(ValueError,'estado explícito'):nativa.validar(dato,2)
        fijo['claves']=fijo['claves'][:1]
        with self.assertRaisesRegex(ValueError,'dos poses'):nativa.validar(dato,2)

    def test_todos_los_sujetos_estaticos_siguen_rechazados(self):
        dato=entrega()
        dato['acciones'][0]['claves'][1]['estado']=copy.deepcopy(dato['acciones'][0]['claves'][0]['estado'])
        dato['acciones'].append(dict(tipo='objeto',objetivo='disco',accion='No se desplaza',
            claves=[dict(t=0,estado={'rotacion':0}),dict(t=2,estado={'rotacion':0})]))
        with self.assertRaisesRegex(ValueError,'cambiar de pose'):nativa.validar(dato,2)

    def test_fuente_con_obstaculo_fijo_se_retoma_sin_otra_consulta(self):
        dato=entrega()
        dato['acciones'].append(dict(tipo='objeto',objetivo='pared',accion='Permanece inmóvil',
            claves=[dict(t=0,estado={'x':200}),dict(t=2,estado={'x':200})]))
        # Simula la entrega pagada que dejó guardada una validación anterior.
        with patch.object(nativa,'consultar',return_value=dato) as ia, \
                patch.object(nativa,'validar',side_effect=ValueError('validación antigua')):
            with self.assertRaisesRegex(ValueError,'validación antigua'):self.generar(unidades=['escena:S001'])
            self.assertEqual(ia.call_count,1)
        with patch.object(nativa,'consultar',side_effect=AssertionError('No repetir IA')):
            resultado=self.generar(unidades=['escena:S001'])
        self.assertTrue(resultado['unidades']['escena:S001']['animacion_estilo']['comprobacion']['movimiento_detectado'])

    def test_limite_temporal_tolera_solo_ruido_de_coma_flotante(self):
        dato = entrega()
        claves = dato['acciones'][0]['claves']
        claves[1]['t'] = 1.046
        duracion = 1.98 - .934
        self.assertLess(duracion, claves[1]['t'])
        self.assertEqual(nativa.validar(dato,duracion)['acciones'][0]['claves'][1]['t'],1.046)
        for tiempos in ((0,1.046001), (0,0), (.5,.4), (-1e-12,1.046), (0,float('nan')),
                        (0,float('inf')), (0,True)):
            claves[0]['t'],claves[1]['t'] = tiempos
            with self.subTest(tiempos=tiempos), self.assertRaisesRegex(ValueError,'tiempos de la acción'):
                nativa.validar(dato,duracion)
    def test_edicion_textual_o_estructurada_sin_perder_decisiones(self):
        edicion = dict(encuadre='Plano general frontal.', ritmo='Anticipación, gesto y resultado.',
            transiciones='Corte directo de entrada y salida.', referencias={'1':'Pose observada.'})
        dato = entrega()
        self.assertEqual(nativa.validar(dato,2)['edicion'],dato['edicion'])
        dato['edicion'] = edicion
        self.assertEqual(nativa.validar(dato,2)['edicion'],edicion)
        for invalida in (None, '', '  ', {}, [], dict(encuadre='Plano general.'),
                         dict(edicion, ritmo=' '), dict(edicion, transiciones=[])):
            with self.subTest(edicion=invalida), self.assertRaisesRegex(ValueError,'encuadre y montaje'):
                nativa.validar(dict(dato,edicion=invalida),2)

    def setUp(self):
        import PIL
        self.tmp = tempfile.TemporaryDirectory(prefix='nativa_contrato_')
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.proyecto = Proyecto.crear(str(self.raiz / 'proyectos'), 'Nativo')
        self.espacio = self.raiz / 'espacio'
        paquete = dict(codigo=CODIGO, dependencias=[], archivos={}, parametros={}, direccion='', descargas=[])
        espacio.materializar(self.espacio, espacio.validar(paquete), [])
        espacio.instalar(self.espacio, lambda *a: None)
        # Copia local de la dependencia ya instalada: ninguna descarga en la prueba.
        shutil.copytree(Path(PIL.__file__).parent, self.espacio / 'dependencias' / 'PIL')
        self.marca = dict(id='a'*32, version=1, huella='b'*64)
        self.params = dict(animacion_nativa=True, estilo=dict(espacio_ia=self.marca), reparto_animaciones=dict(carga_claude=0))
        self.plan = dict(animacion_nativa=True, estilo=self.params['estilo'], resolucion=[320,180], fps=12, duracion_total=4,
            escenas=[dict(id=f'S{i:03}', narracion='Levanta la mano.', prompt='Un personaje saluda.', t_in=(i-1)*2, t_out=i*2)
                     for i in (1,2)], assets={}, dependencias={})
        escribir_json(self.proyecto.ruta('estilo_ia','manifiesto.json'), dict(analisis=dict(resumen='Personajes articulados.')))
        self.parches = [patch.object(espacio, 'espacio_del_video', return_value=self.espacio),
            patch.object(p6_assets, 'planificar', side_effect=lambda *a, **k: copy.deepcopy(self.plan)),
            patch.object(p6_assets, 'plan_actual', return_value={}),
            patch.object(p6_assets, '_ejecutar_base', side_effect=AssertionError('No debe generar imágenes'))]
        for parche in self.parches:
            parche.start(); self.addCleanup(parche.stop)

    def generar(self, **opciones):
        return p6_assets.ejecutar(self.proyecto, self.params, lambda *a: None, **opciones)

    def test_clips_reales_reparto_cache_portabilidad_y_parcial(self):
        original = copy.deepcopy(self.plan)
        with patch.object(nativa, 'consultar', return_value=entrega()) as ia:
            resultado = self.generar(unidades=['escena:S001'])
            self.assertEqual(ia.call_args.args[0], 'ChatGPT')
            self.assertEqual(set(resultado['unidades']), {'escena:S001'})
            resultado = self.generar(unidades=['escena:S002'])
            self.assertEqual(ia.call_count, 2)
            self.assertEqual(set(resultado['todas']), {'escena:S001','escena:S002'})
            resultado = self.generar()
            self.assertEqual(ia.call_count, 2)
        self.assertEqual(self.plan, original)
        for ficha in resultado['todas'].values():
            recibo = ficha['animacion_estilo']
            self.assertTrue(Path(self.proyecto.ruta(recibo['fuente'])).is_file())
            self.assertFalse(recibo['comprobacion']['calidad_verificada'])
        plan = espacio.aplicar_recursos(self.proyecto, copy.deepcopy(self.plan))
        self.assertTrue(all(e.get('animacion_estilo', {}).get('poster') for e in plan['escenas']))
        self.assertEqual(len(nativa.hechos(self.proyecto, plan)), 2)
        self.assertEqual(p6_assets.unidades_pendientes(self.proyecto, self.params), [])
        self.params['reparto_animaciones']['carga_claude'] = 100
        with patch.object(nativa, 'consultar', side_effect=AssertionError('no rebalancear clips válidos')):
            self.generar()
        copia = self.proyecto.duplicar(str(self.raiz/'copias'), 'Copia portátil')
        for ficha in resultado['todas'].values():
            self.assertTrue(Path(copia.ruta(ficha['animacion_estilo']['fuente'])).is_file())

    def test_cancelacion_conserva_clip_y_retoma(self):
        with patch.object(nativa, 'consultar', side_effect=[entrega(), Cancelado('parar')]):
            with self.assertRaises(Cancelado): self.generar()
        trabajo = Path(self.proyecto.ruta_trabajo('assets'))
        self.assertTrue((trabajo/'escenas/S001.estilo_ia.json').is_file())
        self.assertFalse((trabajo/'escenas/S002.estilo_ia.json').exists())
        with patch.object(nativa, 'consultar', return_value=entrega()) as ia:
            self.generar()
            self.assertEqual(ia.call_count, 1)

    def test_reintento_recupera_fuente_con_edicion_estructurada_sin_consultar(self):
        dato = entrega()
        dato['edicion'] = dict(encuadre='Plano medio fijo.', ritmo='Gesto con easing suave.',
            transiciones='Cortes directos.', verificacion='Pendiente de revisión visual.')
        # Reproduce una entrega guardada antes de que el validador antiguo
        # abortase: al reintentar debe usar esa fuente, no pagar otra consulta.
        with patch.object(nativa,'consultar',return_value=dato), \
                patch.object(nativa,'validar',side_effect=ValueError('validador antiguo')):
            with self.assertRaisesRegex(ValueError,'validador antiguo'):
                self.generar(unidades=['escena:S001'])
        with patch.object(nativa,'consultar',side_effect=AssertionError('no volver a consultar')):
            resultado = self.generar(unidades=['escena:S001'])
        self.assertEqual(resultado['unidades']['escena:S001']['animacion_estilo']['edicion'],dato['edicion'])

    def test_montaje_real_usa_clip_y_capas_no_el_poster(self):
        from pasos import p7_callouts, p8_render
        trabajo = Path(self.proyecto.ruta_trabajo('assets'))
        (trabajo/'escenas').mkdir(parents=True,exist_ok=True)
        original = trabajo/'escenas/S001.png'
        original.write_bytes(b'ilustracion antigua que debe conservarse intacta')
        with patch.object(nativa, 'consultar', return_value=entrega()):
            resultado = self.generar()
        self.assertEqual(original.read_bytes(), b'ilustracion antigua que debe conservarse intacta')
        capas = p7_callouts.ejecutar(self.proyecto,dict(plan=str(trabajo/'plan.json')),avisar=lambda *a:None)
        self.assertEqual(len(capas['unidades']),2)
        plan = espacio.aplicar_recursos(self.proyecto, copy.deepcopy(self.plan))
        escena = plan['escenas'][0]
        fuente = p8_render._fuente_para_enlace(escena, {}, str(trabajo), {}, self.proyecto, False, salida=(320,180))
        self.assertEqual(fuente['video'], escena['animacion_estilo']['clip'])
        tarea = dict(fuente, id='S001', fps=6, frames=12, carpeta=str(trabajo/'montaje'),
            hyper=str(trabajo/resultado['todas']['escena:S001']['png']),
            capa_fija='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180"><rect width="20" height="10" fill="#00ff00"/></svg>',
            resolucion=[320,180], calidad='media', clip=str(trabajo/'montado.mp4'),
            ultimo=str(trabajo/'ultimo.png'), conservar_frames=True)
        navegador = p8_render.Navegador(320,180)
        try:
            p8_render.renderizar_plano(tarea,navegador)
        finally:
            navegador.cerrar()
        from PIL import Image, ImageChops, ImageStat
        with Image.open(trabajo/'montaje/f00001.png') as a, Image.open(trabajo/'montaje/f00012.png') as b:
            self.assertGreater(sum(ImageStat.Stat(ImageChops.difference(a,b)).mean), .5)
            self.assertEqual(a.convert('RGB').getpixel((5,5)), (0,255,0))

    def test_estatica_no_se_publica_y_codigo_se_recupera_sin_consulta(self):
        estatico = "from PIL import Image\ndef pintar(pedido,t): return Image.new('RGB',(pedido['ancho'],pedido['alto']),'navy')"
        with patch.object(nativa, 'consultar', return_value=entrega(estatico)) as ia:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'estática'): self.generar(unidades=['escena:S001'])
            self.assertEqual(ia.call_count, 1)
        self.assertFalse(Path(self.proyecto.ruta_trabajo('assets'), 'escenas/S001.estilo_ia.json').exists())

    def test_legacy_no_cuenta_como_nativo_y_texto_distinto_invalida(self):
        with patch.object(nativa, 'consultar', return_value=entrega()): self.generar(unidades=['escena:S001'])
        plan = copy.deepcopy(self.plan)
        plan['escenas'][0]['narracion'] = 'Otra narración.'
        self.assertFalse(espacio.aplicar_recursos(self.proyecto, plan)['escenas'][0].get('animacion_estilo'))
        ruta = self.proyecto.ruta_trabajo('assets') + '/escenas/S001.estilo_ia.json'
        recibo = leer_json(ruta); recibo.pop('modo'); escribir_json(ruta, recibo)
        self.assertFalse(espacio.aplicar_recursos(self.proyecto, copy.deepcopy(self.plan))['escenas'][0].get('animacion_estilo'))

    def test_previa_prefiere_clip_nuevo_de_trabajo_a_version_anterior(self):
        with patch.object(nativa,'consultar',return_value=entrega()):
            self.generar(unidades=['escena:S001'])
            trabajo = Path(self.proyecto.ruta_trabajo('assets'))
            anterior = self.raiz/'version_anterior'
            shutil.copytree(trabajo,anterior)
            nuevo = self.generar(unidades=['escena:S001'],rehacer=True)
        esperado = trabajo/nuevo['unidades']['escena:S001']['animacion_estilo']['clip']
        with patch.object(self.proyecto,'version_activa',return_value=1), \
                patch.object(self.proyecto,'ruta_paso',return_value=str(anterior)):
            plan = espacio.aplicar_recursos(self.proyecto,copy.deepcopy(self.plan))
            self.assertEqual(Path(plan['escenas'][0]['animacion_estilo']['clip']),esperado)

    def test_api_hechos_usa_plan_de_previa_no_prompts_antiguos(self):
        import app
        from types import SimpleNamespace
        from unittest.mock import Mock
        with patch.object(nativa,'consultar',return_value=entrega()):
            self.generar(unidades=['escena:S001'])
        antiguo = copy.deepcopy(self.plan)
        antiguo.pop('animacion_nativa')
        antiguo['escenas'][0]['prompt'] = 'Prompt de la ilustración antigua.'
        self.assertEqual(nativa.hechos(self.proyecto,antiguo),{})
        ctx = SimpleNamespace(proyecto=self.proyecto,estado=Mock())
        ctx.estado.params.return_value = self.params
        with patch.object(app,'contexto',return_value=ctx), \
                patch.object(p6_assets,'planos_hechos',return_value={}), \
                patch.object(p6_assets,'plan_actual',return_value=antiguo), \
                patch.object(app,'_plan_de_previsualizacion',return_value=copy.deepcopy(self.plan)) as previa:
            respuesta = app.planos_hechos('nativo',ligero=1)
        previa.assert_called_once_with(ctx)
        self.assertEqual(respuesta['total'],1)
        self.assertEqual(respuesta['del_plan'],1)
        self.assertIn('S001',respuesta['planos'])
        self.assertNotIn('prompt',respuesta['planos']['S001'])

    def test_guardas_y_acciones_reales_declaradas(self):
        for cambio in (dict(acciones=[]), dict(codigo='import subprocess\ndef pintar(pedido,t): pass')):
            with self.assertRaises(ValueError): nativa.validar(dict(entrega(), **cambio), 2)
        externa = self.raiz / 'referencia.png'
        from PIL import Image
        Image.new('RGB',(320,180)).save(externa)
        codigo = f"from PIL import Image\ndef pintar(pedido,t): return Image.open({str(externa)!r})"
        with self.assertRaisesRegex(ValueError, 'ilustraciones|referencia'):
            espacio.renderizar(self.espacio, dict(ancho=320,alto=180,fps=12,duracion=2), self.espacio/'trabajo/guarda',
                lambda *a: None, codigo_escena=codigo)

    def test_recetas_omiten_preparacion_de_imagenes(self):
        import app
        from types import SimpleNamespace
        from unittest.mock import Mock
        ctx = SimpleNamespace(estado=Mock())
        ctx.estado.params.return_value = self.params
        for tarea in ('escenarios','guia_estilo','plan_cartelas','direccion','piezas'):
            self.assertTrue(app._esta_al_dia(ctx, dict(id=tarea)))
            self.assertIs(app._que_hace(tarea, ctx, {})[0], app._tarea_sin_clave)
        app._validar_params('assets', self.params)
        for valor in ('true', 1, None):
            with self.assertRaises(app.ErrorApi):
                app._validar_params('assets', dict(self.params, animacion_nativa=valor))
        from pasos import presets_canal
        ficha = dict(tipo='estilo', datos=dict(espacio_ia=self.marca, animacion_nativa=True))
        self.assertTrue(presets_canal.cambios_para(ficha)['assets']['animacion_nativa'])


if __name__ == '__main__':
    unittest.main()
