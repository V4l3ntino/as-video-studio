"""
Pruebas de animaciones: las de motion graphics que se pintan encima del plano.

Lo que se protege aqui, por orden de lo que costaria si se rompe:

  1. UN VIDEO QUE NO LAS PIDE SALE IGUAL. Sin el param `animaciones` el reparto
     es vacio y la capa no pinta nada: es lo que mantiene la firma del render de
     todo proyecto guardado.
  2. cada animacion se reparte donde hay algo que ensenar -- una cifra, una fecha,
     un nombre propio, una frase corta -- y NO en cualquier plano;
  3. lo que se dibuja es un SVG valido, a tamano del cuadro y con todos sus
     tiempos DENTRO del plano: SMIL fuera de rango se congela en un estado a medias;
  4. la pagina de render las lleva, y el estilo las guarda y rechaza las que no existen.

No necesita red, ni navegador, ni ffmpeg.
"""
import json
import os
import re
import sys
import tempfile
import xml.dom.minidom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Esta suite importa `app` (para pedirle la previa): los datos del estudio van a
# una carpeta temporal ANTES de cargarlo, o la salud del CLI, el onboarding y las
# estadisticas acabarian en los de verdad.
_DATOS = tempfile.mkdtemp(prefix="prueba_animaciones_")
os.environ["ESTUDIO_SECRETOS"] = os.path.join(_DATOS, "secretos")
os.environ["ESTUDIO_AJUSTES"] = os.path.join(_DATOS, "ajustes.json")
os.environ["ESTUDIO_ESTADISTICAS"] = os.path.join(_DATOS, "estadisticas.json")

import animaciones  # noqa: E402
import p8_render  # noqa: E402
import presets_canal  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fallos = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  ok   {titulo}")
    else:
        print(f"  FALLA {titulo}" + (f"   -> {detalle}" if detalle else ""))
        fallos.append(titulo)


def igual(titulo, obtenido, esperado):
    comprobar(titulo, obtenido == esperado, f"esperaba {esperado!r}, salio {obtenido!r}")


def escena(i, texto, t0, duracion=None):
    """Una escena con una marca de tiempo por palabra, como las del plan."""
    palabras, marcas, t = texto.split(), [], t0 + 0.3
    for _ in palabras:
        marcas.append([round(t, 3), round(t + 0.38, 3)])
        t += 0.42
    fin = t0 + (duracion if duracion else max(3.0, len(palabras) * 0.42 + 0.9))
    return {"id": f"S{i:03d}", "narracion": texto, "marcas": marcas,
            "t_in": float(t0), "t_out": float(fin)}


TODAS = {"animaciones": list(animaciones.CATALOGO)}

print("\n== el catalogo se sostiene ==")
for aid, ficha in animaciones.CATALOGO.items():
    comprobar(f"{aid}: sabe dibujarse", aid in animaciones._DIBUJANTES)
    comprobar(f"{aid}: su senal tiene prioridad", ficha["senal"] in animaciones.PRIORIDAD)
    comprobar(f"{aid}: ninguna entra de fabrica", ficha["defecto"] is False)
    comprobar(f"{aid}: tiene su GIF para la tarjeta",
              os.path.isfile(os.path.join(RAIZ, "web", f"anim_{aid}.gif")))
igual("cada senal tiene al menos una animacion, y ninguna pide una que no existe",
      sorted({f["senal"] for f in animaciones.CATALOGO.values()}), sorted(animaciones.PRIORIDAD))
igual("la pantalla recibe todas, marcando las elegidas",
      [f["id"] for f in animaciones.catalogo_para_pantalla(["ficha-ui"]) if f["elegida"]],
      ["ficha-ui"])

print("\n== un video que no las pide sale IGUAL ==")
muestra = [escena(1, "El 45% de los barcos nunca llegó a puerto.", 0)]
igual("sin el param no se reparte nada", animaciones.repartir(muestra, {}, "es"), {})
igual("con la lista vacia, tampoco", animaciones.repartir(muestra, {"animaciones": []}, "es"), {})
igual("ni se dibuja nada", animaciones.capas(muestra, {}, "es"), {})
igual("un id que no existe se descarta", animaciones.elegidas_de({"animaciones": ["no-existe"]}), [])
comprobar("el render la declara vacia por defecto", p8_render.PARAMS_POR_DEFECTO["animaciones"] == [])

print("\n== las senales salen de lo que se dice ==")
cifra = animaciones.senales(escena(1, "El 45% de los barcos nunca llegó a puerto.", 0), "es")
comprobar("una cifra con porcentaje es cifra", "cifra" in cifra and cifra["cifra"]["porcentaje"],
          str(cifra))
igual("y lleva su texto", cifra.get("cifra", {}).get("texto"), "45%")
anio = animaciones.senales(escena(1, "Todo cambió en 1923, cuando cayó el muro.", 0), "es")
comprobar("un año es fecha", "fecha" in anio, str(anio))
comprobar("y un año NO es una cifra", "cifra" not in anio, str(anio))
nombre = animaciones.senales(escena(1, "Entonces llegó Cristóbal Colón con tres naves.", 0), "es")
igual("un nombre propio es termino", nombre.get("termino", {}).get("nombre"), "Cristóbal Colón")
comprobar("el que abre la frase no cuenta como nombre",
          "termino" not in animaciones.senales(escena(1, "Luego vino la calma", 0), "es"))
frase = animaciones.senales(escena(1, "Nadie volvió a verlos jamás.", 0), "es")
comprobar("una frase corta es frase", "frase" in frase, str(frase))
igual("una escena sin marcas no da senal",
      animaciones.senales({"narracion": "El 45% de todo", "marcas": []}, "es"), {})
desfasada = escena(1, "El 45% de los barcos", 0)
desfasada["marcas"] = desfasada["marcas"][:-1]
igual("y si el texto y las marcas no cuadran, tampoco",
      animaciones.senales(desfasada, "es"), {})

print("\n== el reparto: donde encaja, con aire entre una y otra ==")
escenas = [escena(1, "El 45% de los barcos nunca llegó a puerto.", 0),
           escena(2, "Luego vino el año 1923, cuando todo cambió.", 5),
           escena(3, "Entonces llegó Cristóbal Colón con tres naves.", 10),
           escena(4, "Nadie volvió a verlos jamás.", 15),
           escena(5, "Solo había mar y viento y mas mar", 20)]
