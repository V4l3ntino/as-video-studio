"""Contratos offline y render real opcional: python pasos/prueba_stickman.py --real."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix='prueba_stickman_')
for clave in ('ESTUDIO_ESTADISTICAS', 'ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_PRESETS', 'ESTUDIO_BANCO_PRESETS'):
    os.environ[clave] = str(Path(TEMP.name) / clave)
os.environ['ESTUDIO_SIMULAR'] = '1'

from nucleo.proyecto import Proyecto
from nucleo.estado import Estado
from pasos import stickman, medios, personajes, presets_canal, presets_light, sonido, editor_escena

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


class Stickman(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEMP.name)
        self.addCleanup(self.temp.cleanup)
        self.base = stickman.familias()[0]
        self.config = dict(seleccionada=0, variantes=stickman.familias())

    def test_estilo_viaja_por_preset_y_no_modifica_historicos(self):
        cambios = presets_canal.cambios_para(dict(tipo='estilo', datos=dict(stickman=self.config)))
        self.assertEqual(cambios['assets']['estilo']['stickman'], self.config)
        reconstruida = presets_canal.datos_de_params(cambios)
        self.assertEqual(reconstruida['estilo']['stickman'], self.config)
        viejo = dict(assets=dict(estilo=dict(prompt='mi estilo')))
        antes = copy.deepcopy(viejo)
        presets_canal.datos_de_params(viejo)
        self.assertEqual(viejo, antes)
        e = presets_light.validar_encargo(dict(nombre='Stickman', idioma='es', tono_prompt='Cercano y educativo',
            stickman=self.config, montaje=dict(incorporar_voz=False)))
        self.assertTrue(e['montaje']['generar_personajes'])
        self.assertEqual(presets_light.plan_de(e)['imagenes'], 0)

    def test_rechaza_datos_que_no_se_pueden_animar(self):
        for datos in (dict(self.base, familia='foto'), dict(self.base, altura=float('nan')),
                      dict(self.base, color='url(x)'), dict(self.base, cabeza=30)):
            with self.assertRaises(ValueError):
                stickman.variante(datos)
        with self.assertRaises(ValueError):
            stickman.escena(dict(personajes=[dict(id='inventado')]), 2, {'real': self.base})
        with self.assertRaises(ValueError):
            stickman.escena(dict(sfx=[dict(name='pop', at=4)]), 2, {'real': self.base})

    def test_corrige_contrato_sin_reintentar_cancelaciones_o_cuota(self):
        validar = lambda d: stickman.escena(d, 2, {'real': self.base})
        with patch.object(stickman, '_consultar', side_effect=[dict(personajes=[dict(id='inexistente')]),
                dict(personajes=[dict(id='real')])]) as consulta:
            resultado = stickman.consultar('encargo', validar=validar)
            self.assertEqual(consulta.call_count, 2)
            self.assertEqual(resultado['personajes'][0]['id'], 'real')
        with patch.object(stickman, '_consultar', side_effect=RuntimeError('cancelado')) as consulta:
            with self.assertRaisesRegex(RuntimeError, 'cancelado'):
                stickman.consultar('encargo', validar=validar)
            self.assertEqual(consulta.call_count, 1)

    def test_personajes_no_admiten_pov_ni_foto_con_diseno_inventado(self):
        p = Proyecto.crear(self.temp.name, 'Personaje')
        f = dict(id='ana', nombre='Ana', descripcion='Profesora', categoria='personaje',
                 imagen='medios_usuario/animaciones/' + 'a' * 32 + '.png', stickman=self.base)
        from PIL import Image
        destino = Path(p.ruta(f['imagen']))
        destino.parent.mkdir(parents=True)
        Image.new('RGB', (32, 32)).save(destino)
        with self.assertRaises(ValueError):
            personajes.normalizar(dict(activo=True, items=[f]), p)
        medios.escribir_json(str(destino) + '.json', dict(stickman=self.base))
        normal = personajes.normalizar(dict(activo=True, items=[f]), p)
        self.assertEqual(normal['items'][0]['stickman'], self.base)
        with self.assertRaises(ValueError):
            personajes.normalizar(dict(activo=True, items=[dict(f, primera_persona=True)]), p)
        self.assertIsNone(personajes.personaje_pov(dict(sistema_personajes=dict(stickman=True, generar_personajes=True),
            personajes=dict(activo=True, items=[dict(f, primera_persona=True)]))))

    def test_sonidos_del_plugin_se_editan_y_se_mezclan_una_vez(self):
        contenido = stickman.escena(dict(sfx=[dict(name='pop', at=.2, dur=.12, gain=-12),
            dict(name='roomtone', at=0, dur=1, gain=-26)]), 1, {'ana': self.base})
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        e = dict(id='S001', t_in=3, t_out=4, narracion='Ana saluda.', sonidos_stickman=[
            dict(r, archivo=str(Path(self.temp.name) / r['archivo'])) for r in recursos])
        eventos = sonido.eventos([e], {}, {})
        self.assertEqual(len(eventos), 2)
        self.assertAlmostEqual(eventos[0]['t'], 0)
        fuentes, actual = sonido.bloques_de_escena([e], {}, {}, 'S001')
        self.assertIsNone(actual)
        self.assertEqual({f['nombre'] for f in fuentes}, {'pop', 'roomtone'})
        from pasos import animaciones
        ajuste = dict(ancla=animaciones.ancla_de(e), bloques=[dict(id='stickman:0', inicio=.5, fin=.6)])
        # El editor admite los mismos IDs que la pista de sonido del montaje.
        editor_escena.validar(dict(sonidos=ajuste), e, [1920, 1080])
        manual = sonido.eventos([e], {}, dict(unidades={'escena:S001': dict(sonidos=ajuste)}))
        self.assertEqual(len(manual), 1)
        self.assertAlmostEqual(manual[0]['t'], .5)
        salida = str(Path(self.temp.name) / 'efectos.wav')
        sonido.pista_de_efectos(eventos, 1, salida, igualar=False)
        from scipy.io import wavfile
        _, pcm = wavfile.read(salida)
        self.assertGreater(abs(pcm).max(), 0)

    def test_todos_los_efectos_del_plugin_admiten_recortes_cortos(self):
        contenido = dict(sfx=[dict(name=n, dur=.1, at=0, gain=-20, seed=1, pitch=1) for n in stickman.EFECTOS])
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        self.assertEqual(len(recursos), len(stickman.EFECTOS))
        self.assertTrue(all((Path(self.temp.name) / r['archivo']).is_file() for r in recursos))

    def test_recurso_versionado_se_resuelve_tras_completar_y_no_por_id_solo(self):
        p = Proyecto.crear(self.temp.name, 'Recursos')
        estado = Estado(p)
        trabajo = Path(p.ruta_trabajo('assets'))
        (trabajo / 'escenas').mkdir()
        (trabajo / 'escenas/S001.mp4').write_bytes(b'clip')
        medios.escribir_json(str(trabajo / 'escenas/S001.json'), dict(origen='stickman', narracion='Ana saluda.',
            firma_stickman='firma', clip='escenas/S001.mp4', sonidos_stickman=[]))
        plan = dict(estilo=dict(stickman=self.config), escenas=[dict(id='S001', narracion='Ana saluda.')])
        stickman.aplicar_recursos(p, plan)
        self.assertIn('trabajo', plan['escenas'][0]['stickman']['clip'])
        estado.completar('assets', {})
        stickman.aplicar_recursos(p, plan)
        self.assertIn('v1', plan['escenas'][0]['stickman']['clip'])
        plan['escenas'][0]['narracion'] = 'Otro texto.'
        stickman.aplicar_recursos(p, plan)
        self.assertNotIn('stickman', plan['escenas'][0])

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_creacion_y_edicion_del_estilo_conservan_las_referencias(self):
        import app
        app.fijar_raiz_proyectos(self.temp.name)
        encargo = presets_light.validar_encargo(dict(nombre='Estilo completo', idioma='es',
            tono_prompt='Narrativo y cercano.', stickman=self.config, montaje=dict(incorporar_voz=False)))
        ctx = app._crear_taller(encargo)
        app._sembrar_taller(ctx, encargo)
        def tono(avisar, ctx, encargo):
            ctx.estado.actualizar_params('brief', dict(instrucciones=encargo['tono_prompt']))
        with patch.dict(app._LIGHT_QUE_HACE, tono=tono):
            resultado = app._correr_preset_light(lambda *a: None, ctx, encargo, None, None)
        preset = presets_canal.leer(resultado['preset'])
        anteriores = preset['datos']['estilo']['referencias']
        config = dict(self.config, seleccionada=2)
        editado = app.editar_preset_light(preset['id'], dict(stickman=config))['preset']
        self.assertEqual(editado['datos']['estilo']['stickman']['seleccionada'], 2)
        self.assertTrue(all(Path(r).is_file() for r in anteriores))
        self.assertTrue(all(Path(r).is_file() for r in editado['datos']['estilo']['referencias']))

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_pipeline_interrumpido_retoma_y_monta_con_los_sonidos(self):
        from pasos import p6_assets, p7_callouts, p8_render
        import wave
        p = Proyecto.crear(self.temp.name, 'Pipeline')
        estado = Estado(p)
        voz = Path(p.ruta_trabajo('voz'))
        with wave.open(str(voz / 'narracion.wav'), 'wb') as wav:
            wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0' * (2 * 48000 * 4))
        estado.completar('voz', dict(wav='narracion.wav'))
        params = dict(estilo=dict(stickman=self.config), generar_personajes=True)
        estado.actualizar_params('assets', params)
        escenas = [dict(id=f'S00{i+1}', narracion=t, t_in=i, t_out=i+1, duracion=1,
                       marcas=[[i+.1, i+.8]], personajes=[], transicion='corte')
                   for i, t in enumerate(['Ana saluda.', 'Ana señala.'])]
        plan = dict(estilo=params['estilo'], escenas=escenas, assets={}, dependencias={e['id']: [] for e in escenas},
            conservacion=dict(retirados=[]), resolucion=[320, 180], generacion=[320, 180],
            duracion_total=2, idioma='es', semilla=7, fps=30, formato='horizontal')
        contenido = stickman.escena(dict(personajes=[dict(id='protagonista')],
            sfx=[dict(name='pop', at=.3, dur=.4, gain=-12)]), 1, {'protagonista': self.base})
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **k: copy.deepcopy(plan)), \
             patch.object(stickman, 'generar_escena', side_effect=[contenido, RuntimeError('interrupción')]):
            with self.assertRaisesRegex(RuntimeError, 'interrupción'):
                p6_assets.ejecutar(p, params)
        parcial = stickman.aplicar_recursos(p, copy.deepcopy(plan))
        self.assertTrue(parcial['escenas'][0].get('stickman'))
        self.assertFalse(parcial['escenas'][1].get('stickman'))
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **k: copy.deepcopy(plan)), \
             patch.object(stickman, 'generar_escena', return_value=contenido) as generar:
            resultado = p6_assets.ejecutar(p, params)
            self.assertEqual(generar.call_count, 1)
        estado.completar('assets', resultado['salidas'], resultado['unidades'])
        capas = p7_callouts.ejecutar(p, dict(previsualizar=False, escala_hyper=1))
        estado.completar('callouts', capas['salidas'], capas['unidades'])
        render = p8_render.ejecutar(p, dict(resolucion=[320, 180], fps=12, lotes=1, subtitulos=False))
        final = Path(p.ruta_trabajo('render')) / render['salidas']['mp4']
        self.assertTrue(final.is_file())
        # Narración muda: cualquier energía audible tiene que venir de los efectos.
        audio = subprocess.run([medios.ffmpeg(), '-v', 'error', '-i', str(final), '-f', 'f32le', '-ac', '1', '-'],
            capture_output=True, check=True).stdout
        import numpy as np
        self.assertGreater(np.abs(np.frombuffer(audio, dtype=np.float32)).max(), .001)
        estado.completar('render', render['salidas'], render['unidades'])
        from pasos import paquete_video
        archivo = str(Path(self.temp.name) / 'animacion.video.zip')
        paquete_video.exportar(p, archivo)
        destino = Path(self.temp.name) / 'importados'
        destino.mkdir()
        importado = paquete_video.importar(archivo, str(destino))
        recuperado = stickman.aplicar_recursos(importado, copy.deepcopy(plan))
        for e in recuperado['escenas']:
            self.assertTrue(Path(e['stickman']['clip']).is_relative_to(Path(importado.raiz)))
            self.assertTrue(Path(e['sonidos_stickman'][0]['archivo']).is_file())

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_render_real_familias_y_mp4_con_efectos_del_plugin(self):
        from PIL import Image
        imagenes = []
        for v in stickman.familias():
            png = str(Path(self.temp.name) / (v['familia'] + '.png'))
            stickman.renderizar(v, stickman.muestra(v), 2, png, salida=(320, 180))
            with Image.open(png) as img:
                imagenes.append(img.tobytes())
        self.assertEqual(len(set(imagenes)), 4)
        contenido = stickman.muestra(self.base)
        contenido['sfx'] = [dict(name='pop', at=.3, dur=.5, gain=-10, seed=1, pitch=1)]
        clip = str(Path(self.temp.name) / 'escena.mp4')
        stickman.renderizar(self.base, contenido, 2, str(Path(self.temp.name) / 'poster.png'), clip, salida=(320, 180), fps=12)
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        e = dict(id='S001', t_in=0, t_out=2, sonidos_stickman=[dict(s, archivo=str(Path(self.temp.name) / s['archivo'])) for s in recursos])
        audio = str(Path(self.temp.name) / 'audio.wav')
        sonido.pista_de_efectos(sonido.eventos([e], {}, {}), 2, audio, igualar=False)
        final = str(Path(self.temp.name) / 'final.mp4')
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-i', clip, '-i', audio, '-c:v', 'copy', '-c:a', 'aac', final], check=True)
        r = subprocess.run([medios.ffprobe(), '-v', 'error', '-show_streams', '-of', 'json', final], capture_output=True, text=True, check=True)
        self.assertEqual({s['codec_type'] for s in json.loads(r.stdout)['streams']}, {'video', 'audio'})


if __name__ == '__main__':
    unittest.main()
