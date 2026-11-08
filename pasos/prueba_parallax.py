"""Contrato offline; --real comprueba además DepthFlow y el MP4 con profundidad estimada."""
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
_aislado = tempfile.TemporaryDirectory(prefix="prueba_parallax_")
for variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                 "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[variable] = os.path.join(_aislado.name, variable)

from PIL import Image
from nucleo.proyecto import Proyecto, escribir_json
from nucleo.estado import Estado
from pasos import parallax, clips_parallax, presets_canal, p8_render
from motores import parallax_depthflow

REAL = "--real" in sys.argv
if REAL:
    sys.argv.remove("--real")


class Parallax(unittest.TestCase):
    def test_seleccion_cuenta_imagenes_sin_clips_ni_cartelas_solidas(self):
        escenas = [{"id": str(i)} for i in range(1, 10)]
        escenas.insert(1, {"id": "clip", "medio_usuario": {"tipo": "video"}})
        escenas.insert(3, {"id": "stock", "medio_biblioteca": {"tipo": "video"}})
        with patch("pasos.cartelas.sin_imagen", side_effect=lambda e: e["id"] == "2"):
            self.assertEqual(parallax.seleccionar(escenas, None), {})
            elegidas = parallax.seleccionar(escenas, {"activo": True, "seleccion": "cada"})
            self.assertEqual(list(elegidas), ["4", "7"])
            opciones = {"activo": True, "seleccion": "aleatorias", "movimiento": "aleatorio"}
            copia = copy.deepcopy(escenas)
            a = parallax.seleccionar(escenas, opciones, 17)
            self.assertEqual(a, parallax.seleccionar(escenas, opciones, 17))
            self.assertTrue(0 < len(a) < 8)
            self.assertTrue(all(p["movimiento"] != "aleatorio" for p in a.values()))
            self.assertEqual(escenas, copia)

    def test_validacion_y_herencia_del_estilo_solo_al_render(self):
        for valor in (False, [], {"activo": 1}, {"cada": True}, {"cada": 0},
                      {"cada": 1.5}, {"movimiento": "inventado"}, {"intensidad": "extrema"},
                      {"movimientos": []}, {"movimientos": "lateral"},
                      {"movimientos": ["inventado"]}, {"movimientos": [False]}):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                parallax.normalizar(valor)
        p = parallax.normalizar({"activo": True, "movimiento": "orbita"})
        limpio = presets_canal._limpiar_datos("montaje", {"parallax": p})
        self.assertEqual(presets_canal.cambios_para({"tipo": "montaje", "datos": limpio}),
                         {"render": {"parallax": p}})
        with tempfile.TemporaryDirectory() as tmp:
            estado = Estado(Proyecto.crear(tmp, "Prueba"))
            antes = {paso: estado.firma(paso) for paso in ("voz", "assets", "callouts")}
            estado.actualizar_params("render", {"parallax": p})
            self.assertEqual(antes, {paso: estado.firma(paso) for paso in antes})

    def test_varios_movimientos_se_alternan_solo_entre_los_elegidos(self):
        escenas = [{"id": f"S{i}"} for i in range(1, 31)]
        opciones = {"activo": True, "movimientos": ["lateral", "orbita", "vertical"],
                    "seleccion": "cada", "cada": 2}
        copia = copy.deepcopy(opciones)
        elegidas = parallax.seleccionar(escenas, opciones, 17)
        movimientos = [p["movimiento"] for p in elegidas.values()]
        self.assertEqual(set(movimientos), set(opciones["movimientos"]))
        self.assertTrue(all(a != b for a, b in zip(movimientos, movimientos[1:])))
        self.assertEqual([movimientos.count(m) for m in opciones["movimientos"]], [5, 5, 5])
        self.assertEqual(elegidas, parallax.seleccionar(escenas, opciones, 17))
        opciones["movimientos"].reverse()
        self.assertEqual(movimientos, [p["movimiento"] for p in
            parallax.seleccionar(escenas, opciones, 17).values()])
        opciones["movimientos"].reverse()
        self.assertEqual(opciones, copia)
        con_clip = copy.deepcopy(escenas)
        con_clip.insert(1, {"id": "clip", "medio_biblioteca": {"tipo": "video"}})
        self.assertEqual(elegidas, parallax.seleccionar(con_clip, opciones, 17))
        limpio = presets_canal._limpiar_datos("montaje", {"parallax": opciones})
        self.assertEqual(limpio["parallax"]["movimientos"], opciones["movimientos"])
        self.assertEqual(presets_canal.cambios_para({"tipo": "montaje", "datos": limpio}),
                         {"render": limpio})

    def test_selector_antiguo_conserva_su_movimiento(self):
        escenas = [{"id": f"S{i}"} for i in range(1, 5)]
        for movimiento in parallax.MOVIMIENTOS[:-1]:
            elegidas = parallax.seleccionar(escenas, {"activo": True, "movimiento": movimiento})
            self.assertEqual({p["movimiento"] for p in elegidas.values()}, {movimiento})

    def test_render_envia_solo_las_imagenes_elegidas_a_depthflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = Proyecto.crear(tmp, "Montaje")
            raiz = Path(proyecto.raiz)
            imagen = raiz / "imagen.png"
            Image.new("RGB", (160, 90), "red").save(imagen)
            escenas = [{"id": f"S{i}", "t_in": i-1, "t_out": i, "narracion": "Una frase."}
                       for i in range(1, 4)]
            escenas[1]["medio_biblioteca"] = {"tipo": "video", "archivo": "stock.mp4"}
            plan = raiz / "plan.json"
            movimiento = raiz / "movimiento.json"
            escribir_json(str(plan), {"escenas": escenas, "resolucion": [160, 90]})
            escribir_json(str(movimiento), {"movimientos": [dict(id=e["id"], hyperframe=str(imagen),
                capa="ausente.svg", hyperframe_px=[160, 90], ventana_ini=[0, 0, 1, 1], ventana_fin=[0, 0, 1, 1])
                for e in escenas]})
            tareas = []
            derivado = proyecto.ruta("parallax", "clips", "prueba.mp4")
            Path(derivado).parent.mkdir(parents=True, exist_ok=True)
            Path(derivado).write_bytes(b"clip de prueba")
            def lotes(lista, *args, **kwargs):
                tareas.extend(lista)
                return [{"id": t["id"], "clip": t["clip"], "frames": t["frames"]} for t in lista]
            with patch.object(parallax_depthflow, "generar", return_value=derivado) as generar, \
                 patch.object(p8_render, "correr_lote", side_effect=lotes), \
                 patch.object(p8_render, "_concatenar"), \
                 patch.object(p8_render, "_elegir_codec", return_value="libx264"):
                p8_render.ejecutar(proyecto, {"plan": str(plan), "movimiento": str(movimiento),
                    "sonido": False, "lotes": 1, "fps": 6, "parallax": {"activo": True, "seleccion": "cada", "cada": 2}})
                pedido = clips_parallax.preparar(proyecto, escenas[2], str(imagen),
                    {"movimiento": "zoom_delante", "intensidad": "suave"}, 6)
                self.assertTrue(os.path.samefile(clips_parallax.disponible(proyecto, pedido), derivado))
                self.assertTrue(os.path.samefile(clips_parallax.generar(proyecto, pedido), derivado))
            self.assertEqual(generar.call_count, 1)
            self.assertEqual([t["video"] for t in tareas], [None, "stock.mp4", derivado])

    def test_previa_invalida_clip_si_cambian_imagen_tiempos_o_movimiento(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = Proyecto.crear(tmp, "Previa")
            imagen = proyecto.ruta("imagen.png")
            Image.new("RGB", (160, 90), "red").save(imagen)
            escena = {"id": "S001", "t_in": 0, "t_out": 1}
            opciones = {"movimiento": "lateral", "intensidad": "suave"}
            pedido = clips_parallax.preparar(proyecto, escena, "imagen.png", opciones, 6)
            self.assertFalse(Path(proyecto.ruta("parallax")).exists())
            self.assertIsNone(clips_parallax.disponible(proyecto, pedido))
            otro = clips_parallax.preparar(proyecto, escena, imagen, dict(opciones, movimiento="orbita"), 6)
            self.assertNotEqual(pedido["clave"], otro["clave"])
            otro = clips_parallax.preparar(proyecto, dict(escena, t_out=2), imagen, opciones, 6)
            self.assertNotEqual(pedido["clave"], otro["clave"])
            Image.new("RGB", (160, 90), "blue").save(imagen)
            otro = clips_parallax.preparar(proyecto, escena, imagen, opciones, 6)
            self.assertNotEqual(pedido["clave"], otro["clave"])

    def test_parar_mata_el_motor_y_no_publica_un_clip_incompleto(self):
        with tempfile.TemporaryDirectory() as tmp:
            imagen = os.path.join(tmp, "imagen.png")
            Image.new("RGB", (32, 32), "red").save(imagen)
            def parar():
                raise InterruptedError("Parado")
            with patch.object(parallax_depthflow.subprocess, "Popen") as lanzar:
                proceso = lanzar.return_value
                proceso.wait.side_effect = [subprocess.TimeoutExpired("depthflow", 1), 0]
                proceso.poll.return_value = None
                with self.assertRaises(InterruptedError):
                    parallax_depthflow.generar(imagen, tmp, parallax.normalizar(), 1, 6,
                                               [32, 32], latido=parar)
                proceso.kill.assert_called_once()
            self.assertEqual(list(Path(tmp).glob("*.mp4")), [])

    @unittest.skipUnless(REAL, "usar --real para estimar profundidad y renderizar con DepthFlow")
    def test_motor_real_movimiento_duracion_y_cache(self):
        from pasos._proyecto_animaciones import _imagen
        with tempfile.TemporaryDirectory() as tmp:
            imagen = os.path.join(tmp, "paisaje.png")
            _imagen(imagen, 0)
            p = parallax.normalizar({"activo": True, "movimiento": "lateral"})
            ruta = parallax_depthflow.generar(imagen, tmp, p, 1, 6, [160, 90])
            info = json.loads(subprocess.check_output([p8_render.medios.ffprobe(), "-v", "error",
                "-show_streams", "-of", "json", ruta]))["streams"][0]
            self.assertEqual((info["width"], info["height"]), (160, 90))
            self.assertAlmostEqual(float(info["duration"]), 1, places=2)
            fecha = os.stat(ruta).st_mtime_ns
            self.assertEqual(ruta, parallax_depthflow.generar(imagen, tmp, p, 1, 6, [160, 90]))
            self.assertEqual(os.stat(ruta).st_mtime_ns, fecha)
            frames = p8_render._fotogramas_de_clip(ruta, tmp, {"hyperframe_px": [160, 90]}, 6, 6)
            self.assertNotEqual(Path(frames[0]).read_bytes(), Path(frames[-1]).read_bytes())


if __name__ == "__main__":
    unittest.main()
