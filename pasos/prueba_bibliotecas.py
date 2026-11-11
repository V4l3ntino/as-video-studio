"""Contratos offline de bibliotecas, cadencia, reanudación y audio de escena."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np
import tempfile
import unittest
from unittest.mock import Mock, patch

_aislado = tempfile.TemporaryDirectory(prefix="estudio_bibliotecas_")
for variable, nombre in (("ESTUDIO_SECRETOS", "secretos"),
                         ("ESTUDIO_AJUSTES", "ajustes.json"),
                         ("ESTUDIO_ESTADISTICAS", "estadisticas.json")):
    os.environ[variable] = str(Path(_aislado.name) / nombre)

from PIL import Image
import bibliotecas
import p6_assets
import sonido
from nucleo.proyecto import Proyecto


class Bibliotecas(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="biblioteca_caso_")
        self.addCleanup(self.temporal.cleanup)
        self.proyecto = Proyecto.crear(self.temporal.name, "Video mixto")
        self.escenas = [{"id": f"S{i:03}", "narracion": f"El bosque {i}",
                         "prompt": "A forest", "set": "bosque", "t_in": (i-1)*3,
                         "t_out": i*3} for i in range(1, 7)]
        self.plan = {"escenas": self.escenas, "resolucion": [320, 180],
                     "formato": "horizontal", "dependencias": {}, "assets": {}}
        self.config = dict(bibliotecas.DEFECTOS, proveedores=["pixabay", "pexels"],
                           incorporar_ia=True, ia_cada=3)
        self.params = {"bibliotecas": self.config}
        self.avisar = Mock()

    def test_validacion_y_solo_audio_no_elimina_el_visual(self):
        for valores in ({"ia_cada": 0}, {"ia_cada": True}, {"ia_cada": 1.5},
                         {"audio": "si"}, {"incorporar_ia": "si"},
                         {"proveedores": ["otra"]}):
            with self.subTest(valores=valores), self.assertRaises(ValueError):
                bibliotecas.normalizar(valores)
        b = bibliotecas.Biblioteca(self.proyecto, {"bibliotecas": {
            "imagenes": False, "video": False, "audio": True}}, self.plan, self.avisar)
        with patch.object(b, "consulta") as consulta:
            self.assertIsNone(b.visual(self.escenas[0], "no-se-escribe.png"))
            consulta.assert_not_called()

    def test_cadencia_estable_y_sin_consultas_en_los_turnos_ia(self):
        ruta = Path(self.proyecto.ruta_trabajo("assets")) / "escenas" / "S001.json"
        bibliotecas.medios.escribir_json(str(ruta), {"recurso_biblioteca": {
            "fuente": "pexels", "tipo": "imagen", "id": "ya-descargada"}})
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        self.assertIn(("pexels", "imagen", "ya-descargada"), b.usados)
        self.assertEqual([k for k, ia in b.turnos.items() if ia], ["S003", "S006"])
        with patch.object(b, "consulta") as consulta:
            for e in (self.escenas[2], self.escenas[5]):
                self.assertIsNone(b.visual(e, "no-se-escribe.png"))
            consulta.assert_not_called()

    def test_sin_cadencia_se_busca_stock_en_todas_las_escenas(self):
        self.config["incorporar_ia"] = False
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        self.assertFalse(any(b.turnos.values()))
        with patch.object(b, "consulta", return_value={"visual": "forest"}) as consulta, patch.object(
                bibliotecas, "buscar", return_value=[]) as buscar:
            self.assertIsNone(b.visual(self.escenas[2], "sin.png"))
            consulta.assert_called_once()
            buscar.assert_called()
        self.assertIn("Codex", self.avisar.call_args.args[1])

    def test_proyectos_anteriores_conservan_la_cadencia(self):
        anterior = {"proveedores": ["pixabay"], "ia_cada": 3}
        self.assertTrue(bibliotecas.normalizar(anterior)["incorporar_ia"])
        self.assertFalse(bibliotecas.normalizar({})["incorporar_ia"])

    def test_reparto_por_escenas_excluye_ia_y_medios_propios(self):
        for porcentaje, esperadas in ((0, 0), (50, 2), (70, 3), (100, 4)):
            with self.subTest(porcentaje=porcentaje):
                self.config["carga_claude"] = porcentaje
                b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
                self.assertEqual(len(b.agentes), 4)
                self.assertEqual(list(b.agentes.values()).count("claude"), esperadas)
                retomada = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
                self.assertEqual(b.agentes, retomada.agentes)
        self.escenas[0]["medio_usuario"] = {"archivo": "propio.png"}
        self.escenas[1]["cartela"] = {"fondo": "solido"}
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        self.assertNotIn("S001", b.agentes)
        self.assertNotIn("S002", b.agentes)
        for valor in (-1, 101, True, 1.5, "70"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                bibliotecas.normalizar({"carga_claude": valor})
        self.assertNotIn("carga_claude", bibliotecas.normalizar({}))

    def test_consulta_y_seleccion_usan_el_mismo_agente_y_cache_separada(self):
        self.config.update(incorporar_ia=False, carga_claude=0)
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(
                bibliotecas, "_agente_chatgpt", side_effect=[
                    {"visual": "green forest"}, {"indice": -1}]) as chatgpt, patch.object(
                bibliotecas, "_agente") as claude, patch.object(bibliotecas, "buscar",
                return_value=[{"fuente": "pexels", "tipo": "imagen", "id": "1"}]):
            self.assertIsNone(b.visual(self.escenas[0], "sin.png"))
            self.assertEqual(b.consulta(self.escenas[0])["visual"], "green forest")
            self.assertEqual(chatgpt.call_count, 2)
            claude.assert_not_called()
        self.config.pop("carga_claude")
        antiguo = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(
                bibliotecas, "_agente", return_value={"visual": "old forest"}) as claude:
            self.assertEqual(antiguo.consulta(self.escenas[0])["visual"], "old forest")
            claude.assert_called_once()

    def test_chatgpt_delega_en_el_selector_con_prioridad_configurada(self):
        motor = Mock()
        motor.seleccionar_recursos.return_value = {"visual": "forest"}
        with patch.object(bibliotecas.medios, "motor", return_value=motor) as cargar:
            self.assertEqual(bibliotecas._agente_chatgpt("Busca"), {"visual": "forest"})
        cargar.assert_called_once_with("imagen_openai/imagen.py")
        motor.seleccionar_recursos.assert_called_once_with("Busca")

    def test_reparto_sin_escenas_buscables(self):
        self.config.update(incorporar_ia=True, ia_cada=1, carga_claude=50)
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        self.assertEqual(b.agentes, {})

    def test_adaptadores_cache_y_credenciales_no_se_persisten(self):
        almacen = {p: {"clave": "secreto-prueba"} for p in ("pixabay", "pexels")}
        ejemplos = [
            ("pixabay", "imagen", {"hits": [{"id": 1, "user": "Ana", "tags": "forest",
                "pageURL": "https://pixabay.com/photos/1/", "largeImageURL": "https://cdn.pixabay.com/1.jpg"}]}),
            ("pexels", "video", {"videos": [{"id": 2, "duration": 9,
                "url": "https://www.pexels.com/video/2/", "user": {"name": "Luis"},
                "video_files": [{"width": 1920, "height": 1080, "file_type": "video/mp4",
                                  "link": "https://videos.pexels.com/2.mp4"}]}]}),
        ]
        with patch.object(bibliotecas.claves, "leer", return_value=almacen), patch.dict(
                os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(bibliotecas.requests, "get") as get:
            for proveedor, tipo, datos in ejemplos:
                get.return_value = Mock(status_code=200, json=lambda: datos)
                r = bibliotecas.buscar(proveedor, tipo, "forest", False, self.temporal.name)
                self.assertEqual(r[0]["fuente"], proveedor)
                self.assertEqual(r[0]["tipo"], tipo)
                antes = get.call_count
                self.assertEqual(bibliotecas.buscar(proveedor, tipo, "forest", False, self.temporal.name), r)
                self.assertEqual(get.call_count, antes)
            for ruta in Path(self.temporal.name).glob("*.json"):
                self.assertNotIn("secreto-prueba", ruta.read_text())
            get.return_value = Mock(status_code=429)
            with self.assertRaisesRegex(RuntimeError, "HTTP 429") as fallo:
                bibliotecas.buscar("pixabay", "imagen", "other", False, self.temporal.name)
            self.assertNotIn("secreto-prueba", str(fallo.exception))

    def test_seleccion_respeta_fuentes_y_tipos_y_no_repite_recurso(self):
        self.config.update(proveedores=["pexels"], imagenes=False, video=True)
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        poster = Path(self.temporal.name) / "poster.png"
        video = Path(self.temporal.name) / "video.mp4"
        Image.new("RGB", (320, 180), "green").save(poster)
        video.touch()
        recurso = {"fuente": "pexels", "id": "1", "tipo": "video",
                   "descarga": "https://videos.pexels.com/1.mp4"}
        destino = str(Path(self.temporal.name) / "resultado.png")
        with patch.object(b, "consulta", return_value={"visual": "forest"}), patch.object(
                bibliotecas, "buscar", return_value=[recurso]) as buscar, patch.object(
                bibliotecas, "_agente", return_value={"indice": 0}), patch.object(
                bibliotecas, "descargar"), patch.object(bibliotecas.medios_escena,
                "preparar", return_value={"tipo": "video", "archivo": str(video), "poster": str(poster)}):
            ficha = b.visual(self.escenas[0], destino)
            self.assertEqual(ficha["medio_biblioteca"]["tipo"], "video")
            self.assertTrue(Path(destino).is_file())
            self.assertEqual(buscar.call_args.args[:2], ("pexels", "video"))
            self.assertIsNone(b.visual(self.escenas[1], destino))

    def test_falta_de_resultados_o_recurso_inadecuado_dejan_paso_a_codex(self):
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        with patch.object(b, "consulta", return_value={"visual": "forest"}), patch.object(
                bibliotecas, "buscar", return_value=[]):
            self.assertIsNone(b.visual(self.escenas[0], "sin.png"))
        self.assertIn("Codex", self.avisar.call_args.args[1])

    @unittest.skipUnless(shutil.which("ffmpeg"), "requiere ffmpeg")
    def test_video_de_biblioteca_se_materializa_sin_pista_de_audio(self):
        original = str(Path(self.temporal.name) / "con_audio.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
            "color=c=blue:s=320x180:r=30", "-f", "lavfi", "-i", "sine=frequency=400",
            "-t", "2.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", original],
            check=True, capture_output=True, timeout=30)
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        recurso = {"fuente": "pexels", "id": "video-real", "tipo": "video",
                   "descarga": "https://videos.pexels.com/test.mp4"}
        with patch.object(b, "consulta", return_value={"visual": "forest"}), patch.object(
                bibliotecas, "buscar", return_value=[recurso]), patch.object(
                bibliotecas, "_agente", return_value={"indice": 0}), patch.object(
                bibliotecas, "descargar", side_effect=lambda url, destino: shutil.copyfile(original, destino)):
            resultado = b.visual(self.escenas[0], str(Path(self.temporal.name) / "resultado.png"))
        medio = resultado["medio_biblioteca"]
        lectura = subprocess.run([bibliotecas.medios.ffprobe(), "-v", "error", "-show_entries",
            "stream=codec_type", "-of", "json", medio["archivo"]], capture_output=True,
            check=True, text=True, timeout=30)
        self.assertNotIn('"audio"', lectura.stdout)
        self.assertIn('"video"', lectura.stdout)
        self.assertTrue(Path(medio["poster"]).is_file())

    def test_ia_del_modo_mixto_respeta_el_motor_con_prioridad_y_respaldo(self):
        p = p6_assets._con_defectos(self.params)
        p["banco_imagenes"] = str(Path(self.temporal.name) / "cache_ia")
        png = io.BytesIO()
        Image.new("RGB", (320, 180), "red").save(png, format="PNG")
        motor = Mock()
        motor.TAMANOS = {"apaisado": [1536, 1024]}
        motor.proveedor_imagen.return_value = "api"
        motor.generar.return_value = (png.getvalue(), {"coste": .02, "segundos": 1,
                                                     "proveedor": "api", "respaldo_de": "codex"})
        with patch.object(p6_assets.medios, "motor", return_value=motor), patch.object(
                p6_assets, "_adoptar", return_value=None):
            ficha = p6_assets._producir_imagen("S003", "forest", [],
                str(Path(self.temporal.name) / "ia.png"), p)
        motor.generar.assert_called_once_with("forest", [], quality=p["calidad"], tamano="apaisado")
        motor.codex.return_value.generar.assert_not_called()
        self.assertEqual(ficha["proveedor"], "api")
        self.assertEqual(ficha["respaldo_de"], "codex")
        self.assertEqual(ficha["coste"], .02)

    def test_efectos_locales_sin_surtido_y_limitados_a_su_escena(self):
        ficha = {"fuente": "freesound", "id": "17", "archivo": "sonido-local.mp3"}
        self.escenas[1]["audio_biblioteca"] = ficha
        with patch.object(sonido, "vetados", return_value=set()):
            eventos = sonido.eventos(self.escenas, {}, {})
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["t"], 3)
        self.assertEqual(eventos[0]["duracion"], 3)
        self.assertEqual(eventos[0]["ficha"]["archivo"], "sonido-local.mp3")

    def test_audio_seleccionado_se_guarda_en_el_proyecto_y_se_reutiliza(self):
        self.config["audio"] = True
        b = bibliotecas.Biblioteca(self.proyecto, self.params, self.plan, self.avisar)
        original = Path(self.temporal.name) / "efecto.mp3"
        original.write_bytes(b"audio de prueba")
        ficha = {"fuente": "freesound", "id": "17", "titulo": "Forest birds",
                 "descarga": "https://freesound.org/17.mp3"}
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(
                b, "consulta", return_value={"audio": "forest birds"}), patch.object(
                bibliotecas.sonido, "buscar_efectos", return_value=[ficha]) as buscar, patch.object(
                bibliotecas.sonido, "vetados", return_value=set()), patch.object(
                bibliotecas.sonido, "traer", return_value=str(original)), patch.object(
                bibliotecas, "_agente", return_value={"indice": 0}) as seleccionar:
            b.audio(self.escenas[0])
            b.audio(self.escenas[1])
            buscar.assert_called_once()
            seleccionar.assert_called_once()
        for escena in self.escenas[:2]:
            ruta = Path(escena["audio_biblioteca"]["archivo"])
            self.assertTrue(ruta.is_relative_to(self.proyecto.raiz))
            self.assertEqual(ruta.read_bytes(), b"audio de prueba")

    def test_mezcla_usa_audio_local_y_no_invade_la_escena_siguiente(self):
        ruta = Path(self.temporal.name) / "sonido.mp3"
        ruta.touch()
        evento = {"t": 1, "duracion": 1, "ganancia": 0.3,
                  "ficha": {"fuente": "freesound", "id": "17", "archivo": str(ruta)}}
        with patch.object(sonido, "FRECUENCIA", 10), patch.object(
                sonido, "_a_wav", return_value=str(ruta)), patch.object(
                sonido, "_leer", return_value=np.ones((100, 2), dtype=np.float32)), patch.object(
                sonido, "_escribir") as escribir:
            _, usados = sonido.pista_de_efectos([evento], 4, "mezcla.wav", igualar=False)
        self.assertEqual(usados, 1)
        mezcla = escribir.call_args.args[1]
        self.assertTrue(np.all(mezcla[:10] == 0))
        self.assertTrue(np.all(mezcla[10:20] > 0))
        self.assertTrue(np.all(mezcla[20:] == 0))

    def test_duplicar_conserva_recursos_y_adapta_sus_metadatos(self):
        carpeta = Path(self.proyecto.raiz) / "recursos_biblioteca" / "recurso"
        carpeta.mkdir(parents=True)
        imagen = carpeta / "imagen.png"
        Image.new("RGB", (32, 18), "blue").save(imagen)
        bibliotecas.medios.escribir_json(str(carpeta / "medio.json"), {
            "tipo": "imagen", "archivo": str(imagen), "poster": str(imagen)})
        copia = self.proyecto.duplicar(self.temporal.name, "Copia")
        metadata = bibliotecas.medios.leer_json(copia.ruta(
            "recursos_biblioteca", "recurso", "medio.json"))
        self.assertTrue(Path(metadata["archivo"]).is_relative_to(copia.raiz))
        self.assertTrue(Path(metadata["archivo"]).is_file())

    def test_integracion_mixta_y_retomar_no_vuelve_a_buscar_ni_generar(self):
        p = p6_assets._con_defectos(self.params)
        trabajo = self.proyecto.ruta_trabajo("assets")
        dirs = {k: str(Path(trabajo) / k) for k in ("escenas", "componentes", "cache")}
        for ruta in dirs.values():
            Path(ruta).mkdir(parents=True, exist_ok=True)
        motor = Mock()
        motor.codex.return_value.concurrencia.return_value = 1

        def stock(self_b, escena, destino):
            if self_b.turnos[escena["id"]]:
                return None
            Image.new("RGB", (320, 180), "green").save(destino)
            medio = {"tipo": "imagen", "archivo": destino, "poster": destino}
            escena["medio_biblioteca"] = medio
            recurso = {"fuente": "pixabay", "tipo": "imagen", "id": escena["id"]}
            escena["recurso_biblioteca"] = recurso
            return {"origen": "biblioteca", "coste": 0, "medio_biblioteca": medio,
                    "recurso_biblioteca": recurso, "bibliotecas_peticion": bibliotecas.medios.huella(
                        {k: escena.get(k) for k in ("narracion", "direccion", "prompt")})}

        def ia(sid, prompt, referencias, destino, params, **kwargs):
            Image.new("RGB", (320, 180), "red").save(destino)
            return {"origen": "codex", "coste": 0}

        with patch.object(p6_assets, "bibliotecas", bibliotecas), patch.object(
                bibliotecas.Biblioteca, "verificar_claves"), patch.object(
                bibliotecas.Biblioteca, "visual", autospec=True, side_effect=stock) as visual, patch.object(
                p6_assets.medios, "motor", return_value=motor), patch.object(
                p6_assets, "_referencias_escena", return_value=[]), patch.object(
                p6_assets, "_prompt_completo", return_value="forest"), patch.object(
                p6_assets, "_producir_imagen", side_effect=ia) as generar:
            resultados = {}
            p6_assets._generar_escenas(self.plan, dirs, p, trabajo, lambda _: True,
                None, resultados, self.avisar, proyecto=self.proyecto)
            self.assertEqual([c.args[0] for c in generar.call_args_list], ["S003", "S006"])
            self.assertEqual(sum(f["origen"] == "biblioteca" for f in resultados.values()), 4)
            visual.reset_mock()
            generar.reset_mock()
            p6_assets._generar_escenas(self.plan, dirs, p, trabajo, lambda _: True,
                None, {}, self.avisar, proyecto=self.proyecto)
            visual.assert_not_called()
            generar.assert_not_called()
            # Los params actuales de las bibliotecas pueden haber cambiado
            # desde que se eligieron los recursos; una tanda de montaje normal
            # conserva los recursos ya descargados y solo rehace la unidad pedida.
            p["bibliotecas"]["ia_cada"] = 4
            p["bibliotecas"]["proveedores"] = ["pexels"]
            p6_assets._generar_escenas(self.plan, dirs, p, trabajo, lambda _: True,
                None, {}, self.avisar, proyecto=self.proyecto)
            visual.assert_not_called()
            generar.assert_not_called()

            # Una nota pide IA aunque el plano tuviera un clip propio o fuera
            # uno de los turnos de biblioteca. Solo cambia esa unidad.
            p["unidades"] = {"escena:S002": {"generar_ia": True,
                "medio_usuario": None, "feedback": "Sustituye la escena por un bosque nevado"}}
            self.escenas[1]["medio_usuario"] = {"tipo": "video", "archivo": "clip_anterior.mp4"}
            with patch.object(p6_assets, "_corregir_con_agente", return_value=None):
                rehechas = {}
                p6_assets._generar_escenas(self.plan, dirs, p, trabajo, lambda _: True,
                    ["escena:S002"], rehechas, self.avisar, forzar=True, proyecto=self.proyecto)
            generar.assert_called_once()
            self.assertEqual(generar.call_args.args[0], "S002")
            visual.assert_not_called()
            for clave in ("medio_usuario", "medio_biblioteca", "recurso_biblioteca"):
                self.assertNotIn(clave, self.escenas[1])
                self.assertNotIn(clave, rehechas["escena:S002"])
            with Image.open(Path(dirs["escenas"]) / "S002.png") as imagen:
                self.assertEqual(imagen.getpixel((0, 0)), (255, 0, 0))
            generar.reset_mock()
            p6_assets._generar_escenas(self.plan, dirs, p, trabajo, lambda _: True,
                ["escena:S001"], {}, self.avisar, proyecto=self.proyecto)
            visual.assert_not_called()
            generar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
