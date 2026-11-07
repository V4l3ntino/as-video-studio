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
import os
import re
import sys
import tempfile
import xml.dom.minidom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
igual("una senal por animacion, sin repetirse",
      sorted(f["senal"] for f in animaciones.CATALOGO.values()), sorted(animaciones.PRIORIDAD))
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
igual("el nombre propio, a su ficha", reparto.get("S003", {}).get("animacion"), "ficha-ui")
ids = [e["id"] for e in escenas]
comprobar("nunca dos animadas seguidas",
          all(not (a in reparto and b in reparto) for a, b in zip(ids, ids[1:])))
igual("es determinista", animaciones.repartir(escenas, TODAS, "es"), reparto)
solo = animaciones.repartir(escenas, {"animaciones": ["ficha-ui"]}, "es")
igual("solo cuentan las elegidas", {v["animacion"] for v in solo.values()}, {"ficha-ui"})
cartela = dict(escenas[0], cartela={"plantilla": "titulo"})
igual("una cartela ya es texto animado: no se le pone otra",
      animaciones.repartir([cartela], TODAS, "es"), {})
igual("un plano demasiado corto se queda como esta",
      animaciones.repartir([escena(1, "El 45% de los barcos", 0, duracion=1.5)], TODAS, "es"), {})
tarde = escena(1, "Habia una vez mucha gente en el puerto esperando el 45%", 0, duracion=5.2)
igual("una senal dicha al final no llega a leerse: sin animacion",
      animaciones.repartir([tarde], TODAS, "es"), {})

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

print("\n== la pagina de render las lleva ==")
comprobar("la pagina tiene su capa", 'id="capaanim"' in p8_render.PAGINA)
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
    comprobar("no queda ningun marcador sin sustituir", "__CAPAANIM__" not in html)
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
