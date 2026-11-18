"""Whisper por estilo: contratos sin red; --real descarga y reconoce una voz real."""
import copy
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_transcripcion_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_PRESETS',
              'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_ESTILOS_IA', 'ESTUDIO_PROYECTOS', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import transcripcion_estilo as voz, estilos_ia as ia, espacio_estilo

TEXTO = 'Hola, este es el guion del vídeo.'
TRANSCRIPCION = dict(origen='whisper', motor='faster-whisper', modelo='small', idioma='es', estado='transcrito',
    probabilidad_idioma=.99, duracion_s=2, texto=TEXTO,
    segmentos=[dict(t_in=0, t_out=1.8, texto=TEXTO, palabras=[dict(texto='Hola,', t_in=0, t_out=.3, probabilidad=.95)])])


class Transcripcion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destino = Path(self.tmp.name)
        (self.destino / 'referencia.mkv').write_bytes(b'video de prueba')
        self.ficha = dict(referencia='referencia.mkv', transcripcion='')
        self.metadatos = dict(duracion_s=2, tiene_audio=True)
        self.entorno = patch.dict(os.environ, ESTUDIO_WHISPER_MODELO='small')
        self.entorno.start(); self.addCleanup(self.entorno.stop)

    def extraer(self, orden, *args, **kwargs):
        self.assertIn('16000', orden)
        self.assertIn('0:a:0', orden)
        Path(orden[-1]).write_bytes(b'audio PCM simulado')

    def obtener(self):
        with patch.object(espacio_estilo, 'correr', side_effect=self.extraer), \
                patch.object(voz, 'preparar_motor', return_value=self.destino / 'motor'), \
                patch.object(voz, 'reconocer', return_value=copy.deepcopy(TRANSCRIPCION)) as reconocer:
            dato = voz.obtener(self.destino, self.ficha, self.metadatos, lambda *a: None)
        return dato, reconocer

    def test_automatico_sin_texto_manual_guarda_palabras_y_tiempos(self):
        dato, reconocer = self.obtener()
        self.assertEqual(dato['texto'], TEXTO)
        self.assertEqual(dato['origen'], 'whisper')
        self.assertEqual(dato['segmentos'][0]['t_out'], 1.8)
        self.assertEqual(reconocer.call_args.args[2], 'small')
        self.assertEqual(voz.leer(self.destino)['texto'], TEXTO)
        self.assertEqual(voz.resumen(dato)['idioma'], 'es')

    def test_cache_no_vuelve_a_extraer_instalar_ni_transcribir(self):
        anterior, _ = self.obtener()
        with patch.object(espacio_estilo, 'correr', side_effect=AssertionError('no extraer')), \
                patch.object(voz, 'preparar_motor', side_effect=AssertionError('no instalar')), \
                patch.object(voz, 'reconocer', side_effect=AssertionError('no transcribir')):
            self.assertEqual(voz.obtener(self.destino, self.ficha, self.metadatos, lambda *a: None), anterior)

    def test_audio_cambiado_invalida_la_cache(self):
        anterior, _ = self.obtener()
        (self.destino / 'referencia.mkv').write_bytes(b'otro video')
        nueva, reconocer = self.obtener()
        self.assertNotEqual(nueva['firma'], anterior['firma'])
        reconocer.assert_called_once()

    def test_sin_pista_no_descarga_whisper(self):
        with patch.object(voz, 'preparar_motor', side_effect=AssertionError('no instalar')), \
                patch.object(voz, 'reconocer', side_effect=AssertionError('no reconocer')):
            dato = voz.obtener(self.destino, self.ficha, dict(self.metadatos, tiene_audio=False), lambda *a: None)
        self.assertEqual(dato['origen'], 'sin_audio')
        self.assertEqual(dato['texto'], '')

    def test_texto_manual_sustituye_whisper_sin_instalarlo(self):
        with patch.object(voz, 'preparar_motor', side_effect=AssertionError('no instalar')):
            dato = voz.obtener(self.destino, dict(self.ficha, transcripcion='Texto revisado.'), self.metadatos, lambda *a: None)
        self.assertEqual(dato['origen'], 'manual')
        self.assertEqual(dato['texto'], 'Texto revisado.')

    def test_silencio_no_se_convierte_en_palabras(self):
        with patch.object(espacio_estilo, 'correr', side_effect=self.extraer), \
                patch.object(voz, 'preparar_motor', return_value=self.destino / 'motor'), \
                patch.object(voz, 'reconocer', return_value=dict(TRANSCRIPCION, texto='', segmentos=[], estado='sin_habla', idioma=None)):
            dato = voz.obtener(self.destino, self.ficha, self.metadatos, lambda *a: None)
        self.assertEqual(dato['estado'], 'sin_habla')
        self.assertEqual(dato['texto'], '')

    def test_cancelar_no_publica_transcripcion_incompleta(self):
        with patch.object(espacio_estilo, 'correr', side_effect=self.extraer), \
                patch.object(voz, 'preparar_motor', return_value=self.destino / 'motor'), \
                patch.object(voz, 'reconocer', side_effect=Cancelado()), self.assertRaises(Cancelado):
            voz.obtener(self.destino, self.ficha, self.metadatos, lambda *a: None)
        self.assertIsNone(voz.leer(self.destino))

    def test_segmentos_invalidos_no_se_guardan(self):
        for cambio in (dict(segmentos=[dict(t_in=0, t_out=3, texto=TEXTO)]),
                       dict(segmentos=[dict(t_in=float('nan'), t_out=1, texto=TEXTO)]),
                       dict(texto='Texto que no corresponde a los segmentos.')):
            with self.assertRaises(ValueError): voz.validar(dict(TRANSCRIPCION, **cambio))

    def test_dependencias_y_modelos_son_locales(self):
        with patch.object(espacio_estilo, 'instalar') as instalar, patch.object(espacio_estilo, 'fijar_requisitos'):
            base = voz.preparar_motor(self.destino, lambda *a: None)
        self.assertTrue(base.is_relative_to(self.destino))
        self.assertIn('faster-whisper==1.2.1', (base / 'requisitos' / 'requirements.txt').read_text())
        self.assertEqual(instalar.call_args.args[0], base)
        codigo = (base / 'transcribir.py').read_text(encoding='utf-8')
        self.assertIn("device='cpu', compute_type='int8'", codigo)
        self.assertIn("base / 'modelos'", codigo)

    def test_analisis_recibe_transcripcion_antes_de_consultar(self):
        raiz = self.destino / 'proyectos'
        with patch.dict(os.environ, ESTUDIO_ESTILOS_IA=str(self.destino / 'estilos')):
            ficha = ia.crear(str(raiz), io.BytesIO(b'video'), 'entrada.mkv', 'Automático')
            with patch.object(ia, 'extraer', return_value=(self.metadatos, [])), \
                    patch.object(voz, 'obtener', return_value=copy.deepcopy(TRANSCRIPCION)), \
                    patch.object(ia, 'consultar', return_value={'resumen': 'Analizado'}) as consulta:
                ia.analizar(lambda *a: None, str(raiz), ficha['id'])
            self.assertEqual(consulta.call_args.args[1]['_transcripcion']['texto'], TEXTO)
            guardada = ia.leer(str(raiz), ficha['id'])
            self.assertEqual(guardada['transcripcion_info']['origen'], 'whisper')
            self.assertEqual(guardada['transcripcion'], '')  # no convertir automático en override manual
            with patch.object(ia, 'extraer', return_value=(self.metadatos, [])), \
                    patch.object(voz, 'obtener', side_effect=ValueError('Whisper falló')), \
                    patch.object(ia, 'consultar') as consulta, self.assertRaises(ValueError):
                ia.analizar(lambda *a: None, str(raiz), ficha['id'])
            consulta.assert_not_called()
            self.assertEqual(ia.leer(str(raiz), ficha['id'])['estado'], 'error')

    def test_no_corrige_transcripcion_de_una_version_publicada(self):
        with patch.dict(os.environ, ESTUDIO_ESTILOS_IA=str(self.destino / 'estilos')):
            ficha = ia.crear(str(self.destino), io.BytesIO(b'video'), 'entrada.mkv', 'Publicado')
            ruta = ia.carpeta(str(self.destino), ficha['id']) / 'estilo.json'
            escribir_json(str(ruta), dict(ficha, preset_id='publicado'))
            with self.assertRaises(ValueError): ia.corregir_transcripcion(str(self.destino), ficha['id'], 'No cambiar')
            self.assertEqual(leer_json(str(ruta))['transcripcion'], '')

    def test_transcripcion_se_conserva_en_el_manifiesto(self):
        dato, _ = self.obtener()
        manifiesto = {}
        ia._incluir_transcripcion(self.destino, manifiesto)
        self.assertEqual(manifiesto['transcripcion']['texto'], dato['texto'])
        self.assertEqual(manifiesto['transcripcion']['segmentos'], dato['segmentos'])

    def test_api_permite_revisar_y_corregir_sin_modelos_ni_proveedores(self):
        import app
        raiz = str(self.destino / 'proyectos')
        with patch.dict(os.environ, ESTUDIO_ESTILOS_IA=str(self.destino / 'estilos')), \
                patch.object(app, 'raiz_proyectos', return_value=raiz):
            ficha = ia.crear(raiz, io.BytesIO(b'video'), 'entrada.mkv', 'Revisión')
            destino = ia.carpeta(raiz, ficha['id'])
            escribir_json(str(destino / 'transcripcion' / 'resultado.json'), TRANSCRIPCION)
            self.assertEqual(app.transcripcion_estilo_ia(ficha['id'])['transcripcion']['texto'], TEXTO)
            with patch.object(app.TRABAJOS_ESTILOS_IA, 'listar', return_value=[]), \
                    patch.object(app.TRABAJOS_ESTILOS_IA, 'lanzar', return_value='no_ejecutar') as trabajo:
                app.corregir_transcripcion_estilo_ia(ficha['id'], {'texto': 'Texto corregido.'})
            self.assertEqual(ia.leer(raiz, ficha['id'])['transcripcion'], 'Texto corregido.')
            trabajo.assert_called_once()

    @unittest.skipUnless(REAL, '--real descarga dependencias/modelo y un discurso público para reconocerlo localmente')
    def test_whisper_real_reconoce_voz_en_un_mkv(self):
        import subprocess
        import urllib.request
        from pasos import medios
        audio = self.destino / 'jfk.flac'
        urllib.request.urlretrieve('https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac', audio)
        video = self.destino / 'referencia.mkv'
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
            'color=c=black:s=160x90:r=6', '-i', str(audio), '-shortest', '-c:v', 'libx264', '-c:a', 'flac', str(video)],
            check=True, capture_output=True, timeout=60)
        base_preparada = os.environ.get('ESTUDIO_WHISPER_PRUEBA_MOTOR')
        if base_preparada:
            base = Path(base_preparada)
            shutil.copyfile(voz.EJECUTOR, base / 'transcribir.py')
            preparacion = patch.object(voz, 'preparar_motor', return_value=base)
        else:
            from contextlib import nullcontext
            preparacion = nullcontext()
        with patch.dict(os.environ, ESTUDIO_WHISPER_MODELO='tiny'), preparacion:
            dato = voz.obtener(self.destino, self.ficha, dict(duracion_s=11, tiene_audio=True), lambda *a: None)
            self.assertIn('country', dato['texto'].lower())
            self.assertIn('americans', dato['texto'].lower())
            self.assertEqual(dato['idioma'], 'en')
            self.assertTrue(dato['segmentos'])
            with patch.object(voz, 'reconocer', side_effect=AssertionError('debe usar caché')):
                self.assertEqual(voz.obtener(self.destino, self.ficha, dict(duracion_s=11, tiene_audio=True), lambda *a: None)['texto'], dato['texto'])
            print('\nWhisper real:', dato['texto'])


if __name__ == '__main__':
    unittest.main()
