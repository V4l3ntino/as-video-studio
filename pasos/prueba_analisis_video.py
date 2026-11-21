"""Inspección de vídeo y selector de IA. Sin proveedores; --real usa ffmpeg."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_inspeccion_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_PRESETS',
              'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_ESTILOS_IA', 'ESTUDIO_PROYECTOS', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import analisis_video as av, estilos_ia as ia, cli_claude, espacio_estilo


def medidas(total=200, fps=10):
    return [dict(n=i, t=i / fps, cambio=0, variacion=1, luz=100, contraste=180, saturacion=40,
                 variacion_luz=1) for i in range(total)]


def informe_lote(ventanas):
    return dict(conclusiones='Composición luminosa, capas separadas y cámara suave.', ventanas=[dict(
        id=v['id'], areas={a: 'Detalle observado en la secuencia.' for a in av.AREAS},
        evidencias=[f"F{v['fotogramas'][0]:07d}"], incertidumbres='La fuente exacta no se puede identificar.') for v in ventanas])


class Inspeccion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destino = Path(self.tmp.name)

    def indice(self, segundos=20):
        m = medidas(segundos * 10)
        ventanas, cortes = av.planificar(m, segundos)
        ids = sorted({n for v in ventanas for n in v['fotogramas']} | {v['detalle'] for v in ventanas})
        indice = dict(version=1, firma='referencia', duracion_s=segundos, fotogramas_decodificados=len(m),
            fotogramas=[dict(n=n, t=m[n]['t'], id=f'F{n:07d}', archivo=f'{n}.jpg') for n in ids],
            ventanas=[dict(v, lamina=v['id'] + '.jpg', medidas={}) for v in ventanas], cortes=cortes,
            planos_detectados=1, limite_resolucion_detalle=1920)
        escribir_json(str(self.destino / 'analisis_visual' / 'indice.json'), indice)
        return indice

    def test_no_omite_intervalos_largos_y_captura_movimientos_breves(self):
        m = medidas()
        m[45]['variacion'] = 80
        m[80]['cambio'] = 12
        m[150]['cambio'] = 20
        ventanas, cortes = av.planificar(m, 20)
        self.assertEqual(len(cortes), 2)
        self.assertEqual([(v['t_in'], v['t_out']) for v in ventanas], [(0, 8), (8, 15), (15, 20)])
        self.assertTrue({44, 45, 46}.issubset(ventanas[0]['fotogramas']))
        self.assertTrue(all(len(v['fotogramas']) <= av.FRAMES_VENTANA for v in ventanas))
        continuas, _ = av.planificar(medidas(), 20)
        self.assertEqual([(v['t_in'], v['t_out']) for v in continuas], [(0, 8), (8, 16), (16, 20)])

    def test_cortes_muy_breves_no_se_funden_ni_se_descartan(self):
        m = medidas(40)
        for i in range(4, 40, 4): m[i]['cambio'] = 90
        ventanas, _ = av.planificar(m, 4)
        self.assertEqual(len(ventanas), 10)
        self.assertEqual(sorted(n for v in ventanas for n in v['fotogramas']), list(range(40)))

    def test_medidas_truncadas_o_sin_frame_no_se_dan_por_completas(self):
        ruta = self.destino / 'medidas.txt'
        ruta.write_text('frame:0 pts:0 pts_time:0\nlavfi.scd.score=0\n')
        with self.assertRaises(ValueError): av.leer_medidas(ruta)
        ruta.write_text('no hay fotogramas')
        with self.assertRaises(ValueError): av.leer_medidas(ruta)

    def test_proveedor_no_valido_se_rechaza_antes_de_crear_archivos(self):
        with self.assertRaises(ValueError):
            ia.crear(str(self.destino), None, 'a.mp4', 'Prueba', proveedor_analisis='inventado')

    def test_selector_chatgpt_no_llama_a_claude_ni_genera_imagenes(self):
        from motores.imagen_openai import codex
        with patch.object(codex, 'texto', return_value='{"observado":true}') as chatgpt, \
                patch.object(cli_claude, 'ejecutar') as claude:
            self.assertEqual(av.consultar('ChatGPT', 'Inspecciona', ['f.jpg'], self.destino, lambda *a: None, 'Leyendo'), dict(observado=True))
        claude.assert_not_called()
        self.assertEqual(chatgpt.call_args.kwargs['referencias'], ['f.jpg'])
        with patch.object(codex, 'texto', side_effect=RuntimeError('cuota')), patch.object(cli_claude, 'ejecutar') as claude:
            with self.assertRaises(RuntimeError): av.consultar('ChatGPT', 'p', [], self.destino, lambda *a: None, 'm')
        claude.assert_not_called()

    def test_selector_claude_lee_solo_evidencias_permitidas(self):
        with patch.object(cli_claude, 'ejecutar', return_value=('{"observado":true}', {})) as claude:
            av.consultar('Claude', 'Inspecciona', ['f.jpg'], self.destino, lambda *a: None, 'Leyendo')
        self.assertEqual(claude.call_args.kwargs['herramientas_permitidas'], ('Read(f.jpg)',))
        self.assertEqual(claude.call_args.kwargs['extra'], ['--tools', 'Read'])
        with self.assertRaises(ValueError): av.consultar('Claude', 'p', ['f'] * 6, self.destino, lambda *a: None, 'm')

    def test_json_tolera_comas_finales_sin_alterar_texto_ni_escapes(self):
        dato = dict(texto='Detalle literal ,} y ,] con "comillas" y barra \\.', lista=['uno', 'dos'])
        texto = json.dumps(dato, ensure_ascii=False).replace('"dos"]', '"dos",]').replace(']}', '],}')
        self.assertEqual(av.interpretar_respuesta(texto, 'Claude', self.destino, 'Lote 8/59'), dato)
        diagnosticos = list((self.destino / 'analisis_visual' / 'respuestas').glob('*.json'))
        self.assertEqual(len(diagnosticos), 1)
        self.assertEqual(leer_json(str(diagnosticos[0]))['respuesta'], texto)

    def test_caso_real_cierres_de_areas_omitidos_en_las_dos_ventanas(self):
        indice = self.indice()
        correcto = informe_lote(indice['ventanas'][:2])
        correcto['ventanas'][0]['areas']['composicion'] = 'Texto literal "areas": { y "evidencias": [ sin cambiar.'
        texto = json.dumps(correcto, ensure_ascii=False)
        roto = texto.replace('}, "evidencias":', ', "evidencias":')
        with self.assertRaises(json.JSONDecodeError): json.loads(roto)
        recuperado = av.interpretar_respuesta(roto, 'Claude', self.destino, 'Lote visual 8/59')
        self.assertEqual(recuperado, correcto)
        av.validar_lote(recuperado, indice['ventanas'][:2], indice['fotogramas'])

    def test_no_reconstruye_areas_ausentes_ni_textos_truncados(self):
        dato = informe_lote(self.indice()['ventanas'][:2])
        del dato['ventanas'][0]['areas']['personajes']
        roto = json.dumps(dato).replace('}, "evidencias":', ', "evidencias":')
        with self.assertRaises(ValueError):
            av.interpretar_respuesta(roto, 'Claude', self.destino, 'Lote visual 8/59')

    def test_consulta_visual_pide_salida_estructurada_con_todas_las_areas(self):
        with patch.object(cli_claude, 'ejecutar', return_value=('{"ok":true}', {})) as modelo:
            av.consultar('Claude', 'Inspecciona MINUCIOSAMENTE estas imágenes', ['f.jpg'],
                         self.destino, lambda *a: None, 'Lote visual 8/59')
        extra = modelo.call_args.kwargs['extra']
        esquema = json.loads(extra[extra.index('--json-schema') + 1])
        areas = esquema['properties']['ventanas']['items']['properties']['areas']
        self.assertEqual(set(areas['required']), set(av.AREAS))
        self.assertFalse(areas['additionalProperties'])
        self.assertEqual(modelo.call_args.kwargs['herramientas_permitidas'], ('Read(f.jpg)',))

    def test_cli_admite_structured_output_sin_result_solo_si_se_pidio(self):
        def ejecutar(sobre, extra):
            proceso = Mock(returncode=0)
            proceso.communicate.return_value = (json.dumps(sobre).encode('utf-8'), b'')
            with patch.object(cli_claude, 'construir_orden', return_value=['doble']), \
                    patch.object(cli_claude, 'entorno', return_value={}), \
                    patch.object(cli_claude.subprocess, 'Popen', return_value=proceso):
                return cli_claude._una_pasada_cruda('p', 'sonnet', 'high', str(self.destino), 30, 420,
                    None, (), None, extra, None, None, 'contrato aislado', None)
        texto, _ = ejecutar(dict(result='', structured_output=dict(ok=True)), ['--json-schema', '{}'])
        self.assertEqual(json.loads(texto), dict(ok=True))
        with self.assertRaisesRegex(RuntimeError, 'estructurado'):
            ejecutar(dict(result='Texto libre sin el objeto solicitado'), ['--json-schema', '{}'])
        with self.assertRaisesRegex(RuntimeError, 'vacia'):
            ejecutar(dict(result='', structured_output=dict(ok=True)), [])
        self.assertEqual(ejecutar(dict(result='Texto normal'), [])[0], 'Texto normal')

    def test_esquema_lote_exige_cantidad_e_ids_solicitados(self):
        indice = self.indice()
        with patch.object(cli_claude, 'ejecutar', side_effect=[
                (json.dumps(informe_lote(indice['ventanas'][:2])), {}),
                (json.dumps(informe_lote(indice['ventanas'][2:])), {})]) as modelo:
            av.examinar(self.destino, {}, {}, lambda *a: None)
        for llamada, ventanas in zip(modelo.call_args_list, [indice['ventanas'][:2], indice['ventanas'][2:]]):
            extra = llamada.kwargs['extra']
            esquema = json.loads(extra[extra.index('--json-schema') + 1])['properties']['ventanas']
            self.assertEqual(esquema['minItems'], len(ventanas))
            self.assertEqual(esquema['maxItems'], len(ventanas))
            self.assertEqual(esquema['items']['properties']['id']['enum'], [v['id'] for v in ventanas])
            self.assertIn('Entrega exactamente ' + str(len(ventanas)), llamada.args[0])

    def test_omision_conserva_entrega_diagnostico_y_lotes_completos(self):
        indice = self.indice(segundos=36)
        grupos = av._grupos_inspeccion(indice)
        incompleto = informe_lote(grupos[1][:1])
        with patch.object(av, 'consultar', side_effect=[informe_lote(grupos[0]), incompleto]) as modelo:
            with self.assertRaisesRegex(ValueError, 'Claude, lote visual 2/3:.*faltan V0004.*Reintentar'):
                av.examinar(self.destino, {}, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 2)  # Nunca reintentar automáticamente.
        entregas = [leer_json(str(p)) for p in (self.destino / 'analisis_visual' / 'respuestas').glob('*.json')]
        fallida = next(d for d in entregas if d['lote'] == 2)
        self.assertEqual(fallida['respuesta'], incompleto)
        self.assertEqual(fallida['intervalos_esperados'], ['V0003', 'V0004'])
        self.assertEqual(len(list((self.destino / 'analisis_visual' / 'informes').glob('*/lote_*.json'))), 1)
        self.assertFalse((self.destino / 'analisis_visual' / 'informe_actual.json').exists())
        with patch.object(av, 'consultar', side_effect=[informe_lote(g) for g in grupos[1:]]) as modelo:
            informe = av.examinar(self.destino, {}, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 2)
        self.assertEqual(informe['cobertura']['lotes_completos'], 3)

    def test_ids_duplicados_no_sustituyen_intervalos_ausentes(self):
        indice = self.indice()
        ventanas = indice['ventanas'][:2]
        dato = informe_lote(ventanas)
        dato['ventanas'][1] = copy.deepcopy(dato['ventanas'][0])
        with self.assertRaisesRegex(ValueError, 'no corresponden'):
            av.validar_lote(dato, ventanas, indice['fotogramas'])

    def test_json_acepta_markdown_o_introduccion_sin_consultar_otra_vez(self):
        for texto in ('```json\n{"ok":true}\n```', 'Resultado:\n{"ok":true}\nFin.'):
            with patch.object(cli_claude, 'ejecutar', return_value=(texto, {})) as modelo:
                self.assertEqual(av.consultar('Claude', 'p', [], self.destino, lambda *a: None, 'Lote 8/59'), dict(ok=True))
            self.assertEqual(modelo.call_count, 1)

    def test_json_irrecuperable_no_inventa_campos_y_explica_como_retomar(self):
        for texto in ('{"texto":"cortado', '{clave:"sin comillas"}', '{"texto":"sin cerrar}'):
            with self.assertRaisesRegex(ValueError, 'Lote 8/59.*lotes completados se conservan'):
                av.interpretar_respuesta(texto, 'Claude', self.destino, 'Lote 8/59')

    def test_error_json_no_borra_lotes_ni_obliga_a_repetirlos(self):
        indice = self.indice()
        ficha = dict(proveedor_analisis='Claude', analisis_ejecucion='uno')
        primero = informe_lote(indice['ventanas'][:2])
        segundo = informe_lote(indice['ventanas'][2:])
        with patch.object(cli_claude, 'ejecutar', side_effect=[(json.dumps(primero), {}), ('{"ventanas": [', {})]) as modelo:
            with self.assertRaisesRegex(ValueError, 'Lote visual 2/2'):
                av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 2)
        self.assertEqual(len(list((self.destino / 'analisis_visual' / 'informes').glob('*/lote_*.json'))), 1)
        self.assertFalse((self.destino / 'analisis_visual' / 'informe_actual.json').exists())
        with patch.object(cli_claude, 'ejecutar', return_value=(json.dumps(segundo), {})) as modelo:
            av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 1)

    def test_lote_exige_todas_las_areas_y_evidencias_del_intervalo(self):
        indice = self.indice()
        ventanas = indice['ventanas'][:2]
        dato = informe_lote(ventanas)
        av.validar_lote(dato, ventanas, indice['fotogramas'])
        for cambiado in (dict(dato, ventanas=dato['ventanas'][:1]),
                         dict(dato, ventanas=[dict(dato['ventanas'][0], areas={}), dato['ventanas'][1]]),
                         dict(dato, ventanas=[dict(dato['ventanas'][0], evidencias=['F9999999']), dato['ventanas'][1]]),
                         dict(dato, ventanas=[dict(dato['ventanas'][0], evidencias=dato['ventanas'][1]['evidencias']), dato['ventanas'][1]])):
            with self.assertRaises(ValueError): av.validar_lote(cambiado, ventanas, indice['fotogramas'])

    def test_cache_por_proveedor_y_retomar_sin_repetir_lotes(self):
        indice = self.indice()
        ficha = dict(proveedor_analisis='Claude', analisis_ejecucion='uno')
        respuestas = [informe_lote(indice['ventanas'][:2]), informe_lote(indice['ventanas'][2:])]
        with patch.object(av, 'consultar', side_effect=respuestas) as modelo:
            informe = av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 2)
        with patch.object(av, 'consultar', side_effect=AssertionError('debe reutilizar')):
            self.assertEqual(av.examinar(self.destino, dict(ficha, analisis_ejecucion='dos'), {}, lambda *a: None), informe)
        with patch.object(av, 'consultar', side_effect=respuestas) as modelo:
            nuevo = av.examinar(self.destino, dict(ficha, proveedor_analisis='ChatGPT'), {}, lambda *a: None)
        self.assertNotEqual(nuevo['firma'], informe['firma'])
        self.assertEqual(modelo.call_count, 2)
        self.assertTrue(all(len(llamada.args[2]) <= 5 for llamada in modelo.call_args_list))

    def test_cancelado_no_publica_inspeccion_completa_y_retoma_pendiente(self):
        indice = self.indice()
        ficha = dict(proveedor_analisis='Claude', analisis_ejecucion='uno')
        with patch.object(av, 'consultar', side_effect=[informe_lote(indice['ventanas'][:2]), Cancelado()]), self.assertRaises(Cancelado):
            av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertFalse((self.destino / 'analisis_visual' / 'informe_actual.json').exists())
        with patch.object(av, 'consultar', return_value=informe_lote(indice['ventanas'][2:])) as modelo:
            av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertEqual(modelo.call_count, 1)
        progreso = leer_json(str(self.destino / 'analisis_visual' / 'progreso.json'))
        self.assertEqual(progreso['lotes_completos'], progreso['lotes_total'])

    def test_sintetizar_parcial_reutiliza_lotes_sin_consultar_pendientes(self):
        indice = self.indice()
        ficha = dict(proveedor_analisis='Claude', analisis_ejecucion='uno')
        escribir_json(str(self.destino / 'transcripcion' / 'resultado.json'), {})
        with patch.object(av, 'consultar', side_effect=[informe_lote(indice['ventanas'][:2]), Cancelado()]), self.assertRaises(Cancelado):
            av.examinar(self.destino, ficha, {}, lambda *a: None)
        solicitud = av.solicitar_sintesis(self.destino, ficha)
        self.assertEqual(solicitud['lotes_completos'], 1)
        with patch.object(av, 'consultar', side_effect=AssertionError('no iniciar más lotes')):
            informe = av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertTrue(informe['cobertura']['parcial'])
        self.assertEqual(informe['cobertura']['lotes_completos'], 1)
        self.assertEqual(informe['cobertura']['lotes_total'], 2)
        self.assertEqual(informe['cobertura']['hasta_s'], 16)
        self.assertEqual(len(informe['intervalos']), 2)
        self.assertEqual(leer_json(str(self.destino / 'analisis_visual' / 'progreso.json'))['etapa'], 'sintesis')
        manifiesto = {}
        ia._incluir_inspeccion(self.destino, manifiesto)
        self.assertTrue(manifiesto['inspeccion_visual']['cobertura']['parcial'])
        metadatos = dict(cobertura_visual=av.resumen_cobertura(indice), desfase_audio_s=0)
        transcripcion = dict(segmentos=[dict(t_in=0, t_out=1, texto='Examinado'), dict(t_in=18, t_out=19, texto='NO EXAMINADO')],
                            texto='Examinado NO EXAMINADO')
        analisis = dict(resumen='Informe parcial', guia_visual='Original drawing', guia_guion='Guía narrativa', idioma='es',
            areas={a: 'Observaciones' for a in ia.AREAS}, recursos=[dict(nombre='Recurso', motivo='Necesario', motor='imagen')])
        with patch.object(av, 'examinar', return_value=informe), patch.object(av, 'consultar', return_value=analisis) as modelo:
            ia.consultar(self.destino, dict(ficha, _transcripcion=transcripcion), metadatos, ['hoja_no_examinada.jpg'], lambda *a: None)
        prompt = modelo.call_args.args[1]
        self.assertIn('INFORME PARCIAL', prompt)
        self.assertNotIn('NO EXAMINADO', prompt)
        self.assertNotIn('TODO el vídeo', prompt)
        self.assertNotIn('hoja_no_examinada.jpg', modelo.call_args.args[2])

    def test_peticion_durante_un_lote_termina_ese_lote_y_no_abre_otro(self):
        indice = self.indice(40)
        ficha = dict(proveedor_analisis='Claude', analisis_ejecucion='uno')
        escribir_json(str(self.destino / 'transcripcion' / 'resultado.json'), {})
        llamadas = []
        def consultar(*args, **kwargs):
            numero = len(llamadas)
            llamadas.append(numero)
            if numero == 1:
                av.solicitar_sintesis(self.destino, ficha)
            self.assertLess(numero, 2)
            return informe_lote(indice['ventanas'][numero * 2:numero * 2 + 2])
        with patch.object(av, 'consultar', side_effect=consultar):
            informe = av.examinar(self.destino, ficha, {}, lambda *a: None)
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(informe['cobertura']['lotes_completos'], 2)
        self.assertTrue(informe['cobertura']['parcial'])

    def test_no_sintetiza_cero_lotes_ni_modifica_estilos_publicados(self):
        self.indice()
        escribir_json(str(self.destino / 'transcripcion' / 'resultado.json'), {})
        with self.assertRaisesRegex(ValueError, 'al menos un lote'):
            av.solicitar_sintesis(self.destino, {})
        with self.assertRaisesRegex(ValueError, 'publicado'):
            av.solicitar_sintesis(self.destino, dict(preset_id='publicado'))
        self.assertFalse((self.destino / 'analisis_visual' / 'sintesis_solicitada.json').exists())

    def test_muestreo_selectivo_cubre_inicio_y_final_sin_inventar_continuidad(self):
        indice = self.indice(80)
        indice.update(modo='movimiento_selectivo', ventanas_ia=['V0001', 'V0010'])
        escribir_json(str(self.destino / 'analisis_visual' / 'indice.json'), indice)
        ventanas = [indice['ventanas'][0], indice['ventanas'][-1]]
        transcripcion = dict(segmentos=[dict(t_in=0, t_out=1, texto='Inicio'),
            dict(t_in=30, t_out=31, texto='FUERA'), dict(t_in=78, t_out=79, texto='Final')])
        with patch.object(av, 'consultar', return_value=informe_lote(ventanas)) as modelo:
            informe = av.examinar(self.destino, {}, transcripcion, lambda *a: None)
        self.assertEqual(modelo.call_count, 1)
        self.assertEqual([v['id'] for v in informe['intervalos']], ['V0001', 'V0010'])
        self.assertTrue(informe['cobertura']['muestreo_selectivo'])
        self.assertFalse(informe['cobertura']['cobertura_visual_completa'])
        self.assertFalse(informe['cobertura']['parcial'])  # completó la selección prevista
        self.assertEqual(informe['cobertura']['duracion_examinada_s'], 16)
        self.assertNotIn('FUERA', modelo.call_args.args[1])
        self.assertIn('MEDICIONES_OPENCV', modelo.call_args.args[1])

    def test_modo_eficiente_solicita_esfuerzo_medio_sin_cambiar_proveedor(self):
        with patch.object(cli_claude, 'ejecutar', return_value=('{"ok":true}', {})) as modelo:
            av.consultar('Claude', 'Inspecciona MINUCIOSAMENTE\nMEDICIONES_OPENCV', [], self.destino, lambda *a: None, 'Prueba')
        self.assertEqual(modelo.call_args.kwargs['esfuerzo'], 'medium')

    def test_informe_completo_viaja_en_manifiesto(self):
        indice = self.indice(2)
        with patch.object(av, 'consultar', return_value=informe_lote(indice['ventanas'])):
            av.examinar(self.destino, dict(proveedor_analisis='ChatGPT'), {}, lambda *a: None)
        manifiesto = {}
        ia._incluir_inspeccion(self.destino, manifiesto)
        self.assertEqual(manifiesto['inspeccion_visual']['proveedor'], 'ChatGPT')

    def test_corregir_narracion_invalida_cache_visual(self):
        indice = self.indice(2)
        ficha = dict(proveedor_analisis='ChatGPT')
        with patch.object(av, 'consultar', return_value=informe_lote(indice['ventanas'])) as modelo:
            anterior = av.examinar(self.destino, ficha, dict(texto='Original'), lambda *a: None)
            corregido = av.examinar(self.destino, ficha, dict(texto='Corregido'), lambda *a: None)
        self.assertEqual(modelo.call_count, 2)
        self.assertNotEqual(anterior['firma'], corregido['firma'])

    def test_publicado_no_cambia_de_analista_y_error_no_prepara_motor(self):
        with patch.object(ia, 'carpeta', return_value=self.destino), \
                patch.object(ia, 'leer', return_value=dict(preset_id='publicado')):
            with self.assertRaises(ValueError): ia.cambiar_analista('', '', 'ChatGPT')
        with patch.object(ia, 'carpeta', return_value=self.destino), \
                patch.object(ia, 'leer', return_value=dict(estado='error', analisis={'resumen': 'Informe anterior'})):
            with self.assertRaises(ValueError): ia.preparar(lambda *a: None, '', '', None)

    def test_segmentos_respetan_desfase_audio_y_no_inventan_habla_fuera(self):
        indice = self.indice(20)
        indice['desfase_audio_s'] = 16
        escribir_json(str(self.destino / 'analisis_visual' / 'indice.json'), indice)
        transcripcion = dict(texto='Frase final.', segmentos=[dict(t_in=0, t_out=1, texto='Frase final.', palabras=[])])
        with patch.object(av, 'consultar', side_effect=[informe_lote(indice['ventanas'][:2]),
                informe_lote(indice['ventanas'][2:])]) as modelo:
            av.examinar(self.destino, {}, transcripcion, lambda *a: None)
        narraciones = [json.loads(c.args[1].split('Narración de estos intervalos:\n')[1]) for c in modelo.call_args_list]
        self.assertEqual(narraciones[0], [])
        self.assertEqual(narraciones[1][0]['t_in'], 16)

    @unittest.skipUnless(REAL, '--real comprueba todos los frames, cortes y extracción con ffmpeg; sin IA')
    def test_ffmpeg_barre_todos_los_frames_y_detecta_cortes_en_mkv(self):
        import subprocess
        from PIL import Image
        from pasos import medios
        video = self.destino / 'referencia.mkv'
        grafo = 'color=red:s=640x360:r=12:d=1.25[r];color=blue:s=640x360:r=12:d=1.25[b];color=white:s=640x360:r=12:d=1.25[w];[r][b][w]concat=n=3:v=1:a=0'
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', grafo, '-c:v', 'libx264', str(video)],
                       capture_output=True, check=True, timeout=60)
        meta, hojas = ia.extraer(self.destino, dict(referencia=video.name), lambda *a: None)
        indice = leer_json(str(self.destino / 'analisis_visual' / 'indice.json'))
        self.assertEqual(indice['fotogramas_decodificados'], 45)
        self.assertEqual(len(indice['cortes']), 2)
        self.assertEqual(indice['planos_detectados'], 3)
        self.assertGreater(len(indice['fotogramas']), 24)
        self.assertEqual(len(hojas), 6)
        with Image.open(self.destino / 'analisis_visual' / indice['fotogramas'][0]['archivo']) as imagen:
            self.assertEqual(imagen.size, (640, 360))  # no fabricar detalle reescalando
        with patch.object(espacio_estilo, 'correr', side_effect=AssertionError('no volver a decodificar')):
            self.assertEqual(av.explorar(self.destino, video, meta, lambda *a: None)['firma'], indice['firma'])


if __name__ == '__main__':
    unittest.main()
