"""Pronunciación, marcas SSE/WS y persistencia. Sin llamadas a proveedores.

Con --real abre Chromium contra un servidor temporal y comprueba lo visible.
"""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import Mock, patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
AISLADO = tempfile.TemporaryDirectory(prefix='estudio_pronunciaciones_')
for variable in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS',
                 'ESTUDIO_COSTE_GLOBAL', 'ESTUDIO_BITACORA_GLOBAL',
                 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_PRESETS'):
    os.environ[variable] = os.path.join(AISLADO.name, variable)
REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')

from nucleo import Estado, Proyecto
from pasos import p4_voz as voz, p5_revision_audio as revision, presets_canal as presets, pronunciaciones as pr

DICCIONARIO = 'William = <<ˈ|w|ɪ|l|j|ə|m>>\nShakespeare = shéik spir'
TEXTO = 'William Shakespeare habló. Después Shakespeare volvió.'
LEIDAS = ['<<ˈ|w|ɪ|l|j|ə|m>>', 'shéik', 'spir', 'habló.', 'Después', 'shéik', 'spir', 'volvió.']


def evento():
    return {'data': base64.b64encode(b'\0\0' * voz.SR * 4).decode(),
            'word_timestamps': {'words': LEIDAS,
                'start': [i * .5 for i in range(8)],
                'end': [i * .5 + .4 for i in range(8)]}}


