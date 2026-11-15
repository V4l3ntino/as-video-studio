"""Contrato ElevenLabs sin consumir cuota. --real verifica además la interfaz en Chromium."""
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
from unittest.mock import MagicMock, Mock, patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
AISLADO = tempfile.TemporaryDirectory(prefix='estudio_elevenlabs_')
for variable in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS',
                 'ESTUDIO_COSTE_GLOBAL', 'ESTUDIO_BITACORA_GLOBAL',
                 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_PRESETS'):
    os.environ[variable] = os.path.join(AISLADO.name, variable)
REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')

from nucleo import Estado, Proyecto
from pasos import claves, comun, p4_voz as voz, p5_revision_audio as revision, presets_canal
from nucleo import coste


def respuesta(datos, status=200):
    r = MagicMock(status_code=status, text='error de prueba')
    r.json.return_value = datos
    r.__enter__.return_value = r
    return r


def tts_fake(_url, **kwargs):
    texto = kwargs['json']['text']
    paso = .04
    return respuesta({'audio_base64': base64.b64encode(b'\0\0' * int(24000 * paso * (len(texto) + 1))).decode(),
        'alignment': {'characters': list(texto),
            'character_start_times_seconds': [i * paso for i in range(len(texto))],
            'character_end_times_seconds': [(i + 1) * paso for i in range(len(texto))]}})


