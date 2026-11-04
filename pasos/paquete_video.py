"""Proyectos portables: historial, fuentes y trabajo parcial, sin generar nada."""
import hashlib
import os
import shutil
import tempfile
import uuid
import zipfile

from nucleo.proyecto import Proyecto, escribir_json, leer_json, lock_de, ruta_contenida
from . import paquete_estilo as comun
from herramientas import mudar_proyecto as mudanza

ErrorPaquete = comun.ErrorPaquete
FORMATO = "as-video-studio/video"
VERSION = 1
MAX_ARCHIVO = 2 * 1024 ** 3
MAX_BYTES = 20 * 1024 ** 3
MAX_FICHEROS = 100000


def _huella(ruta, avanzar=None):
    sello = hashlib.sha256()
    with open(ruta, "rb") as fuente:
        for bloque in iter(lambda: fuente.read(1024 * 1024), b""):
            sello.update(bloque)
            if avanzar:
                avanzar(len(bloque))
    return sello.hexdigest()


def _ficheros(carpeta):
    for base, _, nombres in os.walk(carpeta):
        for nombre in sorted(nombres):
            ruta = os.path.join(base, nombre)
            yield os.path.relpath(ruta, carpeta).replace("\\", "/"), ruta


def _comprobar_salidas(estado, raiz_guardada):
    """Comprueba el contrato de cada version, no las rutas de su ejecucion.

    Voz conserva `pista=.../trabajo/narracion.wav` junto a `archivo=narracion.wav`;
    las escenas conservan referencias a trabajo/_refs. Al completar se recoge
    trabajo en vN sin reescribir esos metadatos. La comprobacion debe resolverlos
    en SU version (tambien para el historico), sin tocar firmas ni documentos.
    """
    proyecto = estado.proyecto
    reglas = [(raiz_guardada, proyecto.raiz)]

    def comprobar(dato, paso, numero):
        if isinstance(dato, dict):
            for clave, valor in dato.items():
                if (clave in ("archivo", "png", "meta", "guion_fichero")
                        and isinstance(valor, str) and valor
                        and not comun._absoluta(valor)):
                    ruta = ruta_contenida(proyecto.ruta_paso(paso, numero), valor)
                    if not os.path.isfile(ruta):
                        raise ErrorPaquete(f"falta una salida del video ({paso} v{numero}): {valor}")
                comprobar(valor, paso, numero)
        elif isinstance(dato, list):
            for valor in dato:
                comprobar(valor, paso, numero)
        elif isinstance(dato, str) and comun._absoluta(dato):
            ruta = mudanza.mudar_cadena(dato, reglas)[0]
            # Primero la version: un nuevo trabajo parcial puede estar usando
            # el mismo nombre, pero no es la salida de esta version historica.
            for pid, datos in estado._doc["pasos"].items():
                trabajo = proyecto.ruta_trabajo(pid, crear=False)
                if comun._bajo(ruta, trabajo):
                    version = numero if pid == paso else datos.get("activa")
                    if version is not None:
                        ruta = mudanza.mudar_cadena(
                            ruta, [(trabajo, proyecto.ruta_paso(pid, version))])[0]
                    break
            if not os.path.exists(ruta):
                raise ErrorPaquete(f"falta una salida del video ({paso} v{numero}): {dato}")

    for paso, datos in estado._doc["pasos"].items():
        numero = datos.get("activa")
        comprobar(datos.get("salidas"), paso, numero)
        comprobar(datos.get("unidades"), paso, numero)
        for version in datos.get("versiones") or []:
            comprobar(version.get("salidas"), paso, version["n"])
            comprobar(estado.manifiesto_version(paso, version), paso, version["n"])


