"""Contrato Codex -> motor -> medidor, sin red ni consumo de cuota.

    python pasos/prueba_codex_imagen.py
"""
import importlib.util
import io
import base64
import json
import os
import sys
import tempfile
import unittest
import queue
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
CARPETA = tempfile.TemporaryDirectory(prefix="prueba_codex_")
for variable, nombre in (("ESTUDIO_SECRETOS", "secretos"),
                         ("ESTUDIO_ESTADISTICAS", "estadisticas.json"),
                         ("ESTUDIO_AJUSTES", "ajustes.json"),
                         ("ESTUDIO_COSTE_GLOBAL", "coste.jsonl")):
    os.environ[variable] = os.path.join(CARPETA.name, nombre)

from PIL import Image  # noqa: E402
from nucleo import coste  # noqa: E402
from nucleo.proyecto import Proyecto  # noqa: E402
sys.path.insert(0, os.path.join(RAIZ, "pasos"))
import ajustes  # noqa: E402
import medios  # noqa: E402
import presets_light  # noqa: E402


def cargar(nombre, fichero):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(
        RAIZ, "motores", "imagen_openai", fichero))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


codex = cargar("codex_prueba", "codex.py")
motor = cargar("imagen_prueba_codex", "imagen.py")


class PruebaCodex(unittest.TestCase):
    def setUp(self):
        codex.cerrar_conexiones()
        self.addCleanup(codex.cerrar_conexiones)
        self.carpeta = tempfile.TemporaryDirectory(dir=CARPETA.name)
        self.addCleanup(self.carpeta.cleanup)
        self.png = os.path.join(self.carpeta.name, "nativa.png")
        Image.new("RGB", (60, 40), "blue").save(self.png)
        self.conexion = mock.Mock()
        self.conexion.errores_cli = []
        self.conexion.pendientes = deque()
        self.conexion.descartar = False
        self.conexion.proceso.poll.return_value = None
        self.conexion.cuenta.return_value = {"type": "chatgpt"}
        self.historial = []
        self.limites = {"ordinaryUsageAllowed": True}
        self.conexion.pedir.side_effect = self.responder
        self.eventos = [
            {"method": "item/completed", "params": {"item": {
                "id": "img", "type": "imageGeneration", "status": "completed", "savedPath": self.png}}},
            {"method": "turn/completed", "params": {"turn": {"id": "turno", "status": "completed"}}},
        ]

    def responder(self, metodo, params=None, **kwargs):
        return {"account/rateLimits/read": self.limites,
                "thread/start": {"thread": {"id": "hilo"}},
                "turn/start": {"turn": {"id": "turno"}},
                "thread/items/list": {"data": self.historial},
                "thread/read": {"thread": {"turns": []}}}.get(metodo, {})

    def generar(self, referencias=()):
        self.conexion.recibir.side_effect = self.eventos
        with mock.patch.object(codex, "Conexion", return_value=self.conexion):
            return codex.generar("Un paisaje", referencias, "low", "96x64")

    def test_solo_imagen_nativa_y_dimensiones_del_contrato(self):
        png, meta = self.generar([self.png])
        with Image.open(io.BytesIO(png)) as imagen:
            self.assertEqual(imagen.size, (96, 64))
        self.assertEqual(meta["facturacion"], "suscripcion_chatgpt")
        self.assertEqual(meta["coste"], 0)
        inicio = next(c for c in self.conexion.pedir.call_args_list if c.args[0] == "turn/start")
        entradas = inicio.args[1]["input"]
        self.assertEqual(entradas[1]["type"], "localImage")
        self.assertTrue(entradas[1]["path"].endswith("referencia_01.png"))
        self.conexion.cerrar.assert_not_called()

    def test_mensaje_de_exito_no_es_una_imagen(self):
        self.eventos[0]["params"]["item"] = {"type": "agentMessage", "text": "Imagen creada"}
        with self.assertRaises(codex.ErrorCodex):
            self.generar()

    def test_png_sin_evento_de_generacion_no_se_acepta(self):
        self.eventos = self.eventos[-1:]
        with self.assertRaises(codex.ErrorCodex):
            self.generar()

    def test_turno_fallido_no_se_reintenta_ni_cobra_api(self):
        self.eventos = self.eventos[-1:]
        self.eventos[-1]["params"]["turn"]["status"] = "failed"
        with self.assertRaises(codex.ErrorCodex):
            self.generar()
        self.assertEqual(sum(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list), 1)
        self.conexion.cerrar.assert_called_once()

    def test_no_acepta_login_con_api_key(self):
        self.conexion.cuenta.return_value = {"type": "apiKey"}
        with self.assertRaises(codex.ErrorCodex):
            self.generar()
        self.conexion.pedir.assert_not_called()

    def test_quita_credenciales_de_pago_del_entorno(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "secreto",
                "OPENAI_API_KEY_2": "otra", "CODEX_API_KEY": "secreto",
                "OPENAI_BASE_URL": "https://otro.invalid", "ESTUDIO_CODEX_HOME": self.carpeta.name}):
            entorno = codex.entorno()
        self.assertNotIn("OPENAI_API_KEY", entorno)
        self.assertNotIn("OPENAI_API_KEY_2", entorno)
        self.assertNotIn("CODEX_API_KEY", entorno)
        self.assertNotIn("OPENAI_BASE_URL", entorno)
        self.assertEqual(entorno["CODEX_HOME"], self.carpeta.name)

    def test_motor_con_codex_no_llama_a_la_api_aunque_haya_clave(self):
        with mock.patch.object(motor, "RUTA_PROVEEDOR", os.path.join(self.carpeta.name, "imagenes.json")), \
                mock.patch.object(motor, "CARPETA_SECRETOS", self.carpeta.name), \
                mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-no-usar"}), \
                mock.patch.object(motor, "codex", return_value=codex), \
                mock.patch.object(codex, "generar", return_value=(b"png", {"coste": 0})) as generar, \
                mock.patch.object(motor.requests, "post", side_effect=AssertionError("llamada de pago")):
            motor.activar_codex()
            self.assertEqual(motor.proveedor_imagen(), "codex")
            motor.generar("plano", [self.png])
            generar.assert_called_once_with("plano", [self.png], "low", "1536x1024")

    def test_sesion_publica_no_devuelve_tokens(self):
        self.conexion.cuenta.return_value = {"type": "chatgpt", "email": "persona@example.com",
            "planType": "plus", "access_token": "no-publicar"}
        with mock.patch.object(codex, "Conexion", return_value=self.conexion):
            ficha = codex.estado()
        self.assertTrue(ficha["conectada"])
        self.assertNotIn("no-publicar", json.dumps(ficha))

    def test_medidor_no_aplica_tarifas_api_a_la_suscripcion(self):
        proyecto = Proyecto.crear(self.carpeta.name, "Imagen con cuota")
        def nativa(*args, **kwargs):
            return b"png", {"facturacion": "suscripcion_chatgpt", "coste": 0,
                "usage": {"input_tokens": 1000, "output_tokens": 2000}}
        with coste.contexto(proyecto, "assets"):
            _, meta = coste._medir_imagen(nativa)("plano", [])
        eventos = coste.Medidor(proyecto).eventos()
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["usd"], 0)
        self.assertFalse(eventos[0]["usd_estimado"])
        self.assertEqual(eventos[0]["cantidad"]["imagenes"], 1)
        self.assertEqual(eventos[0]["tokens"]["entrada"], 1000)
        self.assertEqual(meta["coste"], 0)

    def test_estimaciones_no_reintroducen_un_precio_api_de_respaldo(self):
        with mock.patch.object(medios.motor("imagen_openai/imagen.py"),
                               "proveedor_imagen", return_value="codex"):
            for calidad in ajustes.CALIDADES:
                ficha = ajustes.coste_por_imagen(calidad)
                self.assertEqual(ficha["usd_total"], 0)
                self.assertEqual(ficha["facturacion"], "suscripcion_chatgpt")
                self.assertEqual(presets_light.usd_por_imagen(calidad), 0)

    def test_notificacion_antes_de_respuesta_rpc_no_se_pierde(self):
        conexion = codex.Conexion.__new__(codex.Conexion)
        conexion.numero = 0
        conexion.cola = queue.Queue()
        conexion.pendientes = deque()
        conexion.enviar = mock.Mock()
        aviso = {"method": "account/login/completed", "params": {"success": True}}
        conexion.cola.put(aviso)
        conexion.cola.put({"id": 1, "result": {"loginId": "login"}})
        self.assertEqual(conexion.pedir("account/login/start")["loginId"], "login")
        self.assertEqual(conexion.recibir(time.monotonic() + 1), aviso)

    def test_login_reutiliza_el_intento_y_limpia_el_codigo_al_terminar(self):
        self.conexion.pedir.side_effect = None
        self.conexion.pedir.return_value = {"verificationUrl": "https://auth.openai.com/codex/device",
                                            "userCode": "ABCD-1234"}
        self.conexion.recibir.return_value = {
            "method": "account/login/completed", "params": {"success": True}}
        with mock.patch.object(codex, "_LOGIN", None), \
                mock.patch.object(codex, "_ESTADO_LOGIN", {}), \
                mock.patch.object(codex, "Conexion", return_value=self.conexion), \
                mock.patch.object(codex.threading, "Thread"):
            intento = codex.iniciar_login()
            self.assertEqual(intento, codex.iniciar_login())
            self.conexion.pedir.assert_called_once()
            codex._esperar_login(self.conexion)
            self.assertIsNone(codex._LOGIN)
            self.assertEqual(codex._ESTADO_LOGIN["estado"], "listo")
            self.assertNotIn("codigo", codex._ESTADO_LOGIN)

    def test_cuota_de_imagenes_se_reconoce_por_failure_nativo(self):
        self.eventos[0]["params"]["item"].update(status="failed", failure={
            "type": "usageLimitExceeded", "limitId": "image_generation", "resetsAt": 1793700000})
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "cuota")
        self.assertIn("Reinicio indicado", str(fallo.exception))

    def test_no_infiere_cuota_de_una_imagen_ausente(self):
        self.eventos = self.eventos[-1:]
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "respuesta_incompleta")
        self.assertIn("causa no está confirmada", str(fallo.exception))

    def test_cuota_general_bloqueada_no_empieza_turno(self):
        self.limites["ordinaryUsageAllowed"] = False
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "cuota")
        self.assertFalse(any(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list))

    def test_cuota_renovable_espera_y_solo_genera_cuando_el_uso_vuelve(self):
        from pasos import recuperacion_imagenes as recuperacion
        from nucleo.trabajos import GestorTrabajos
        proyecto = Proyecto.crear(self.carpeta.name, "Esperar uso incluido")
        gestor = GestorTrabajos()
        consultas, esperas, mensajes = [], [], []

        def responder(metodo, params=None, **kwargs):
            if metodo == "account/rateLimits/read":
                consultas.append(metodo)
                return {"ordinaryUsageAllowed": len(consultas) >= 3}
            return self.responder(metodo, params, **kwargs)

        def esperar(sesion, segundos, unidad):
            esperas.append(segundos)
            sesion.avisar_progreso(None)
            # Ninguna solicitud de imagen en los dos sondeos bloqueados.
            self.assertFalse(any(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list))

        def correr(avisar):
            def progreso(valor, mensaje=""):
                mensajes.append(mensaje)
                avisar(valor, mensaje, mensaje)
            sesion = recuperacion.Recuperacion(proyecto, progreso)
            return sesion.ejecutar(self.generar, "S001")

        self.conexion.pedir.side_effect = responder
        with mock.patch.object(recuperacion.avisos, "leer", return_value={
                "reintentos": True, "intervalo": 60, "intervalo_maximo": 300}), \
                mock.patch.object(recuperacion.avisos, "enviar", return_value={}), \
                mock.patch.object(recuperacion.Recuperacion, "_esperar", esperar):
            tid = gestor.lanzar("generar:video", correr)
            final = gestor.esperar(tid, 5)
        self.assertEqual(final["estado"], "listo", final.get("error"))
        self.assertEqual(len(consultas), 3)
        self.assertEqual(len(esperas), 2)
        self.assertTrue(any("Uso de ChatGPT no disponible" in m for m in mensajes))
        self.assertTrue(any("Comprobando si vuelve" in m for m in mensajes))
        self.assertEqual(sum(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list), 1)
        self.assertTrue(final["resultado"][0].startswith(b"\x89PNG"))

    def test_recupera_native_del_mismo_turno_sin_otra_generacion(self):
        item = self.eventos[0]["params"]["item"]
        self.historial = [{"turnId": "otro", "item": dict(item, id="ajena")},
                          {"turnId": "turno", "item": item}]
        self.eventos = self.eventos[-1:]
        _, meta = self.generar()
        self.assertTrue(meta["recuperada"])
        consultas = [c for c in self.conexion.pedir.call_args_list if c.args[0] == "thread/items/list"]
        self.assertEqual(consultas[0].args[1]["turnId"], "turno")
        self.assertEqual(sum(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list), 1)

    def test_recupera_result_inline_autenticado_sin_savedpath(self):
        with open(self.png, "rb") as fh:
            self.eventos[0]["params"]["item"] = {"type": "imageGeneration", "id": "img",
                "status": "completed", "result": base64.b64encode(fh.read()).decode()}
        png, meta = self.generar()
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertTrue(meta["recuperada"])

    def test_turno_terminal_incluye_item_que_no_llego_por_notificacion(self):
        item = self.eventos[0]["params"]["item"]
        self.eventos = self.eventos[-1:]
        self.eventos[0]["params"]["turn"]["items"] = [item]
        png, _ = self.generar()
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_imagen_completa_se_salva_aunque_agente_falle_despues(self):
        self.eventos[-1]["params"]["turn"].update(status="failed", error={"message": "stream disconnected"})
        _, meta = self.generar()
        self.assertTrue(meta["recuperada"])

    def test_diagnostico_conserva_explicacion_sin_credenciales(self):
        self.eventos[0]["params"]["item"] = {"type": "agentMessage", "text":
            "Refusal: cannot help. Bearer secreto-de-acceso api_key=sk-no-publicar"}
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "rechazo")
        ruta = os.path.join(os.environ["ESTUDIO_SECRETOS"], "codex_imagenes", fallo.exception.diagnostico + ".json")
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        self.assertIn("cannot help", texto)
        self.assertNotIn("secreto-de-acceso", texto)
        self.assertNotIn("sk-no-publicar", texto)
        self.assertNotIn("Un paisaje", texto)

    def test_rechazo_de_seguridad_en_castellano_sin_failure_estructurado(self):
        # El CLI puede terminar el turno con exito aunque image_gen haya fallado.
        # El item no lleva failure: la explicacion viene en el mensaje del agente.
        self.eventos = [
            {"method": "item/completed", "params": {"item": {
                "id": "aviso", "type": "agentMessage",
                "text": "Generaré una sola imagen usando las tres referencias en el orden indicado."}}},
            {"method": "item/completed", "params": {"item": {
                "id": "img", "type": "imageGeneration", "status": "failed", "failure": None}}},
            {"method": "item/completed", "params": {"item": {
                "id": "explicacion", "type": "agentMessage",
                "text": "No se pudo generar la imagen: image_gen rechazó la solicitud por su "
                        "filtro de seguridad («self-harm»), aparentemente por el gesto de "
                        "pellizcarse el antebrazo. No he realizado llamadas adicionales."}}},
            {"method": "turn/completed", "params": {"turn": {"id": "turno", "status": "completed"}}},
        ]
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar([self.png] * 3)
        self.assertEqual(fallo.exception.tipo, "rechazo")
        self.assertIn("self-harm", str(fallo.exception))
        self.assertNotIn("La causa no está confirmada", str(fallo.exception))
        self.assertEqual(sum(c.args[0] == "turn/start" for c in self.conexion.pedir.call_args_list), 1)
        ruta = os.path.join(os.environ["ESTUDIO_SECRETOS"], "codex_imagenes",
                            fallo.exception.diagnostico + ".json")
        with open(ruta, encoding="utf-8") as fh:
            diagnostico = json.load(fh)
        self.assertEqual(diagnostico["tipo_error"], "rechazo")

    def test_bloqueo_de_moderacion_estructurado_es_rechazo(self):
        self.eventos[0]["params"]["item"].update(
            status="failed", failure={"code": "moderation_blocked"})
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "rechazo")

    def test_modelo_no_compatible_no_es_entrega_incompleta_reintentable(self):
        error = codex._error_de({"message": json.dumps({"error": {
            "message": "The 'gpt-5.5' model is not supported when using Codex with a ChatGPT account.",
            "code": "model_not_found"}})})
        self.assertEqual(error.tipo, "modelo")
        self.assertIn("modelo no compatible", str(error))

    def test_mencionar_el_gesto_sin_rechazo_no_prueba_bloqueo(self):
        self.eventos[0]["params"]["item"] = {"type": "agentMessage",
            "text": "Generaré la imagen del personaje pellizcándose el antebrazo."}
        with self.assertRaises(codex.ErrorCodex) as fallo:
            self.generar()
        self.assertEqual(fallo.exception.tipo, "respuesta_incompleta")

    def test_seis_referencias_se_envian_en_cinco_adjuntos_sin_descartar(self):
        ultima = os.path.join(self.carpeta.name, "sexta.png")
        Image.new("RGB", (60, 40), "red").save(ultima)
        carpeta = os.path.join(self.carpeta.name, "refs")
        os.makedirs(carpeta)
        rutas, mapa = codex._preparar_referencias([self.png] * 5 + [ultima], carpeta)
        self.assertEqual(len(rutas), 5)
        self.assertIn("referencia original 5: REF 5", mapa)
        self.assertIn("referencia original 6: REF 6", mapa)
        with Image.open(rutas[-1]) as hoja:
            self.assertEqual(hoja.getpixel((320, 268)), (0, 0, 255))
            self.assertEqual(hoja.getpixel((960, 268)), (255, 0, 0))
        _, meta = self.generar([self.png] * 5 + [ultima])
        entradas = next(c for c in self.conexion.pedir.call_args_list if c.args[0] == "turn/start").args[1]["input"]
        self.assertEqual(len([i for i in entradas if i["type"] == "localImage"]), 5)
        self.assertEqual(meta["refs"], 6)
        self.assertEqual(meta["refs_enviadas"], 5)
        self.assertTrue(meta["refs_agrupadas"])

    def test_limite_de_referencias_no_se_confunde_con_cuota(self):
        error = codex._error_de("image_gen admite un máximo de 5 imágenes de referencia; hay 6")
        self.assertEqual(error.tipo, "referencias")

    def test_reutiliza_proceso_pero_abre_hilo_nuevo_por_imagen(self):
        self.conexion.recibir.side_effect = self.eventos * 2
        with mock.patch.object(codex, "Conexion", return_value=self.conexion) as crear:
            _, primera = codex.generar("primera", [], "low", "96x64")
            _, segunda = codex.generar("segunda", [], "low", "96x64")
        crear.assert_called_once()
        self.assertFalse(primera["conexion_reutilizada"])
        self.assertTrue(segunda["conexion_reutilizada"])
        metodos = [c.args[0] for c in self.conexion.pedir.call_args_list]
        self.assertEqual(metodos.count("thread/start"), 2)
        self.assertEqual(metodos.count("thread/unsubscribe"), 2)
        self.assertNotIn("thread/resume", metodos)

    def test_pool_no_supera_dos_generaciones_y_reutiliza_para_la_tercera(self):
        liberar = threading.Event()
        dos_dentro = threading.Event()
        cerrojo = threading.Lock()
        contadores = {"dentro": 0, "maximo": 0, "entradas": 0}
        creadas = []
        def crear():
            conexion = mock.Mock(descartar=False)
            conexion.proceso.poll.return_value = None
            creadas.append(conexion)
            return conexion
        def correr():
            with codex._prestar_conexion():
                with cerrojo:
                    contadores["dentro"] += 1
                    contadores["entradas"] += 1
                    contadores["maximo"] = max(contadores["maximo"], contadores["dentro"])
                    if contadores["entradas"] == 2:
                        dos_dentro.set()
                liberar.wait(5)
                with cerrojo:
                    contadores["dentro"] -= 1
        with mock.patch.dict(os.environ, {"ESTUDIO_CODEX_CONCURRENCIA": "2"}), \
                mock.patch.object(codex, "Conexion", side_effect=crear), \
                ThreadPoolExecutor(max_workers=3) as pool:
            tareas = [pool.submit(correr) for _ in range(3)]
            try:
                self.assertTrue(dos_dentro.wait(3))
                self.assertEqual(contadores["entradas"], 2)
            finally:
                liberar.set()
            for tarea in tareas:
                tarea.result()
        self.assertEqual(contadores["maximo"], 2)
        self.assertEqual(len(creadas), 2)

    def test_cambio_de_cuenta_no_reutiliza_conexion_anterior(self):
        with mock.patch.object(codex, "Conexion", return_value=self.conexion):
            with codex._prestar_conexion():
                pass
            codex.cerrar_conexiones()
            self.conexion.cerrar.assert_called_once()
            with codex._prestar_conexion() as (_, reutilizada):
                self.assertFalse(reutilizada)


