"""Contratos de IA Remotion: sin llamadas a proveedores ni consumo de cuota."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_animaciones_ia_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_REMOTION'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import Proyecto, escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import animaciones_ia as ia, remotion


class Contratos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = str(Path(self.tmp.name) / 'proyectos')
        self.proyecto = Proyecto.crear(self.raiz, 'Original')
        self.entorno = patch.dict(os.environ, ESTUDIO_REMOTION=str(Path(self.tmp.name) / 'biblioteca'))
        self.entorno.start(); self.addCleanup(self.entorno.stop)
        self.fuente = remotion.validar_plantilla(remotion.catalogo(self.raiz)[0])
        self.plan = dict(escenas=[dict(id=f'S00{i}', narracion=f'Escena {i}', t_in=i - 1, t_out=i) for i in range(1, 5)])

    def ejecutar(self, datos, generador=None, validacion=None):
        pedido = ia.validar_peticion(self.raiz, datos, self.proyecto.id, self.plan)
        with patch.object(ia, '_claude', return_value=dict(mensaje='Propuesta', conceptos={'S001': 'Movimiento suave'})), \
                patch.object(ia, '_generar', side_effect=generador or (lambda *a: dict(plantilla=copy.deepcopy(self.fuente)))) as modelo, \
                patch.object(ia, '_validar_resultado', side_effect=validacion or (lambda p, f, a: remotion.validar_plantilla(f))):
            resultado = ia.conversar(self.raiz, self.proyecto, self.proyecto.id, self.plan, pedido, lambda *a: None)
        return resultado, modelo

    def test_claude_respeta_contrato_real_del_prompt_de_sistema(self):
        from pasos import cli_claude
        ordenes = []
        def ejecutar(instruccion, **opciones):
            ordenes.append(cli_claude.construir_orden(**{k: opciones[k] for k in (
                'modelo', 'esfuerzo', 'sistema', 'herramientas_permitidas', 'herramientas_vetadas')}))
            self.assertIn('Encargo\ncon contexto', instruccion)
            self.assertIn('imagen con espacios.png', instruccion)
            return '{"mensaje":"Listo"}', {}
        with patch.object(cli_claude, 'localizar', return_value='claude.cmd'), \
                patch.object(cli_claude, 'ejecutar', side_effect=ejecutar):
            for llamada in (ia._claude, lambda *a: ia._generar('Claude', *a)):
                self.assertEqual(llamada('Encargo\ncon contexto', self.proyecto,
                    ['imagen con espacios.png'], lambda *a: None), dict(mensaje='Listo'))
        self.assertEqual(len(ordenes), 2)
        for orden in ordenes:
            sistema = orden[orden.index('--append-system-prompt') + 1]
            self.assertEqual(sistema, ' '.join(ia.SISTEMA.split()))
            self.assertNotIn('\n', sistema)
            self.assertNotIn('\r', sistema)
            self.assertEqual(orden[orden.index('--allowedTools') + 1], 'Read')

    def test_reparto_historial_global_y_borrado_no_rompe_proyecto(self):
        datos = dict(modo='escenas', escenas=[e['id'] for e in self.plan['escenas']], mensaje='Animar', porcentaje=50, generar=True)
        resultado, modelo = self.ejecutar(datos)
        self.assertEqual([c.args[0] for c in modelo.call_args_list], ['ChatGPT', 'ChatGPT', 'Claude', 'Claude'])
        fichas = ia.historial(self.raiz)
        self.assertEqual(len(fichas), 4)
        self.assertEqual({f['escena_origen'] for f in fichas}, {'S001', 'S002', 'S003', 'S004'})
        self.assertTrue(all(f['duracion'] == 1 for f in fichas))
        otra = Proyecto.crear(self.raiz, 'Otro vídeo')
        fuente = remotion.validar_plantilla(fichas[0]); referencia = remotion.huella(fuente)
        escribir_json(otra.ruta('remotion', 'plantillas', referencia + '.json'), fuente)
        ia.eliminar(self.raiz, 'historial', fichas[0]['id'])
        self.assertEqual(len(ia.historial(self.raiz)), 3)
        self.assertEqual(remotion.resolver(otra, referencia), fuente)
        self.assertEqual(len(ia.confirmar(self.raiz, resultado['sesion'], self.proyecto.id)), 4)
        self.assertEqual(len(ia.historial(self.raiz)), 3)  # No duplica el guardado automático.

    def test_extremos_del_reparto(self):
        for modo in ('escenas', 'crear', 'editar'):
            for porcentaje, proveedor in ((0, 'Claude'), (100, 'ChatGPT')):
                with self.subTest(modo=modo, porcentaje=porcentaje):
                    _, modelo = self.ejecutar(dict(modo=modo, escenas=['S001'], referencia='ejemplo-titulo',
                        categoria='reutilizables', mensaje='Animar', porcentaje=porcentaje, generar=True))
                    self.assertEqual(modelo.call_args.args[0], proveedor)

    def test_conversacion_pregunta_y_recuerda_respuesta_sin_generar(self):
        datos = dict(modo='crear', mensaje='Quiero un título', generar=False)
        pedido = ia.validar_peticion(self.raiz, datos, self.proyecto.id, {})
        with patch.object(ia, '_claude', return_value=dict(mensaje='¿Qué estilo buscas?', necesita_aclaracion=True)) as claude, \
                patch.object(ia, '_generar') as generar:
            respuesta = ia.conversar(self.raiz, self.proyecto, self.proyecto.id, {}, pedido, lambda *a: None)
            self.assertTrue(respuesta['pendiente_aclaracion'])
            self.assertIn('aún no debes iniciar la generación', claude.call_args.args[0])
            generar.assert_not_called()
        datos.update(sesion=respuesta['sesion'], mensaje='Cinematográfico, con letras doradas')
        pedido = ia.validar_peticion(self.raiz, datos, self.proyecto.id, {})
        with patch.object(ia, '_claude', return_value=dict(mensaje='Propongo una entrada suave.', necesita_aclaracion=False)) as claude, \
                patch.object(ia, '_generar') as generar:
            respuesta = ia.conversar(self.raiz, self.proyecto, self.proyecto.id, {}, pedido, lambda *a: None)
            self.assertIn('¿Qué estilo buscas?', claude.call_args.args[0])
            self.assertIn('letras doradas', claude.call_args.args[0])
            generar.assert_not_called()
        self.assertEqual(respuesta['resultados'], [])
        self.assertEqual(ia.historial(self.raiz), [])

    def test_pedir_aclaracion_impide_generar_codigo_aunque_se_pulse_empezar(self):
        pedido = ia.validar_peticion(self.raiz, dict(modo='crear', mensaje='Hazlo mejor', generar=True), self.proyecto.id, {})
        with patch.object(ia, '_claude', return_value=dict(mensaje='¿Qué quieres destacar?', necesita_aclaracion=True)), \
                patch.object(ia, '_generar') as generar, patch.object(ia, '_validar_resultado') as validar:
            resultado = ia.conversar(self.raiz, self.proyecto, self.proyecto.id, {}, pedido, lambda *a: None)
        generar.assert_not_called(); validar.assert_not_called()
        self.assertTrue(resultado['pendiente_aclaracion'])
        self.assertEqual(resultado['resultados'], [])

    def test_actividad_se_persiste_durante_la_generacion_y_no_se_duplica(self):
        pedido = ia.validar_peticion(self.raiz, dict(modo='crear', mensaje='Crear', generar=True), self.proyecto.id, {})
        def generar(proveedor, prompt, proyecto, referencias, avisar):
            for _ in range(3):
                avisar(.2, 'Generando código de prueba')
            charla = leer_json(str(ia.ruta(self.raiz, 'charlas', pedido['sesion'])))
            self.assertEqual(sum(e['texto'] == 'Generando código de prueba' for e in charla['eventos']), 1)
            self.assertTrue(any(e['autor'] == 'claude' for e in charla['eventos']))
            return dict(plantilla=self.fuente)
        with patch.object(ia, '_claude', return_value=dict(mensaje='Voy a modificar el título.')), \
                patch.object(ia, '_generar', side_effect=generar), \
                patch.object(ia, '_validar_resultado', return_value=copy.deepcopy(self.fuente)):
            resultado = ia.conversar(self.raiz, self.proyecto, self.proyecto.id, {}, pedido, lambda *a: None)
        charla = leer_json(str(ia.ruta(self.raiz, 'charlas', pedido['sesion'])))
        self.assertEqual(resultado['eventos'], charla['eventos'])
        self.assertTrue(any('Generación terminada' in e['texto'] for e in charla['eventos']))

    def test_crear_no_recibe_escenas_y_confirmar_es_idempotente(self):
        resultado, modelo = self.ejecutar(dict(modo='crear', escenas=['S001'], mensaje='Gráfica reutilizable', generar=True))
        self.assertNotIn('Escena 1', modelo.call_args.args[1])
        self.assertEqual(ia.historial(self.raiz), [])
        self.assertEqual(len(remotion.catalogo(self.raiz)), 12)
        a = ia.confirmar(self.raiz, resultado['sesion'], self.proyecto.id)
        self.assertEqual(a, ia.confirmar(self.raiz, resultado['sesion'], self.proyecto.id))
        self.assertEqual(len(remotion.catalogo(self.raiz)), 13)

    def test_editar_recibe_fuente_completa_y_guarda_otra_version(self):
        original, _ = self.ejecutar(dict(modo='escenas', escenas=['S001'], mensaje='Animar', generar=True))
        ficha = ia.historial(self.raiz)[0]
        modificada = dict(self.fuente, nombre='Revisión', props=dict(titulo='Nuevo'))
        revision, modelo = self.ejecutar(dict(modo='editar', categoria='historial', referencia=ficha['id'], mensaje='Cambiar título', generar=True),
            generador=lambda *a: dict(plantilla=modificada))
        prompt = modelo.call_args.args[1]
        self.assertIn(self.fuente['codigo'][:40], json.loads(prompt.split('\n')[1])['animacion_actual']['codigo'])
        guardada = ia.confirmar(self.raiz, revision['sesion'], self.proyecto.id)[0]
        self.assertNotEqual(guardada['id'], ficha['id'])
        self.assertEqual(guardada['anterior'], ficha['id'])
        self.assertEqual(guardada['escena_origen'], 'S001')
        self.assertEqual(ia.obtener(self.raiz, 'historial', ficha['id']), ficha)

    def test_error_de_codigo_conserva_borrador_y_corrige_sin_perder_historial(self):
        datos = dict(modo='crear', mensaje='Crear', generar=True)
        resultado, _ = self.ejecutar(datos)
        datos.update(sesion=resultado['sesion'], mensaje='Cambiar')
        fallida, modelo = self.ejecutar(datos, validacion=lambda *a: (_ for _ in ()).throw(ValueError('JSX incorrecto')))
        self.assertEqual(modelo.call_count, 3)
        self.assertEqual(fallida['resultados'], resultado['resultados'])
        self.assertEqual(len(fallida['errores']), 1)
        self.assertTrue(ia.confirmar(self.raiz, resultado['sesion'], self.proyecto.id))

    def test_cancelacion_no_se_reintenta(self):
        with self.assertRaises(Cancelado):
            self.ejecutar(dict(modo='crear', mensaje='Crear', generar=True), validacion=lambda *a: (_ for _ in ()).throw(Cancelado()))
        self.assertEqual(ia.historial(self.raiz), [])

    def test_contextos_sesion_y_validacion(self):
        resultado, _ = self.ejecutar(dict(modo='crear', mensaje='Hola'))
        for datos in (dict(modo='escenas', escenas=['S001'], mensaje='Hola', sesion=resultado['sesion']),
                      dict(modo='escenas', escenas=['S999'], mensaje='Hola'),
                      dict(modo='escenas', escenas=['S001'], mensaje='Hola', porcentaje=15),
                      dict(modo='editar', referencia='../fuera', mensaje='Hola')):
            with self.assertRaises(ValueError):
                ia.validar_peticion(self.raiz, datos, self.proyecto.id, self.plan)
        with self.assertRaises(ValueError):
            ia.confirmar(self.raiz, resultado['sesion'], 'otro-proyecto')

    def test_recursos_portables_y_miniatura_se_validan_antes_de_publicar(self):
        from PIL import Image
        imagen = Path(self.proyecto.ruta('imagen.png')); Image.new('RGB', (8, 8), 'red').save(imagen)
        fuente = dict(self.fuente, props=dict(imagen1='proyecto://imagen.png'))
        carpeta = Path(self.proyecto.ruta('remotion', 'compilados', 'f' * 64)); carpeta.mkdir(parents=True)
        def miniatura(pedido, avisar):
            Image.new('RGB', (16, 9), 'blue').save(carpeta / 'miniatura.png')
        with patch.object(remotion, 'compilar', return_value=dict(compilado='f' * 64)), patch.object(remotion, '_correr', side_effect=miniatura):
            validada = ia._validar_resultado(self.proyecto, fuente, lambda *a: None)
        imagen.unlink()
        self.assertTrue(validada['props']['imagen1'].startswith('data:image/png;base64,'))
        self.assertTrue(validada['miniatura'].startswith('data:image/png;base64,'))
        recursos = {}; reducida = ia._sin_binarios(validada, recursos)
        self.assertEqual(ia._restaurar(reducida, recursos)['props'], validada['props'])

    @unittest.skipUnless(REAL, 'usa --real para comprobar navegador y Remotion sin consumir IA')
    def test_editor_real_tres_modos_historial_y_aplicacion(self):
        import socket
        import subprocess
        import time
        import urllib.request
        import wave
        from PIL import Image, ImageChops
        from playwright.sync_api import sync_playwright
        from pasos._proyecto_animaciones import construir
        from pasos import medios
        proyecto, estado = construir(self.raiz)
        with wave.open(str(Path(proyecto.ruta_trabajo('voz')) / 'narracion.wav'), 'wb') as voz:
            voz.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            voz.writeframes(b'\0\0' * 16000 * 30)
        estado.completar('voz', {'pista': 'narracion.wav'})
        fuente = dict(self.fuente, nombre='Prueba IA', duracion=.3, ancho=640, alto=360,
            codigo="import React from 'react'; import {AbsoluteFill,useCurrentFrame} from 'remotion'; export default function T({titulo}) {const f=useCurrentFrame(); return <AbsoluteFill style={{color:'white',fontSize:40,opacity:Math.min(1,f/5)}}>{titulo}</AbsoluteFill>;}")
        editada = dict(fuente, nombre='Prueba IA editada', props=dict(titulo='Título editado'),
                       codigo=fuente['codigo'].replace("color:'white'", "color:'lime'"))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); puerto = sock.getsockname()[1]
        entorno = dict(os.environ, ESTUDIO_PROYECTOS=self.raiz, ESTUDIO_REMOTION_BROWSER=medios.edge())
        programa = ("import uvicorn, app; from pasos import animaciones_ia as ia; "
            "ia._claude=lambda p,*a: {'mensaje':'¿Qué estilo buscas?' if 'Este es solo un mensaje' in p and 'dorado' not in p else 'Concepto cinematográfico preparado',"
            "'necesita_aclaracion':'Este es solo un mensaje' in p and 'dorado' not in p,'conceptos':{}}; "
            f"ia._generar=lambda proveedor,p,*a: {{'plantilla':{editada!r} if p.startswith('Edita exactamente') else {fuente!r}}}; "
            f"uvicorn.run(app.app,host='127.0.0.1',port={puerto},log_level='error')")
        proceso = subprocess.Popen([sys.executable, '-c', programa], env=entorno, cwd=Path(__file__).resolve().parents[1])
        try:
            url = f'http://127.0.0.1:{puerto}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(url, timeout=1).close(); break
                except OSError:
                    time.sleep(.1)
            with sync_playwright() as pw:
                navegador = pw.chromium.launch(headless=True, executable_path=medios.edge())
                pagina = navegador.new_page(viewport=dict(width=1600, height=1000))
                errores = []; peticiones = []
                pagina.on('pageerror', lambda e: errores.append(str(e)))
                pagina.on('request', lambda r: peticiones.append(r.post_data_json) if r.url.endswith('/remotion/chat') and r.method == 'POST' else None)
                pagina.goto(url)
                pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                pagina.evaluate('''async pid => {
                    APP.light.video.pid=pid; APP.light.video.vista='previa';
                    PREVIA.ficha=await pedir(`${API.proyecto(pid)}/previsualizacion`); PREVIA.i=0;
                    document.querySelector('#inicio')?.remove();
                    document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                }''', proyecto.id)
                pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                activo = pagina.locator('.editor-global-escena[data-panel-activo="true"]')
                activo.get_by_role('tab', name='Animaciones con IA', exact=True).click()
                pagina.wait_for_selector('.remotion-crear')
                self.assertEqual(activo.locator('.remotion-tarjeta').count(), 13)
                self.assertFalse(activo.locator('.remotion-taller').is_visible())
                self.assertEqual(activo.locator('.remotion-catalogo > :last-child').inner_text().strip(), '+\nCrear plantilla')
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-biblioteca.png', full_page=True)
                activo.get_by_role('button', name='Crear plantilla', exact=False).click()
                self.assertTrue(activo.locator('.remotion-chat').is_visible())
                self.assertEqual(activo.get_by_role('button', name='Enviar a Claude', exact=True).count(), 0)
                self.assertTrue(activo.get_by_role('button', name='Enviar mensaje', exact=True).is_visible())
                self.assertTrue(activo.locator('.remotion-chat-reparto').is_visible())
                activo.get_by_label('Porcentaje de trabajo de ChatGPT').fill('0')
                self.assertEqual(activo.locator('.remotion-taller [role="tab"], .remotion-taller .remotion-plantilla-cab, .remotion-taller .remotion-editor-codigo').count(), 0)
                self.assertGreater(activo.locator('.remotion-chat').bounding_box()['height'], activo.locator('.remotion-taller').bounding_box()['height'] * .7)
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-solo-chat.png', full_page=True)
                self.assertFalse(activo.locator('.remotion-chat-escenas').is_visible())
                # El reloj del vídeo no selecciona otro panel ni reconstruye el chat.
                activo.get_by_label('Instrucción para Claude').fill('Borrador estable sin enviar')
                pagina.evaluate('''() => {
                    window.panelFijoIA = document.querySelector('.editor-global-escena[data-panel-activo="true"] .editor-global-panel');
                    window.chatFijoIA = document.querySelector('.editor-global-escena[data-panel-activo="true"] .remotion-chat');
                    window.tarjetasFijasIA = document.querySelector('.editor-global-escena[data-panel-activo="true"] .remotion-catalogo').innerHTML;
                    EDITOR_GLOBAL.audio(PREVIA.ficha.audio).playbackRate = 4;
                }''')
                mandos = pagina.locator('.editor-global-timeline > .anim-timeline-cab')
                mandos.get_by_role('button', name='Reproducir', exact=False).click()
                pagina.wait_for_function('PREVIA.i >= 1', timeout=15000)
                mandos.get_by_role('button', name='Pausar', exact=False).click()
                self.assertIn('S001', activo.get_attribute('aria-label'))
                self.assertTrue(activo.locator('.remotion-taller').is_visible())
                self.assertTrue(pagina.locator('.editor-global').evaluate("n => n.classList.contains('con-remotion')"))
                audio_destino = pagina.locator('.editor-global-columna').nth(4).locator('.anim-timeline-pista.audio').bounding_box()
                pagina.mouse.click(audio_destino['x'] + audio_destino['width'] / 2, audio_destino['y'] + 12)
                self.assertEqual(pagina.evaluate('PREVIA.i'), 4)
                self.assertEqual(activo.get_by_label('Instrucción para Claude').input_value(), 'Borrador estable sin enviar')
                self.assertTrue(pagina.evaluate('''() => panelFijoIA === document.querySelector('.editor-global-escena[data-panel-activo="true"] .editor-global-panel')
                    && chatFijoIA === document.querySelector('.editor-global-escena[data-panel-activo="true"] .remotion-chat')
                    && tarjetasFijasIA === document.querySelector('.editor-global-escena[data-panel-activo="true"] .remotion-catalogo').innerHTML'''))
                self.assertIn('S005', pagina.locator('.editor-global-escena[data-visual-activo="true"]').get_attribute('aria-label'))
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-panel-fijo.png', full_page=True)
                pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "remotion", 0)')
                activo.get_by_label('Instrucción para Claude').fill('Quiero un título reutilizable')
                activo.get_by_role('button', name='Enviar mensaje', exact=True).click()
                pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-chat-mensajes").textContent.includes("¿Qué estilo buscas?") && !document.querySelector(".remotion-chat.enviando")')
                self.assertFalse(peticiones[-1]['generar'])
                self.assertEqual(activo.locator('.remotion-chat-resultados article').count(), 0)
                sesion = peticiones[-1]['sesion']
                activo.get_by_label('Instrucción para Claude').fill('Cinematográfico y dorado')
                activo.get_by_label('Instrucción para Claude').press('Enter')
                pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-chat-mensajes").textContent.includes("Concepto cinematográfico preparado") && !document.querySelector(".remotion-chat.enviando")')
                self.assertFalse(peticiones[-1]['generar'])
                self.assertEqual(peticiones[-1]['sesion'], sesion)
                activo.get_by_role('button', name='Empezar a generar', exact=True).click()
                pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-chat-mensajes").textContent.includes("node motor.mjs")', timeout=120000)
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-actividad.png', full_page=True)
                confirmar = activo.get_by_role('button', name='Confirmar y guardar versión', exact=True)
                confirmar.wait_for(state='visible', timeout=120000)
                self.assertEqual(peticiones[-1]['modo'], 'crear')
                self.assertEqual(peticiones[-1]['porcentaje'], 0)
                self.assertTrue(peticiones[-1]['generar'])
                self.assertEqual(peticiones[-1]['sesion'], sesion)
                self.assertEqual(activo.locator('.remotion-chat-mensajes p').filter(has_text='Concepto cinematográfico preparado').count(), 2)
                confirmar.click()
                pagina.wait_for_function('document.querySelectorAll(".editor-global-escena:not([hidden]) .remotion-tarjeta").length === 14')
                activo.get_by_role('button', name='Animar escenas', exact=False).click()
                self.assertTrue(activo.locator('.remotion-chat-escenas').is_visible())
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-escenas.png', full_page=True)
                activo.get_by_role('button', name='Seleccionar todas', exact=True).click()
                self.assertEqual(activo.locator('.remotion-escenas-chips button').count(), 5)
                for id in ('S002', 'S003', 'S004', 'S005'):
                    activo.get_by_role('button', name=f'Quitar {id}', exact=True).click()
                activo.get_by_label('Porcentaje de trabajo de ChatGPT').fill('100')
                self.assertEqual(activo.locator('.remotion-chat-reparto output').inner_text(), '100%')
                activo.get_by_label('Instrucción para Claude').fill('Anima S001')
                activo.get_by_role('button', name='Empezar a generar', exact=True).click()
                pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("guardadas en el historial")', timeout=120000)
                self.assertEqual(peticiones[-1]['escenas'], ['S001'])
                self.assertEqual(peticiones[-1]['porcentaje'], 100)
                selector = activo.get_by_label('Biblioteca de animaciones')
                selector.select_option('historial')
                self.assertEqual(activo.locator('.remotion-tarjeta').count(), 1)
                self.assertEqual(activo.locator('.remotion-crear').count(), 0)
                tarjeta = activo.locator('.remotion-tarjeta-contenedor').first
                tarjeta.get_by_role('button', name='Más opciones', exact=False).click()
                tarjeta.get_by_role('menuitem', name='Editar', exact=True).click()
                self.assertIn('Editar animación', activo.locator('.remotion-chat h4').inner_text())
                self.assertTrue(activo.locator('.remotion-chat-reparto').is_visible())
                activo.get_by_label('Porcentaje de trabajo de ChatGPT').fill('100')
                activo.get_by_label('Instrucción para Claude').fill('Hazlo más lento')
                activo.get_by_role('button', name='Empezar a generar', exact=True).click()
                confirmar.wait_for(state='visible', timeout=120000)
                self.assertEqual(peticiones[-1]['categoria'], 'historial')
                self.assertEqual(peticiones[-1]['porcentaje'], 100)
                self.assertEqual(activo.locator('.remotion-taller [role="tab"]').count(), 0)
                # Cambiar el modo desde la tarjeta original conserva el borrador
                # sin id, tanto su código como sus props, antes de publicarlo.
                self.assertEqual(tarjeta.locator('.remotion-tarjeta').get_attribute('aria-pressed'), 'true')
                for modo, texto in [('sustituir', 'Sustituir contenido'), ('superponer', 'Superponer Animación')]:
                    tarjeta.get_by_role('button', name='Más opciones', exact=False).click()
                    tarjeta.get_by_role('menuitemradio', name=texto, exact=True).click()
                    tarjeta.get_by_role('button', name='Más opciones', exact=False).click()
                    self.assertEqual(tarjeta.get_by_role('menuitemradio', name=texto, exact=True).get_attribute('aria-checked'), 'true')
                    pagina.keyboard.press('Escape')
                    activo.get_by_role('button', name='Insertar en la línea de tiempo', exact=False).click()
                    popup = pagina.get_by_role('dialog')
                    self.assertEqual(popup.get_by_label('titulo', exact=True).input_value(), 'Título editado')
                    popup.get_by_role('button', name='Guardar', exact=True).click()
                    pagina.wait_for_function('document.querySelectorAll(".remotion .anim-timeline-bloque").length === 1', timeout=180000)
                    pagina.wait_for_function('!document.querySelector(".remotion-popup-props")')
                    capas = pagina.evaluate('EDITOR_GLOBAL.capasRemotion(PREVIA.ficha.escenas[0])')
                    self.assertEqual(capas[0]['opaca'], modo == 'sustituir')
                    with Image.open(proyecto.ruta(capas[0]['fotogramas'][-1])) as imagen:
                        self.assertGreater(ImageChops.subtract(imagen.getchannel('G'), imagen.getchannel('R')).getextrema()[1], 200)
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "remotion", .2)')
                    pagina.wait_for_function('document.querySelector(".editor-global-escena[data-visual-activo=true] .remotion-capas img")?.complete')
                    pagina.screenshot(path=f'/tmp/opencode/animacion-editada-{modo}.png', full_page=True)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Deshacer', exact=False).click()
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "remotion", 0)')
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 0)
                    self.assertTrue(confirmar.is_visible())
                confirmar.click()
                pagina.wait_for_function('document.querySelectorAll(".editor-global-escena:not([hidden]) .remotion-tarjeta").length === 2')
                historicas = ia.historial(self.raiz)
                self.assertNotEqual(historicas[0]['id'], historicas[1]['id'])
                pagina.screenshot(path='/tmp/opencode/animaciones-ia-historial.png', full_page=True)
                activo.get_by_role('button', name='Configurar y aplicar', exact=True).click()
                popup = pagina.get_by_role('dialog')
                popup.wait_for(state='visible')
                popup.get_by_role('button', name='Guardar', exact=True).click()
                pagina.wait_for_function('document.querySelectorAll(".remotion .anim-timeline-bloque").length === 1', timeout=180000)
                pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                # Insertar desde el panel fijado usa el cursor global, no su tiempo antiguo.
                pista = pagina.locator('.editor-global-columna').nth(4).locator('.anim-timeline-pista.audio').bounding_box()
                pagina.mouse.click(pista['x'] + pista['width'] / 2, pista['y'] + 12)
                cursor = pagina.evaluate('PREVIA.t')
                activo.locator('.remotion-tarjeta').first.click()
                activo.get_by_role('button', name='Insertar en la línea de tiempo', exact=False).click()
                popup.wait_for(state='visible')
                popup.get_by_role('button', name='Guardar', exact=True).click()
                pagina.wait_for_function('document.querySelectorAll(".remotion .anim-timeline-bloque").length === 2', timeout=180000)
                pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                ficha = pagina.evaluate('async pid => await pedir(`${API.proyecto(pid)}/escenas/S001/editor`)', proyecto.id)
                self.assertAlmostEqual(ficha['remotion'][-1]['origen'] + ficha['remotion'][-1]['inicio'], cursor, places=3)
                self.assertEqual(errores, [])
                navegador.close()
        finally:
            proceso.terminate(); proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
