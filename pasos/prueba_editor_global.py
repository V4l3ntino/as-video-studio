"""Regresión de navegador del editor global, sin proveedores ni generación.

    python pasos/prueba_editor_global.py --real

Requiere Chromium de Playwright. El proyecto, las claves y los ajustes son
temporales; no se abre ninguna cuenta ni se solicita contenido a IA.
"""
import math
import os
from pathlib import Path
import socket
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import wave
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


@unittest.skipUnless(REAL, 'usa --real para comprobar el editor en Chromium')
class EditorGlobal(unittest.TestCase):
    def test_edicion_global_conserva_borradores_guardado_y_reloj(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix='editor_global_') as tmp, patch.dict(os.environ):
            entorno = dict(os.environ)
            for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS'):
                entorno[clave] = os.path.join(tmp, clave)
                os.environ[clave] = entorno[clave]
            # El constructor no carga ajustes, credenciales ni proveedores.
            from pasos._proyecto_animaciones import construir
            from nucleo.proyecto import leer_json, escribir_json
            proyecto, estado = construir(os.path.join(tmp, 'proyectos'))
            clip = proyecto.ruta('fondo.mp4') if shutil.which('ffmpeg') else None
            if clip:
                subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                    'testsrc2=s=160x90:r=30:d=2', '-pix_fmt', 'yuv420p', clip], check=True)
                ruta_plan = proyecto.ruta('pasos', 'assets', 'v1', 'plan.json')
                plan = leer_json(ruta_plan)
                plan['escenas'][0]['medio_biblioteca'] = {'tipo': 'video', 'archivo': clip}
                escribir_json(ruta_plan, plan)
            with wave.open(os.path.join(proyecto.ruta_trabajo('voz'), 'narracion.wav'), 'wb') as voz:
                voz.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
                voz.writeframes(b''.join(struct.pack('<h', int(6000 * math.sin(i * .15))) for i in range(480000)))
            estado.completar('voz', {'pista': 'narracion.wav'})
            if clip:
                shutil.copyfile(clip, os.path.join(proyecto.ruta_trabajo('render'), 'video.mp4'))
                estado.completar('render', {'mp4': 'video.mp4'})
            antes = Path(proyecto.ruta('estado.json')).read_bytes()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                puerto = sock.getsockname()[1]
            proceso = subprocess.Popen([sys.executable, str(RAIZ / 'app.py'), '--puerto', str(puerto),
                '--proyectos', os.path.join(tmp, 'proyectos')], cwd=RAIZ, env=entorno,
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
                    navegador = pw.chromium.launch(headless=True, executable_path=os.environ.get('ESTUDIO_EDGE') or None)
                    pagina = navegador.new_page(viewport={'width': 1440, 'height': 1000})
                    errores = []
                    pagina.on('pageerror', lambda error: errores.append(str(error)))
                    # Retrato sin clip de avatar: abrir el editor no genera Boson.
                    peticiones_editor = []
                    def con_retrato(ruta):
                        if ruta.request.method != 'GET':
                            ruta.continue_()
                            return
                        respuesta = ruta.fetch()
                        peticiones_editor.append(ruta.request.url)
                        ficha = respuesta.json()
                        ficha['avatar']['retrato'] = 'pasos/assets/v1/escenas/S001.png'
                        ruta.fulfill(response=respuesta, json=ficha)
                    pagina.route('**/escenas/*/editor', con_retrato)
                    pagina.goto(url)
                    pagina.wait_for_function('typeof editorGlobalImagenes === "function"')
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate('''async pid => {
                        APP.light.video.pid = pid; APP.light.video.vista = 'previa';
                        PREVIA.ficha = await pedir(`${API.proyecto(pid)}/previsualizacion`);
                        PREVIA.i = 0; document.querySelector('#inicio')?.remove();
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.wait_for_timeout(500)
                    self.assertEqual(antes, Path(proyecto.ruta('estado.json')).read_bytes(), 'Abrir el editor no escribe params')
                    activo = pagina.locator('.editor-global-escena:not([hidden])')
                    self.assertEqual(activo.get_by_role('tab').count(), 6)
                    self.assertEqual(pagina.locator('dialog[open]').count(), 0)
                    if clip:
                        pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .previa-clip")?.readyState >= 2')
                        pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "imagenes", 3)')
                        pagina.wait_for_function('document.querySelector(".editor-global-escena:not([hidden]) .previa-clip").currentTime > 1.9')
                        self.assertTrue(activo.locator('.previa-clip').evaluate('n => n.paused && n.muted && !n.loop'))
                        pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "imagenes", 0)')
                    cabecera = pagina.locator('.editor-global > .light-cab')
                    bloques = pagina.locator('.editor-global-bloque-escena')
                    activo.get_by_role('tab', name='Animación', exact=True).click()
                    activo.get_by_role('button', name='+ Añadir bloque').click()
                    bloques.nth(1).click()
                    activo.get_by_role('tab', name='Animación', exact=True).click()
                    activo.get_by_role('button', name='+ Añadir bloque').click()
                    bloques.nth(0).click()
                    activo.get_by_role('tab', name='Animación', exact=True).click()
                    self.assertEqual(activo.locator('.escena-editor-bloques button').count(), 2)
                    cabecera.get_by_role('button', name='Deshacer', exact=False).click()
                    self.assertIn('S002', activo.get_attribute('aria-label'))
                    self.assertEqual(pagina.locator('.editor-global-columna').nth(1).locator('.animacion .anim-timeline-bloque').count(), 1)
                    # Un repintado de la aplicación conserva el árbol y los borradores.
                    pagina.evaluate('document.querySelector("#panel").replaceChildren(vistaPreviaLight())')
                    self.assertTrue(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    cabecera.get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()')
                    # Reabrir reutiliza las fichas persistidas después de guardar.
                    peticiones_antes = len(peticiones_editor)
                    pagina.evaluate('EDITOR_GLOBAL.cerrar(); EDITOR_GLOBAL = null; document.querySelector("#panel").replaceChildren(vistaPreviaLight())')
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.wait_for_timeout(500)
                    self.assertEqual(len(peticiones_editor), peticiones_antes, 'No vuelve a pedir las escenas guardadas')
                    self.assertEqual(pagina.locator('.editor-global-columna').nth(0).locator('.animacion .anim-timeline-bloque').count(), 2)
                    bloques.nth(0).click()
                    pista = pagina.locator('.editor-global-columna').nth(0).locator('.animacion .anim-timeline-bloque').first
                    pista.click()
                    self.assertEqual(activo.get_by_role('tab', name='Animación', exact=True).get_attribute('aria-selected'), 'true')
                    # Arrastrar el extremo cambia la duración dentro de su escena.
                    asa = pista.locator('[data-extremo="fin"]').bounding_box()
                    pagina.mouse.move(asa['x'] + asa['width'] / 2, asa['y'] + asa['height'] / 2)
                    pagina.mouse.down()
                    pagina.mouse.move(asa['x'] - 20, asa['y'] + asa['height'] / 2, steps=5)
                    pagina.mouse.up()
                    self.assertTrue(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    for nombre in ('Sonidos', 'Efecto Parallax', 'Transición', 'Avatar'):
                        activo.get_by_role('tab', name=nombre, exact=True).click()
                    bloques.nth(0).click()
                    mandos = pagina.locator('.editor-global-timeline > .anim-timeline-cab')
                    mandos.get_by_role('button', name='Reproducir', exact=False).click()
                    pagina.wait_for_function('PREVIA.i >= 1', timeout=15000)
                    mandos.get_by_role('button', name='Pausar', exact=False).click()
                    activo.get_by_role('tab', name='Imágenes', exact=True).click()
                    activo.locator('[data-escena="S003"]').click()
                    self.assertEqual(pagina.evaluate('PREVIA.i'), 2)
                    self.assertAlmostEqual(pagina.evaluate('PREVIA.t'), 12, places=2)
                    self.assertEqual(activo.locator('[aria-pressed="true"][data-escena]').get_attribute('data-escena'), 'S003')
                    # El cabezal se puede arrastrar a través de los cortes.
                    pistas = pagina.locator('.editor-global-columna .anim-timeline-pista.audio')
                    desde, hasta = pistas.nth(0).bounding_box(), pistas.nth(3).bounding_box()
                    pagina.mouse.move(desde['x'] + 5, desde['y'] + 12)
                    pagina.mouse.down()
                    pagina.mouse.move(hasta['x'] + hasta['width'] / 2, hasta['y'] + 12, steps=5)
                    pagina.mouse.up()
                    self.assertEqual(pagina.evaluate('PREVIA.i'), 3)
                    cabecera.get_by_role('button', name='Descartar cambios', exact=True).click()
                    self.assertFalse(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    # Salir por la navegación real y volver reutiliza el editor.
                    pagina.evaluate('''async pid => {
                        await abrirVideoLight(pid);
                        APP.light.video.vista = 'previa'; pintarLight();
                    }''', proyecto.id)
                    navegacion = pagina.get_by_role('navigation', name='Pasos del vídeo')
                    destinos = ('Encargo', 'Guion', 'Vídeo', 'Shorts', 'Estilos') if clip else ('Encargo', 'Guion', 'Estilos')
                    for destino in destinos:
                        pagina.wait_for_selector('.editor-global-escena:not([hidden]) img.previa-avatar', state='attached')
                        navegacion.get_by_role('button', name=destino, exact=True).click()
                        pagina.wait_for_function('!document.querySelector(".editor-global")')
                        if destino == 'Estilos':
                            pagina.evaluate('pid => abrirVideoLight(pid)', proyecto.id)
                        navegacion.get_by_role('button', name='Imágenes', exact=True).click()
                        pagina.wait_for_selector('.editor-global')
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.wait_for_selector('.editor-global-escena:not([hidden]) img.previa-avatar', state='attached')
                    pagina.set_viewport_size({'width': 390, 'height': 844})
                    self.assertTrue(pagina.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    pagina.set_viewport_size({'width': 1440, 'height': 1000})
                    # Recarga real: conserva los bloques y el borrador sin GET por escena.
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "animacion", 0)')
                    cuantos = activo.locator('.escena-editor-bloques button').count()
                    activo.get_by_role('button', name='+ Añadir bloque').click()
                    pagina.wait_for_function('EDITOR_GLOBAL.modificado()')
                    pagina.wait_for_function('''async pid => {
                        const fila = await CACHE_EDITOR.leer(pid, 'S001');
                        return fila && fila.borrador !== fila.original;
                    }''', arg=proyecto.id)
                    peticiones_antes = len(peticiones_editor)
                    pagina.reload()
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate('''async pid => {
                        APP.light.video.pid = pid; APP.light.video.vista = 'previa';
                        PREVIA.ficha = await pedir(`${API.proyecto(pid)}/previsualizacion`);
                        PREVIA.i = 0; document.querySelector('#inicio')?.remove();
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('EDITOR_GLOBAL?.modificado()')
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.wait_for_timeout(500)
                    self.assertEqual(len(peticiones_editor), peticiones_antes)
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "animacion", 0)')
                    self.assertEqual(activo.locator('.escena-editor-bloques button').count(), cuantos + 1)
                    cabecera.get_by_role('button', name='Descartar cambios', exact=True).click()
                    pagina.wait_for_function('''async pid => {
                        const fila = await CACHE_EDITOR.leer(pid, 'S001');
                        return fila && fila.borrador === fila.original;
                    }''', arg=proyecto.id)
                    # Una entrada ausente obliga a pedir solo esa escena.
                    pagina.evaluate('''async pid => {
                        await CACHE_EDITOR.operar('readwrite', tabla => tabla.delete([BASE, pid, 'S004']));
                        EDITOR_GLOBAL.cerrar(); EDITOR_GLOBAL = null;
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.wait_for_function('''async pid => !!await CACHE_EDITOR.leer(pid, 'S004')''', arg=proyecto.id)
                    pagina.wait_for_timeout(500)
                    self.assertEqual(len(peticiones_editor), peticiones_antes + 1)
                    self.assertTrue(peticiones_editor[-1].endswith('/S004/editor'))
                    # Un cambio remoto invalida esa escena y protege su borrador local.
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S002", "animacion", 0)')
                    activo.get_by_role('button', name='+ Añadir bloque').click()
                    pagina.wait_for_function('''async pid => {
                        const f = await CACHE_EDITOR.leer(pid, 'S002'); return f.borrador !== f.original;
                    }''', arg=proyecto.id)
                    pagina.evaluate('''async pid => {
                        const base = `${API.proyecto(pid)}/escenas/S002/editor`;
                        const ficha = await pedir(base);
                        await pedir(base, { method: 'PUT', cuerpo: { sonidos: { ancla: ficha.animacion.ancla, bloques: [] } } });
                        PREVIA.ficha = await pedir(`${API.proyecto(pid)}/previsualizacion`);
                        EDITOR_GLOBAL.cerrar(); EDITOR_GLOBAL = null;
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .anim-timeline-pistas").length === 5')
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S002", "animacion", 0)')
                    activo.get_by_role('button', name='Recuperar mis cambios', exact=True).wait_for()
                    self.assertFalse(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    activo.get_by_role('button', name='Recuperar mis cambios', exact=True).click()
                    self.assertTrue(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    cabecera.get_by_role('button', name='Guardar cambios', exact=True).click()
                    pagina.wait_for_function('!EDITOR_GLOBAL.modificado()')
                    # La misma comprobación funciona sin destruir el editor en memoria.
                    pagina.evaluate('''async pid => {
                        const base = `${API.proyecto(pid)}/escenas/S005/editor`;
                        const ficha = await pedir(base);
                        await pedir(base, { method: 'PUT', cuerpo: { sonidos: { ancla: ficha.animacion.ancla, bloques: [] } } });
                        PREVIA.ficha = await pedir(`${API.proyecto(pid)}/previsualizacion`);
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''', proyecto.id)
                    pagina.wait_for_function('''async pid => {
                        const fila = await CACHE_EDITOR.leer(pid, 'S005');
                        return fila.revision === PREVIA.ficha.escenas.find(e => e.id === 'S005').editor_revision;
                    }''', arg=proyecto.id)
                    # IndexedDB denegado o sin espacio: las peticiones normales siguen funcionando.
                    pagina.evaluate('''() => {
                        CACHE_EDITOR.proyecto = async () => { throw new Error('Almacenamiento denegado'); };
                        CACHE_EDITOR.guardar = async () => { throw new Error('Sin espacio'); };
                        EDITOR_GLOBAL.cerrar(); EDITOR_GLOBAL = null;
                        document.querySelector('#panel').replaceChildren(vistaPreviaLight());
                    }''')
                    pagina.wait_for_function('document.querySelectorAll(".editor-global-columna .animacion .anim-timeline-bloque").length >= 5')
                    pagina.get_by_text('No se pudo acceder al almacenamiento local.', exact=False).wait_for()
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "animacion", 0)')
                    activo.get_by_role('button', name='+ Añadir bloque').click()
                    self.assertTrue(pagina.evaluate('EDITOR_GLOBAL.modificado()'))
                    self.assertFalse(errores, errores)
                    pagina.unroute_all(behavior='wait')
                    navegador.close()
            finally:
                proceso.terminate()
                proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
