"""Escaleta previa, narracion inmutable y direccion posterior. Sin proveedores."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

AISLADO = tempfile.TemporaryDirectory(prefix="prueba_editorial_")
for variable in ("ESTUDIO_ESTADISTICAS", "ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES",
                 "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[variable] = os.path.join(AISLADO.name, variable)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo import Estado, Proyecto
from pasos import comun, editorial_guion as editorial, marcas_tts, p3_guion


def escaleta():
    return dict(titulo="La infraestructura propia", pregunta_central="Cómo cambió sus costes.",
        respuesta_temprana="Construyó sus propias tuberías.", promesa_final="",
        recompensa_final="La infraestructura cambió sus costes.", voz="Directa y serena.",
        limites=[], descartes=["No hace falta una biografía."], tramos=[
            dict(id="T01", pregunta="Qué decidió.", aporte_nuevo="Construyó tuberías.",
                 recurso="explicacion", hechos=["La empresa construyó tuberías."], palabras=70, puente="Qué cambió."),
            dict(id="T02", pregunta="Qué cambió.", aporte_nuevo="Redujo sus costes.",
                 recurso="consecuencia", hechos=["Se redujeron los costes."], palabras=70, puente="")])


def narracion():
    return dict(titulo="La infraestructura propia", personajes_automaticos=[], bloques=[
        dict(id=f"B{i:03d}", tramo=f"T{i:02d}", abre_seccion=i == 1, personaje_id="",
             texto=("La empresa construyó sus propias tuberías y redujo sus costes. " * 7).strip())
        for i in (1, 2)])


class Editorial(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=AISLADO.name)
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = Proyecto.crear(self.tmp.name, "Encargo editorial")
        self.estado = Estado(self.proyecto)
        comun.escribir_json(os.path.join(self.proyecto.ruta_trabajo("ingesta"), "ingesta.json"),
            dict(transcript=[dict(texto="La empresa construyó tuberías y redujo sus costes.")],
                 metadatos=dict(sin_tiempos=True)))
        self.estado.completar("ingesta", {})
        comun.escribir_json(os.path.join(self.proyecto.ruta_trabajo("brief"), "brief.json"),
            dict(instrucciones="Cuenta la decisión sin tecnicismos.", idioma_salida="es",
                 presupuesto_palabras=140, palabras_minimo=100, palabras_maximo=180,
                 bloques_estimados=2, palabras_por_bloque=70, duracion_objetivo_s=60))
        self.estado.completar("brief", {})

    def ejecutar(self, respuestas, params=None):
        sobre = dict(usage=dict(input_tokens=10, output_tokens=20))
        opciones = dict(escaleta_previa=True, reintentos=0)
        opciones.update(params or {})
        with patch.object(p3_guion, "_llamar_claude", side_effect=[
                (json.dumps(r, ensure_ascii=False), sobre) for r in respuestas]) as cli:
            salida = p3_guion.ejecutar(self.proyecto, opciones, lambda *a: None)
        # Todavia no se publica la version: solo existe trabajo/.
        with open(os.path.join(self.proyecto.ruta_trabajo("guion"), "guion.json"), encoding="utf-8") as f:
            documento = json.load(f)
        return salida, documento, cli

    def test_presupuestos_exactos_sin_segunda_llamada_por_aritmetica(self):
        crudo = escaleta()
        crudo["tramos"][0]["palabras"] = 1
        normalizada = editorial.validar_escaleta(crudo, 141)
        self.assertEqual(sum(t["palabras"] for t in normalizada["tramos"]), 141)
        self.assertTrue(all(t["palabras"] > 0 for t in normalizada["tramos"]))
        self.assertEqual(crudo["tramos"][0]["palabras"], 1)
        with self.assertRaises(ValueError):
            editorial.validar_escaleta(dict(crudo, tramos=[]), 140)

    def test_escaleta_antes_de_redactar_y_tokens_de_ambas_fases(self):
        salida, doc, cli = self.ejecutar([escaleta(), narracion()])
        self.assertEqual(cli.call_count, 2)
        self.assertEqual(salida["tokens"], dict(entrada=20, salida=40, cache=0))
        self.assertEqual(doc["fases_guion"], dict(escaleta=1, narracion=1))
        self.assertEqual(doc["plan_narrativo"]["tramos"][1]["bloques"], ["B002"])
        prompt_plan, prompt_texto = [c.args[0] for c in cli.call_args_list]
        self.assertIn("no un dosier verificado", prompt_plan)
        self.assertNotIn("DIRECCIÓN VISUAL STICKMAN", prompt_plan)
        self.assertIn('"descartes": ["No hace falta una biografía."]', prompt_texto)
        self.assertNotIn("== COMO SE ESTRUCTURA ESTE VIDEO ==", prompt_texto)
        self.assertTrue(os.path.exists(os.path.join(self.proyecto.ruta_trabajo("guion"), "escaleta.json")))

    def test_escaleta_invalida_detiene_antes_de_redactar(self):
        with patch.object(p3_guion, "_llamar_claude", return_value=('{}', {})) as cli:
            with self.assertRaises(RuntimeError):
                p3_guion.ejecutar(self.proyecto, dict(escaleta_previa=True, reintentos=0), lambda *a: None)
        self.assertEqual(cli.call_count, 1)

    def test_longitud_se_corrige_sin_repetir_la_escaleta(self):
        corta = narracion()
        for bloque in corta["bloques"]:
            bloque["texto"] = "La empresa construyó una tubería."
        _, doc, cli = self.ejecutar([escaleta(), corta, narracion()], dict(reintentos=1))
        self.assertEqual(cli.call_count, 3)
        self.assertEqual(doc["fases_guion"], dict(escaleta=1, narracion=2))
        self.assertEqual(doc["palabras"], 140)
        self.assertIn("La empresa construyó una tubería.", cli.call_args.args[0])

    def test_no_se_puede_ignorar_ni_reordenar_la_escaleta(self):
        bloques = narracion()["bloques"]
        with self.assertRaises(ValueError):
            editorial.plan_del_texto(escaleta(), bloques[::-1])
        with self.assertRaises(ValueError):
            editorial.plan_del_texto(escaleta(), bloques[:1])

    def test_direccion_posterior_preserva_narracion_y_hablantes(self):
        self.estado.actualizar_params("assets", dict(generar_personajes=True,
            estilo=dict(stickman=dict(activo=True))))
        # Usa un contexto explicito: esta suite no depende del selector de estilo.
        modo = dict(generar_personajes=True, stickman=True, incorporar_voz=True, incorporar_dialogos=False)
        visuales = []
        for b in narracion()["bloques"]:
            frases = p3_guion.medios.motor("guion/segmentar.py").frases_del_texto(b["texto"])
            visuales.append(dict(id=b["id"], personajes_visibles=[], descripcion_visual="Una tubería.",
                escenas_visuales=[dict(texto=f, personajes_visibles=[],
                    descripcion_visual=f"Una tubería en el panel {i} de {b['id']}.") for i, f in enumerate(frases)]))
        with patch.object(p3_guion.personajes, "contexto", return_value=modo):
            salida, doc, cli = self.ejecutar([escaleta(), narracion(),
                dict(personajes_automaticos=[], bloques=visuales)], dict(sistema_personajes=modo))
        self.assertEqual(cli.call_count, 3)
        self.assertNotIn("DIRECCIÓN VISUAL STICKMAN", cli.call_args_list[1].args[0])
        self.assertIn("DIRECCIÓN VISUAL STICKMAN", cli.call_args_list[2].args[0])
        self.assertEqual([marcas_tts.limpiar(b["texto"]) for b in doc["guion"]],
                         [b["texto"] for b in narracion()["bloques"]])
        self.assertTrue(all(b["escenas_visuales"] for b in doc["guion"]))
        self.assertEqual(salida["tokens"]["entrada"], 30)

    def test_director_no_puede_reescribir_ni_cambiar_orden(self):
        bloques = narracion()["bloques"]
        visual = [dict(id=b["id"], descripcion_visual="Una tubería.") for b in bloques]
        for cambio in (dict(texto="Otro texto."), dict(personaje_id="auto_otro")):
            mal = copy.deepcopy(visual)
            mal[0].update(cambio)
            with self.assertRaises(ValueError):
                editorial.aplicar_direccion({}, bloques, dict(bloques=mal))
        with self.assertRaises(ValueError):
            editorial.aplicar_direccion({}, bloques, dict(bloques=visual[::-1]))

    def test_dialogos_conservan_su_voz_al_dirigir(self):
        modo = dict(generar_personajes=True, incorporar_voz=False)
        params = dict(sistema_personajes=modo, personajes=dict(activo=True,
            incorporar_dialogos=True, items=[dict(id="p_ana", nombre="Ana", categoria="personaje",
                descripcion="Exploradora.", voz_id="voz_ana")]))
        texto = narracion()
        for b in texto["bloques"]:
            b["personaje_id"] = "p_ana"
        visual = dict(personajes_automaticos=[], bloques=[dict(id=b["id"],
            personajes_visibles=["p_ana"], descripcion_visual="Ana observa una tubería.")
            for b in texto["bloques"]])
        with patch.object(p3_guion.personajes, "contexto", return_value=modo):
            _, doc, cli = self.ejecutar([escaleta(), texto, visual], params)
        self.assertEqual(cli.call_count, 3)
        self.assertTrue(all(b["personaje_id"] == "p_ana" and b["voz_id"] == "voz_ana"
                            for b in doc["guion"]))

    def test_timeout_visual_no_repite_escaleta_ni_tira_la_narracion(self):
        respuestas = [(json.dumps(escaleta()), {}), (json.dumps(narracion()), {}),
                      p3_guion.TiempoAgotado("se agoto el tiempo de direccion")]
        modo = dict(generar_personajes=True, incorporar_voz=True)
        with patch.object(p3_guion.personajes, "contexto", return_value=modo), \
                patch.object(p3_guion, "_llamar_claude", side_effect=respuestas) as cli:
            with self.assertRaises(p3_guion.TiempoAgotado):
                p3_guion.ejecutar(self.proyecto, dict(escaleta_previa=True,
                    sistema_personajes=modo, reintentos=1), lambda *a: None)
        self.assertEqual(cli.call_count, 3)
        trabajo = Path(self.proyecto.ruta_trabajo("guion", crear=False))
        self.assertTrue((trabajo / "narracion.json").exists())
        self.assertFalse((trabajo / "guion.json").exists())

    def test_guion_propio_y_correccion_local_no_abren_escaleta(self):
        original = narracion()
        _, doc, cli = self.ejecutar([original], dict(guion_propio=True))
        self.assertEqual(cli.call_count, 1)
        self.assertNotIn("escaleta_editorial", doc)
        self.estado.completar("guion", dict(guion_fichero="guion.json"))
        _, siguiente, cli = self.ejecutar([original], dict(prompt_general="Conserva el texto."))
        self.assertEqual(cli.call_count, 1)
        self.assertNotIn("escaleta_editorial", siguiente)


if __name__ == "__main__":
    unittest.main()