class Pronunciaciones(unittest.TestCase):
    def setUp(self):
        self.cfg = voz.resolver_params({'pronunciaciones': DICCIONARIO,
                                        'hueco_minimo': 0})

    def test_sustitucion_no_encadena_ni_toca_etiquetas_o_deletreos(self):
        reglas = 'John Smith = yon smiz\nJohn = yon\nyon = otro'
        texto = 'JOHN SMITH, John y Johnson. <spell>John</spell><break time="400ms"/>'
        self.assertEqual(pr.aplicar(texto, reglas),
            'yon smiz, yon y Johnson. <spell>John</spell><break time="400ms"/>')
        self.assertEqual(pr.aplicar(texto, ''), texto)

    def test_entradas_invalidas_se_rechazan_antes_de_pagar(self):
        for valor in ('William', '= lectura', 'William = ',
                      'William = uno\nWILLIAM = dos', 'W = <break/>',
                      'W = <<w|NO>>', [], False):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                voz.resolver_params({'pronunciaciones': valor})
        with self.assertRaises(ValueError):
            voz.resolver_params({'modelo': 'sonic-2', 'pronunciaciones': DICCIONARIO})
        self.assertNotIn('pronunciaciones', voz.resolver_params({}))

    def comprobar_marcas(self, palabras):
        self.assertEqual([p['w'] for p in palabras], TEXTO.split())
        # Las anclas posteriores a los nombres retienen sus marcas exactas.
        self.assertEqual(palabras[2], dict(w='habló.', s=1.5, e=1.9))
        self.assertEqual(palabras[-1], dict(w='volvió.', s=3.5, e=3.9))
        _, reparto = voz._reparto([dict(id='B001', texto='William Shakespeare habló.'),
            dict(id='B002', texto='Después Shakespeare volvió.')], palabras)
        self.assertEqual(reparto['B002'][0]['w'], 'Después')
        self.assertEqual(reparto['B002'][0]['s'], 2)

    def test_sse_envia_fonemas_y_restaura_nombre_y_cortes(self):
        respuesta = Mock(status_code=200)
        respuesta.iter_lines.return_value = ['data:' + json.dumps(evento())]
        with patch.object(voz.motor, 'cargar_api_key', return_value='doble'), \
                patch.object(voz.requests, 'post', return_value=respuesta) as post:
            wav, duracion, palabras = voz._toma_real(TEXTO, self.cfg, lambda *a: None)
        enviado = post.call_args.kwargs['json']
        self.assertEqual(enviado['language'], 'es')
        self.assertIn('<<ˈ|w|ɪ|l|j|ə|m>> shéik spir habló.', enviado['transcript'])
        self.assertTrue(wav.startswith(b'RIFF'))
        self.assertEqual(duracion, 4)
        self.comprobar_marcas(palabras)

    def test_contexto_ws_recibe_correcciones_y_conserva_marcas(self):
        import websocket
        conexion = Mock()
        conexion.recv.side_effect = [json.dumps(evento()), json.dumps({'type': 'done'})]
        with patch.object(voz.motor, 'cargar_api_key', return_value='doble'), \
                patch.object(websocket, 'create_connection', return_value=conexion):
            _, _, palabras = voz._toma_por_contexto(
                ['William Shakespeare habló.', 'Después Shakespeare volvió.'],
                self.cfg, lambda *a: None)
        enviados = [json.loads(c.args[0]) for c in conexion.send.call_args_list]
        self.assertIn('shéik spir', enviados[1]['transcript'])
        self.assertEqual(enviados[0]['context_id'], enviados[1]['context_id'])
        self.comprobar_marcas(palabras)

    def test_marcas_omitidas_no_se_disimulan(self):
        with self.assertRaises(RuntimeError):
            pr.restaurar('William habló.', [dict(w='habló.', s=1, e=2)])

    def test_estilo_transmite_diccionario_y_permite_vaciarlo(self):
        ficha = presets.guardar('canal', 'Con pronunciaciones',
            {'voz': {'voz_id': 'voz_de_prueba', 'pronunciaciones': DICCIONARIO}})
        self.assertEqual(presets.cambios_para(ficha)['voz']['pronunciaciones'], DICCIONARIO)
        vacio = presets._limpiar_datos('voz', {'voz_id': 'voz_de_prueba', 'pronunciaciones': ''})
        self.assertNotIn('pronunciaciones', vacio)
        with self.assertRaises(presets.ErrorPreset):
            presets._limpiar_datos('voz', {'pronunciaciones': 'sin separador'})

    def test_api_estilo_permite_borrar_diccionario_y_rechaza_invalido(self):
        import app
        ficha = presets.guardar('canal', 'Editar pronunciaciones',
            {'voz': {'voz_id': 'voz_de_prueba', 'pronunciaciones': DICCIONARIO}})
        with patch.object(app, '_presets', return_value=presets), \
                patch.object(app, '_taller_de', side_effect=app.ErrorApi(404, 'sin taller')):
            with self.assertRaises(app.ErrorApi):
                app.editar_preset_light(ficha['id'], {'voz': {'pronunciaciones': 'inválido'}})
            resultado = app.editar_preset_light(ficha['id'], {'voz': {'pronunciaciones': ''}})
        self.assertNotIn('pronunciaciones', resultado['preset']['datos']['voz'])

    def test_cache_escucha_cambia_con_la_pronunciacion(self):
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta:
            proyecto = Proyecto.crear(carpeta, 'Muestra')
            params = dict(bloques=[dict(id='B001', texto=TEXTO)], pronunciaciones=DICCIONARIO)
            with patch.dict(os.environ, ESTUDIO_SIMULAR='1'):
                primera = voz.previsualizar(proyecto, params, 12)
                self.assertEqual(primera, voz.previsualizar(proyecto, params, 12))
                segunda = voz.previsualizar(proyecto, dict(params, pronunciaciones='William = uíliam'), 12)
            self.assertNotEqual(primera, segunda)
            meta = json.loads(Path(primera[:-4] + '.json').read_text())
            self.assertEqual(meta['texto'], 'William. Shakespeare.')

    def test_quitar_diccionario_no_sella_audio_con_la_lectura_anterior(self):
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta, \
                patch.dict(os.environ, ESTUDIO_SIMULAR='1'):
            proyecto = Proyecto.crear(carpeta, 'Quitar pronunciaciones')
            estado = Estado(proyecto)
            params = dict(bloques=[dict(id='B001', texto=TEXTO)], pronunciaciones=DICCIONARIO)
            estado.actualizar_params('voz', {'pronunciaciones': DICCIONARIO})
            salidas = voz.ejecutar(proyecto, params)
            estado.completar('voz', salidas)
            destino = proyecto.ruta_trabajo('revision_audio')
            cfg = voz.resolver_params(params)
            self.assertIsNotNone(revision._sellar_sin_cambios(proyecto,
                params['bloques'], cfg, destino, lambda *a: None))
            cfg_sin = voz.resolver_params(dict(params, pronunciaciones=''))
            self.assertIsNone(revision._sellar_sin_cambios(proyecto,
                params['bloques'], cfg_sin, destino, lambda *a: None))
            self.assertEqual(revision._config_voz(proyecto, {'pronunciaciones': ''})['pronunciaciones'], '')

    @unittest.skipUnless(REAL, 'usa --real para abrir Chromium')
    def test_navegador_muestra_autoguarda_recarga_y_vacia(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta:
            proyecto = Proyecto.crear(carpeta, 'Pronunciación visible')
            estado = Estado(proyecto)
            estado.actualizar_params('voz', {'voz_id': 'voz_de_prueba'})
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                puerto = sock.getsockname()[1]
            env = dict(os.environ, ESTUDIO_SIMULAR='1')
            proceso = subprocess.Popen([sys.executable, 'app.py', '--puerto', str(puerto),
                '--proyectos', carpeta], cwd=RAIZ, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                    abrir = '''async pid => {
                        document.querySelector('#inicio')?.remove();
                        APP.light.vista='elegido'; APP.light.video.vista='encargo_video';
                        await cargarVideoLight(pid);
                    }'''
                    pagina.evaluate(abrir, proyecto.id)
                    pagina.wait_for_function('!APP.light.voces?.pidiendo')
                    area = pagina.get_by_role('textbox', name='Pronunciaciones', exact=True)
                    area.scroll_into_view_if_needed()
                    self.assertTrue(area.is_visible())
                    self.assertTrue(pagina.get_by_role('button', name='Escuchar pronunciaciones', exact=False).is_visible())
                    # Abrir no escribe params por defecto.
                    self.assertNotIn('pronunciaciones', Estado(proyecto).params('voz'))
                    area.fill(DICCIONARIO)
                    pagina.wait_for_function('APP.light.video.pedido?.guardado.pronunciaciones?.includes("Shakespeare")')
                    self.assertEqual(Estado(proyecto).params('voz')['pronunciaciones'], DICCIONARIO)
                    pagina.reload()
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate(abrir, proyecto.id)
                    pagina.wait_for_function('!APP.light.voces?.pidiendo')
                    self.assertEqual(area.input_value(), DICCIONARIO)
                    captura = os.environ.get('ESTUDIO_CAPTURA_PRONUNCIACIONES')
                    if captura:
                        area.scroll_into_view_if_needed()
                        pagina.screenshot(path=captura)
                    pagina.get_by_role('button', name='Escuchar pronunciaciones', exact=False).click()
                    pagina.wait_for_function('Object.keys(APP.light.escuchas || {}).length > 0')
                    area.fill('')
                    pagina.wait_for_function('APP.light.video.pedido?.guardado.pronunciaciones === ""')
                    self.assertEqual(Estado(proyecto).params('voz')['pronunciaciones'], '')
                    self.assertEqual(errores, [])
                    navegador.close()
            finally:
                proceso.terminate()
                proceso.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
