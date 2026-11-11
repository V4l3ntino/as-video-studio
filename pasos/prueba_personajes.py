"""Personajes, narrador, voces y exclusión de stock. Todo offline y aislado."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
AISLADO = tempfile.TemporaryDirectory(prefix="estudio_personajes_")
for variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                 "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[variable] = os.path.join(AISLADO.name, variable)

from PIL import Image
from nucleo import Estado, Proyecto
from pasos import bibliotecas, imagenes_animacion, medios, personajes, p3_guion, p4_voz, p5_revision_audio, p6_assets


class Personajes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=AISLADO.name)
        self.addCleanup(self.tmp.cleanup)
        self.proyecto = Proyecto.crear(self.tmp.name, "Historia de personajes")
        self.estado = Estado(self.proyecto)
        png = io.BytesIO()
        Image.new("RGB", (60, 90), "red").save(png, "PNG")
        self.imagen = imagenes_animacion.guardar(self.proyecto, png.getvalue(), "personaje.png")
        self.ana = dict(id="p_ana", nombre="Ana", descripcion="Exploradora curiosa de abrigo rojo.",
                        categoria="personaje", imagen=self.imagen, voz_id="voz_ana", voz_nombre="Ana voz")
        self.narrador = dict(id="p_narrador", nombre="Cronista", descripcion="Narrador sabio de capa azul.",
                             categoria="narrador", imagen=self.imagen)
        self.opciones = dict(personajes={"activo": True, "items": [self.ana, self.narrador]},
                             sistema_personajes={"generar_personajes": True, "incorporar_voz": True, "voz_id": "general"})

    def bloques(self):
        datos = {"bloques": [dict(id="B001", texto="Ana llegó al bosque.", personaje_id="p_narrador", personajes_visibles=["p_ana"], descripcion_visual="Ana observa los árboles."),
                             dict(id="B002", texto="Voy a explorar este camino.", personaje_id="p_ana", personajes_visibles=["p_ana"], descripcion_visual="Ana señala el camino."),
                             dict(id="B003", texto="El camino parecía tranquilo.", personaje_id="", personajes_visibles=[], descripcion_visual="Un camino vacío.")]}
        bloques = p3_guion._normalizar_bloques(datos)
        personajes.preparar_intervenciones(datos, bloques, self.opciones)
        return bloques

    def sembrar_guion(self):
        self.estado.actualizar_params("guion", self.opciones)
        self.estado.actualizar_params("assets", {"generar_personajes": True, "catalogo": {"sets": {"bosque": {"descripcion": "A forest"}}, "beats": []}})
        medios.escribir_json(os.path.join(self.proyecto.ruta_trabajo("guion"), "guion.json"),
                             {"guion": self.bloques(), "escenas_por_frase": True, "idioma": "es"})
        self.estado.completar("guion", {"guion_fichero": "guion.json"})

    def test_validacion_narrador_unico_identidad_y_rutas(self):
        config = self.opciones["personajes"]
        limpia = personajes.normalizar(config, self.proyecto)
        self.assertEqual(limpia["items"][0]["id"], "p_ana")
        for otro in (dict(self.narrador, id="otro", nombre="Otro narrador"),
                     dict(self.ana, id="otro"), dict(self.ana, nombre="Otra")):
            with self.subTest(otro=otro), self.assertRaises(ValueError):
                personajes.normalizar(dict(config, items=config["items"] + [otro]))
        for imagen in ("../../fuera.png", "medios_usuario/animaciones/" + "a" * 32 + ".png"):
            with self.assertRaises(ValueError):
                personajes.normalizar(dict(config, items=[dict(self.ana, imagen=imagen)]), self.proyecto)
        limpia = personajes.normalizar(dict(config, items=[dict(self.narrador, voz_id="intrusa")]))
        self.assertNotIn("voz_id", limpia["items"][0])

    def test_generacion_cuerpo_entero_crea_buzon_y_conserva_referencias(self):
        destino = os.path.join(self.tmp.name, "buzon_nuevo", "personaje.png")
        motor = Mock()
        motor.generar.return_value = (Path(self.proyecto.ruta(self.imagen)).read_bytes(), {})
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(personajes.medios, "motor", return_value=motor):
            personajes.generar_imagen(self.ana["descripcion"], destino, [self.imagen])
        self.assertTrue(os.path.isfile(destino))
        self.assertIn("full-body", motor.generar.call_args.args[0])
        self.assertIn(self.ana["descripcion"], motor.generar.call_args.args[0])
        self.assertEqual(motor.generar.call_args.args[1], [self.imagen])
        self.assertEqual(motor.generar.call_args.kwargs["tamano"], "vertical")
        self.assertIn("only the visual style", motor.generar.call_args.args[0])
        with patch.dict(os.environ, {"ESTUDIO_SIMULAR": "0"}), patch.object(personajes.medios, "motor", return_value=motor):
            personajes.generar_imagen("Cambia la postura.", destino, [self.imagen], tiene_personaje=True)
        self.assertIn("Reference image 1 is the current character", motor.generar.call_args.args[0])

    def test_pov_validacion_y_compatibilidad_de_fichas(self):
        config = copy.deepcopy(self.opciones["personajes"])
        self.assertNotIn("primera_persona", personajes.normalizar(config)["items"][1])
        config["items"][1]["primera_persona"] = True
        self.assertTrue(personajes.normalizar(config)["items"][1]["primera_persona"])
        config["items"][1]["primera_persona"] = "si"
        with self.assertRaisesRegex(ValueError, "casilla"):
            personajes.normalizar(config)
        config["items"][1]["primera_persona"] = False
        config["items"][0]["primera_persona"] = True
        self.assertNotIn("primera_persona", personajes.normalizar(config)["items"][0])
        self.assertIsNone(personajes.narrador_pov(self.opciones))

    def test_pov_todas_las_escenas_referencia_completa_y_prompts(self):
        from pasos import direccion, redactor
        self.narrador["primera_persona"] = True
        self.sembrar_guion()
        with patch.object(p4_voz, "simulado", return_value=True):
            salida = p4_voz.ejecutar(self.proyecto, {"voz_id": "general"})
        self.estado.completar("voz", salida)
        plan = p6_assets.planificar(self.proyecto, self.estado.params("assets"))
        for escena in plan["escenas"]:
            self.assertEqual(escena["perspectiva_narrador"]["id"], self.narrador["id"])
            self.assertIn("first-person POV", escena["encuadre"])
            self.assertIn("asset:p_narrador", p6_assets._assets_de_escena(escena))
            prompt = p6_assets._prompt_completo(escena, [], {}, feedback="Muestra al narrador desde fuera.")
            self.assertIn("MANDATORY FIRST-PERSON POV", prompt)
            self.assertIn("Never show the narrator from an external", prompt)
            self.assertGreater(prompt.index("MANDATORY FIRST-PERSON POV"), prompt.index("Muestra al narrador"))
        self.assertIn("PRIMERA PERSONA (POV)", personajes.instruccion(self.opciones))
        self.assertIn("PRIMERA PERSONA (POV)", direccion._planos_legibles(plan["escenas"]))
        self.assertIn("PRIMERA PERSONA (POV)", redactor._planos_legibles(plan["escenas"]))
        self.assertEqual(plan["assets"]["asset:p_narrador"]["imagen_personalizada"], self.imagen)
        # La hoja completa se copia incluso si solo hay planos sin cuerpo visible.
        params = dict(self.estado.params("assets"), estilo={"referencias": [self.proyecto.ruta(self.imagen)], "prompt": "Dibujo plano"})
        with patch.object(p6_assets, "_producir_imagen", side_effect=AssertionError("no redibujar referencias")):
            p6_assets.ejecutar(self.proyecto, params, tipos=["reparto"])
        trabajo = Path(self.proyecto.ruta_trabajo("assets"))
        hoja = trabajo / "assets" / "reparto" / "p_narrador.png"
        self.assertEqual(hoja.read_bytes(), Path(self.proyecto.ruta(self.imagen)).read_bytes())
        dirs = {"reparto": str(hoja.parent), "cache": str(trabajo / "cache"), "escenas": str(trabajo / "escenas")}
        escena = next(e for e in plan["escenas"] if not e["personajes"])
        refs = p6_assets._referencias_escena(escena, plan, dirs, params, dirs["cache"], {}, anteriores=[])
        self.assertTrue(any(r.get("nombre") == "p_narrador" for r in refs))
        for config in (dict(self.opciones["personajes"], activo=False),
                       dict(self.opciones["personajes"], items=[self.ana, dict(self.narrador, primera_persona=False)])):
            self.estado.actualizar_params("guion", dict(self.opciones, personajes=config))
            normal = p6_assets.planificar(self.proyecto, self.estado.params("assets"))
            self.assertTrue(all("perspectiva_narrador" not in e for e in normal["escenas"]))
            self.assertNotIn("MANDATORY FIRST-PERSON POV", p6_assets._prompt_completo(normal["escenas"][0], [], {}))

    def test_cuatro_modos_y_prioridad_en_instruccion(self):
        for generar in (False, True):
            for voz in (False, True):
                opciones = dict(self.opciones, sistema_personajes=dict(generar_personajes=generar, incorporar_voz=voz))
                texto = personajes.instruccion(opciones)
                self.assertEqual(bool(texto), generar)
                if generar:
                    self.assertIn("p_ana", texto)
                    self.assertEqual("SIN VOZ" in texto, not voz)
                    self.assertIn("personajes_automaticos", texto)
        apagada = dict(self.opciones, personajes=dict(self.opciones["personajes"], activo=False))
        self.assertNotIn('"p_ana"', personajes.instruccion(apagada))
        self.assertEqual(len(apagada["personajes"]["items"]), 2)

    def test_pov_componentes_tambien_generan_un_plano_subjetivo(self):
        dirs = {k: os.path.join(self.tmp.name, k) for k in ("escenas", "componentes", "cache")}
        for ruta in dirs.values():
            os.makedirs(ruta, exist_ok=True)
        escena = dict(id="S001", narracion="Examino el mapa.", prompt="A map on the table.",
                      componente="mapa", personajes=[], set="mesa", t_in=0, t_out=2,
                      perspectiva_narrador={k: self.narrador[k] for k in ("id", "nombre", "descripcion")})
        plan = dict(escenas=[escena], assets={}, dependencias={}, resolucion=[320, 180])
        params = p6_assets._con_defectos({"generar_personajes": True})
        motor = Mock()
        motor.bloque_prompt.return_value = ""
        motor.codex.return_value.concurrencia.return_value = 1
        with patch.object(p6_assets.medios, "motor", return_value=motor), \
                patch.object(p6_assets, "_referencias_escena", return_value=[]), \
                patch.object(p6_assets, "_producir_imagen", side_effect=RuntimeError("imagen POV solicitada")) as generar:
            with self.assertRaisesRegex(RuntimeError, "imagen POV solicitada"):
                p6_assets._generar_escenas(plan, dirs, params, self.tmp.name, lambda _: True, None, {}, Mock(), proyecto=self.proyecto)
        self.assertIn("MANDATORY FIRST-PERSON POV", generar.call_args.args[1])
        self.assertNotIn("asset:mapa", p6_assets._assets_de_escena(escena))

    def test_intervenciones_no_permiten_ids_voces_ni_narrador_inventados(self):
        bloques = self.bloques()
        self.assertEqual([b["voz_id"] for b in bloques], ["general", "voz_ana", "general"])
        sin_voz = dict(self.opciones, sistema_personajes=dict(self.opciones["sistema_personajes"], incorporar_voz=False))
        with self.assertRaisesRegex(ValueError, "sin narrador"):
            personajes.preparar_intervenciones({}, bloques, sin_voz)
        for cambio in ({"personaje_id": "desconocido"}, {"personaje_id": []}, {"personajes_visibles": ["otro"]}):
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                personajes.preparar_intervenciones({}, [dict(bloques[1], **cambio)], self.opciones)
        automatico = {"id": "auto_guardian", "nombre": "Guardián", "descripcion": "Protector del bosque."}
        b = dict(id="B001", texto="No pases por aquí.", personaje_id="auto_guardian", personajes_visibles=["auto_guardian"], descripcion_visual="El guardián levanta una mano.")
        with self.assertRaisesRegex(ValueError, "no tiene voz propia"):
            personajes.preparar_intervenciones({"personajes_automaticos": [automatico]}, [b], sin_voz)
        self.assertEqual(personajes.preparar_intervenciones({"personajes_automaticos": [automatico]}, [b], self.opciones)[0]["id"], "auto_guardian")
        with self.assertRaisesRegex(ValueError, "duplicó"):
            personajes.preparar_intervenciones({"personajes_automaticos": [dict(automatico, nombre="Ana")]}, [b], sin_voz)

    def test_cambiar_nombre_y_voz_general_conserva_id_y_vinculo(self):
        bloques = self.bloques()
        opciones = copy.deepcopy(self.opciones)
        opciones["personajes"]["items"][0]["nombre"] = "Alicia"
        personajes.aplicar_voces(bloques, opciones, "nueva_general")
        self.assertEqual(bloques[1]["personaje_id"], "p_ana")
        self.assertEqual(bloques[1]["personaje_nombre"], "Alicia")
        self.assertEqual([b["voz_id"] for b in bloques], ["nueva_general", "voz_ana", "nueva_general"])

    def test_audio_por_voces_orden_marcas_y_cache_al_reintentar(self):
        bloques = self.bloques()
        cfg = p4_voz.resolver_params({"voz_id": "general", "hueco_minimo": 0})
        llamadas = []
        def toma(texto, config, progreso):
            llamadas.append(config["voz_id"])
            return p4_voz._toma_simulada(texto, config)
        with patch.object(p4_voz, "sintetizar_toma", side_effect=toma), patch.object(p4_voz, "simulado", return_value=False):
            salida = p4_voz.sintetizar_bloques(bloques, self.tmp.name, cfg)
            self.assertEqual(llamadas, ["general", "voz_ana", "general"])
            p4_voz.sintetizar_bloques(bloques, self.tmp.name, cfg)
            self.assertEqual(len(llamadas), 3)
        self.assertEqual([b["personaje_id"] for b in salida["bloques"]], ["p_narrador", "p_ana", "p_narrador"])
        marcas = salida["palabras"]
        self.assertEqual([p["w"] for p in marcas], " ".join(b["texto"] for b in bloques).split())
        self.assertTrue(all(a["e"] <= b["s"] + .001 for a, b in zip(marcas, marcas[1:])))

    def test_pista_muda_explicita_sigue_sin_llamar_tts(self):
        cfg = p4_voz.resolver_params({"voz_id": "general"})
        with patch.object(p4_voz, "sintetizar_toma", side_effect=AssertionError("no llamar TTS")), patch.object(p4_voz, "_toma_por_contexto", side_effect=AssertionError("no llamar TTS")):
            salida = p4_voz.sintetizar_bloques(self.bloques(), self.tmp.name, cfg, sin_voz=True)
        self.assertTrue(salida["sin_voz"])
        self.assertEqual(salida["bloques"][1]["voz_id"], "voz_ana")
        pcm = p4_voz.motor._pcm_de_wav(Path(salida["pista"]).read_bytes())
        self.assertFalse(any(pcm))

    def test_solo_personajes_exige_todas_las_voces_antes_de_claude(self):
        opciones = copy.deepcopy(self.opciones)
        opciones["sistema_personajes"]["incorporar_voz"] = False
        personajes.validar_voces(opciones)  # El narrador no necesita voz propia.
        for config in ({"activo": False, "items": [self.ana]}, {"activo": True, "items": []},
                       {"activo": True, "items": [self.narrador]},
                       {"activo": True, "items": [dict(self.ana, voz_id=" ")]}):
            with self.subTest(config=config):
                opciones["personajes"] = config
                self.estado.actualizar_params("guion", opciones)
                self.estado.actualizar_params("assets", {"generar_personajes": True})
                self.estado.actualizar_params("voz", {"incorporar_voz": False})
                with patch.object(p3_guion, "_llamar_claude", side_effect=AssertionError("no consumir cuota")):
                    with self.assertRaisesRegex(ValueError, "antes de generar el guion"):
                        p3_guion.ejecutar(self.proyecto, opciones, Mock())
        opciones["sistema_personajes"]["generar_personajes"] = False
        personajes.validar_voces(opciones)  # Sin sistema de personajes conserva el modo mudo.

    def test_solo_personajes_sintetiza_voces_propias_y_revision_no_las_silencia(self):
        opciones = copy.deepcopy(self.opciones)
        opciones["sistema_personajes"]["incorporar_voz"] = False
        otra = dict(self.ana, id="p_luz", nombre="Luz", voz_id="voz_luz")
        opciones["personajes"]["items"].append(otra)
        self.estado.actualizar_params("guion", opciones)
        self.estado.actualizar_params("assets", {"generar_personajes": True})
        params = {"incorporar_voz": False, "voz_id": "general"}
        self.estado.actualizar_params("voz", params)
        bloques = [dict(id="B001", texto="Vamos a explorar el bosque.", personaje_id="p_ana", personajes_visibles=["p_ana"], descripcion_visual="Ana camina."),
                   dict(id="B002", texto="Te acompañaré por el camino.", personaje_id="p_luz", personajes_visibles=["p_luz"], descripcion_visual="Luz sigue a Ana.")]
        personajes.preparar_intervenciones({}, bloques, opciones)
        medios.escribir_json(os.path.join(self.proyecto.ruta_trabajo("guion"), "guion.json"), {"guion": bloques, "idioma": "es"})
        self.estado.completar("guion", {"guion_fichero": "guion.json"})
        voces = []
        def toma(texto, cfg, progreso):
            voces.append(cfg["voz_id"])
            return p4_voz._toma_simulada(texto, cfg)
        with patch.object(p4_voz, "sintetizar_toma", side_effect=toma):
            salida = p4_voz.ejecutar(self.proyecto, params)
        self.assertEqual(voces, ["voz_ana", "voz_luz"])
        self.assertFalse(salida.get("sin_voz"))
        self.estado.completar("voz", salida)
        with patch.object(p4_voz, "sintetizar_toma", side_effect=AssertionError("no repagar al revisar")):
            revision = p5_revision_audio.ejecutar(self.proyecto, {}, Mock())
        self.assertTrue(revision["sellada_del_paso_4"])
        self.assertFalse(revision.get("sin_voz"))
        self.assertEqual([b["voz_id"] for b in revision["bloques"]], voces)
        with self.assertRaisesRegex(ValueError, "regenera el guion"):
            personajes.aplicar_voces([self.bloques()[0]], opciones, "general")

    def test_api_bloquea_sin_voces_antes_de_lanzar_trabajo(self):
        import app
        self.estado.actualizar_params("assets", {"generar_personajes": True})
        self.estado.actualizar_params("voz", {"incorporar_voz": False})
        ctx = app.Contexto(self.proyecto.raiz)
        impedimentos = app._impedimentos(ctx, "guion", [{"id": "guion"}])
        self.assertIn("voz asignada", impedimentos[0]["que"])
        with patch.object(ctx.gestor, "lanzar", side_effect=AssertionError("no lanzar")):
            with self.assertRaises(app.ErrorApi):
                app.lanzar_paso(ctx, "guion", None)

    def test_reintentar_paso_tras_fallo_no_repaga_turnos_completados(self):
        self.sembrar_guion()
        llamadas = []
        def toma(texto, cfg, progreso):
            llamadas.append(cfg["voz_id"])
            if len(llamadas) == 3:
                raise RuntimeError("proveedor temporalmente no disponible")
            return p4_voz._toma_simulada(texto, cfg)
        with patch.object(p4_voz, "simulado", return_value=False), patch.object(p4_voz, "sintetizar_toma", side_effect=toma):
            with self.assertRaisesRegex(RuntimeError, "temporalmente"):
                p4_voz.ejecutar(self.proyecto, {"voz_id": "general"})
            salida = p4_voz.ejecutar(self.proyecto, {"voz_id": "general"})
        self.assertEqual(llamadas, ["general", "voz_ana", "general", "general"])
        self.assertEqual(len(salida["bloques"]), 3)

    def test_regrabar_tramo_desde_app_conserva_su_voz_y_sus_ids(self):
        import app
        self.sembrar_guion()
        self.estado.actualizar_params("voz", {"voz_id": "general"})
        with patch.object(p4_voz, "simulado", return_value=True):
            salida = p4_voz.ejecutar(self.proyecto, {"voz_id": "general"})
        self.estado.completar("voz", salida)
        ctx = app.Contexto(self.proyecto.raiz)
        ctx.estado.marcar_ejecutando("voz")
        voces = []
        def toma(trozos, cfg, progreso):
            voces.append(cfg["voz_id"])
            return p4_voz._toma_simulada(" ".join(trozos), cfg)
        with patch.object(p4_voz, "simulado", return_value=False), patch.object(p4_voz, "_toma_por_contexto", side_effect=toma):
            nueva = app._correr_regrabar(Mock(), ctx, "SB002", "", {})
        self.assertEqual(voces, ["voz_ana"])
        self.assertEqual(nueva["bloques"][1]["personaje_id"], "p_ana")
        self.assertEqual(nueva["bloques"][1]["voz_id"], "voz_ana")
        self.assertEqual(nueva["bloques"][0]["personaje_id"], "p_narrador")

    def test_guion_voz_plan_y_referencias_personalizadas_integrados(self):
        self.sembrar_guion()
        with patch.object(p4_voz, "simulado", return_value=True):
            salida = p4_voz.ejecutar(self.proyecto, {"voz_id": "general"})
        self.estado.completar("voz", salida)
        params = self.estado.params("assets")
        plan = p6_assets.planificar(self.proyecto, params)
        self.assertEqual(plan["escenas"][0]["personajes"], ["p_ana"])
        self.assertEqual(plan["escenas"][1]["intervencion"]["personaje_id"], "p_ana")
        self.assertEqual(plan["escenas"][1]["intervencion"]["escena_id"], plan["escenas"][1]["id"])
        self.assertEqual(plan["assets"]["asset:p_ana"]["imagen_personalizada"], self.imagen)
        params["estilo"] = {"referencias": [self.proyecto.ruta(self.imagen)], "prompt": "Dibujo plano"}
        with patch.object(p6_assets, "_producir_imagen", side_effect=AssertionError("la imagen ya está creada")):
            p6_assets.ejecutar(self.proyecto, params, tipos=["reparto"])
        hoja = Path(self.proyecto.ruta_trabajo("assets")) / "assets" / "reparto" / "p_ana.png"
        self.assertEqual(hoja.read_bytes(), Path(self.proyecto.ruta(self.imagen)).read_bytes())
        # La revisión que necesita resíntesis conserva también el hablante.
        with patch.object(p4_voz, "simulado", return_value=True):
            revision = p5_revision_audio.ejecutar(self.proyecto, {"voz": {"voz_id": "general", "velocidad": "slow"}}, lambda *_: None)
        self.assertEqual(revision["bloques"][1]["voz_id"], "voz_ana")

    def test_catalogo_prioriza_manual_y_no_duplica_identidades(self):
        catalogo = {"reparto": {"ana": {"nombre": "Ana", "descripcion": "inventada"}}, "beats": [{"personajes": ["ana"]}]}
        combinado = personajes.integrar_catalogo(catalogo, {}, self.opciones)
        self.assertNotIn("ana", combinado["reparto"])
        self.assertEqual(combinado["reparto"]["p_ana"]["imagen"], self.imagen)
        self.assertEqual(combinado["beats"][0]["personajes"], ["p_ana"])
        self.assertIn("ana", catalogo["reparto"])

    def test_redaccion_real_del_paso_con_cli_doblado_guarda_hablantes(self):
        self.narrador["primera_persona"] = True
        self.estado.actualizar_params("guion", self.opciones)
        self.estado.actualizar_params("assets", {"generar_personajes": True})
        self.estado.actualizar_params("voz", {"voz_id": "general", "incorporar_voz": True})
        medios.escribir_json(os.path.join(self.proyecto.ruta_trabajo("brief"), "brief.json"),
            {"idioma": "es", "presupuesto_palabras": 30, "margen": {"minimo": 10, "maximo": 60},
             "instrucciones": "Cuenta la aventura en el bosque.", "duracion_objetivo_s": 30})
        self.estado.completar("brief", {"brief_fichero": "brief.json"})
        datos = {"titulo": "El bosque", "bloques": self.bloques()}
        with patch.object(p3_guion.fuentes, "material_de", return_value=(
                [{"texto": "Una exploradora sigue un camino del bosque."}], {"sin_tiempos": True}, "texto")), \
                patch.object(p3_guion, "_llamar_claude", return_value=(json.dumps(datos), {})) as cli:
            salida = p3_guion.ejecutar(self.proyecto, dict(self.opciones, reintentos=0), Mock())
        self.assertIn("p_ana", cli.call_args.args[0])
        self.assertIn("personajes_visibles", cli.call_args.args[0])
        self.assertIn("PRIMERA PERSONA (POV)", cli.call_args.args[0])
        self.estado.completar("guion", salida)
        documento = medios.leer_json(self.proyecto.ruta_paso("guion") + "/guion.json")
        self.assertEqual(documento["guion"][1]["personaje_id"], "p_ana")
        self.assertEqual(documento["bloques_detalle"][1]["voz_id"], "voz_ana")

    def test_bloqueo_stock_interno_no_modifica_preferencias(self):
        anterior = dict(proveedores=["pixabay", "pexels"], origen_principal="bibliotecas", porcentaje_bibliotecas=100, modo_ia="cada", bibliotecas_cada=1)
        params = dict(bibliotecas=copy.deepcopy(anterior), generar_personajes=True)
        plan = {"escenas": [{"id": "S001"}, {"id": "S002"}]}
        b = bibliotecas.Biblioteca(self.proyecto, params, plan, Mock())
        with patch.object(bibliotecas, "buscar", side_effect=AssertionError("stock prohibido")):
            b.verificar_claves()
            for e in plan["escenas"]:
                self.assertIsNone(b.visual(e, "no.png"))
        self.assertFalse(bibliotecas.activa(params))
        self.assertEqual(params["bibliotecas"], anterior)
        params["generar_personajes"] = False
        self.assertTrue(bibliotecas.activa(params))
        self.assertEqual(bibliotecas.Biblioteca(self.proyecto, params, plan, Mock()).p["proveedores"], anterior["proveedores"])

    def test_stock_previo_no_se_conserva_ni_se_usa_como_respaldo(self):
        trabajo = self.proyecto.ruta_trabajo("assets")
        dirs = {k: os.path.join(trabajo, k) for k in ("escenas", "componentes", "cache")}
        for ruta in dirs.values():
            os.makedirs(ruta, exist_ok=True)
        destino = os.path.join(dirs["escenas"], "S001.png")
        Image.new("RGB", (32, 18), "blue").save(destino)
        medios.escribir_json(os.path.join(dirs["escenas"], "S001.json"), {"recurso_biblioteca": {"fuente": "pexels"}})
        e = dict(id="S001", narracion="Un bosque.", prompt="A forest", set="bosque", t_in=0, t_out=2)
        plan = dict(escenas=[e], assets={}, dependencias={}, resolucion=[320, 180])
        params = p6_assets._con_defectos(dict(generar_personajes=True, bibliotecas={"proveedores": ["pexels"]}))
        motor = Mock()
        motor.codex.return_value.concurrencia.return_value = 1
        with patch.object(p6_assets.medios, "motor", return_value=motor), patch.object(p6_assets, "_referencias_escena", return_value=[]), \
                patch.object(p6_assets, "_prompt_completo", return_value="forest"), patch.object(p6_assets, "_producir_imagen", side_effect=RuntimeError("fallan ambos generadores")), \
                patch.object(bibliotecas, "buscar", side_effect=AssertionError("stock prohibido")):
            with self.assertRaisesRegex(RuntimeError, "ambos generadores"):
                p6_assets._generar_escenas(plan, dirs, params, trabajo, lambda _: True, None, {}, Mock(), proyecto=self.proyecto)

    def test_peticion_de_una_escena_no_redibuja_otras_con_stock(self):
        carpeta = os.path.join(self.tmp.name, "escenas")
        os.makedirs(carpeta)
        medios.escribir_json(os.path.join(carpeta, "S002.json"), {"recurso_biblioteca": {"fuente": "pexels"}})
        plan = {"escenas": [{"id": "S001"}, {"id": "S002"}]}
        with self.assertRaisesRegex(RuntimeError, "otras escenas"):
            p6_assets._exigir_stock_en_peticion(plan, {"escenas": carpeta}, {"generar_personajes": True}, ["escena:S001"])
        p6_assets._exigir_stock_en_peticion(plan, {"escenas": carpeta}, {"generar_personajes": True}, None)
        p6_assets._exigir_stock_en_peticion(plan, {"escenas": carpeta}, {"generar_personajes": False}, ["escena:S001"])

    def test_montaje_no_recupera_stock_de_versiones_previas(self):
        from pasos import p8_render, avatar
        self.estado.actualizar_params("assets", {"generar_personajes": True})
        plan = os.path.join(self.tmp.name, "plan.json")
        movimiento = os.path.join(self.tmp.name, "movimiento.json")
        medios.escribir_json(plan, {"escenas": [{"id": "S001", "recurso_biblioteca": {"fuente": "pixabay"}}]})
        medios.escribir_json(movimiento, {"movimientos": []})
        with patch.object(avatar, "preparar", side_effect=AssertionError("no generar avatar ni componer antes de validar")):
            with self.assertRaisesRegex(RuntimeError, "biblioteca pendientes"):
                p8_render.ejecutar(self.proyecto, {"plan": plan, "movimiento": movimiento})
        # Una sustitución explícita del usuario conserva el contrato existente.
        personajes.exigir_visuales_ia(self.proyecto, {"escenas": [{"id": "S001", "medio_usuario": {"tipo": "imagen"}}]}, self.tmp.name)

    def test_api_persistencia_edicion_desactivacion_y_duplicacion(self):
        import app
        self.narrador["primera_persona"] = True
        with patch.object(app, "raiz_proyectos", return_value=self.tmp.name):
            ctx = app.contexto(self.proyecto.id)
            app._sembrar_video_light(ctx, dict(generar_personajes=True, incorporar_voz=True, personajes=self.opciones["personajes"]))
            app.fijar_params(ctx.id, "voz", {"voz_id": "otra_general"})
            self.assertEqual(ctx.estado.params("guion")["sistema_personajes"]["voz_id"], "otra_general")
            cambio = copy.deepcopy(self.opciones["personajes"])
            cambio["items"][0]["nombre"] = "Alicia"
            app.fijar_params(ctx.id, "guion", {"personajes": cambio})
            self.assertEqual(Estado(self.proyecto).params("guion")["personajes"]["items"][0]["id"], "p_ana")
            self.assertTrue(Estado(self.proyecto).params("guion")["personajes"]["items"][1]["primera_persona"])
            app.fijar_params(ctx.id, "voz", {"incorporar_voz": False})
            app.fijar_params(ctx.id, "assets", {"generar_personajes": False})
            self.assertEqual(len(ctx.estado.params("guion")["personajes"]["items"]), 2)
            copia = self.proyecto.duplicar(self.tmp.name, "Copia personajes")
            self.assertEqual(Estado(copia).params("guion")["personajes"]["items"][0]["id"], "p_ana")
            self.assertTrue(Estado(copia).params("guion")["personajes"]["items"][1]["primera_persona"])
            self.assertTrue(os.path.isfile(copia.ruta(self.imagen)))
            antes = Path(self.proyecto.ruta("estado.json")).read_bytes()
            app.leer_paso(ctx.id, "guion")
            self.assertEqual(Path(self.proyecto.ruta("estado.json")).read_bytes(), antes)

    def test_video_historico_cambiar_voz_no_activa_el_sistema(self):
        import app
        ctx = app.Contexto(self.proyecto.raiz)
        ctx.estado.actualizar_params("assets", {"bibliotecas": {"proveedores": ["pexels"]}})
        ctx.estado.actualizar_params("voz", {"incorporar_voz": False})
        antes = Path(self.proyecto.ruta("estado.json")).read_bytes()
        app._sincronizar_personajes(ctx)
        self.assertEqual(Path(self.proyecto.ruta("estado.json")).read_bytes(), antes)
        self.assertNotIn("sistema_personajes", ctx.estado.params("guion"))
        self.assertTrue(bibliotecas.activa(ctx.estado.params("assets")))


if __name__ == "__main__":
    unittest.main()
