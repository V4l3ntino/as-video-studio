"""Transferencias sin red: independencia, firmas, historial e integridad."""
import io
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo.proyecto import Proyecto, escribir_json, leer_json
from nucleo.estado import Estado, PASOS
from pasos import paquete_video as paquete


class Transferencia(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="prueba_video_portable_")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = self.temporal.name
        self.origen = os.path.join(self.raiz, "origen")
        self.destino = os.path.join(self.raiz, "destino")
        self.proyecto = Proyecto.crear(self.origen, "Video viajero")
        self.proyecto.config["estilo_light"] = "preset-del-origen"
        self.proyecto.guardar_config()
        self.externo = os.path.join(self.origen, "referencia.png")
        with open(self.externo, "wb") as fh:
            fh.write(b"referencia")
        estado = Estado(self.proyecto)
        for paso in PASOS:
            pid = paso["id"]
            estado.actualizar_params(pid, {"referencia": self.externo})
            salida = os.path.join(self.proyecto.ruta_paso(pid, 1, crear=True), "salida.txt")
            with open(salida, "w", encoding="utf-8") as fh:
                fh.write("contenido ya generado")
            salidas = {"archivo": salida}
            if pid in ("voz", "revision_audio"):
                salidas = {"archivo": "salida.txt", "pista": self.proyecto.ruta(
                    "pasos", pid, "trabajo", "salida.txt")}
            estado.completar(pid, salidas,
                             unidades={"escena:S001": {"archivo": salida}}
                             if paso["unidades"] else None)
            if pid == "assets":
                self.hasta_imagenes = copy.deepcopy(estado._doc)
        estado.completar("assets", estado.salidas("assets"),
                         unidades={"escena:S001": estado.salidas("assets")})
        doc = leer_json(self.proyecto.ruta("estado.json"))
        doc["pasos"]["guion"]["firma"] = "edicion-manual-intencionada"
        doc["pasos"]["render"]["firma"] = "pendiente-de-remontar"
        escribir_json(self.proyecto.ruta("estado.json"), doc)
        parcial = self.proyecto.ruta_trabajo("render")
        with open(os.path.join(parcial, "parcial.bin"), "wb") as fh:
            fh.write(b"trabajo parcial")
        self.previos = {p["id"]: Estado(self.proyecto).estado_de(p["id"]) for p in PASOS}
        escribir_json(self.proyecto.ruta("pasos", "voz", "v1", "audio_meta.json"), {
            "pista": self.proyecto.ruta("pasos", "voz", "trabajo", "narracion.wav")})
        self.zip = os.path.join(self.raiz, "video.zip")
        paquete.exportar(self.proyecto, self.zip)

    def importar(self, contenido=None):
        with open(self.zip, "rb") as fh:
            return paquete.importar(io.BytesIO(contenido or fh.read()), self.destino)

    def alterar(self, transformar):
        salida = io.BytesIO()
        with zipfile.ZipFile(self.zip) as fuente, zipfile.ZipFile(salida, "w") as destino:
            for entrada in fuente.infolist():
                datos = transformar(entrada.filename, fuente.read(entrada))
                if datos is not None:
                    destino.writestr(entrada, datos)
        return salida.getvalue()

    def test_independencia_historial_y_continuacion(self):
        shutil.rmtree(self.origen)
        nuevo = self.importar()
        actual = Estado(nuevo)
        self.assertEqual({p["id"]: actual.estado_de(p["id"]) for p in PASOS}, self.previos)
        self.assertNotIn("estilo_light", nuevo.config)
        self.assertEqual(actual._doc["pasos"]["guion"]["firma"], "edicion-manual-intencionada")
        self.assertTrue(os.path.isfile(actual.params("assets")["referencia"]))
        self.assertTrue(os.path.isfile(nuevo.ruta_trabajo("render") + "/parcial.bin"))
        versiones = actual._doc["pasos"]["assets"]["versiones"]
        self.assertEqual(len(versiones), 2)
        for version in versiones:
            mapa = actual.manifiesto_version("assets", version)
            self.assertTrue(os.path.isfile(mapa["escena:S001"]["salidas"]["archivo"]))
        segunda = self.importar()
        self.assertNotEqual(nuevo.id, segunda.id)
        # Completar el montaje en destino conserva el contenido previo.
        actual.completar("render", actual.salidas("render"))
        self.assertTrue(os.path.isfile(actual.salidas("assets")["archivo"]))

    def test_progreso_real_y_cancelacion(self):
        actualizaciones = []
        paquete.exportar(self.proyecto, self.zip,
                         avisar=lambda valor, mensaje: actualizaciones.append((valor, mensaje)))
        valores = [valor for valor, _ in actualizaciones]
        self.assertEqual(valores[0], 0)
        self.assertEqual(valores[-1], 1)
        self.assertEqual(valores, sorted(valores))
        self.assertTrue(any('Copiando archivos' in m for _, m in actualizaciones))
        self.assertTrue(any('Verificando integridad' in m for _, m in actualizaciones))
        self.assertTrue(any('Comprimiendo ZIP' in m for _, m in actualizaciones))
        from nucleo.trabajos import Cancelado
        def detener(valor, mensaje):
            if valor > .55:
                raise Cancelado()
        with self.assertRaises(Cancelado):
            paquete.exportar(self.proyecto, self.zip, avisar=detener)

    def test_importacion_progreso_y_cancelacion_antes_de_publicar(self):
        from nucleo.trabajos import Cancelado
        actualizaciones = []
        with open(self.zip, "rb") as f:
            proyecto = paquete.importar(f, self.destino, avisar=lambda valor, mensaje:
                                       actualizaciones.append((valor, mensaje)))
        self.assertTrue(os.path.isfile(proyecto.ruta("proyecto.json")))
        valores = [v for v, _ in actualizaciones]
        self.assertEqual(valores, sorted(valores))
        self.assertEqual(valores[0], 0)
        self.assertEqual(valores[-1], .99)
        for etapa in ('Descomprimiendo', 'Verificando integridad', 'Adaptando rutas',
                      'Adaptando las firmas', 'Finalizando'):
            self.assertTrue(any(etapa in mensaje for _, mensaje in actualizaciones), etapa)
        cancelada = os.path.join(self.raiz, "cancelada")
        def detener(valor, mensaje):
            if valor >= .99:
                raise Cancelado()
        with open(self.zip, "rb") as f, self.assertRaises(Cancelado):
            paquete.importar(f, cancelada, avisar=detener)
        self.assertEqual(os.listdir(cancelada), [])

    def test_incompleto_y_alterado_no_publican(self):
        for contenido in (
                self.alterar(lambda n, d: None if n.endswith("_versiones/v1.json") else d),
                self.alterar(lambda n, d: b"alterado" if n.endswith("parcial.bin") else d),
                b"no es un ZIP"):
            with self.assertRaises(paquete.ErrorPaquete):
                self.importar(contenido)
            self.assertEqual(Proyecto.listar(self.destino), [])
            self.assertEqual(os.listdir(self.destino), [])

    def test_listo_para_montar_desde_windows(self):
        escribir_json(self.proyecto.ruta("estado.json"), self.hasta_imagenes)
        esperado = {p["id"]: Estado(self.proyecto).estado_de(p["id"]) for p in PASOS}
        self.assertEqual(esperado["assets"], "listo")
        # Simula el origen Windows, incluidas sus firmas, sin necesitar ese SO.
        antes = paquete.mudanza._calculadas(Estado(self.proyecto))
        raiz_windows = "C:\\Estudio\\proyectos\\viajero"
        reglas = [(self.proyecto.raiz, raiz_windows),
                  (self.externo, "C:\\Banco\\referencia.png")]
        for ruta, tipo in list(paquete.mudanza.ficheros_json(self.proyecto.raiz)):
            paquete.mudanza.mudar_fichero(ruta, tipo, reglas, True)
        paquete.mudanza.resellar(self.proyecto.raiz, antes, True, [])
        # Empaqueta directamente: los ficheros siguen en el disco Linux de prueba.
        carpeta = os.path.join(self.raiz, "paquete_windows")
        paquete.comun._copiar_arbol(self.proyecto.raiz, os.path.join(carpeta, "proyecto"))
        os.makedirs(os.path.join(carpeta, "extras"))
        shutil.copyfile(self.externo, os.path.join(carpeta, "extras", "ref.png"))
        inventario = {n: {"bytes": os.path.getsize(r), "sha256": paquete._huella(r)}
                      for n, r in paquete._ficheros(carpeta)}
        escribir_json(os.path.join(carpeta, "video.json"), {
            "formato": paquete.FORMATO, "version": paquete.VERSION,
            "raiz": raiz_windows, "externos": {"C:\\Banco\\referencia.png": "extras/ref.png"},
            "ficheros": inventario})
        with zipfile.ZipFile(self.zip, "w") as z:
            for n, r in paquete._ficheros(carpeta):
                z.write(r, n)
        shutil.rmtree(self.origen)
        nuevo = self.importar()
        actual = Estado(nuevo)
        self.assertEqual({p["id"]: actual.estado_de(p["id"]) for p in PASOS}, esperado)
        self.assertTrue(os.path.isfile(actual.salidas("assets")["archivo"]))
        self.assertTrue(os.path.isfile(actual.params("assets")["referencia"]))

    def test_traversal_y_limites(self):
        malo = io.BytesIO()
        with zipfile.ZipFile(malo, "w") as z:
            z.writestr("../fuera", "no")
        with self.assertRaises(paquete.ErrorPaquete):
            self.importar(malo.getvalue())
        with patch.object(paquete, "MAX_BYTES", 10):
            with self.assertRaises(paquete.ErrorPaquete):
                self.importar()

    def test_manifiesto_ausente_aun_con_inventario_coherente(self):
        ausente = "proyecto/pasos/assets/_versiones/v1.json"
        def transformar(nombre, datos):
            if nombre == ausente:
                return None
            if nombre == "video.json":
                doc = json.loads(datos)
                doc["ficheros"].pop(ausente)
                return json.dumps(doc).encode()
            return datos
        with self.assertRaises(paquete.ErrorPaquete):
            self.importar(self.alterar(transformar))
        self.assertEqual(Proyecto.listar(self.destino), [])

    def test_salida_ausente_aun_con_inventario_coherente(self):
        ausente = "proyecto/pasos/assets/v1/salida.txt"
        def transformar(nombre, datos):
            if nombre == ausente:
                return None
            if nombre == "video.json":
                doc = json.loads(datos)
                doc["ficheros"].pop(ausente)
                return json.dumps(doc).encode()
            return datos
        with self.assertRaises(paquete.ErrorPaquete):
            self.importar(self.alterar(transformar))
        self.assertEqual(Proyecto.listar(self.destino), [])

    def test_ejecucion_interrumpida_se_puede_retomar(self):
        estado = Estado(self.proyecto)
        estado.marcar_ejecutando("render")
        paquete.exportar(self.proyecto, self.zip)
        nuevo = self.importar()
        self.assertNotEqual(Estado(nuevo).estado_de("render"), "ejecutando")
        self.assertTrue(os.path.isfile(nuevo.ruta("pasos", "render", "trabajo", "parcial.bin")))

    def test_referencias_temporales_se_resuelven_en_cada_version(self):
        estado = Estado(self.proyecto)
        doc = estado._doc
        referencia = self.proyecto.ruta("pasos", "assets", "trabajo", "_refs", "ref.png")
        for version in doc["pasos"]["assets"]["versiones"]:
            n = version["n"]
            ruta = self.proyecto.ruta("pasos", "assets", f"v{n}", "_refs", "ref.png")
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "wb") as f:
                f.write(b"referencia de la version")
            mapa = estado.manifiesto_version("assets", version)
            mapa["escena:S001"]["salidas"]["referencias"] = [{"ruta": referencia}]
            estado._guardar_manifiesto("assets", n, mapa)
        doc["pasos"]["assets"]["unidades"]["escena:S001"]["salidas"]["referencias"] = [
            {"ruta": referencia}]
        escribir_json(self.proyecto.ruta("estado.json"), doc)
        paquete.exportar(self.proyecto, self.zip)
        nuevo = self.importar()
        self.assertTrue(os.path.isfile(nuevo.ruta("pasos", "voz", "v1", "salida.txt")))
        # No basta con que exista la referencia en la version activa.
        os.remove(self.proyecto.ruta("pasos", "assets", "v1", "_refs", "ref.png"))
        with self.assertRaises(paquete.ErrorPaquete):
            paquete.exportar(self.proyecto, self.zip)

    def test_audio_definitivo_ausente_no_se_oculta(self):
        os.remove(self.proyecto.ruta("pasos", "voz", "v1", "salida.txt"))
        with self.assertRaises(paquete.ErrorPaquete):
            paquete.exportar(self.proyecto, self.zip)


if __name__ == "__main__":
    unittest.main()
