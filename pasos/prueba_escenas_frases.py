"""Contrato editorial y montaje de una frase completa por escena, sin red."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

AISLADO = tempfile.TemporaryDirectory(prefix="prueba_escenas_frases_")
for variable, nombre in (("ESTUDIO_SECRETOS", "secretos"),
                         ("ESTUDIO_AJUSTES", "ajustes.json"),
                         ("ESTUDIO_ESTADISTICAS", "estadisticas.json")):
    os.environ[variable] = os.path.join(AISLADO.name, nombre)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import comun
import medios
import p3_guion
import p4_voz
import p5_revision_audio
import p6_assets
from nucleo import Estado, Proyecto

segmentar = medios.motor("guion/segmentar.py")


def marcas(texto, paso=.4):
    return [{"w": w, "s": round(i * paso, 3), "e": round((i + 1) * paso, 3)}
            for i, w in enumerate(texto.split())]


class FrasesCompletas(unittest.TestCase):
    def test_punto_y_mayuscula_en_cada_frase(self):
        self.assertEqual(segmentar.frases_del_texto("Una frase. Otra frase."),
                         ["Una frase.", "Otra frase."])
        for texto in ("una frase.", "Una frase", "Una frase,", "Una frase. otra.",
                      "Una pregunta?", "¿Una pregunta?.", "Una pausa...", "Una sorpresa!."):
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                segmentar.frases_del_texto(texto)

    def test_abreviaturas_y_comillas_no_inventan_escenas(self):
        self.assertEqual(segmentar.frases_del_texto('El Dr. López llegó. «Todo está listo».'),
                         ['El Dr. López llegó.', '«Todo está listo».'])
        self.assertEqual(segmentar.frases_del_texto('J. R. Tolkien escribió el relato.'),
                         ['J. R. Tolkien escribió el relato.'])

    def test_una_frase_larga_no_se_parte_por_comas_ni_por_el_maximo(self):
        texto = "Una narración larga, con una pausa interna, permanece en su propia escena."
        reporte = {}
        segmentos = segmentar.segmentar_frases(marcas(texto, 1), [texto], 1, 4,
                                               reparto=reporte)
        self.assertEqual(len(segmentos), 1)
        self.assertEqual(" ".join(p["w"] for p in segmentos[0][2]), texto)
        self.assertFalse(reporte["maximo_respetado"])
        self.assertTrue(reporte["por_frases"])

    def test_dos_frases_cortas_no_se_funden_para_alcanzar_el_minimo(self):
        texto = "Llegó. Esperó."
        segmentos = segmentar.segmentar_frases(marcas(texto), [texto], 3, 6, reparto={})
        self.assertEqual(len(segmentos), 2)

    def test_la_puntuacion_y_las_mayusculas_salen_del_guion_no_del_tts(self):
        texto = "Una frase termina. Otra frase empieza."
        tts = marcas(texto.lower().replace(".", ""))
        segmentos = segmentar.segmentar_frases(tts, [texto], reparto={})
        self.assertEqual([" ".join(p["w"] for p in seg[2]) for seg in segmentos],
                         ["Una frase termina.", "Otra frase empieza."])
        escenas = segmentar.construir_escenas(segmentos)
        p6_assets._encadenar(escenas, None, .25, .45, segmentar)
        self.assertGreaterEqual(escenas[1]["t_in"], tts[2]["e"])
        self.assertLessEqual(escenas[1]["t_in"], tts[3]["s"])

    def test_tokens_unidos_o_separados_conservan_los_tiempos_reales(self):
        tts = [{"w": "NuevaYork", "s": 1., "e": 2.},
               {"w": "espera", "s": 2.1, "e": 2.8}]
        segmentos = segmentar.segmentar_frases(tts, ["Nueva York espera."], reparto={})
        self.assertEqual(segmentos[0][:2], (1., 2.8))
        self.assertEqual(segmentos[0][2][0]["s"], 1.)
        self.assertEqual(segmentos[0][2][1]["e"], 2.)

    def test_no_se_adivina_una_frontera_sin_marca_real(self):
        with self.assertRaisesRegex(ValueError, "cruza el punto"):
            segmentar.segmentar_frases(marcas("LlegóEsperó"), ["Llegó. Esperó."])
        with self.assertRaisesRegex(ValueError, "no coinciden"):
            segmentar.segmentar_frases(marcas("Una palabra distinta"), ["Otra frase."])

    def test_el_reparto_no_depende_de_la_velocidad(self):
        texto = "Una frase breve. Otra frase bastante más larga, con una coma."
        resultados = []
        for paso in (.15, .4, 1.2):
            segmentos = segmentar.segmentar_frases(marcas(texto, paso), [texto], reparto={})
            resultados.append([" ".join(p["w"] for p in s[2]) for s in segmentos])
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(resultados[1], resultados[2])

    def test_ssml_se_ignora_al_validar_y_el_error_se_detecta_antes_de_pagar(self):
        p4_voz.validar_frases([{"id": "B001", "texto": '<emotion value="curiosity"/>Una frase.<break time="500ms"/>'}])
        with patch.object(p4_voz, "sintetizar_toma", side_effect=AssertionError("no pagar")):
            with self.assertRaisesRegex(ValueError, "B001.*mayuscula"):
                p4_voz.sintetizar_bloques(
                    [{"id": "B001", "texto": "una frase."}], AISLADO.name, {},
                    extra_meta={"escenas_por_frase": True})

    def test_el_redactor_detecta_las_frases_incompletas(self):
        self.assertTrue(p3_guion.problemas_de_frases([{"id": "B002", "texto": "Sin final"}]))
        self.assertFalse(p3_guion.problemas_de_frases([{"id": "B002", "texto": "Con final."}]))


class FlujoPorFrases(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=AISLADO.name)
        self.addCleanup(self.temp.cleanup)
        self.proyecto = Proyecto.crear(self.temp.name, "Una frase por escena")
        self.estado = Estado(self.proyecto)
        self.texto = "La puerta se abre, despacio, sin que nadie la toque. Nadie entra."
        self.bloques = [{"id": "B001", "texto": self.texto}]
        comun.escribir_json(os.path.join(self.proyecto.ruta_trabajo("guion"), "guion.json"),
                            {"guion": self.bloques, "idioma": "es", "escenas_por_frase": True})
        self.estado.completar("guion", {"guion_fichero": "guion.json"})

    def grabar(self):
        with patch.object(p4_voz, "simulado", return_value=True):
            salidas = p4_voz.ejecutar(self.proyecto, {})
        self.estado.completar("voz", salidas)
        return salidas

    def test_la_voz_y_el_plan_conservan_el_contrato_sin_heredar_cortes_a_media_frase(self):
        salidas = self.grabar()
        self.assertTrue(salidas["escenas_por_frase"])
        anterior = {"corte": ["La puerta se abre,", "despacio, sin que nadie la toque. Nadie entra."]}
        plan = p6_assets.planificar(self.proyecto, {}, previo=anterior)
        self.assertTrue(plan["escenas_por_frase"])
        self.assertEqual([e["narracion"] for e in plan["escenas"]],
                         ["La puerta se abre, despacio, sin que nadie la toque.", "Nadie entra."])
        self.assertTrue(all(e["frase_completa"] for e in plan["escenas"]))
        self.assertEqual(plan["informe"]["frases_partidas"], 0)

    def test_sellar_la_revision_no_pierde_el_contrato(self):
        self.grabar()
        with patch.object(p4_voz, "sintetizar_bloques", side_effect=AssertionError("no regrabar")):
            salida = p5_revision_audio.ejecutar(self.proyecto, {}, lambda *_: None)
        self.assertTrue(salida["escenas_por_frase"])
        self.assertTrue(salida["sellada_del_paso_4"])

    def test_regrabar_la_revision_tambien_conserva_el_contrato(self):
        self.grabar()
        with patch.object(p4_voz, "simulado", return_value=True):
            salida = p5_revision_audio.ejecutar(
                self.proyecto, {"voz": {"velocidad": "slowest"}}, lambda *_: None)
        self.assertTrue(salida["escenas_por_frase"])
        self.assertFalse(salida.get("sellada_del_paso_4", False))

    def test_las_cartelas_no_pueden_absorber_la_frase_vecina(self):
        self.grabar()
        plan = p6_assets.planificar(self.proyecto, {}, previo={})
        escenas = plan["escenas"]
        escenas[0]["cartela"] = {"plantilla": "tesis", "texto": "La puerta se abre"}
        puestas = {escenas[0]["id"]: escenas[0]["cartela"]}
        with patch.object(p6_assets.cartelas, "tramo_de", return_value=(0, 0, {})) as tramo:
            p6_assets._fundir_cartelas(escenas, [{}, {}], puestas)
        self.assertEqual(tramo.call_args.kwargs["planos"], 1)
        self.assertEqual(len(escenas), 2)

    def test_un_guion_antiguo_no_activa_el_contrato_por_defecto(self):
        with patch.object(p4_voz.comun, "leer_salida", return_value={"guion": self.bloques}):
            self.assertEqual(p4_voz.contrato_de_escenas(self.proyecto), {})


if __name__ == "__main__":
    unittest.main()