def exportar(proyecto, destino, avisar=None):
    """Conserva las rutas y firmas originales para el sellado selectivo al importar."""
    avisar = avisar or (lambda valor, mensaje: None)
    avisar(0, "Revisando los archivos del proyecto")
    with lock_de(proyecto.ruta("estado.json")), lock_de(proyecto.ruta("proyecto.json")):
        with tempfile.TemporaryDirectory(prefix="video_exportar_") as temporal:
            carpeta = os.path.join(temporal, "proyecto")
            total_origen = sum(os.path.getsize(ruta) for _, ruta in _ficheros(proyecto.raiz))
            copiados = 0
            def copiar(cantidad):
                nonlocal copiados
                copiados += cantidad
                avisar(.3 * min(1, copiados / max(1, total_origen)),
                       f"Copiando archivos: {copiados / 1024 ** 2:.1f} de "
                       f"{total_origen / 1024 ** 2:.1f} MiB")
            comun._copiar_arbol(proyecto.raiz, carpeta, avisar=copiar)
            avisar(.3, "Comprobando las versiones y sus archivos")
            _comprobar_salidas(comun._comprobar_manifiestos(carpeta), proyecto.raiz)
            externos = {}
            documentos = list(mudanza.ficheros_json(carpeta))
            for indice, (ruta, tipo) in enumerate(documentos):
                avisar(.3 + .1 * (indice + 1) / max(1, len(documentos)),
                       f"Revisando referencias: {indice + 1} de {len(documentos)} archivos")
                if tipo != "json":
                    continue
                for valor in comun._cadenas(leer_json(ruta, estricto=True)):
                    if (not comun._absoluta(valor) or comun._bajo(valor, proyecto.raiz)
                            or valor in externos):
                        continue
                    if not os.path.isfile(valor) or os.path.islink(valor):
                        raise ErrorPaquete(f"no se puede trasladar esta referencia: {valor}")
                    relativo = "extras/" + uuid.uuid4().hex + os.path.splitext(valor)[1]
                    final = os.path.join(temporal, *relativo.split("/"))
                    os.makedirs(os.path.dirname(final), exist_ok=True)
                    shutil.copyfile(valor, final)
                    externos[valor] = relativo
            ficheros = list(_ficheros(temporal))
            total_bytes = sum(os.path.getsize(ruta) for _, ruta in ficheros)
            verificados = 0
            def verificar(cantidad):
                nonlocal verificados
                verificados += cantidad
                avisar(.4 + .15 * verificados / max(1, total_bytes),
                       f"Verificando integridad: {verificados / 1024 ** 2:.1f} de "
                       f"{total_bytes / 1024 ** 2:.1f} MiB")
            inventario = {nombre: {"bytes": os.path.getsize(ruta),
                                   "sha256": _huella(ruta, avanzar=verificar)}
                          for nombre, ruta in ficheros}
            if (len(inventario) >= MAX_FICHEROS
                    or sum(f["bytes"] for f in inventario.values()) > MAX_BYTES):
                raise ErrorPaquete("el video supera 20 GB o 100000 ficheros")
            escribir_json(os.path.join(temporal, "video.json"), {
                "formato": FORMATO, "version": VERSION, "raiz": proyecto.raiz,
                "externos": externos, "ficheros": inventario,
            })
            ficheros = list(_ficheros(temporal))
            total_bytes = sum(os.path.getsize(ruta) for _, ruta in ficheros)
            comprimidos = 0
            with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as salida:
                for indice, (nombre, ruta) in enumerate(ficheros):
                    info = zipfile.ZipInfo.from_file(ruta, nombre)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with open(ruta, "rb") as fuente, salida.open(info, "w", force_zip64=True) as final:
                        for bloque in iter(lambda: fuente.read(1024 * 1024), b""):
                            final.write(bloque)
                            comprimidos += len(bloque)
                            avisar(.55 + .44 * comprimidos / max(1, total_bytes),
                                   f"Comprimiendo ZIP: archivo {indice + 1} de {len(ficheros)} · "
                                   f"{comprimidos / 1024 ** 2:.1f} de {total_bytes / 1024 ** 2:.1f} MiB")
            if os.path.getsize(destino) > MAX_ARCHIVO:
                raise ErrorPaquete("el ZIP del video supera el limite de 2 GB")
            avisar(1, "ZIP preparado; listo para descargar")


