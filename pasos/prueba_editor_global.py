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
                    activo = pagina.locator('.editor-global-escena[data-panel-activo="true"]')
                    self.assertEqual(activo.get_by_role('tab').count(), 7)
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
                    # La narración es una sola toma: los cortes visuales no
                    # provocan pause/play, seeking ni una recarga del archivo.
                    pagina.evaluate('''() => {
                        const a = EDITOR_GLOBAL.audio(PREVIA.ficha.audio);
                        window.eventosVoz = [];
                        for (const ev of ['pause', 'play', 'seeking', 'emptied'])
                            a.addEventListener(ev, () => eventosVoz.push(ev));
                        a.playbackRate = 4;
                    }''')
                    mandos.get_by_role('button', name='Reproducir', exact=False).click()
                    pagina.wait_for_function('PREVIA.i >= 2', timeout=15000)
                    eventos = pagina.evaluate('eventosVoz')
                    self.assertEqual(eventos.count('play'), 1, eventos)
                    self.assertLessEqual(eventos.count('seeking'), 1, eventos)
                    self.assertNotIn('pause', eventos)
                    self.assertNotIn('emptied', eventos)
                    mandos.get_by_role('button', name='Pausar', exact=False).click()
                    detenido = pagina.evaluate('PREVIA.t')
                    pagina.wait_for_timeout(200)
                    self.assertAlmostEqual(pagina.evaluate('PREVIA.t'), detenido, places=2)
                    mandos.get_by_role('button', name='Reproducir', exact=False).click()
                    pagina.wait_for_function('t => PREVIA.t > t + .2', arg=detenido)
                    mandos.get_by_role('button', name='Pausar', exact=False).click()
                    activo.get_by_role('tab', name='Imágenes', exact=True).click()
                    activo.locator('[data-escena="S003"]').click()
                    self.assertEqual(pagina.evaluate('PREVIA.i'), 2)
                    self.assertAlmostEqual(pagina.evaluate('PREVIA.t'), 12, places=2)
                    self.assertEqual(activo.locator('[aria-pressed="true"][data-escena]').get_attribute('data-escena'), 'S003')
                    # Una tanda global no bloquea la galería ni el cambio de
                    # escena. Las ediciones siguen protegidas mientras genera.
                    pagina.evaluate('''() => {
                        window.trabajoVideoOriginal = trabajoVideoLight;
                        trabajoVideoLight = () => ({id: 'tanda-simulada', estado: 'ejecutando'});
                        EDITOR_GLOBAL.refrescar(PREVIA.ficha.escenas);
                    }''')
                    galeria = activo.locator('.previa-galeria')
                    self.assertEqual(galeria.evaluate('n => getComputedStyle(n).pointerEvents'), 'auto')
                    self.assertEqual(activo.locator('.escena-editor-panel').evaluate('n => getComputedStyle(n).opacity'), '1')
                    galeria.locator('[data-escena="S004"]').click()
                    self.assertEqual(pagina.evaluate('PREVIA.i'), 3)
                    galeria.locator('[data-escena="S002"]').focus()
                    pagina.keyboard.press('Enter')
                    self.assertEqual(pagina.evaluate('PREVIA.i'), 1)
                    activo.get_by_role('tab', name='Animación', exact=True).click()
                    self.assertEqual(activo.locator('.escena-editor-panel').evaluate('n => getComputedStyle(n).pointerEvents'), 'none')
                    activo.get_by_role('tab', name='Imágenes', exact=True).click()
                    galeria.locator('[data-escena="S003"]').click()
                    pagina.screenshot(path='/tmp/opencode/galeria-durante-generacion.png', full_page=True)
                    pagina.evaluate('''() => {
                        trabajoVideoLight = window.trabajoVideoOriginal;
                        delete window.trabajoVideoOriginal;
                        EDITOR_GLOBAL.refrescar(PREVIA.ficha.escenas);
                    }''')
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
                        window.cacheProyectoOriginal = CACHE_EDITOR.proyecto;
                        window.cacheGuardarOriginal = CACHE_EDITOR.guardar;
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
                    # El selector Stickman es común al editor y gobierna chat y aplicación.
                    pagina.route('**/stickman/chat', lambda ruta: ruta.fulfill(json={'mensajes': []}))
                    def revision_stickman(ruta):
                        respuesta = ruta.fetch()
                        ficha = respuesta.json()
                        revisiones = pagina.evaluate('window.revisionesStickman || {}')
                        for escena in ficha['escenas']:
                            if escena['id'] in revisiones:
                                escena['editor_revision'] += ':' + str(revisiones[escena['id']])
                        ruta.fulfill(response=respuesta, json=ficha)
                    pagina.route('**/previsualizacion', revision_stickman)
                    pagina.evaluate('''() => {
                        CACHE_EDITOR.proyecto = window.cacheProyectoOriginal;
                        CACHE_EDITOR.guardar = window.cacheGuardarOriginal;
                        window.revisionesStickman = {};
                        repintarVideo = () => document.querySelector('#panel').replaceChildren(editorGlobalImagenes(PREVIA.ficha.escenas));
                        const pedidoOriginal = pedidoDelVideoLight;
                        pedidoDelVideoLight = () => {
                            const p = pedidoOriginal();
                            return {...p, copia: {...p.copia, stickman: {}}};
                        };
                        window.turnosStickman = [];
                        const crearOriginal = crearChatEdicionStickman;
                        crearChatEdicionStickman = opciones => crearOriginal({...opciones,
                            trabajo: async (ruta, datos) => {
                                window.turnosStickman.push(datos);
                                if (datos.aplicar) window.revisionesStickman[opciones.escena.id] = window.turnosStickman.length;
                                return {mensajes: [{autor: 'usuario', texto: datos.mensaje, imagen: datos.imagen},
                                    {autor: datos.porcentaje ? 'chatgpt' : 'claude', texto: 'Entendido.'}]};
                            }});
                        EDITOR_GLOBAL.cerrar(); EDITOR_GLOBAL = null;
                        document.querySelector('#panel').replaceChildren(editorGlobalImagenes(PREVIA.ficha.escenas));
                    }''')
                    pagina.wait_for_timeout(500)
                    self.assertFalse(errores, errores)
                    pagina.wait_for_selector('.stickman-edicion', state='attached')
                    selector = pagina.get_by_role('group', name='IA para el chat y los cambios de escena')
                    claude = selector.get_by_role('button', name='Claude', exact=True)
                    chatgpt = selector.get_by_role('button', name='ChatGPT', exact=True)
                    self.assertEqual(claude.get_attribute('aria-pressed'), 'true')
                    self.assertEqual(pagina.locator('.stickman-edicion .stickman-proveedores').count(), 0)
                    titulo = cabecera.get_by_role('heading', name='Editor del vídeo').bounding_box()
                    botones = selector.bounding_box()
                    self.assertGreater(botones['y'], titulo['y'] + titulo['height'])
                    self.assertAlmostEqual(botones['x'], titulo['x'], delta=1)
                    chatgpt.click()
                    pagina.evaluate('EDITOR_GLOBAL.seleccionar("S001", "imagenes", 0)')
                    activo.get_by_role('button', name='Editar escena', exact=True).click()
                    chat = activo.locator('.stickman-edicion')
                    chat.get_by_role('textbox').fill('Aleja el zoom')
                    imagen_contexto = proyecto.ruta('pasos', 'assets', 'v1', 'escenas', 'S001.png')
                    estado_antes_subida = Path(proyecto.ruta('estado.json')).read_bytes()
                    chat.locator('input[type=file]').set_input_files(imagen_contexto)
                    chat.get_by_role('button', name='Quitar imagen', exact=True).wait_for()
                    self.assertEqual(estado_antes_subida, Path(proyecto.ruta('estado.json')).read_bytes())
                    chat.get_by_role('button', name='Quitar imagen', exact=True).click()
                    self.assertTrue(chat.locator('.stickman-chat-adjunto').is_hidden())
                    chat.locator('input[type=file]').set_input_files(imagen_contexto)
                    chat.get_by_role('button', name='Quitar imagen', exact=True).wait_for()
                    self.assertTrue(chat.locator('.stickman-chat-imagen').evaluate('n => n.complete && n.naturalWidth > 0'))
                    chat.get_by_role('button', name='Enviar mensaje', exact=True).click()
                    chat.get_by_text('ChatGPT: ', exact=True).wait_for()
                    referencia = pagina.evaluate('turnosStickman[0].imagen')
                    self.assertTrue(referencia.startswith('medios_usuario/animaciones/'))
                    self.assertTrue(chat.locator('.remotion-chat-mensajes .stickman-chat-imagen').is_visible())
                    self.assertTrue(chat.locator('.stickman-chat-adjunto').is_hidden())
                    pagina.evaluate('''() => {
                        window.timelineAnterior = document.querySelector('.editor-global-timeline');
                        window.columnasAnteriores = [...document.querySelectorAll('.editor-global-columna')];
                        window.editorAnterior = EDITOR_GLOBAL;
                    }''')
                    peticiones_aplicar = []
                    def contar_editor(solicitud):
                        if solicitud.url.endswith('/editor') and solicitud.method == 'GET':
                            peticiones_aplicar.append(solicitud.url)
                    pagina.on('request', contar_editor)
                    chat.get_by_role('button', name='Aplicar cambios', exact=True).click()
                    pagina.wait_for_function('turnosStickman.length === 2')
                    pagina.wait_for_function('PREVIA.ficha.escenas[0].editor_revision.endsWith(":2")')
                    pagina.wait_for_function('!document.querySelector(".stickman-proveedores button").disabled')
                    def esperar_cache_stickman(sid, turno):
                        for _ in range(100):
                            if pagina.evaluate('''async ([pid, sid, turno]) => {
                                const fila = await CACHE_EDITOR.leer(pid, sid);
                                return fila.revision.endsWith(':' + turno) && fila.revision === PREVIA.ficha.escenas.find(e => e.id === sid).editor_revision;
                            }''', [proyecto.id, sid, turno]):
                                return
                            pagina.wait_for_timeout(100)
                        self.fail('No se actualizó la caché de ' + sid)
                    esperar_cache_stickman('S001', 2)
                    self.assertTrue(pagina.evaluate('''() => EDITOR_GLOBAL === window.editorAnterior
                        && document.querySelector('.editor-global-timeline') === window.timelineAnterior
                        && [...document.querySelectorAll('.editor-global-columna')].every((n, i) => n === window.columnasAnteriores[i])'''))
                    self.assertEqual(peticiones_aplicar,
                        [url + f'/api/proyectos/{proyecto.id}/escenas/S001/editor'])
                    pagina.remove_listener('request', contar_editor)
                    pagina.wait_for_function('''() => {
                        EDITOR_GLOBAL.seleccionar('S002', 'imagenes', 0);
                        return document.querySelector('.editor-global-escena[data-panel-activo="true"]')?.getAttribute('aria-label').includes('S002');
                    }''')
                    self.assertEqual(chatgpt.get_attribute('aria-pressed'), 'true')
                    activo.get_by_role('button', name='Editar escena', exact=True).click()
                    claude.click()
                    chat.get_by_role('textbox').fill('Conserva los colores')
                    chat.get_by_role('button', name='Enviar mensaje', exact=True).click()
                    chat.get_by_text('Claude: ', exact=True).wait_for()
                    chat.locator('input[type=file]').set_input_files(imagen_contexto)
                    chat.get_by_role('button', name='Quitar imagen', exact=True).wait_for()
                    chat.get_by_role('button', name='Aplicar cambios', exact=True).click()
                    pagina.wait_for_function('turnosStickman.length === 4')
                    pagina.wait_for_function('PREVIA.ficha.escenas[1].editor_revision.endsWith(":4")')
                    esperar_cache_stickman('S002', 4)
                    self.assertEqual(pagina.evaluate('turnosStickman.map(t => [t.porcentaje, t.aplicar])'),
                        [[100, False], [100, True], [0, False], [0, True]])
                    self.assertTrue(pagina.evaluate('!!turnosStickman[3].imagen'))
                    pagina.wait_for_function('!document.querySelector(".stickman-proveedores button").disabled')
                    regeneraciones = []
                    def regenerar_sin_proveedor(ruta):
                        regeneraciones.append(ruta.request.post_data_json)
                        ruta.fulfill(json={'trabajo_id': 'regeneracion-prueba'})
                    pagina.route('**/stickman/regenerar', regenerar_sin_proveedor)
                    pagina.route('**/api/trabajos/regeneracion-prueba', lambda ruta: ruta.fulfill(
                        json={'estado': 'listo', 'progreso': 1, 'resultado': {}}))
                    # Conserva el editor de prueba tras refrescar la previa simulada.
                    pagina.evaluate('repintarVideo = () => {}')
                    for boton, porcentaje in ((chatgpt, 100), (claude, 0)):
                        boton.click()
                        activo.get_by_role('button', name='Regenerar escena', exact=True).click()
                        pagina.wait_for_function('!document.querySelector(".stickman-proveedores button").disabled')
                        self.assertEqual(regeneraciones[-1], {'porcentaje': porcentaje})
                    pagina.set_viewport_size({'width': 390, 'height': 844})
                    self.assertTrue(pagina.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    pagina.set_viewport_size({'width': 1440, 'height': 1000})
                    chat.locator('input[type=file]').set_input_files(imagen_contexto)
                    chat.get_by_role('button', name='Quitar imagen', exact=True).wait_for()
                    if os.environ.get('ESTUDIO_CAPTURA_EDITOR'):
                        pagina.screenshot(path=os.environ['ESTUDIO_CAPTURA_EDITOR'], full_page=True)
                    self.assertFalse(errores, errores)
                    pagina.unroute_all(behavior='wait')
                    navegador.close()
            finally:
                proceso.terminate()
                proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