class PruebaPrioridadesImagen(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory(dir=CARPETA.name)
        self.addCleanup(carpeta.cleanup)
        self.carpeta = carpeta.name
        for nombre, valor in (("CARPETA_SECRETOS", self.carpeta),
                              ("RUTA_PROVEEDOR", os.path.join(self.carpeta, "imagenes.json"))):
            parche = mock.patch.object(motor, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        self.claves = mock.patch.object(motor, "_claves_declaradas", return_value=[("", "sk-prueba")]).start()
        self.api = mock.patch.object(motor, "_generar_api", return_value=(b"api", {"coste": .01})).start()
        self.codex = mock.Mock()
        self.codex.generar.return_value = (b"codex", {"coste": 0, "facturacion": "suscripcion_chatgpt"})
        self.codex._limpiar.side_effect = str
        self.codex.ErrorCodex = codex.ErrorCodex
        self.adaptador = mock.patch.object(motor, "codex", return_value=self.codex).start()
        self.addCleanup(mock.patch.stopall)

    def test_conserva_principal_antiguo_y_persiste_ambos_ordenes(self):
        self.assertEqual(motor.prioridades_imagen(), ["api", "codex"])
        self.claves.return_value = []
        self.assertEqual(motor.prioridades_imagen(), ["codex", "api"])
        for orden in (["api", "codex"], ["codex", "api"]):
            motor.guardar_prioridades(orden)
            self.assertEqual(motor.prioridades_imagen(), orden)
            reiniciado = cargar("motor_reiniciado", "imagen.py")
            reiniciado.RUTA_PROVEEDOR = motor.RUTA_PROVEEDOR
            self.assertEqual(reiniciado.prioridades_imagen(), orden)
        with open(motor.RUTA_PROVEEDOR, "w", encoding="utf-8") as fh:
            json.dump({"proveedor": "codex"}, fh)
        self.assertEqual(motor.proveedor_imagen(), "codex")

    def test_rechaza_orden_incompleto_o_duplicado_sin_sobrescribir(self):
        motor.guardar_prioridades(["api", "codex"])
        for orden in (None, "api", [], ["api"], ["api", "api"], ["api", "otro"]):
            with self.assertRaises(ValueError):
                motor.guardar_prioridades(orden)
            self.assertEqual(motor.prioridades_imagen(), ["api", "codex"])

    def test_anadir_o_quitar_una_clave_no_cambia_la_prioridad(self):
        self.claves.return_value = []
        motor.conservar_prioridades_actuales()
        self.claves.return_value = [("", "sk-nueva")]
        self.assertEqual(motor.prioridades_imagen(), ["codex", "api"])
        motor.guardar_prioridades(["api", "codex"])
        motor.conservar_prioridades_actuales()
        self.claves.return_value = []
        self.assertEqual(motor.prioridades_imagen(), ["api", "codex"])

    def test_principal_sano_no_llama_al_respaldo(self):
        for orden in (["api", "codex"], ["codex", "api"]):
            motor.guardar_prioridades(orden)
            self.api.reset_mock()
            self.codex.generar.reset_mock()
            png, meta = motor.generar("plano", [])
            self.assertEqual(png.decode(), orden[0])
            self.assertEqual(meta["proveedor"], orden[0])
            self.assertNotIn("respaldo_de", meta)
            (self.api if orden[1] == "api" else self.codex.generar).assert_not_called()

    def test_codex_sin_cuota_sesion_o_servicio_recurre_a_api(self):
        motor.guardar_prioridades(["codex", "api"])
        for tipo in ("cuota", "sesion", "conexion", "tiempo", "servicio", "desconocido"):
            self.codex.generar.side_effect = codex.ErrorCodex("no disponible", tipo)
            png, meta = motor.generar("plano", [], quality="high", tamano="vertical")
            self.assertEqual(png, b"api")
            self.assertEqual(meta["respaldo_de"], "codex")
            self.assertEqual(meta["coste"], .01)
            self.api.assert_called_with("plano", [], quality="high", tamano="vertical", reintentos=0)

    def test_api_sin_saldo_autenticacion_o_red_recurre_a_codex(self):
        motor.guardar_prioridades(["api", "codex"])
        for fallo in (motor.SinSaldo("sin crédito"), RuntimeError("401 Incorrect API key"),
                      TimeoutError("timeout"), RuntimeError("HTTP 503")):
            self.api.side_effect = fallo
            png, meta = motor.generar("plano", [], quality="medium", tamano="cuadrado")
            self.assertEqual(png, b"codex")
            self.assertEqual(meta["respaldo_de"], "api")
            self.assertEqual(meta["coste"], 0)
            self.assertEqual(meta["facturacion"], "suscripcion_chatgpt")
            self.codex.generar.assert_called_with("plano", [], "medium", "1024x1024")

    def test_api_sin_clave_pasa_directamente_a_codex(self):
        motor.guardar_prioridades(["api", "codex"])
        self.claves.return_value = []
        self.assertEqual(motor.generar("plano", [])[0], b"codex")
        self.api.assert_not_called()

    def test_si_fallan_ambos_conserva_diagnosticos_y_recuperacion(self):
        from pasos.recuperacion_imagenes import clasificar
        for orden in (["api", "codex"], ["codex", "api"]):
            motor.guardar_prioridades(orden)
            self.api.side_effect = motor.SinSaldo("sin crédito")
            self.codex.generar.side_effect = codex.ErrorCodex("cuota agotada", "cuota", {"id": "diagnostico"})
            with self.assertRaises(motor.ErrorProveedores) as error:
                motor.generar("plano", [])
            self.assertIn("sin crédito", str(error.exception))
            self.assertIn("cuota agotada", str(error.exception))
            self.assertTrue(clasificar(error.exception))
            self.assertTrue(error.exception.cuota_renovable)
            self.assertEqual(error.exception.diagnostico["id"], "diagnostico")
        self.codex.generar.side_effect = codex.ErrorCodex("sesión caducada", "sesion")
        with self.assertRaises(motor.ErrorProveedores) as error:
            motor.generar("plano", [])
        self.assertFalse(clasificar(error.exception))
        self.api.side_effect = TimeoutError("timeout")
        with self.assertRaises(motor.ErrorProveedores) as error:
            motor.generar("plano", [])
        self.assertTrue(clasificar(error.exception))

    def test_cancelacion_y_rechazos_no_se_reenvian(self):
        from nucleo.trabajos import Cancelado
        motor.guardar_prioridades(["codex", "api"])
        for fallo in (Cancelado("parar"), codex.ErrorCodex("revisar encargo", "rechazo")):
            self.codex.generar.side_effect = fallo
            with self.assertRaises(type(fallo)):
                motor.generar("plano", [])
            self.api.assert_not_called()

    def test_api_real_429_pasa_al_respaldo_sin_esperar_ni_repetir(self):
        # Quita solo el doble de transporte: se ejercita la respuesta HTTP real
        # con una cuenta efímera, sin modificar claves ni límites del usuario.
        self.api.side_effect = self.generar_api_real
        motor.guardar_prioridades(["api", "codex"])
        respuesta = mock.Mock(status_code=429, text='{"error":{"code":"rate_limit_exceeded"}}', headers={})
        cuenta = motor._Cuenta("prueba", "sk-prueba")
        with mock.patch.object(motor, "_elegir_cuenta", return_value=cuenta), \
                mock.patch.object(motor, "_pedir_ficha"), \
                mock.patch.object(motor, "_esperar_turno"), \
                mock.patch.object(motor, "_aprender_del_429"), \
                mock.patch.object(motor.requests, "post", return_value=respuesta) as post, \
                mock.patch.object(motor.time, "sleep") as dormir:
            self.assertEqual(motor.generar("plano", [])[0], b"codex")
        post.assert_called_once()
        dormir.assert_not_called()

    generar_api_real = staticmethod(motor._generar_api)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        CARPETA.cleanup()
