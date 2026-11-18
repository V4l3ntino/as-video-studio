"""PySceneDetect: contratos sin red; --real instala el entorno y procesa vídeo."""
import copy
import csv
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
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_escenas_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_ESTILOS_IA',
              'ESTUDIO_PROYECTOS', 'ESTUDIO_PRESETS', 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import deteccion_escenas as de, analisis_video as av, espacio_estilo


def resultado(total=40):
    return dict(motor='PySceneDetect', version='0.6.7', completo=True, fotogramas_procesados=total,
                configuracion=copy.deepcopy(de.CONFIGURACION), cortes=[dict(fotograma=10, detectores=['adaptativo'],
                    metricas={'content_val': 50.})])


class Contratos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destino = Path(self.tmp.name)
        self.medidas = [dict(n=n, t=n * .1 if n < 10 else 1.5 + (n - 10) * .05,
            cambio=0, variacion=0, luz=120, contraste=100, saturacion=40) for n in range(40)]

    def test_rechaza_resultados_truncados_y_cortes_invalidos(self):
        de.validar(resultado(), 40)
        for modificacion in (dict(completo=False), dict(fotogramas_procesados=39), dict(configuracion={}),
                             dict(cortes=[dict(fotograma=40, detectores=['adaptativo'], metricas={})]),
                             dict(cortes=[dict(fotograma=10, detectores=['inventado'], metricas={})]),
                             dict(cortes=[dict(fotograma=10, detectores=['adaptativo'], metricas={'x': float('nan')})])):
            with self.assertRaises(ValueError): de.validar(dict(resultado(), **modificacion), 40)

    def test_frames_se_traducen_con_pts_reales_y_cache_no_repite_proceso(self):
        base = self.destino / 'motor'
        base.mkdir()
        def correr(orden, *args, **kwargs):
            pedido = leer_json(orden[-1])
            escribir_json(pedido['resultado'], resultado())
            Path(pedido['metricas']).write_text('fotograma,content_val\n10,50\n', encoding='utf-8')
        with patch.object(de, 'preparar_motor', return_value=base), patch.object(espacio_estilo, 'correr', side_effect=correr):
            dato = de.detectar(self.destino, 'referencia.mkv', dict(duracion_s=3), self.medidas, 'video', lambda *a: None)
        self.assertEqual(dato['cortes'][0]['t'], 1.5)  # no 10 / FPS
        self.assertEqual([(s['t_in'], s['t_out']) for s in dato['escenas']], [(0, 1.5), (1.5, 3)])
        with patch.object(de, 'preparar_motor', side_effect=AssertionError('la caché debe bastar')):
            self.assertEqual(de.detectar(self.destino, 'referencia.mkv', dict(duracion_s=3), self.medidas,
                                        'video', lambda *a: None), dato)

    def test_error_o_cancelacion_no_publica_segmentacion(self):
        base = self.destino / 'motor'
        base.mkdir()
        for fallo in (Cancelado(), ValueError('no ha decodificado todo')):
            with patch.object(de, 'preparar_motor', return_value=base), \
                    patch.object(espacio_estilo, 'correr', side_effect=fallo), self.assertRaises(type(fallo)):
                de.detectar(self.destino, 'referencia.mkv', dict(duracion_s=3), self.medidas, 'video', lambda *a: None)
            self.assertFalse((self.destino / 'escenas.json').exists())

    def test_plan_usa_escenas_pyscenedetect_y_conserva_ambos_lados_del_corte(self):
        self.medidas[20]['cambio'] = 90  # scdet no decide ya la segmentación
        ventanas, cortes = av.planificar(self.medidas, 3,
            [dict(fotograma=10, t=1.5, detectores=['adaptativo'], metricas={})])
        self.assertEqual(len(cortes), 1)
        self.assertEqual([(v['t_in'], v['t_out']) for v in ventanas], [(0, 1.5), (1.5, 3)])
        self.assertEqual(ventanas[0]['contexto_transicion'], [10, 11])
        self.assertEqual(ventanas[1]['contexto_transicion'], [8, 9])
        self.assertTrue(all(len(v['fotogramas']) + len(v['contexto_transicion']) <= av.FRAMES_VENTANA for v in ventanas))
        sin_cortes, _ = av.planificar(self.medidas, 3, [])
        self.assertEqual(len(sin_cortes), 1)

    def test_contrato_incluye_codigo_requisitos_y_configuracion(self):
        original = de.contrato()
        with patch.object(de, 'CONFIGURACION', dict(de.CONFIGURACION, resolucion=[640, 360])):
            self.assertNotEqual(original, de.contrato())
        self.assertEqual(len(original['codigo']), 64)


