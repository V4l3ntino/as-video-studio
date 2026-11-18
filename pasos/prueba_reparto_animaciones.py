"""Reparto real de dirección por escenas; sin proveedores ni generación pagada."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_reparto_animaciones_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS', 'ESTUDIO_COSTE_GLOBAL',
              'ESTUDIO_BITACORA_GLOBAL', 'ESTUDIO_PROYECTOS', 'ESTUDIO_PRESETS', 'ESTUDIO_ESTILOS_IA'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import Proyecto, escribir_json
from pasos import reparto_animaciones as reparto, espacio_estilo as espacio, cli_claude


class Reparto(unittest.TestCase):
    def test_extremos_redondeo_y_validacion(self):
        escenas = [dict(id=f'S{i:03d}') for i in range(5)]
        self.assertEqual(set(reparto.proveedores(escenas, {}).values()), {'Claude'})
        for carga, gpt in ((0, 5), (100, 0), (50, 2), (30, 3)):
            asignadas = reparto.proveedores(escenas, dict(reparto_animaciones=dict(carga_claude=carga)))
            self.assertEqual(sum(p == 'ChatGPT' for p in asignadas.values()), gpt)
        for valor in (True, 30.5, -1, 101, '50', None):
            with self.assertRaises(ValueError): reparto.normalizar(dict(carga_claude=valor))
        for valor in ({}, dict(otro=5), '50'):
            with self.assertRaises(ValueError): reparto.normalizar(valor)
        self.assertIsNone(reparto.normalizar(None))

    def test_direccion_chatgpt_no_llama_a_claude_ni_cambia_narracion(self):
        from motores.imagen_openai import codex
        pedido = dict(escena=dict(id='S001', narracion='Texto inmutable.'), duracion=3)
        original = copy.deepcopy(pedido)
        paquete = dict(direccion='Elige velocidad y cámara.', parametros=dict(velocidad=1))
        with patch.object(codex, 'texto', return_value='{"velocidad":0.5}') as gpt, \
                patch.object(cli_claude, 'ejecutar') as claude:
            self.assertEqual(espacio.dirigir(Path(_DATOS.name), pedido, paquete, lambda *a: None,
                proveedor='ChatGPT'), dict(velocidad=.5))
        claude.assert_not_called()
        self.assertIn('Texto inmutable.', gpt.call_args.args[0])
        self.assertEqual(pedido, original)
        with patch.object(codex, 'texto', side_effect=RuntimeError('cuota')), patch.object(cli_claude, 'ejecutar') as claude:
            with self.assertRaises(RuntimeError): espacio.dirigir(Path(_DATOS.name), pedido, paquete,
                lambda *a: None, proveedor='ChatGPT')
        claude.assert_not_called()

    def test_motor_reparte_escenas_y_reutiliza_clips_validos_al_cambiar_porcentaje(self):
        with tempfile.TemporaryDirectory(dir=_DATOS.name) as tmp:
            proyecto = Proyecto.crear(tmp, 'Reparto real')
            trabajo = Path(proyecto.ruta_trabajo('assets'))
            (trabajo / 'escenas').mkdir()
            motor = Path(tmp) / 'motor'
            motor.mkdir()
            escribir_json(str(motor / 'paquete.json'), {})
            escenas = [dict(id=f'S{i:03d}', t_in=i * 3, t_out=(i + 1) * 3,
                narracion=f'Frase {i}.', prompt=f'Escena {i}.') for i in range(5)]
            for e in escenas:
                (trabajo / 'escenas' / (e['id'] + '.png')).write_bytes(b'imagen sin generar')
            unidades = {'escena:' + e['id']: dict(png='escenas/' + e['id'] + '.png') for e in escenas}
            resultado = dict(plan=dict(escenas=escenas, resolucion=[160, 90], fps=12), unidades=unidades)
            params = dict(estilo=dict(espacio_ia=dict(huella='b' * 64)), reparto_animaciones=dict(carga_claude=50))
            def renderizar(base, pedido, salida, *args):
                salida = Path(salida)
                (salida / 'clip.mp4').write_bytes(b'clip local')
                (salida / 'poster.png').write_bytes(b'poster local')
                return dict(clip=salida / 'clip.mp4', poster=salida / 'poster.png', audio=None)
            with patch.object(espacio, 'espacio_del_video', return_value=motor), \
                    patch.object(espacio, 'validar', return_value=dict(direccion='Elige', parametros={})), \
                    patch.object(espacio, 'dirigir', return_value={}) as dirigir, \
                    patch.object(espacio, 'renderizar', side_effect=renderizar):
                listo = espacio.animar_resultado(proyecto, params, copy.deepcopy(resultado), lambda *a: None)
                self.assertEqual([c.kwargs['proveedor'] for c in dirigir.call_args_list], ['Claude'] * 3 + ['ChatGPT'] * 2)
                dirigir.reset_mock()
                espacio.animar_resultado(proyecto, dict(params, reparto_animaciones=dict(carga_claude=0)),
                    copy.deepcopy(resultado), lambda *a: None)
                dirigir.assert_not_called()
                solo_ultima = copy.deepcopy(resultado)
                solo_ultima['unidades'] = {'escena:S004': unidades['escena:S004']}
                espacio.animar_resultado(proyecto, params, solo_ultima, lambda *a: None, rehacer=True)
                self.assertEqual(dirigir.call_count, 1)
                self.assertEqual(dirigir.call_args.kwargs['proveedor'], 'ChatGPT')
            self.assertEqual(listo['unidades']['escena:S004']['animacion_estilo']['proveedor'], 'ChatGPT')

    def test_api_rechaza_repartos_invalidos_antes_de_guardar(self):
        import app
        for valor in (dict(carga_claude=-1), dict(carga_claude='50'), dict(carga_claude=True)):
            with self.assertRaises(app.ErrorApi):
                app._validar_params('assets', dict(reparto_animaciones=valor))
        app._validar_params('assets', dict(reparto_animaciones=dict(carga_claude=30)))

    def test_direccion_previa_respeta_chatgpt_al_100_y_no_consulta_claude(self):
        from pasos import direccion
        from motores.imagen_openai import codex
        escena = dict(id='S001', narracion='Una persona abre la ventana.', personajes=[], t_in=0, t_out=3)
        with patch.object(codex, 'texto', return_value='{"S001":"A person opens a window."}') as gpt, \
                patch.object(direccion, '_llamar_claude') as claude:
            ficha = direccion.proponer([escena], proveedor='ChatGPT')
        claude.assert_not_called()
        self.assertEqual(ficha['dirigidos'], 1)
        self.assertIn('Una persona abre la ventana.', gpt.call_args.args[0])

    def test_cadena_reparte_direccion_previa_y_no_pierde_la_parte_completada(self):
        import app
        from pasos import direccion
        from unittest.mock import Mock
        escenas = [dict(id=f'S{i:03d}', narracion='Frase.', t_in=i, t_out=i + 1) for i in range(4)]
        ctx = SimpleNamespace(id='prueba', proyecto=SimpleNamespace(id='prueba'), estado=Mock(), bitacora=Mock())
        ctx.estado.params.return_value = dict(reparto_animaciones=dict(carga_claude=50))
        def proponer(escenas, **opciones):
            if opciones['proveedor'] == 'ChatGPT':
                raise RuntimeError('cuota del segundo proveedor')
            return dict(plan={e['id']: 'Dirección propia.' for e in escenas}, planos=len(escenas), dirigidos=len(escenas))
        with patch.object(app, '_direccion', return_value=direccion), \
                patch.object(app, '_plan_de_planos', return_value=dict(escenas=escenas)), \
                patch.object(app, '_plan_de_direccion', return_value={}), \
                patch.object(app, '_idioma_del_video', return_value='es'), \
                patch.object(app, '_guardar_direccion_por_unidad') as guardar, \
                patch.object(direccion, 'proponer', side_effect=proponer) as modelo:
            with self.assertRaisesRegex(RuntimeError, 'cuota del segundo'):
                app._correr_direccion(lambda *a: None, ctx, {}, aplicar=True)
        self.assertEqual([c.kwargs['proveedor'] for c in modelo.call_args_list], ['Claude', 'ChatGPT'])
        self.assertEqual(len(modelo.call_args.kwargs['contexto']), 4)
        self.assertEqual(set(guardar.call_args.args[1]), {'S000', 'S001'})

    def test_cadena_con_claude_cero_no_lo_llama_en_la_fase_previa(self):
        import app
        from pasos import direccion
        from unittest.mock import Mock
        escenas = [dict(id='S001', narracion='Frase.', t_in=0, t_out=3)]
        ctx = SimpleNamespace(id='prueba', proyecto=SimpleNamespace(id='prueba'), estado=Mock(), bitacora=Mock())
        ctx.estado.params.return_value = dict(reparto_animaciones=dict(carga_claude=0))
        with patch.object(app, '_direccion', return_value=direccion), \
                patch.object(app, '_plan_de_planos', return_value=dict(escenas=escenas)), \
                patch.object(app, '_plan_de_direccion', return_value={}), \
                patch.object(app, '_idioma_del_video', return_value='es'), \
                patch.object(direccion, 'proponer', return_value=dict(plan={'S001': 'Una acción.'}, planos=1, dirigidos=1)) as modelo:
            app._correr_direccion(lambda *a: None, ctx, {})
        self.assertEqual(modelo.call_count, 1)
        self.assertEqual(modelo.call_args.kwargs['proveedor'], 'ChatGPT')


if __name__ == '__main__':
    unittest.main()
