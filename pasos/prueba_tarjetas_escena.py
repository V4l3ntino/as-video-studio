"""Dos recursos exclusivos por escena, generación y reanudación sin servicios reales."""
import copy
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from unittest.mock import MagicMock

AISLADO = tempfile.TemporaryDirectory(prefix="prueba_tarjetas_")
for variable in ("ESTUDIO_ESTADISTICAS", "ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES"):
    os.environ[variable] = os.path.join(AISLADO.name, variable)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import animaciones
import p6_assets
from _proyecto_animaciones import construir


class TarjetasEscena(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=AISLADO.name)
        self.addCleanup(self.tmp.cleanup)
        self.proyecto, self.estado = construir(self.tmp.name)
        self.plan = p6_assets.plan_actual(self.proyecto)
        for escena in self.plan["escenas"]:
            escena.pop("tarjetas_animacion", None)
            escena["prompt"] = "Illustrate this scene."
        self.plan["assets"] = {}
        self.plan["dependencias"] = {}
        p6_assets._planificar_tarjetas(self.proyecto, self.plan)
        self.trabajo = os.path.join(self.tmp.name, "generacion")
        self.dirs = {k: os.path.join(self.trabajo, k) for k in ("escenas", "componentes", "cache")}
        for ruta in self.dirs.values():
            os.makedirs(ruta)
        self.params = p6_assets._con_defectos({"cadenas": 1})
        self.llamadas = []
        self.numero = 0
        self.mismo_png = False
        self.fallar_extra = False

    def producir(self, nombre, prompt, referencias, destino, params, **opciones):
        self.llamadas.append((nombre, prompt))
        if self.fallar_extra and nombre.endswith("__tarjeta"):
            raise RuntimeError("interrupción de prueba")
        self.numero += 1
        color = (100, 50, 0) if self.mismo_png else (15 * self.numero, 50, 0)
        Image.new("RGB", (32, 24), color).save(destino)
        return {"origen": "generada", "coste": 0.1}

    def generar(self, unidades=None, forzar=False):
        resultados = {}
        with patch.object(p6_assets, "_referencias_escena", return_value=[]), \
                patch.object(p6_assets, "_producir_imagen", side_effect=self.producir):
            coste = p6_assets._generar_escenas(self.plan, self.dirs, self.params,
                self.trabajo, lambda _: True, unidades, resultados, lambda *_: None,
                forzar=forzar, proyecto=self.proyecto)
        return coste, resultados

    def test_reserva_solo_las_escenas_de_dos_tarjetas(self):
        self.assertEqual([e["id"] for e in self.plan["escenas"] if e.get("tarjetas_animacion")],
                         ["S003", "S004"])
        self.assertEqual(len(self.plan["escenas"]), 5)

    def test_dos_recursos_y_retomar_sin_repagar(self):
        coste, resultados = self.generar()
        self.assertAlmostEqual(coste, 0.7)
        self.assertEqual(len(self.llamadas), 7)
        self.assertEqual(len(resultados), 5)
        for sid in ("S003", "S004"):
            ficha = resultados[f"escena:{sid}"]
            self.assertNotEqual(ficha["png"], ficha["tarjeta"]["png"])
            self.assertTrue(os.path.isfile(os.path.join(self.trabajo, ficha["tarjeta"]["png"])))
        self.assertFalse(p6_assets._planos_repetidos(
            {nombre: {"tipo": "escena", "png": os.path.relpath(os.path.join(self.dirs["escenas"], nombre + ".png"), self.trabajo)}
             for nombre, _ in self.llamadas}, self.trabajo))
        antes = copy.deepcopy(self.llamadas)
        coste, resultados = self.generar()
        self.assertEqual(coste, 0)
        self.assertEqual(self.llamadas, antes)
        self.assertIn("tarjeta", resultados["escena:S003"])

    def test_rehacer_una_escena_solo_rehace_su_pareja(self):
        self.generar()
        self.llamadas.clear()
        self.generar(["escena:S004"], forzar=True)
        self.assertEqual({nombre for nombre, _ in self.llamadas}, {"S004", "S004__tarjeta"})
        self.assertIn("RAÍCES SANAS", self.llamadas[0][1])
        self.assertIn("RAÍCES ATROFIADAS", self.llamadas[1][1])

    def test_interrupcion_conserva_la_primera_imagen(self):
        self.fallar_extra = True
        with self.assertRaisesRegex(RuntimeError, "interrupción"):
            self.generar()
        anteriores = [nombre for nombre, _ in self.llamadas if not nombre.endswith("__tarjeta")]
        self.fallar_extra = False
        self.llamadas.clear()
        self.generar()
        self.assertFalse(set(anteriores) & {nombre for nombre, _ in self.llamadas})

    def test_rehacer_una_pareja_no_completa_la_pendiente_de_otra_escena(self):
        self.generar()
        os.unlink(os.path.join(self.dirs["escenas"], "S003__tarjeta.png"))
        self.llamadas.clear()
        self.generar(["escena:S004"], forzar=True)
        self.assertEqual({nombre for nombre, _ in self.llamadas}, {"S004", "S004__tarjeta"})
        self.assertFalse(os.path.exists(os.path.join(self.dirs["escenas"], "S003__tarjeta.png")))

    def test_no_acepta_repetir_imagenes(self):
        self.mismo_png = True
        with self.assertRaisesRegex(RuntimeError, "exclusivas"):
            self.generar()

    def test_reserva_manual_esta_anclada_al_texto(self):
        escena = self.plan["escenas"][0]
        edicion = {"id": "collage-titulo", "ancla": animaciones.ancla_de(escena),
                   "contenido": {"nombre": "PUERTO"}}
        params = {"unidades": {"escena:S001": {"tarjetas_animacion": edicion}}}
        p6_assets._planificar_tarjetas(self.proyecto, self.plan, params)
        self.assertEqual(escena["tarjetas_animacion"]["datos"], edicion["contenido"])

    def test_editor_reserva_la_segunda_imagen_sin_generarla_ni_tocar_otras_escenas(self):
        import app as servidor
        escena = self.plan["escenas"][0]
        ctx = SimpleNamespace(proyecto=self.proyecto, estado=self.estado,
                              gestor=MagicMock(), bitacora=MagicMock())
        ctx.gestor.listar.return_value = []
        edicion = {"id": "comparacion-tarjetas", "ancla": animaciones.ancla_de(escena),
                   "contenido": {"izquierda": "PUERTO", "derecha": "MAR"}}
        firma = self.estado.firma_unidad("assets", "escena:S002")
        with patch.object(servidor, "contexto", return_value=ctx), \
                patch.object(servidor, "_plan_de_previsualizacion", return_value=self.plan), \
                patch.object(servidor, "_audio_de_la_toma", return_value=None), \
                patch.object(p6_assets, "_producir_imagen") as generar:
            previa = servidor.editar_animacion_escena(self.proyecto.id, "S001", edicion)
        generar.assert_not_called()
        self.assertEqual(self.estado.params("assets")["unidades"]["escena:S001"]["tarjetas_animacion"], edicion)
        self.assertEqual(self.estado.firma_unidad("assets", "escena:S002"), firma)
        # Una pareja pendiente no debe ocultar las otras animaciones de la previa.
        self.assertTrue(next(e for e in previa["escenas"] if e["id"] == "S002").get("animacion"))


if __name__ == "__main__":
    unittest.main()
