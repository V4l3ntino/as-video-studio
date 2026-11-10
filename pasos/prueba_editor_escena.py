"""Editor conjunto: guardado validado, bloques independientes y compatibilidad."""
import copy
import io
import os
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import wave
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_editor_escena_')
for clave, nombre in [('ESTUDIO_SECRETOS', 'secretos'), ('ESTUDIO_AJUSTES', 'ajustes.json'),
                      ('ESTUDIO_ESTADISTICAS', 'estadisticas.json')]:
    os.environ[clave] = os.path.join(_DATOS.name, nombre)

import app as servidor  # noqa: E402
from pasos import animaciones, avatar, cartelas, editor_escena  # noqa: E402
import _proyecto_animaciones as juguete  # noqa: E402


class EditorEscena(unittest.TestCase):
    def test_editor_admite_avatar_con_cartela_y_clip_sin_ocultar_el_fondo(self):
        from PIL import Image
        from nucleo.proyecto import leer_json
        from pasos import imagenes_animacion
        with tempfile.TemporaryDirectory() as tmp:
            proyecto, estado = juguete.construir(tmp, animaciones=[], etiquetas={})
            imagen = io.BytesIO()
            Image.new('RGB', (40, 40), 'red').save(imagen, format='PNG')
            retrato = imagenes_animacion.guardar(proyecto, imagen.getvalue(), 'avatar.png')
            estado.actualizar_params('render', {'avatar': dict(activo=True, metodo='subir', imagen=retrato)})
            audio = proyecto.ruta('voz.wav')
            with wave.open(audio, 'wb') as fh:
                fh.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                fh.writeframes(b'\0\0' * 24000 * 30)
            plan = leer_json(proyecto.ruta('pasos', 'assets', 'v1', 'plan.json'))
            escena = plan['escenas'][0]
            escena['cartela'] = dict(plantilla='pregunta', datos=cartelas.PLANTILLAS['pregunta']['ejemplo'])
            clip = proyecto.ruta('clip.mp4')
            Path(clip).write_bytes(b'clip preparado')
            escena['medio_usuario'] = dict(tipo='video', archivo=clip)
            ctx = SimpleNamespace(proyecto=proyecto, estado=estado, gestor=MagicMock())
            ctx.gestor.listar.return_value = []
            with patch.object(servidor, 'contexto', return_value=ctx), patch.object(servidor, '_audio_de_la_toma', return_value=audio), \
                    patch.object(servidor, '_plan_de_previsualizacion', return_value=plan):
                ficha = servidor.leer_editor_avatar(proyecto.id, escena['id'])
                self.assertTrue(ficha['disponible'], ficha['motivo'])
                datos = dict(ancla=ficha['ancla'], activo=True,
                    posicion={k: ficha['actual']['posicion'][k] for k in ('x', 'y')}, presentacion=ficha['actual']['presentacion'])
                previa = servidor.guardar_editor_escena(proyecto.id, escena['id'], {'avatar': datos})
                visible = previa['escenas'][0]
                self.assertTrue(visible['admite_avatar'])
                self.assertIsNotNone(visible['avatar'])
                self.assertTrue(visible['clip'].endswith('clip.mp4'))

    @unittest.skipUnless(REAL, 'usa --real para verificar vídeo, cartela y avatar simultáneos')
    def test_avatar_sobre_cartela_conserva_video_y_reloj_en_ambos_caminos(self):
        from PIL import Image
        from playwright.sync_api import sync_playwright
        from pasos import p8_render
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--allow-file-access-from-files'])
            try:
                page = browser.new_page(viewport={'width': 160, 'height': 90})
                def abrir(ruta):
                    page.goto(Path(ruta).as_uri())
                    page.evaluate('Promise.all([document.fonts.ready, ...Array.from(document.images, img => img.decode())])')
                navegador = SimpleNamespace(abrir=abrir,
                    evaluar=lambda exp, esperar=False: page.evaluate(exp),
                    pintar=lambda t: page.evaluate(f'pintar({t})'),
                    capturar=lambda ruta=None: page.screenshot(path=ruta))
                clips = []
                for nombre, colores, tamano in [('fondo', ['blue', 'yellow'], '160x90'), ('avatar', ['red', 'lime'], '40x40')]:
                    clip = os.path.join(tmp, nombre + '.mp4')
                    subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        f'color={colores[0]}:s={tamano}:r=10:d=1', '-f', 'lavfi', '-i', f'color={colores[1]}:s={tamano}:r=10:d=1',
                        '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-pix_fmt', 'yuv420p', clip], check=True)
                    clips.append(clip)
                imagen = os.path.join(tmp, 'poster.png')
                Image.new('RGB', (160, 90), 'blue').save(imagen)
                for conservar in (True, False):
                    with self.subTest(conservar_frames=conservar):
                        tarea = dict(id='S001', escena=dict(id='S001', t_in=0, t_out=2),
                            mov=dict(ventana_ini=[0, 0, 1, 1], ventana_fin=[0, 0, 1, 1], hyperframe_px=[160, 90]),
                            hyper=imagen, capa='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 90"><rect width="60" height="60" fill="#808080"/></svg>',
                            frames=20, fps=10, video=clips[0], resolucion=[160, 90], calidad='alta', codec='libx264',
                            carpeta=os.path.join(tmp, 'frames'), clip=os.path.join(tmp, 'montado.mp4'), ultimo=os.path.join(tmp, 'ultimo.png'),
                            corte=dict(tipo='corte'), conservar_frames=conservar,
                            avatar=dict(clip=clips[1], posicion=dict(x=.1, y=.1),
                                        presentacion=dict(entrada='sin-animacion', inicio=0, fin=2)))
                        p8_render.renderizar_plano(tarea, navegador)
                        for tiempo in (.5, 1.5):
                            resultado = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(tiempo), '-i', tarea['clip'],
                                '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True, check=True)
                            with Image.open(io.BytesIO(resultado.stdout)) as img:
                                img = img.convert('RGB')
                                figura, fondo, cartela = img.getpixel((30, 25)), img.getpixel((140, 75)), img.getpixel((5, 5))
                                if tiempo < 1:
                                    self.assertGreater(figura[0], figura[1] + 100)
                                    self.assertGreater(fondo[2], fondo[0] + 100)
                                else:
                                    self.assertGreater(figura[1], figura[0] + 100)
                                    self.assertGreater(fondo[0], fondo[2] + 100)
                                self.assertTrue(all(abs(c - 128) < 15 for c in cartela), cartela)
            finally:
                browser.close()

    @unittest.skipUnless(REAL, 'usa --real para verificar la transición por fotogramas')
    def test_enlace_renderizado_sigue_el_intervalo_y_conserva_el_destino(self):
        from PIL import Image
        from playwright.sync_api import sync_playwright
        from pasos import p8_render, transiciones
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--allow-file-access-from-files'])
            try:
                page = browser.new_page(viewport={'width': 160, 'height': 90})
                def abrir(ruta):
                    page.goto(Path(ruta).as_uri())
                    page.evaluate('Promise.all([document.fonts.ready, ...Array.from(document.images, img => img.decode())])')
                navegador = SimpleNamespace(abrir=abrir,
                    evaluar=lambda exp, esperar=False: page.evaluate(exp),
                    pintar=lambda t: page.evaluate(f'pintar({t})'),
                    capturar=lambda ruta: page.screenshot(path=ruta))
                destino = os.path.join(tmp, 'destino.png')
                Image.new('RGB', (160, 90), '#00ff00').save(destino)
                for numero in range(1, 21):
                    Image.new('RGB', (160, 90), 'red').save(os.path.join(tmp, f'f{numero:05d}.png'))
                fuente = dict(escena=dict(id='S002', t_in=2, t_out=4),
                    mov=dict(ventana_ini=[0, 0, 1, 1], ventana_fin=[0, 0, 1, 1], hyperframe_px=[160, 90]),
                    hyper=destino, capa='', capa_fija='', capa_anim='', fondo_anim=None, precarga=[])
                tarea = dict(carpeta=tmp, fps=10, frames=20, resolucion=[160, 90],
                    pagina_trans=transiciones.pagina(os.path.join(tmp, 'transicion.html'), 160, 90),
                    enlace_salida=dict(tipo='fundido', inicio=.5, fin=1.5, destino=fuente))
                self.assertEqual(p8_render._componer_enlace_salida(tarea, navegador), 15)
                for numero, esperado in [(1, (255, 0, 0)), (11, (128, 128, 0)), (17, (0, 255, 0))]:
                    with Image.open(os.path.join(tmp, f'f{numero:05d}.png')) as img:
                        pixel = img.convert('RGB').getpixel((80, 45))
                    self.assertTrue(all(abs(a - b) <= 1 for a, b in zip(pixel, esperado)), (numero, pixel))
            finally:
                browser.close()

    def test_intervalo_enlace_se_guarda_reabre_y_valida_sin_cambios_parciales(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto, estado = juguete.construir(tmp, animaciones=[], etiquetas={})
            ctx = SimpleNamespace(proyecto=proyecto, estado=estado, gestor=MagicMock())
            ctx.gestor.listar.return_value = []
            with patch.object(servidor, 'contexto', return_value=ctx), patch.object(servidor, '_audio_de_la_toma', return_value=None):
                ficha = servidor.leer_editor_escena(proyecto.id, 'S001')
                enlace = dict(tipo='fundido', ancla=ficha['enlace']['ancla'], inicio=2, fin=4)
                antes = Path(proyecto.ruta('estado.json')).read_bytes()
                with self.assertRaises(servidor.ErrorApi):
                    servidor.guardar_editor_escena(proyecto.id, 'S001', {'enlace': dict(enlace, fin=7)})
                self.assertEqual(Path(proyecto.ruta('estado.json')).read_bytes(), antes)
                firmas = {p: estado.firma(p) for p in ('voz', 'guion', 'assets', 'callouts')}
                global_antes = estado.firma_global('render')
                servidor.guardar_editor_escena(proyecto.id, 'S001', {'enlace': enlace})
                reabierto = servidor.leer_editor_escena(proyecto.id, 'S001')['enlace']['actual']
                self.assertEqual((reabierto['inicio'], reabierto['fin'], reabierto['duracion']), (2, 4, 2))
                unidades = estado.params('render')['unidades']
                self.assertEqual(unidades['escena:S001']['salida_transicion'], enlace)
                self.assertEqual(unidades['escena:S002']['transicion'], enlace)
                self.assertEqual({p: estado.firma(p) for p in firmas}, firmas)
                self.assertEqual(estado.firma_global('render'), global_antes)

    @unittest.skipUnless(REAL, 'usa --real para comparar las cartelas en Chromium con Playwright')
    def test_cartelas_por_bloques_conservan_cobertura_y_composicion(self):
        from PIL import Image, ImageChops, ImageStat
        from playwright.sync_api import sync_playwright
        escena = dict(id='S001', narracion='Una frase para la cartela.', duracion=6, t_in=0, t_out=6)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': 600, 'height': 600}, device_scale_factor=1)
                for salida in [(1920, 1080), (1080, 1920), (1280, 720)]:
                    ancho, alto = (480, 270) if salida[0] > salida[1] else (270, 480)
                    for plantilla in cartelas.PLANTILLAS:
                        with self.subTest(salida=salida, plantilla=plantilla):
                            edicion = dict(id='cartela-' + plantilla, ancla=animaciones.ancla_de(escena),
                                contenido=animaciones.contenido_de('cartela-' + plantilla, cartelas.PLANTILLAS[plantilla]['ejemplo']),
                                duracion=5, inicio=.2)
                            imagenes = []
                            for por_bloques in (False, True):
                                animacion = dict(edicion, bloques=[edicion]) if por_bloques else edicion
                                capa = animaciones.capas([escena], {'unidades': {'escena:S001': {'animacion': animacion}}}, salida=salida)['S001']
                                self.assertEqual(len(list(ET.fromstring(capa['svg']).iter('{http://www.w3.org/2000/svg}svg'))), 1)
                                page.set_content(f'<style>body{{margin:0}}#marco{{width:{ancho}px;height:{alto}px;background:#40bf80}}svg{{width:100%;height:100%;display:block}}</style><div id="marco">{capa["svg"]}</div>')
                                page.evaluate("document.fonts.ready")
                                page.evaluate("const svg=document.querySelector('svg');svg.pauseAnimations();svg.setCurrentTime(2.89)")
                                imagenes.append(Image.open(io.BytesIO(page.locator('#marco').screenshot())).convert('RGB'))
                            diferencia = ImageChops.difference(*imagenes)
                            self.assertLess(max(ImageStat.Stat(diferencia).mean), .5,
                                            'la composición por bloques debe conservar la escala y la cobertura de la cartela original')
            finally:
                browser.close()

    def test_guarda_todas_las_pistas_reabre_y_rechaza_sin_guardar_a_medias(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto, estado = juguete.construir(tmp, animaciones=[], etiquetas={})
            ctx = SimpleNamespace(proyecto=proyecto, estado=estado, gestor=MagicMock())
            ctx.gestor.listar.return_value = []
            with patch.object(servidor, 'contexto', return_value=ctx), patch.object(servidor, '_audio_de_la_toma', return_value=None):
                antes = Path(proyecto.ruta('estado.json')).read_bytes()
                ficha = servidor.leer_editor_escena(proyecto.id, 'S001')
                self.assertEqual(antes, Path(proyecto.ruta('estado.json')).read_bytes())
                ancla = ficha['animacion']['ancla']
                bloques = [dict(id='editorial-fecha', ancla=ancla, contenido={'texto': str(2020 + i), 'contexto': 'Prueba'},
                    inicio=i * 3, duracion=2, posiciones={'conjunto': {'x': i * .1, 'y': 0}}) for i in range(2)]
                datos = dict(animacion=dict(bloques[0], bloques=bloques),
                    parallax=dict(ficha['parallax']['actual'], ancla=ficha['parallax']['ancla'], activo=False),
                    transiciones=dict(ancla=ancla, bloques=[dict(tipo='fundido', sentido='entrada', inicio=0, fin=.5),
                                                          dict(tipo='glitch', sentido='salida', inicio=5, fin=6)]),
                    enlace=dict(tipo='sdf-iris', ancla=ficha['enlace']['ancla']))
                firmas = {p: estado.firma(p) for p in ('voz', 'guion', 'assets', 'callouts')}
                invalido = copy.deepcopy(datos)
                invalido['transiciones']['bloques'][1]['fin'] = 8
                with self.assertRaises(servidor.ErrorApi):
                    servidor.guardar_editor_escena(proyecto.id, 'S001', invalido)
                self.assertEqual(antes, Path(proyecto.ruta('estado.json')).read_bytes())
                previa = servidor.guardar_editor_escena(proyecto.id, 'S001', datos)
                capa = previa['escenas'][0]['animacion']
                self.assertEqual(capa['bloques'], bloques)
                self.assertIn('2020', capa['svg'])
                self.assertIn('2021', capa['svg'])
                ET.fromstring(capa['svg'])
                ids = [e.attrib['id'] for e in ET.fromstring(capa['svg']).iter() if 'id' in e.attrib]
                self.assertEqual(len(ids), len(set(ids)))
                reabierta = servidor.leer_editor_escena(proyecto.id, 'S001')
                self.assertEqual(reabierta['transiciones'], datos['transiciones']['bloques'])
                self.assertEqual(reabierta['enlace']['actual']['tipo'], 'sdf-iris')
                self.assertEqual({p: estado.firma(p) for p in firmas}, firmas)
                escena = servidor._plan_de_previsualizacion(ctx)['escenas'][0]
                params = estado.params('render')
                render = animaciones.capas([escena], params, salida=tuple(previa['resolucion']))
                self.assertEqual(render['S001']['svg'], capa['svg'])
                self.assertEqual(servidor.leer_editor_escena(proyecto.id, 'S005')['enlace'], None)
                servidor.guardar_editor_escena(proyecto.id, 'S001', {'animacion': dict(id='sin-animacion', contenido={}, ancla=ancla, bloques=[])})
                self.assertIsNone(servidor.leer_editor_escena(proyecto.id, 'S001')['animacion']['actual'])

    def test_limites_de_bloques_y_avatar_sin_reiniciar_reloj(self):
        escena = dict(id='S001', narracion='Una frase.', duracion=6, t_in=10, t_out=16)
        bloques = [dict(entrada='fundido', inicio=1, fin=2), dict(entrada='desde-derecha', inicio=4, fin=5)]
        presentacion = avatar.validar_presentacion(dict(bloques[0], bloques=bloques), 6)
        self.assertEqual(presentacion['bloques'], bloques)
        for valor in [-1, float('nan'), 7]:
            invalido = copy.deepcopy(bloques)
            invalido[1]['fin'] = valor
            with self.assertRaises(ValueError):
                avatar.validar_presentacion(dict(invalido[0], bloques=invalido), 6)
        with self.assertRaises(ValueError):
            animaciones.validar_edicion({'bloques': [None]}, escena)
        self.assertEqual(editor_escena.transiciones_de({'transiciones_escena': {'ancla': 'otra', 'bloques': bloques}}, escena), [])

    @unittest.skipUnless(shutil.which('ffmpeg'), 'requiere ffmpeg')
    def test_avatar_real_multiples_apariciones_conserva_intervalos(self):
        from PIL import Image
        from nucleo.proyecto import Proyecto
        with tempfile.TemporaryDirectory() as tmp:
            p = Proyecto.crear(tmp, 'Avatar por bloques')
            fondo, clip = p.ruta('fondo.png'), p.ruta('avatar.mp4')
            Image.new('RGB', (160, 90), '#00ff00').save(fondo)
            subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                'color=c=red:s=40x40:d=2:r=30', '-pix_fmt', 'yuv420p', clip], check=True)
            bloques = [dict(entrada='sin-animacion', inicio=.2, fin=.6), dict(entrada='sin-animacion', inicio=1.2, fin=1.6)]
            presentacion = dict(bloques[0], bloques=bloques)
            resultado = avatar.componer(p, clip, fondo, lambda: None, (160, 90), {'x': .1, 'y': .1}, presentacion)
            for t, visible in [(0, False), (.4, True), (.9, False), (1.4, True), (1.8, False)]:
                datos = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(t), '-i', resultado,
                    '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
                pixel = datos[(20 * 160 + 25) * 3:(20 * 160 + 25) * 3 + 3]
                self.assertEqual(pixel[0] > pixel[1], visible, f't={t}: {list(pixel)}')


if __name__ == '__main__':
    unittest.main()
