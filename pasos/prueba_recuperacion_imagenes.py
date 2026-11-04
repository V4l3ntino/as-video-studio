"""Recuperación y correo con reloj virtual, SMTP doble y sin imágenes de pago."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_aislado = tempfile.TemporaryDirectory(prefix="recuperacion_config_")
for _variable in ("ESTUDIO_SECRETOS", "ESTUDIO_AJUSTES", "ESTUDIO_ESTADISTICAS",
                  "ESTUDIO_COSTE_GLOBAL", "ESTUDIO_BITACORA_GLOBAL"):
    os.environ[_variable] = os.path.join(_aislado.name, _variable)

from nucleo.trabajos import Cancelado
from pasos import avisos, medios, p6_assets, recuperacion_imagenes as recuperacion


class ErrorServicio(RuntimeError):
    def __init__(self, mensaje="Selected model is at capacity", tipo="saturacion"):
        super().__init__(mensaje)
        self.tipo = tipo
        self.diagnostico = "diagnostico-de-prueba"


class RecuperacionImagenes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="recuperacion_prueba_")
        self.addCleanup(self.tmp.cleanup)
        entorno = patch.dict(os.environ, {"ESTUDIO_SECRETOS": os.path.join(self.tmp.name, "secretos")})
        entorno.start()
        self.addCleanup(entorno.stop)
        self.proyecto = SimpleNamespace(id="video", config={"nombre": "Vídeo de prueba"}, raiz=self.tmp.name,
            ruta=lambda *p: os.path.join(self.tmp.name, *p),
            ruta_trabajo=lambda paso, crear=False: os.path.join(self.tmp.name, "pasos", paso, "trabajo"))
        avisos.guardar({"intervalo": 10, "intervalo_maximo": 20})

    def reloj(self):
        self.ahora = 0.0
        def dormir(segundos):
            self.ahora += segundos
        uno = patch.object(recuperacion.time, "monotonic", side_effect=lambda: self.ahora)
        dos = patch.object(recuperacion.time, "sleep", side_effect=dormir)
        uno.start()
        dos.start()
        self.addCleanup(uno.stop)
        self.addCleanup(dos.stop)

    def test_reintenta_solo_la_imagen_pendiente_y_avisa_una_vez(self):
        self.reloj()
        sesion = recuperacion.Recuperacion(self.proyecto, lambda *_a: None)
        carpeta = self.proyecto.ruta_trabajo("assets")
        medios.escribir_json(os.path.join(carpeta, "plan.json"), {"escenas": [{"id": "S001"}, {"id": "S002"}]})
        llamadas = []
        intentos_dos = 0
        def generar(prompt, *_a, **_k):
            nonlocal intentos_dos
            llamadas.append(prompt)
            if prompt == "segunda":
                intentos_dos += 1
                if intentos_dos < 3:
                    raise ErrorServicio()
            return prompt.encode(), {"coste": 0, "segundos": 1}
        p = p6_assets._con_defectos({"banco_imagenes": os.path.join(self.tmp.name, "banco")})
        with patch.object(p6_assets.medios, "motor", return_value=SimpleNamespace(generar=generar)), \
             patch.object(avisos, "enviar", return_value={"estado": "enviado"}) as correo:
            p6_assets._producir_imagen("S001", "primera", [], os.path.join(carpeta, "escenas", "S001.png"),
                                      p, recuperacion=sesion)
            p6_assets._producir_imagen("S002", "segunda", [], os.path.join(carpeta, "escenas", "S002.png"),
                                      p, recuperacion=sesion)
        self.assertEqual(llamadas, ["primera", "segunda", "segunda", "segunda"])
        self.assertEqual(self.ahora, 30)
        self.assertEqual(correo.call_count, 2)  # incidencia y recuperación, no cada sondeo
        registros = list(Path(self.proyecto.ruta("incidencias_imagenes")).glob("*.json"))
        self.assertEqual(len(registros), 1)
        datos = json.loads(registros[0].read_text())
        self.assertEqual(datos["estado"], "recuperada")
        self.assertEqual(datos["progreso"], {"total": 2, "con_imagen": 1})
        self.assertEqual(datos["unidades"], ["S002"])

    def test_fallos_no_recuperables_no_se_repiten(self):
        for tipo in ("cuota", "sesion", "rechazo", "referencias", "modelo", "respuesta_ambigua"):
            fallo = ErrorServicio("no se ha entregado imagen", tipo)
            with self.subTest(tipo=tipo), patch.object(avisos, "enviar", return_value={"estado": "desactivado"}):
                funcion = Mock(side_effect=fallo)
                sesion = recuperacion.Recuperacion(self.proyecto, lambda *_a: None)
                with self.assertRaises(ErrorServicio):
                    sesion.ejecutar(funcion, "S001")
                funcion.assert_called_once()

    def test_entrega_incompleta_e_interrupcion_reintentan_hasta_recuperar(self):
        self.reloj()
        for tipo in ("respuesta_incompleta", "interrumpido"):
            with self.subTest(tipo=tipo), patch.object(avisos, "enviar", return_value={}) as correo:
                progreso = Mock()
                sesion = recuperacion.Recuperacion(self.proyecto, progreso)
                funcion = Mock(side_effect=[ErrorServicio("sin imagen", tipo)] * 12 + [b"imagen"])
                self.assertEqual(sesion.ejecutar(funcion, "S001"), b"imagen")
                self.assertEqual(funcion.call_count, 13)
                self.assertEqual(correo.call_count, 2)
                self.assertFalse(sesion._reintentos)
                mensajes = [c.args[1] for c in progreso.call_args_list]
                self.assertTrue(any("Nuevo intento automático" in m for m in mensajes))
                self.assertTrue(any("Solicitando de nuevo la imagen" in m for m in mensajes))
                self.assertTrue(all(c.args[0] is None for c in progreso.call_args_list))

    def test_el_avance_de_otra_cadena_no_oculta_la_espera(self):
        self.reloj()
        progreso = Mock()
        sesion = recuperacion.Recuperacion(self.proyecto, progreso)
        with patch.object(avisos, "enviar", return_value={}):
            sesion._registrar(ErrorServicio(), "S001", True, 1, 10)
        sesion.avisar_progreso(.6, "S002 resuelto", (20, 100))
        args = progreso.call_args.args
        self.assertEqual(args[0], .6)
        self.assertEqual(args[2], (20, 100))
        self.assertIn("Esperando al servicio de imágenes:", args[1])
        self.assertIn("S001", args[1])
        self.assertIn("Tanda activa", args[1])
        with patch.object(avisos, "enviar", return_value={}):
            self.assertEqual(sesion.ejecutar(lambda: b"imagen", "S001"), b"imagen")
        sesion.avisar_progreso(.7, "S001 resuelto", (21, 100))
        self.assertEqual(progreso.call_args.args, (.7, "S001 resuelto", (21, 100)))

    def test_desactivar_reintentos_detiene_sin_hacer_otra_peticion(self):
        self.reloj()
        progreso = Mock(side_effect=lambda *_a: avisos.guardar({"reintentos": False}))
        sesion = recuperacion.Recuperacion(self.proyecto, progreso)
        funcion = Mock(side_effect=ErrorServicio())
        with patch.object(avisos, "enviar", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "desactivado"):
                sesion.ejecutar(funcion, "S001")
        funcion.assert_called_once()
        self.assertTrue(sesion._parar.is_set())

    def test_trabajo_sigue_activo_en_espera_y_solo_termina_al_recuperarse(self):
        from nucleo.trabajos import GestorTrabajos
        esperando, continuar = threading.Event(), threading.Event()
        gestor = GestorTrabajos()
        funcion = Mock(side_effect=[ErrorServicio("entrega incompleta", "respuesta_incompleta"), b"png"])

        def correr(avisar):
            sesion = recuperacion.Recuperacion(self.proyecto,
                lambda valor, mensaje="": avisar(valor, mensaje, mensaje))
            sesion.avisar_progreso(.42, "42 de 100 imagenes")
            return sesion.ejecutar(funcion, "S043")

        def esperar(sesion, *_a):
            sesion.avisar_progreso(None)
            esperando.set()
            self.assertTrue(continuar.wait(3))

        with patch.object(recuperacion.Recuperacion, "_esperar", esperar), \
                patch.object(avisos, "enviar", return_value={}):
            tid = gestor.lanzar("generar:video", correr)
            try:
                self.assertTrue(esperando.wait(3))
                ficha = gestor.estado(tid)
                self.assertEqual(ficha["estado"], "ejecutando")
                self.assertEqual(ficha["progreso"], .42)
                self.assertIn("Nuevo intento automático", ficha["publico"])
                self.assertEqual(len(gestor.listar(activos=True)), 1)
                funcion.assert_called_once()
            finally:
                continuar.set()
            final = gestor.esperar(tid, 3)
        self.assertEqual(final["estado"], "listo")
        self.assertEqual(final["resultado"], b"png")
        self.assertEqual(funcion.call_count, 2)
        self.assertFalse(gestor.listar(activos=True))

    def test_cancelar_durante_espera_detiene_las_otras_cadenas(self):
        with patch.object(avisos, "enviar", return_value={"estado": "enviado"}):
            def cancelar(*_a):
                raise Cancelado("cancelado")
            sesion = recuperacion.Recuperacion(self.proyecto, cancelar)
            with self.assertRaises(Cancelado):
                sesion.ejecutar(Mock(side_effect=ErrorServicio()), "S001")
            otro = Mock()
            with self.assertRaises(Cancelado):
                sesion.ejecutar(otro, "S002")
            otro.assert_not_called()

    def test_correo_que_falla_no_impide_recuperar_el_servicio(self):
        self.reloj()
        with patch.object(avisos, "enviar", side_effect=RuntimeError("SMTP no responde")):
            resultado = recuperacion.Recuperacion(self.proyecto, lambda *_a: None).ejecutar(
                Mock(side_effect=[ErrorServicio(), "imagen"]), "S001")
        self.assertEqual(resultado, "imagen")

    def test_dos_cadenas_comparten_incidencia_y_no_duplican_correos(self):
        barrera = threading.Barrier(2)
        sesion = recuperacion.Recuperacion(self.proyecto, lambda *_a: None)
        funciones = {nombre: Mock(side_effect=[ErrorServicio(), nombre]) for nombre in ("S001", "S002")}
        with patch.object(sesion, "_esperar", side_effect=lambda *_a: barrera.wait(timeout=3)), \
             patch.object(avisos, "enviar", return_value={"estado": "enviado"}) as correo, \
             ThreadPoolExecutor(max_workers=2) as hilos:
            futuros = [hilos.submit(sesion.ejecutar, funciones[nombre], nombre) for nombre in funciones]
            self.assertEqual({f.result(timeout=5) for f in futuros}, {"S001", "S002"})
        self.assertEqual(correo.call_count, 2)
        registros = list(Path(self.proyecto.ruta("incidencias_imagenes")).glob("*.json"))
        self.assertEqual(len(registros), 1)
        self.assertEqual(set(json.loads(registros[0].read_text())["unidades"]), {"S001", "S002"})

    def test_fallo_permanente_desbloquea_la_cadena_que_espera(self):
        esperando = threading.Event()
        sesion = recuperacion.Recuperacion(self.proyecto, lambda *_a: None)
        def esperar(*_a):
            esperando.set()
            self.assertTrue(sesion._parar.wait(timeout=3))
        def fallar():
            self.assertTrue(esperando.wait(timeout=3))
            raise ErrorServicio("sesión caducada", "sesion")
        with patch.object(sesion, "_esperar", side_effect=esperar), \
             patch.object(avisos, "enviar", return_value={"estado": "enviado"}) as correo, \
             ThreadPoolExecutor(max_workers=2) as hilos:
            temporal = hilos.submit(sesion.ejecutar, Mock(side_effect=ErrorServicio()), "S001")
            permanente = hilos.submit(sesion.ejecutar, fallar, "S002")
            with self.assertRaises(ErrorServicio):
                permanente.result(timeout=5)
            with self.assertRaises(RuntimeError):
                temporal.result(timeout=5)
        self.assertEqual(correo.call_count, 2)  # incidencia inicial y detención que exige intervención

    def test_no_hay_callback_cancelable_entre_imagen_obtenida_y_su_guardado(self):
        self.reloj()
        obtenida = {"si": False}
        def avisar(*_a):
            if obtenida["si"]:
                raise Cancelado("la imagen pagada no debe perderse antes de guardarla")
        def pedir():
            if pedir.llamadas == 0:
                pedir.llamadas += 1
                raise ErrorServicio()
            obtenida["si"] = True
            return b"imagen recuperada"
        pedir.llamadas = 0
        with patch.object(avisos, "enviar", return_value={"estado": "enviado"}):
            resultado = recuperacion.Recuperacion(self.proyecto, avisar).ejecutar(pedir, "S001")
        self.assertEqual(resultado, b"imagen recuperada")

    def test_gmail_prueba_mensaje_real_smtp_doble_y_no_expone_clave(self):
        cfg = avisos.guardar({"usuario": "cuenta@example.com", "clave": "contraseña-de-aplicación",
            "remitente": "cuenta@example.com", "destinatario": "persona@example.com", "activo": True})
        self.assertNotIn("contraseña-de-aplicación", json.dumps(cfg))
        conexion = Mock()
        conexion.__enter__ = Mock(return_value=conexion)
        conexion.__exit__ = Mock(return_value=False)
        conexion.send_message.return_value = {}
        with patch.object(avisos.smtplib, "SMTP_SSL", return_value=conexion) as smtp:
            resultado = avisos.probar()
        self.assertEqual(resultado["estado"], "enviado")
        self.assertEqual(smtp.call_args.args[:2], ("smtp.gmail.com", 465))
        conexion.login.assert_called_once_with("cuenta@example.com", "contraseña-de-aplicación")
        mensaje = conexion.send_message.call_args.args[0]
        self.assertEqual(mensaje["To"], "persona@example.com")
        self.assertIn("diagnóstico", mensaje.get_content())
        self.assertNotIn("contraseña-de-aplicación", mensaje.as_string())
        avisos.guardar({"clave": avisos.CONSERVAR})
        self.assertTrue(avisos.resumen()["clave_guardada"])
        with patch.object(avisos.smtplib, "SMTP_SSL", side_effect=RuntimeError("error contraseña-de-aplicación")):
            resultado = avisos.probar()
        self.assertNotIn("contraseña-de-aplicación", json.dumps(resultado))

    def test_red_y_timeout_son_recuperables_y_la_cuota_no(self):
        import requests
        self.assertTrue(recuperacion.clasificar(requests.ConnectionError("offline")))
        self.assertTrue(recuperacion.clasificar(TimeoutError("sin respuesta")))
        self.assertFalse(recuperacion.clasificar(ErrorServicio("timeout pero cuota agotada", "cuota")))
        ultimo = ErrorServicio("la petición alternativa agotó el tiempo", "tiempo")
        ultimo.__context__ = ErrorServicio("el prompt original fue rechazado", "rechazo")
        self.assertTrue(recuperacion.clasificar(ultimo))

    def test_correos_de_finalizacion_por_fase_y_version_sin_duplicados(self):
        with patch.object(avisos, "enviar", return_value={"estado": "enviado"}) as correo:
            for _ in range(2):
                avisos.notificar_finalizacion(self.proyecto, "imagenes", 3, {"escenas": 211})
            avisos.notificar_finalizacion(self.proyecto, "video", 1,
                {"archivo": "pasos/render/v1/video.mp4", "duracion": 120})
            self.assertEqual(correo.call_count, 2)
            self.assertIn("listas para montar", correo.call_args_list[0].args[0])
            self.assertIn("Escenas preparadas: 211", correo.call_args_list[0].args[1])
            self.assertIn("vídeo disponible", correo.call_args_list[1].args[0])
            self.assertIn("descargar el MP4", correo.call_args_list[1].args[1])
            avisos.notificar_finalizacion(self.proyecto, "video", 2,
                {"archivo": "pasos/render/v2/video.mp4", "duracion": 120})
            self.assertEqual(correo.call_count, 3)

    def test_avisa_solo_si_la_tanda_completa_y_el_mp4_estan_en_disco(self):
        import app
        self.proyecto.ruta_paso = lambda paso, version=None: self.proyecto.ruta("pasos", paso, f"v{version or 1}")
        ctx = SimpleNamespace(proyecto=self.proyecto, estado=SimpleNamespace(al_dia=lambda _p: True),
                              bitacora=SimpleNamespace(anotar=Mock()))
        imagen = Path(self.proyecto.ruta_paso("assets", 1), "escenas", "S001.png")
        imagen.parent.mkdir(parents=True)
        imagen.write_bytes(b"imagen de prueba")
        with patch.object(app.PASOS_MODULOS.p6_assets, "plan_actual", return_value={"escenas": [{"id": "S001"}]}), \
             patch.object(app.PASOS_MODULOS.avisos, "notificar_finalizacion", return_value={"estado": "enviado"}) as aviso:
            app._avisar_paso_listo(ctx, "assets", 1, {"n_escenas": 0}, None, {})
            app._avisar_paso_listo(ctx, "assets", 1, {"n_escenas": 1}, None, {"solo_assets": True})
            app._avisar_paso_listo(ctx, "assets", 1, {"n_escenas": 1}, ["escena:S001"], {})
            aviso.assert_not_called()
            app._avisar_paso_listo(ctx, "assets", 1, {"n_escenas": 1}, ["escena:S001"],
                                  {"avisar_tanda_imagenes": True})
            self.assertEqual(aviso.call_args.args[1], "imagenes")
            imagen.unlink()
            app._avisar_paso_listo(ctx, "assets", 1, {"n_escenas": 1}, None, {})
            self.assertEqual(aviso.call_count, 1)
            app._avisar_paso_listo(ctx, "render", 1, {"mp4": "video.mp4"}, None, {})
            self.assertEqual(aviso.call_count, 1)
            video = Path(self.proyecto.ruta_paso("render", 1), "video.mp4")
            video.parent.mkdir(parents=True)
            video.write_bytes(b"mp4 ya completado")
            app._avisar_paso_listo(ctx, "render", 1, {"mp4": "video.mp4", "duracion": 60}, None, {})
            self.assertEqual(aviso.call_count, 2)
            self.assertEqual(aviso.call_args.args[1], "video")

    def test_fallo_de_correo_no_invalida_el_video_completado(self):
        import app
        self.proyecto.ruta_paso = lambda paso, version=None: self.proyecto.ruta("pasos", paso, f"v{version or 1}")
        estado = SimpleNamespace(params=lambda _p: {}, completar=Mock(return_value=1))
        ctx = SimpleNamespace(proyecto=self.proyecto, estado=estado, bitacora=SimpleNamespace(anotar=Mock()))
        modulo = SimpleNamespace(ejecutar=lambda _p, _params, _avisar: {"mp4": "video.mp4"})
        with patch.object(app, "modulo_de", return_value=modulo), \
             patch.object(app, "_avisar_paso_listo", side_effect=RuntimeError("SMTP no disponible")):
            resultado = app._ejecutar_paso(lambda *_a: None, ctx, "render", None)
        self.assertEqual(resultado["version"], 1)
        estado.completar.assert_called_once()
        self.assertIn("aviso_no_disponible", [c.args[0] for c in ctx.bitacora.anotar.call_args_list])


if __name__ == "__main__":
    unittest.main()
