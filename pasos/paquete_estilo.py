"""Traslado de estilos con sus ficheros y taller, sin llamadas a proveedores.

El ZIP conserva las rutas originales hasta importar: asi podemos comparar las
firmas antes y despues y conservar las obsolescencias intencionadas. Se usa el
mismo sellado selectivo que la herramienta de mudanza, tambien en el historico.
"""
import copy
import json
import ntpath
import os
import shutil
import stat
import tempfile
import uuid
import zipfile

from nucleo.proyecto import (Proyecto, ahora, escribir_json, leer_json, lock_de,
                            ruta_contenida)
from nucleo.estado import Estado
from herramientas import mudar_proyecto as mudanza

FORMATO = "as-video-studio/estilo"
VERSION = 1
MAX_BYTES = 1024 * 1024 * 1024
MAX_FICHEROS = 20000
CONFIG_TALLER = "taller_de_preset"


class ErrorPaquete(ValueError):
    """Paquete incompleto o incompatible, con un mensaje para la pantalla."""


def _cadenas(dato):
    if isinstance(dato, dict):
        for valor in dato.values():
            yield from _cadenas(valor)
    elif isinstance(dato, list):
        for valor in dato:
            yield from _cadenas(valor)
    elif isinstance(dato, str):
        yield dato


def _absoluta(valor):
    return os.path.isabs(valor) or ntpath.isabs(valor)


def _bajo(ruta, raiz):
    ruta = ruta.replace("\\", "/").lower()
    raiz = raiz.replace("\\", "/").rstrip("/").lower()
    return ruta == raiz or ruta.startswith(raiz + "/")


def _contenido(ruta, raices):
    """Comprueba rutas del destino tambien ante '..' y enlaces del disco."""
    if not isinstance(ruta, str) or not os.path.isabs(ruta):
        return False
    for raiz in raices:
        try:
            ruta_contenida(raiz, ruta)
            return True
        except ValueError:
            pass
    return False


def _copiar_arbol(origen, destino):
    if not os.path.isdir(origen):
        return
    for base, dirs, nombres in os.walk(origen):
        for nombre in dirs + nombres:
            if os.path.islink(os.path.join(base, nombre)):
                raise ErrorPaquete("el estilo contiene enlaces simbolicos; "
                                   "copia sus ficheros antes de exportar")
        for nombre in nombres:
            fuente = os.path.join(base, nombre)
            final = os.path.join(destino, os.path.relpath(fuente, origen))
            os.makedirs(os.path.dirname(final), exist_ok=True)
            shutil.copyfile(fuente, final)


def _comprobar_manifiestos(carpeta):
    documento = leer_json(os.path.join(carpeta, "estado.json"), estricto=True)
    if not isinstance(documento, dict) or not isinstance(documento.get("pasos"), dict):
        raise ErrorPaquete("falta el estado valido del taller")
    estado = Estado(Proyecto(carpeta))
    for paso, datos in estado._doc["pasos"].items():
        for version in datos.get("versiones") or []:
            estado.manifiesto_version(paso, version)
    return estado


def _comprobar_salidas(estado):
    for paso, datos in estado._doc["pasos"].items():
        salidas = [datos.get("salidas"), datos.get("unidades")]
        for version in datos.get("versiones") or []:
            salidas.extend([version.get("salidas"),
                            estado.manifiesto_version(paso, version)])
        for valor in _cadenas(salidas):
            if _absoluta(valor) and not os.path.exists(valor):
                raise ErrorPaquete(f"falta una salida del taller ({paso}): {valor}")


def _necesarios(ficha):
    datos = ficha.get("datos") or {}
    yield from (datos.get("estilo") or {}).get("referencias") or []
    for ruta in (datos.get("origen") or {}).get("estilo_imagenes") or []:
        if isinstance(ruta, str) and _absoluta(ruta):
            yield ruta
    if ficha.get("miniatura"):
        yield ficha["miniatura"]