reparto = animaciones.repartir(escenas, TODAS, "es")
igual("la cifra se anima", reparto.get("S001", {}).get("animacion"), "infografia-cifra")
comprobar("la escena siguiente descansa", "S002" not in reparto)
comprobar("el nombre propio, a una de las que lo ensenan SIN otra imagen",
          reparto.get("S003", {}).get("animacion") in ("ficha-ui", "ficha-cristal", "etiqueta-escrita"),
          str(reparto.get("S003", {}).get("animacion")))
ids = [e["id"] for e in escenas]
comprobar("nunca dos animadas seguidas",
          all(not (a in reparto and b in reparto) for a, b in zip(ids, ids[1:])))
igual("es determinista", animaciones.repartir(escenas, TODAS, "es"), reparto)
solo = animaciones.repartir(escenas, {"animaciones": ["ficha-ui"]}, "es")
igual("solo cuentan las elegidas", {v["animacion"] for v in solo.values()}, {"ficha-ui"})
comprobar("sin imagenes de los vecinos no entra ninguna que las necesite",
          all(not animaciones.CATALOGO[v["animacion"]].get("requiere_imagenes")
              for v in reparto.values()))
cartela = dict(escenas[0], cartela={"plantilla": "titulo"})
igual("una cartela ya es texto animado: no se le pone otra",
      animaciones.repartir([cartela], TODAS, "es"), {})
igual("un plano demasiado corto se queda como esta",
      animaciones.repartir([escena(1, "El 45% de los barcos", 0, duracion=1.5)], TODAS, "es"), {})
tarde = escena(1, "Habia una vez mucha gente en el puerto esperando el 45%", 0, duracion=5.2)
igual("una senal dicha al final no llega a leerse: sin animacion",
      animaciones.repartir([tarde], TODAS, "es"), {})

print("\n== contraste: dos cosas que se oponen ==")
cont = animaciones.senales(escena(1, "Las raíces sanas crecen profundas mientras que las raíces atrofiadas apenas avanzan.", 0), "es")
igual("«mientras que» parte la frase en dos etiquetas",
      (cont.get("contraste") or {}).get("izquierda"), "RAÍCES SANAS")
igual("y la otra mitad", (cont.get("contraste") or {}).get("derecha"), "RAÍCES ATROFIADAS")
comprobar("una frase sin conector no es contraste",
          "contraste" not in animaciones.senales(escena(1, "Las raíces sanas crecen profundas hacia abajo.", 0), "es"))
comprobar("«pero» no basta: esta en media frase del mundo",
          "contraste" not in animaciones.senales(escena(1, "Era sano pero estaba cansado de todo.", 0), "es"))

print("\n== las que ensenan la imagen del plano siguiente ==")
vecinas = [escena(1, "Las raíces sanas crecen profundas mientras que las raíces atrofiadas apenas avanzan.", 0, duracion=6.0),
           escena(2, "Y despues vino la calma de siempre.", 6, duracion=4.0)]
urls = {"S001": "file:///a.png", "S002": "file:///b.png"}
con = animaciones.repartir(vecinas, {"animaciones": ["comparacion-tarjetas"]}, "es", imagenes=urls)
igual("con la imagen del vecino, la comparacion entra", con.get("S001", {}).get("animacion"), "comparacion-tarjetas")
igual("y lleva las dos imagenes", sorted((con.get("S001") or {}).get("imagenes", {})), ["otra", "propia"])
invertidas = [dict(vecinas[0], nombre_imagen="S001-camaleonagitado.png"),
             dict(vecinas[1], nombre_imagen="S002-camaleontranquilo.png")]
invertidas[0]["narracion"] = "El camaleón tranquilo descansa mientras que uno agitado se mueve."
invertidas[0]["marcas"] = [[0.3 + i * 0.4, 0.6 + i * 0.4]
                            for i in range(len(invertidas[0]["narracion"].split()))]
con_nombres = animaciones.repartir(invertidas, {"animaciones": ["comparacion-tarjetas"]},
                                  "es", imagenes=urls)
igual("los nombres antiguos no cambian el orden habitual de las etiquetas",
      con_nombres["S001"]["datos"]["izquierda"], "CAMALEÓN TRANQUILO")
igual("la otra etiqueta queda debajo de la otra foto",
      con_nombres["S001"]["datos"]["derecha"], "UNO AGITADO")
ambiguas = [dict(invertidas[0], nombre_imagen="S001-camaleon.png"), invertidas[1]]
igual("los nombres antiguos ambiguos tampoco condicionan la comparacion",
      animaciones.repartir(ambiguas, {"animaciones": ["comparacion-tarjetas"]},
                            "es", imagenes=urls), con_nombres)
igual("sin imagenes no entra",
      animaciones.repartir(vecinas, {"animaciones": ["comparacion-tarjetas"]}, "es"), {})
igual("al ultimo plano le falta vecino: tampoco",
      animaciones.repartir(vecinas[1:], {"animaciones": ["comparacion-tarjetas"]}, "es", imagenes=urls), {})
cartela_vecina = [vecinas[0], dict(vecinas[1], cartela={"plantilla": "titulo"})]
igual("si el vecino es una cartela, tampoco",
      animaciones.repartir(cartela_vecina, {"animaciones": ["comparacion-tarjetas"]}, "es", imagenes=urls), {})
nombre_vecinas = [escena(1, "Entonces llegó Cristóbal Colón con tres naves hacia el oeste.", 0, duracion=6.0),
                  escena(2, "Y despues vino la calma de siempre.", 6, duracion=4.0)]
collage = animaciones.capas(nombre_vecinas, {"animaciones": ["collage-titulo"]}, "es", None,
                            (1920, 1080), imagenes=urls)
igual("el collage se dibuja con las dos imagenes", sorted(collage.get("S001", {}).get("imagenes", [])),
      ["file:///a.png", "file:///b.png"])
comprobar("y atenua el plano de debajo", bool((collage.get("S001") or {}).get("fondo")), str(collage))
comprobar("las dos fotos estan en el SVG", (collage.get("S001") or {}).get("svg", "").count("<image") == 2)
comprobar("el titulo se escribe letra a letra",
          (collage.get("S001") or {}).get("svg", "").count("<tspan") == len("CRISTÓBAL COLÓN"))
