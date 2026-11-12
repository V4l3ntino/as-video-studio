"""Comprueba el codificador acelerado y la concatenacion real de sus clips."""
import base64
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import p8_render
from nucleo.proyecto import Proyecto


class RenderAcelerado(unittest.TestCase):
    def test_desactivar_subtitulos_conserva_cartelas_y_capas_originales(self):
        with tempfile.TemporaryDirectory(prefix="estudio_subtitulos_") as carpeta:
            raiz = Path(carpeta)
            proyecto = Proyecto.crear(carpeta, 'Render de prueba')
            hyper = raiz / "hyper.png"
            hyper.touch()
            movil = raiz / "cartela.svg"
            movil.write_text("<svg>Cartela</svg>", encoding="utf-8")
            fija = raiz / "subtitulo.svg"
            fija.write_text("<svg>Subtitulo</svg>", encoding="utf-8")
            plan = raiz / "plan.json"
            movimiento = raiz / "movimiento.json"
            p8_render.medios.escribir_json(str(plan), {"escenas": [
                {"id": "S001", "t_in": 0, "t_out": 1}]})
            p8_render.medios.escribir_json(str(movimiento), {"movimientos": [{
                "id": "S001", "hyperframe": str(hyper), "capa": movil.name,
                "capa_fija": fija.name, "ventana_ini": [0, 0, 1, 1],
                "ventana_fin": [0, 0, 1, 1]}]})
            for opcion, esperado in (({}, "<svg>Subtitulo</svg>"),
                                     ({"subtitulos": False}, ""),
                                     ({"subtitulos": True}, "<svg>Subtitulo</svg>")):
                with self.subTest(opcion=opcion), patch.object(
                        p8_render.medios, "sembrar_trabajo", return_value=carpeta), patch.object(
                        p8_render, "_elegir_codec", return_value="libx264"), patch.object(
                        p8_render, "correr_lote", side_effect=RuntimeError("captura de prueba")) as lote:
                    with self.assertRaisesRegex(RuntimeError, "captura de prueba"):
                        p8_render.ejecutar(proyecto, dict(
                            plan=str(plan), movimiento=str(movimiento), audio="voz.wav", **opcion))
                    tarea = lote.call_args.args[0][0]
                    self.assertEqual(tarea["capa_fija"], esperado)
                    self.assertEqual(tarea["capa"], "<svg>Cartela</svg>")
                    self.assertEqual(fija.read_text(encoding="utf-8"), "<svg>Subtitulo</svg>")

    def test_retomar_no_mezcla_codificadores_tras_un_fallo(self):
        with tempfile.TemporaryDirectory(prefix="estudio_codec_") as carpeta:
            clips = [str(Path(carpeta) / f"S{i}.mp4") for i in range(2)]
            for clip in clips:
                Path(clip).touch()
            with patch.object(p8_render, "_nvenc_disponible", return_value=True):
                self.assertEqual(p8_render._elegir_codec(carpeta, clips, {clips[1]}), "libx264")
                self.assertEqual(p8_render._elegir_codec(carpeta, clips, set(clips)), "h264_nvenc")
                p8_render.medios.escribir_json(clips[0] + ".codec.json", {"codec": "h264_nvenc"})
                with self.assertRaisesRegex(RuntimeError, "interrumpido"):
                    p8_render._elegir_codec(carpeta, clips, set())
                self.assertEqual(p8_render._elegir_codec(carpeta, clips, {clips[1]}), "h264_nvenc")
            with patch.object(p8_render, "_nvenc_disponible", return_value=False):
                with self.assertRaisesRegex(RuntimeError, "no esta disponible"):
                    p8_render._elegir_codec(carpeta, clips, {clips[1]})
                self.assertEqual(p8_render._elegir_codec(carpeta, clips, set(clips)), "libx264")

    def test_flujo_preserva_video_anterior_si_falla_la_captura(self):
        with tempfile.TemporaryDirectory(prefix="estudio_flujo_error_") as carpeta:
            destino = Path(carpeta) / "clip.mp4"
            destino.write_bytes(b"clip anterior valido")
            png = io.BytesIO()
            Image.new("RGB", (320, 240), "red").save(png, format="PNG")

            def capturas():
                yield png.getvalue()
                raise RuntimeError("captura interrumpida")

            with self.assertRaisesRegex(RuntimeError, "captura interrumpida"):
                p8_render._codificar_flujo(capturas(), str(destino), 30, "media", "libx264")
            self.assertEqual(destino.read_bytes(), b"clip anterior valido")
            self.assertFalse(Path(str(destino) + ".parcial.mp4").exists())

    def test_flujo_y_secuencia_conservan_pixeles_subtitulos_y_transiciones(self):
        with tempfile.TemporaryDirectory(prefix="estudio_flujo_visual_") as carpeta:
            raiz = Path(carpeta)
            hyper = raiz / "hyper.png"
            imagen = Image.new("RGB", (640, 480))
            imagen.putdata([((x * 3) % 256, (y * 5) % 256, (x + y) % 256)
                            for y in range(480) for x in range(640)])
            imagen.save(hyper)
            anterior = raiz / "anterior.png"
            Image.new("RGB", (320, 240), "green").save(anterior)
            pagina_trans = p8_render.transiciones.pagina(str(raiz / "transicion.html"), 320, 240, {})
            fija = ('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240">'
                    '<g><text x="12" y="215" fill="white" font-size="24">Subtitulo</text>'
                    '<animate attributeName="opacity" from="0" to="1" dur="0.3s" fill="freeze"/>'
                    '</g></svg>')
            navegador = p8_render.Navegador(320, 240)
            try:
                for transicion in (False, True):
                    huellas, ultimos = [], []
                    for conservar in (True, False):
                        nombre = f"{transicion}_{conservar}"
                        tarea = {
                            "id": nombre, "escena": {"t_in": 0, "t_out": 0.4},
                            "mov": {"ventana_ini": [0, 0, 1, 1],
                                    "ventana_fin": [0.1, 0.1, 0.8, 0.8],
                                    "hyperframe_px": [640, 480]},
                            "capa": "", "capa_fija": fija, "hyper": str(hyper),
                            "frames": 12, "fps": 30, "resolucion": [320, 240],
                            "calidad": "alta", "codec": "libx264",
                            "carpeta": str(raiz / nombre), "clip": str(raiz / f"{nombre}.mp4"),
                            "ultimo": str(raiz / f"ultimo_{nombre}.png"),
                            "anterior": str(anterior) if transicion else None,
                            "corte": {"tipo": "fundido", "duracion": 0.2,
                                      "shader": p8_render.transiciones.frag_de("fundido")},
                            "pagina_trans": pagina_trans, "conservar_frames": conservar,
                        }
                        ficha = p8_render.renderizar_plano(tarea, navegador)
                        self.assertEqual(ficha["frames_transicion"], 6 if transicion else 0)
                        lectura = subprocess.run(
                            [p8_render.medios.ffmpeg(), "-v", "error", "-i", tarea["clip"],
                             "-f", "framemd5", "-"], capture_output=True, check=True, timeout=30)
                        huellas.append(lectura.stdout)
                        with Image.open(tarea["ultimo"]) as ultimo:
                            ultimos.append(ultimo.tobytes())
                    self.assertEqual(huellas[0], huellas[1], "el flujo cambia los fotogramas")
                    self.assertEqual(ultimos[0], ultimos[1], "el ultimo limpio debe conservarse")
                navegador.abrir(p8_render._pagina_de(
                    {"t_in": 0, "t_out": 1}, tarea["mov"], "", str(hyper),
                    {"resolucion": [320, 240]}, str(raiz / "comparar.html"), capa_fija=fija))
                navegador.pintar(0.2)
                png_rapido = navegador.capturar()
                normal = navegador.llamar("Page.captureScreenshot", format="png",
                                           captureBeyondViewport=False)["data"]
                with Image.open(io.BytesIO(png_rapido)) as rapido, \
                        Image.open(io.BytesIO(base64.b64decode(normal))) as referencia:
                    self.assertEqual(rapido.tobytes(), referencia.tobytes())
            finally:
                navegador.cerrar()

    def test_nvenc_concatena_clips_y_cola_sin_perder_fotogramas(self):
        if not p8_render._nvenc_disponible():
            self.skipTest("NVENC no esta disponible en esta maquina")
        with tempfile.TemporaryDirectory(prefix="estudio_nvenc_") as carpeta:
            frames = Path(carpeta) / "frames"
            frames.mkdir()
            clips = []
            for color in ("red", "blue"):
                for i in range(6):
                    Image.new("RGB", (320, 240), color).save(frames / f"f{i+1:05d}.png")
                clip = str(Path(carpeta) / f"{color}.mp4")
                p8_render._codificar(str(frames), clip, 30, "alta", "h264_nvenc")
                clips.append(clip)
            salida = str(Path(carpeta) / "final.mp4")
            p8_render._concatenar(clips, salida, None, 0, carpeta, fps=30,
                                  calidad="alta", codec="h264_nvenc")
            comprobacion = subprocess.run(
                [p8_render.medios.ffmpeg(), "-v", "error", "-i", salida,
                 "-f", "null", "-"], capture_output=True, timeout=30)
            self.assertEqual(comprobacion.returncode, 0, comprobacion.stderr.decode(errors="replace"))
            self.assertAlmostEqual(p8_render.medios.duracion_media(salida), 3.4, delta=0.1)
            # Remontar el paquete en una maquina sin NVIDIA debe conservar
            # tambien la cola final; no requiere recodificar las escenas.
            portable = str(Path(carpeta) / "sin_gpu.mp4")
            with patch.object(p8_render, "_nvenc_disponible", return_value=False):
                p8_render._concatenar(clips, portable, None, 0, carpeta, fps=30,
                                      calidad="alta", codec="h264_nvenc")
            lectura = subprocess.run(
                [p8_render.medios.ffmpeg(), "-v", "error", "-i", portable,
                 "-f", "null", "-"], capture_output=True, timeout=30)
            self.assertEqual(lectura.returncode, 0, lectura.stderr.decode(errors="replace"))
            self.assertAlmostEqual(p8_render.medios.duracion_media(portable), 3.4, delta=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