def exportar(presets, pid, taller, destino):
    """Escribe un ZIP completo. `taller` es su carpeta o None si no lo tiene."""
    with lock_de(presets.FICHERO):
        ficha = presets.leer(pid)
        if ficha.get("tipo") != "canal":
            raise ErrorPaquete("solo se pueden exportar estilos de canal")
        banco = os.path.abspath(presets.carpeta_de(pid))
        with tempfile.TemporaryDirectory(prefix="estilo_exportar_") as temporal:
            raices = {"banco": banco}
            _copiar_arbol(banco, os.path.join(temporal, "banco"))
            if taller:
                raices["taller"] = os.path.abspath(taller)
                with lock_de(os.path.join(taller, "estado.json")):
                    _copiar_arbol(taller, os.path.join(temporal, "taller"))
                _comprobar_salidas(_comprobar_manifiestos(os.path.join(temporal, "taller")))

            for ruta in _necesarios(ficha):
                if not isinstance(ruta, str) or not os.path.isfile(ruta):
                    raise ErrorPaquete(f"falta un fichero del estilo: {ruta}")
            for nombre in ((ficha.get("datos") or {}).get("origen") or {}).get("muestras") or []:
                if not os.path.isfile(ruta_contenida(banco, nombre)):
                    raise ErrorPaquete(f"falta la muestra {nombre}")

            # Las entradas antiguas pueden seguir en el buzon de imagenes o en
            # el banco global de moodboards. Viajan tambien, sin copiar bancos
            # ajenos enteros ni depender de ellos en el servidor de destino.
            documentos = [ficha]
            for ruta, tipo in mudanza.ficheros_json(temporal):
                if tipo == "json":
                    documentos.append(leer_json(ruta, estricto=True))
            externos = {}
            for doc in documentos:
                for valor in _cadenas(doc):
                    if not _absoluta(valor) or any(_bajo(valor, r) for r in raices.values()):
                        continue
                    if valor in externos:
                        continue
                    if not os.path.isfile(valor):
                        raise ErrorPaquete(f"no se puede trasladar esta referencia: {valor}")
                    relativo = "extras/" + uuid.uuid4().hex + os.path.splitext(valor)[1]
                    final = os.path.join(temporal, *relativo.split("/"))
                    os.makedirs(os.path.dirname(final), exist_ok=True)
                    shutil.copyfile(valor, final)
                    externos[valor] = relativo
            escribir_json(os.path.join(temporal, "estilo.json"), {
                "formato": FORMATO, "version": VERSION, "preset": ficha,
                "raices": raices, "externos": externos,
            })
            total = cantidad = 0
            with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as salida:
                for base, _, nombres in os.walk(temporal):
                    for nombre in nombres:
                        ruta = os.path.join(base, nombre)
                        total += os.path.getsize(ruta)
                        cantidad += 1
                        if total > MAX_BYTES or cantidad > MAX_FICHEROS:
                            raise ErrorPaquete("el estilo supera el limite de 1 GB o 20000 ficheros")
                        salida.write(ruta, os.path.relpath(ruta, temporal).replace("\\", "/"))