comprobar("y el contorno del titulo tambien (sin fantasma de las que faltan)",
          'stroke-opacity="0"' in (collage.get("S001") or {}).get("svg", ""))
etiqueta = animaciones.capas(nombre_vecinas, {"animaciones": ["etiqueta-escrita"]}, "es")
fondo = (etiqueta.get("S001") or {}).get("fondo") or {}
comprobar("la etiqueta desenfoca el fondo y lo devuelve",
          fondo.get("blur", 0) > 0 and fondo["t"] == sorted(fondo["t"]), str(fondo))
cristal = animaciones.capas(nombre_vecinas, {"animaciones": ["ficha-cristal"]}, "es")
igual("la ficha de cristal no toca el fondo", (cristal.get("S001") or {}).get("fondo"), None)
igual("y sin animacion tampoco hay capa", animaciones.capas(nombre_vecinas, {}, "es"), {})
comprobar("el fondo se aplica con una funcion de t", "function aplicarFondo" in animaciones.JS_FONDO)

print("\n== lo que se dibuja ==")
capas = animaciones.capas(escenas, TODAS, "es", None, (1920, 1080))
comprobar("hay capa para cada plano repartido", set(capas) == set(reparto), str(sorted(capas)))
for sid, capa in capas.items():
    duracion = next(e["t_out"] - e["t_in"] for e in escenas if e["id"] == sid)
    try:
        xml.dom.minidom.parseString(capa["svg"])
        valido = True
    except Exception as fallo:  # noqa: BLE001
        valido = False
        print("     ", fallo)
    comprobar(f"{sid} ({capa['animacion']}): es un SVG valido", valido)
    comprobar(f"{sid}: a tamano del cuadro", 'viewBox="0 0 1920 1080"' in capa["svg"])
    tiempos = [float(x) for x in re.findall(r'begin="([0-9.]+)s"', capa["svg"])]
    comprobar(f"{sid}: todos sus tiempos caen dentro del plano ({duracion:.1f} s)",
              bool(tiempos) and max(tiempos) <= duracion, f"max={max(tiempos or [0])}")
vertical = animaciones.capas(escenas, TODAS, "es", None, (1080, 1920))
comprobar("en vertical tambien se dibujan",
          vertical and all('viewBox="0 0 1080 1920"' in c["svg"] for c in vertical.values()))
igual("el texto se escapa", animaciones._esc('a<b & "c"'), "a&lt;b &amp; &quot;c&quot;")

print("\n== el plan, ANTES de escribir el guion ==")
todas_ids = list(animaciones.CATALOGO)
plan = animaciones.plan_de_huecos(todas_ids, 240, 36, semilla=3)
igual("cada animacion elegida tiene al menos un hueco",
      {h["animacion"] for h in plan}, set(todas_ids))
comprobar("los huecos caen entre el segundo bloque y el penultimo",
          all(2 <= h["bloque"] <= 35 for h in plan), str([h["bloque"] for h in plan]))
comprobar("y en bloques distintos y en orden",
          [h["bloque"] for h in plan] == sorted({h["bloque"] for h in plan}))
comprobar("nunca la misma animacion dos veces seguidas",
          all(a["animacion"] != b["animacion"] for a, b in zip(plan, plan[1:])))
igual("es determinista", animaciones.plan_de_huecos(todas_ids, 240, 36, semilla=3), plan)
igual("sin animaciones elegidas no hay plan", animaciones.plan_de_huecos([], 240, 36), [])
igual("ni con un video de dos bloques", animaciones.plan_de_huecos(todas_ids, 30, 2), [])
largo = animaciones.plan_de_huecos(["ficha-ui", "editorial-fecha"], 600, 80)
comprobar("un video largo repite rotando, sin pasarse de 3 veces cada una",
          len(largo) > 2 and all(sum(h["animacion"] == a for h in largo) <= 3
                                 for a in ("ficha-ui", "editorial-fecha")), str(len(largo)))
instruccion = animaciones.bloque_para_guion(plan, 36)
comprobar("la instruccion nombra cada animacion y su id",
          all(f'id "{a}"' in instruccion.replace("(", "").replace(")", "") or f'"{a}"' in instruccion
              for a in todas_ids))
comprobar("pide marcar el bloque y no inventar datos",
           '"animacion"' in instruccion and "NUNCA inventes" in instruccion)
comprobar("el texto se redacta para la animacion y selecciona un fragmento literal",
          "REDACTA ese bloque a partir" in instruccion and
          '"animacion_texto"' in instruccion and "comparación DE VERDAD" in instruccion)
igual("sin plan no hay instruccion", animaciones.bloque_para_guion([], 36), "")

import p3_guion  # noqa: E402
opciones_g = p3_guion._normalizar({"animaciones": ["ficha-ui", "comparacion-tarjetas"]})
igual("el guion guarda las que existen", opciones_g["animaciones"], ["ficha-ui", "comparacion-tarjetas"])
try:
    p3_guion._normalizar({"animaciones": ["nada"]})
    comprobar("el guion rechaza una animacion que no existe", False)
except ValueError:
    comprobar("el guion rechaza una animacion que no existe", True)
igual("sin animaciones, el guion no cambia", p3_guion._normalizar({})["animaciones"], [])
brief_g = {"instrucciones": "", "idioma_salida_nombre": "espanol", "presupuesto_palabras": 600,
           "margen": {"minimo": 500, "maximo": 700}, "palabras_por_bloque": 30,
           "duracion_objetivo_s": 240, "bloques_estimados": 20}
transcript_g = [{"t_in": 0, "t_out": 4, "texto": "Material de ejemplo."}]
meta_g = {"titulo": "Prueba", "palabras_transcript": 3, "sin_tiempos": True}
con_plan = p3_guion._instruccion(transcript_g, meta_g, brief_g, None, opciones_g, [], "es")
sin_plan = p3_guion._instruccion(transcript_g, meta_g, brief_g, None, p3_guion._normalizar({}), [], "es")
comprobar("con animaciones elegidas la instruccion las pide, repartidas",
          "ANIMACIONES GRAFICAS" in con_plan and "hacia el bloque" in con_plan)
