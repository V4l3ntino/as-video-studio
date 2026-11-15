"""Edición visual independiente y navegador opcional, sin llamadas a proveedores."""
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
AISLADO = tempfile.TemporaryDirectory(prefix='descripciones_escenas_')
for nombre in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_COSTE_GLOBAL', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[nombre] = os.path.join(AISLADO.name, nombre)
os.environ['ESTUDIO_SIMULAR'] = '1'

from nucleo import Estado, Proyecto
from pasos import descripciones_escenas as visuales, intercambio_guion, medios, p4_voz, p6_assets

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


def construir(carpeta, capitulos=False):
    p = Proyecto.crear(carpeta, 'La cercanía')
    estado = Estado(p)
    estado.actualizar_params('assets', dict(generar_personajes=False, catalogo=dict(
        reparto={}, sets={'sala': {'descripcion': 'Una sala sencilla'}}, beats=[])))
    estado.actualizar_params('voz', dict(voz_id='general'))
    documento = dict(titulo='La cercanía', escenas_por_frase=True, idioma='es', guion=[
        dict(id='B001', texto='El niño levanta los brazos. El cuidador se acerca.',
             personaje_id='', personajes_visibles=[], descripcion_visual='Un niño pide consuelo.', escenas_visuales=[
                 dict(texto='El niño levanta los brazos.', descripcion_visual='Un niño alza los brazos para pedir consuelo.', personajes_visibles=[],
                      colores='azules fríos, turquesas, amarillo cálido'),
                 dict(texto='El cuidador se acerca.', descripcion_visual='El cuidador camina hacia el niño.', personajes_visibles=[],
                      colores='azules fríos, turquesas, amarillo cálido')]),
        dict(id='B002', texto='El abrazo lo tranquiliza.', descripcion_visual='El niño sonríe durante el abrazo.')])
    if capitulos:
        for bloque,numero,titulo,estilo in zip(documento['guion'],(1,2),('La petición','El abrazo'),('arctic','ember')):
            bloque['capitulo']=dict(numero=numero,titulo=titulo,estilo=estilo)
    medios.escribir_json(p.ruta_trabajo('guion') + '/guion.json', documento)
    estado.completar('guion', {'guion_fichero': 'guion.json'})
    with patch.object(p4_voz, 'simulado', return_value=True):
        salida = p4_voz.ejecutar(p, estado.params('voz'))
    estado.completar('voz', salida)
    plan = p6_assets.planificar(p, estado.params('assets'))
    medios.escribir_json(p.ruta_trabajo('assets') + '/plan.json', plan)
    estado.completar('assets', {'plan': 'plan.json'})
    return p, estado


