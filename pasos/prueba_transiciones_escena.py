"""Transiciones de salida: persistencia, anclas y contrato con el render, sin red."""
import copy
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_DATOS = tempfile.TemporaryDirectory(prefix="prueba_transiciones_escena_")
for clave, nombre in (("ESTUDIO_SECRETOS", "secretos"), ("ESTUDIO_AJUSTES", "ajustes.json"),
                      ("ESTUDIO_ESTADISTICAS", "estadisticas.json")):
    os.environ[clave] = os.path.join(_DATOS.name, nombre)

import app as servidor  # noqa: E402
from nucleo.estado import Estado  # noqa: E402
from nucleo.proyecto import Proyecto, escribir_json  # noqa: E402
import _proyecto_animaciones as juguete  # noqa: E402
import p8_render  # noqa: E402
import transiciones  # noqa: E402


class TransicionesEscena(unittest.TestCase):
    def setUp(self):
        self.escenas = [{"id": f"S{i:03d}", "narracion": f"Frase {i}.",
                         "duracion": 2, "t_in": 2 * (i - 1), "t_out": 2 * i}
                        for i in range(1, 7)]

    def params(self, tipo):
        edicion = transiciones.validar_edicion({"tipo": tipo,
            "ancla": transiciones.ancla_de(*self.escenas[:2])}, *self.escenas[:2])
        return {"unidades": {"escena:S002": {"transicion": edicion}}}

    def test_salida_se_cuece_en_siguiente_y_no_cambia_vecinas(self):
        base = transiciones.resolver(self.escenas, {}, 7)
        for tipo in transiciones.CATALOGO:
            with self.subTest(tipo=tipo):
                resultado = transiciones.resolver(self.escenas, self.params(tipo), 7)
                self.assertEqual(resultado["S002"]["tipo"], tipo)
                self.assertEqual(resultado["S002"]["shader"], transiciones.frag_de(tipo))
                self.assertLessEqual(resultado["S002"]["duracion"], 0.7)
                self.assertEqual({k: v for k, v in resultado.items() if k != "S002"},
                                 {k: v for k, v in base.items() if k != "S002"})

    def test_sin_paleta_y_continuacion_admiten_edicion_explicita(self):
        params = dict(self.params("glitch"), transiciones_personalizadas=True, transiciones=[])
        self.escenas[1]["sigue_a"] = "S001"
        resultado = transiciones.resolver(self.escenas, params)
        self.assertEqual(resultado["S002"]["tipo"], "glitch")
        self.assertTrue(all(v["tipo"] == "corte" for k, v in resultado.items() if k != "S002"))
        corte = transiciones.resolver(self.escenas, self.params("corte"))["S002"]
        self.assertEqual((corte["shader"], corte["duracion"]), (None, 0))

    def test_ancla_de_los_dos_planos_y_validacion(self):
        params = self.params("glitch")
        for indice in (0, 1):
            otras = copy.deepcopy(self.escenas)
            otras[indice]["narracion"] = "Una frase corregida."
            self.assertEqual(transiciones.resolver(otras, params), transiciones.resolver(otras))
            with self.assertRaisesRegex(ValueError, "han cambiado"):
                transiciones.validar_edicion(params["unidades"]["escena:S002"]["transicion"], *otras[:2])
        for tipo in ("inventada", [], None):
            with self.assertRaises(ValueError):
                transiciones.validar_edicion({"tipo": tipo,
                    "ancla": transiciones.ancla_de(*self.escenas[:2])}, *self.escenas[:2])

    def test_api_lee_sin_mutar_guarda_reabre_y_conserva_otros_ajustes(self):
        with tempfile.TemporaryDirectory() as tmp:
            proyecto, estado = juguete.construir(tmp, animaciones=[], etiquetas={})
            estado.actualizar_params("render", {"unidades": {"escena:S001": {},
                "escena:S002": {"otro_ajuste": "conservar"}, "escena:S003": {}}})
            ctx = SimpleNamespace(proyecto=proyecto, estado=estado, gestor=MagicMock())
            ctx.gestor.listar.return_value = []
            with patch.object(servidor, "contexto", return_value=ctx), \
                 patch.object(servidor, "_audio_de_la_toma", return_value=None):
                antes = Path(proyecto.ruta("estado.json")).read_bytes()
                ficha = servidor.leer_transicion_escena(proyecto.id, "S001")
                self.assertEqual(Path(proyecto.ruta("estado.json")).read_bytes(), antes)
                self.assertEqual([e["id"] for e in ficha["escenas"]], ["S001", "S002"])
                self.assertEqual(len(ficha["transiciones"]), 15)
                self.assertTrue(all(t["frag"] and t["duracion"] > 0 for t in ficha["transiciones"]))
                firmas = {p: estado.firma(p) for p in ("guion", "voz", "assets", "callouts")}
                global_antes = estado.firma_global("render")
                vecinas = {uid: estado.firma_unidad("render", uid) for uid in ("escena:S001", "escena:S003")}
                for tipo in ("glitch", "corte", "sdf-iris"):
                    previa = servidor.editar_transicion_escena(proyecto.id, "S001",
                        {"tipo": tipo, "ancla": ficha["ancla"]})
                    self.assertEqual(previa["escenas"][0]["transicion"]["tipo"], tipo)
                    self.assertTrue(previa["escenas"][0]["transicion"]["personalizada"])
                    ctx.estado = estado = Estado(proyecto)
                    reabierta = servidor.leer_transicion_escena(proyecto.id, "S001")
                    self.assertEqual(reabierta["actual"]["tipo"], tipo)
                    self.assertEqual(estado.params("render")["unidades"]["escena:S002"]["otro_ajuste"], "conservar")
                self.assertEqual({p: estado.firma(p) for p in firmas}, firmas)
                self.assertEqual(estado.firma_global("render"), global_antes)
                self.assertEqual({uid: estado.firma_unidad("render", uid) for uid in vecinas}, vecinas)
                for sid, codigo in (("S005", 400), ("ausente", 404)):
                    with self.assertRaises(servidor.ErrorApi) as error:
                        servidor.leer_transicion_escena(proyecto.id, sid)
                    self.assertEqual(error.exception.codigo, codigo)
                antes = Path(proyecto.ruta("estado.json")).read_bytes()
                with self.assertRaises(servidor.ErrorApi) as error:
                    servidor.editar_transicion_escena(proyecto.id, "S001", {"tipo": "glitch", "ancla": "vieja"})
                self.assertEqual(error.exception.codigo, 400)
                ctx.gestor.listar.return_value = [{"nombre": "render"}]
                with self.assertRaises(servidor.ErrorApi) as error:
                    servidor.editar_transicion_escena(proyecto.id, "S001", {"tipo": "glitch", "ancla": ficha["ancla"]})
                self.assertEqual(error.exception.codigo, 409)
                self.assertEqual(Path(proyecto.ruta("estado.json")).read_bytes(), antes)

    def test_render_recibe_shader_manual_y_corte_sin_efecto(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            proyecto = Proyecto.crear(tmp, "Montaje")
            imagen = proyecto.ruta("imagen.png")
            Image.new("RGB", (160, 90), "red").save(imagen)
            escenas = self.escenas[:3]
            plan, movimiento = proyecto.ruta("plan.json"), proyecto.ruta("movimiento.json")
            escribir_json(plan, {"escenas": escenas, "resolucion": [160, 90]})
            escribir_json(movimiento, {"movimientos": [dict(id=e["id"], hyperframe=imagen,
                capa="ausente.svg", hyperframe_px=[160, 90], ventana_ini=[0, 0, 1, 1], ventana_fin=[0, 0, 1, 1])
                for e in escenas]})
            tareas = []
            def lotes(lista, *args, **kwargs):
                tareas.extend(lista)
                return [{"id": t["id"], "clip": t["clip"], "frames": t["frames"]} for t in lista]
            with patch.object(p8_render, "correr_lote", side_effect=lotes), \
                 patch.object(p8_render, "_concatenar"), \
                 patch.object(p8_render, "_elegir_codec", return_value="libx264"):
                for tipo in ("glitch", "corte"):
                    tareas.clear()
                    p8_render.ejecutar(proyecto, dict(self.params(tipo), plan=plan, movimiento=movimiento,
                        sonido=False, lotes=1, fps=6))
                    corte = tareas[1]["corte"]
                    self.assertEqual(corte["tipo"], tipo)
                    self.assertEqual(corte["shader"], transiciones.frag_de(tipo))
                    self.assertEqual(corte["duracion"], transiciones.duracion_de(tipo, escenas[1]))


if __name__ == "__main__":
    unittest.main()