comprobar("y sin ellas la instruccion no cambia", "ANIMACIONES GRAFICAS" not in sin_plan)
comprobar("el modelo sabe como marcar el bloque", '"animacion": "<id de la lista>"' in con_plan)
bloques_n = p3_guion._normalizar_bloques({"bloques": [
    {"id": "B001", "texto": "uno"}, {"id": "B002", "texto": "dos", "animacion": " ficha-ui "}]})
igual("el redactor marca un bloque y se recoge su id", bloques_n[1]["animacion"], "ficha-ui")
igual("y el que no lo marca queda vacio", bloques_n[0]["animacion"], "")
comprobar("se le pide a Claude el fragmento visible de cada animacion",
          '"animacion_texto"' in con_plan and "Universidad de Ginebra" in con_plan)
eleccion = p3_guion._normalizar_bloques({"bloques": [
    {"id": "B002", "texto": "Investigadores de la Universidad de Ginebra descubrieron algo.",
     "animacion": "etiqueta-escrita", "animacion_texto": "Universidad de Ginebra"}]})
animaciones.validar_textos(eleccion, "es")
igual("Claude puede elegir el nombre completo y se conserva", eleccion[0].get("animacion_texto"),
      "Universidad de Ginebra")
eleccion[0]["animacion_texto"] = "Universidad de Oxford"
animaciones.validar_textos(eleccion, "es")
comprobar("una frase inventada no se conserva", "animacion_texto" not in eleccion[0])
universidad = escena(5, "Investigadores de la Universidad de Ginebra descubrieron algo.", 0, 6)
universidad["origen"] = {"bloque": "B002"}
url_universidad = {"S005": "file:///foto.png"}
for tipo in ("ficha-ui", "ficha-cristal", "etiqueta-escrita"):
    seleccionado = animaciones.repartir([universidad], {"animaciones": [tipo]}, "es",
        imagenes=url_universidad, etiquetas={"B002": tipo},
        textos={"B002": "Universidad de Ginebra"})
    igual(f"{tipo}: se muestra el nombre que eligio Claude",
          seleccionado.get("S005", {}).get("datos", {}).get("nombre"), "Universidad de Ginebra")
igual("el nombre completo tambien se reconoce en guiones anteriores",
      animaciones.senales(universidad, "es")["termino"]["nombre"], "Universidad de Ginebra")
dos_nombres = escena(11, "La Universidad de Ginebra publicó en Nature Communications el estudio.", 0, 7)
dos_nombres["origen"] = {"bloque": "B011"}
eleccion_nombre = [{"texto": dos_nombres["narracion"], "animacion": "collage-titulo",
                    "animacion_texto": "Nature Communications"}]
animaciones.validar_textos(eleccion_nombre, "es")
igual("Claude puede escoger el segundo nombre propio del mismo plano",
      eleccion_nombre[0].get("animacion_texto"), "Nature Communications")
elegido_nombre = animaciones.repartir([dos_nombres, escena(12, "Y continuó.", 7)],
    {"animaciones": ["collage-titulo"]}, "es", imagenes={"S011": "a", "S012": "b"},
    etiquetas={"B011": "collage-titulo"}, textos={"B011": "Nature Communications"})
igual("el titulo sigue la seleccion de Claude y no el nombre mas largo",
      elegido_nombre.get("S011", {}).get("datos", {}).get("nombre"), "Nature Communications")
igual("no se sustituye en silencio una seleccion de Claude que no aparece en el plano",
       animaciones.repartir([universidad], {"animaciones": ["etiqueta-escrita"]}, "es",
           etiquetas={"B002": "etiqueta-escrita"}, textos={"B002": "Universidad de Oxford"}), {})
concepto = {"id": "B002", "texto": "Aquí aparece la fotosíntesis, que convierte la luz en energía.",
            "animacion": "ficha-ui", "animacion_texto": "fotosíntesis"}
animaciones.etiquetar_bloques([concepto], ["ficha-ui"], [], "es")
animaciones.validar_textos([concepto], "es")
igual("la ficha conserva un concepto sin nombre propio elegido en el guion",
      (concepto.get("animacion"), concepto.get("animacion_texto", "").rstrip(",")),
      ("ficha-ui", "fotosíntesis"))
plano_concepto = escena(5, concepto["texto"], 0, 6)
plano_concepto["origen"] = {"bloque": "B002"}
reparto_concepto = animaciones.repartir([plano_concepto], {"animaciones": ["ficha-ui"]}, "es",
    etiquetas={"B002": "ficha-ui"}, textos={"B002": "fotosíntesis"})
igual("la ficha muestra la palabra clave de la narración, no otra",
      reparto_concepto["S005"]["datos"]["nombre"], "fotosíntesis")
for tipo, texto, fragmento, campo, esperado in (
    ("infografia-cifra", "El 45% de los barcos quedó atrás.", "45% de los barcos",
     "texto", "45%"),
    ("editorial-fecha", "Todo cambió en 1923, cuando cayó el muro.", "1923, cuando cayó el muro",
     "texto", "1923"),
    ("tipografia-cinetica", "Nadie volvió a verlos jamás.", "Nadie volvió a verlos jamás",
     "palabras", ["Nadie", "volvió", "a", "verlos", "jamás."]),
    ("comparacion-tarjetas", "Las raíces sanas crecen mientras que las atrofiadas mueren.",
     "raíces sanas crecen mientras que las atrofiadas mueren", "izquierda", "RAÍCES SANAS")):
    bloque = {"texto": texto, "animacion": tipo, "animacion_texto": fragmento}
    animaciones.validar_textos([bloque], "es")
    comprobar(f"{tipo}: Claude puede elegir el texto relevante", bool(bloque.get("animacion_texto")))
    e = escena(9, texto, 0, 7)
    e["origen"] = {"bloque": "B009"}
    vecino = escena(10, "Y la historia siguió.", 7, 4)
    elegido = animaciones.repartir([e, vecino], {"animaciones": [tipo]}, "es",
        imagenes={"S009": "a", "S010": "b"}, etiquetas={"B009": tipo},
        textos={"B009": bloque.get("animacion_texto")})
    igual(f"{tipo}: el plano usa el fragmento elegido", elegido["S009"]["datos"][campo], esperado)