@unittest.skipUnless(REAL, '--real instala PySceneDetect local y usa FFmpeg; no llama a IA')
class VideosReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='escenas_reales_')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.raiz = Path(cls.tmp.name)
        cls.motor = de.preparar_motor(cls.raiz, lambda *a: None)

    def analizar(self, fuente, nombre, duracion):
        import subprocess
        from pasos import medios, estilos_ia
        destino = self.raiz / nombre
        destino.mkdir()
        video = destino / 'referencia.mkv'
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i', fuente,
            '-c:v', 'ffv1', '-fps_mode', 'passthrough', str(video)], check=True, capture_output=True, timeout=60)
        with patch.object(de, 'preparar_motor', return_value=self.motor):
            estilos_ia.extraer(destino, dict(referencia=video.name), lambda *a: None)
        indice = leer_json(str(destino / 'analisis_visual' / 'indice.json'))
        self.assertAlmostEqual(indice['duracion_s'], duracion, delta=.11)
        with (destino / 'analisis_visual' / 'metricas_escenas.csv').open(encoding='utf-8') as archivo:
            self.assertEqual(len(list(csv.DictReader(archivo))), indice['fotogramas_decodificados'])
        self.assertEqual(indice['segmentacion']['fotogramas_procesados'], indice['fotogramas_decodificados'])
        return indice

    def test_cortes_en_todo_el_video_incluido_un_plano_muy_corto(self):
        fuente = ('color=red:s=320x180:r=10:d=1[r];color=blue:s=320x180:r=10:d=0.3[b];'
                  'color=green:s=320x180:r=10:d=1.7[g];[r][b][g]concat=n=3:v=1:a=0')
        indice = self.analizar(fuente, 'cortes', 3)
        self.assertEqual(indice['fotogramas_decodificados'], 30)
        self.assertEqual([c['fotograma'] for c in indice['cortes']], [10, 13])
        self.assertEqual(indice['planos_detectados'], 3)
        self.assertTrue(all('adaptativo' in c['detectores'] for c in indice['cortes']))

    def test_fundido_negro_se_detecta_sin_corte_brusco(self):
        fuente = ('color=red:s=320x180:r=20:d=2,fade=t=out:st=1:d=1[a];'
                  'color=blue:s=320x180:r=20:d=2,fade=t=in:st=0:d=1[b];[a][b]concat=n=2:v=1:a=0')
        indice = self.analizar(fuente, 'fundido', 4)
        negros = [c for c in indice['cortes'] if 'fundido_negro' in c['detectores']]
        self.assertEqual(len(negros), 1)
        self.assertAlmostEqual(negros[0]['t'], 2, delta=.25)

    def test_fundido_blanco_y_plano_blanco_no_inventan_cortes(self):
        fuente = ('color=blue:s=320x180:r=20:d=2,fade=t=out:st=1:d=1:color=white[a];'
                  'color=red:s=320x180:r=20:d=2,fade=t=in:st=0:d=1:color=white[b];[a][b]concat=n=2:v=1:a=0')
        indice = self.analizar(fuente, 'blanco', 4)
        blancos = [c for c in indice['cortes'] if 'fundido_blanco' in c['detectores']]
        self.assertEqual(len(blancos), 1)
        self.assertAlmostEqual(blancos[0]['t'], 2, delta=.25)
        liso = self.analizar('color=white:s=320x180:r=10:d=1', 'blanco_liso', 1)
        self.assertEqual(liso['cortes'], [])

    def test_frecuencia_variable_conserva_tiempos_y_todos_los_frames(self):
        fuente = ('color=red:s=320x180:r=10:d=1[r];color=blue:s=320x180:r=20:d=1[b];'
                  '[r][b]concat=n=2:v=1:a=0')
        indice = self.analizar(fuente, 'vfr', 2)
        self.assertEqual(indice['fotogramas_decodificados'], 30)
        self.assertEqual([c['fotograma'] for c in indice['cortes']], [10])
        self.assertAlmostEqual(indice['cortes'][0]['t'], 1, delta=.01)

    def test_movimiento_continuo_no_se_convierte_en_multitud_de_planos(self):
        indice = self.analizar('testsrc2=s=320x180:r=20:d=3', 'movimiento', 3)
        self.assertEqual(indice['fotogramas_decodificados'], 60)
        self.assertEqual(indice['cortes'], [])

    def test_cinco_minutos_cubiertos_hasta_el_ultimo_fotograma(self):
        fuente = ('color=red:s=320x180:r=6:d=90[r];color=blue:s=320x180:r=6:d=90[b];'
                  'color=green:s=320x180:r=6:d=119[g];color=yellow:s=320x180:r=6:d=1[y];'
                  '[r][b][g][y]concat=n=4:v=1:a=0')
        indice = self.analizar(fuente, 'cinco_minutos', 300)
        self.assertEqual(indice['fotogramas_decodificados'], 1800)
        self.assertEqual([c['t'] for c in indice['cortes']], [90, 180, 299])
        ventanas = indice['ventanas']
        self.assertEqual(ventanas[0]['t_in'], 0)
        self.assertEqual(ventanas[-1]['t_out'], 300)
        self.assertTrue(all(a['t_out'] == b['t_in'] for a, b in zip(ventanas, ventanas[1:])))
        self.assertEqual(indice['fotogramas'][-1]['n'], 1799)


if __name__ == '__main__':
    unittest.main()
