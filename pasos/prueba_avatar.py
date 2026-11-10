"""Contratos offline de Boson, caché y montaje del avatar sin llamadas de pago."""
import io
import copy
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_aislado = tempfile.TemporaryDirectory(prefix="prueba_avatar_")
for variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                 "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[variable] = os.path.join(_aislado.name, variable)

from PIL import Image
from nucleo.proyecto import Proyecto
from nucleo.estado import Estado
from pasos import avatar, claves, imagenes_animacion, medios
from motores import avatar_boson


class Avatar(unittest.TestCase):
    def test_presentacion_valida_intervalos_y_no_reutiliza_ajustes_de_otro_texto(self):
        escena = {"id": "S1", "narracion": "La tesis.", "t_in": 10, "t_out": 12}
        p = {"unidades": {"escena:S1": {"avatar": {"ancla": avatar.ancla_de(escena),
             "presentacion": {"entrada": "fundido", "inicio": .4, "fin": 1.8}}}}}
        self.assertEqual(avatar.presentacion_de(p, escena)["inicio"], .4)
        self.assertEqual(avatar.presentacion_de(p, dict(escena, narracion="Otra tesis."))["inicio"], 0)
        for entrada, inicio, fin in (("inventada", 0, 1), ("fundido", -1, 1), ("fundido", 1, .5),
                                    ("fundido", 0, 3), ("fundido", True, 1), ("fundido", 0, float("nan"))):
            with self.subTest(entrada=entrada, inicio=inicio, fin=fin), self.assertRaises(ValueError):
                avatar.validar_presentacion({"entrada": entrada, "inicio": inicio, "fin": fin}, 2)

    def test_entradas_y_ventana_temporal_renderizan_sin_desplazar_el_video_del_avatar(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Proyecto.crear(tmp, "Entradas")
            clip = p.ruta("colores.mp4")
            subprocess.run([medios.ffmpeg(), "-nostdin", "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=red:s=64x64:r=30:d=1", "-f", "lavfi", "-i", "color=lime:s=64x64:r=30:d=1",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", clip],
                check=True, capture_output=True, **medios.SIN_VENTANA)
            fondo = p.ruta("fondo.png")
            Image.new("RGB", (320, 180), "blue").save(fondo)
            for entrada in avatar.ENTRADAS:
                ruta = avatar.componer(p, clip, fondo, lambda: None, (320, 180), {"x": .2, "y": .2},
                    {"entrada": entrada["id"], "inicio": .4, "fin": 1.7})
                for tiempo, color in ((.2, "blue"), (1.2, "lime"), (1.85, "blue")):
                    frame = subprocess.run([medios.ffmpeg(), "-v", "error", "-ss", str(tiempo), "-i", ruta,
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                        check=True, capture_output=True, **medios.SIN_VENTANA)
                    with Image.open(io.BytesIO(frame.stdout)) as img:
                        r, g, b = img.convert("RGB").getpixel((100, 72))
                        if color == "blue": self.assertGreater(b, r + g + 100, (entrada, tiempo))
                        else: self.assertGreater(g, r + b + 100, (entrada, tiempo))

    def test_posicion_normalizada_limites_y_ancla(self):
        escena = {"id": "S1", "narracion": "La explicación central."}
        p = {"unidades": {"escena:S1": {"avatar": {
            "ancla": avatar.ancla_de(escena), "posicion": {"x": .1, "y": .2}}}}}
        self.assertEqual(avatar.posicion_de(p, escena, (1920, 1080))["x"], .1)
        self.assertAlmostEqual(avatar.posicion_de({}, escena, (1920, 1080))["x"], .73375)
        self.assertAlmostEqual(avatar.posicion_de({}, escena, (1080, 1920))["x"], .55)
        self.assertNotEqual(avatar.posicion_de(p, dict(escena, narracion="Otra frase."), (1920, 1080))["x"], .1)
        for salida in ((1920, 1080), (1080, 1920)):
            cuadro = avatar.geometria(salida)
            limitada = avatar.validar_posicion({"x": 1, "y": 1}, salida)
            self.assertAlmostEqual(limitada["x"] + cuadro["ancho"], 1)
            self.assertAlmostEqual(limitada["y"] + cuadro["alto"], 1)
        for posicion in (None, {}, {"x": True, "y": 0}, {"x": -1, "y": 0},
                         {"x": float("nan"), "y": 0}, {"x": 0, "y": float("inf")}):
            with self.subTest(posicion=posicion), self.assertRaises(ValueError):
                avatar.validar_posicion(posicion, (1920, 1080))

    def test_incorporacion_manual_esta_anclada_al_texto_y_respeta_los_limites(self):
        escenas = [{"id": "S1", "t_in": 0, "t_out": 2, "narracion": "La tesis."},
                   {"id": "S2", "t_in": 2, "t_out": 4, "narracion": "El detalle."}]
        params = {"unidades": {"escena:S2": {"avatar": {"activo": True, "ancla": avatar.ancla_de(escenas[1])}}}}
        self.assertEqual(avatar.aplicar_ediciones({"S1"}, escenas, params), {"S1", "S2"})
        otras = copy.deepcopy(escenas)
        otras[1]["narracion"] = "Otra explicación diferente."
        self.assertEqual(avatar.aplicar_ediciones({"S1"}, otras, params), {"S1"})
        self.assertFalse(avatar.admite_escena(dict(escenas[1], t_out=70)))
        self.assertFalse(avatar.admite_escena(dict(escenas[1], medio_usuario={"tipo": "video"})))
        self.assertFalse(avatar.admite_escena(dict(escenas[1], cartela={"plantilla": "cifra"})))

    def test_retrato_antes_del_montaje_con_referencia_y_formato_cuatro_tres(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}):
            png = io.BytesIO()
            Image.new("RGB", (1536, 1024), "green").save(png, "PNG")
            motor = Mock()
            motor.generar.return_value = (png.getvalue(), {})
            destino = os.path.join(tmp, "retrato.png")
            with patch.object(avatar.medios, "motor", return_value=motor):
                avatar.generar_retrato("Cambia la camisa a verde", destino, ["anterior.png"])
            self.assertEqual(motor.generar.call_args.args[1], ["anterior.png"])
            with Image.open(destino) as imagen:
                self.assertEqual(imagen.size, (1024, 768))
            with self.assertRaises(ValueError):
                avatar.generar_retrato(" ", destino)

    def test_clave_enmascarada_y_conservacion(self):
        clave = "boson-secreto-no-devolver"
        resumen = claves.guardar({"boson": {"clave": clave}})
        self.assertNotIn(clave, str(resumen))
        self.assertTrue(resumen["boson"]["puesta"])
        claves.guardar({"pixabay": {"clave": "otra"}})
        self.assertEqual(claves.leer()["boson"]["clave"], clave)

    def test_boson_reanuda_id_sin_crear_otro_trabajo(self):
        with tempfile.TemporaryDirectory() as tmp:
            imagen = os.path.join(tmp, "imagen.png")
            audio = os.path.join(tmp, "audio.wav")
            Path(imagen).write_bytes(b"imagen")
            Path(audio).write_bytes(b"audio")
            destino = os.path.join(tmp, "avatar.mp4")
            datos = {}
            def solicitud(metodo, url, **kwargs):
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secreta")
                if metodo == "POST":
                    self.assertEqual(set(kwargs["files"]), {"ref_image", "input"})
                    return Mock(ok=True, json=lambda: {"id": "video_1", "status": "queued"})
                if url.endswith("/content"):
                    respuesta = Mock(ok=True, iter_content=lambda _n: [b"mp4" * 32])
                    respuesta.__enter__ = Mock(return_value=respuesta)
                    respuesta.__exit__ = Mock(return_value=False)
                    return respuesta
                return Mock(ok=True, json=lambda: {"id": "video_1", "status": "completed"})
            def guardar(ficha):
                datos.update(ficha)
            with patch.object(avatar_boson.requests, "request", side_effect=solicitud) as red, patch.object(avatar_boson.time, "sleep"):
                avatar_boson.generar(imagen, audio, destino, "secreta", lambda: datos, guardar, lambda _m: None)
                self.assertEqual(sum(c.args[0] == "POST" for c in red.call_args_list), 1)
                red.reset_mock()
                os.remove(destino)
                avatar_boson.generar(imagen, audio, destino, "secreta", lambda: datos, guardar, lambda _m: None)
                self.assertFalse(any(c.args[0] == "POST" for c in red.call_args_list))
                self.assertGreater(os.path.getsize(destino), 32)

    def test_generacion_cache_y_composicion_reales_sin_red(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ESTUDIO_SIMULAR": "1"}):
            proyecto = Proyecto.crear(tmp, "Avatar")
            estado = Estado(proyecto)
            antes = {p: estado.firma(p) for p in ("guion", "voz", "assets", "callouts")}
            contenido = io.BytesIO()
            Image.new("RGB", (100, 100), "red").save(contenido, "PNG")
            referencia = imagenes_animacion.guardar(proyecto, contenido.getvalue(), "foto.png")
            opciones = {"avatar": {"activo": True, "metodo": "subir", "imagen": referencia}}
            estado.actualizar_params("render", opciones)
            self.assertEqual(antes, {p: estado.firma(p) for p in antes})
            audio = proyecto.ruta("voz.wav")
            with wave.open(audio, "wb") as fh:
                fh.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                fh.writeframes(b"\0\0" * 48000)
            plan = {"escenas": [{"id": "S1", "narracion": "La explicación central.", "t_in": 0, "t_out": 2}]}
            with patch.object(avatar_boson.requests, "request", side_effect=AssertionError("sin red")):
                previa = avatar.estado_previa(proyecto, opciones, plan, audio)
                self.assertEqual(previa["estado"], "pendiente")
                self.assertFalse(Path(proyecto.ruta("avatar")).exists())
                clips = avatar.preparar(proyecto, opciones, plan, audio, lambda *_a: None)
                ruta = clips["S1"]
                previa = avatar.estado_previa(proyecto, opciones, plan, audio)
                self.assertEqual(previa["estado"], "listo")
                self.assertEqual(proyecto.ruta(previa["clips"]["S1"]), ruta)
                movidas = copy.deepcopy(opciones)
                movidas["unidades"] = {"escena:S1": {"avatar": {
                    "ancla": avatar.ancla_de(plan["escenas"][0]), "posicion": {"x": .1, "y": .2}}}}
                self.assertEqual(avatar.estado_previa(proyecto, movidas, plan, audio), previa)
                self.assertEqual(avatar.preparar(proyecto, movidas, plan, audio, lambda *_a: None), clips)
                with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0", "BOSON_API_KEY": ""}), \
                        patch.object(avatar.claves, "leer", return_value={"boson": {"clave": ""}}):
                    self.assertEqual(avatar.preparar(proyecto, opciones, plan, audio, lambda *_a: None), clips)
                cambiado = copy.deepcopy(plan)
                cambiado["escenas"][0]["t_out"] = 1
                self.assertEqual(avatar.estado_previa(proyecto, opciones, cambiado, audio)["estado"], "pendiente")
                cambiado = copy.deepcopy(plan)
                cambiado["escenas"][0]["narracion"] = "Otra frase distinta."
                self.assertEqual(avatar.estado_previa(proyecto, opciones, cambiado, audio)["estado"], "pendiente")
                self.assertIsNone(avatar.estado_previa(proyecto, {"avatar": {"activo": False}}, plan, audio))
                fecha = os.stat(ruta).st_mtime_ns
                self.assertEqual(clips, avatar.preparar(proyecto, opciones, plan, audio, lambda *_a: None))
                self.assertEqual(fecha, os.stat(ruta).st_mtime_ns)
                fondo = proyecto.ruta("fondo.png")
                Image.new("RGB", (320, 180), "blue").save(fondo)
                compuesto = avatar.componer(proyecto, ruta, fondo, lambda: None)
                self.assertTrue(os.path.getsize(compuesto) > 100)
                # El recuadro debe quedar dentro del recorte del vídeo, tanto
                # horizontal como vertical, con el mismo audio/duración.
                for salida in ((320, 180), (180, 320)):
                    compuesto = avatar.componer(proyecto, ruta, fondo, lambda: None, salida)
                    frame = subprocess.run([medios.ffmpeg(), "-v", "error", "-i", compuesto,
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                        capture_output=True, check=True, **medios.SIN_VENTANA)
                    with Image.open(io.BytesIO(frame.stdout)) as img:
                        proporcion = salida[0] / salida[1]
                        va = min(320, 180 * proporcion)
                        vh = min(180, 320 / proporcion)
                        lado = int(min(va, vh) * .42) // 2 * 2
                        x = int((320 + va) / 2 - lado - va * .03) + lado // 2
                        y = int((180 - vh) / 2 + vh * .04) + lado // 2
                        r, _g, b = img.convert("RGB").getpixel((x, y))
                        self.assertGreater(r, b + 100)
                    movido = avatar.componer(proyecto, ruta, fondo, lambda: None, salida, {"x": 0, "y": 0})
                    self.assertNotEqual(movido, compuesto)
                    frame = subprocess.run([medios.ffmpeg(), "-v", "error", "-i", movido,
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                        capture_output=True, check=True, **medios.SIN_VENTANA)
                    with Image.open(io.BytesIO(frame.stdout)) as img:
                        x = int((320 - va) / 2) + lado // 2
                        y = int((180 - vh) / 2) + lado // 2
                        r, _g, b = img.convert("RGB").getpixel((x, y))
                        self.assertGreater(r, b + 100)
                self.assertEqual(fecha, os.stat(ruta).st_mtime_ns)

    def test_seleccion_editorial_cache_y_exclusiones(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}):
            proyecto = Proyecto.crear(tmp, "Seleccion")
            escenas = [{"id": "central", "narracion": "Esto explica la causa.", "t_in": 0, "t_out": 5},
                       {"id": "larga", "narracion": "Más de un minuto.", "t_in": 5, "t_out": 66},
                       {"id": "manual", "narracion": "Propia.", "t_in": 66, "t_out": 70, "medio_usuario": {"tipo": "video"}}]
            with patch.object(avatar.cli_claude, "escribiendo", return_value={"escenas": [{"id": "central", "motivo": "Tesis"}]}) as modelo:
                self.assertEqual(avatar.seleccionar(proyecto, escenas, lambda *_a: None), {"central"})
                avatar.seleccionar(proyecto, escenas, lambda *_a: None)
                modelo.assert_called_once()
                self.assertNotIn('"id": "larga"', modelo.call_args.args[0])
                self.assertNotIn('"id": "manual"', modelo.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