def _extraer(archivo, carpeta):
    try:
        with zipfile.ZipFile(archivo) as paquete:
            entradas = paquete.infolist()
            if len(entradas) > MAX_FICHEROS or sum(e.file_size for e in entradas) > MAX_BYTES:
                raise ErrorPaquete("el ZIP supera el limite de 1 GB o 20000 ficheros")
            vistos = set()
            for entrada in entradas:
                nombre = entrada.filename
                partes = nombre.rstrip("/").split("/")
                if (not nombre or "\\" in nombre or ":" in nombre
                        or any(p in ("", ".", "..") for p in partes)
                        or partes[0] not in ("estilo.json", "banco", "taller", "extras")
                        or stat.S_ISLNK(entrada.external_attr >> 16)
                        or nombre.lower() in vistos):
                    raise ErrorPaquete("el ZIP contiene una ruta no valida")
                vistos.add(nombre.lower())
                destino = ruta_contenida(carpeta, *partes)
                if entrada.is_dir():
                    os.makedirs(destino, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with paquete.open(entrada) as fuente, open(destino, "wb") as salida:
                    shutil.copyfileobj(fuente, salida)
    except (zipfile.BadZipFile, RuntimeError, EOFError) as fallo:
        raise ErrorPaquete("el archivo no es un ZIP de estilo valido") from fallo


def importar(presets, archivo, raiz_proyectos):
    """Publica una copia nueva solo despues de validar y trasladar sus datos."""
    banco_final = taller_final = None
    with tempfile.TemporaryDirectory(prefix="estilo_importar_") as temporal:
        _extraer(archivo, temporal)
        try:
            doc = leer_json(os.path.join(temporal, "estilo.json"), estricto=True)
            if not isinstance(doc, dict) or doc.get("formato") != FORMATO or doc.get("version") != VERSION:
                raise ErrorPaquete("este ZIP no es un estilo exportado compatible")
            ficha = copy.deepcopy(doc["preset"])
            if not isinstance(ficha, dict) or not isinstance(ficha.get("datos"), dict):
                raise ErrorPaquete("la ficha del estilo no es valida")
            if ficha.get("tipo") != "canal" or not str(ficha.get("nombre") or "").strip():
                raise ErrorPaquete("el paquete no contiene un estilo con nombre")
            presets._limpiar_datos("canal", ficha["datos"])
            raices = doc["raices"]
            if not isinstance(raices, dict) or not isinstance(doc.get("externos", {}), dict):
                raise ErrorPaquete("las referencias del paquete no son validas")
            if set(raices) - {"banco", "taller"} or not raices.get("banco"):
                raise ErrorPaquete("las carpetas del paquete no son validas")
            for raiz in raices.values():
                if not isinstance(raiz, str) or not _absoluta(raiz) or len(raiz.rstrip("/\\")) < 4:
                    raise ErrorPaquete("las rutas originales del paquete no son validas")
            tiene_taller = bool((ficha["datos"].get("origen") or {}).get("taller"))
            if tiene_taller != ("taller" in raices):
                raise ErrorPaquete("falta el taller declarado por el estilo")
            antes = None
            if tiene_taller:
                ruta_taller = os.path.join(temporal, "taller")
                if not os.path.isfile(os.path.join(ruta_taller, "proyecto.json")):
                    raise ErrorPaquete("falta la configuracion del taller")
                antes = mudanza._calculadas(_comprobar_manifiestos(ruta_taller))

            with lock_de(presets.FICHERO):
                guardado = presets._leer()
                pid = "pr" + uuid.uuid4().hex
                banco_final = presets.carpeta_de(pid)
                tid = "taller_importado_" + uuid.uuid4().hex
                taller_final = os.path.join(raiz_proyectos, tid) if tiene_taller else None
                destinos = {"banco": banco_final}
                if tiene_taller:
                    destinos["taller"] = taller_final
                reglas = [(r, destinos[k]) for k, r in raices.items()]
                for original, relativo in doc.get("externos", {}).items():
                    if (not _absoluta(original) or not isinstance(relativo, str)
                            or not relativo.startswith("extras/")
                            or len(relativo.split("/")) != 2):
                        raise ErrorPaquete("referencia adjunta no valida")
                    fuente = ruta_contenida(temporal, *relativo.split("/"))
                    if not os.path.isfile(fuente):
                        raise ErrorPaquete("falta un fichero adjunto")
                    destino = os.path.join(banco_final, "_adjuntos", os.path.basename(fuente))
                    reglas.insert(0, (original, destino))
                for ruta, tipo in list(mudanza.ficheros_json(temporal)):
                    if os.path.basename(ruta) != "estilo.json":
                        mudanza.mudar_fichero(ruta, tipo, reglas, True)
                        if tipo == "json":
                            for valor in _cadenas(leer_json(ruta, estricto=True)):
                                if _absoluta(valor) and not _contenido(valor, destinos.values()):
                                    raise ErrorPaquete("el taller contiene referencias fuera del paquete")
                ficha, _ = mudanza.mudar_dato(ficha, reglas)
                # Nunca se permite que un paquete utilice rutas locales del
                # destino que no pertenezcan a sus propias carpetas nuevas.
                for valor in _cadenas(ficha):
                    if _absoluta(valor) and not _contenido(valor, destinos.values()):
                        raise ErrorPaquete("el estilo contiene referencias fuera del paquete")
                os.makedirs(banco_final)
                _copiar_arbol(os.path.join(temporal, "banco"), banco_final)
                for original, relativo in doc.get("externos", {}).items():
                    destino = mudanza.mudar_cadena(original, reglas)[0]
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    shutil.copyfile(ruta_contenida(temporal, *relativo.split("/")), destino)
                if tiene_taller:
                    _copiar_arbol(ruta_taller, taller_final)
                    proyecto = Proyecto(taller_final)
                    proyecto.id = tid
                    proyecto.config[CONFIG_TALLER] = True
                    proyecto.guardar_config()
                    mudanza.resellar(taller_final, antes, True, [])
                    _comprobar_salidas(_comprobar_manifiestos(taller_final))
                    ficha["datos"].setdefault("origen", {})["taller"] = tid
                for ruta in _necesarios(ficha):
                    if not _contenido(ruta, destinos.values()) or not os.path.isfile(ruta):
                        raise ErrorPaquete("el paquete esta incompleto: falta una referencia del estilo")
                for nombre in (ficha["datos"].get("origen") or {}).get("muestras") or []:
                    if not os.path.isfile(ruta_contenida(banco_final, nombre)):
                        raise ErrorPaquete("el paquete esta incompleto: falta una muestra")
                ficha.update(id=pid, fecha=ahora(), modificado=ahora())
                ficha.pop("apartado", None)
                guardado["presets"].append(ficha)
                presets._escribir(guardado)
                banco_final = taller_final = None  # publicado: ya no se limpia
                return presets.publicar(ficha)
        except (KeyError, TypeError, ValueError, OSError) as fallo:
            if isinstance(fallo, ErrorPaquete):
                raise
            raise ErrorPaquete(f"no se ha podido importar el estilo: {fallo}") from fallo
        finally:
            for carpeta in (banco_final, taller_final):
                if carpeta:
                    shutil.rmtree(carpeta, ignore_errors=True)
