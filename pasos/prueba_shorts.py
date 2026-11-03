"""Shorts: selección, reutilización y montaje local real sin consumir APIs."""
import copy
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_aislado = tempfile.TemporaryDirectory(prefix="shorts_config_")
for _variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                  "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[_variable] = os.path.join(_aislado.name, _variable)

from PIL import Image
from nucleo.trabajos import Cancelado
from pasos import medios, recetas, shorts


class Shorts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="shorts_prueba_")
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = SimpleNamespace(raiz=self.tmp.name,
            ruta=lambda *p: os.path.join(self.tmp.name, *p))
        self.escenas = [{"id": f"S{i}", "narracion": "Este es el relato original de la escena central.",
            "t_in": i * 10, "t_out": (i + 1) * 10, "duracion": 10, "imagen": "fuente.png",
            "marcas": [[i * 10 + j, i * 10 + j + 0.9] for j in range(9)]}
            for i in range(5)]
        self.origen = {"escenas": self.escenas, "audio": "origen.wav", "video": "video.mp4", "guion": {}}
        self.propuesta = {"desde": "S1", "hasta": "S3", "inicio": "Esto parece imposible.",
            "final": "Descubre la historia completa en el vídeo relacionado.",
            "titulo": "Un giro inesperado", "motivo": "Revela un conflicto del relato."}

    def test_rango_y_seleccion_se_validan_antes_de_locutar(self):
        for minimo, maximo in [(0, 20), (10, 181), (60, 20), (1, float("nan")),
                                (True, 50), ("x", 20), (1, float("inf"))]:
            with self.assertRaises(ValueError):
                shorts.validar_rango(minimo, maximo)
        self.assertEqual(shorts.validar_rango(1, 180), (1, 180))
        for cambios in ({"desde": "no_existe"}, {"hasta": "S2"}, {"final": ""},
                        {"inicio": "<break time='100s'/>"}):
            with self.assertRaises(ValueError):
                shorts.validar_seleccion({**self.propuesta, **cambios}, self.origen, 10, 30)
        with self.assertRaises(ValueError):
            shorts.validar_seleccion(self.propuesta, self.origen, 1, 5)

    def test_solo_reescribe_extremos_y_reubica_subtitulos(self):
        anterior = copy.deepcopy(self.origen)
        seleccion = shorts.validar_seleccion(self.propuesta, self.origen, 10, 30)
        toma = {"duracion": 3, "audio": "extremo.wav", "palabras": [
            {"w": "Una", "s": 0, "e": 1}, {"w": "sorpresa.", "s": 1, "e": 2.9}]}
        plan = shorts.plan_montaje(self.proyecto, self.origen, seleccion, toma, toma, 10, 30)
        self.assertEqual(self.origen, anterior)
        central = plan["escenas"][1]
        self.assertEqual(central["narracion"], self.escenas[2]["narracion"])
        self.assertEqual(central["origen_t"], 20)
        self.assertNotIn("audio", central)
        self.assertEqual(central["marcas"][0][0], central["t_in"])
        for escena in plan["escenas"]:
            self.assertTrue(escena["subtitulos"])
            for sub in escena["subtitulos"]:
                self.assertGreaterEqual(sub["desde"], 0)
                self.assertLessEqual(sub["hasta"], escena["duracion"] + 0.01)
        with self.assertRaises(ValueError):
            shorts.plan_montaje(self.proyecto, self.origen, seleccion, toma, toma, 100, 110)

    def test_la_voz_de_los_extremos_se_cachea(self):
        cfg = {"voz_id": "voz-original"}
        with patch.object(shorts.p4_voz, "sintetizar_toma", return_value=(b"wav", 1,
                [{"w": "Hola", "s": 0, "e": 1}])) as voz:
            uno = shorts._locutar(self.proyecto, "Hola", cfg, lambda *_a: None)
            dos = shorts._locutar(self.proyecto, "Hola", cfg, lambda *_a: None)
            self.assertEqual(uno, dos)
            voz.assert_called_once()

    def test_sse_sin_charset_conserva_tildes_en_las_marcas(self):
        import requests
        palabras = ["Simbad", "ideó", "cómo", "vídeo", "acción", "niño"]
        evento = {"data": base64.b64encode(b"\0\0" * 44100).decode("ascii"),
            "word_timestamps": {"words": palabras,
                "start": [i * 0.1 for i in range(len(palabras))],
                "end": [(i + 1) * 0.1 for i in range(len(palabras))]}}
        respuesta = requests.Response()
        respuesta.status_code = 200
        respuesta.headers["Content-Type"] = "text/event-stream"
        respuesta.encoding = requests.utils.get_encoding_from_headers(respuesta.headers)
        self.assertEqual(respuesta.encoding, "ISO-8859-1")
        respuesta.raw = io.BytesIO(("data: " + json.dumps(evento, ensure_ascii=False) + "\n\n").encode("utf-8"))
        cfg = shorts.p4_voz.resolver_params({"voz_id": "voz-de-prueba"})
        with patch.object(shorts.p4_voz.requests, "post", return_value=respuesta), \
             patch.object(shorts.p4_voz.motor, "cargar_api_key", return_value="clave-de-prueba"):
            _wav, _duracion, marcas = shorts.p4_voz._toma_real(" ".join(palabras), cfg, lambda *_a: None)
        self.assertEqual([m["w"] for m in marcas], palabras)

    def test_repara_cache_antigua_sin_locutar_ni_alterar_tiempos(self):
        texto = "Simbad ideó un plan. Descubre cómo acaba en el vídeo relacionado."
        cfg = {"voz_id": "la-misma-voz"}
        marcas = [{"w": p.encode("utf-8").decode("latin1"), "s": i, "e": i + 0.5}
                  for i, p in enumerate(texto.split())]
        clave = medios.huella({"texto": texto, "cfg": cfg, "simulado": shorts.p4_voz.simulado()})
        ruta = self.proyecto.ruta("shorts", "_audio", clave + ".wav")
        os.makedirs(os.path.dirname(ruta))
        Path(ruta).write_bytes(b"audio que se conserva sin generar de nuevo")
        medios.escribir_json(ruta + ".json", {"duracion": 12, "palabras": marcas})
        with patch.object(shorts.p4_voz, "sintetizar_toma", side_effect=AssertionError("no se debe locutar")):
            toma = shorts._locutar(self.proyecto, texto, cfg, lambda *_a: None)
        self.assertEqual([m["w"] for m in toma["palabras"]], texto.split())
        self.assertEqual([(m["s"], m["e"]) for m in toma["palabras"]],
                         [(m["s"], m["e"]) for m in marcas])
        self.assertEqual(Path(ruta).read_bytes(), b"audio que se conserva sin generar de nuevo")
        motor = medios.motor("render_video/shorts.py")
        destino = self.proyecto.ruta("subtitulos.ass")
        motor._subtitulos([{"t_in": 0, "subtitulos": [{"texto": " ".join(m["w"] for m in toma["palabras"]),
                             "desde": 0, "hasta": 12}]}], destino)
        escrito = Path(destino).read_text(encoding="utf-8").replace("\\N", " ")
        self.assertIn("ideó", escrito)
        self.assertIn("cómo", escrito)
        self.assertIn("vídeo", escrito)
        self.assertNotIn("Ã", escrito)

    def test_cancelar_mata_ffmpeg(self):
        motor = medios.motor("render_video/shorts.py")
        proceso = SimpleNamespace(poll=lambda: None, kill=lambda: None, wait=lambda: None)
        with patch.object(motor.subprocess, "Popen", return_value=proceso), \
             patch.object(proceso, "kill") as matar:
            def cancelar(*_a):
                raise Cancelado("cancelado")
            with self.assertRaises(Cancelado):
                motor._correr(["ffmpeg"], self.tmp.name, cancelar, 0.3)
            matar.assert_called_once()

    def test_reintentar_montaje_no_repite_ia_ni_voz(self):
        sid = "a" * 32
        carpeta = self.proyecto.ruta("shorts", sid)
        os.makedirs(carpeta)
        origen = {**self.origen, "cfg": {"voz_id": "original"}, "version_render": 1}
        medios.escribir_json(os.path.join(carpeta, "fuentes.json"), origen)
        shorts.guardar(self.proyecto, sid, {"id": sid, "creado": "2026-01-01", "estado": "pendiente",
            "minimo": 10, "maximo": 30, "version_render": 1})
        toma = (b"audio cacheado", 3, [{"w": "Gancho", "s": 0, "e": 2.9}])
        motor = SimpleNamespace(montar=lambda *_a: None)
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), \
             patch.object(shorts, "_llamar_claude", return_value=(json.dumps(self.propuesta), {})) as ia, \
             patch.object(shorts.p4_voz, "sintetizar_toma", return_value=toma) as voz, \
             patch.object(shorts.medios, "motor", return_value=motor), \
             patch.object(motor, "montar", side_effect=[RuntimeError("ffmpeg falló"),
                {"mp4": os.path.join(carpeta, "short.mp4"), "duracion": 16, "resolucion": [1080, 1920]}]):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg falló"):
                shorts.ejecutar(self.proyecto, sid, recetas.SHORTS, lambda *_a: None)
            self.assertEqual(shorts.leer(self.proyecto)[0]["estado"], "error")
            resultado = shorts.ejecutar(self.proyecto, sid, recetas.SHORTS, lambda *_a: None)
            self.assertEqual(resultado["short"]["estado"], "listo")
            ia.assert_called_once()
            self.assertEqual(voz.call_count, 2)

    def test_descarte_incompatible_o_sin_manifiesto_no_cambia_el_grafo(self):
        from nucleo.estado import Estado, PASOS
        from nucleo.proyecto import Proyecto
        proyecto = Proyecto.crear(self.tmp.name, "Restauracion de prueba")
        estado = Estado(proyecto)
        for paso in PASOS:
            estado.completar(paso["id"], {})
        versiones = {p["id"]: 1 for p in PASOS}
        estado.actualizar_params("guion", {"bloques": {"B001": {"texto": "Pendiente"}}})
        antes = Path(estado.ruta).read_bytes()
        plan = estado.restaurar_versiones(versiones, "render")
        self.assertIn("guion", plan["pasos"])
        self.assertEqual(Path(estado.ruta).read_bytes(), antes)
        original = estado.manifiesto_version
        def manifiesto(paso, version):
            if paso == "assets":
                raise ValueError("falta el manifiesto")
            return original(paso, version)
        with patch.object(estado, "manifiesto_version", side_effect=manifiesto):
            with self.assertRaisesRegex(ValueError, "falta el manifiesto"):
                estado.restaurar_versiones(versiones, "render", aplicar=True)
        self.assertEqual(Path(estado.ruta).read_bytes(), antes)
        estado.completar("guion", {})
        antes = Path(estado.ruta).read_bytes()
        with self.assertRaisesRegex(ValueError, "no se ha podido recuperar"):
            estado.restaurar_versiones({**versiones, "guion": 2}, "render", aplicar=True)
        self.assertEqual(Path(estado.ruta).read_bytes(), antes)
        self.assertEqual(proyecto.version_activa("guion"), 2)

    def test_si_faltan_las_fuentes_se_deshace_el_descarte(self):
        from nucleo.estado import Estado, PASOS
        from nucleo.proyecto import Proyecto
        proyecto = Proyecto.crear(self.tmp.name, "Fuentes incompletas")
        estado = Estado(proyecto)
        for paso in PASOS:
            estado.completar(paso["id"], {})
        Path(proyecto.ruta_paso("render", 1), "video.mp4").write_bytes(b"mp4 anterior")
        estado.actualizar_params("guion", {"bloques": {"B001": {"texto": "Mi cambio pendiente"}}})
        trabajo = Path(proyecto.ruta_trabajo("assets"))
        (trabajo / "pendiente.txt").write_text("Trabajo que no se debe perder")
        antes = Path(estado.ruta).read_bytes()
        with self.assertRaisesRegex(ValueError, "al menos tres escenas"):
            shorts.descartar_cambios(proyecto, estado)
        self.assertEqual(Path(estado.ruta).read_bytes(), antes)
        self.assertEqual((trabajo / "pendiente.txt").read_text(), "Trabajo que no se debe perder")
        self.assertEqual(estado.params("guion")["bloques"]["B001"]["texto"], "Mi cambio pendiente")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "necesita ffmpeg")
    def test_mp4_real_vertical_y_audio_central_sin_regrabar(self):
        motor = medios.motor("render_video/shorts.py")
        imagen = self.proyecto.ruta("fuente.png")
        Image.new("RGB", (320, 180), "#a5794b").save(imagen)
        def audio(nombre, frecuencia):
            ruta = self.proyecto.ruta(nombre)
            pcm = b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * frecuencia * n / 44100)))
                           for n in range(3 * 44100))
            with wave.open(ruta, "wb") as fh:
                fh.setnchannels(1)
                fh.setsampwidth(2)
                fh.setframerate(44100)
                fh.writeframes(pcm)
            return ruta, pcm
        fuente, original = audio("origen.wav", 440)
        nuevo, _ = audio("nuevo.wav", 660)
        firma = hashlib.sha256(Path(fuente).read_bytes()).hexdigest()
        escenas = [{"t_in": i, "t_out": i + 1, "duracion": 1, "origen_t": i,
                    "imagen": imagen, "subtitulos": [{"texto": "Narración", "desde": 0, "hasta": 1}]}
                   for i in range(3)]
        for i in (0, 2):
            escenas[i].update({"audio": nuevo, "tempo": 1})
        with patch.object(motor, "ANCHO", 180), patch.object(motor, "ALTO", 320), \
             patch.object(motor, "FPS", 10):
            salida = motor.montar({"escenas": escenas, "audio_origen": fuente,
                "video_origen": "no_se_necesita.mp4", "minimo": 2.8, "maximo": 3.5},
                self.proyecto.ruta("montaje"), lambda *_a: None)
        datos = json.loads(subprocess.check_output([shutil.which("ffprobe"), "-v", "error",
            "-show_entries", "stream=width,height", "-of", "json", salida["mp4"]]))
        self.assertEqual(datos["streams"][0]["width"], 180)
        self.assertEqual(datos["streams"][0]["height"], 320)
        self.assertTrue(2.8 <= salida["duracion"] <= 3.5)
        with wave.open(self.proyecto.ruta("montaje", "narracion.wav"), "rb") as fh:
            fh.setpos(44100)
            central = fh.readframes(44100)
        self.assertEqual(central, original[44100 * 2:44100 * 4])
        self.assertEqual(hashlib.sha256(Path(fuente).read_bytes()).hexdigest(), firma)


if __name__ == "__main__":
    unittest.main()
