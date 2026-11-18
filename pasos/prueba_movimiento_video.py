"""Selección eficiente y mediciones OpenCV; --real usa el entorno local probado."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_movimiento_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_ESTILOS_IA',
              'ESTUDIO_PROYECTOS', 'ESTUDIO_PRESETS', 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from pasos import movimiento_video as mv, analisis_video as av, deteccion_escenas as de, estilos_ia as ia
from nucleo.proyecto import leer_json, escribir_json


class Seleccion(unittest.TestCase):
    def ventanas(self, total=120):
        return [dict(id=f'V{i + 1:04d}', t_in=i * 2.5, t_out=(i + 1) * 2.5,
            movimiento=dict(frames_fiables=10, velocidad_media_fraccion_s=.01 if i != 77 else 2,
                zoom_log_s=.5 if i == 81 else 0, residual_px=4 if i == 90 else 0,
                aceleracion_max_fraccion_s2=3 if i == 30 else 0, cambio_luz_max=90 if i == 100 else 0))
            for i in range(total)]

    def test_seleccion_acotada_distribuida_y_con_eventos_distintos(self):
        ventanas = self.ventanas()
        seleccion = mv.seleccionar(ventanas)
        self.assertEqual(len(seleccion), 12)
        self.assertEqual(seleccion[0], ventanas[0])
        self.assertEqual(seleccion[-1], ventanas[-1])
        for i in (77, 81, 90, 30, 100):
            self.assertIn(ventanas[i], seleccion)
        self.assertEqual(len(av._grupos_inspeccion(dict(ventanas=ventanas,
            ventanas_ia=[v['id'] for v in seleccion]))), 6)

    def test_video_corto_no_pierde_ventanas_y_contexto_global_esta_acotado(self):
        ventanas = self.ventanas(4)
        self.assertEqual(mv.seleccionar(ventanas), ventanas)
        resumen = mv.resumen_global(dict(motor='OpenCV', fotogramas_procesados=9000, limites='Sin alpha',
            ventanas=[dict(v, medidas=v['movimiento']) for v in self.ventanas(2000)]))
        self.assertLessEqual(len(resumen['bloques']), 60)
        self.assertEqual(sum(b['intervalos'] for b in resumen['bloques']), 2000)

    def test_velocidad_y_aceleracion_usan_pts_variables_y_no_fps(self):
        with tempfile.TemporaryDirectory() as temporal:
            base = Path(temporal)
            motor = base / 'motor'
            motor.mkdir()
            def correr(orden, *args, **kwargs):
                pedido = leer_json(orden[-1])
                escribir_json(pedido['resultado'], dict(motor='OpenCV', fotogramas_procesados=4, medidas=[
                    dict(n=0, valido=False), dict(n=1, valido=True, dx=.1, dy=0, escala=1),
                    dict(n=2, valido=True, dx=.1, dy=0, escala=1), dict(n=3, valido=False, corte=True)]))
            with patch.object(de, 'preparar_motor', return_value=motor), \
                    patch.object(mv.espacio_estilo, 'correr', side_effect=correr):
                dato = mv.medir(base, base / 'referencia.mkv', dict(duracion_s=.4),
                    [dict(t=t) for t in (0, .1, .3, .4)], dict(cortes=[dict(fotograma=3)]), 'video', lambda *a: None)
            self.assertAlmostEqual(dato['medidas'][1]['velocidad'], 1)
            self.assertAlmostEqual(dato['medidas'][2]['velocidad'], .5)
            self.assertAlmostEqual(dato['medidas'][2]['aceleracion'], -2.5)
            self.assertNotIn('velocidad', dato['medidas'][3])


@unittest.skipUnless(REAL, '--real instala/reutiliza las dependencias locales, sin IA')
class OpenCVReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='opencv_movimiento_')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.raiz = Path(cls.tmp.name)
        cls.motor = de.preparar_motor(cls.raiz, lambda *a: None)

    def test_traslacion_zoom_rotacion_estatico_y_sin_textura(self):
        codigo = r'''
import sys
sys.path.insert(0,sys.argv[1]);sys.path.insert(0,sys.argv[2])
import cv2,numpy as np
from movimiento import medir_par
rng=np.random.default_rng(42)
imagen=cv2.GaussianBlur(rng.integers(20,230,(180,320),dtype=np.uint8),(3,3),0)
estatico=medir_par(imagen,imagen)
assert estatico['valido'] and abs(estatico['dx'])<.001 and abs(estatico['escala']-1)<.001,estatico
matriz=np.array([[1.,0.,4.],[0.,1.,-2.]])
trasladada=cv2.warpAffine(imagen,matriz,(320,180))
d=medir_par(imagen,trasladada)
assert d['valido'] and abs(d['dx']*320-4)<.4 and abs(d['dy']*180+2)<.4,d
zoom=cv2.getRotationMatrix2D((160,90),0,1.025)
d=medir_par(imagen,cv2.warpAffine(imagen,zoom,(320,180)))
assert d['valido'] and abs(d['escala']-1.025)<.01 and abs(d['dx'])<.005,d
rotacion=cv2.getRotationMatrix2D((160,90),1.5,1)
d=medir_par(imagen,cv2.warpAffine(imagen,rotacion,(320,180)))
assert d['valido'] and abs(abs(d['rotacion_grados'])-1.5)<.3,d
d=medir_par(np.full((180,320),40,np.uint8),np.full((180,320),90,np.uint8))
assert not d['valido'] and d['delta_luz']==50 and d['puntos']==0,d
print('OpenCV real: traslación, zoom, rotación, estático y falta de textura correctos')
'''
        import shutil
        shutil.copyfile(mv.EJECUTOR, self.motor / 'movimiento.py')
        subprocess.run([sys.executable, '-I', '-S', '-c', codigo, str(self.motor / 'dependencias'), str(self.motor)],
                       check=True, timeout=60)

    def test_video_entero_medido_y_solo_doce_ventanas_visuales(self):
        from pasos import medios
        destino = self.raiz / 'video'
        destino.mkdir()
        video = destino / 'referencia.mkv'
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
            'testsrc2=s=320x180:r=10:d=32', '-c:v', 'ffv1', str(video)], capture_output=True, check=True, timeout=60)
        with patch.object(de, 'preparar_motor', return_value=self.motor), patch.object(av, 'SEGUNDOS_VENTANA', 1):
            ia.extraer(destino, dict(referencia=video.name, analisis_eficiente=True), lambda *a: None)
        indice = leer_json(str(destino / 'analisis_visual' / 'indice.json'))
        movimiento = leer_json(str(destino / 'analisis_visual' / 'movimiento.json'))
        self.assertEqual(movimiento['fotogramas_procesados'], 320)
        self.assertEqual(movimiento['medidas'][-1]['n'], 319)
        self.assertEqual(indice['modo'], 'movimiento_selectivo')
        self.assertEqual(len(indice['ventanas_ia']), 12)
        self.assertEqual(len(av._grupos_inspeccion(indice)), 6)
        self.assertEqual(indice['ventanas_ia'][-1], indice['ventanas'][-1]['id'])
        self.assertTrue(any(v['movimiento']['frames_fiables'] for v in indice['ventanas']))


if __name__ == '__main__':
    unittest.main()
