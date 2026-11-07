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

Dos de ellas -- collage-titulo y comparacion-tarjetas -- ensenan TAMBIEN la
imagen del plano siguiente, asi que solo se reparten si esa imagen existe (ver
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
No toca imagenes, ni voz, ni subtitulos: es un parametro del RENDER y nada mas,
asi que cambiar la seleccion nunca deja obsoleto un plano ya pagado. Y sin el
param `animaciones` -- cualquier video de antes -- no pinta nada: el montaje
sale byte a byte como salia.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import medios  # noqa: E402
import subtitulos  # noqa: E402
import tipografia  # noqa: E402

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
        "descripcion": "El fondo se oscurece, entran dos fotos una tras otra y el título se escribe encima. Usa la imagen del plano siguiente.",
        "tecnica": "Collage Animation", "senal": "termino", "defecto": False, "tiempo": 3.6,
        "requiere_imagenes": True,
    },
    "comparacion-tarjetas": {
        "nombre": "Comparación de tarjetas",
        "descripcion": "Una tarjeta sube desde abajo y otra cae desde arriba, cada una con su etiqueta. Usa la imagen del plano siguiente.",
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


def _fecha(palabras, marcas, t_in):
    for i, palabra in enumerate(palabras):
        coincide = _RE_ANIO.match(str(palabra))
        if not coincide:
            continue
        desde, hasta = _tiempos(marcas, i, i + 1, t_in)
        # el contexto es lo que cuelga del ano: «en 1923, cuando cayó el muro»
        resto = _contexto(palabras, i + 1, despues=6, tope=7)
        return {"texto": coincide.group(1), "contexto": resto,
                "desde": desde, "hasta": hasta}
    for i, palabra in enumerate(palabras[:-1]):
        if _limpio(palabra).lower() == "de" and i >= 1 and re.fullmatch(
                _MESES, _limpio(palabras[i + 1]).lower() or "-"):
            dia = _limpio(palabras[i - 1])
            if dia.isdigit() and 1 <= int(dia) <= 31:
                desde, hasta = _tiempos(marcas, i - 1, i + 2, t_in)
                return {"texto": f"{dia} {_limpio(palabras[i + 1]).upper()}",
                        "contexto": _contexto(palabras, i + 2, despues=6, tope=7),
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
        while j < len(palabras) and j - i < 3 and _limpio(palabras[j])[:1].isupper() \
                and not _RE_ANIO.match(str(palabras[j])):
            j += 1
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
                              ("fecha", lambda: _fecha(palabras, marcas, t_in)),
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


def repartir(escenas, params=None, idioma=None, imagenes=None, semilla=0):
    """Que animacion lleva cada plano. Determinista.

    -> {id_de_plano: {"animacion", "senal", "datos", "imagenes"?}}

    Solo los planos que llevan algo: el resto no aparece. Mirando la narracion
    de cada uno, y con aire entre dos animadas (HUECO_ENTRE_ANIMACIONES).

    `imagenes` es {id_de_plano: url de su imagen}. Sin ella -- o si al plano le
    falta su vecino -- las animaciones que ensenan una SEGUNDA imagen no entran.
    `semilla` desempata entre las que comparten senal sin usar random: rehacer un
    plano suelto no puede cambiarle la animacion a otro.
    """
    elegidas = elegidas_de(params)
    if not elegidas:
        return {}
    imagenes = imagenes or {}
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
        siguiente = lista[indice + 1] if indice + 1 < len(lista) else None
        con_vecina = bool(siguiente and siguiente.get("id") and not _es_cartela(siguiente)
                          and imagenes.get(sid) and imagenes.get(siguiente["id"]))
        vistas = senales(escena, idioma)
        largo = _duracion(escena)
        opciones = []
        for senal in PRIORIDAD:
            if senal not in vistas or senal not in por_senal:
                continue
            if vistas[senal]["hasta"] > largo - 0.1:
                continue
            opciones += [(senal, a) for a in por_senal[senal]
                         if (con_vecina or not CATALOGO[a].get("requiere_imagenes"))
                         and vistas[senal]["desde"] <= largo - CATALOGO[a].get(
                             "tiempo", TIEMPO_PARA_LEERSE)]
        if not opciones:
            sin_animar += 1
            continue
        # la misma animacion dos veces seguidas cansa: se prefiere otra si la hay
        posibles = [o for o in opciones if o[1] != ultima] or opciones
        senal = posibles[0][0]
        grupo = [a for s, a in posibles if s == senal]
        animacion = grupo[medios.desempatar(semilla, sid, "animacion") % len(grupo)]
        ficha = {"animacion": animacion, "senal": senal, "datos": vistas[senal]}
        if CATALOGO[animacion].get("requiere_imagenes"):
            ficha["imagenes"] = {"propia": imagenes[sid],
                                 "siguiente": imagenes[siguiente["id"]]}
        salida[sid] = ficha
        ultima = animacion
        sin_animar = 0
    return salida


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
                f'CONCEPTO</text>')
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
    # la palabra clave: la mas larga de las ultimas, la que cierra la idea
    clave = max(range(len(palabras)), key=lambda k: (len(_limpio(palabras[k])), k))
    piezas = [f'<rect x="{-pad:.1f}" y="{-pad*0.55:.1f}" width="{caja_w + 2*pad:.1f}" '
              f'height="{caja_h + pad*0.4:.1f}" rx="{20*u:.1f}" fill="{c["sombra"]}" '
              f'fill-opacity="0.62"/>']
    for fila, ln in enumerate(lineas):
        cursor = 0.0
        for k in ln:
            px, py = cursor, tam + fila * interlinea
            t0 = tiempos[k][0]
            if k == clave:
                piezas.append(
                    f'<rect x="{px - 10*u:.1f}" y="{py - tam*0.9:.1f}" width="0" '
                    f'height="{tam*1.15:.1f}" rx="{8*u:.1f}" fill="{c["acento"]}" '
                    f'fill-opacity="0.9">{_anim("width", 0, f"{medidas[k] + 20*u:.1f}", t0, 0.4)}</rect>')
            tinta = _sobre(c["acento"]) if k == clave else c["texto"]
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
    chip_w = tipografia.medir("CONCEPTO", FUENTE_MEDIDA, chip_t, True, 3 * u)[0] + 40 * u
    tam_n, tam_d = 50 * u, 26 * u
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
            f'letter-spacing="{3*u:.1f}" fill="#e9e6df">CONCEPTO</text></g>')
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
    entra, sale = _ventana(datos["desde"], duracion, minimo=3.6)
    cw, ch = _medidas_tarjetas(ancho, alto)
    y = 0.31 * alto
    titulo = str(datos["nombre"]).upper()
    tam = min(86 * u, 0.9 * ancho / max(6, len(titulo)) * 1.5)
    una = _tarjeta_foto("co1", ctx["imagenes"]["propia"], cw, ch, u, entra + 0.3, (-70 * u, 0), fin=sale)
    dos = _tarjeta_foto("co2", ctx["imagenes"]["siguiente"], cw, ch, u, entra + 0.95, (70 * u, 0), fin=sale)
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
    entra, sale = _ventana(datos["desde"], duracion, minimo=3.0)
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
    una = _tarjeta_foto("cp1", ctx["imagenes"]["propia"], cw, ch, u, entra + 0.3,
                        (0, 0.4 * alto), dur=0.8, fin=sale)
    dos = _tarjeta_foto("cp2", ctx["imagenes"]["siguiente"], cw, ch, u, entra + 1.3,
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


def svg_de(asignacion, duracion, salida=(1920, 1080), paleta=None):
    """El SVG de la animacion de UN plano, a tamano del cuadro de salida.

    `asignacion` es lo que devuelve `repartir` para ese plano. -> (svg, fondo):
    el SVG va encima del plano y `fondo` (o None) es lo que hay que hacerle al
    plano de debajo (ver JS_FONDO). Cadena vacia si la animacion no se sabe
    dibujar: el plano sale sin ella, que es lo que habria salido sin pedirla.
    """
    dibujar = _DIBUJANTES.get((asignacion or {}).get("animacion"))
    if not dibujar:
        return "", None
    ancho, alto = int(salida[0]), int(salida[1])
    try:
        resultado = dibujar(asignacion["datos"], float(duracion), ancho, alto,
                            _colores(paleta), asignacion)
    except (KeyError, TypeError, ValueError, IndexError):
        return "", None
    interior, fondo = resultado if isinstance(resultado, tuple) else (resultado, None)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
            f'viewBox="0 0 {ancho} {alto}">{interior}</svg>'), fondo


def capas(escenas, params=None, idioma=None, paleta=None, salida=(1920, 1080),
          imagenes=None, semilla=0):
    """Todo lo que hace falta para el render.
    -> {id_de_plano: {"svg", "animacion", "fondo", "imagenes"}}

    `imagenes` son las URL de las imagenes de cada plano; en el resultado vuelven
    las que la pagina tiene que PRECARGAR (las de las tarjetas): un <image>
    dentro de un SVG no lo espera nadie y la primera captura saldria con la
    tarjeta vacia.
    """
    reparto = repartir(escenas, params, idioma, imagenes=imagenes, semilla=semilla)
    por_id = {e.get("id"): e for e in escenas or []}
    resultado = {}
    for sid, asignacion in reparto.items():
        svg, fondo = svg_de(asignacion, _duracion(por_id[sid]), salida, paleta)
        if svg:
            resultado[sid] = {"svg": svg, "animacion": asignacion["animacion"], "fondo": fondo,
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