for texto, fragmento, esperado in (
    ("Todo cambió en mil novecientos veintitrés, cuando cayó el muro.",
     "mil novecientos veintitrés", "1923"),
    ("La historia empezó el cinco de mayo, con la llegada del barco.",
     "cinco de mayo", "5 MAYO")):
    bloque = {"texto": texto, "animacion": "editorial-fecha", "animacion_texto": fragmento}
    animaciones.validar_textos([bloque], "es")
    igual("la fecha escrita con letras conserva la selección del guion",
          bloque.get("animacion_texto", "").rstrip(","), fragmento)
    e = escena(9, texto, 0, 8)
    e["origen"] = {"bloque": "B009"}
    reparto = animaciones.repartir([e], {"animaciones": ["editorial-fecha"]}, "es",
        etiquetas={"B009": "editorial-fecha"}, textos={"B009": fragmento})
    igual("la banda convierte lo dicho a fecha visible sin perder el reloj",
          reparto["S009"]["datos"]["texto"], esperado)

print("\n== etiquetar los bloques: lo marcado, lo rescatado y lo que no cabe ==")
bl = [{"id": f"B{i:03d}", "texto": t} for i, t in enumerate([
    "Un gancho sin nada concreto.",
    "El 45 por ciento de los barcos nunca llegó a puerto.",
    "Luego, en 1923, cayó el muro.",
    "Las raíces sanas crecen profundas mientras que las raíces atrofiadas apenas avanzan.",
    "Entonces llegó Cristóbal Colón con tres naves.",
    "Nadie volvió.",
    "El cierre del video."], 1)]
bl[1]["animacion"] = "infografia-cifra"        # marcada y bien
bl[2]["animacion"] = "comparacion-tarjetas"    # marcada, pero ahi no hay comparacion
avisos_b = animaciones.etiquetar_bloques(
    bl, ["infografia-cifra", "editorial-fecha", "comparacion-tarjetas", "ficha-ui", "collage-titulo"],
    plan, "es")
por_bloque = {b["id"]: b.get("animacion") for b in bl}
igual("lo que el redactor marco bien se respeta", por_bloque["B002"], "infografia-cifra")
comprobar("una marca sin frase que la sostenga se quita", por_bloque["B003"] != "comparacion-tarjetas")
igual("la comparacion se rescata en el bloque que SI la dice", por_bloque["B004"], "comparacion-tarjetas")
comprobar("la fecha se rescata aunque quede pegada a otra",
          "editorial-fecha" in por_bloque.values(), str(por_bloque))
comprobar("lo rescatado se dice en los avisos", any("se ha colocado" in a for a in avisos_b))
comprobar("el gancho y el cierre no llevan animacion", por_bloque["B001"] is None and por_bloque["B007"] is None)
comprobar("una animacion que el texto no puede sostener se avisa por su nombre",
          any("Collage con título" in a and "no saldra" in a for a in avisos_b) or
          "collage-titulo" in por_bloque.values(), str(avisos_b))
sueltos = [{"id": "B001", "texto": "algo", "animacion": "ficha-ui"}]
animaciones.etiquetar_bloques(sueltos, [], [], "es")
comprobar("sin animaciones elegidas se limpian las marcas", "animacion" not in sueltos[0])

print("\n== el reparto sigue lo previsto, y rescata lo que falte ==")
escenas_p = [escena(1, "Un gancho sin nada.", 0), escena(2, "El 45% de los barcos nunca llegó.", 6),
             escena(3, "Y asi siguio la historia de siempre.", 12),
             escena(4, "Todo cambió en 1923, cuando cayó el muro.", 18),
             escena(5, "Fin del recorrido de hoy.", 24)]
for i, e in enumerate(escenas_p):
    e["origen"] = {"bloque": f"B{i + 1:03d}"}
urls_p = {e["id"]: f"file:///{e['id']}.png" for e in escenas_p}
prev = animaciones.repartir(escenas_p, {}, "es", imagenes=urls_p, etiquetas={"B002": "infografia-cifra"})
igual("con etiquetas solo sale lo previsto", {k: v["animacion"] for k, v in prev.items()},
      {"S002": "infografia-cifra"})
resc = animaciones.repartir(escenas_p, {"animaciones": ["editorial-fecha"]}, "es", imagenes=urls_p,
                            etiquetas={"B002": "infografia-cifra"})
igual("una elegida sin etiqueta se rescata donde el texto la dice",
      {k: v["animacion"] for k, v in resc.items()}, {"S002": "infografia-cifra", "S004": "editorial-fecha"})
cob = animaciones.cobertura(resc, ["infografia-cifra", "editorial-fecha", "ficha-ui"])
igual("la cobertura dice cual falta", cob["faltan"], ["ficha-ui"])
igual("y cuantas salen", cob["colocadas"], {"infografia-cifra": 1, "editorial-fecha": 1})
bloque_equivocado = animaciones.repartir(escenas_p, {}, "es", imagenes=urls_p,
                                         etiquetas={"B003": "infografia-cifra"})
igual("una etiqueta en un bloque sin la frase se rescata donde SI hay cifra",
      {k: v["animacion"] for k, v in bloque_equivocado.items()}, {"S002": "infografia-cifra"})
tarjetas = [escena(1, "Las raíces sanas crecen mientras que las atrofiadas mueren pronto.", 0),
            escena(2, "Y asi termina.", 6)]
for i, e in enumerate(tarjetas):
    e["origen"] = {"bloque": f"B{i + 1:03d}"}
ult = animaciones.repartir(tarjetas[::-1], {}, "es", imagenes={"S001": "a", "S002": "b"},
                           etiquetas={"B001": "comparacion-tarjetas"})
igual("las tarjetas usan la escena de al lado (la anterior si no hay siguiente)",
      (ult.get("S001") or {}).get("elementos"), {"propia": "S001", "otra": "S002"})
igual("y con un solo plano sin vecina no entran",
       animaciones.repartir(tarjetas[:1], {}, "es", imagenes={"S001": "a"},
                            etiquetas={"B001": "comparacion-tarjetas"}), {})