class Descripciones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=AISLADO.name)
        self.addCleanup(self.tmp.cleanup)
        self.p, self.estado = construir(self.tmp.name)

    def documento_portatil(self):
        escenas = visuales.listar(self.p)
        bloques = p4_voz.cargar_guion(self.p)
        return dict(formato=intercambio_guion.FORMATO, bloques=[dict(texto=b['texto'],
            **({'capitulo': next(e['capitulo'] for e in escenas if e['bloque']==b['id'])}
                if any('capitulo' in e for e in escenas if e['bloque']==b['id']) else {}),
            escenas=[dict(texto=e['texto'], descripcion_visual=e['descripcion_visual'], colores=e['colores'])
                     for e in escenas if e['bloque'] == b['id']]) for b in bloques])

    def test_importacion_sin_cambios_y_solo_visual_conserva_audio(self):
        documento = self.documento_portatil()
        antes = Path(self.p.ruta('estado.json')).read_bytes()
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), antes)
        firmas = {p: self.estado.firma(p) for p in ('guion', 'voz', 'revision_audio')}
        documento['bloques'][0]['escenas'][0]['descripcion_visual'] = 'Un niño saluda desde el umbral.'
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(visuales.listar(self.p)[0]['descripcion_visual'], 'Un niño saluda desde el umbral.')
        self.assertEqual({p: self.estado.firma(p) for p in firmas}, firmas)
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        self.assertIn('saluda desde el umbral', plan['escenas'][0]['prompt'])

    def test_colores_por_frase_importan_y_cambian_solo_la_unidad_visual(self):
        escenas = visuales.listar(self.p)
        self.assertEqual(escenas[0]['colores'], 'azules fríos, turquesas, amarillo cálido')
        self.assertEqual(escenas[-1]['colores'], '')  # Dirección histórica sin paleta.
        firmas = {p: self.estado.firma(p) for p in ('guion', 'voz', 'revision_audio')}
        vecina = self.estado.firma_unidad('assets', 'escena:S002')
        resultado = visuales.guardar(self.p, [dict(escenas[0], colores='cobre, naranja')])
        self.assertEqual(resultado['cambiadas'], 1)
        self.assertEqual({p: self.estado.firma(p) for p in firmas}, firmas)
        self.assertEqual(self.estado.firma_unidad('assets', 'escena:S002'), vecina)
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        self.assertEqual(plan['escenas'][0]['colores'], 'cobre, naranja')
        self.assertIn('Colores principales de esta escena: cobre, naranja', plan['escenas'][0]['prompt'])
        self.assertEqual(plan['escenas'][1]['colores'], escenas[1]['colores'])
        self.assertEqual(visuales.guardar(self.p, [resultado['escenas'][0]])['cambiadas'], 0)
        documento = self.documento_portatil()
        documento['bloques'][0]['escenas'][0]['colores'] = 'rosa, violeta'
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(visuales.listar(self.p)[0]['colores'], 'rosa, violeta')
        # Los JSON antiguos sin campo no borran la dirección cromática existente.
        antes = Path(self.p.ruta('estado.json')).read_bytes()
        for bloque in documento['bloques']:
            for escena in bloque['escenas']:
                escena.pop('colores', None)
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), antes)
        documento['bloques'][0]['escenas'][0]['colores'] = ['azul']
        with self.assertRaisesRegex(ValueError, 'colores debe ser texto'):
            intercambio_guion.importar(self.p, documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), antes)

    def test_capitulos_viajan_por_escenas_y_json_sin_anadir_tiempo_ni_tocar_voz(self):
        self.p,self.estado=construir(self.tmp.name,capitulos=True)
        escenas=visuales.listar(self.p)
        self.assertEqual([e.get('apertura_capitulo',{}).get('numero') for e in escenas],[1,None,2])
        firmas={paso:self.estado.firma(paso) for paso in ('guion','voz','revision_audio')}
        audio=Path(self.p.ruta_paso('voz')+'/narracion.wav').read_bytes()
        plan=p6_assets.planificar(self.p,self.estado.params('assets'))
        self.assertEqual(len(plan['escenas']),3)
        self.assertEqual([e['narracion'] for e in plan['escenas']],[e['texto'] for e in escenas])
        for e in plan['escenas']:
            if e.get('apertura_capitulo'):
                self.assertLessEqual(e['apertura_capitulo']['duracion_s'],e['t_out']-e['t_in']+.000001)
                self.assertIn('Apertura del capítulo',e['prompt'])
        params=copy.deepcopy(self.estado.params('assets'))
        params['estilo']=dict(stickman=dict(activo=True))
        params['catalogo']['capitulos']={'B001':dict(titulo='Cabecera anterior')}
        sin_duplicados=p6_assets.planificar(self.p,params)
        self.assertFalse(any(v.get('tipo')=='capitulo' for e in sin_duplicados['escenas'] for v in e['capa_vectorial']))
        self.assertFalse(any(f['tipo']=='cabecera' for f in sin_duplicados['assets'].values()))
        documento=self.documento_portatil()
        self.assertEqual(documento['bloques'][0]['capitulo']['titulo'],'La petición')
        documento['bloques'][0]['capitulo']['titulo']='Pedir ayuda'
        intercambio_guion.importar(self.p,documento)
        self.assertEqual({paso:self.estado.firma(paso) for paso in firmas},firmas)
        self.assertEqual(Path(self.p.ruta_paso('voz')+'/narracion.wav').read_bytes(),audio)
        self.assertEqual(visuales.listar(self.p)[0]['capitulo']['titulo'],'Pedir ayuda')
        # Editar una descripción después de importar conserva su capítulo efectivo.
        actual=visuales.listar(self.p)[0]
        visuales.guardar(self.p,[dict(actual,descripcion_visual='El niño pide ayuda al adulto.')])
        self.assertEqual(visuales.listar(self.p)[0]['capitulo']['titulo'],'Pedir ayuda')
        antes=Path(self.p.ruta('estado.json')).read_bytes()
        documento=self.documento_portatil()
        for bloque in documento['bloques']:
            bloque.pop('capitulo',None)
        intercambio_guion.importar(self.p,documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(),antes)
        documento['bloques'][0]['capitulo']=dict(numero=2,titulo='Fuera de orden',estilo='mixto')
        with self.assertRaisesRegex(ValueError,'empezar en 1'):
            intercambio_guion.importar(self.p,documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(),antes)
        documento=self.documento_portatil()
        for bloque in documento['bloques']:
            bloque['capitulo']=None
        intercambio_guion.importar(self.p,documento)
        self.assertTrue(all(not e.get('apertura_capitulo') for e in visuales.listar(self.p)))
        self.assertEqual(Path(self.p.ruta_paso('voz')+'/narracion.wav').read_bytes(),audio)

    def test_regeneracion_stickman_recibe_paletas_y_exige_colores_por_escena(self):
        from pasos import cli_claude, personajes
        self.estado.actualizar_params('assets', {'estilo': {'stickman': {'seleccionada': 0,
            'variantes': [{'acabado': 'arctic'}]}}})
        opciones = dict(sistema_personajes=dict(stickman=True, generar_personajes=True))
        escenas = visuales.listar(self.p)
        nuevas = [dict(e, descripcion_visual=f'Acción cromática concreta {i}.',
            colores='azules fríos, turquesas, amarillo cálido') for i, e in enumerate(escenas)]
        incompletas = copy.deepcopy(nuevas)
        incompletas[0].pop('colores')
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), \
                patch.object(personajes, 'opciones_del_proyecto', return_value=opciones), \
                patch.object(cli_claude, 'escribiendo', side_effect=[dict(escenas=incompletas), dict(escenas=nuevas)]) as cli:
            salida = visuales.regenerar(self.p, escenas)
        self.assertEqual(cli.call_count, 2)
        prompt = cli.call_args_list[0].args[0]
        for texto in ('Ember Forge', 'Arctic Glass', 'Sakura Bloom', 'Retro Print', '#ffcb52',
                      'colores', 'arctic', 'NÍTIDO'):
            self.assertIn(texto, prompt)
        self.assertEqual([e['colores'] for e in salida], [e['colores'] for e in nuevas])
        visuales.guardar(self.p, salida)
        self.assertEqual(visuales.listar(self.p)[2]['colores'], nuevas[2]['colores'])

    def test_importacion_nuevas_frases_y_estructura_llegan_a_voz_y_plan(self):
        documento = self.documento_portatil()
        documento['bloques'][0] = dict(texto='La puerta se abre.', escenas=[dict(
            texto='La puerta se abre.', descripcion_visual='Una mano gira el pomo de la puerta.')])
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(p4_voz.cargar_guion(self.p)[0]['texto'], 'La puerta se abre.')
        self.assertEqual(visuales.listar(self.p)[0]['descripcion_visual'], 'Una mano gira el pomo de la puerta.')
        # También puede sustituirse por un guion completamente nuevo, más corto.
        documento['bloques'] = documento['bloques'][:1]
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(len(p4_voz.cargar_guion(self.p)), 1)
        self.assertTrue(Path(self.p.ruta_paso('guion', 1) + '/guion.json').exists())
        with patch.object(p4_voz, 'simulado', return_value=True):
            voz = p4_voz.ejecutar(self.p, self.estado.params('voz'))
        self.estado.completar('voz', voz)
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        self.assertEqual(len(plan['escenas']), 1)
        self.assertIn('gira el pomo', plan['escenas'][0]['prompt'])
        documento['bloques'].append(dict(texto='El sol sale.', escenas=[dict(
            texto='El sol sale.', descripcion_visual='El sol asoma tras las montañas.')]))
        intercambio_guion.importar(self.p, documento)
        self.assertEqual(len(p4_voz.cargar_guion(self.p)), 2)
        self.assertEqual(visuales.listar(self.p)[1]['descripcion_visual'], 'El sol asoma tras las montañas.')

    def test_importacion_invalida_no_guarda_narracion_parcial(self):
        documento = self.documento_portatil()
        documento['bloques'][0]['texto'] = 'Otra narración.'
        antes = Path(self.p.ruta('estado.json')).read_bytes()
        with self.assertRaisesRegex(ValueError, 'descripción por frase'):
            intercambio_guion.importar(self.p, documento)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), antes)

    def test_lectura_pura_y_edicion_llega_al_plan_sin_tocar_guion_ni_audio(self):
        antes = Path(self.p.ruta('estado.json')).read_bytes()
        escenas = visuales.listar(self.p)
        self.assertEqual(len(escenas), 3)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), antes)
        guion = Path(self.p.ruta_paso('guion') + '/guion.json').read_bytes()
        voz = Path(self.p.ruta_paso('voz') + '/narracion.wav').read_bytes()
        firmas = {p: self.estado.firma(p) for p in ('guion', 'voz', 'revision_audio')}
        vecina = self.estado.firma_unidad('assets', 'escena:S002')
        resultado = visuales.guardar(self.p, [dict(escenas[0], descripcion_visual='El niño extiende ambos brazos hacia el cuidador.')])
        self.assertEqual(resultado['cambiadas'], 1)
        self.assertEqual(self.estado.firma_unidad('assets', 'escena:S002'), vecina)
        self.assertEqual({p: self.estado.firma(p) for p in firmas}, firmas)
        self.assertEqual(Path(self.p.ruta_paso('guion') + '/guion.json').read_bytes(), guion)
        self.assertEqual(Path(self.p.ruta_paso('voz') + '/narracion.wav').read_bytes(), voz)
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        self.assertIn('extiende ambos brazos', plan['escenas'][0]['prompt'])
        self.assertNotIn('extiende ambos brazos', plan['escenas'][1]['prompt'])
        despues = Path(self.p.ruta('estado.json')).read_bytes()
        self.assertEqual(visuales.guardar(self.p, [resultado['escenas'][0]])['cambiadas'], 0)
        self.assertEqual(Path(self.p.ruta('estado.json')).read_bytes(), despues)

    def test_ancla_impide_aplicar_descripciones_a_otra_frase(self):
        escena = visuales.listar(self.p)[0]
        visuales.guardar(self.p, [dict(escena, descripcion_visual='Una petición de ayuda con ambos brazos.')])
        self.estado.actualizar_params('guion', {'bloques': {'B001': {'texto': 'El niño se aleja. El cuidador se acerca.'}}})
        with self.assertRaisesRegex(ValueError, 'guion ha cambiado'):
            visuales.guardar(self.p, [escena])
        self.assertNotIn('petición de ayuda', visuales.listar(self.p)[0]['descripcion_visual'])
        editada = visuales.listar(self.p)[0]
        self.assertEqual(editada['id'], 'S001')
        visuales.guardar(self.p, [dict(editada, descripcion_visual='El niño retrocede y se aleja del adulto.')])
        with patch.object(p4_voz, 'simulado', return_value=True):
            voz = p4_voz.ejecutar(self.p, self.estado.params('voz'))
        self.estado.completar('voz', voz)
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        self.assertIn('retrocede', plan['escenas'][0]['prompt'])
        self.assertNotIn('escena:S004', self.estado.unidades_declaradas('assets'))

    def test_regeneracion_valida_cobertura_y_no_acepta_cambiar_la_narracion(self):
        from pasos import cli_claude
        escenas = visuales.listar(self.p)
        nuevas = [dict(e, descripcion_visual=f'Nueva acción concreta {i}.') for i, e in enumerate(escenas)]
        invalida = copy.deepcopy(nuevas)
        invalida[0]['texto'] = 'El niño no dice eso.'
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), patch.object(cli_claude, 'escribiendo', side_effect=[
                {'escenas': invalida}, {'escenas': nuevas}]) as cli:
            salida = visuales.regenerar(self.p, escenas, 'Acciones más fáciles de comprender.')
        self.assertEqual(cli.call_count, 2)
        self.assertNotIn(escenas[0]['descripcion_visual'], cli.call_args_list[0].args[0])
        self.assertNotIn('Write', cli.call_args.kwargs['herramientas_vetadas'])
        self.assertIn('Bash', cli.call_args.kwargs['herramientas_vetadas'])
        self.assertIn('Acciones más fáciles', cli.call_args.args[0])
        self.assertEqual([e['texto'] for e in salida], [e['texto'] for e in escenas])
        with self.assertRaisesRegex(ValueError, 'falta una descripción'):
            visuales.validar(nuevas[:-1], escenas, completa=True)
        visuales.guardar(self.p, [dict(escenas[0], descripcion_visual='Cambio manual durante la generación.')])
        with self.assertRaisesRegex(ValueError, 'durante la generación'):
            visuales.guardar(self.p, nuevas, anteriores=escenas)

    def test_duracion_es_la_del_montaje_actual_no_la_del_plan_antiguo(self):
        plan = p6_assets.planificar(self.p, self.estado.params('assets'))
        antiguo = copy.deepcopy(plan)
        antiguo['escenas'][0]['t_out'] = 99
        with patch.object(p6_assets, 'plan_actual', return_value=antiguo):
            actuales = visuales.listar(self.p)
        self.assertEqual([e['duracion_s'] for e in actuales],
            [round(e['t_out'] - e['t_in'], 3) for e in plan['escenas']])
        self.assertTrue(all(not e['duracion_estimada'] for e in actuales))
        # Cambiar tiempos de voz durante una tanda también invalida su foto.
        nuevas = [dict(e, descripcion_visual='Una acción nueva.') for e in actuales]
        otros = copy.deepcopy(actuales)
        otros[0]['duracion_s'] += 1
        with patch.object(visuales, 'listar', return_value=otros):
            with self.assertRaisesRegex(ValueError, 'durante la generación'):
                visuales.guardar(self.p, nuevas, anteriores=actuales)

    def test_sin_audio_estima_por_frase_y_respeta_la_velocidad_de_voz(self):
        from pasos import personajes
        params_original = personajes.params_de
        def params(proyecto, paso):
            return dict(params_original(proyecto, paso), velocidad='slowest') if paso == 'voz' else params_original(proyecto, paso)
        with patch.object(p6_assets, 'plan_actual', return_value={}), \
                patch.object(medios, 'salida_de', return_value=None):
            normales = visuales.listar(self.p)
            with patch.object(personajes, 'params_de', side_effect=params):
                lentas = visuales.listar(self.p)
        self.assertEqual(len(normales), 3)
        self.assertTrue(all(e['duracion_estimada'] and e['duracion_s'] > 0 for e in normales))
        self.assertTrue(all(l['duracion_s'] > n['duracion_s'] for n, l in zip(normales, lentas)))

    def test_regeneracion_envia_presupuesto_por_escena_en_todas_las_tandas(self):
        from pasos import cli_claude, personajes
        escenas = visuales.listar(self.p)
        escenas[0].update(duracion_s=2, duracion_estimada=False)
        escenas[1].update(duracion_s=8, duracion_estimada=False)
        def responder(prompt, **opciones):
            pedido = json.loads(prompt[prompt.index('{"escenas": [{'):])
            recibidas.append(pedido)
            self.assertIn('UNA acción o reacción breve', prompt)
            self.assertIn('no termines todo al principio', prompt)
            return dict(escenas=[dict(e, descripcion_visual=f'Acción de {e["bloque"]}, {e["indice"]}.')
                                for e in pedido['escenas']])
        recibidas = []
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), \
                patch.object(visuales, 'ESCENAS_POR_TANDA', 1), \
                patch.object(cli_claude, 'escribiendo', side_effect=responder):
            salida = visuales.regenerar(self.p, escenas)
        self.assertEqual(recibidas[0]['escenas'][0]['duracion_s'], 2)
        self.assertEqual(recibidas[1]['escenas'][0]['duracion_s'], 8)
        self.assertEqual(recibidas[2]['guion_contexto'][0]['duracion_s'], 2)
        self.assertEqual([e['duracion_s'] for e in salida], [e['duracion_s'] for e in escenas])
        self.assertIn('Antes de tener audio', personajes.instruccion_visual_stickman())

    def test_api_guarda_y_regenera_sin_lanzar_voz(self):
        import app
        ctx = app.Contexto(self.p.raiz)
        with patch.object(app, 'contexto', return_value=ctx):
            escenas = app.leer_descripciones_guion(self.p.id)['escenas']
            with patch.object(ctx.gestor, 'listar', return_value=[{'estado': 'ejecutando'}]):
                with self.assertRaises(app.ErrorApi):
                    app.regenerar_descripciones_guion(self.p.id, {})
            respuesta = app.guardar_descripciones_guion(self.p.id, {'escenas': [dict(escenas[0], descripcion_visual='El niño pide un abrazo.')]})
            self.assertEqual(respuesta['cambiadas'], 1)
            trabajo = app.regenerar_descripciones_guion(self.p.id, {})
            ficha = ctx.gestor.esperar(trabajo['trabajo_id'], 10)
            self.assertEqual(ficha['estado'], 'listo', ficha.get('error'))
            self.assertEqual(ficha['resultado']['cambiadas'], 3)

    def test_espera_informa_del_modelo_y_cancelar_interrumpe_el_cli(self):
        from nucleo.trabajos import Cancelado
        from pasos import cli_claude, estadisticas
        eventos = []
        interrumpido = threading.Event()
        avance_original = estadisticas.Avance

        def avisar(valor, mensaje=''):
            eventos.append(mensaje)
            if len(eventos) >= 3:
                raise Cancelado('parado por el usuario')

        def rapido(*args, **kwargs):
            return avance_original(*args, **kwargs, cadencia=.01)

        def ejecutar(prompt, **opciones):
            opciones['avance'].al_cancelar = interrumpido.set
            self.assertIn('--no-session-persistence', opciones['extra'])
            self.assertTrue(interrumpido.wait(2), 'la cancelación no llegó al CLI')
            raise RuntimeError('proceso interrumpido')

        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), \
                patch.object(estadisticas, 'Avance', side_effect=rapido), \
                patch.object(cli_claude, 'ejecutar', side_effect=ejecutar) as cli:
            with self.assertRaises(Cancelado):
                visuales.regenerar(self.p, visuales.listar(self.p), avisar=avisar)
        self.assertEqual(cli.call_count, 1)
        self.assertTrue(any('Esperando las descripciones de Claude' in e for e in eventos))

    def test_tandas_publican_antes_de_terminar_y_cancelar_conserva_lo_guardado(self):
        import app
        from nucleo.trabajos import Cancelado
        escenas = visuales.listar(self.p)
        audio = Path(self.p.ruta_paso('voz') + '/narracion.wav').read_bytes()
        contexto = app.Contexto(self.p.raiz)
        original = visuales._regenerar_tanda
        progresos = []

        def tanda(proyecto, actuales, *args):
            if actuales[0]['id'] == 'S002':
                guardadas = visuales.listar(proyecto)
                self.assertTrue(guardadas[0]['descripcion_visual'].startswith('Una figura actúa'))
                self.assertEqual(guardadas[1]['descripcion_visual'], escenas[1]['descripcion_visual'])
                raise Cancelado('parado en la segunda tanda')
            return original(proyecto, actuales, *args)

        with patch.object(visuales, 'ESCENAS_POR_TANDA', 1), \
                patch.object(visuales, '_regenerar_tanda', side_effect=tanda):
            with self.assertRaises(Cancelado):
                app._correr_descripciones_guion(lambda v, *a: progresos.append(v), contexto, escenas, '')
        self.assertIn(1 / 3, progresos)
        self.assertNotIn(1, progresos)
        self.assertTrue(visuales.listar(self.p)[0]['descripcion_visual'].startswith('Una figura actúa'))
        self.assertEqual(Path(self.p.ruta_paso('voz') + '/narracion.wav').read_bytes(), audio)

    @unittest.skipUnless(REAL, 'usa --real para abrir la interfaz en Chromium')
    def test_navegador_edita_autoguarda_recarga_y_regenera_descripciones(self):
        from playwright.sync_api import sync_playwright
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            puerto = sock.getsockname()[1]
        continuar = Path(self.tmp.name) / 'continuar_tanda'
        servidor = '''import sys, time
from pathlib import Path
from pasos import descripciones_escenas as d
import app
d.ESCENAS_POR_TANDA = 1
original = d._regenerar_tanda
continuar = Path(sys.argv[1])
def tanda(proyecto, escenas, *args):
    if escenas[0]['id'] == 'S002':
        while not continuar.exists():
            time.sleep(.05)
    return original(proyecto, escenas, *args)
d._regenerar_tanda = tanda
sys.argv = [sys.argv[0]] + sys.argv[2:]
app.main()
'''
        proceso = subprocess.Popen([sys.executable, '-c', servidor, str(continuar), '--puerto', str(puerto), '--proyectos', self.tmp.name],
            cwd=RAIZ, env=os.environ.copy(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            url = f'http://127.0.0.1:{puerto}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(url, timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            with sync_playwright() as pw:
                navegador = pw.chromium.launch(headless=True)
                pagina = navegador.new_page(viewport={'width': 1440, 'height': 1100})
                errores = []
                pagina.on('pageerror', lambda e: errores.append(str(e)))
                pagina.goto(url)
                pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                pagina.evaluate('''async pid => {
                    document.querySelector('#inicio')?.remove();
                    APP.light.vista='elegido'; APP.light.video.vista='guion';
                    await cargarVideoLight(pid);
                }''', self.p.id)
                boton = pagina.get_by_role('button', name='Regenerar las descripciones de las escenas', exact=True)
                self.assertTrue(boton.is_visible())
                etiquetas = pagina.locator('.parrafo-guion[data-bloque="B001"] > .cabecera .color-guion')
                self.assertEqual(etiquetas.all_text_contents(), ['azules fríos', 'turquesas', 'amarillo cálido'])
                self.assertTrue(etiquetas.last.is_visible())
                pagina.locator('.descripciones-guion summary').first.click()
                area = pagina.get_by_role('textbox', name='Descripción visual de B001, escena 1', exact=True)
                area.fill('El niño se acerca al cuidador con los brazos abiertos.')
                pagina.wait_for_function('!Object.keys(APP.light.video.descripcionesPendientes || {}).length')
                pagina.evaluate('cargarVideoLight(APP.light.video.pid)')
                self.assertEqual(area.input_value(), 'El niño se acerca al cuidador con los brazos abiertos.')
                exportar = pagina.get_by_role('button', name='Exportar guion (.json)', exact=True)
                self.assertTrue(exportar.is_visible())
                # La descarga recoge incluso una descripción aún pendiente de autoguardar.
                area.fill('El niño saluda desde el umbral de la casa.')
                with pagina.expect_download() as descarga:
                    exportar.click()
                documento = json.loads(Path(descarga.value.path()).read_text(encoding='utf-8'))
                self.assertEqual(documento['bloques'][0]['escenas'][0]['descripcion_visual'],
                    'El niño saluda desde el umbral de la casa.')
                self.assertEqual(documento['bloques'][0]['escenas'][0]['colores'],
                    'azules fríos, turquesas, amarillo cálido')
                documento['bloques'][0]['texto'] = 'El niño saluda. El cuidador se acerca.'
                documento['bloques'][0]['capitulo']=dict(numero=1,titulo='La petición',estilo='arctic')
                documento['bloques'][1]['capitulo']=dict(numero=2,titulo='El abrazo',estilo='ember')
                documento['bloques'][0]['escenas'][0] = dict(texto='El niño saluda.',
                    descripcion_visual='El niño mueve la mano para saludar al cuidador.', colores='cobre, naranja')
                with pagina.expect_file_chooser() as selector:
                    pagina.get_by_role('button', name='Importar guion (.json o .txt)', exact=True).click()
                selector.value.set_files(dict(name='nuevo-guion.json', mimeType='application/json',
                    buffer=json.dumps(documento, ensure_ascii=False).encode('utf-8')))
                pagina.wait_for_function('APP.light.video.guion?.escenasVisuales[0]?.texto === "El niño saluda."')
                self.assertEqual(area.input_value(), 'El niño mueve la mano para saludar al cuidador.')
                self.assertEqual(etiquetas.all_text_contents(), ['cobre', 'naranja', 'azules fríos', 'turquesas', 'amarillo cálido'])
                self.assertEqual(pagina.locator('.capitulo-guion h3').all_text_contents(),['La petición','El abrazo'])
                self.assertEqual(pagina.locator('.numero-capitulo').all_text_contents(),['01','02'])
                with pagina.expect_download() as descarga_capitulos:
                    exportar.click()
                exportado=json.loads(Path(descarga_capitulos.value.path()).read_text(encoding='utf-8'))
                self.assertEqual(exportado['bloques'][0]['capitulo'],documento['bloques'][0]['capitulo'])
                captura = os.environ.get('ESTUDIO_CAPTURA_GUION')
                if captura:
                    pagina.screenshot(path=captura, full_page=True)
                pagina.locator('.prompt-general textarea').fill('Representa acciones físicas sencillas.')
                boton.click()
                pagina.wait_for_function('APP.light.video.guion?.escenasVisuales[0]?.descripcion_visual.startsWith("Una figura actúa")')
                self.assertIn('Una figura actúa', area.input_value())
                pagina.wait_for_function('trabajoVideoLight()?.progreso > 0')
                self.assertAlmostEqual(pagina.evaluate('trabajoVideoLight().progreso'), 1 / 3, places=3)
                self.assertFalse(pagina.evaluate('APP.light.video.guion.escenasVisuales[1].descripcion_visual.startsWith("Una figura actúa")'))
                self.assertTrue(pagina.evaluate('''async () => {
                    const campo = document.querySelector('textarea[data-descripcion]');
                    await refrescarDescripcionesLight(APP.light.video.pid);
                    return campo === document.querySelector('textarea[data-descripcion]');
                }'''))
                self.assertTrue(pagina.locator('.descripcion-actualizada').first.is_visible())
                if captura:
                    pagina.screenshot(path=captura, full_page=True)
                pagina.reload()
                pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                pagina.evaluate('''async pid => {
                    document.querySelector('#inicio')?.remove();
                    APP.light.vista='elegido'; APP.light.video.vista='guion';
                    await cargarVideoLight(pid);
                }''', self.p.id)
                pagina.wait_for_function('trabajoVideoLight()?.progreso > 0')
                self.assertTrue(pagina.evaluate('APP.light.video.guion.escenasVisuales[0].descripcion_visual.startsWith("Una figura actúa")'))
                continuar.touch()
                pagina.wait_for_function('!trabajoVideoLight() && APP.light.video.guion.escenasVisuales.every(e => e.descripcion_visual.startsWith("Una figura actúa"))')
                pagina.get_by_text('Descripciones de las escenas regeneradas.',exact=True).wait_for()
                # Un cambio solo cromático actualiza etiquetas sin sustituir el campo visual.
                self.assertTrue(pagina.evaluate('''async () => {
                    const v=APP.light.video,campo=document.querySelector('textarea[data-descripcion]');
                    await pedir(`${API.proyecto(v.pid)}/guion/descripciones`, {method:'PUT',cuerpo:{escenas:[{
                        ...v.guion.escenasVisuales[0],colores:'violeta, melocotón'}]}});
                    await refrescarDescripcionesLight(v.pid);
                    return campo===document.querySelector('textarea[data-descripcion]');
                }'''))
                self.assertEqual(etiquetas.all_text_contents(),
                    ['violeta', 'melocotón', 'azules fríos', 'turquesas', 'amarillo cálido'])
                if captura:
                    pagina.screenshot(path=captura, full_page=True)
                self.assertEqual(errores, [])
                navegador.close()
        finally:
            proceso.terminate()
            proceso.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
