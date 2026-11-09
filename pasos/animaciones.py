"""Las animaciones de motion graphics: el catalogo, quien las reparte y como se pintan.

DE DONDE SALEN
--------------
De la guia de tecnicas de animacion documental (Kinetic Typography, UI Motion,
Editorial, Infografias...). Cada ficha del CATALOGO es una de esas tecnicas
reducida a lo que cabe en una escena de ESTE motor: un plano con su imagen o su
clip, su narracion con los tiempos de cada palabra, y nada mas. Las que
necesitan varios recursos a la vez (collage, pantalla dividida, reorganizacion)
o un avatar no estan: no hay dónde ponerlas sin cambiar el modelo del plan.

POR QUE SON UNA CAPA SVG Y NO UNA TRANSICION
--------------------------------------------
Las transiciones (`transiciones.py`) necesitan DOS fotogramas y por eso son una
segunda pasada. Una animacion de este modulo necesita UNO: se dibuja ENCIMA del
plano, como el subtitulo, con SMIL, y la pagina de render la congela y la mueve
con `setCurrentTime` igual que la capa quieta. Mismo reloj, mismo fotograma:
previsualizacion y exportacion no pueden diferir.

QUE ANIMACION LE TOCA A CADA ESCENA
-----------------------------------
No se alternan a ciegas. Cada tecnica pide una SENAL en lo que se dice:

    cifra     una cantidad o un porcentaje    -> infografia-cifra
    fecha     un ano o una fecha              -> editorial-fecha
    contraste dos cosas que se oponen         -> comparacion-tarjetas
    termino   un nombre propio                -> ficha-ui, ficha-cristal,
                                                 etiqueta-escrita, collage-titulo
    frase     una frase corta y redonda       -> tipografia-cinetica

Cuando una senal tiene varias animaciones, se rota entre las elegidas con una
semilla (como las transiciones), sin repetir la del plano animado anterior.

Dos de ellas -- collage-titulo y comparacion-tarjetas -- ensenan dos imagenes
exclusivas de su escena, asi que solo se reparten si ambas existen (ver
`repartir`, parametro `imagenes`). Y tres atenuan o desenfocan el plano de
fondo: eso no lo puede hacer una capa SVG, asi que viaja aparte como `fondo` y
lo aplica la pagina de render con la misma funcion de t (`JS_FONDO`).

La senal se saca de la NARRACION con reglas deterministas -- sin modelo y por
tanto sin coste --, y solo cuentan las tecnicas que estan elegidas. Una escena
sin senal para ninguna de las elegidas se queda como estaba: la propia guia
pide movimiento sobrio, y una animacion en cada plano es un salvapantallas,
igual que una transicion en cada corte (ver `transiciones.resolver`).

LO QUE NO HACE
--------------
No genera imagenes nuevas ni cambia la voz o los subtitulos. La seleccion de
videos nuevos es un parametro del GUION: Claude elige un fragmento literal
para cada bloque animado. Cambiarla deja obsoletas voz e imagenes. Los guiones
antiguos sin fragmentos elegidos siguen usando las senales deterministas; sin
animaciones pedidas no se pinta nada.
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import medios  # noqa: E402
import imagenes_animacion  # noqa: E402
import subtitulos  # noqa: E402
import tipografia  # noqa: E402
import cartelas  # noqa: E402

# ===========================================================================
# EL CATALOGO
#
#   tecnica   como se llama en la guia, para poder buscarla.
#   senal     que tiene que haber en la narracion para que encaje.
#   defecto   si entra sin que nadie toque nada. Ninguna: es una decision de
#             estilo y vale mas que se tome mirando las tarjetas.
# ===========================================================================

CATALOGO = {
    "infografia-cifra": {
        "nombre": "Cifra animada",
        "descripcion": "Un contador sube hasta el dato y, si es un porcentaje, una barra se rellena a la vez.",
        "tecnica": "Animated Infographics", "senal": "cifra", "defecto": False,
    },
    "editorial-fecha": {
        "nombre": "Banda de fecha",
        "descripcion": "Una banda de color se extiende de izquierda a derecha y deja el año encima, con su contexto debajo.",
        "tecnica": "Editorial Motion Design", "senal": "fecha", "defecto": False,
    },
    "ficha-ui": {
        "nombre": "Ficha de concepto",
        "descripcion": "Una ficha se expande y revela, por este orden, la etiqueta, el nombre y la frase que lo explica.",
        "tecnica": "UI Motion Design", "senal": "termino", "defecto": False,
    },
    "tipografia-cinetica": {
        "nombre": "Tipografía cinética",
        "descripcion": "La frase se escribe palabra a palabra al ritmo de la voz y un resaltado cae sobre la palabra clave.",
        "tecnica": "Kinetic Typography", "senal": "frase", "defecto": False,
    },
    "ficha-cristal": {
        "nombre": "Ficha de cristal",
        "descripcion": "Una barra se ensancha hasta una tarjeta de cristal oscuro; salen la etiqueta, el título y la explicación y un brillo la barre.",
        "tecnica": "UI Motion Design", "senal": "termino", "defecto": False, "tiempo": 2.8,
    },
    "etiqueta-escrita": {
        "nombre": "Etiqueta escrita",
        "descripcion": "Una caja blanca escribe el nombre letra a letra mientras el fondo se desenfoca.",
        "tecnica": "Kinetic Typography", "senal": "termino", "defecto": False, "tiempo": 2.6,
    },
    "collage-titulo": {
        "nombre": "Collage con título",
        "descripcion": "El fondo se oscurece, entran dos fotos exclusivas de esta escena una tras otra y el título se escribe encima.",
        "tecnica": "Collage Animation", "senal": "termino", "defecto": False, "tiempo": 3.6,
        "requiere_imagenes": True,
    },
    "comparacion-tarjetas": {
        "nombre": "Comparación de tarjetas",
        "descripcion": "Una tarjeta sube desde abajo y otra cae desde arriba, cada una con su etiqueta y una imagen exclusiva de esta escena.",
        "tecnica": "Split-Screen Animation", "senal": "contraste", "defecto": False, "tiempo": 3.2,
        "requiere_imagenes": True,
    },
}

#: Orden en que se mira la senal de una escena cuando hay varias: lo mas
#: concreto primero. Una cifra manda sobre un nombre propio, que aparece en
#: casi cualquier frase.
PRIORIDAD = ("cifra", "fecha", "contraste", "termino", "frase")

#: Una escena mas corta no tiene tiempo de entrar, leerse y salir.
DURACION_MINIMA = 2.4

#: Cuantos planos SIN animacion tienen que separar a dos con animacion.
HUECO_ENTRE_ANIMACIONES = 1

#: Lo que tiene que quedar de plano desde que se dice la senal hasta el final
#: para que la animacion entre y se lea. Una cifra dicha en el ultimo segundo se
#: queda sin animar: empezaria y el corte se la llevaria a medias.
TIEMPO_PARA_LEERSE = 1.2

#: Cuanto se queda la animacion visible desde que entra, como mucho.
PERMANENCIA_MAXIMA = 4.2

FUENTE_SVG = 'Verdana, "DejaVu Sans", sans-serif'
FUENTE_MEDIDA = "verdana"

# Contrato del editor: solo contenido visible, nunca SVG ni tiempos arbitrarios.
CAMPOS = {
    "infografia-cifra": [("texto", "Cifra"), ("etiqueta", "Etiqueta")],
    "editorial-fecha": [("texto", "Fecha"), ("contexto", "Contexto")],
    "ficha-ui": [("etiqueta", "Etiqueta"), ("nombre", "Título"), ("definicion", "Explicación")],
    "ficha-cristal": [("etiqueta", "Etiqueta"), ("nombre", "Título"), ("definicion", "Explicación")],
    "etiqueta-escrita": [("nombre", "Texto")],
    "collage-titulo": [("nombre", "Título")],
    "comparacion-tarjetas": [("izquierda", "Etiqueta izquierda"), ("derecha", "Etiqueta derecha")],
    "tipografia-cinetica": [("texto", "Frase"), ("subrayado", "Subrayado")],
}

# Las cartelas son elegibles manualmente sin entrar en el plan del guion.
CATALOGO_EDITOR = dict(CATALOGO, **{
    f"cartela-{pid}": ficha for pid, ficha in cartelas.PLANTILLAS.items()})
NOMBRES_CARTELA = {"cifra": "Cifra", "label": "Etiqueta", "nota": "Nota",
                   "icono": "Icono (opcional)", "texto": "Texto", "quien": "Autor",
                   "titulo": "Título", "lineas": "Líneas (una por renglón)",
                   "izq_valor": "Valor izquierdo", "izq_label": "Etiqueta izquierda",
                   "der_valor": "Valor derecho", "der_label": "Etiqueta derecha",
                   "termino": "Término", "numero": "Número", "antetitulo": "Antetítulo",
                   "hitos": "Hitos (uno por renglón)"}
CAMPOS_EDITOR = dict(CAMPOS, **{
    f"cartela-{pid}": [(k, NOMBRES_CARTELA[k]) for k in ficha["campos"]]
    for pid, ficha in cartelas.PLANTILLAS.items()})


def es_cartela_editor(aid):
    return str(aid).startswith("cartela-") and aid in CATALOGO_EDITOR


def datos_cartela(aid, contenido):
    ficha = cartelas.PLANTILLAS[aid.removeprefix("cartela-")]
    lista = (ficha.get("lista") or [None])[0]
    return {k: [v.strip() for v in contenido[k].splitlines() if v.strip()]
            if k == lista else contenido[k] for k in ficha["campos"]}


def ancla_de(escena):
    return " ".join(str(escena.get("narracion") or "").split())


def subrayadas_de(datos):
    """Coincidencias de palabras completas; sin campo conserva la elección antigua."""
    palabras = datos.get("palabras") or []
    if not palabras:
        return set()
    if "subrayado" not in datos:
        return {max(range(len(palabras)), key=lambda k: (len(_limpio(palabras[k])), k))}
    buscadas = set(re.findall(r"\w+", str(datos["subrayado"]).casefold()))
    return {i for i, palabra in enumerate(palabras)
            if buscadas.intersection(re.findall(r"\w+", str(palabra).casefold()))}


def contenido_de(aid, datos):
    if es_cartela_editor(aid):
        return {k: "\n".join(datos.get(k) or []) if isinstance(datos.get(k), list)
                else str(datos.get(k) or "") for k, _ in CAMPOS_EDITOR[aid]}
    if aid == "tipografia-cinetica":
        palabras = datos.get("palabras") or []
        subrayado = (str(datos["subrayado"]) if "subrayado" in datos else
                     " ".join(_limpio(palabras[i]) for i in sorted(subrayadas_de(datos))))
        return {"texto": " ".join(palabras), "subrayado": subrayado}
    return {k: str(datos.get(k, "CONCEPTO" if k == "etiqueta" and aid.startswith("ficha-") else ""))
            for k, _ in CAMPOS[aid]}


def validar_edicion(edicion, escena):
    if (not isinstance(edicion, dict) or not isinstance(edicion.get("id"), str)
            or edicion["id"] not in {*CATALOGO_EDITOR, "sin-animacion"}):
        raise ValueError("elige una animación del catálogo")
    if edicion.get("ancla") != ancla_de(escena):
        raise ValueError("la escena ha cambiado; vuelve a abrir su animación")
    aid, contenido = edicion["id"], edicion.get("contenido")
    if aid == "sin-animacion":
        if contenido != {}:
            raise ValueError("Sin animación no admite campos de contenido")
        return {"id": aid, "ancla": ancla_de(escena), "contenido": {}}
    campos = {k for k, _ in CAMPOS_EDITOR[aid]}
    # Las ediciones anteriores solo guardaban la frase. Leerlas mantiene el
    # resaltado automático sin escribir defaults ni cambiar sus firmas.
    if aid == "tipografia-cinetica" and isinstance(contenido, dict) and "subrayado" not in contenido:
        campos.remove("subrayado")
    if not isinstance(contenido, dict) or set(contenido) != campos:
        raise ValueError("faltan campos de la animación o hay campos desconocidos")
    limpio = {}
    for k, nombre in CAMPOS_EDITOR[aid]:
        if k not in campos:
            continue
        valor = contenido[k]
        if not isinstance(valor, str) or len(valor) > 500:
            raise ValueError(f"{nombre}: utiliza como máximo 500 caracteres")
        limpio[k] = ("\n".join(" ".join(v.split()) for v in valor.splitlines())
                     if es_cartela_editor(aid) else " ".join(valor.split()))
    if es_cartela_editor(aid):
        ficha = CATALOGO_EDITOR[aid]
        datos = datos_cartela(aid, limpio)
        lista = ficha.get("lista")
        for k, (obligatorio, tope) in ficha["campos"].items():
            valores = datos[k] if lista and k == lista[0] else [datos[k]]
            if obligatorio and (not valores or any(not v for v in valores)):
                raise ValueError(f"{NOMBRES_CARTELA[k]}: escribe el contenido obligatorio")
            if any(len(v) > tope for v in valores):
                raise ValueError(f"{NOMBRES_CARTELA[k]}: máximo {tope} caracteres por renglón")
        if lista and not lista[1] <= len(datos[lista[0]]) <= lista[2]:
            raise ValueError(f"escribe entre {lista[1]} y {lista[2]} renglones")
        if datos.get("icono") and datos["icono"] not in cartelas.ICONOS:
            raise ValueError("elige un icono conocido o deja el campo vacío")
    principal = CAMPOS_EDITOR[aid][1][0] if aid.startswith("ficha-") else CAMPOS_EDITOR[aid][0][0]
    if not es_cartela_editor(aid) and not limpio[principal]:
        raise ValueError("el texto principal no puede estar vacío")
    if aid == "comparacion-tarjetas" and not limpio["derecha"]:
        raise ValueError("escribe las dos etiquetas")
    if aid == "infografia-cifra":
        partes = _partes_cifra(limpio["texto"])
        if not partes or not math.isfinite(partes[1]):
            raise ValueError("escribe una cifra válida, por ejemplo 45% o 1200")
    resultado = {"id": aid, "ancla": ancla_de(escena), "contenido": limpio}
    if "duracion" in edicion:
        valor = edicion["duracion"]
        if (isinstance(valor, bool) or not isinstance(valor, (int, float))
                or not math.isfinite(valor) or not 0.1 <= valor <= _duracion(escena)):
            raise ValueError("la duración debe estar entre 0,1 segundos y la duración de la escena")
        resultado["duracion"] = float(valor)
    if "posiciones" in edicion:
        posiciones = edicion["posiciones"]
        if not isinstance(posiciones, dict) or len(posiciones) > 500:
            raise ValueError("posiciones de elementos no válidas")
        resultado["posiciones"] = {}
        for clave, punto in posiciones.items():
            if (not re.fullmatch(r"e\d{1,4}|conjunto", str(clave)) or not isinstance(punto, dict)
                    or set(punto) != {"x", "y"} or any(
                        isinstance(v, bool) or not isinstance(v, (int, float))
                        or not math.isfinite(v) or abs(v) > 2 for v in punto.values())):
                raise ValueError("posición de elemento no válida")
            resultado["posiciones"][clave] = dict(punto)
    if "imagenes" in edicion:
        if not CATALOGO_EDITOR[aid].get("requiere_imagenes"):
            raise ValueError("esta animación no utiliza tarjetas con imágenes")
        resultado["imagenes"] = imagenes_animacion.validar_referencias(edicion["imagenes"])
    return resultado


def opciones_de(escena, actual=None, idioma=None):
    vistas = senales(escena, idioma)
    frase = " ".join(str(escena.get("narracion") or "Texto de la escena").split()[:8])
    opciones = [{"id": "sin-animacion", "nombre": "Sin animación",
                 "descripcion": "Quita la animación de esta escena al guardar.",
                 "campos": [], "contenido": {}}]
    for aid, ficha in CATALOGO.items():
        datos = vistas.get(ficha["senal"]) or {}
        respaldo = {"texto": "45%" if ficha["senal"] == "cifra" else "2026",
                    "nombre": frase, "definicion": ancla_de(escena), "etiqueta": "CONCEPTO",
                    "contexto": ancla_de(escena), "izquierda": "Antes", "derecha": "Después",
                    "palabras": frase.split()}
        contenido = contenido_de(aid, dict(respaldo, **datos))
        if actual and actual["id"] == aid:
            contenido = actual["contenido"]
        tarjetas = ([{"id": "propia", "nombre": "Imagen izquierda",
                      "antes": "izquierda" if aid == "comparacion-tarjetas" else "nombre"},
                     {"id": "otra", "nombre": "Imagen derecha",
                      "antes": "derecha" if aid == "comparacion-tarjetas" else "nombre"}]
                    if ficha.get("requiere_imagenes") else [])
        opciones.append({"id": aid, "nombre": ficha["nombre"], "descripcion": ficha["descripcion"],
                         "campos": [{"id": k, "nombre": n} for k, n in CAMPOS[aid]],
                          "contenido": contenido, "imagenes": tarjetas})
    for pid, ficha in cartelas.PLANTILLAS.items():
        aid = f"cartela-{pid}"
        contenido = contenido_de(aid, ficha["ejemplo"])
        if actual and actual["id"] == aid:
            contenido = actual["contenido"]
        lista = (ficha.get("lista") or [None])[0]
        opciones.append({"id": aid, "nombre": ficha["nombre"], "descripcion": ficha["descripcion"],
                         "contenido": contenido,
                         "campos": [{"id": k, "nombre": n,
                                     "maxlength": 500 if k == lista else ficha["campos"][k][1],
                                     "ayuda": ("Una entrada por renglón; entre 2 y 4 entradas." if k == lista
                                               else "Iconos: " + ", ".join(sorted(cartelas.ICONOS)) if k == "icono" else "")}
                                    for k, n in CAMPOS_EDITOR[aid]]})
    return opciones


def ediciones_de(params):
    """Las asignaciones pertenecen a su unidad, nunca a la firma global."""
    return {uid.split(":", 1)[1]: unidad["animacion"]
            for uid, unidad in ((params or {}).get("unidades") or {}).items()
            if uid.startswith("escena:") and isinstance(unidad, dict) and unidad.get("animacion")}


def tarjetas_de(escenas, sid, imagenes):
    return {"propia": (imagenes or {}).get(sid),
            "otra": (imagenes or {}).get(sid + "__tarjeta")}


def urls_imagenes(proyecto, params, escenas, convertir):
    """Resuelve solo referencias de las escenas cuyo texto sigue vigente."""
    anclas = {e.get("id"): ancla_de(e) for e in escenas or []}
    urls = {}
    for sid, edicion in ediciones_de(params).items():
        if edicion.get("ancla") != anclas.get(sid):
            continue
        for referencia in imagenes_animacion.validar_referencias(edicion.get("imagenes") or {}).values():
            urls[referencia] = convertir(imagenes_animacion.ruta_de(proyecto, referencia))
    return urls


def aplicar_ediciones(reparto, escenas, ediciones, imagenes, imagenes_usuario=None, estricto=True):
    salida = dict(reparto)
    lista = list(escenas or [])
    for i, escena in enumerate(lista):
        sid = escena.get("id")
        edicion = (ediciones or {}).get(sid)
        if not edicion or edicion.get("ancla") != ancla_de(escena):
            continue
        edicion = validar_edicion(edicion, escena)
        aid = edicion["id"]
        if aid == "sin-animacion":
            salida.pop(sid, None)
            continue
        if es_cartela_editor(aid):
            salida[sid] = dict(edicion, animacion=aid, datos=datos_cartela(aid, edicion["contenido"]))
            continue
        datos = dict(edicion["contenido"], desde=0.0, hasta=min(1.0, _duracion(escena)))
        if aid == "infografia-cifra":
            datos["porcentaje"] = "%" in datos["texto"]
        if aid == "tipografia-cinetica":
            datos["palabras"] = datos.pop("texto").split()
            paso = max(0.01, min(0.42, (_duracion(escena) - 0.8) / len(datos["palabras"])))
            datos["tiempos"] = [[k * paso, (k + 1) * paso] for k in range(len(datos["palabras"]))]
        if CATALOGO[aid].get("requiere_imagenes"):
            tarjetas = tarjetas_de(lista, sid, imagenes)
            referencias = edicion.get("imagenes") or {}
            for lado, referencia in referencias.items():
                tarjetas[lado] = (imagenes_usuario or {}).get(referencia)
            if not all(tarjetas.values()):
                if not estricto:
                    salida.pop(sid, None)
                    continue
                raise ValueError("falta la segunda imagen propia de esta escena; genera sus imágenes o sube una imagen para la tarjeta")
            ficha = {"animacion": aid, "senal": CATALOGO[aid]["senal"], "datos": datos,
                     "imagenes": tarjetas, "imagenes_usuario": referencias,
                     "elementos": {"propia": sid, "otra": "imagen subida" if "otra" in referencias
                                    else sid + "__tarjeta"}}
        else:
            ficha = _ficha_de(lista, i, aid, CATALOGO[aid]["senal"], datos, imagenes or {})
        if ficha is None:
            raise ValueError("esta animación necesita dos imágenes propias de la escena")
        salida[sid] = dict(ficha, **{k: edicion[k] for k in ("posiciones", "duracion") if k in edicion})
    return salida


_MESES = ("enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|"
          "setiembre|octubre|noviembre|diciembre|january|february|march|april|"
          "may|june|july|august|september|october|november|december")
_RE_ANIO = re.compile(r"^\(?\"?'?(1[0-9]{3}|20[0-9]{2})[\"')]?[.,;:!?]*$")
_RE_NUMERO = re.compile(r"^[^\d]*(\d[\d.,]*)\s*(%?)[^\d]*$")


# ===========================================================================
# LAS SENALES
# ===========================================================================

def _limpio(palabra):
    return str(palabra).strip(" \t\"'()[]¿¡«»“”‘’.,;:!?…—–-")


def _frases(palabras):
    """Los rangos (a, b) de palabras de cada frase, partiendo por . ! ? y …"""
    rangos, inicio = [], 0
    for i, palabra in enumerate(palabras):
        if re.search(r"[.!?…]+[\"')»”]*$", str(palabra)):
            rangos.append((inicio, i + 1))
            inicio = i + 1
    if inicio < len(palabras):
        rangos.append((inicio, len(palabras)))
    return rangos


def _tiempos(marcas, a, b, t_in):
    """(desde, hasta) en el reloj del plano de las palabras a..b-1."""
    desde = float(marcas[a][0]) - t_in
    hasta = float(marcas[b - 1][1]) - t_in
    return round(max(0.0, desde), 3), round(max(desde, hasta), 3)


def _contexto(palabras, a, antes=0, despues=5, tope=7):
    """Unas pocas palabras alrededor de la senal, sin cortar la frase."""
    trozo = [str(p) for p in palabras[max(0, a - antes):a + despues]]
    trozo = trozo[:tope]
    texto = " ".join(trozo).strip()
    return texto.rstrip(",;:—–-")


def _cifra(palabras, marcas, t_in, idioma):
    """La cifra que se dice en la escena, o None. Un ano no es una cifra."""
    try:
        tramos = list(subtitulos._cifras_de(palabras, idioma))
    except Exception:                                          # noqa: BLE001
        tramos = []
    cubiertas = {i for a, b in tramos for i in range(a, b)}
    for i, palabra in enumerate(palabras):
        if i not in cubiertas and re.search(r"\d", str(palabra)):
            tramos.append((i, i + 1))
    candidatas = []
    for a, b in sorted(tramos):
        texto = subtitulos.limpiar_texto(palabras[a:b], idioma)
        sin = texto.strip(" .,;:!?¿¡\"'()")
        coincide = _RE_NUMERO.match(sin)
        if not coincide or not re.search(r"\d", sin):
            continue
        porcentaje = bool(coincide.group(2)) or any(
            "porciento" in _limpio(p).lower() or "percent" in _limpio(p).lower()
            for p in palabras[b:b + 2])
        if _RE_ANIO.match(sin) and not porcentaje:
            continue
        # «uno», «dos»... se convierten en 1 y 2: una cifra de verdad es otra cosa
        if not porcentaje and len(re.sub(r"\D", "", sin)) < 2:
            continue
        candidatas.append((a, b, sin, porcentaje))
    if not candidatas:
        return None
    # el porcentaje manda: es lo unico que se puede dibujar como barra
    candidatas.sort(key=lambda c: (not c[3], c[0]))
    a, b, texto, porcentaje = candidatas[0]
    cola = [_limpio(p) for p in palabras[b:b + 3]]
    cola = [p for p in cola if p and p.lower() not in ("por", "ciento", "percent", "%")]
    etiqueta = " ".join(cola[:3])
    if porcentaje and "%" not in texto:
        texto += "%"
    desde, hasta = _tiempos(marcas, a, b, t_in)
    return {"texto": texto, "porcentaje": porcentaje, "etiqueta": etiqueta,
            "desde": desde, "hasta": hasta}


def _fecha(palabras, marcas, t_in, idioma=None):
    # El guion se locuta con TODO en letras. Recuperar los tramos numericos con
    # la misma conversion que usan los subtitulos, conservando los indices de
    # las palabras originales para sincronizar la banda con la voz.
    tramos = list(subtitulos._cifras_de(palabras, idioma))
    cubiertas = {i for a, b in tramos for i in range(a, b)}
    tramos += [(i, i + 1) for i, p in enumerate(palabras)
               if i not in cubiertas and re.search(r"\d", str(p))]
    for a, b in sorted(tramos):
        coincide = _RE_ANIO.match(subtitulos.limpiar_texto(palabras[a:b], idioma))
        if not coincide:
            continue
        desde, hasta = _tiempos(marcas, a, b, t_in)
        # el contexto es lo que cuelga del ano: «en 1923, cuando cayó el muro»
        resto = _contexto(palabras, b, despues=6, tope=7)
        return {"texto": coincide.group(1), "contexto": resto,
                "desde": desde, "hasta": hasta}
    # Las unidades («cinco de mayo») no se convierten a cifra en los
    # subtitulos, pero aqui SI son dias cuando preceden al nombre del mes.
    dias = medios.numeros_en([medios.normalizar_texto(p) for p in palabras], idioma)
    for a, n, valor in dias:
        b = a + n
        if b + 1 >= len(palabras) or _limpio(palabras[b]).lower() != "de" or not re.fullmatch(
                _MESES, _limpio(palabras[b + 1]).lower() or "-"):
            continue
        if valor == int(valor) and 1 <= valor <= 31:
            desde, hasta = _tiempos(marcas, a, b + 2, t_in)
            return {"texto": f"{int(valor)} {_limpio(palabras[b + 1]).upper()}",
                    "contexto": _contexto(palabras, b + 2, despues=6, tope=7),
                    "desde": desde, "hasta": hasta}
    return None


def _termino(palabras, marcas, t_in):
    """Un nombre propio: palabras con mayuscula que no abren frase. -> dict | None"""
    inicios = {a for a, _ in _frases(palabras)}
    i, mejor = 0, None
    while i < len(palabras):
        pal = _limpio(palabras[i])
        if i in inicios or len(pal) < 3 or not pal[:1].isupper() or pal.isupper():
            i += 1
            continue
        j = i + 1
        while j < len(palabras) and j - i < 6:
            siguiente = _limpio(palabras[j])
            if siguiente[:1].isupper() and not _RE_ANIO.match(str(palabras[j])):
                j += 1
            elif siguiente.lower() in ("de", "del", "la", "las", "los", "of", "the") \
                    and j + 1 < len(palabras) and _limpio(palabras[j + 1])[:1].isupper():
                j += 1
            else:
                break
        nombre = " ".join(_limpio(p) for p in palabras[i:j])
        if mejor is None or len(nombre) > len(mejor[2]):
            mejor = (i, j, nombre)
        i = j
    if not mejor:
        return None
    a, b, nombre = mejor
    # la frase entera que lo contiene es su «definicion»
    for fa, fb in _frases(palabras):
        if fa <= a < fb:
            frase = [str(p) for p in palabras[fa:fb]]
            if len(frase) > 16:
                frase = frase[:16]
                frase[-1] = frase[-1].rstrip(",;:") + "…"
            desde, hasta = _tiempos(marcas, a, b, t_in)
            return {"nombre": nombre, "definicion": " ".join(frase),
                    "desde": desde, "hasta": hasta}
    return None


def _nombre_propio(palabras):
    """Nombre completo elegido por Claude, incluidos conectores como «de»."""
    conectores = {"de", "del", "la", "las", "los", "of", "the"}
    if not 1 <= len(palabras) <= 7:
        return False
    limpias = [_limpio(p) for p in palabras]
    return (limpias[0][:1].isupper() and
            all(p[:1].isupper() or p.lower() in conectores for p in limpias) and
             limpias[-1][:1].isupper())


def _concepto_elegido(palabras):
    """Un concepto breve elegido literalmente por el guionista, no por heuristica."""
    limpias = [_limpio(p) for p in palabras]
    return (1 <= len(limpias) <= 5 and
            any(len(p) >= 4 and p.lower() not in _VACIAS for p in limpias))


def _frase(palabras, marcas, t_in):
    """La primera frase corta y redonda (3 a 9 palabras). -> dict | None"""
    for a, b in _frases(palabras):
        n = b - a
        if 3 <= n <= 9:
            desde, hasta = _tiempos(marcas, a, b, t_in)
            return {"palabras": [str(p) for p in palabras[a:b]],
                    "tiempos": [_tiempos(marcas, k, k + 1, t_in) for k in range(a, b)],
                    "desde": desde, "hasta": hasta}
    return None


#: Lo que une dos cosas que se oponen. Corto a proposito: «pero» y «but» estan en
#: media frase del mundo, y una comparacion de tarjetas mal puesta es peor que
#: ninguna.
_CONECTORES = (("mientras", "que"), ("mientras",), ("frente", "a"), ("en", "cambio"),
               ("por", "el", "contrario"), ("a", "diferencia", "de"), ("versus",),
               ("vs",), ("while",), ("whereas",), ("compared", "to"), ("unlike",))
_VACIAS = frozenset("el la los las un una unos unas de del al en y o e que lo se su sus "
                    "the a an of in on and or to is are".split())


def _etiqueta(palabras, maximo=2):
    """Las primeras palabras con contenido, en mayusculas: «Las raices sanas» -> RAICES SANAS"""
    utiles = [_limpio(p) for p in palabras]
    utiles = [p for p in utiles if p and p.lower() not in _VACIAS]
    return " ".join(utiles[:maximo]).upper()


def _contraste(palabras, marcas, t_in):
    """Dos mitades de una misma frase unidas por un «mientras que», «frente a»... -> dict | None"""
    llanas = [_limpio(p).lower() for p in palabras]
    for fa, fb in _frases(palabras):
        for conector in _CONECTORES:
            n = len(conector)
            for i in range(fa + 1, fb - n):
                if tuple(llanas[i:i + n]) != conector:
                    continue
                izquierda, derecha = _etiqueta(palabras[fa:i]), _etiqueta(palabras[i + n:fb])
                if not izquierda or not derecha or izquierda == derecha:
                    continue
                desde = _tiempos(marcas, fa, fa + 1, t_in)[0]
                hasta = _tiempos(marcas, fb - 1, fb, t_in)[1]
                return {"izquierda": izquierda, "derecha": derecha,
                        "desde": desde, "hasta": hasta}
    return None


def senales(escena, idioma=None):
    """Lo que se dice en una escena y se puede dibujar. -> {senal: datos}

    Vacio si el texto y las marcas de tiempo no cuadran: sin tiempos una
    animacion saldria desplazada de la voz, que es peor que no salir.
    """
    escena = escena if isinstance(escena, dict) else {}
    palabras = str(escena.get("narracion") or "").split()
    marcas = escena.get("marcas") or []
    if not palabras or len(palabras) != len(marcas):
        return {}
    try:
        t_in = float(escena.get("t_in") or 0.0)
        salida = {}
        for clave, buscar in (("cifra", lambda: _cifra(palabras, marcas, t_in, idioma)),
                              ("fecha", lambda: _fecha(palabras, marcas, t_in, idioma)),
                              ("contraste", lambda: _contraste(palabras, marcas, t_in)),
                              ("termino", lambda: _termino(palabras, marcas, t_in)),
                              ("frase", lambda: _frase(palabras, marcas, t_in))):
            datos = buscar()
            if datos:
                salida[clave] = datos
        return salida
    except (TypeError, ValueError, IndexError):
        return {}


# ===========================================================================
# EL REPARTO
# ===========================================================================

def elegidas_de(params):
    """Las animaciones que entran en este video, en orden de catalogo."""
    pedidas = (params or {}).get("animaciones") or []
    return [a for a in CATALOGO if a in set(str(x) for x in pedidas)]


def _duracion(escena):
    try:
        return float(escena.get("t_out")) - float(escena.get("t_in"))
    except (TypeError, ValueError):
        return 0.0


def _es_cartela(escena):
    """Las cartelas ya son texto animado: encima no se pinta otra cosa."""
    return bool(escena.get("cartela")) or bool(escena.get("capitulo_svg"))


def _ficha_de(lista, indice, animacion, senal, datos, imagenes):
    """La asignacion de UN plano. None si no tiene con que hacer sus tarjetas."""
    ficha = {"animacion": animacion, "senal": senal, "datos": datos}
    if CATALOGO[animacion].get("requiere_imagenes"):
        sid = lista[indice].get("id")
        tarjetas = tarjetas_de(lista, sid, imagenes)
        if not all(tarjetas.values()):
            return None
        ficha["imagenes"] = tarjetas
        ficha["elementos"] = {"propia": sid, "otra": sid + "__tarjeta"}
    return ficha


def _admite(lista, indice, animacion, imagenes, idioma, texto=None):
    """Si el plano `indice` puede llevar `animacion`. -> (senal, datos) | None"""
    escena = lista[indice]
    if not escena.get("id") or _es_cartela(escena) or _duracion(escena) < DURACION_MINIMA:
        return None
    senal = CATALOGO[animacion]["senal"]
    datos = senales(escena, idioma).get(senal)
    # Claude escoge el fragmento en el guion; la voz decide en QUE plano y en
    # QUE segundo cae. Nunca se muestra una frase de otro plano o inventada.
    if texto:
        palabras = str(escena.get("narracion") or "").split()
        rango = _rango_literal(palabras, texto)
        if not rango:
            return None
        marcas = escena.get("marcas") or []
        if len(marcas) != len(palabras):
            return None
        trozo = palabras[rango[0]:rango[1]]
        fragmento = {"narracion": " ".join(trozo), "marcas": marcas[rango[0]:rango[1]],
                     "t_in": escena.get("t_in")}
        elegido = senales(fragmento, idioma).get(senal)
        if senal == "termino" and _concepto_elegido(trozo):
            # Una ficha también puede explicar un concepto sin nombre propio:
            # solo cuando Claude eligió su nombre literal en el guion. La
            # heurística sin selección sigue exigiendo un nombre propio.
            elegido = {"nombre": " ".join(_limpio(p) for p in trozo),
                       "definicion": " ".join(palabras[:16]),
                       "desde": float(marcas[rango[0]][0]) - float(escena["t_in"]),
                       "hasta": float(marcas[rango[1] - 1][1]) - float(escena["t_in"])}
        if not elegido:
            return None
        datos = elegido
    largo = _duracion(escena)
    desde_inicio = animacion in ("collage-titulo", "comparacion-tarjetas")
    if (not datos or (not desde_inicio and datos["hasta"] > largo - 0.1)
            or (not desde_inicio and datos["desde"] > largo - CATALOGO[animacion].get(
                "tiempo", TIEMPO_PARA_LEERSE))):
        return None
    if _ficha_de(lista, indice, animacion, senal, datos, imagenes) is None:
        return None
    return senal, datos


def _repartir_planificado(lista, pedidas, etiquetas, idioma, imagenes, textos):
    """Las animaciones que el GUION dejo previstas, y las que aun faltan.

    Cada bloque etiquetado lleva UNA animacion y se le busca, dentro del bloque,
    el plano que dice lo que esa animacion necesita. Despues, lo que no ha
    salido -- el redactor no escribio la frase, o salio en un plano sin tiempo
    para leerse -- se busca por la senal en cualquier plano libre, con aire
    respecto a los ya animados: que una animacion elegida no aparezca nunca es
    justo lo que esto existe para evitar.
    """
    salida, ocupados = {}, set()
    por_bloque = {}
    for i, escena in enumerate(lista):
        por_bloque.setdefault(str((escena.get("origen") or {}).get("bloque") or ""), []).append(i)
    for bloque, animacion in sorted(etiquetas.items(),
                                    key=lambda par: (por_bloque.get(par[0]) or [10 ** 9])[0]):
        for i in por_bloque.get(bloque, []):
            visto = _admite(lista, i, animacion, imagenes, idioma, textos.get(bloque))
            if visto:
                salida[lista[i]["id"]] = _ficha_de(lista, i, animacion, visto[0], visto[1], imagenes)
                ocupados.add(i)
                break
    puestas = {f["animacion"] for f in salida.values()}
    for animacion in pedidas:
        if animacion in puestas:
            continue
        # Si Claude eligio una frase concreta pero no cabe en ningun plano de
        # su bloque, no sustituirla a escondidas por otra frase del video.
        if any(a == animacion and textos.get(b) for b, a in etiquetas.items()):
            continue
        for i in range(len(lista)):
            if i in ocupados or {i - 1, i + 1} & ocupados:
                continue
            visto = _admite(lista, i, animacion, imagenes, idioma)
            if visto:
                salida[lista[i]["id"]] = _ficha_de(lista, i, animacion, visto[0], visto[1], imagenes)
                ocupados.add(i)
                puestas.add(animacion)
                break
    return salida


def repartir(escenas, params=None, idioma=None, imagenes=None, semilla=0, etiquetas=None,
            textos=None):
    """Que animacion lleva cada plano. Determinista.

    -> {id_de_plano: {"animacion", "senal", "datos", "imagenes"?, "elementos"?}}

    Con `etiquetas` ({id_de_bloque: animacion}, lo que dejo el guion) se reparte
    LO PREVISTO: cada animacion va al plano de su bloque que dice lo que necesita
    (`_repartir_planificado`). Sin ellas -- un video de antes del plan -- se
    reparte mirando la narracion de cada plano, con aire entre dos animadas
    (HUECO_ENTRE_ANIMACIONES).

    `imagenes` es {id_de_plano: url, id_de_plano + '__tarjeta': segunda url}.
    Sin las dos imagenes propias, las animaciones que ensenan una SEGUNDA
    imagen no entran. `semilla` desempata entre las que comparten senal sin usar
    random: rehacer un plano suelto no puede cambiarle la animacion a otro.
    """
    imagenes = imagenes or {}
    etiquetas = {str(b): a for b, a in (etiquetas or {}).items() if a in CATALOGO}
    elegidas = elegidas_de(params)
    if etiquetas:
        previstas = set(etiquetas.values())
        pedidas = [a for a in CATALOGO if a in set(elegidas) | previstas]
        return _repartir_planificado(list(escenas or []), pedidas, etiquetas, idioma, imagenes,
                                    textos or {})
    if not elegidas:
        return {}
    por_senal = {}
    for a in elegidas:
        por_senal.setdefault(CATALOGO[a]["senal"], []).append(a)
    lista = list(escenas or [])
    salida, sin_animar, ultima = {}, HUECO_ENTRE_ANIMACIONES, None
    for indice, escena in enumerate(lista):
        sid = escena.get("id")
        if not sid:
            continue
        if _es_cartela(escena) or _duracion(escena) < DURACION_MINIMA:
            sin_animar += 1
            continue
        if sin_animar < HUECO_ENTRE_ANIMACIONES:
            sin_animar += 1
            continue
        vistas = senales(escena, idioma)
        largo = _duracion(escena)
        opciones = []
        for senal in PRIORIDAD:
            if senal not in vistas or senal not in por_senal:
                continue
            opciones += [(senal, a) for a in por_senal[senal]
                          if (a in ("collage-titulo", "comparacion-tarjetas") or
                              (vistas[senal]["hasta"] <= largo - 0.1 and
                               vistas[senal]["desde"] <= largo - CATALOGO[a].get(
                                   "tiempo", TIEMPO_PARA_LEERSE)))
                         and _ficha_de(lista, indice, a, senal, vistas[senal], imagenes) is not None]
        if not opciones:
            sin_animar += 1
            continue
        # la misma animacion dos veces seguidas cansa: se prefiere otra si la hay
        posibles = [o for o in opciones if o[1] != ultima] or opciones
        senal = posibles[0][0]
        grupo = [a for s, a in posibles if s == senal]
        animacion = grupo[medios.desempatar(semilla, sid, "animacion") % len(grupo)]
        salida[sid] = _ficha_de(lista, indice, animacion, senal, vistas[senal], imagenes)
        ultima = animacion
        sin_animar = 0
    return salida


def cobertura(reparto, pedidas):
    """Cuantas veces sale cada animacion pedida. -> {"pedidas", "colocadas", "faltan"}

    Es lo que dice si el video lleva TODAS las que se eligieron: una que falta
    es un guion que no tiene una frase que la sostenga, y se dice para que se
    pueda arreglar en vez de descubrirlo en el MP4.
    """
    pedidas = [a for a in CATALOGO if a in set(pedidas or [])]
    cuenta = {}
    for ficha in (reparto or {}).values():
        cuenta[ficha["animacion"]] = cuenta.get(ficha["animacion"], 0) + 1
    return {"pedidas": pedidas,
            "colocadas": {a: cuenta[a] for a in pedidas if a in cuenta},
            "faltan": [a for a in pedidas if a not in cuenta]}


# ===========================================================================
# EL PLAN, ANTES DEL GUION
#
# Las animaciones se colocan por lo que se DICE, asi que de nada sirve elegir
# ocho si el guion no tiene ni una cifra ni una comparacion: salen las que el
# texto casualmente permite. Por eso el plan va PRIMERO: antes de redactar se
# reparten las animaciones por el video (cada elegida, al menos una vez) y se le
# pide al redactor que escriba, en cada hueco, la frase que esa animacion
# necesita -- y que marque el bloque con su id. Lo que no escriba se rescata
# despues buscando el bloque que mejor lo diga (`etiquetar_bloques`).
# ===========================================================================

#: Lo que se le pide al redactor para que cada animacion tenga de que vivir.
PIDE = {
    "infografia-cifra": "una frase con una CIFRA o un PORCENTAJE concreto y de que es "
                        "(«el 45 por ciento de los barcos...»), tomada del material",
    "editorial-fecha": "una frase con un AÑO o una FECHA concreta del material (en la voz, "
                       "«en mil novecientos veintitrés», «el cinco de mayo»; la banda "
                       "mostrará 1923 o 5 MAYO)",
    "ficha-ui": "una frase que presente un NOMBRE PROPIO o CONCEPTO concreto y diga "
                "qué significa; elige su nombre literal para la ficha",
    "ficha-cristal": "una frase que presente un NOMBRE PROPIO o CONCEPTO concreto y diga "
                     "qué significa; elige su nombre literal para la ficha",
    "etiqueta-escrita": "una frase que introduzca un NOMBRE PROPIO o término clave "
                        "concreto; elige su nombre literal para la etiqueta",
    "collage-titulo": "una frase que nombre un lugar, institución, movimiento o CONCEPTO "
                      "concreto como protagonista; elige su nombre literal como título",
    "comparacion-tarjetas": "UNA frase que compare dos elementos concretos del material "
                            "con «mientras que» o «frente a» (por ejemplo, «las raíces "
                            "sanas crecen mientras que las atrofiadas...»). Sus dos "
                            "etiquetas deben describir dos imágenes distintas y exclusivas de esta escena",
    "tipografia-cinetica": "una frase CORTA y contundente, de 3 a 9 palabras, que se sostenga "
                           "sola y resuma el momento",
}

#: Un hueco cada tantos segundos de video, como minimo uno por animacion elegida.
SEGUNDOS_POR_HUECO = 35


def plan_de_huecos(elegidas, duracion_s, bloques, semilla=0):
    """Donde va cada animacion en el video, ANTES de escribirlo.

    -> [{"animacion", "senal", "bloque": n (1..bloques), "pide"}], en orden.

    Cada elegida sale al menos una vez; si sobra video se repiten rotando. Van
    repartidas entre el segundo bloque y el penultimo (el primero es el gancho y
    el ultimo el cierre, y las de tarjetas necesitan otro plano al lado), nunca
    en bloques seguidos mientras haya sitio, y sin repetir la misma dos veces
    seguidas.
    """
    elegidas = [a for a in CATALOGO if a in set(elegidas or [])]
    bloques = int(bloques or 0)
    if not elegidas or bloques < 3:
        return []
    libres = max(1, bloques - 2)
    huecos = max(len(elegidas), int(round(float(duracion_s or 0) / SEGUNDOS_POR_HUECO)))
    huecos = min(huecos, libres, 3 * len(elegidas))
    arranque = medios.desempatar(semilla, "plan_animaciones") % len(elegidas)
    orden = [elegidas[(arranque + k) % len(elegidas)] for k in range(huecos)]
    paso = libres / huecos
    plan = []
    for k, animacion in enumerate(orden):
        bloque = 2 + int(k * paso + paso / 2)
        plan.append({"animacion": animacion, "senal": CATALOGO[animacion]["senal"],
                     "bloque": min(bloque, bloques - 1), "pide": PIDE[animacion]})
    return plan


def bloque_para_guion(plan, bloques):
    """El trozo de la instruccion del guion que cuenta el plan. '' si no hay plan."""
    if not plan:
        return ""
    lineas = [
        "== ANIMACIONES GRAFICAS (motion graphics) ==",
        "En el montaje se superpondra una animacion sobre la imagen en las escenas "
        "donde se dice algo concreto. El video lleva estas, y CADA UNA tiene que "
        f"quedar colocada (el video tiene unos {int(bloques)} bloques):",
    ]
    for hueco in plan:
        nombre = CATALOGO[hueco["animacion"]]["nombre"]
        lineas.append(f"  - hacia el bloque {hueco['bloque']}: «{nombre}» "
                      f"(id \"{hueco['animacion']}\") -> {hueco['pide']}.")
    lineas += [
        "Como colocarlas:",
        "  1. Decide primero qué hecho o idea del material corresponde a cada "
        "animación y en qué parada del relato encaja. REDACTA ese bloque a partir "
        "de la animación asignada: una comparación DE VERDAD para las tarjetas, "
        "una fecha para la banda, un nombre y qué significa para las fichas o "
        "collage, una frase breve para la tipografía. No marques un bloque "
        "cualquiera por cumplir. Si el material no trae ese dato ahí, mueve la "
        "animación al bloque más cercano que sí lo tenga. NUNCA inventes datos.",
        "  2. Marca ese bloque con \"animacion\": \"<id>\" en el JSON (el id de la "
        "lista, tal cual) y elige \"animacion_texto\": el fragmento LITERAL que "
        "aparecerá en pantalla, con la cifra/fecha, el nombre completo, las dos "
        "ideas y su conector, o la frase corta. No marques otros bloques. "
        "Un bloque lleva como mucho una.",
        "  3. Comprueba antes de entregar que CADA animación elegida tenga un "
        "bloque distinto con su frase adecuada y su fragmento literal. El resto "
        "se escribe con naturalidad: la animación acompaña al relato, no lo sustituye.",
    ]
    return "\n".join(lineas)


def _texto_llano(texto):
    """El texto de un bloque sin anotaciones de voz (<break/>, <spell>...)."""
    return " ".join(re.sub(r"<[^>]*>", " ", str(texto or "")).split())


def senales_de_texto(texto, idioma=None):
    """Las senales de un TEXTO suelto (un bloque del guion), sin tiempos.

    Un bloque aun no tiene voz, asi que se le ponen marcas inventadas y
    uniformes: solo importa SI la senal esta, no cuando se dice.
    """
    palabras = _texto_llano(texto).split()
    marcas = [[round(i * 0.4, 3), round(i * 0.4 + 0.38, 3)] for i in range(len(palabras))]
    return senales({"narracion": " ".join(palabras), "marcas": marcas, "t_in": 0.0}, idioma)


def _rango_literal(palabras, fragmento):
    """Rango de palabras que reproduce literalmente el fragmento elegido."""
    objetivo = [_limpio(p).casefold() for p in _texto_llano(fragmento).split()]
    if not objetivo or len(objetivo) > 20:
        return None
    limpias = [_limpio(p).casefold() for p in palabras]
    for i in range(len(limpias) - len(objetivo) + 1):
        if limpias[i:i + len(objetivo)] == objetivo:
            return i, i + len(objetivo)
    return None


def validar_textos(bloques, idioma=None):
    """Descartar selecciones no literales o que no contienen lo que se anima."""
    for bloque in bloques:
        animacion = bloque.get("animacion")
        texto = bloque.get("animacion_texto")
        palabras = _texto_llano(bloque.get("texto")).split()
        rango = _rango_literal(palabras, texto) if texto else None
        senal = CATALOGO[animacion]["senal"] if animacion in CATALOGO else None
        trozo = palabras[rango[0]:rango[1]] if rango else []
        presentes = senales_de_texto(" ".join(trozo), idioma) if trozo else {}
        # Un concepto o nombre propio elegido por Claude no tiene por qué
        # llevar mayúsculas ni empezar a mitad de frase.
        valido = senal in presentes or (senal == "termino" and _concepto_elegido(trozo))
        if not animacion or not rango or not valido:
            bloque.pop("animacion_texto", None)
        else:
            bloque["animacion_texto"] = " ".join(palabras[rango[0]:rango[1]])


def etiquetar_bloques(bloques, elegidas, plan, idioma=None):
    """Deja en cada bloque la animacion que lleva. -> avisos (se toca `bloques`)

    Se parte de lo que marco el redactor, comprobando que de verdad dice lo que
    la animacion necesita (una marca sin frase que la sostenga no vale), y lo
    que quede sin colocar se RESCATA: se busca el bloque libre -- cerca de donde
    el plan lo pedia, sin pegarse a otro marcado -- cuyo texto tiene la senal.
    Lo que ni asi cabe se dice en los avisos con su nombre.
    """
    elegidas = [a for a in CATALOGO if a in set(elegidas or [])]
    avisos = []
    if not elegidas:
        for b in bloques:
            b.pop("animacion", None)
        return avisos
    vistas = [senales_de_texto(b.get("texto"), idioma) for b in bloques]
    for b, v in zip(bloques, vistas):
        a = str(b.get("animacion") or "").strip()
        texto = _texto_llano(b.get("texto")).split()
        fragmento = b.get("animacion_texto")
        rango = _rango_literal(texto, fragmento) if fragmento else None
        concepto = (a in CATALOGO and CATALOGO[a]["senal"] == "termino" and
                    rango and _concepto_elegido(texto[rango[0]:rango[1]]))
        if a and (a not in elegidas or (CATALOGO[a]["senal"] not in v and not concepto)):
            b.pop("animacion", None)
        elif not a:
            b.pop("animacion", None)
    puestas = {b["animacion"] for b in bloques if b.get("animacion")}
    donde = {h["animacion"]: h["bloque"] for h in (plan or []) if h["animacion"] not in puestas}
    for animacion in elegidas:
        if animacion in puestas:
            continue
        senal = CATALOGO[animacion]["senal"]
        pedido = donde.get(animacion, len(bloques) // 2)
        candidatos = []
        for i, (b, v) in enumerate(zip(bloques, vistas)):
            if b.get("animacion") or senal not in v or i in (0, len(bloques) - 1):
                continue
            # sin pegarse a otro marcado si hay sitio; si no, pegado: que salgan
            # TODAS importa mas que el aire entre dos
            pegado = any(bloques[j].get("animacion") for j in (i - 1, i + 1)
                         if 0 <= j < len(bloques))
            candidatos.append((pegado, abs((i + 1) - pedido), i))
        if not candidatos:
            avisos.append(f"la animacion «{CATALOGO[animacion]['nombre']}» no ha encontrado en "
                          f"el guion una frase que la sostenga: no saldra en el video")
            continue
        _, _, i = min(candidatos)
        bloques[i]["animacion"] = animacion
        puestas.add(animacion)
        avisos.append(f"la animacion «{CATALOGO[animacion]['nombre']}» se ha colocado en el "
                      f"bloque {bloques[i].get('id')}, donde el texto ya trae lo que necesita")
    return avisos


def pedidas_de(proyecto):
    """Las animaciones que se eligieron al escribir el guion. [] si no hay (o es de antes)."""
    try:
        import comun  # noqa: PLC0415
        documento = comun.leer_salida(proyecto, "guion", "guion.json", obligatorio=False) or {}
    except Exception:                                          # noqa: BLE001
        return []
    return [a for a in CATALOGO if a in set(documento.get("animaciones") or [])]


def etiquetas_de(proyecto):
    """{id_de_bloque: animacion} tal como las dejo el guion. {} si no hay (o es de antes)."""
    try:
        import comun  # noqa: PLC0415
        documento = comun.leer_salida(proyecto, "guion", "guion.json", obligatorio=False) or {}
    except Exception:                                          # noqa: BLE001
        return {}
    return {str(b["id"]): b["animacion"] for b in (documento.get("guion") or [])
            if isinstance(b, dict) and b.get("id") and b.get("animacion") in CATALOGO}


def textos_de(proyecto):
    """Fragmentos que Claude eligió al redactar cada bloque animado."""
    try:
        import comun  # noqa: PLC0415
        documento = comun.leer_salida(proyecto, "guion", "guion.json", obligatorio=False) or {}
    except Exception:                                          # noqa: BLE001
        return {}
    return {str(b["id"]): b["animacion_texto"] for b in (documento.get("guion") or [])
            if isinstance(b, dict) and b.get("id") and isinstance(b.get("animacion_texto"), str)
            and b.get("animacion") in CATALOGO}


# ===========================================================================
# EL DIBUJO
# ===========================================================================

def _rgb(hexa, respaldo=(255, 255, 255)):
    crudo = str(hexa or "").strip().lstrip("#")
    if len(crudo) == 3:
        crudo = "".join(c * 2 for c in crudo)
    try:
        return tuple(int(crudo[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return respaldo


def _sobre(fondo, claro="#f4f1ea", oscuro="#14130f"):
    """El color de texto que se lee sobre este fondo."""
    r, g, b = _rgb(fondo)
    return oscuro if 0.299 * r + 0.587 * g + 0.114 * b > 150 else claro


def _colores(paleta):
    p = paleta if isinstance(paleta, dict) else {}
    return {"texto": p.get("texto") or "#ece7dc", "tenue": p.get("tenue") or "#c9c2b4",
            "linea": p.get("linea") or "#d8a657", "sombra": p.get("sombra") or "#12130f",
            "acento": p.get("acento") or p.get("linea") or "#d8785a"}


def _s(segundos):
    return f"{max(0.0, float(segundos)):.3f}s"


def _esc(texto):
    return tipografia.escapar(texto)


def _anim(atributo, desde, hasta, inicio, dur, suave=True):
    spline = (' calcMode="spline" keyTimes="0;1" keySplines="0.22 0.7 0.2 1"'
              if suave else "")
    return (f'<animate attributeName="{atributo}" from="{desde}" to="{hasta}" '
            f'begin="{_s(inicio)}" dur="{_s(dur)}" fill="freeze"{spline}/>')


def _entra(inicio, dur=0.35, atributo="opacity"):
    return _anim(atributo, 0, 1, inicio, dur, suave=False)


def _sale(fin, dur=0.3, atributo="opacity"):
    return _anim(atributo, 1, 0, fin, dur, suave=False)


def _desliza(desde_xy, inicio, dur=0.45):
    return ('<animateTransform attributeName="transform" type="translate" '
            f'from="{desde_xy[0]:.1f} {desde_xy[1]:.1f}" to="0 0" '
            f'begin="{_s(inicio)}" dur="{_s(dur)}" fill="freeze" calcMode="spline" '
            'keyTimes="0;1" keySplines="0.22 0.7 0.2 1"/>')


def _grupo(interior, inicio, fin, desliza=None, dur_entra=0.35):
    """Un bloque que entra con fundido (y desplazamiento) y sale al final."""
    mueve = (f'<g>{_desliza(desliza, inicio)}{interior}</g>'
             if desliza else interior)
    return (f'<g opacity="0">{_entra(inicio, dur_entra)}{_sale(fin)}{mueve}</g>')


def _ventana(inicio, duracion_plano, minimo=2.0):
    """Cuando entra y cuando sale: el dato se enseña un poco antes de decirse."""
    entra = max(0.0, float(inicio) - 0.2)
    sale = min(float(duracion_plano) - 0.15, entra + PERMANENCIA_MAXIMA)
    sale = max(sale, entra + minimo)
    return round(entra, 3), round(min(sale, float(duracion_plano) - 0.05), 3)


def _unidad(ancho, alto):
    return max(0.5, min(float(ancho), float(alto)) / 1080.0)


def _formato_numero(valor, decimales, miles, coma):
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\0").replace(".", coma).replace("\0", miles)


def _partes_cifra(texto):
    """'45%' -> ('', 45.0, 0, ',', '.', '%'), o None si no se puede contar."""
    coincide = re.fullmatch(r"(\D*?)(\d[\d.,]*)(\D*)", texto.strip())
    if not coincide:
        return None
    prefijo, cuerpo, sufijo = coincide.groups()
    miles, coma, decimales = "", ".", 0
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", cuerpo):
        miles = cuerpo[len(re.match(r"\d{1,3}", cuerpo).group(0))]
        numero = float(re.sub(r"[.,]", "", cuerpo))
    elif re.fullmatch(r"\d+[.,]\d+", cuerpo):
        coma = re.search(r"[.,]", cuerpo).group(0)
        decimales = len(cuerpo) - cuerpo.index(coma) - 1
        numero = float(cuerpo.replace(coma, "."))
    elif re.fullmatch(r"\d+", cuerpo):
        numero = float(cuerpo)
    else:
        return None
    return prefijo, numero, decimales, miles, coma, sufijo


def _svg_cifra(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = _ventana(datos["desde"], duracion)
    x, y = 0.07 * ancho, 0.13 * alto
    w = min(0.46 * ancho, 700 * u) if ancho >= alto else 0.86 * ancho
    tam = 124 * u
    partes = _partes_cifra(datos["texto"])
    lleno = datos.get("porcentaje") and partes
    h = (330 if lleno else 262) * u
    interior = [f'<rect x="0" y="0" width="{w:.1f}" height="{h:.1f}" rx="{26*u:.1f}" '
                f'fill="{c["sombra"]}" fill-opacity="0.78"/>',
                f'<rect x="0" y="0" width="{9*u:.1f}" height="{h:.1f}" fill="{c["acento"]}"/>']
    if datos.get("etiqueta"):
        interior.append(
            f'<text x="{44*u:.1f}" y="{58*u:.1f}" font-family=\'{FUENTE_SVG}\' '
            f'font-size="{30*u:.1f}" font-weight="700" letter-spacing="{3*u:.1f}" '
            f'fill="{c["tenue"]}">{_esc(datos["etiqueta"].upper())}</text>')
    base_y = (200 if lleno else 190) * u
    pasos = 12
    inicio_cuenta, dur_cuenta = entra + 0.4, 1.1
    if partes:
        prefijo, numero, dec, miles, coma, sufijo = partes
        for k in range(pasos + 1):
            valor = numero * k / pasos
            t0 = inicio_cuenta + dur_cuenta * k / pasos
            t1 = inicio_cuenta + dur_cuenta * (k + 1) / pasos
            txt = f"{prefijo}{_formato_numero(valor, dec, miles, coma)}{sufijo}"
            fin = ('' if k == pasos else f'<set attributeName="display" to="none" '
                   f'begin="{_s(t1)}" fill="freeze"/>')
            interior.append(
                f'<text x="{44*u:.1f}" y="{base_y:.1f}" display="none" '
                f'font-family=\'{FUENTE_SVG}\' font-size="{tam:.1f}" font-weight="700" '
                f'fill="{c["texto"]}"><set attributeName="display" to="inline" '
                f'begin="{_s(t0)}" fill="freeze"/>{fin}{_esc(txt)}</text>')
    else:
        interior.append(
            f'<text x="{44*u:.1f}" y="{base_y:.1f}" font-family=\'{FUENTE_SVG}\' '
            f'font-size="{tam:.1f}" font-weight="700" fill="{c["texto"]}">'
            f'{_esc(datos["texto"])}</text>')
    if lleno:
        pista, ancho_barra = 30 * u, w - 88 * u
        porcentaje = max(0.0, min(100.0, partes[1])) / 100.0
        yb = 252 * u
        interior.append(
            f'<rect x="{44*u:.1f}" y="{yb:.1f}" width="{ancho_barra:.1f}" '
            f'height="{pista:.1f}" rx="{pista/2:.1f}" fill="{c["texto"]}" fill-opacity="0.18"/>')
        interior.append(
            f'<rect x="{44*u:.1f}" y="{yb:.1f}" width="0" height="{pista:.1f}" '
            f'rx="{pista/2:.1f}" fill="{c["acento"]}">'
            f'{_anim("width", 0, f"{ancho_barra * porcentaje:.1f}", inicio_cuenta, dur_cuenta)}'
            f'</rect>')
    else:
        interior.append(
            f'<rect x="{44*u:.1f}" y="{base_y + 30*u:.1f}" width="0" height="{6*u:.1f}" '
            f'fill="{c["acento"]}">{_anim("width", 0, f"{w - 88*u:.1f}", inicio_cuenta, dur_cuenta)}</rect>')
    cuerpo = _grupo("".join(interior), entra, sale, desliza=(-60 * u, 0))
    return f'<g transform="translate({x:.1f} {y:.1f})">{cuerpo}</g>'


def _svg_fecha(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = _ventana(datos["desde"], duracion)
    tam = 118 * u
    texto = str(datos["texto"])
    ancho_texto = tipografia.medir(texto, FUENTE_MEDIDA, tam, True)[0]
    w, h = ancho_texto + 120 * u, 176 * u
    x, y = 0.0, 0.13 * alto
    tinta = _sobre(c["acento"])
    banda = (f'<g transform="rotate(-1.6 {w/2:.1f} {h/2:.1f})">'
             f'<rect x="0" y="0" width="0" height="{h:.1f}" fill="{c["acento"]}">'
             f'{_anim("width", 0, f"{w:.1f}", entra, 0.55)}</rect>'
             f'<text x="{60*u:.1f}" y="{h*0.69:.1f}" opacity="0" '
             f'font-family=\'{FUENTE_SVG}\' font-size="{tam:.1f}" font-weight="700" '
             f'fill="{tinta}">{_entra(entra + 0.35)}{_esc(texto)}</text>'
             f'<rect x="{60*u:.1f}" y="{h + 14*u:.1f}" width="0" height="{5*u:.1f}" '
             f'fill="{c["texto"]}" fill-opacity="0.9">'
             f'{_anim("width", 0, f"{max(w - 60*u, 80*u):.1f}", entra + 0.5, 0.6)}</rect></g>')
    pie = ""
    if datos.get("contexto"):
        tam_c = 40 * u
        ctx = datos["contexto"]
        caja = tipografia.medir(ctx, FUENTE_MEDIDA, tam_c, True)[0] + 56 * u
        caja = min(caja, 0.9 * ancho - 60 * u)
        pie = (f'<g transform="translate({60*u:.1f} {h + 52*u:.1f})" opacity="0">'
               f'{_entra(entra + 0.85)}'
               f'<rect x="0" y="0" width="{caja:.1f}" height="{tam_c*1.7:.1f}" '
               f'rx="{10*u:.1f}" fill="{c["sombra"]}" fill-opacity="0.78"/>'
               f'<text x="{28*u:.1f}" y="{tam_c*1.2:.1f}" font-family=\'{FUENTE_SVG}\' '
               f'font-size="{tam_c:.1f}" fill="{c["texto"]}">{_esc(ctx)}</text></g>')
    cuerpo = _grupo(banda + pie, entra, sale)
    return f'<g transform="translate({x:.1f} {y:.1f})">{cuerpo}</g>'


def _svg_ficha(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = _ventana(datos["desde"], duracion, minimo=2.6)
    w = min(0.5 * ancho, 820 * u) if ancho >= alto else 0.86 * ancho
    margen = 40 * u
    tam_n, tam_d = 66 * u, 31 * u
    tam_n *= min(1.0, (w - 2 * margen) / max(1, tipografia.medir(
        datos["nombre"], FUENTE_MEDIDA, tam_n, True)[0]))
    lineas = tipografia.partir(datos["definicion"], FUENTE_MEDIDA, tam_d, False, 0,
                               w - 2 * margen)[:3]
    h = margen + 34 * u + 86 * u + len(lineas) * tam_d * 1.45 + margen * 0.8
    x, y = 0.07 * ancho, 0.13 * alto
    base = (f'<rect x="0" y="0" width="{w*0.18:.1f}" height="{h:.1f}" rx="{28*u:.1f}" '
            f'fill="{c["sombra"]}" fill-opacity="0.82">'
            f'{_anim("width", f"{w*0.18:.1f}", f"{w:.1f}", entra, 0.5)}</rect>')
    etiqueta = (f'<text x="{margen:.1f}" y="{margen + 24*u:.1f}" opacity="0" '
                f'font-family=\'{FUENTE_SVG}\' font-size="{26*u:.1f}" font-weight="700" '
                f'letter-spacing="{4*u:.1f}" fill="{c["acento"]}">{_entra(entra + 0.5)}'
                f'{_esc(datos.get("etiqueta", "CONCEPTO"))}</text>')
    nombre = (f'<text x="{margen:.1f}" y="{margen + 24*u + 76*u:.1f}" opacity="0" '
              f'font-family=\'{FUENTE_SVG}\' font-size="{tam_n:.1f}" font-weight="700" '
              f'fill="{c["texto"]}">{_entra(entra + 0.7)}{_esc(datos["nombre"])}</text>')
    cuerpo = "".join(
        f'<text x="{margen:.1f}" y="{margen + 24*u + 76*u + 50*u + k*tam_d*1.45:.1f}" '
        f'opacity="0" font-family=\'{FUENTE_SVG}\' font-size="{tam_d:.1f}" '
        f'fill="{c["tenue"]}">{_entra(entra + 1.0 + k * 0.12)}{_esc(linea)}</text>'
        for k, linea in enumerate(lineas))
    return (f'<g transform="translate({x:.1f} {y:.1f})"><g opacity="0">{_entra(entra, 0.2)}'
            f'{_sale(sale)}{base}{etiqueta}{nombre}{cuerpo}</g></g>')


def _svg_cinetica(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    palabras, tiempos = datos["palabras"], datos["tiempos"]
    tam = 74 * u
    ancho_max = 0.78 * ancho
    hueco = tam * 0.32
    # las lineas se parten midiendo, no contando letras
    lineas, actual, ancho_actual = [], [], 0.0
    medidas = [tipografia.medir(p, FUENTE_MEDIDA, tam, True)[0] for p in palabras]
    for k, ancho_p in enumerate(medidas):
        extra = ancho_p + (hueco if actual else 0)
        if actual and ancho_actual + extra > ancho_max:
            lineas.append(actual)
            actual, ancho_actual = [], 0.0
            extra = ancho_p
        actual.append(k)
        ancho_actual += extra
    if actual:
        lineas.append(actual)
    interlinea = tam * 1.3
    caja_w = max(sum(medidas[k] for k in ln) + hueco * (len(ln) - 1) for ln in lineas)
    pad = 36 * u
    caja_h = len(lineas) * interlinea + pad * 0.6
    x, y = 0.07 * ancho, 0.13 * alto
    inicio = max(0.0, tiempos[0][0] - 0.25)
    fin = min(duracion - 0.05, max(tiempos[-1][1] + 1.6, inicio + 2.6))
    claves = subrayadas_de(datos)
    piezas = [f'<rect x="{-pad:.1f}" y="{-pad*0.55:.1f}" width="{caja_w + 2*pad:.1f}" '
              f'height="{caja_h + pad*0.4:.1f}" rx="{20*u:.1f}" fill="{c["sombra"]}" '
              f'fill-opacity="0.62"/>']
    for fila, ln in enumerate(lineas):
        cursor = 0.0
        for k in ln:
            px, py = cursor, tam + fila * interlinea
            t0 = tiempos[k][0]
            if k in claves:
                piezas.append(
                    f'<rect x="{px - 10*u:.1f}" y="{py - tam*0.9:.1f}" width="0" '
                    f'height="{tam*1.15:.1f}" rx="{8*u:.1f}" fill="{c["acento"]}" '
                    f'fill-opacity="0.9">{_anim("width", 0, f"{medidas[k] + 20*u:.1f}", t0, 0.4)}</rect>')
            tinta = _sobre(c["acento"]) if k in claves else c["texto"]
            piezas.append(
                f'<text x="{px:.1f}" y="{py:.1f}" fill-opacity="0" '
                f'font-family=\'{FUENTE_SVG}\' font-size="{tam:.1f}" font-weight="700" '
                f'fill="{tinta}">{_anim("fill-opacity", 0, 1, t0, 0.18, suave=False)}'
                f'{_esc(palabras[k])}</text>')
            cursor += medidas[k] + hueco
    cuerpo = _grupo("".join(piezas), inicio, fin, dur_entra=0.2)
    return f'<g transform="translate({x:.1f} {y:.1f})">{cuerpo}</g>'


# ---------------------------------------------------------------- el fondo
#
# Atenuar o desenfocar el PLANO no lo puede hacer una capa SVG puesta encima: se
# haria con un filtro sobre el propio plano. Lo aplica la pagina de render con
# esta funcion de t (la misma en p8 y en el generador de GIF, para que la tarjeta
# ensene lo que se monta). `F` = {"t": [sube_ini, sube_fin, baja_ini, baja_fin],
# "blur": px, "luz": brillo}. Sin `F` no toca nada.
JS_FONDO = """function aplicarFondo(el, F, t){
  if (!F) return;
  const S = u => { u = Math.min(1, Math.max(0, u)); return u*u*(3-2*u); };
  const k = S((t-F.t[0])/Math.max(1e-6, F.t[1]-F.t[0]))
          * (1 - S((t-F.t[2])/Math.max(1e-6, F.t[3]-F.t[2])));
  el.style.filter = k > 0.001 ? 'blur(' + (F.blur*k).toFixed(2) + 'px) brightness('
    + (1 + (F.luz-1)*k).toFixed(4) + ')' : '';
}"""


def _fondo(entra, sale, blur, luz, sube=0.6, baja=0.4):
    return {"t": [round(entra, 3), round(entra + sube, 3), round(sale, 3), round(sale + baja, 3)],
            "blur": blur, "luz": luz}


def _tecleo(texto, x, y, tam, color, inicio, paso, ancla="start", espaciado=0, extra="",
            trazo=None):
    """Un texto que se ESCRIBE: todas las letras estan, a opacidad 0, y cada una
    se enciende a su hora. Asi la caja no se mueve mientras se escribe.

    `trazo` es la opacidad del contorno (si `extra` lo lleva): hay que encenderlo
    letra a letra tambien, o el contorno de las que faltan se ve como un fantasma.
    """
    def letra(k, ch):
        t0 = inicio + k * paso
        atributo = ' stroke-opacity="0"' if trazo is not None else ""
        anim = (_anim("stroke-opacity", 0, trazo, t0, 0.01, suave=False)
                if trazo is not None else "")
        return (f'<tspan fill-opacity="0"{atributo}>'
                f'{_anim("fill-opacity", 0, 1, t0, 0.01, suave=False)}{anim}{_esc(ch)}</tspan>')
    letras = "".join(letra(k, ch) for k, ch in enumerate(texto))
    return (f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" text-anchor="{ancla}" '
            f'font-family=\'{FUENTE_SVG}\' font-size="{tam:.1f}" font-weight="700" '
            f'letter-spacing="{espaciado:.1f}" fill="{color}" {extra}>{letras}</text>')


def _svg_etiqueta(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = _ventana(datos["desde"], duracion, minimo=2.6)
    texto = str(datos["nombre"]).upper()
    tam, esp = 62 * u, 5 * u
    pad = 34 * u
    escala = min(1.0, (0.9 * ancho - 2 * pad) / max(1, tipografia.medir(
        texto, FUENTE_MEDIDA, tam, True, esp)[0]))
    tam, esp = tam * escala, esp * escala
    w = tipografia.medir(texto, FUENTE_MEDIDA, tam, True, esp)[0] + 2 * pad
    h = tam * 1.7
    paso = min(0.075, max(0.03, 1.3 / max(1, len(texto))))
    inicio = entra + 0.15
    dur = paso * len(texto) + 0.1
    x, y = 0.05 * ancho, 0.58 * alto
    caja = (f'<clipPath id="eti"><rect x="0" y="-4" width="0" height="{h + 12:.1f}">'
            f'{_anim("width", 0, f"{w + 8:.1f}", inicio, dur, suave=False)}</rect></clipPath>'
            f'<polygon points="0,0 {w:.1f},0 {w - 16*u:.1f},{h:.1f} 0,{h:.1f}" '
            f'fill="#f6f4ee" clip-path="url(#eti)"/>'
            f'<rect x="0" y="{h:.1f}" width="0" height="{6*u:.1f}" fill="{c["acento"]}">'
            f'{_anim("width", 0, f"{w - 16*u:.1f}", inicio + dur * 0.6, 0.5)}</rect>')
    letras = _tecleo(texto, pad, h * 0.68, tam, "#14130f", inicio + 0.05, paso, espaciado=esp)
    cuerpo = _grupo(caja + letras, entra, sale, dur_entra=0.1)
    return (f'<g transform="translate({x:.1f} {y:.1f})">{cuerpo}</g>',
            _fondo(entra, sale, 7.0, 0.8))


def _svg_cristal(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = _ventana(datos["desde"], duracion, minimo=2.8)
    w = min(0.64 * ancho, 1120 * u) if ancho >= alto else 0.9 * ancho
    m = 34 * u
    chip_t = 22 * u
    etiqueta = str(datos.get("etiqueta", "CONCEPTO"))
    chip_medido = tipografia.medir(etiqueta, FUENTE_MEDIDA, chip_t, True, 3 * u)[0] + 40 * u
    chip_w = min(w * 0.35, chip_medido)
    ajuste_chip = (f'textLength="{max(1, chip_w - 40*u):.1f}" lengthAdjust="spacingAndGlyphs" '
                   if chip_medido > chip_w else "")
    tam_n, tam_d = 50 * u, 26 * u
    tam_n *= min(1.0, (w - 2 * m - chip_w - 26 * u) / max(1, tipografia.medir(
        datos["nombre"], FUENTE_MEDIDA, tam_n, True)[0]))
    nombre = str(datos["nombre"])
    lineas = tipografia.partir(datos["definicion"], FUENTE_MEDIDA, tam_d, False, 0, w - 2 * m)[:2]
    h = m * 2 + 56 * u + len(lineas) * tam_d * 1.5 + 6 * u
    x, y = (0.06 * ancho if ancho >= alto else 0.05 * ancho), 0.56 * alto
    cx = w / 2
    tarjeta = (f'<rect x="{cx - 5*u:.1f}" y="0" width="{10*u:.1f}" height="{h:.1f}" rx="{22*u:.1f}" '
               f'fill="#17171b" fill-opacity="0.88" stroke="#ffffff" stroke-opacity="0.16" '
               f'stroke-width="{1.5*u:.1f}">'
               f'{_anim("x", f"{cx - 5*u:.1f}", "0", entra + 0.25, 0.5)}'
               f'{_anim("width", f"{10*u:.1f}", f"{w:.1f}", entra + 0.25, 0.5)}</rect>')
    brillo = (f'<clipPath id="cri"><rect width="{w:.1f}" height="{h:.1f}" rx="{22*u:.1f}"/></clipPath>'
              f'<linearGradient id="bri" x1="0" x2="1" y1="0" y2="0">'
              f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
              f'<stop offset="0.5" stop-color="#fff" stop-opacity="0.26"/>'
              f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
              f'<g clip-path="url(#cri)"><rect x="{-0.3*w:.1f}" y="0" width="{0.26*w:.1f}" '
              f'height="{h:.1f}" fill="url(#bri)" opacity="0">'
              f'<animateTransform attributeName="transform" type="translate" from="0 0" '
              f'to="{1.5*w:.1f} 0" begin="{_s(entra + 1.6)}" dur="{_s(1.0)}" fill="freeze"/>'
              f'{_entra(entra + 1.6, 0.05)}{_sale(entra + 2.55, 0.05)}</rect></g>')
    chip = (f'<g opacity="0">{_entra(entra + 0.7)}'
            f'<rect x="{m:.1f}" y="{m:.1f}" width="{chip_w:.1f}" height="{40*u:.1f}" rx="{20*u:.1f}" '
            f'fill="#ffffff" fill-opacity="0.08" stroke="#ffffff" stroke-opacity="0.3" '
            f'stroke-width="{1.2*u:.1f}"/>'
            f'<text x="{m + chip_w/2:.1f}" y="{m + 28*u:.1f}" text-anchor="middle" '
            f'font-family=\'{FUENTE_SVG}\' font-size="{chip_t:.1f}" font-weight="700" '
            f'{ajuste_chip}letter-spacing="{3*u:.1f}" fill="#e9e6df">{_esc(etiqueta)}</text></g>')
    titulo = (f'<text x="{m + chip_w + 26*u:.1f}" y="{m + 36*u:.1f}" opacity="0" '
              f'font-family=\'{FUENTE_SVG}\' font-size="{tam_n:.1f}" font-weight="700" '
              f'fill="#ffffff">{_entra(entra + 0.85)}{_esc(nombre)}</text>')
    texto = "".join(
        f'<text x="{m:.1f}" y="{m + 56*u + 28*u + k*tam_d*1.5:.1f}" opacity="0" '
        f'font-family=\'{FUENTE_SVG}\' font-size="{tam_d:.1f}" fill="#cfcbc2">'
        f'{_entra(entra + 1.1 + k * 0.12)}{_esc(l)}</text>' for k, l in enumerate(lineas))
    cuerpo = _grupo(tarjeta + brillo + chip + titulo + texto, entra, sale, dur_entra=0.15)
    return f'<g transform="translate({x:.1f} {y:.1f})">{cuerpo}</g>', None


def _tarjeta_foto(uid, href, cw, ch, u, inicio, desliza, dur=0.7, fin=None):
    """Una foto con esquinas redondeadas y sombra que entra deslizando y se queda."""
    r = 16 * u
    interior = (f'<defs><clipPath id="{uid}"><rect width="{cw:.1f}" height="{ch:.1f}" rx="{r:.1f}"/></clipPath>'
                f'<filter id="{uid}s" x="-20%" y="-20%" width="140%" height="140%">'
                f'<feGaussianBlur stdDeviation="{14*u:.1f}"/></filter></defs>'
                f'<rect x="{6*u:.1f}" y="{16*u:.1f}" width="{cw:.1f}" height="{ch:.1f}" rx="{r:.1f}" '
                f'fill="#000" fill-opacity="0.45" filter="url(#{uid}s)"/>'
                f'<image href="{_esc(href)}" width="{cw:.1f}" height="{ch:.1f}" '
                f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{uid})"/>')
    salida = _sale(fin) if fin is not None else ""
    return (f'<g opacity="0">{_entra(inicio, 0.45)}{salida}'
            f'<g>{_desliza(desliza, inicio, dur)}{interior}</g></g>')


def _medidas_tarjetas(ancho, alto, altura=0.5):
    ch = altura * alto
    cw = min(ch * 0.75, 0.40 * ancho)
    return cw, cw / 0.75


def _svg_collage(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    # Las dos fotos constituyen el plano completo: no aplicarles el limite de
    # permanencia de los rotulos breves ni fundirlas antes del corte.
    entra, sale = 0.0, float(duracion)
    cw, ch = _medidas_tarjetas(ancho, alto)
    y = 0.31 * alto
    titulo = str(datos["nombre"]).upper()
    tam = min(86 * u, 0.9 * ancho / max(6, len(titulo)) * 1.5)
    una = _tarjeta_foto("co1", ctx["imagenes"]["propia"], cw, ch, u, entra, (-70 * u, 0), fin=sale)
    dos = _tarjeta_foto("co2", ctx["imagenes"]["otra"], cw, ch, u, entra + 0.95, (70 * u, 0), fin=sale)
    paso = min(0.07, max(0.035, 1.2 / max(1, len(titulo))))
    letras = _tecleo(titulo, ancho / 2, 0.2 * alto, tam, "#ffffff", entra + 1.7, paso,
                     ancla="middle", espaciado=4 * u,
                     extra=f'stroke="#000" stroke-width="{5*u:.1f}" '
                           f'paint-order="stroke" stroke-linejoin="round"', trazo=0.5)
    cuerpo = (f'<g transform="translate({ancho * 0.33 - cw / 2:.1f} {y:.1f})">{una}</g>'
              f'<g transform="translate({ancho * 0.67 - cw / 2:.1f} {y:.1f})">{dos}</g>'
              f'<g opacity="1">{_sale(sale)}{letras}</g>')
    return cuerpo, _fondo(entra, sale, 10.0, 0.14)


def _svg_comparacion(datos, duracion, ancho, alto, c, ctx=None):
    u = _unidad(ancho, alto)
    entra, sale = 0.0, float(duracion)
    cw, ch = _medidas_tarjetas(ancho, alto, 0.5)
    y = 0.2 * alto
    tam = min(44 * u, cw / max(6, len(datos["izquierda"])) * 1.6)

    def etiqueta(texto, cx, inicio):
        return (f'<text x="{cx:.1f}" y="{y + ch + 66*u:.1f}" text-anchor="middle" opacity="0" '
                f'font-family=\'{FUENTE_SVG}\' font-size="{tam:.1f}" font-weight="700" '
                f'letter-spacing="{2*u:.1f}" fill="#ffffff" stroke="#000" stroke-opacity="0.5" '
                f'stroke-width="{6*u:.1f}" paint-order="stroke" stroke-linejoin="round">'
                f'{_entra(inicio)}{_sale(sale)}{_esc(texto)}</text>')
    xa, xb = ancho * 0.31, ancho * 0.69
    una = _tarjeta_foto("cp1", ctx["imagenes"]["propia"], cw, ch, u, entra,
                        (0, 0.4 * alto), dur=0.8, fin=sale)
    dos = _tarjeta_foto("cp2", ctx["imagenes"]["otra"], cw, ch, u, entra + 1.3,
                        (0, -0.55 * alto), dur=0.8, fin=sale)
    cuerpo = (f'<g transform="translate({xa - cw / 2:.1f} {y:.1f})">{una}</g>'
              f'<g transform="translate({xb - cw / 2:.1f} {y:.1f})">{dos}</g>'
              + etiqueta(datos["izquierda"], xa, entra + 1.0)
              + etiqueta(datos["derecha"], xb, entra + 2.0))
    return cuerpo, _fondo(entra, sale, 6.0, 0.42)


_DIBUJANTES = {"infografia-cifra": _svg_cifra, "editorial-fecha": _svg_fecha,
               "ficha-ui": _svg_ficha, "tipografia-cinetica": _svg_cinetica,
               "ficha-cristal": _svg_cristal, "etiqueta-escrita": _svg_etiqueta,
               "collage-titulo": _svg_collage, "comparacion-tarjetas": _svg_comparacion}


def ajustar_svg(svg, fondo, asignacion, duracion):
    """Desplazamientos en coordenadas del lienzo y un único reloj para previa/render."""
    import xml.etree.ElementTree as ET
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    raiz = ET.fromstring(svg)
    caja = [float(v) for v in raiz.attrib["viewBox"].split()]
    posiciones = asignacion.get("posiciones") or {}
    indice = 0

    def envolver(padre):
        nonlocal indice
        for hijo in list(padre):
            tipo = hijo.tag.split("}")[-1]
            if tipo in {"defs", "clipPath", "mask", "filter"}:
                continue
            if tipo in {"text", "rect", "image", "path", "circle", "ellipse", "line", "polygon", "polyline"}:
                clave = f"e{indice}"
                indice += 1
                punto = posiciones.get(clave) or {"x": 0, "y": 0}
                grupo = ET.Element(f"{{{ns}}}g", {"data-elemento": clave,
                    "transform": f'translate({punto["x"] * caja[2]:.6f} {punto["y"] * caja[3]:.6f})'})
                padre.insert(list(padre).index(hijo), grupo)
                padre.remove(hijo)
                grupo.append(hijo)
            else:
                envolver(hijo)
    envolver(raiz)
    punto = posiciones.get("conjunto") or {"x": 0, "y": 0}
    conjunto = ET.Element(f"{{{ns}}}g", {"data-conjunto": "animacion",
        "transform": f'translate({punto["x"] * caja[2]:.6f} {punto["y"] * caja[3]:.6f})'})
    for hijo in list(raiz):
        if hijo.tag.split("}")[-1] not in {"defs", "style", "title", "desc", "metadata"}:
            raiz.remove(hijo)
            conjunto.append(hijo)
    raiz.append(conjunto)
    if "duracion" in asignacion:
        # Escalar también los set y animateTransform: no cortar entradas largas.
        fin = max((float(el.get("begin", "0s")[:-1]) + float(el.get("dur", "0s")[:-1])
                   for el in raiz.iter() if el.tag.split("}")[-1] in {"animate", "animateTransform", "set"}
                   and el.get("repeatCount") != "indefinite"
                   and re.fullmatch(r"[\d.]+s", el.get("begin", "0s"))
                   and re.fullmatch(r"[\d.]+s", el.get("dur", "0s"))), default=duracion)
        if es_cartela_editor(asignacion.get("animacion")):
            # Las cartelas se escriben y permanecen: su ventana original es el
            # plano completo, no la duración de la deriva decorativa en bucle.
            fin = max(float(duracion), fin)
        limite = asignacion["duracion"]
        salida_cartela = min(0.25, limite * 0.1) if es_cartela_editor(asignacion.get("animacion")) else 0
        escala = (limite - salida_cartela) / max(fin, 0.001)
        for el in raiz.iter():
            for atributo in ("begin", "dur"):
                valor = el.get(atributo, "")
                if re.fullmatch(r"[\d.]+s", valor):
                    el.set(atributo, _s(float(valor[:-1]) * escala))
        if fondo:
            fondo = dict(fondo, t=[t * escala for t in fondo["t"]])
        if es_cartela_editor(asignacion.get("animacion")):
            conjunto.append(ET.Element(f"{{{ns}}}animate", {
                "attributeName": "opacity", "from": "1", "to": "0",
                "begin": _s(limite - salida_cartela), "dur": _s(salida_cartela), "fill": "freeze"}))
            conjunto.append(ET.Element(f"{{{ns}}}set", {
                "attributeName": "display", "to": "none", "begin": _s(limite), "fill": "freeze"}))
    return ET.tostring(raiz, encoding="unicode"), fondo


def svg_de(asignacion, duracion, salida=(1920, 1080), paleta=None):
    """El SVG de la animacion de UN plano, a tamano del cuadro de salida.

    `asignacion` es lo que devuelve `repartir` para ese plano. -> (svg, fondo):
    el SVG va encima del plano y `fondo` (o None) es lo que hay que hacerle al
    plano de debajo (ver JS_FONDO). Cadena vacia si la animacion no se sabe
    dibujar: el plano sale sin ella, que es lo que habria salido sin pedirla.
    """
    aid = (asignacion or {}).get("animacion")
    if es_cartela_editor(aid):
        lienzo = (864, 1536) if salida[1] > salida[0] else (1536, 864)
        svg = cartelas.svg_capa({"plantilla": aid.removeprefix("cartela-"),
                                 "datos": asignacion["datos"]}, paleta,
                                duracion=float(duracion), lienzo=lienzo, salida=salida, reloj_unico=True)
        svg = re.sub(r'width="\d+" height="\d+"',
                     f'width="{int(salida[0])}" height="{int(salida[1])}"', svg, count=1)
        return ajustar_svg(svg, None, asignacion, duracion)
    dibujar = _DIBUJANTES.get(aid)
    if not dibujar:
        return "", None
    ancho, alto = int(salida[0]), int(salida[1])
    try:
        resultado = dibujar(asignacion["datos"], float(duracion), ancho, alto,
                            _colores(paleta), asignacion)
    except (KeyError, TypeError, ValueError, IndexError):
        return "", None
    interior, fondo = resultado if isinstance(resultado, tuple) else (resultado, None)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
           f'viewBox="0 0 {ancho} {alto}">{interior}</svg>')
    return ajustar_svg(svg, fondo, asignacion, duracion)


def capas(escenas, params=None, idioma=None, paleta=None, salida=(1920, 1080),
          imagenes=None, semilla=0, etiquetas=None, textos=None, imagenes_usuario=None):
    """Todo lo que hace falta para el render.
    -> {id_de_plano: {"svg", "animacion", "fondo", "imagenes"}}

    `imagenes` son las URL de las imagenes de cada plano; en el resultado vuelven
    las que la pagina tiene que PRECARGAR (las de las tarjetas): un <image>
    dentro de un SVG no lo espera nadie y la primera captura saldria con la
    tarjeta vacia.
    """
    reparto = repartir(escenas, params, idioma, imagenes=imagenes, semilla=semilla,
                       etiquetas=etiquetas, textos=textos)
    reparto = aplicar_ediciones(reparto, escenas, ediciones_de(params), imagenes, imagenes_usuario,
                                estricto=False)
    por_id = {e.get("id"): e for e in escenas or []}
    resultado = {}
    for sid, asignacion in reparto.items():
        svg, fondo = svg_de(asignacion, _duracion(por_id[sid]), salida, paleta)
        if svg:
            resultado[sid] = {"svg": svg, "animacion": asignacion["animacion"], "fondo": fondo,
                              "contenido": contenido_de(asignacion["animacion"], asignacion["datos"]),
                              "elementos": asignacion.get("elementos"),
                              "tarjetas": asignacion.get("imagenes") or {},
                               "imagenes_usuario": asignacion.get("imagenes_usuario") or {},
                               "posiciones": asignacion.get("posiciones") or {},
                               "duracion": asignacion.get("duracion"),
                              "imagenes": sorted((asignacion.get("imagenes") or {}).values()),
                              "pico": pico_de(svg, _duracion(por_id[sid]))}
    return resultado


_RE_ANIMATE = re.compile(
    r'<animate\b[^>]*?attributeName="([^"]*)"[^>]*?\bfrom="([^"]*)"'
    r'[^>]*?\bto="([^"]*)"[^>]*?\bbegin="([0-9.]+)s"'
    r'(?:[^>]*?\bdur="([0-9.]+)s")?')


def pico_de(svg, duracion):
    """El instante en que la animacion esta COMPLETA y todavia no ha salido.

    Es el cuadro que ensena la previa cuando nadie esta reproduciendo: en t=0 una
    animacion no ha empezado y la previa parecería no llevar ninguna. Sale de los
    propios tiempos del SVG -- cuando acaba la ultima entrada, antes de la primera
    salida -- sin que cada dibujante tenga que declararlo.
    """
    entradas, salidas = [], []
    for atributo, origen, destino, inicio, dur in _RE_ANIMATE.findall(svg or ""):
        inicio, dur = float(inicio), float(dur or 0)
        # una SALIDA es un fundido hacia 0. Otras cosas acaban en 0 sin salir (una
        # posicion que vuelve a su sitio, un ancho que parte de 0 no): solo cuenta
        # la opacidad que baja
        sale = "opacity" in atributo and destino in ("0", "0.0") and origen not in ("0", "0.0")
        (salidas if sale else entradas).append(inicio + dur)
    if not entradas:
        return 0.0
    pico = max(entradas) + 0.15
    if salidas:
        pico = min(pico, min(salidas) - 0.05)
    return round(max(0.0, min(pico, float(duracion) - 0.05)), 3)


def describir(params=None):
    elegidas = elegidas_de(params)
    return ("sin animaciones" if not elegidas
            else "animaciones: " + ", ".join(CATALOGO[a]["nombre"] for a in elegidas))


def catalogo_para_pantalla(elegidas=None):
    """Las fichas del catalogo, listas para pintar las tarjetas de la pantalla."""
    marcadas = set(elegidas or [])
    return [{"id": aid, "nombre": f["nombre"], "descripcion": f["descripcion"],
             "tecnica": f["tecnica"], "senal": f["senal"],
             "defecto": bool(f["defecto"]), "elegida": aid in marcadas,
             "gif": f"anim_{aid}.gif"}
            for aid, f in CATALOGO.items()]
