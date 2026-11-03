"""Contrato de publicación: sin CLI ni generación de imágenes reales.

    python pasos/prueba_publicacion.py
"""
import io
import contextlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_aislado = tempfile.TemporaryDirectory(prefix="publicacion_config_")
for _variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS"):
    os.environ[_variable] = os.path.join(_aislado.name, _variable)

from PIL import Image
from pasos import p6_assets, publicacion


class Publicacion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="publicacion_prueba_")
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = SimpleNamespace(raiz=self.tmp.name,
            ruta=lambda *p: os.path.join(self.tmp.name, *p))
        self.params = {"estilo": {"referencias": []}}
        self.estado = SimpleNamespace(params=lambda _p: self.params)
        self.guion = {"titulo": "Un viaje", "guion": [
            {"id": "B001", "texto": "La partida"}, {"id": "B002", "texto": "La isla"},
            {"id": "B003", "texto": "El regreso"}]}
        self.escenas = [{"id": f"S00{i + 1}", "origen": {"bloque": f"B00{i + 1}"},
                         "t_in": i * 20, "t_out": (i + 1) * 20,
                         "narracion": b["texto"]} for i, b in enumerate(self.guion["guion"])]
        self.propuesta = {"titulo": "Una isla y un viaje", "descripcion": "El relato de un viaje.",
            "capitulos": [{"bloque": b["id"], "titulo": b["texto"]} for b in self.guion["guion"]],
            "miniatura_prompt": "Un viajero en una isla", "escenas_referencia": ["S001"],
            "miniatura_texto": "¿UNA ISLA VIVA?", "miniatura_subtitulo": "El viaje inesperado"}
        imagen = Image.new("RGB", (1536, 1024), "#6e8ca1")
        buf = io.BytesIO()
        imagen.save(buf, "PNG")
        self.png = buf.getvalue()
        self.llamadas = {"texto": 0, "imagen": 0}
        self.fallar_imagen = False
        self.instrucciones = []
        self.prompts = []
        def redactar(instruccion, *_a):
            self.instrucciones.append(instruccion)
            self.llamadas["texto"] += 1
            return json.dumps(self.propuesta), {}
        def dibujar(prompt, *_a, **_k):
            self.prompts.append(prompt)
            self.llamadas["imagen"] += 1
            if self.fallar_imagen:
                raise RuntimeError("serverOverloaded")
            return self.png, {}
        parches = [patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}),
            patch.object(publicacion.comun, "leer_salida", return_value=self.guion),
            patch.object(p6_assets, "plan_actual", return_value={"escenas": self.escenas}),
            patch.object(p6_assets, "planos_hechos", return_value={}),
            patch.object(publicacion, "_llamar_claude", side_effect=redactar),
            patch.object(publicacion.medios, "motor", return_value=SimpleNamespace(generar=dibujar))]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)

    def preparar(self, parte="pendientes"):
        return publicacion.preparar(self.proyecto, self.estado, lambda *_a: None, parte)

    def test_prepara_descargas_y_no_regenera_al_abrir_o_repetir(self):
        datos = self.preparar()
        self.assertTrue(datos["completo"])
        self.assertIn("0:00 La partida\n0:20 La isla\n0:40 El regreso", datos["descripcion"])
        with Image.open(self.proyecto.ruta(datos["miniatura"])) as img:
            self.assertEqual(img.size, (1280, 720))
            self.assertEqual(img.format, "JPEG")
        self.assertLess(os.path.getsize(self.proyecto.ruta(datos["miniatura"])), 2 * 1024 * 1024)
        self.preparar()
        publicacion.leer(self.proyecto, self.estado)
        self.assertEqual(self.llamadas, {"texto": 1, "imagen": 1})
        self.assertEqual(self.params, {"estilo": {"referencias": []}})

    def test_fallo_miniatura_conserva_textos_y_reintenta_solo_imagen(self):
        self.fallar_imagen = True
        with self.assertRaisesRegex(RuntimeError, "serverOverloaded"):
            self.preparar()
        datos = publicacion.leer(self.proyecto, self.estado)
        self.assertEqual(datos["titulo"], self.propuesta["titulo"])
        self.assertIn("serverOverloaded", datos["error_miniatura"])
        self.fallar_imagen = False
        self.assertTrue(self.preparar()["completo"])
        self.assertEqual(self.llamadas, {"texto": 1, "imagen": 2})

    def test_edicion_y_cambio_de_guion_no_sobrescriben_lo_revisado(self):
        anterior = self.preparar()
        publicacion.editar(self.proyecto, self.estado, {"titulo": "Mi título"})
        self.guion["guion"][0]["texto"] = "Otro comienzo"
        datos = publicacion.leer(self.proyecto, self.estado)
        self.assertTrue(datos["texto_obsoleto"])
        self.assertTrue(datos["miniatura_obsoleta"])
        self.assertEqual(self.preparar()["titulo"], "Mi título")
        self.assertEqual(self.llamadas, {"texto": 1, "imagen": 1})
        nueva = self.preparar("miniatura")
        self.assertEqual(nueva["titulo"], "Mi título")
        self.assertNotEqual(nueva["miniatura"], anterior["miniatura"])
        self.assertTrue(os.path.isfile(self.proyecto.ruta(anterior["miniatura"])))
        self.assertEqual(self.llamadas, {"texto": 2, "imagen": 2})

    def test_limites_y_capitulos_no_inventan_tiempos(self):
        for cambios in ({"titulo": "x" * 101}, {"descripcion": "x" * 5001},
                        {"titulo": ""}, {"titulo": "<script>"}):
            with self.assertRaises(ValueError):
                publicacion.editar(self.proyecto, self.estado, cambios)
        escenas = publicacion.fuentes(self.proyecto, self.estado)["escenas"]
        self.assertEqual(publicacion._capitulos([
            {"bloque": "no_existe", "titulo": "Inventado"}], escenas), "")
        self.propuesta["titulo"] = "x" * 101
        with self.assertRaises(ValueError):
            self.preparar()
        self.assertEqual(self.llamadas["imagen"], 0)

    def test_la_receta_conserva_el_mp4_si_falla_y_respeta_cancelar(self):
        import app
        from nucleo.trabajos import Cancelado
        ctx = SimpleNamespace(proyecto=self.proyecto, estado=self.estado,
                              bitacora=SimpleNamespace(anotar=Mock()))
        modulo = SimpleNamespace(preparar=Mock(side_effect=RuntimeError("sin servicio")))
        with patch.object(app, "_publicacion", return_value=modulo), \
             patch.object(app.COSTE, "contexto", return_value=contextlib.nullcontext()):
            funcion, args = app._que_hace("publicacion", ctx, {})
            resultado = funcion(lambda *_a: None, *args)
            self.assertIn("pendiente", resultado["resumen"])
            ctx.bitacora.anotar.assert_called_once()
            with self.assertRaisesRegex(RuntimeError, "sin servicio"):
                app._correr_publicacion(lambda *_a: None, ctx)
            modulo.preparar.side_effect = Cancelado("cancelado")
            with self.assertRaises(Cancelado):
                funcion(lambda *_a: None, *args)

    def test_miniatura_editorial_exige_textos_y_actualiza_conceptos_antiguos(self):
        datos = self.preparar()
        self.assertIn("ilustración Y TEXTO", self.instrucciones[0])
        self.assertIn('"¿UNA ISLA VIVA?"', self.prompts[0])
        self.assertIn('"El viaje inesperado"', self.prompts[0])
        self.assertIn("LARGE DESIGNED TYPOGRAPHY", self.prompts[0])
        self.assertIn("takes precedence", self.prompts[0])
        publicacion.editar(self.proyecto, self.estado, {"titulo": "Mi título revisado"})
        publicacion._guardar(self.proyecto, {"version_diseno": 1, "miniatura_texto": ""})
        # Abrir o volver a montar no redibuja ni sobrescribe lo editado.
        self.assertEqual(self.preparar()["miniatura"], datos["miniatura"])
        nueva = self.preparar("miniatura")
        self.assertEqual(nueva["titulo"], "Mi título revisado")
        self.assertEqual(nueva["miniatura_texto"], "¿UNA ISLA VIVA?")
        self.assertEqual(self.llamadas, {"texto": 2, "imagen": 2})
        self.propuesta["miniatura_texto"] = ""
        with self.assertRaisesRegex(ValueError, "necesita un titular"):
            self.preparar("texto")
        self.assertEqual(self.llamadas["imagen"], 2)


if __name__ == "__main__":
    unittest.main()