class ElevenLabs(unittest.TestCase):
    def setUp(self):
        self.motor = voz.motor_elevenlabs()
        self.cfg = voz.resolver_params({'proveedor': 'elevenlabs', 'voz_id': 'voice_prueba_123',
                                        'hueco_minimo': 0, 'velocidad': 'normal'})

    def test_compatibilidad_sin_proveedor_y_validacion(self):
        cfg = voz.resolver_params({})
        self.assertNotIn('proveedor', cfg)
        self.assertEqual(voz.proveedor_de(cfg), 'cartesia')
        self.assertEqual(self.cfg['modelo'], 'eleven_multilingual_v2')
        with self.assertRaises(ValueError):
            voz.resolver_params({'proveedor': 'inventado'})
        with self.assertRaisesRegex(ValueError, 'fonemas'):
            voz.resolver_params(dict(self.cfg, pronunciaciones='William = <<w|ɪ>>'))
        with patch.object(self.motor.requests, 'post', side_effect=AssertionError('sin API')):
            with self.assertRaisesRegex(ValueError, 'Elige una voz'):
                voz._toma_elevenlabs('Hola.', dict(self.cfg, voz_id=''), Mock())

    def test_clave_aislada_conservada_y_sin_filtrarse(self):
        guardada = claves.guardar({'elevenlabs': {'clave': 'clave_elevenlabs_123456'}})
        self.assertTrue(guardada['elevenlabs']['puesta'])
        self.assertNotIn('clave_elevenlabs_123456', json.dumps(guardada))
        claves.guardar({'cartesia': {'clave': 'otra_clave'}})
        self.assertEqual(self.motor.cargar_api_key(), 'clave_elevenlabs_123456')
        claves.guardar({'elevenlabs': {'clave': claves.CONSERVAR}})
        self.assertIn('ELEVENLABS_API_KEY=clave_elevenlabs_123456', Path(claves.FICHERO_ENV).read_text())
        with patch.dict(os.environ, ELEVENLABS_API_KEY='clave_entorno'):
            self.assertEqual(self.motor.cargar_api_key(), 'clave_entorno')
        claves.guardar({'elevenlabs': {'clave': ''}})
        self.assertNotIn('ELEVENLABS_API_KEY=', Path(claves.FICHERO_ENV).read_text())

    def test_alineacion_por_caracter_y_audio_convertido_sin_cartesia(self):
        with patch.object(self.motor, 'cargar_api_key', return_value='clave'), \
                patch.object(self.motor.requests, 'post', side_effect=tts_fake) as api, \
                patch('websocket.create_connection', side_effect=AssertionError('no Cartesia')):
            wav, duracion, palabras = voz._toma_por_contexto(
                ['Hola, mundo.', ' Otra frase.'], self.cfg, Mock())
        self.assertEqual(wav[:4], b'RIFF')
        self.assertAlmostEqual((len(wav) - 44) / (44100 * 2), duracion)
        self.assertEqual([p['w'] for p in palabras], ['Hola,', 'mundo.', 'Otra', 'frase.'])
        self.assertIn('/with-timestamps', api.call_args.args[0])
        self.assertEqual(api.call_args.kwargs['headers']['xi-api-key'], 'clave')
        self.assertEqual(api.call_args.kwargs['params']['output_format'], 'pcm_24000')
        self.assertNotIn('language_code', api.call_args.kwargs['json'])

    def test_diccionario_restaura_palabras_y_no_envia_ssml_cartesia(self):
        with patch.object(self.motor, 'cargar_api_key', return_value='clave'), \
                patch.object(self.motor.requests, 'post', side_effect=tts_fake) as api:
            _, _, palabras = voz.sintetizar_toma('Shakespeare habló.<break time="900ms"/>',
                dict(self.cfg, pronunciaciones='Shakespeare = shéik spir'))
        self.assertEqual(api.call_args.kwargs['json']['text'], 'shéik spir habló.')
        self.assertEqual([p['w'] for p in palabras], ['Shakespeare', 'habló.'])

    def test_tomas_largas_respetan_limite_y_contexto_sin_perder_texto(self):
        texto = ('Una frase completa. ' * 700).strip()
        partes = self.motor.dividir(texto)
        self.assertEqual(''.join(partes), texto)
        self.assertTrue(all(len(p) <= 9000 for p in partes))
        with patch.object(self.motor, 'cargar_api_key', return_value='clave'), \
                patch.object(self.motor.requests, 'post', side_effect=tts_fake) as api:
            _, duracion, palabras = voz.sintetizar_toma(texto, self.cfg)
        self.assertEqual(api.call_count, len(partes))
        self.assertIn('next_text', api.call_args_list[0].kwargs['json'])
        self.assertIn('previous_text', api.call_args_list[1].kwargs['json'])
        self.assertEqual(len(palabras), len(texto.split()))
        self.assertLessEqual(palabras[-1]['e'], duracion)

    def test_fallo_no_reintenta_ni_cambia_a_cartesia(self):
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta, \
                patch.object(self.motor, 'cargar_api_key', return_value='clave'), \
                patch.object(self.motor.requests, 'post', return_value=respuesta(
                    {'detail': {'message': 'quota exceeded'}}, 401)) as api, \
                patch('websocket.create_connection', side_effect=AssertionError('no respaldo')):
            with self.assertRaisesRegex(RuntimeError, 'ElevenLabs HTTP 401: quota exceeded'):
                voz.sintetizar_bloques([{'id': 'B001', 'texto': 'Hola.', 'abre_seccion': True},
                    {'id': 'B002', 'texto': 'Adiós.', 'abre_seccion': True}], carpeta, self.cfg)
        self.assertEqual(api.call_count, 1)
        with self.assertRaisesRegex(RuntimeError, 'alineación incompleta'):
            self.motor.palabras_de({'characters': ['a']})

    def test_catalogo_paginado_y_cache_por_cuenta(self):
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta, \
                patch.object(self.motor, 'cargar_api_key', return_value='cuenta1') as clave, \
                patch.object(self.motor.requests, 'get', side_effect=[
                    respuesta({'voices': [{'voice_id': 'uno', 'name': 'Uno', 'category': 'cloned'}],
                               'has_more': True, 'next_page_token': 'pagina2'}),
                    respuesta({'voices': [{'voice_id': 'dos', 'name': 'Dos'}], 'has_more': False}),
                    respuesta({'voices': [{'voice_id': 'tres', 'name': 'Tres'}]})]) as api:
            cache = os.path.join(carpeta, 'voces.json')
            voces = self.motor.listar_voces(cache)
            self.assertEqual([v['id'] for v in voces], ['uno', 'dos'])
            self.assertFalse(voces[0]['publica'])
            self.assertEqual(api.call_args.kwargs['params']['next_page_token'], 'pagina2')
            self.assertEqual(self.motor.listar_voces(cache), voces)
            self.assertEqual(api.call_count, 2)
            clave.return_value = 'cuenta2'
            self.assertEqual(self.motor.listar_voces(cache)[0]['id'], 'tres')
            self.assertNotIn('cuenta2', Path(cache).read_text())

    def test_consulta_id_fuera_del_catalogo_no_genera_audio(self):
        ident = 'jtfxplhZxnBzQICVwoQn'
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta, \
                patch.object(self.motor, 'cargar_api_key', return_value='cuenta'), \
                patch.object(self.motor.requests, 'get', side_effect=[
                    respuesta({'voices': [{'voice_id': 'otra_voz', 'name': 'Otra'}]}),
                    respuesta({'voice_id': ident, 'name': 'David Martin - Confident and Friendly',
                        'category': 'professional', 'sharing': {'public_owner_id': 'propietario_publico'},
                        'verified_languages': [{'language': 'es'}]})]) as api, \
                patch.object(self.motor.requests, 'post', side_effect=AssertionError('sin síntesis')):
            cache = os.path.join(carpeta, 'voces.json')
            self.motor.listar_voces(cache)
            fecha = json.loads(Path(cache).read_text())['epoch']
            ficha = self.motor.obtener_voz(ident, cache)
            self.assertEqual(ficha['nombre'], 'David Martin - Confident and Friendly')
            self.assertTrue(ficha['publica'])
            self.assertEqual(ficha['idioma'], 'es')
            self.assertEqual(api.call_args.args[0], self.motor.API + '/voices/' + ident)
            voces = self.motor.listar_voces(cache)
            self.assertEqual([v['id'] for v in voces], ['otra_voz', ident])
            self.assertEqual(json.loads(Path(cache).read_text())['epoch'], fecha)
        with patch.object(self.motor, 'cargar_api_key', return_value='cuenta'), \
                patch.object(self.motor.requests, 'get', return_value=respuesta({}, 404)):
            with self.assertRaisesRegex(ValueError, 'no encuentra'):
                voz.obtener_voz(ident, 'elevenlabs')
        with patch.object(self.motor.requests, 'get', side_effect=AssertionError('sin petición')):
            with self.assertRaises(ValueError):
                voz.obtener_voz('../../secreto', 'elevenlabs')

    def test_consulta_cartesia_y_endpoint_respetan_el_proveedor(self):
        import app
        ident = '12345678-1234-1234-1234-123456789abc'
        with patch.object(comun, 'llamar_motor', return_value='clave'), \
                patch.object(voz.requests, 'get', return_value=respuesta({
                    'id': ident, 'name': 'Voz Cartesia', 'language': 'es'})) as api:
            ficha = voz.obtener_voz(ident)
            self.assertEqual(ficha['nombre'], 'Voz Cartesia')
            self.assertEqual(api.call_args.args[0], voz.API_VOCES + ident)
        with patch.object(app.PASOS_MODULOS.p4_voz, 'obtener_voz', return_value=ficha) as obtener:
            self.assertEqual(app.consultar_voz_por_id(ident, 'cartesia')['voz'], ficha)
            obtener.assert_called_once_with(ident, 'cartesia')
        with patch.object(app.PASOS_MODULOS.p4_voz, 'obtener_voz', side_effect=ValueError('ID inválido')):
            with self.assertRaises(app.ErrorApi) as fallo:
                app.consultar_voz_por_id('..', 'cartesia')
            self.assertEqual(fallo.exception.codigo, 400)

    def test_generacion_revision_y_regrabado_con_marcas_reales(self):
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta, \
                patch.object(self.motor, 'cargar_api_key', return_value='clave'), \
                patch.object(self.motor.requests, 'post', side_effect=tts_fake), \
                patch('websocket.create_connection', side_effect=AssertionError('no Cartesia')):
            proyecto = Proyecto.crear(carpeta, 'Prueba ElevenLabs')
            estado = Estado(proyecto)
            estado.actualizar_params('voz', self.cfg)
            bloques = [{'id': 'B001', 'texto': 'Hola, mundo.<break time="900ms"/>'},
                       {'id': 'B002', 'texto': 'Otra frase.'}]
            salida = voz.ejecutar(proyecto, dict(self.cfg, bloques=bloques))
            estado.completar('voz', salida)
            meta = comun.leer_salida(proyecto, 'voz', voz.NOMBRE_META)
            self.assertEqual(len(meta['secciones']), 2)
            self.assertEqual(meta['controles']['proveedor'], 'elevenlabs')
            destino = comun.preparar_trabajo(proyecto, 'revision_audio')
            self.assertIsNotNone(revision._sellar_sin_cambios(proyecto, bloques,
                self.cfg, destino, Mock()))
            nueva_cfg = voz.resolver_params({'voz_id': self.cfg['voz_id'], 'hueco_minimo': 0})
            self.assertIsNone(revision._sellar_sin_cambios(proyecto, bloques, nueva_cfg, destino, Mock()))
            # La regrabación usa el mismo proveedor y cose sin perder el otro bloque.
            salida, nuevos = voz.regrabar_seccion(bloques, 'SB001', self.cfg, meta,
                proyecto.ruta_paso('voz'), avisar=Mock())
            self.assertEqual(len(salida['bloques']), 2)
            self.assertEqual(nuevos, bloques)

    def test_estilo_conserva_proveedor_y_no_tarifa_como_cartesia(self):
        ficha = presets_canal._limpiar_datos('voz', {'proveedor': 'elevenlabs', 'voz_id': 'voz123456'})
        self.assertEqual(ficha['proveedor'], 'elevenlabs')
        with patch.object(coste, '_anotar') as anotar, patch.object(coste, 'tarifas', return_value={
                'tts': {'usd_por_caracter': .123}}):
            coste.reportar_tts(100, detalle={'proveedor': 'elevenlabs'})
            self.assertIsNone(anotar.call_args.kwargs['usd'])

    def test_api_cambia_proveedor_del_estilo_sin_reutilizar_voz_anterior(self):
        import app
        ficha = presets_canal.guardar('canal', 'Cambio de proveedor',
            {'voz': {'voz_id': 'cartesia_123', 'voz_nombre': 'Antes', 'modelo': 'sonic-3.5'}})
        with patch.object(app, '_presets', return_value=presets_canal), \
                patch.object(app, '_taller_de', side_effect=app.ErrorApi(404, 'sin taller')):
            resultado = app.editar_preset_light(ficha['id'], {'voz': {
                'proveedor': 'elevenlabs', 'voz_id': '', 'voz_nombre': '', 'modelo': 'eleven_multilingual_v2'}})
        datos = resultado['preset']['datos']
        self.assertEqual(datos['voz']['proveedor'], 'elevenlabs')
        self.assertNotIn('voz_id', datos['voz'])
        self.assertEqual(datos['origen']['proveedor_voz'], 'elevenlabs')
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta:
            proyecto = Proyecto.crear(carpeta, 'Vídeo con proveedor')
            ctx = app.Contexto(proyecto.raiz)
            app._sembrar_video_light(ctx, {'proveedor_voz': 'elevenlabs', 'voz_id': 'eleven_12345'})
            self.assertEqual(ctx.estado.params('voz')['proveedor'], 'elevenlabs')
            self.assertEqual(ctx.estado.params('voz')['voz_id'], 'eleven_12345')

    @unittest.skipUnless(REAL, 'usa --real para abrir Chromium')
    def test_interfaz_pestanas_guardado_y_configuracion(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(dir=AISLADO.name) as carpeta:
            proyecto = Proyecto.crear(carpeta, 'Proveedor visible')
            estado = Estado(proyecto)
            estado.actualizar_params('voz', {'voz_id': 'voz_cartesia_123',
                'bloques': [{'id': 'B001', 'texto': 'Esta es una muestra para elegir una voz.'}]})
            taller = Proyecto.crear(carpeta, 'Taller de voz')
            estilo = presets_canal.guardar('canal', 'Estilo con proveedor',
                {'voz': {'voz_id': 'cartesia_123', 'voz_nombre': 'Voz anterior'},
                 'origen': {'taller': taller.id}})
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); puerto = sock.getsockname()[1]
            env = dict(os.environ, ESTUDIO_SIMULAR='1')
            proceso = subprocess.Popen([sys.executable, 'app.py', '--puerto', str(puerto),
                '--proyectos', carpeta], cwd=RAIZ, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                url = f'http://127.0.0.1:{puerto}'
                for _ in range(100):
                    try:
                        urllib.request.urlopen(url, timeout=1).close(); break
                    except OSError:
                        time.sleep(.1)
                with sync_playwright() as pw:
                    navegador = pw.chromium.launch(headless=True)
                    pagina = navegador.new_page(viewport={'width': 1440, 'height': 1100})
                    errores = []
                    escuchas = []
                    pagina.on('pageerror', lambda e: errores.append(str(e)))
                    pagina.on('request', lambda r: escuchas.append((r.url, r.post_data_json))
                        if r.method == 'POST' and r.url.endswith('/voz/previsualizar') else None)
                    pagina.route('**/api/voces?**', lambda route: route.fulfill(json={
                        'voces': [{'id': 'voz_eleven_123', 'nombre': 'Voz ElevenLabs'},
                                  {'id': 'voz_eleven_456', 'nombre': 'Otra voz', 'descripcion': 'Cálida y pausada'}]
                        if 'proveedor=elevenlabs' in route.request.url else []}))
                    ident = 'jtfxplhZxnBzQICVwoQn'
                    pagina.route('**/api/voces/*?**', lambda route: route.fulfill(json={
                        'voz': {'id': ident, 'nombre': 'David Martin - Confident and Friendly',
                                'idioma': 'es', 'publica': True}, 'proveedor': 'elevenlabs'})
                        if ident in route.request.url else route.fulfill(status=400,
                            json={'error': 'No se encuentra esa voz en ElevenLabs'}))
                    pagina.goto(url)
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    abrir = '''async pid => {
                        document.querySelector('#inicio')?.remove();
                        APP.light.vista='elegido'; APP.light.video.vista='encargo_video';
                        await cargarVideoLight(pid);
                    }'''
                    pagina.evaluate(abrir, proyecto.id)
                    pagina.get_by_role('tab', name='Cartesia', exact=True).wait_for()
                    self.assertEqual(pagina.get_by_role('tab', name='Cartesia', exact=True).get_attribute('aria-selected'), 'true')
                    self.assertNotIn('proveedor', Estado(proyecto).params('voz'))
                    pagina.get_by_role('tab', name='ElevenLabs', exact=True).click()
                    pagina.wait_for_function('APP.light.video.pedido?.guardado.proveedor_voz === "elevenlabs"')
                    self.assertEqual(Estado(proyecto).params('voz')['proveedor'], 'elevenlabs')
                    selector = pagina.locator('.selector-voz-video')
                    selector.get_by_role('button', name='Elegir locutor', exact=True).click()
                    buscador = selector.get_by_role('textbox', name='Buscar locutor', exact=True)
                    buscador.fill('Voz ElevenLabs')
                    self.assertEqual(selector.locator('.elegir-voz').count(), 1)
                    selector.get_by_title('escuchar Voz ElevenLabs', exact=True).click()
                    pagina.wait_for_function('Object.keys(APP.light.escuchas || {}).length > 0')
                    self.assertEqual(Estado(proyecto).params('voz').get('voz_id'), '')
                    self.assertEqual(escuchas[-1][1]['params']['proveedor'], 'elevenlabs')
                    self.assertEqual(escuchas[-1][1]['params']['voz_id'], 'voz_eleven_123')
                    buscador.press('Escape')
                    self.assertEqual(selector.get_by_role('button', name='Elegir locutor', exact=True).get_attribute('aria-expanded'), 'false')
                    selector.get_by_role('button', name='Elegir locutor', exact=True).click()
                    selector.locator('.elegir-voz').filter(has_text='Voz ElevenLabs').click()
                    pagina.wait_for_function('APP.light.video.pedido?.guardado.voz_id === "voz_eleven_123"')
                    self.assertIn('Voz ElevenLabs', selector.locator('.desplegable-voz').inner_text())
                    selector.locator('.desplegable-voz').click()
                    selector.get_by_role('textbox', name='Buscar locutor', exact=True).fill('pausada')
                    self.assertEqual(selector.locator('.elegir-voz').count(), 1)
                    selector.scroll_into_view_if_needed()
                    pagina.screenshot(path='/tmp/opencode/elevenlabs-video.png')
                    buscador = selector.get_by_role('textbox', name='Buscar locutor', exact=True)
                    buscador.fill('voice_missing_123')
                    selector.get_by_role('button', name='Buscar por ID en el proveedor', exact=True).click()
                    selector.get_by_text('No se encuentra esa voz en ElevenLabs', exact=True).wait_for()
                    buscador.fill(ident)
                    buscador.press('Enter')
                    remota = selector.locator('.elegir-voz').filter(has_text='David Martin')
                    remota.wait_for()
                    self.assertEqual(Estado(proyecto).params('voz')['voz_id'], 'voz_eleven_123')
                    selector.scroll_into_view_if_needed()
                    pagina.screenshot(path='/tmp/opencode/voz-buscada-por-id.png')
                    remota.click()
                    pagina.wait_for_function('id => APP.light.video.pedido?.guardado.voz_id === id', arg=ident)
                    self.assertEqual(Estado(proyecto).params('voz')['voz_id'], ident)
                    pagina.reload()
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate(abrir, proyecto.id)
                    self.assertEqual(pagina.get_by_role('tab', name='ElevenLabs', exact=True).get_attribute('aria-selected'), 'true')
                    pagina.evaluate('conmutarConfig(true)')
                    campo = pagina.get_by_role('textbox', name='API key de ElevenLabs', exact=True)
                    campo.wait_for(); campo.fill('clave_visible_prueba_1234')
                    seccion = pagina.locator('section').filter(has=pagina.get_by_role('heading', name='ElevenLabs — voz', exact=True))
                    seccion.get_by_role('button', name='Guardar clave', exact=True).click()
                    pagina.wait_for_function('estadoConfig().ficha?.elevenlabs?.puesta')
                    pagina.get_by_role('textbox', name='API key de ElevenLabs', exact=True).scroll_into_view_if_needed()
                    pagina.screenshot(path='/tmp/opencode/elevenlabs-configuracion.png')
                    pagina.evaluate('conmutarConfig(false)')
                    pagina.evaluate('id => irALight("preset", { abierto: id })', estilo['id'])
                    pagina.get_by_role('tab', name='ElevenLabs', exact=True).click()
                    pagina.evaluate('volcarPresetLight()')
                    self.assertEqual(presets_canal.leer(estilo['id'])['datos']['voz']['proveedor'], 'elevenlabs')
                    self.assertNotIn('voz_id', presets_canal.leer(estilo['id'])['datos']['voz'])
                    # Cambiar proveedor y elegir voz antes del debounce no debe perder el proveedor.
                    pagina.evaluate('''async id => {
                        const ficha = fichaLight(id);
                        apuntarVozLight(ficha, { proveedor: 'elevenlabs', voz_id: '' });
                        apuntarVozLight(ficha, { voz_id: 'voz_eleven_123', voz_nombre: 'Voz ElevenLabs' });
                        await volcarPresetLight();
                        repintarBloqueVoz(ficha);
                    }''', estilo['id'])
                    guardada = presets_canal.leer(estilo['id'])['datos']['voz']
                    self.assertEqual((guardada['proveedor'], guardada['voz_id']), ('elevenlabs', 'voz_eleven_123'))
                    pagina.locator('.bloque-voz summary').click()
                    pagina.locator('.bloque-voz').scroll_into_view_if_needed()
                    pagina.screenshot(path='/tmp/opencode/elevenlabs-estilo.png')
                    # Crear un vídeo reutiliza las tarjetas, pero elegir no cambia el estilo.
                    pagina.evaluate('id => elegirEstiloLight(fichaLight(id))', estilo['id'])
                    selector = pagina.locator('.selector-voz-video')
                    selector.get_by_role('button', name='Elegir locutor', exact=True).click()
                    selector.get_by_role('textbox', name='Buscar locutor', exact=True).fill('pausada')
                    antes = pagina.evaluate('Object.keys(APP.light.escuchas || {}).length')
                    selector.get_by_title('escuchar Otra voz', exact=True).click()
                    pagina.wait_for_function('n => Object.keys(APP.light.escuchas || {}).length > n', arg=antes)
                    self.assertIn('/api/presets-light/' + estilo['id'], escuchas[-1][0])
                    self.assertEqual(escuchas[-1][1]['voz_id'], 'voz_eleven_456')
                    self.assertEqual(escuchas[-1][1]['proveedor'], 'elevenlabs')
                    selector.locator('.elegir-voz').filter(has_text='Otra voz').click()
                    self.assertEqual(pagina.evaluate('encargoVideoLight().voz_id'), 'voz_eleven_456')
                    self.assertEqual(presets_canal.leer(estilo['id'])['datos']['voz']['voz_id'], 'voz_eleven_123')
                    selector.locator('.desplegable-voz').click()
                    selector.scroll_into_view_if_needed()
                    pagina.screenshot(path='/tmp/opencode/selector-locutor-crear-video.png')
                    self.assertEqual(errores, [])
                    navegador.close()
            finally:
                proceso.terminate(); proceso.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
