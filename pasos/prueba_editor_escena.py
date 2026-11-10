"""Editor conjunto: guardado validado, bloques independientes y compatibilidad."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_editor_escena_')
for clave, nombre in [('ESTUDIO_SECRETOS', 'secretos'), ('ESTUDIO_AJUSTES', 'ajustes.json'),
                      ('ESTUDIO_ESTADISTICAS', 'estadisticas.json')]:
    os.environ[clave] = os.path.join(_DATOS.name, nombre)

import app as servidor  # noqa: E402
from pasos import animaciones, avatar, editor_escena  # noqa: E402
import _proyecto_animaciones as juguete  # noqa: E402


class EditorEscena(unittest.TestCase):
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