for tipo, texto in (("collage-titulo", "Entonces llegó Cristóbal Colón con tres naves."),
                    ("comparacion-tarjetas", "Las raíces sanas crecen mientras que las atrofiadas mueren pronto.")):
    entrada = escena(7, texto, 0, 8.5)
    entrada["origen"] = {"bloque": "B007"}
    vecina = escena(8, "A continuación vemos el resultado.", 8.5, 4)
    foto = {"S007": "file:///a.png", "S008": "file:///b.png"}
    capa = animaciones.capas([entrada, vecina], {"animaciones": [tipo]}, "es",
                             imagenes=foto, etiquetas={"B007": tipo})["S007"]
    igual(f"{tipo} empieza a atenuar desde el inicio del plano", capa["fondo"]["t"][0], 0.0)
    comprobar(f"{tipo} deja entrar la primera foto desde el segundo cero",
              'begin="0.000s"' in capa["svg"])
    igual(f"{tipo} mantiene el fondo hasta el final de una escena larga",
          capa["fondo"]["t"][2], 8.5)
    salidas = [float(t) for t in re.findall(
        r'<animate\b[^>]*attributeName="opacity" from="1" to="0" begin="([0-9.]+)s"',
        capa["svg"])]
    comprobar(f"{tipo} no oculta fotos ni titulo antes del ultimo fotograma",
              bool(salidas) and all(t == 8.5 for t in salidas), str(salidas))

print("\n== la previa lleva la animacion de cada escena ==")
comprobar("el instante de reposo cae despues de las entradas y antes de la salida",
          0 < animaciones.pico_de(capas["S001"]["svg"], 6.0) < 6.0,
          str(animaciones.pico_de(capas["S001"]["svg"], 6.0)))
comprobar("un SVG sin animar descansa en 0", animaciones.pico_de("<svg/>", 6.0) == 0.0)
igual("el pico viaja con la capa", capas["S001"]["pico"], animaciones.pico_de(capas["S001"]["svg"], 6.0))
with open(os.path.join(RAIZ, "web", "app.js"), encoding="utf-8") as fh:
    js = fh.read()
quitar = lambda t: re.sub(r"\s+", "", t)  # noqa: E731
comprobar("la previa aplica el fondo con LA MISMA funcion que el render",
          quitar(animaciones.JS_FONDO) in quitar(js))
comprobar("y la pantalla sabe pintar la animacion", "function animarPrevia" in js and "previa-anim" in js)
sys.path.insert(0, RAIZ)
import _proyecto_animaciones as juguete  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402
import app as servidor  # noqa: E402
with tempfile.TemporaryDirectory(prefix="previa_anim_") as carpeta_previa:
    proyecto, estado = juguete.construir(carpeta_previa)
    ctx = SimpleNamespace(proyecto=proyecto, estado=estado, bitacora=MagicMock())
    with patch.object(servidor, "contexto", return_value=ctx), \
            patch.object(servidor, "_audio_de_la_toma", return_value=None):
        previa = servidor.leer_previsualizacion(proyecto.id)
    por_id = {e["id"]: e for e in previa["escenas"]}
    marcadas = {sid: (e.get("animacion") or {}).get("id") for sid, e in por_id.items()}
    igual("la previa pone LO QUE EL GUION DEJO MARCADO en cada bloque", marcadas, {
        "S001": "infografia-cifra", "S002": "editorial-fecha", "S003": "collage-titulo",
        "S004": "comparacion-tarjetas", "S005": "tipografia-cinetica"})
    comprobar("y su svg, su nombre y su instante de reposo",
              all((por_id["S001"].get("animacion") or {}).get(k) for k in ("svg", "nombre", "pico")))
    igual("las de tarjetas dicen con que otro elemento se hacen",
          (por_id["S003"].get("animacion") or {}).get("elementos"), {"propia": "S003", "otra": "S004"})
    igual("la ultima comparte con la anterior si no hay siguiente",
          (por_id["S004"].get("animacion") or {}).get("elementos"), {"propia": "S004", "otra": "S005"})
    resumen = previa["animaciones"]
    igual("la previa dice cuales de las elegidas NO han encontrado sitio", resumen["faltan"], ["ficha-ui"])
    igual("y cuantas se han colocado", sum(resumen["colocadas"].values()), 5)
    comprobar("con su nombre para poder decirlo", resumen["nombres"]["ficha-ui"] == "Ficha de concepto")
    comprobar("las tarjetas con otra imagen llevan su ruta del proyecto, no una URL",
              "proyecto://pasos/assets/v1/escenas/" in (por_id["S003"].get("animacion") or {}).get("svg", ""))
    comprobar("y el navegador puede completarlas (la ruta existe)", all(
        os.path.isfile(os.path.join(proyecto.raiz, *p.split("proyecto://")[1].split('"')[0].split("/")))
        for e in por_id.values() for p in (e.get("animacion") or {}).get("svg", "").split(" ")
        if p.startswith('href="proyecto://')))
    estado.actualizar_params("guion", {"animaciones": []})
    with patch.object(servidor, "contexto", return_value=ctx), \
            patch.object(servidor, "_audio_de_la_toma", return_value=None):
        sin = servidor.leer_previsualizacion(proyecto.id)
    comprobar("las etiquetas del guion siguen mandando aunque se vacie la eleccion",
              sum(1 for e in sin["escenas"] if "animacion" in e) == 5)

with tempfile.TemporaryDirectory(prefix="previa_anim_antes_") as carpeta_antes:
    # UN VIDEO DE ANTES DEL PLAN: sin etiquetas en el guion y con las animaciones en
    # los params del render. Sigue repartiendose por lo que se dice.
    proyecto, estado = juguete.construir(carpeta_antes, animaciones=[], etiquetas={})
    estado.actualizar_params("render", {"animaciones": ["infografia-cifra", "editorial-fecha"]})
    ctx = SimpleNamespace(proyecto=proyecto, estado=estado, bitacora=MagicMock())
    with patch.object(servidor, "contexto", return_value=ctx), \
            patch.object(servidor, "_audio_de_la_toma", return_value=None):
        antes = servidor.leer_previsualizacion(proyecto.id)
    por_id = {e["id"]: (e.get("animacion") or {}).get("id") for e in antes["escenas"]}
    comprobar("un video de antes del plan reparte por lo que se dice (con aire entre dos)",
              por_id["S001"] == "infografia-cifra" and por_id["S002"] is None, str(por_id))
    estado.actualizar_params("render", {"animaciones": []})
    with patch.object(servidor, "contexto", return_value=ctx), \
            patch.object(servidor, "_audio_de_la_toma", return_value=None):
        vacio = servidor.leer_previsualizacion(proyecto.id)
    comprobar("sin nada elegido la previa sale como siempre",
              all("animacion" not in e for e in vacio["escenas"]) and vacio["animaciones"] is None)

