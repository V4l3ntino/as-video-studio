"""Sustituciones, limites reales de clips y montaje mixto; sin proveedores IA."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_aislado = tempfile.TemporaryDirectory(prefix="prueba_medios_config_")
for variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                 "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[variable] = os.path.join(_aislado.name, variable)
from PIL import Image
from nucleo.proyecto import Proyecto, escribir_json
from nucleo.estado import Estado
from pasos import medios_escena as propios, p6_assets, p8_render


class Sustituciones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="medios_escena_")
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = Proyecto.crear(self.tmp.name, "video")
        self.estado = Estado(self.proyecto)
        for paso in ("ingesta", "brief", "guion", "voz", "revision_audio"):
            self.estado.completar(paso, {})
        self.plan = {"generacion": [160, 90], "resolucion": [160, 90], "escenas": [
            {"id": "S001", "narracion": "Primera escena", "t_in": 0, "t_out": 3, "duracion": 3},
            {"id": "S002", "narracion": "Segunda escena", "t_in": 3, "t_out": 6, "duracion": 3}]}
        trabajo = self.proyecto.ruta_trabajo("assets")
        for sid, color in (("S001", "red"), ("S002", "blue")):
            ruta = os.path.join(trabajo, "escenas", sid + ".png")
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            Image.new("RGB", (160, 90), color).save(ruta)
        escribir_json(os.path.join(trabajo, "plan.json"), self.plan)
        self.estado.actualizar_params("assets", {"unidades": {"escena:S001": {}, "escena:S002": {}}})
        self.estado.completar("assets", {"plan": "plan.json"}, unidades={
            "escena:S001": {"png": "escenas/S001.png"}, "escena:S002": {"png": "escenas/S002.png"}})
        for paso in ("callouts", "render"):
            self.estado.completar(paso, {}, unidades={"escena:S001": {}, "escena:S002": {}})

    def nueva_imagen(self):
        ruta = self.proyecto.ruta("aportada.jpg")
        Image.new("RGB", (90, 160), "green").save(ruta)
        return propios.preparar(ruta, "foto.jpg", self.proyecto.ruta("medios_usuario", "uno"), (160, 90))

    def test_sustituye_solo_un_plano_con_historia_y_sin_mover_la_voz(self):
        antigua = self.proyecto.ruta_paso("assets", 1) + "/escenas/S001.png"
        contenido = Path(antigua).read_bytes()
        firma_voz = self.estado.firma("voz")
        segunda = copy.deepcopy(self.estado.salidas_unidad("assets", "escena:S002"))
        resultado = propios.sustituir(self.proyecto, self.estado, copy.deepcopy(self.plan), "S001", self.nueva_imagen())
        self.assertEqual(resultado["version"], 2)
        self.assertEqual(self.estado.firma("voz"), firma_voz)
        self.assertEqual(Path(antigua).read_bytes(), contenido)
        self.assertNotEqual(Path(self.proyecto.ruta_paso("assets", 2), "escenas/S001.png").read_bytes(), contenido)
        self.assertEqual(self.estado.salidas_unidad("assets", "escena:S002"), segunda)
        self.assertEqual(self.estado.unidades_obsoletas("callouts"), ["escena:S001"])
        self.assertEqual(self.estado.unidades_obsoletas("render"), ["escena:S001"])
        with Image.open(resultado["medio"]["poster"]) as imagen:
            self.assertEqual(imagen.size, (160, 90))
        self.estado.revertir("assets", 1)
        self.assertNotIn("medio_usuario", self.estado.params("assets")["unidades"]["escena:S001"])

    def test_no_da_por_hechas_las_otras_escenas_de_una_tanda_incompleta(self):
        proyecto = Proyecto.crear(self.tmp.name, "incompleto")
        estado = Estado(proyecto)
        ruta = proyecto.ruta("entrada.png")
        Image.new("RGB", (32, 32), "red").save(ruta)
        medio = propios.preparar(ruta, "entrada.png", proyecto.ruta("medios_usuario", "uno"), (160, 90))
        propios.sustituir(proyecto, estado, copy.deepcopy(self.plan), "S001", medio)
        self.assertIn("escena:S002", estado.unidades_sin_hacer("assets"))
        self.assertNotIn("escena:S001", estado.unidades_sin_hacer("assets"))

    def test_replanificar_conserva_el_medio_solo_para_su_texto(self):
        propios.sustituir(self.proyecto, self.estado, copy.deepcopy(self.plan), "S001", self.nueva_imagen())
        plan = propios.aplicar_al_plan(copy.deepcopy(self.plan), self.estado.params("assets"))
        self.assertIn("medio_usuario", plan["escenas"][0])
        plan = copy.deepcopy(self.plan)
        plan["escenas"][0]["narracion"] = "Otro contenido"
        propios.aplicar_al_plan(plan, self.estado.params("assets"))
        self.assertNotIn("medio_usuario", plan["escenas"][0])
        plan["escenas"][1]["narracion"] = "Primera escena"
        propios.aplicar_al_plan(plan, self.estado.params("assets"))
        self.assertIn("medio_usuario", plan["escenas"][1])

    def test_duplicar_lleva_sus_ficheros_y_reescribe_sus_rutas(self):
        propios.sustituir(self.proyecto, self.estado, copy.deepcopy(self.plan), "S001", self.nueva_imagen())
        copia = self.proyecto.duplicar(self.tmp.name, "Copia con material propio")
        medio = Estado(copia).params("assets")["unidades"]["escena:S001"]["medio_usuario"]
        self.assertTrue(medio["archivo"].startswith(copia.raiz))
        self.assertTrue(os.path.isfile(medio["archivo"]))
        self.assertTrue(os.path.isfile(medio["poster"]))

    def test_retomar_una_escena_propia_no_solicita_otra_imagen(self):
        propios.sustituir(self.proyecto, self.estado, copy.deepcopy(self.plan), "S001", self.nueva_imagen())
        plan = propios.aplicar_al_plan(copy.deepcopy(self.plan), self.estado.params("assets"))
        plan["escenas"] = plan["escenas"][:1]
        plan["dependencias"] = {}
        trabajo = self.proyecto.ruta_trabajo("assets")
        dirs = {"escenas": os.path.join(trabajo, "escenas"), "cache": os.path.join(trabajo, "_refs")}
        resultados = {}
        with patch.object(p6_assets, "_producir_imagen", side_effect=AssertionError("no llamar a IA")):
            p6_assets._generar_escenas(plan, dirs, p6_assets._con_defectos({}), trabajo,
                lambda _u: True, ["escena:S001"], resultados, lambda *_a: None,
                forzar=True, proyecto=self.proyecto)
        self.assertEqual(resultados["escena:S001"]["origen"], "usuario")

    def test_imagen_invalida_y_tipo_no_admitido(self):
        ruta = self.proyecto.ruta("roto.png")
        Path(ruta).write_bytes(b"no es una imagen")
        for nombre in ("roto.png", "programa.exe"):
            with self.assertRaises(ValueError):
                propios.preparar(ruta, nombre, self.proyecto.ruta("intento"), (160, 90))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requiere ffmpeg y ffprobe")
class ClipsReales(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="clips_escena_")
        self.addCleanup(self.tmp.cleanup)

    def clip(self, segundos):
        ruta = os.path.join(self.tmp.name, str(segundos) + ".mp4")
        subprocess.run([shutil.which("ffmpeg"), "-nostdin", "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(segundos),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", ruta],
            check=True, capture_output=True, timeout=30)
        return ruta

    def test_limites_dos_y_seis_y_medio_con_recorte_real_y_sin_audio(self):
        for duracion in (2, 4, 8):
            with self.subTest(duracion=duracion):
                medio = propios.preparar(self.clip(duracion), "clip.mp4",
                    os.path.join(self.tmp.name, "normalizado" + str(duracion)), (160, 90))
                self.assertAlmostEqual(medio["duracion"], min(duracion, 6.5), places=2)
                self.assertEqual(medio["recortado"], duracion > 6.5)
                datos = json.loads(subprocess.check_output([shutil.which("ffprobe"), "-v", "error",
                    "-show_entries", "stream=codec_type", "-of", "json", medio["archivo"]]))
                self.assertEqual([s["codec_type"] for s in datos["streams"]], ["video"])

    def test_menos_de_dos_segundos_se_rechaza(self):
        with self.assertRaisesRegex(ValueError, "mínimo"):
            propios.preparar(self.clip(1.5), "corto.mp4", os.path.join(self.tmp.name, "rechazo"), (160, 90))

    def test_frames_mueven_el_video_y_congelan_el_final_para_la_narracion(self):
        medio = propios.preparar(self.clip(2), "clip.mp4", os.path.join(self.tmp.name, "entrada"), (160, 90))
        frames = p8_render._fotogramas_de_clip(medio["archivo"], self.tmp.name,
            {"hyperframe_px": [160, 90]}, 90, 30)
        self.assertEqual(len(frames), 90)
        self.assertNotEqual(Path(frames[0]).read_bytes(), Path(frames[30]).read_bytes())
        self.assertEqual(Path(frames[65]).read_bytes(), Path(frames[-1]).read_bytes())
        html = p8_render._pagina_de({"t_in": 0, "t_out": 3},
            {"ventana_ini": [0, 0, 1, 1], "ventana_fin": [0, 0, 1, 1], "hyperframe_px": [160, 90]},
            "", medio["poster"], {"resolucion": [160, 90]}, os.path.join(self.tmp.name, "escena.html"),
            fps=30, fotogramas=frames)
        texto = Path(html).read_text(encoding="utf-8")
        self.assertIn("fondo.decode()", texto)
        self.assertNotIn("__FOTOGRAMAS__", texto)
        self.assertIn("v00090.png", texto)

    def test_monta_imagen_y_clip_con_la_misma_codificacion(self):
        quietos = os.path.join(self.tmp.name, "quietos")
        os.makedirs(quietos)
        for i in range(15):
            Image.new("RGB", (160, 90), "green").save(os.path.join(quietos, f"f{i+1:05d}.png"))
        imagen = os.path.join(self.tmp.name, "imagen.mp4")
        p8_render._codificar(quietos, imagen, 30, "media")
        frames = p8_render._fotogramas_de_clip(self.clip(2), self.tmp.name,
            {"hyperframe_px": [160, 90]}, 15, 30)
        moviles = os.path.join(self.tmp.name, "moviles")
        os.makedirs(moviles)
        for i, ruta in enumerate(frames):
            shutil.copyfile(ruta, os.path.join(moviles, f"f{i+1:05d}.png"))
        video = os.path.join(self.tmp.name, "clip.mp4")
        p8_render._codificar(moviles, video, 30, "media")
        salida = os.path.join(self.tmp.name, "mixto.mp4")
        with patch.object(p8_render, "_cola_negra", side_effect=lambda clips, *_a: clips):
            p8_render._concatenar([imagen, video], salida, None, 0, self.tmp.name, fps=30)
        self.assertAlmostEqual(propios.informacion_video(salida)["duracion"], 1, places=2)

    def test_render_real_captura_movimiento_y_capa_fija_sobre_el_clip(self):
        try:
            navegador_bin = p8_render.medios.edge()
        except RuntimeError:
            self.skipTest("requiere Edge o Chrome para el render real")
        if not os.path.isfile(navegador_bin):
            self.skipTest("requiere Edge o Chrome para el render real")
        ruta = self.clip(2)
        poster = os.path.join(self.tmp.name, "poster.png")
        Image.new("RGB", (160, 90), "red").save(poster)
        carpeta = os.path.join(self.tmp.name, "render")
        tarea = {"id": "S001", "fps": 6, "frames": 6, "carpeta": carpeta,
            "escena": {"id": "S001", "t_in": 0, "t_out": 1},
            "mov": {"ventana_ini": [0, 0, 1, 1], "ventana_fin": [0, 0, 1, 1],
                    "hyperframe_px": [160, 90]}, "capa": "", "hyper": poster,
            "capa_fija": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 90"><rect width="20" height="10" fill="#00ff00"/></svg>',
            "resolucion": [160, 90], "calidad": "media", "video": ruta,
            "clip": os.path.join(self.tmp.name, "render.mp4"),
            "ultimo": os.path.join(self.tmp.name, "ultimo.png"),
            "conservar_frames": True}
        navegador = p8_render.Navegador(160, 90)
        try:
            resultado = p8_render.renderizar_plano(tarea, navegador)
        finally:
            navegador.cerrar()
        self.assertEqual(resultado["frames"], 6)
        primero, ultimo = Path(carpeta, "f00001.png"), Path(carpeta, "f00006.png")
        self.assertNotEqual(primero.read_bytes(), ultimo.read_bytes())
        with Image.open(primero) as imagen:
            self.assertEqual(imagen.convert("RGB").getpixel((5, 5)), (0, 255, 0))
        self.assertAlmostEqual(propios.informacion_video(tarea["clip"])["duracion"], 1, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
