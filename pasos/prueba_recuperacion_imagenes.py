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
        for tipo in ("cuota", "sesion", "rechazo", "referencias", "respuesta_incompleta"):
            fallo = ErrorServicio("no se ha entregado imagen", tipo)
            with self.subTest(tipo=tipo), patch.object(avisos, "enviar", return_value={"estado": "desactivado"}):
                funcion = Mock(side_effect=fallo)
                sesion = recuperacion.Recuperacion(self.proyecto, lambda *_a: None)
                with self.assertRaises(ErrorServicio):
                    sesion.ejecutar(funcion, "S001")
                funcion.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()