print("\n== editar y crear animaciones por escena sin regenerar recursos ==")
with tempfile.TemporaryDirectory(prefix="editor_anim_") as carpeta_editor:
    proyecto, estado = juguete.construir(carpeta_editor, animaciones=[], etiquetas={})
    # Con unidades declaradas el núcleo detecta los mapas globales indexados
    # por escena. Un juguete sin este bloque ocultaba el fallo de producción.
    estado.actualizar_params("render", {"unidades": {
        "escena:S001": {"ajuste_previo": "conservar"}, "escena:S002": {}, "escena:S009": {}}})
    firma_global = estado.firma_global("render")
    firma_vecina = estado.firma_unidad("render", "escena:S002")
    gestor = MagicMock()
    gestor.listar.return_value = []
    ctx = SimpleNamespace(proyecto=proyecto, estado=estado, gestor=gestor)
    with patch.object(servidor, "contexto", return_value=ctx), \
            patch.object(servidor, "_audio_de_la_toma", return_value=None):
        anteriores = {p: estado.params(p) for p in ("guion", "voz", "assets", "callouts", "render")}
        editor = servidor.leer_animacion_escena(proyecto.id, "S001")
        igual("abrir el editor no escribe defaults", {p: estado.params(p) for p in anteriores}, anteriores)
        igual("una escena vacia ofrece todo el catalogo", [o["id"] for o in editor["opciones"]],
              ["sin-animacion", *animaciones.CATALOGO])
        for opcion in editor["opciones"]:
            if opcion["id"] == "sin-animacion":
                continue
            edicion = {"id": opcion["id"], "contenido": dict(opcion["contenido"]), "ancla": editor["ancla"]}
            resultado = servidor.editar_animacion_escena(proyecto.id, "S001", edicion)
            hecha = resultado["escenas"][0].get("animacion") or {}
            igual(f"crear/cambiar a {opcion['id']} llega a la previa", hecha.get("id"), opcion["id"])
            ctx.estado = estado = type(estado)(proyecto)
            leida = servidor.leer_animacion_escena(proyecto.id, "S001")["actual"]
            igual(f"{opcion['id']} conserva su contenido al reabrir", leida["contenido"], hecha["contenido"])
            xml.dom.minidom.parseString(hecha["svg"])
            igual(f"{opcion['id']} no cambia la firma global", estado.firma_global("render"), firma_global)
            igual(f"{opcion['id']} no invalida otra escena", estado.firma_unidad("render", "escena:S002"), firma_vecina)
            igual("conserva los otros ajustes de la unidad",
                  estado.params("render")["unidades"]["escena:S001"]["ajuste_previo"], "conservar")
        igual("editar solo cambia params de render",
              {p: estado.params(p) for p in anteriores if p != "render"},
              {p: v for p, v in anteriores.items() if p != "render"})
        edicion = {"id": "ficha-cristal", "ancla": editor["ancla"],
                   "contenido": {"etiqueta": "NOMBRE", "nombre": "Megalosaurus <grande>",
                                 "definicion": "Una explicación corregida & propia."}}
        resultado = servidor.editar_animacion_escena(proyecto.id, "S001", edicion)
        svg = resultado["escenas"][0]["animacion"]["svg"]
        comprobar("los tres textos editados llegan al SVG y se escapan",
                  all(t in svg for t in ("NOMBRE", "Megalosaurus &lt;grande&gt;", "corregida &amp; propia")))
        plan = servidor._plan_de_previsualizacion(ctx)
        capas_manuales = animaciones.capas(plan["escenas"], estado.params("render"), salida=(1280, 720))
        igual("el motor del render produce exactamente el SVG de la previa", capas_manuales["S001"]["svg"], svg)
        # Un MP4 anterior ya tiene clips: remontar debe volver a dibujar la
        # animación editada, no confundir ids de animación con ids de unidades.
        trabajo_render = proyecto.ruta_trabajo("render")
        os.makedirs(os.path.join(trabajo_render, "clips"), exist_ok=True)
        movimientos = []
        for e in plan["escenas"]:
            with open(os.path.join(trabajo_render, "clips", e["id"] + ".mp4"), "wb") as fh:
                fh.write(b"clip anterior")
            movimientos.append({"id": e["id"], "ventana_ini": [0, 0, 1, 1],
                                "ventana_fin": [0, 0, 1, 1], "capa": "ausente.svg",
                                "hyperframe": proyecto.ruta_paso("assets", 1) + "/escenas/" + e["id"] + ".png"})
        ruta_mov = os.path.join(carpeta_editor, "movimiento.json")
        with open(ruta_mov, "w", encoding="utf-8") as fh:
            json.dump({"movimientos": movimientos}, fh)
        params_render = dict(estado.params("render"), movimiento=ruta_mov, sonido=False,
                             lotes=1, transiciones=[])
        capturadas = []

        def capturar_lote(tareas, *args, **kwargs):
            capturadas.extend(tareas)
            return [{"id": t["id"], "frames": t["frames"]} for t in tareas]

        with patch.object(p8_render.medios, "sembrar_trabajo", return_value=trabajo_render), \
                patch.object(p8_render, "correr_lote", side_effect=capturar_lote), \
                patch.object(p8_render.transiciones, "resolver", return_value={}), \
                patch.object(p8_render, "_elegir_codec", return_value="libx264"), \
                patch.object(p8_render, "_concatenar"), \
                patch.object(p8_render.medios, "duracion_media", return_value=30):
            montado = p8_render.ejecutar(proyecto, params_render)
            igual("un montaje completo rehace los clips existentes", len(capturadas), len(plan["escenas"]))
            igual("la animacion corregida llega a la tarea real de render", capturadas[0]["capa_anim"], svg)
            igual("el montaje sella las unidades rehechas", len(montado["unidades"]), len(plan["escenas"]))
            capturadas.clear()
            p8_render.ejecutar(proyecto, params_render, unidades=["escena:S001"])
            igual("rehacer una escena respeta los ids de unidad", [t["id"] for t in capturadas], ["S001"])
        antes = estado.params("render")
        for mala in (dict(edicion, id="no-existe"), dict(edicion, ancla="otro texto"),
                     dict(edicion, contenido={"nombre": "incompleto"}),
                     {"id": "infografia-cifra", "ancla": editor["ancla"],
                      "contenido": {"texto": "no es una cifra", "etiqueta": "dato"}}):
            try:
                servidor.editar_animacion_escena(proyecto.id, "S001", mala)
                comprobar("rechaza una edicion invalida", False)
            except servidor.ErrorApi:
                igual("un error conserva lo guardado", estado.params("render"), antes)
        gestor.listar.return_value = ["trabajo activo"]
        try:
            servidor.editar_animacion_escena(proyecto.id, "S001", edicion)
            comprobar("no edita durante un trabajo activo", False)
        except servidor.ErrorApi:
            igual("no edita durante un trabajo activo", estado.params("render"), antes)
        escena_cambiada = dict(plan["escenas"][0], narracion="Una escena diferente.")
        igual("no reutiliza una edicion si el id pasa a otra frase",
              animaciones.capas([escena_cambiada], estado.params("render")), {})
        gestor.listar.return_value = []
        escena_nueve = dict(plan["escenas"][0], id="S009")
        firma_uno = estado.firma_unidad("render", "escena:S001")
        firma_nueve = estado.firma_unidad("render", "escena:S009")
        with patch.object(servidor, "_plan_de_previsualizacion", return_value=dict(plan, escenas=[escena_nueve])):
            resultado = servidor.editar_animacion_escena(proyecto.id, "S009", edicion)
            igual("S009 se guarda con unidades ya declaradas", resultado["escenas"][0]["animacion"]["id"], "ficha-cristal")
            comprobar("la firma de S009 cambia al asignar animación",
                      estado.firma_unidad("render", "escena:S009") != firma_nueve)
            igual("guardar S009 no cambia S001", estado.firma_unidad("render", "escena:S001"), firma_uno)
            igual("guardar S009 no cambia la firma global", estado.firma_global("render"), firma_global)
            comprobar("no hay un mapa de escenas en params globales", "animaciones_escenas" not in estado.params("render"))
        sin_animacion = {"id": "sin-animacion", "ancla": editor["ancla"], "contenido": {}}
        resultado = servidor.editar_animacion_escena(proyecto.id, "S001", sin_animacion)
        comprobar("Sin animación quita la asignación manual de la previa", "animacion" not in resultado["escenas"][0])
        ctx.estado = estado = type(estado)(proyecto)
        igual("al reabrir la escena sigue sin animación",
              servidor.leer_animacion_escena(proyecto.id, "S001")["actual"], None)
        params_auto = dict(estado.params("render"), animaciones=["infografia-cifra"])
        automaticas = animaciones.capas(plan["escenas"], {"animaciones": ["infografia-cifra"]})
        comprobar("el plano tenía una animación automática", "S001" in automaticas)
        comprobar("la elección Sin animación impide que reaparezca al montar",
                  "S001" not in animaciones.capas(plan["escenas"], params_auto))
        igual("quitar la animación no cambia la firma global", estado.firma_global("render"), firma_global)
        servidor.editar_animacion_escena(proyecto.id, "S001", edicion)
        comprobar("se puede volver a asignar una animación después de quitarla",
                  servidor.leer_animacion_escena(proyecto.id, "S001")["actual"]["id"] == "ficha-cristal")

