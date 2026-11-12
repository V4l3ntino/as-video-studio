"""Remotion adicional: contratos, versiones, composición y editor real opcional.

    python pasos/prueba_remotion.py [--real]
"""
import copy
import io
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_remotion_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_REMOTION'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import Proyecto, escribir_json, leer_json  # noqa: E402
from pasos import animaciones, editor_escena, remotion, p8_render  # noqa: E402
from pasos._proyecto_animaciones import construir  # noqa: E402


class Contratos(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'requiere Node para comprobar la cancelación del proceso')
    def test_cancelacion_cierra_el_proceso_sin_publicar_resultado(self):
        from nucleo.trabajos import Cancelado
        with tempfile.TemporaryDirectory() as tmp:
            motor = Path(tmp) / 'motor'; motor.mkdir()
            (motor / 'motor.mjs').write_text('setInterval(() => {}, 1000);', encoding='utf-8')
            procesos = []
            popen = subprocess.Popen
            def lanzar(*args, **kwargs):
                p = popen(*args, **kwargs); procesos.append(p); return p
            def cancelar(*args):
                raise Cancelado('parar')
            with patch.object(remotion, 'MOTOR', motor), patch.object(remotion, 'disponible', return_value=True), patch.object(remotion.subprocess, 'Popen', side_effect=lanzar):
                with self.assertRaises(Cancelado):
                    remotion._correr(dict(accion='compilar', carpeta=str(Path(tmp) / 'salida')), cancelar)
            self.assertIsNotNone(procesos[0].poll())
            self.assertFalse((Path(tmp) / 'salida' / 'listo.json').exists())

    def test_version_inmutable_y_duplicacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = Proyecto.crear(tmp, 'Original')
            p = remotion.catalogo(tmp)[0]
            a = remotion.guardar(tmp, p)
            p['props']['titulo'] = 'Otro título'
            b = remotion.guardar(tmp, p)
            self.assertNotEqual(a['id'], b['id'])
            fuente = remotion.validar_plantilla(a)
            clave = remotion.huella(fuente)
            escribir_json(proyecto.ruta('remotion', 'plantillas', clave + '.json'), fuente)
            copia = proyecto.duplicar(tmp, 'Copia')
            self.assertEqual(remotion.resolver(copia, clave)['props']['titulo'], 'La Cordillera')
            with self.assertRaises(ValueError):
                remotion.resolver(copia, '../fuera')

    def test_validacion_y_compatibilidad(self):
        escena = dict(id='S001', narracion='Una escena.', t_in=0, t_out=6)
        self.assertEqual(editor_escena.validar({}, escena, [1920, 1080]), {})
        self.assertEqual(remotion.bloques_de({}, escena), [])
        bloque = dict(plantilla='a' * 64, nombre='Título', props={}, inicio=0, fin=5)
        ficha = dict(ancla=animaciones.ancla_de(escena), bloques=[bloque])
        self.assertIn('remotion', editor_escena.validar({'remotion': ficha}, escena, [1920, 1080]))
        for cambio in ({'fin': 7}, {'inicio': float('nan')}, {'fin': True}, {'props': []}):
            mala = copy.deepcopy(ficha); mala['bloques'][0].update(cambio)
            with self.assertRaises(ValueError):
                remotion.validar_edicion(mala, escena)
        mala = dict(ficha, ancla='otra narración')
        with self.assertRaises(ValueError):
            remotion.validar_edicion(mala, escena)

    def test_eliminar_biblioteca_conserva_instantaneas(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'ESTUDIO_REMOTION': str(Path(tmp) / 'biblioteca')}):
            proyecto = Proyecto.crear(tmp, 'Con plantilla')
            ejemplo = remotion.catalogo(tmp)[0]
            propia = remotion.guardar(tmp, ejemplo)
            fuente = remotion.validar_plantilla(propia)
            referencia = remotion.huella(fuente)
            escribir_json(proyecto.ruta('remotion', 'plantillas', referencia + '.json'), fuente)
            remotion.eliminar(tmp, propia['id'])
            self.assertNotIn(propia['id'], [p['id'] for p in remotion.catalogo(tmp)])
            self.assertEqual(remotion.resolver(proyecto, referencia), fuente)
            remotion.eliminar(tmp, ejemplo['id'])
            self.assertEqual(len(remotion.catalogo(tmp)), 11)
            self.assertNotIn(ejemplo['id'], [p['id'] for p in remotion.catalogo(tmp)])
            for identificador in ('../fuera', 'ejemplo-inventado', 'a.json', None):
                with self.assertRaises(ValueError):
                    remotion.eliminar(tmp, identificador)
            for plantilla in remotion.catalogo(tmp):
                remotion.eliminar(tmp, plantilla['id'])
            self.assertEqual(remotion.catalogo(tmp), [])
            remotion.guardar(tmp, ejemplo)
            self.assertEqual(len(remotion.catalogo(tmp)), 1)

    def test_capas_reloj_alpha_y_camino_actual(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / 'capa.png'
            Image.new('RGBA', (4, 4), (255, 0, 0, 128)).save(ruta)
            base = io.BytesIO(); Image.new('RGB', (4, 4), 'blue').save(base, format='PNG')
            png = base.getvalue()
            capas = [dict(inicio=1, fin=2, fps=30, fotogramas=[str(ruta)])]
            self.assertEqual(remotion.superponer(png, capas, .99), png)
            self.assertEqual(remotion.superponer(png, capas, 2), png)
            resultado = Image.open(io.BytesIO(remotion.superponer(png, capas, 1)))
            self.assertEqual(resultado.getpixel((0, 0)), (128, 0, 127, 255))
            class Navegador:
                def capturar(self, destino=None):
                    return png
            self.assertEqual(p8_render._capturar_con_avatar({'fps': 30}, Navegador(), 0), png)
            mezclado = p8_render._capturar_con_avatar({'fps': 30, 'remotion': capas}, Navegador(), 30)
            self.assertEqual(Image.open(io.BytesIO(mezclado)).getpixel((0, 0)), (128, 0, 127, 255))

    def test_timeline_cruza_escenas_sin_reiniciar_y_sella_destinos(self):
        escenas = [dict(id=f'S00{i + 1}', narracion=f'Frase {i}.', t_in=i * 2, t_out=(i + 1) * 2, timeline_fin=6) for i in range(3)]
        bloque = dict(plantilla='a' * 64, nombre='Libre', props={}, inicio=1, fin=5, origen=0)
        ficha = dict(ancla=animaciones.ancla_de(escenas[0]), bloques=[bloque])
        remotion.validar_edicion(ficha, escenas[0])
        params = {'unidades': {'escena:S001': {'remotion': ficha}}}
        proyectados = [remotion.bloques_de(params, e)[0] for e in escenas]
        self.assertEqual([(b['inicio'], b['fin']) for b in proyectados], [(1, 5), (-1, 3), (-3, 1)])
        with tempfile.TemporaryDirectory() as tmp:
            from PIL import Image
            proyecto = Proyecto.crear(tmp, 'Reloj libre')
            plantilla = remotion.catalogo(tmp)[0]
            with patch.object(remotion, 'resolver', side_effect=lambda *_: copy.deepcopy(plantilla)):
                carpetas = [remotion.pedido_de(proyecto, b, [1280, 720], 30)[1] for b in proyectados]
                self.assertEqual(len(set(carpetas)), 1)
                libre = dict(proyectados[0], modo='sustituir')
                remotion.validar_edicion(dict(ficha, bloques=[libre]), escenas[0])
                antigua = dict(libre); del antigua['origen']
                self.assertNotEqual(remotion.pedido_de(proyecto, libre, [1280, 720], 30)[1],
                                    remotion.pedido_de(proyecto, antigua, [1280, 720], 30)[1])
            marcos = []
            for i in range(4):
                ruta = Path(tmp) / f'{i}.png'
                Image.new('RGBA', (2, 2), (i * 60, 0, 0, 255)).save(ruta)
                marcos.append(str(ruta))
            base = io.BytesIO(); Image.new('RGB', (2, 2)).save(base, format='PNG')
            for escena, b in zip(escenas, proyectados):
                capa = dict(b, fps=1, fotogramas=marcos)
                t = max(0, b['inicio'])
                pixel = Image.open(io.BytesIO(remotion.superponer(base.getvalue(), [capa], t))).getpixel((0, 0))
                self.assertEqual(pixel[0], int(t - b['inicio']) * 60)
        self.assertTrue(all(remotion.dependencias(params, escenas).values()))
        params['unidades']['escena:S001']['remotion']['bloques'] = []
        self.assertFalse(any(remotion.dependencias(params, escenas).values()))
        # Puede desplazarse antes de la escena desde la que se insertó.
        bloque.update(origen=2, inicio=-2, fin=1)
        remotion.validar_edicion(dict(ancla=animaciones.ancla_de(escenas[1]), bloques=[bloque]), escenas[1])
        for cambio in ({'inicio': -3}, {'fin': 5}, {'origen': float('nan')}):
            with self.assertRaises(ValueError):
                remotion.validar_edicion(dict(ancla=animaciones.ancla_de(escenas[1]), bloques=[dict(bloque, **cambio)]), escenas[1])

    def test_sustitucion_exclusiva_y_recursos_portables(self):
        escena = dict(id='S001', narracion='Una escena.', t_in=0, t_out=6)
        b = dict(plantilla='a' * 64, nombre='Completa', props={}, inicio=0, fin=6, modo='sustituir')
        ficha = dict(ancla=animaciones.ancla_de(escena), bloques=[b])
        self.assertEqual(remotion.validar_edicion(ficha, escena)['bloques'][0]['modo'], 'sustituir')
        for bloques in ([b, b], [dict(b, inicio=1)], [dict(b, modo='otro')], [dict(b, fin='6')]):
            with self.assertRaises(ValueError):
                remotion.validar_edicion(dict(ficha, bloques=bloques), escena)
        with tempfile.TemporaryDirectory() as tmp:
            from PIL import Image
            proyecto = Proyecto.crear(tmp, 'Recursos')
            imagen = Path(proyecto.ruta('imagen.png'))
            Image.new('RGB', (4, 4), 'red').save(imagen)
            props = {'imagenes': ['proyecto://imagen.png']}
            a = remotion.props_recursos(proyecto, props)
            self.assertTrue(a['imagenes'][0].startswith('data:image/png;base64,'))
            Image.new('RGB', (4, 4), 'blue').save(imagen)
            self.assertNotEqual(a, remotion.props_recursos(proyecto, props))
            self.assertEqual(props['imagenes'][0], 'proyecto://imagen.png')
            for ref in ('proyecto://../fuera.png', 'proyecto://estado.json', 'proyecto://falta.png'):
                with self.assertRaises(ValueError):
                    remotion.props_recursos(proyecto, {'imagen': ref})

    def test_galeria_recibe_tres_imagenes(self):
        galeria = next(p for p in remotion.catalogo(_DATOS.name) if p['id'] == 'ejemplo-galeria')
        self.assertEqual(galeria['props'], dict(imagen1='', imagen2='', imagen3=''))

    @unittest.skipUnless(REAL, 'usa --real para compilar, previsualizar y renderizar en Chromium')
    def test_taller_y_render_local(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix='remotion_real_') as tmp:
            proyecto, estado = construir(str(Path(tmp) / 'proyectos'))
            antes = Path(proyecto.ruta('estado.json')).read_bytes()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); puerto = sock.getsockname()[1]
            proceso = subprocess.Popen([sys.executable, str(RAIZ / 'app.py'), '--puerto', str(puerto),
                '--proyectos', str(Path(tmp) / 'proyectos')], cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                url = f'http://127.0.0.1:{puerto}'
                for _ in range(100):
                    try:
                        urllib.request.urlopen(url, timeout=1).close(); break
                    except OSError:
                        time.sleep(.1)
                with sync_playwright() as pw:
                    navegador = pw.chromium.launch(headless=True, executable_path=os.environ.get('ESTUDIO_EDGE') or None)
                    pagina = navegador.new_page(viewport={'width': 1920, 'height': 1080})
                    errores = []
                    preparaciones = []
                    pagina.on('pageerror', lambda e: errores.append(str(e)))
                    pagina.on('request', lambda r: preparaciones.append(r.url) if r.url.endswith('/remotion/preparar') else None)
                    pagina.goto(url)
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate('''async pid => {
                        APP.light.video.pid = pid; APP.light.video.vista = 'previa';
                        PREVIA.ficha = await pedir(`${API.proyecto(pid)}/previsualizacion`); PREVIA.i = 0;
                        document.querySelector('#inicio')?.remove();
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    activo = pagina.locator('.editor-global-escena:not([hidden])')
                    activo.get_by_role('tab', name='Plantillas Remotion', exact=True).click()
                    pagina.wait_for_selector('.remotion-tarjeta')
                    self.assertEqual(activo.locator('.remotion-tarjeta').count(), 12)
                    self.assertEqual(antes, Path(proyecto.ruta('estado.json')).read_bytes())
                    self.assertFalse(activo.locator('.remotion-taller').is_visible())
                    activo.get_by_role('button', name='Gráfico Circular', exact=True).click()
                    self.assertFalse(activo.locator('.remotion-taller').is_visible())
                    activo.get_by_role('button', name='Título Cinematográfico', exact=True).click()
                    pagina.evaluate('document.querySelector("#panel").scrollTop = 0')
                    pagina.screenshot(path='/tmp/opencode/remotion-biblioteca.png', full_page=True)
                    desplegar = activo.get_by_role('button', name='Taller de Remotion', exact=False)
                    self.assertEqual(desplegar.get_attribute('aria-expanded'), 'false')
                    desplegar.click()
                    self.assertTrue(activo.locator('.remotion-taller').is_visible())
                    self.assertEqual(desplegar.get_attribute('aria-expanded'), 'true')
                    # El ejemplo incluido también compila: la biblioteca no es una maqueta.
                    activo.get_by_role('button', name='Compilar', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Compilación lista")', timeout=120000)
                    activo.locator('.remotion-player').content_frame.get_by_text('La Cordillera', exact=True).wait_for()
                    activo.locator('.remotion-player').evaluate("n => n.contentWindow.postMessage({tipo:'asvs-remotion',frame:60}, '*')")
                    pagina.wait_for_timeout(200)
                    pagina.evaluate('document.querySelector("#panel").scrollTop = 0')
                    pagina.screenshot(path='/tmp/opencode/remotion-ejemplo.png', full_page=True)
                    pagina.set_viewport_size({'width': 1000, 'height': 900})
                    self.assertGreaterEqual(activo.locator('.remotion-taller').bounding_box()['y'], activo.locator('.editor-global-visual').bounding_box()['y'])
                    pagina.set_viewport_size({'width': 390, 'height': 844})
                    self.assertLessEqual(activo.locator('.remotion-taller').bounding_box()['width'], 390)
                    pagina.evaluate('document.querySelector("#panel").scrollTop = 0')
                    pagina.screenshot(path='/tmp/opencode/remotion-movil.png', full_page=True)
                    pagina.set_viewport_size({'width': 1920, 'height': 1080})
                    # Una plantilla breve: verifica JSX, hooks, props y transparencia reales.
                    activo.get_by_label('Código React TSX').fill("import React from 'react';\nimport {AbsoluteFill, useCurrentFrame} from 'remotion';\nexport default function T({titulo}) { const f = useCurrentFrame(); return <AbsoluteFill style={{color:'white',fontSize:80,backgroundColor:'rgba(255,0,0,0.3)'}}>{titulo} {f}</AbsoluteFill>; }")
                    activo.locator('.remotion-prop').filter(has=pagina.locator('span', has_text='duración (s)')).locator('input').fill('0.2')
                    activo.get_by_role('button', name='Compilar', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Compilación lista")', timeout=120000)
                    frame = activo.locator('.remotion-player').content_frame
                    frame.get_by_text('La Cordillera', exact=False).wait_for(timeout=30000)
                    pagina.screenshot(path='/tmp/opencode/remotion-taller.png', full_page=True)
                    desplegar.click()
                    pagina.evaluate('''() => {
                        window.progresoBiblioteca = [];
                        const n = document.querySelector('.editor-global-escena:not([hidden]) .remotion-estado-biblioteca');
                        new MutationObserver(() => progresoBiblioteca.push(n.textContent)).observe(n, {childList:true, subtree:true});
                    }''')
                    activo.get_by_role('button', name='Insertar en la línea de tiempo', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=180000)
                    self.assertTrue(pagina.evaluate("progresoBiblioteca.some(t => /Renderizando Remotion.*[0-9]+ %/.test(t))"))
                    self.assertTrue(activo.locator('.remotion-estado-biblioteca').is_visible())
                    self.assertEqual(activo.locator('.remotion-bloque-edicion').count(), 0)
                    self.assertEqual(activo.get_by_text('Bloques libres en el timeline', exact=True).count(), 0)
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    # Contraer no pierde el trabajo ni cambia el borrador.
                    self.assertFalse(activo.locator('.remotion-taller').is_visible())
                    self.assertFalse(pagina.locator('.editor-global').evaluate("n => n.classList.contains('con-remotion')"))
                    pagina.screenshot(path='/tmp/opencode/remotion-taller-contraido.png', full_page=True)
                    pagina.locator('.remotion .anim-timeline-bloque').first.click()
                    self.assertFalse(activo.locator('.remotion-taller').is_visible())
                    desplegar.click()
                    self.assertTrue(activo.locator('.remotion-taller').is_visible())
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    # Seleccionar un bloque recupera su código y permite sustituirlo.
                    pagina.locator('.remotion .anim-timeline-bloque').first.click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-taller").dataset.plantillaEditada')
                    titulo = activo.locator('.remotion-prop').filter(has=pagina.get_by_text('titulo', exact=True)).locator('input')
                    titulo.fill('Título corregido'); titulo.press('Tab')
                    activo.get_by_role('button', name='Aplicar al timeline', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=120000)
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    datos = leer_json(proyecto.ruta('estado.json'))
                    bloques = datos['pasos']['render']['params']['unidades']['escena:S001']['remotion']['bloques']
                    self.assertEqual(bloques[0]['props']['titulo'], 'Título corregido')
                    capas = remotion.capas_guardadas(proyecto, bloques, [1280, 720], 30)
                    # El fixture tiene resolución propia; se comprueba el contrato publicado.
                    self.assertTrue(list(Path(proyecto.ruta('remotion', 'renders')).glob('*/listo.json')))
                    ficha = pagina.evaluate('''async pid => await pedir(`${API.proyecto(pid)}/escenas/S001/editor`)''', proyecto.id)
                    self.assertEqual(len(ficha['remotion']), 1)
                    self.assertEqual(len(ficha['remotion_capas'][0]['fotogramas']), 6)
                    self.assertEqual(len(capas), 1)
                    from PIL import Image
                    png = proyecto.ruta(ficha['remotion_capas'][0]['fotogramas'][0])
                    with Image.open(png) as im:
                        self.assertEqual(im.mode, 'RGBA')
                        self.assertLess(im.getpixel((1279, 719))[3], 255)
                    # El montaje real mantiene las capas y su reloj al codificar.
                    hyper = proyecto.ruta('pasos', 'assets', 'v1', 'escenas', 'S001.png')
                    tarea = dict(id='S001', escena={'t_in': 0, 't_out': .2}, fps=30, frames=6,
                        resolucion=[1280, 720], hyper=hyper, capa='', capa_fija='',
                        mov={'ventana_ini': [0, 0, 1, 1], 'ventana_fin': [0, 0, 1, 1]},
                        remotion=[dict(capas[0], fotogramas=[proyecto.ruta(p) for p in capas[0]['fotogramas']])],
                        carpeta=str(Path(tmp) / 'frames'), clip=str(Path(tmp) / 'escena.mp4'),
                        ultimo=str(Path(tmp) / 'ultimo.png'), conservar_frames=False, calidad='alta', codec='libx264')
                    renderer = p8_render.Navegador(1280, 720)
                    try:
                        p8_render.renderizar_plano(tarea, renderer)
                    finally:
                        renderer.cerrar()
                    self.assertGreater(Path(tarea['clip']).stat().st_size, 100)
                    with Image.open(tarea['ultimo']) as im:
                        self.assertGreater(im.getpixel((1279, 719))[0], 70)
                    limite = pagina.evaluate('PREVIA.ficha.escenas[0].t_out')
                    bloque_dom = pagina.locator('.remotion .anim-timeline-bloque').first
                    pista = pagina.locator('.editor-global-columna').first.locator('.anim-timeline-pistas')
                    def intervalo():
                        return bloque_dom.evaluate('''(n, total) => ({inicio:parseFloat(n.style.left)*total/100,
                            duracion:parseFloat(n.style.width)*total/100})''', limite)
                    def arrastrar(inicio=None, fin=None, borrar=False, cancelar=False):
                        p = intervalo()
                        objetivo = bloque_dom.locator('[data-extremo="fin"]') if fin is not None else bloque_dom
                        caja = objetivo.bounding_box()
                        x, y = caja['x'] + caja['width'] / 2, caja['y'] + caja['height'] / 2
                        if borrar:
                            basura = pagina.get_by_role('img', name='Papelera de bloques', exact=True).bounding_box()
                            destino = (basura['x'] + basura['width'] / 2, basura['y'] + basura['height'] / 2)
                        else:
                            delta = fin - p['inicio'] - p['duracion'] if fin is not None else inicio - p['inicio']
                            destino = (x + delta / limite * pista.evaluate('n => n.clientWidth'), y)
                        pagina.mouse.move(x, y); pagina.mouse.down()
                        pagina.mouse.move(*destino, steps=10)
                        if borrar:
                            pagina.screenshot(path='/tmp/opencode/remotion-papelera.png', full_page=True)
                            self.assertTrue(pagina.locator('.timeline-papelera').evaluate("n => n.classList.contains('encima')"))
                        if cancelar:
                            pagina.evaluate('''() => {
                                const n = document.querySelector('.remotion .anim-timeline-bloque');
                                n.dispatchEvent(new PointerEvent('pointercancel', {pointerId:1, bubbles:true}));
                            }''')
                        pagina.mouse.up()
                    # Redimensionar prepara automáticamente los nuevos fotogramas.
                    pagina.get_by_label('Zoom del timeline', exact=True).evaluate("n => {n.value = 6; n.dispatchEvent(new Event('input'));}")
                    arrastrar(fin=2)
                    pagina.wait_for_function('!document.querySelector(".remotion-trabajando")', timeout=180000)
                    self.assertAlmostEqual(intervalo()['duracion'], 2, places=4)
                    pagina.wait_for_function("async pid => (await CACHE_EDITOR.leer(pid, 'S001'))?.remotion_previa?.capas[0]?.fotogramas?.length === 60", arg=proyecto.id)
                    pagina.get_by_label('Zoom del timeline', exact=True).evaluate("n => {n.value = 1; n.dispatchEvent(new Event('input'));}")
                    solicitudes = len(preparaciones)
                    # Desplazar conserva el recurso y su reloj sin trabajo nuevo.
                    arrastrar(inicio=limite + 1)
                    self.assertGreater(intervalo()['inicio'], limite)
                    self.assertAlmostEqual(intervalo()['duracion'], 2, places=4)
                    inicio_movido = intervalo()['inicio']
                    pagina.evaluate("t => EDITOR_GLOBAL.seleccionar('S002', 'remotion', t)", inicio_movido - limite + .1)
                    self.assertRegex(activo.locator('.remotion-capas img').get_attribute('src'), r'/f0*3\.png$')
                    pagina.evaluate("EDITOR_GLOBAL.seleccionar('S001', 'remotion', 0, 0)")
                    arrastrar(inicio=limite - .1)
                    pagina.evaluate("EDITOR_GLOBAL.seleccionar('S002', 'remotion', 0)")
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-capas img")')
                    continuada = activo.locator('.remotion-capas img').get_attribute('src')
                    self.assertRegex(continuada, r'/f0*3\.png$')
                    self.assertEqual(len(preparaciones), solicitudes)
                    pagina.screenshot(path='/tmp/opencode/remotion-cruza-escenas.png', full_page=True)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    datos = leer_json(proyecto.ruta('estado.json'))['pasos']['render']['params']
                    self.assertTrue(datos['unidades']['escena:S002']['remotion_timeline'])
                    pagina.evaluate("EDITOR_GLOBAL.seleccionar('S001', 'remotion', 0, 0)")
                    arrastrar(inicio=0)
                    arrastrar(fin=.2)
                    pagina.wait_for_function('!document.querySelector(".remotion-trabajando")', timeout=180000)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    # Escena completa: render separado, MP4 cacheado y fondo del editor.
                    datos = leer_json(proyecto.ruta('estado.json'))['pasos']['render']['params']
                    self.assertEqual(datos['unidades']['escena:S002']['remotion_timeline'], [])
                    activo.get_by_role('button', name='Sustituir contenido visual', exact=False).click()
                    salida = activo.locator('.remotion-salida')
                    self.assertTrue(salida.is_visible())
                    salida.get_by_role('spinbutton', name='Duración (s)', exact=True).fill('0.2')
                    salida.get_by_role('button', name='Renderizar vídeo (MP4)', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("MP4 listo")', timeout=180000)
                    self.assertFalse(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    pagina.screenshot(path='/tmp/opencode/remotion-escena-completa.png', full_page=True)
                    activo.get_by_role('button', name='Aplicar al timeline', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=180000)
                    self.assertEqual(pagina.locator('.remotion-completa').count(), 1)
                    pagina.evaluate("EDITOR_GLOBAL.seleccionar('S001', undefined, 0.1)")
                    self.assertTrue(activo.locator('.remotion-capas img.remotion-opaca').is_visible())
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    ficha = pagina.evaluate('''async pid => await pedir(`${API.proyecto(pid)}/escenas/S001/editor`)''', proyecto.id)
                    completa = ficha['remotion'][0]
                    self.assertEqual(completa['modo'], 'sustituir')
                    self.assertIn('origen', completa)
                    # Las sustituciones históricas de escena mantienen su contrato MP4.
                    completa = dict(completa, inicio=0, fin=limite); del completa['origen']
                    capa_completa = remotion.preparar(proyecto, completa, [1280, 720], 30)
                    mp4 = Path(capa_completa['clip']); sello = mp4.stat().st_mtime_ns
                    self.assertEqual(remotion.preparar(proyecto, completa, [1280, 720], 30), capa_completa)
                    self.assertEqual(mp4.stat().st_mtime_ns, sello)
                    escena = pagina.evaluate('''async pid => (await pedir(`${API.proyecto(pid)}/previsualizacion`)).escenas[0]''', proyecto.id)
                    fuente = p8_render._fuente_para_enlace(escena, {}, tmp, {}, proyecto, True,
                        params={'unidades': {'escena:S001': {'remotion': {'ancla': ficha['animacion']['ancla'], 'bloques': [completa]}}}},
                        salida=(1280, 720))
                    self.assertEqual(fuente['video'], str(mp4))
                    self.assertTrue(Path(fuente['hyper']).is_file())
                    self.assertEqual(fuente['mov']['ventana_ini'], [0, 0, 1, 1])
                    # P8 decodifica ese MP4, mantiene su último cuadro y añade una capa independiente.
                    tarea.update(video=str(mp4), hyper=fuente['hyper'], mov=fuente['mov'], remotion=[], frames=12, escena={'t_in': 0, 't_out': .4},
                                 capa_fija='<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="30" height="30" fill="lime"/></svg>')
                    renderer = p8_render.Navegador(1280, 720)
                    try:
                        p8_render.renderizar_plano(tarea, renderer)
                    finally:
                        renderer.cerrar()
                    with Image.open(tarea['ultimo']) as im:
                        self.assertGreater(im.getpixel((10, 10))[1], 200)
                        self.assertGreater(im.getpixel((1279, 719))[0], 70)
                        self.assertLess(im.getpixel((1279, 719))[2], 10)
                    # Eliminar la sustitución recupera la imagen, sin borrar el MP4 ni el original.
                    arrastrar(borrar=True, cancelar=True)
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    self.assertFalse(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    arrastrar(borrar=True)
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 0)
                    self.assertFalse(pagina.locator('.timeline-papelera').evaluate("n => n.classList.contains('encima')"))
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Deshacer', exact=False).click()
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    arrastrar(borrar=True)
                    self.assertEqual(activo.locator('.escena-editor-previa > video.previa-clip').count(), 0)
                    self.assertTrue(mp4.is_file()); self.assertTrue(Path(hyper).is_file())
                    # La galería acepta imágenes del proyecto y una subida propia, no textos.
                    activo.get_by_role('button', name='Galería Animada', exact=True).click()
                    activo.get_by_role('tab', name='Props', exact=False).click()
                    self.assertEqual(activo.locator('.remotion-imagen-prop').count(), 3)
                    self.assertEqual(activo.locator('.remotion-prop').filter(has=pagina.get_by_text('titulo', exact=True)).count(), 0)
                    activo.get_by_role('combobox', name='Foto 1', exact=True).select_option(index=1)
                    activo.get_by_role('combobox', name='Foto 2', exact=True).select_option(index=2)
                    foto = io.BytesIO(); Image.new('RGB', (200, 200), '#00ff00').save(foto, format='PNG')
                    activo.get_by_label('Subir foto 3', exact=True).set_input_files({'name': 'foto.png', 'mimeType': 'image/png', 'buffer': foto.getvalue()})
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Foto 3 preparada")')
                    activo.locator('.remotion-prop').filter(has=pagina.locator('span', has_text='duración (s)')).locator('input').fill('0.2')
                    activo.get_by_role('button', name='Compilar', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Compilación lista")', timeout=120000)
                    frame = activo.locator('.remotion-player').content_frame
                    frame.locator('img').nth(2).wait_for()
                    self.assertEqual(frame.locator('img').count(), 3)
                    activo.locator('.remotion-player').evaluate("n => n.contentWindow.postMessage({tipo:'asvs-remotion',frame:3}, '*')")
                    pagina.screenshot(path='/tmp/opencode/remotion-galeria-fotos.png', full_page=True)
                    activo.get_by_role('button', name='Aplicar al timeline', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=180000)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    ficha = pagina.evaluate('''async pid => await pedir(`${API.proyecto(pid)}/escenas/S001/editor`)''', proyecto.id)
                    self.assertTrue(ficha['remotion'][0]['props']['imagen3'].startswith('proyecto://medios_usuario/'))
                    with Image.open(proyecto.ruta(ficha['remotion_capas'][0]['fotogramas'][3])) as im:
                        self.assertGreater(im.getpixel((867, 360))[1], 200)
                    # Los tres puntos no seleccionan la tarjeta y eliminan solo la biblioteca.
                    activo.get_by_label('Nombre de la plantilla', exact=True).fill('Galería para borrar')
                    activo.get_by_role('button', name='Guardar plantilla', exact=False).click()
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-escena:not([hidden]) .remotion-tarjeta").length === 13')
                    tarjeta = activo.locator('.remotion-tarjeta-contenedor').filter(has=pagina.get_by_role('button', name='Galería para borrar', exact=True))
                    seleccionada = activo.locator('.remotion-tarjeta[aria-pressed="true"]').inner_text()
                    puntos = tarjeta.get_by_role('button', name='Más opciones de Galería para borrar', exact=True)
                    puntos.click()
                    self.assertEqual(activo.locator('.remotion-tarjeta[aria-pressed="true"]').inner_text(), seleccionada)
                    self.assertTrue(tarjeta.get_by_role('menuitem', name='Eliminar plantilla', exact=True).is_visible())
                    self.assertEqual(tarjeta.get_by_role('menuitemradio', name='Superponer Animación', exact=True).get_attribute('aria-checked'), 'true')
                    self.assertEqual(tarjeta.get_by_role('menuitemradio', name='Sustituir contenido', exact=True).get_attribute('aria-checked'), 'false')
                    pagina.keyboard.press('Escape')
                    self.assertEqual(puntos.get_attribute('aria-expanded'), 'false')
                    # El modo del menú se usa al insertar, también con el taller contraído.
                    desplegar.click()
                    for modo, texto in [('sustituir', 'Sustituir contenido'), ('superponer', 'Superponer Animación')]:
                        puntos.click()
                        tarjeta.get_by_role('menuitemradio', name=texto, exact=True).click()
                        self.assertFalse(activo.locator('.remotion-taller').is_visible())
                        self.assertEqual(activo.locator('.remotion-modo').nth(1 if modo == 'sustituir' else 0).get_attribute('aria-pressed'), 'true')
                        puntos.click()
                        self.assertEqual(tarjeta.get_by_role('menuitemradio', name=texto, exact=True).get_attribute('aria-checked'), 'true')
                        pagina.keyboard.press('Escape')
                        with pagina.expect_request(lambda r: r.url.endswith('/remotion/preparar')) as solicitud:
                            activo.get_by_role('button', name='Insertar en la línea de tiempo', exact=False).click()
                        pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=180000)
                        self.assertEqual(solicitud.value.post_data_json['bloques'][-1]['modo'], modo)
                        self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 2)
                        self.assertEqual(activo.locator('.remotion-capas img.remotion-opaca').count(), 1 if modo == 'sustituir' else 0)
                        pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Deshacer', exact=False).click()
                        self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    puntos.click()
                    pagina.screenshot(path='/tmp/opencode/remotion-menu-plantilla.png', full_page=True)
                    tarjeta.get_by_role('menuitem', name='Eliminar plantilla', exact=True).click()
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-escena:not([hidden]) .remotion-tarjeta").length === 12')
                    activo.get_by_role('button', name='Más opciones de Galería Animada', exact=True).click()
                    activo.get_by_role('menuitem', name='Eliminar plantilla', exact=True).click()
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-escena:not([hidden]) .remotion-tarjeta").length === 11')
                    biblioteca = pagina.evaluate('async () => await pedir(`${BASE}/api/remotion/plantillas`)')
                    self.assertNotIn('ejemplo-galeria', [p['id'] for p in biblioteca['plantillas']])
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    self.assertEqual(remotion.resolver(proyecto, ficha['remotion'][0]['plantilla'])['props']['imagen3'], ficha['remotion'][0]['props']['imagen3'])
                    pagina.evaluate("EDITOR_GLOBAL.seleccionar('S002', 'remotion', 0)")
                    self.assertEqual(activo.locator('.remotion-tarjeta').count(), 11)
                    self.assertEqual(errores, [])
                    navegador.close()
            finally:
                proceso.terminate(); proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