def importar(archivo, raiz_proyectos, avisar=None):
    """Valida en una carpeta privada y publica por renombrado una copia nueva."""
    avisar = avisar or (lambda valor, mensaje: None)
    avisar(0, "Abriendo el ZIP recibido")
    os.makedirs(raiz_proyectos, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video_importar_", dir=raiz_proyectos) as temporal:
        try:
            def extraer(cantidad, total, indice, ficheros):
                avisar(.35 * cantidad / max(1, total),
                       f"Descomprimiendo: archivo {indice} de {ficheros} · "
                       f"{cantidad / 1024 ** 2:.1f} de {total / 1024 ** 2:.1f} MiB")
            comun._extraer(archivo, temporal, max_bytes=MAX_BYTES,
                           max_ficheros=MAX_FICHEROS,
                           permitidos=("video.json", "proyecto", "extras"), avisar=extraer)
            avisar(.35, "Comprobando el inventario del paquete")
            doc = leer_json(os.path.join(temporal, "video.json"), estricto=True)
            if (not isinstance(doc, dict) or doc.get("formato") != FORMATO
                    or doc.get("version") != VERSION):
                raise ErrorPaquete("este ZIP no es un video exportado compatible")
            original = doc.get("raiz")
            if (not isinstance(original, str) or not comun._absoluta(original)
                    or len(original.rstrip("/\\")) < 4):
                raise ErrorPaquete("la ruta original no es valida")
            inventario = doc["ficheros"]
            presentes = dict(_ficheros(temporal))
            presentes.pop("video.json", None)
            if not isinstance(inventario, dict) or set(inventario) != set(presentes):
                raise ErrorPaquete("el paquete esta incompleto: no coincide su inventario")
            total_bytes = sum(os.path.getsize(ruta) for ruta in presentes.values())
            verificados = 0
            def verificar(cantidad):
                nonlocal verificados
                verificados += cantidad
                avisar(.35 + .2 * verificados / max(1, total_bytes),
                       f"Verificando integridad: {verificados / 1024 ** 2:.1f} de "
                       f"{total_bytes / 1024 ** 2:.1f} MiB")
            for nombre, ruta in presentes.items():
                ficha = inventario[nombre]
                if (ficha["bytes"] != os.path.getsize(ruta)
                        or ficha["sha256"] != _huella(ruta, avanzar=verificar)):
                    raise ErrorPaquete(f"el fichero esta incompleto o alterado: {nombre}")
            carpeta = os.path.join(temporal, "proyecto")
            config = leer_json(os.path.join(carpeta, "proyecto.json"), estricto=True)
            if not isinstance(config, dict) or not str(config.get("nombre") or "").strip():
                raise ErrorPaquete("falta la configuracion del video")
            if config.get("taller_de_preset"):
                raise ErrorPaquete("usa Importar estilo para trasladar un taller")
            avisar(.55, "Comprobando las versiones y sus firmas originales")
            estado = comun._comprobar_manifiestos(carpeta)
            antes = mudanza._calculadas(estado)
            pid = "video_importado_" + uuid.uuid4().hex
            final = os.path.abspath(os.path.join(raiz_proyectos, pid))
            reglas = [(original, final)]
            externos = doc.get("externos", {})
            if not isinstance(externos, dict):
                raise ErrorPaquete("los adjuntos no son validos")
            avisar(.6, "Preparando las referencias y los adjuntos")
            for fuente, relativo in externos.items():
                if (not comun._absoluta(fuente) or not isinstance(relativo, str)
                        or not relativo.startswith("extras/") or len(relativo.split("/")) != 2):
                    raise ErrorPaquete("referencia adjunta no valida")
                adjunto = ruta_contenida(temporal, *relativo.split("/"))
                if not os.path.isfile(adjunto):
                    raise ErrorPaquete("falta un adjunto del video")
                destino = os.path.join(final, "_adjuntos_importados", os.path.basename(adjunto))
                reglas.insert(0, (fuente, destino))
                local = os.path.join(carpeta, "_adjuntos_importados", os.path.basename(adjunto))
                os.makedirs(os.path.dirname(local), exist_ok=True)
                shutil.copyfile(adjunto, local)
            documentos = list(mudanza.ficheros_json(carpeta))
            for indice, (ruta, tipo) in enumerate(documentos):
                avisar(.6 + .28 * (indice + 1) / max(1, len(documentos)),
                       f"Adaptando rutas: {indice + 1} de {len(documentos)} archivos")
                mudanza.mudar_fichero(ruta, tipo, reglas, True)
                if tipo == "json":
                    for valor in comun._cadenas(leer_json(ruta, estricto=True)):
                        if not comun._absoluta(valor):
                            continue
                        if not comun._contenido(valor, [final]):
                            raise ErrorPaquete("el video contiene referencias fuera del paquete")
            # Los metadatos conservan tambien rutas diagnosticas a trabajo/
            # ya recogido (audio_meta.pista, referencias usadas al dibujar).
            # No son archivos pendientes: se comprueban las salidas declaradas
            # y los params necesarios, no cada cadena del registro historico.
            avisar(.88, "Comprobando el audio, las imágenes y las referencias del video")
            trasladado = comun._comprobar_manifiestos(carpeta)
            def resolver(valor):
                return mudanza.mudar_cadena(valor, [(final, carpeta)])[0]
            _comprobar_salidas(trasladado, final)
            for datos in trasladado._doc["pasos"].values():
                params = [datos.get("params")]
                params.extend(v.get("params") for v in datos.get("versiones") or [])
                for valor in comun._cadenas(params):
                    if comun._absoluta(valor) and not os.path.exists(resolver(valor)):
                        raise ErrorPaquete(f"falta una referencia del video: {valor}")
            proyecto = Proyecto(carpeta)
            proyecto.id = pid
            # El id del preset pertenece al servidor de origen; los params y las
            # referencias del estilo ya viajan con el propio video.
            proyecto.config.pop("estilo_light", None)
            proyecto.config["video_light"] = True
            proyecto.guardar_config()
            avisar(.94, "Adaptando las firmas y el historial de versiones")
            mudanza.resellar(carpeta, antes, True, [])
            trasladado = comun._comprobar_manifiestos(carpeta)
            for paso, datos in trasladado._doc["pasos"].items():
                if (datos.get("marca") or {}).get("estado") == "ejecutando":
                    trasladado.limpiar_marca(paso)
            # Ultimo punto cancelable ANTES de publicar. El gestor marca el
            # 100 % al recibir el proyecto, sin dejar copias publicadas a medias.
            avisar(.99, "Finalizando la importación del video")
            os.replace(carpeta, final)
            return Proyecto(final)
        except (KeyError, TypeError, ValueError, OSError, RuntimeError) as fallo:
            if isinstance(fallo, ErrorPaquete):
                raise
            raise ErrorPaquete(f"no se ha podido importar el video: {fallo}") from fallo