print("\n== la pagina de render las lleva ==")
comprobar("la pagina tiene su capa", 'id="capaanim"' in p8_render.PAGINA)
comprobar("y aplica el fondo con el mismo reloj", "aplicarFondo(camara, FONDOANIM, t)" in p8_render.PAGINA)
comprobar("y la mueve con el mismo reloj", "svgAnim.setCurrentTime(t)" in p8_render.PAGINA)
with tempfile.TemporaryDirectory() as carpeta:
    mov = {"ventana_ini": [0, 0, 1, 1], "ventana_fin": [0, 0, 1, 1]}
    destino = os.path.join(carpeta, "escena.html")
    svg = capas["S001"]["svg"]
    p8_render._pagina_de({"t_in": 0, "t_out": 5}, mov, "", "fondo.png",
                         {"resolucion": [1920, 1080]}, destino, capa_anim=svg)
    with open(destino, encoding="utf-8") as fh:
        html = fh.read()
    comprobar("la capa de animacion llega a la pagina", svg in html)
    comprobar("no queda ningun marcador sin sustituir",
              not re.search(r"__(CAPAANIM|FONDOANIM|JSFONDO|PRECARGA)__", html))
    comprobar("sin fondo que aplicar, la pagina no toca el plano", "const FONDOANIM = null;" in html)
    p8_render._pagina_de({"t_in": 0, "t_out": 5}, mov, "", "fondo.png",
                         {"resolucion": [1920, 1080]}, destino, capa_anim=svg,
                         fondo_anim={"t": [0, 1, 4, 5], "blur": 6, "luz": 0.5},
                         precarga=["file:///x.png"])
    with open(destino, encoding="utf-8") as fh:
        html2 = fh.read()
    comprobar("con fondo, lo lleva", '"blur": 6' in html2)
    comprobar("y precarga las imagenes de las tarjetas", '<img src="file:///x.png">' in html2)
    p8_render._pagina_de({"t_in": 0, "t_out": 5}, mov, "", "fondo.png",
                         {"resolucion": [1920, 1080]}, destino)
    with open(destino, encoding="utf-8") as fh:
        comprobar("sin animacion la capa va vacia", '<div id="capaanim"></div>' in fh.read())

print("\n== el estilo las guarda ==")
limpio = presets_canal._limpiar_datos("montaje", {"animaciones": ["ficha-ui", "editorial-fecha"]})
igual("un estilo guarda las que existen", limpio["animaciones"], ["ficha-ui", "editorial-fecha"])
for malo, por_que in ((["nada"], "una que no existe"), ("ficha-ui", "algo que no es una lista")):
    try:
        presets_canal._limpiar_datos("montaje", {"animaciones": malo})
        comprobar(f"se rechaza {por_que}", False)
    except presets_canal.ErrorPreset:
        comprobar(f"se rechaza {por_que}", True)
comprobar("el montaje declara la clave", "animaciones" in presets_canal.TIPOS["montaje"]["claves"])

print()
if fallos:
    print(f"FALLARON {len(fallos)} comprobaciones:")
    for f in fallos:
        print(f"  - {f}")
    raise SystemExit(1)
print("ANIMACIONES OK: todo en orden")
