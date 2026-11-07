"""La imagen y el visto de su nota se sellan en el mismo trabajo, también sin navegador."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_datos = tempfile.TemporaryDirectory(prefix="prueba_notas_imagen_")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for nombre, ruta in (("ESTUDIO_SECRETOS", "secretos"),
                     ("ESTUDIO_ESTADISTICAS", "estadisticas.json"),
                     ("ESTUDIO_AJUSTES", "ajustes.json")):
    os.environ[nombre] = str(Path(_datos.name) / ruta)

import app
from nucleo.proyecto import Proyecto
from pasos import repaso


class RegeneracionNotas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="notas_escena_")
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = Proyecto.crear(self.tmp.name, "Notas")
        self.ctx = SimpleNamespace(proyecto=self.proyecto)
        self.nota = repaso.anadir(self.proyecto, "Cambia el plano", 2.0, plano="S001",
                                 pantalla="imagenes")
        self.pedido = {"id": self.nota["id"], "plano": "S001", "texto": self.nota["texto"]}

    def test_se_confirma_solo_al_producir_la_escena(self):
        self.assertEqual(app._confirmar_notas_imagen(self.ctx, [self.pedido], {}), [])
        self.assertEqual(repaso.leer(self.proyecto)["notas"][0]["estado"], "pendiente")
        self.assertEqual(app._confirmar_notas_imagen(self.ctx, [self.pedido],
                         {"escena:S001": {"png": "escenas/S001.png"}}), [self.nota["id"]])
        self.assertEqual(repaso.leer(self.proyecto)["notas"][0]["estado"], "aplicado")

    def test_no_confirma_una_nota_editada_durante_la_generacion(self):
        repaso.editar(self.proyecto, self.nota["id"], texto="Otro cambio")
        self.assertEqual(app._confirmar_notas_imagen(self.ctx, [self.pedido],
                         {"escena:S001": {"png": "escenas/S001.png"}}), [])
        self.assertEqual(repaso.leer(self.proyecto)["notas"][0]["estado"], "pendiente")


if __name__ == "__main__":
    unittest.main()
