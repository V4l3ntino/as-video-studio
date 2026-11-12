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
                    pagina.on('pageerror', lambda e: errores.append(str(e)))
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
                    self.assertTrue(activo.locator('.remotion-taller').is_visible())
                    pagina.evaluate('document.querySelector("#panel").scrollTop = 0')
                    pagina.screenshot(path='/tmp/opencode/remotion-biblioteca.png', full_page=True)
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
                    activo.get_by_role('button', name='Aplicar a la escena', exact=False).click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-estado").textContent.includes("Animación incorporada")', timeout=180000)
                    self.assertEqual(pagina.locator('.remotion .anim-timeline-bloque').count(), 1)
                    pagina.locator('.editor-global > .light-cab').get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()', timeout=30000)
                    # Seleccionar un bloque recupera su código y permite sustituirlo.
                    pagina.locator('.remotion .anim-timeline-bloque').first.click()
                    pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .remotion-taller").dataset.plantillaEditada')
                    titulo = activo.locator('.remotion-prop').filter(has=pagina.get_by_text('titulo', exact=True)).locator('input')
                    titulo.fill('Título corregido'); titulo.press('Tab')
                    activo.get_by_role('button', name='Aplicar a la escena', exact=False).click()
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
                    self.assertEqual(errores, [])
                    navegador.close()
            finally:
                proceso.terminate(); proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
