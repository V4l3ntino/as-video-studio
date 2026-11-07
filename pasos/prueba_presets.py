"""
Presets de canal: guardar, aplicar, apartar y borrar.

Lo que hay que dejar clavado aqui, porque son las tres cosas que si se rompen se
rompen en silencio:

  COPIAR      aplicar un preset copia sus VALORES a los params del paso que
              toque; no se guarda su nombre en ningun sitio. Es lo que hace que
              borrar un preset no pueda romper un video ya terminado.

  FUSIONAR    el estilo vive dentro de assets.estilo, junto al prompt escrito a
              mano de los proyectos antiguos. Escribir ese diccionario entero
              sin mirar lo que habia se llevaria el prompt por delante sin
              decirlo.

  EL BANCO    los fotogramas de un preset de estilo se COPIAN a
              banco/presets/<id>/. Si apuntaran a los del proyecto donde se
              creo, extraer estilo otra vez alli borra esa carpeta entera y el
              preset se queda apuntando a ficheros que ya no estan.

No hay red, ni CLI, ni proyecto de verdad: todo es determinista.

    C:\\IA\\venvs\\cartoon\\Scripts\\python.exe C:\\IA\\estudio\\pasos\\prueba_presets.py
"""
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "pasos"))

import presets_canal as presets  # noqa: E402

CARPETA = os.path.join(tempfile.gettempdir(), "estudio_prueba_presets")

_fallos = []
_comprobaciones = [0]


def ok(condicion, mensaje):
    _comprobaciones[0] += 1
    if not condicion:
        _fallos.append(mensaje)
        print(f"    FALLO: {mensaje}")
    else:
        print(f"  ok   {mensaje}")
    return bool(condicion)


def igual(obtenido, esperado, mensaje):
    return ok(obtenido == esperado, f"{mensaje} (obtenido {obtenido!r}, "
                                    f"esperado {esperado!r})")


def revienta(tarea, trozo, mensaje):
    """Comprueba que algo falla RUIDOSAMENTE y que el mensaje dice que falta."""
    try:
        tarea()
    except presets.ErrorPreset as fallo:
        return ok(trozo.lower() in str(fallo).lower(),
                  f"{mensaje} (dice: {str(fallo)[:80]})")
    except Exception as fallo:  # noqa: BLE001
        return ok(False, f"{mensaje}: ha lanzado {type(fallo).__name__}: {fallo}")
    return ok(False, f"{mensaje}: no ha fallado, y tenia que fallar")


def _fotogramas(cuantos=3, nombre="f"):
    rutas = []
    origen = os.path.join(CARPETA, "origen")
    os.makedirs(origen, exist_ok=True)
    for indice in range(cuantos):
        ruta = os.path.join(origen, f"{nombre}{indice}.png")
        with open(ruta, "wb") as fh:
            fh.write(b"\x89PNG" + bytes([indice]) * 32)
        rutas.append(ruta)
    return rutas


# --------------------------------------------------------------------- tipos

def prueba_catalogo():
    print("\n  CATALOGO DE TIPOS")
    ids = [t["id"] for t in presets.tipos()]
    igual(ids, ["guion", "estilo", "voz", "rotulos", "montaje", "canal"],
          "los tipos salen en su orden, con el canal el ultimo")
    for ficha in presets.tipos():
        ok(bool(ficha["nombre"]) and bool(ficha["que_fija"]),
           f"el tipo {ficha['id']} dice como se llama y que fija")
        ok(all(p in ("brief", "guion", "assets", "voz", "callouts", "render")
               for p in ficha["pasos"]),
           f"el tipo {ficha['id']} solo toca pasos que existen")
    revienta(lambda: presets.guardar("loquesea", "x", {"a": 1}),
             "tipo de preset desconocido", "un tipo inventado se rechaza")


def prueba_claves_cerradas():
    print("\n  LO QUE NO SE GUARDA SE DICE EN VOZ ALTA")
    revienta(lambda: presets.guardar("guion", "x", {"idioma_salida": "es", "colorete": 1}),
             "no sabe guardar", "una clave que no es del tipo se rechaza, no se cuela")
    revienta(lambda: presets.guardar("guion", "", {"idioma_salida": "es"}),
             "nombre", "un preset sin nombre se rechaza")
    revienta(lambda: presets.guardar("guion", "x", {}),
             "vacio", "un preset que no fija nada se rechaza")
    revienta(lambda: presets.guardar("canal", "x", {"guion": {"lo_que_sea": 1}}),
             "no sabe guardar",
             "un canal valida cada bloque con las reglas de SU tipo")


# ------------------------------------------------------------------- guardar

def prueba_guion():
    print("\n  GUION")
    ficha = presets.guardar("guion", "Canal ingles", {
        "instrucciones": "sin tecnicismos", "idioma_salida": "en",
        "duracion_objetivo_s": 600, "palabras_por_bloque": 34,
        "emocion_en_voz": False})
    ok(ficha["id"].startswith("pr"), "el preset nace con un id propio")
    ok("en" in ficha["resumen"] and "10m 00s" in ficha["resumen"],
       f"el resumen dice lo que hay dentro sin abrirlo ({ficha['resumen']})")
    cambios = presets.cambios_para(presets.leer(ficha["id"]))
    igual(sorted(cambios), ["brief", "guion"],
          "un preset de guion reparte sus claves entre los dos pasos que las entienden")
    igual(cambios["brief"]["idioma_salida"], "en", "escribe el idioma del canal")
    # UN VIDEO, UN IDIOMA: la lista vieja se lee, no se escribe.
    viejo = presets.guardar("guion", "Canal viejo", {"idiomas_salida": ["pt", "es"]})
    igual(presets.cambios_para(presets.leer(viejo["id"]))["brief"]["idioma_salida"],
          "pt", "de un preset guardado con la lista se coge el primero")
    presets.apartar(viejo["id"])
    presets.borrar(viejo["id"], confirmar=True)
    igual(cambios["brief"]["instrucciones"], "sin tecnicismos",
          "las instrucciones van al brief")
    # Y AL GUION LO SUYO. Se prueba con `False` a proposito: el valor por
    # defecto es True, y un preset que guarda lo mismo que ya hay no tiene nada
    # que aplicar -- `cambios_para` no lo reparte, y con razon.
    igual(cambios["guion"], {"emocion_en_voz": False},
          "y al guion lo suyo: como se anota la emocion en la locucion")
    return ficha


def prueba_estilo():
    print("\n  ESTILO: los fotogramas se copian al banco")
    rutas = _fotogramas(4)
    ficha = presets.guardar("estilo", "Cartoon plano", {
        "referencias": rutas,
        "guia": {"guia": "flat vector", "palabras": 60, "paleta": ["#fff", "#000"]},
        "calidad": "medium", "min_s": 2, "max_s": 4,
    }, miniatura=rutas[2])

    banco = presets.carpeta_de(ficha["id"])
    guardado = presets.leer(ficha["id"])
    ok(all(r.startswith(banco) for r in guardado["datos"]["referencias"]),
       "las referencias guardadas apuntan al banco, no al proyecto de origen")
    ok(all(os.path.exists(r) for r in guardado["datos"]["referencias"]),
       "y los ficheros estan de verdad ahi")
    ok(os.path.basename(ficha["miniatura"]).endswith("f2.png"),
       "la miniatura es el fotograma que se eligio, no siempre el primero")
    ok(ficha["hay_miniatura"], "y la interfaz sabe que la hay")

    # el caso que motiva el banco: se borra el origen y el preset sigue entero
    shutil.rmtree(os.path.join(CARPETA, "origen"), ignore_errors=True)
    cambios = presets.cambios_para(presets.leer(ficha["id"]))
    igual(len(cambios["assets"]["estilo"]["referencias"]), 4,
          "borrar la carpeta del proyecto de origen no deja al preset sin fotogramas")
    igual(cambios["assets"]["calidad"], "medium",
          "la calidad va SUELTA en assets, no dentro del diccionario 'estilo'")
    igual(cambios["assets"]["min_s"], 2, "y la duracion de plano tambien")

    revienta(lambda: presets.guardar("estilo", "corto", {"referencias": _fotogramas(2, "g")}),
             "al menos 3", "menos de 3 fotogramas se rechaza: con menos no es un estilo")
    revienta(lambda: presets.guardar("estilo", "fantasma",
                                     {"referencias": ["C:\\no\\existe\\1.png",
                                                      "C:\\no\\existe\\2.png",
                                                      "C:\\no\\existe\\3.png"]}),
             "no estan en el disco", "fotogramas que no existen se rechazan al guardar")
    return ficha


def prueba_fusion(ficha_estilo):
    print("\n  ESTILO: fusiona, no pisa")
    # un proyecto antiguo lleva un prompt de estilo escrito a mano DENTRO del
    # mismo diccionario. Escribirlo entero se lo llevaria por delante en
    # silencio, que es justo la degradacion que este sistema no se permite.
    actuales = {"assets": {"estilo": {"prompt": "flat cartoon a mano",
                                      "referencias": ["vieja.png"]}}}
    cambios = presets.cambios_para(presets.leer(ficha_estilo["id"]), actuales)
    estilo = cambios["assets"]["estilo"]
    igual(estilo["prompt"], "flat cartoon a mano",
          "el prompt escrito a mano del proyecto sobrevive")
    igual(len(estilo["referencias"]), 4, "las referencias si se sustituyen")
    ok("guia" in estilo, "y la guia escrita entra")


def prueba_voz():
    print("\n  VOZ")
    ficha = presets.guardar("voz", "Narrador ES", {
        "modelo": "sonic-3.5", "voz_id": "abc-123", "voz_nombre": "Luis",
        "idioma": "es", "velocidad": "slow", "emociones": ["curiosity:high"],
        "hueco_minimo": 1.2})
    ok("Luis" in ficha["resumen"], "el resumen dice el nombre de la voz, no su UUID")
    cambios = presets.cambios_para(presets.leer(ficha["id"]))
    igual(sorted(cambios), ["voz"], "la voz solo toca el paso de voz")
    ok("voz_nombre" not in cambios["voz"],
       "el nombre de la voz NO entra en params: no cambia lo que suena y "
       "cambiaria la firma del paso")
    igual(cambios["voz"]["voz_id"], "abc-123", "el id de la voz si entra")
    return ficha


def prueba_canal(guion, estilo, voz):
    print("\n  CANAL: un paquete de los otros")
    ficha = presets.guardar("canal", "el motor anterior EN", {
        "guion": presets.leer(guion["id"])["datos"],
        "estilo": presets.leer(estilo["id"])["datos"],
        "voz": presets.leer(voz["id"])["datos"],
    })
    cambios = presets.cambios_para(presets.leer(ficha["id"]))
    igual(sorted(cambios), ["assets", "brief", "guion", "voz"],
          "un canal aplica de golpe lo de los tres")
    ok("estilo" in cambios["assets"] and "min_s" in cambios["assets"],
       "y lo de dos claves distintas sobre el mismo paso se suma, no se pisa")
    # LA VOZ DEL CANAL LLEGA AL BRIEF. Un video largo (28-09-2026) conto las
    # palabras para 'normal' y «voz sin elegir» porque desde un canal la voz es
    # un bloque HERMANO del guion y la rama de guion no la veia: pidio 2.286
    # palabras para 14 minutos donde con su voz cabian 2.747.
    igual({c: cambios["brief"].get(c) for c in ("velocidad", "hueco_minimo", "voz_id")},
          {"velocidad": "slow", "hueco_minimo": 1.2, "voz_id": "abc-123"},
          "la voz del canal llega tambien al brief: cuenta las palabras para "
          "la voz que despues las dice")
    igual(cambios["voz"]["velocidad"], cambios["brief"]["velocidad"],
          "y es el MISMO valor en los dos pasos")
    igual(cambios["brief"]["instrucciones"], "sin tecnicismos",
          "sin quitarle al brief lo que le pone el bloque de guion")
    sin_voz = presets.guardar("canal", "Canal sin voz",
                              {"guion": presets.leer(guion["id"])["datos"]})
    del_brief = presets.cambios_para(presets.leer(sin_voz["id"]))["brief"]
    igual([c for c in ("velocidad", "hueco_minimo", "voz_id") if c in del_brief], [],
          "un canal sin voz no se inventa una para el brief")
    presets.apartar(sin_voz["id"])
    presets.borrar(sin_voz["id"], confirmar=True)
    propio = presets.carpeta_de(ficha["id"])
    ok(all(r.startswith(propio) for r in presets.leer(ficha["id"])["datos"]["estilo"]["referencias"]),
       "el estilo de dentro de un canal tiene su propia copia de los fotogramas")
    return ficha


def prueba_canal_conserva_lo_suyo(ficha):
    """Guardar OTRA VEZ no puede llevarse las muestras ni la 2x2.

    El fallo que cierra: sembrar el estilo borra la carpeta del preset entera y
    la rehace desde los fotogramas, asi que todo lo que no sea un fotograma
    desaparecia en el SEGUNDO guardado. Como las muestras se copian despues de
    congelar el preset, el primero salia bien y el fallo aparecia al cambiar el
    nombre, mover el ritmo o tocar un mando de voz: la ficha seguia diciendo
    `muestra1.png` y en el disco no habia ninguna. En pantalla, el banner del
    estilo en blanco y la tarjeta de la galeria con un fotograma crudo.
    """
    print("\n  CANAL: lo suyo sobrevive a un segundo guardado")
    carpeta = presets.carpeta_de(ficha["id"])
    propios = ["miniatura.png"] + [f"muestra{n}.png" for n in range(1, 5)]
    for indice, nombre in enumerate(propios):
        with open(os.path.join(carpeta, nombre), "wb") as fh:
            fh.write(b"\x89PNG-muestra" + bytes([indice]) * 16)

    datos = presets.leer(ficha["id"])["datos"]
    otra = presets.guardar("canal", "el motor anterior EN (2)", datos, pid=ficha["id"],
                           miniatura=os.path.join(carpeta, "miniatura.png"))
    faltan = [n for n in propios if not os.path.isfile(os.path.join(carpeta, n))]
    igual(faltan, [], "la 2x2 y las cuatro muestras siguen en el banco")
    igual(otra["miniatura"], os.path.join(carpeta, "miniatura.png"),
          "y la ficha sigue apuntando a la 2x2, no al primer fotograma")
    with open(os.path.join(carpeta, "muestra3.png"), "rb") as fh:
        ok(fh.read().startswith(b"\x89PNG-muestra"),
           "y son las mismas, no unas recortadas de cualquier sitio")
    ok(not os.path.isdir(f"{carpeta}.propios"),
       "el rincon donde se apartan no se queda por ahi")

    # sin `miniatura` explicita tampoco se pierde: es el caso de `_curar_muestras`
    tercera = presets.guardar("canal", "el motor anterior EN (3)",
                              presets.leer(ficha["id"])["datos"], pid=ficha["id"])
    igual(tercera["miniatura"], os.path.join(carpeta, "miniatura.png"),
          "y guardar sin decir miniatura la recupera igual")
    return ficha


# ------------------------------------------------------------------ papelera

def prueba_papelera(ficha):
    print("\n  PAPELERA: apartar no es borrar")
    presets.apartar(ficha["id"])
    listado = presets.listar()
    ok(not any(f["id"] == ficha["id"] for f in listado["presets"][ficha["tipo"]]),
       "lo apartado sale de la lista")
    ok(any(f["id"] == ficha["id"] for f in listado["papelera"]),
       "y aparece en la papelera")
    ok(os.path.exists(presets.carpeta_de(ficha["id"])),
       "apartar no toca los ficheros: siguen enteros")

    peso = presets.peso(ficha["id"])
    ok(peso["ficheros"] > 0, "se puede decir cuantos ficheros se perderian antes de borrar")

    revienta(lambda: presets.borrar(ficha["id"]),
             "confirmar", "borrar sin confirmar no borra")

    presets.restaurar(ficha["id"])
    ok(any(f["id"] == ficha["id"] for f in presets.listar()["presets"][ficha["tipo"]]),
       "y se puede devolver")

    revienta(lambda: presets.borrar(ficha["id"], confirmar=True),
             "apartalo primero",
             "un preset vivo no se puede borrar de golpe: hay que apartarlo antes")

    presets.apartar(ficha["id"])
    salida = presets.borrar(ficha["id"], confirmar=True)
    igual(salida["borrado"], ficha["id"], "y desde la papelera si se borra")
    ok(not os.path.exists(presets.carpeta_de(ficha["id"])),
       "el borrado definitivo se lleva tambien su carpeta del banco")
    revienta(lambda: presets.leer(ficha["id"]), "no hay ningun preset",
             "y ya no existe en ningun sitio")


def prueba_actualizar(ficha):
    print("\n  ACTUALIZAR")
    mismo = presets.guardar("guion", "Canal ingles (2)", {"idioma_salida": "en"},
                            pid=ficha["id"])
    igual(mismo["id"], ficha["id"], "guardar con id sustituye en vez de duplicar")
    igual(mismo["fecha"], ficha["fecha"], "y conserva la fecha de creacion")
    ok(mismo["modificado"] >= ficha["modificado"], "anotando cuando se cambio")
    revienta(lambda: presets.guardar("voz", "no", {"voz_id": "x"}, pid=ficha["id"]),
             "no de voz",
             "cambiarle el tipo a un preset se rechaza: seria otra cosa con el mismo nombre")
    total = len(presets.listar()["presets"]["guion"])
    igual(total, 1, "y no se ha duplicado")


def prueba_renombrar(ficha):
    """Renombrar cambia el nombre y NADA mas.

    Es una operacion aparte de guardar() y no un guardar() con los mismos datos
    porque guardar() vuelve a sembrar los ficheros del preset: en uno de estilo
    eso le borra la carpeta del banco y recopia los fotogramas para cambiar una
    letra. Aqui se protege lo unico que importa de esa distincion.
    """
    print("\n  RENOMBRAR")
    original = presets.leer(ficha["id"])
    cambiado = presets.renombrar(ficha["id"], nombre="Canal ingles renombrado",
                                 nota="una nota nueva")
    igual(cambiado["nombre"], "Canal ingles renombrado", "cambia el nombre")
    igual(cambiado["nota"], "una nota nueva", "y la nota")
    igual(cambiado["id"], ficha["id"], "conservando el id")
    igual(cambiado["fecha"], original["fecha"], "y la fecha de creacion")
    igual(cambiado["datos"], original["datos"],
          "lo que el preset guarda no se toca")

    solo_nota = presets.renombrar(ficha["id"], nota="solo la nota")
    igual(solo_nota["nombre"], "Canal ingles renombrado",
          "tocar solo la nota no se lleva por delante el nombre")
    solo_nombre = presets.renombrar(ficha["id"], nombre="Otro nombre")
    igual(solo_nombre["nota"], "solo la nota",
          "y tocar solo el nombre no borra la nota")

    revienta(lambda: presets.renombrar(ficha["id"], nombre="   "),
             "necesita un nombre",
             "un nombre en blanco se rechaza: es lo unico que se ve fuera")
    revienta(lambda: presets.renombrar("noexiste", nombre="x"),
             "no hay ningun preset",
             "y un id inventado tambien")
    igual(len(presets.listar()["presets"]["guion"]), 1,
          "renombrar no duplica")


def prueba_renombrar_estilo(ficha):
    """El caso que motiva que renombrar sea una operacion aparte."""
    print("\n  RENOMBRAR UN ESTILO (sus fotogramas no se tocan)")
    antes = presets.leer(ficha["id"])
    rutas = list(antes["datos"].get("referencias") or [])
    marcas = {r: os.path.getmtime(r) for r in rutas if os.path.exists(r)}
    ok(len(marcas) >= 3, f"el preset tiene sus {len(marcas)} fotogramas en el banco")

    despues = presets.renombrar(ficha["id"], nombre="Estilo renombrado")
    igual(despues["datos"].get("referencias"), rutas,
          "las rutas de los fotogramas siguen siendo las mismas")
    ok(all(os.path.exists(r) for r in marcas),
       "y los ficheros siguen en el disco")
    ok(all(os.path.getmtime(r) == marcas[r] for r in marcas),
       "sin haberlos vuelto a copiar (misma fecha de modificacion)")
    igual(despues["miniatura"], antes["miniatura"], "y conserva su miniatura")


def prueba_ids_no_chocan():
    """Dos presets seguidos son DOS presets, aunque caigan en el mismo milisegundo.

    El id era `pr{milisegundos:x}` a secas, y dos guardados en el mismo
    milisegundo salian con el mismo id -- que `guardar` toma por una
    actualizacion y usa para SUSTITUIR el anterior. Guardar dos se llevaba uno
    por delante, sin decir nada. Se veia como esta misma suite fallando dos de
    cada tres veces con un KeyError, y en la interfaz habria sido «he guardado
    dos y solo aparece uno». Cuanto mas rapida la maquina, mas a menudo.
    """
    print("\n  IDS: dos presets seguidos no se pisan")
    antes = len(presets.listar()["presets"]["guion"])
    ids = [presets.guardar("guion", f"Rafaga {i}",
                           {"idioma_salida": "es"})["id"]
           for i in range(12)]
    igual(len(set(ids)), 12, "doce presets seguidos dan doce ids distintos")
    igual(len(presets.listar()["presets"]["guion"]), antes + 12,
          "y estan los doce en la lista, no uno pisando a otro")
    # y el contenido de cada uno es el suyo, no el del ultimo que paso por ahi
    igual(len({presets.leer(i)["nombre"] for i in ids}), 12,
          "cada uno conserva SU nombre")




def prueba_grafismo_guarda_el_subtitulo():
    """El preset de grafismo guardaba `arquetipos` (muertos) y perdia el tamano.

    Los rotulos se retiraron enteros el 22-08, y `arquetipos` se quedo en las
    claves del preset: se guardaba y se aplicaba sin que nadie lo leyera. Al
    mismo tiempo `subtitulo_tam` --que SI es una decision de grafismo, y la unica
    que queda del subtitulo-- no estaba en la lista, asi que la pantalla lo
    mandaba, el almacen lo tiraba, y guardar un preset y aplicarlo devolvia el
    tamano por defecto.
    """
    print("\n[grafismo] el preset guarda el tamano del subtitulo, no arquetipos")
    claves = presets.TIPOS["rotulos"]["claves"]
    ok("subtitulo_tam" in claves,
       f"el tamano del subtitulo viaja en el preset: {claves}")
    ok("arquetipos" not in claves,
       "y `arquetipos` ya no: no hay rotulos que elegir desde el 22-08")
    igual(presets.TIPOS["rotulos"]["nombre"], "Grafismo",
          "se llama por lo que es. El id se queda en 'rotulos' porque es la "
          "clave con la que estan guardados los presets del canal en disco")


def prueba_paquetes():
    """El estilo sigue usable y editable despues de quitar el servidor origen."""
    import io
    import json
    import zipfile
    from unittest.mock import patch
    from nucleo.proyecto import Proyecto, escribir_json, leer_json
    from nucleo.estado import Estado, PASOS
    import paquete_estilo as paquetes

    fichero, banco = presets.FICHERO, presets.BANCO
    with tempfile.TemporaryDirectory(prefix="prueba_paquetes_") as raiz:
        try:
            origen = os.path.join(raiz, "origen")
            presets.FICHERO = os.path.join(origen, "presets.json")
            presets.BANCO = os.path.join(origen, "banco")
            taller = Proyecto.crear(os.path.join(origen, "proyectos"), "taller")
            taller.config[paquetes.CONFIG_TALLER] = True
            taller.guardar_config()
            referencias = []
            for i in range(3):
                ruta = taller.ruta("estilo", f"ref{i}.png")
                os.makedirs(os.path.dirname(ruta), exist_ok=True)
                with open(ruta, "wb") as fh:
                    fh.write(b"imagen de prueba" + bytes([i]))
                referencias.append(ruta)
            externo = os.path.join(origen, "adjunto.png")
            shutil.copyfile(referencias[0], externo)
            estado = Estado(taller)
            for paso in PASOS:
                pid = paso["id"]
                estado.actualizar_params(pid, {"entrada": externo})
                if pid == "assets":
                    estado.actualizar_params(pid, {"estilo": {"referencias": referencias}})
                ruta = taller.ruta_paso(pid, 1, crear=True)
                salida = os.path.join(ruta, "salida.txt")
                with open(salida, "w", encoding="utf-8") as fh:
                    fh.write("salida ya generada")
                estado.completar(pid, {"archivo": salida},
                                 unidades={"escena:S001": {"archivo": salida}}
                                 if paso["unidades"] else None)
            estado.completar("assets", estado.salidas("assets"),
                             unidades={"escena:S001": estado.salidas("assets")})
            # Una firma desparejada a proposito debe seguir desparejada.
            doc = leer_json(taller.ruta("estado.json"))
            doc["pasos"]["render"]["firma"] = "descuadrada-a-proposito"
            escribir_json(taller.ruta("estado.json"), doc)
            previos = {p["id"]: Estado(taller).estado_de(p["id"]) for p in PASOS}
            with patch.object(presets, "_moodboard", side_effect=RuntimeError("sin red")):
                ficha = presets.guardar("canal", "Estilo viajero", {
                    "estilo": {"referencias": referencias, "min_s": 3, "max_s": 6},
                    "guion": {"idioma_salida": "es", "instrucciones": "tono cercano"},
                    "voz": {"voz_id": "voz-elegida", "velocidad": "fast"},
                    "origen": {"taller": taller.id, "estilo_imagenes": ["aportada.png"],
                               "muestras": ["muestra1.png"]},
                }, miniatura=referencias[0])
            carpeta = presets.carpeta_de(ficha["id"])
            shutil.copyfile(referencias[1], os.path.join(carpeta, "muestra1.png"))
            archivo = io.BytesIO()
            paquetes.exportar(presets, ficha["id"], taller.raiz, archivo)
            contenido = archivo.getvalue()
            shutil.rmtree(origen)
            destino = os.path.join(raiz, "destino")
            presets.FICHERO = os.path.join(destino, "presets.json")
            presets.BANCO = os.path.join(destino, "banco")
            proyectos = os.path.join(destino, "proyectos")
            nueva = paquetes.importar(presets, io.BytesIO(contenido), proyectos)
            ok(nueva["id"] != ficha["id"], "importar crea otro estilo, sin sobrescribir")
            igual(nueva["datos"]["voz"], ficha["datos"]["voz"], "la voz viaja intacta")
            ok(all(os.path.isfile(r) for r in nueva["datos"]["estilo"]["referencias"]),
               "las referencias existen sin el servidor original")
            ok(os.path.isfile(nueva["miniatura"]), "la miniatura viaja")
            ok(os.path.isfile(os.path.join(presets.carpeta_de(nueva["id"]), "muestra1.png")),
               "las muestras viajan")
            taller_nuevo = Proyecto(os.path.join(proyectos, nueva["datos"]["origen"]["taller"]))
            ok(taller_nuevo.config.get(paquetes.CONFIG_TALLER), "el taller sigue oculto como taller")
            actual = Estado(taller_nuevo)
            igual({p["id"]: actual.estado_de(p["id"]) for p in PASOS}, previos,
                  "la mudanza conserva los estados y las obsolescencias reales")
            igual(actual._doc["pasos"]["render"]["firma"], "descuadrada-a-proposito",
                  "no se arreglan firmas desparejadas a proposito")
            for paso in PASOS:
                p = paso["id"]
                ok(os.path.isfile(actual.salidas(p)["archivo"]), f"la salida de {p} existe")
            ok(os.path.isfile(actual.params("ingesta")["entrada"]), "los adjuntos externos viajan")
            mapa = actual.manifiesto_version("assets", actual._doc["pasos"]["assets"]["versiones"][0])
            ok(os.path.isfile(mapa["escena:S001"]["salidas"]["archivo"]),
               "el manifiesto externo apunta al nuevo taller")
            igual(len(actual._doc["pasos"]["assets"]["versiones"]), 2,
                  "se conserva tambien el historico del taller")
            segunda = paquetes.importar(presets, io.BytesIO(contenido), proyectos)
            ok(segunda["id"] != nueva["id"], "importar dos veces no pisa la primera copia")
            presets.cambios_para(nueva)
            ok(True, "el estilo importado se puede aplicar a un video nuevo")

            # Reescribimos un paquete como si viniera de Linux. Las firmas se
            # sellan alli antes de importarlo en Windows, como haria el origen.
            with tempfile.TemporaryDirectory(dir=raiz) as linux:
                paquetes._extraer(io.BytesIO(contenido), linux)
                manifiesto = leer_json(os.path.join(linux, "estilo.json"))
                taller_linux = os.path.join(linux, "taller")
                antes_linux = paquetes.mudanza._calculadas(Estado(Proyecto(taller_linux)))
                reglas = [(r, f"/srv/estudio/{k}") for k, r in manifiesto["raices"].items()]
                reglas += [(r, f"/srv/adjuntos/{i}.png")
                           for i, r in enumerate(manifiesto["externos"])]
                for ruta, tipo in list(paquetes.mudanza.ficheros_json(linux)):
                    paquetes.mudanza.mudar_fichero(ruta, tipo, reglas, True)
                manifiesto = leer_json(os.path.join(linux, "estilo.json"))
                manifiesto["externos"] = {paquetes.mudanza.mudar_cadena(k, reglas)[0]: v
                                          for k, v in manifiesto["externos"].items()}
                escribir_json(os.path.join(linux, "estilo.json"), manifiesto)
                paquetes.mudanza.resellar(taller_linux, antes_linux, True, [])
                zip_linux = io.BytesIO()
                with zipfile.ZipFile(zip_linux, "w") as z:
                    for base, _, nombres in os.walk(linux):
                        for nombre in nombres:
                            ruta = os.path.join(base, nombre)
                            z.write(ruta, os.path.relpath(ruta, linux).replace("\\", "/"))
                desde_linux = paquetes.importar(presets, io.BytesIO(zip_linux.getvalue()), proyectos)
                otro = Estado(Proyecto(os.path.join(proyectos, desde_linux["datos"]["origen"]["taller"])))
                igual({p["id"]: otro.estado_de(p["id"]) for p in PASOS}, previos,
                      "un paquete de Linux conserva sus estados en Windows")
                ok(all(os.path.isfile(r) for r in desde_linux["datos"]["estilo"]["referencias"]),
                   "las barras de las referencias se adaptan al sistema de destino")

            incompleto = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(contenido)) as fuente, zipfile.ZipFile(incompleto, "w") as salida_zip:
                for entrada in fuente.infolist():
                    if entrada.filename != "taller/pasos/assets/_versiones/v1.json":
                        salida_zip.writestr(entrada, fuente.read(entrada))
            try:
                paquetes.importar(presets, io.BytesIO(incompleto.getvalue()), proyectos)
                ok(False, "un manifiesto historico ausente se rechaza")
            except (paquetes.ErrorPaquete, RuntimeError):
                ok(True, "un manifiesto historico ausente se rechaza")

            # Este fallo llega despues de copiar el taller: se deben retirar
            # tambien sus carpetas, no solo evitar anadir la ficha al catalogo.
            sin_referencia = io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(contenido)) as fuente, zipfile.ZipFile(sin_referencia, "w") as salida_zip:
                for entrada in fuente.infolist():
                    if not entrada.filename.startswith("banco/"):
                        salida_zip.writestr(entrada, fuente.read(entrada))
            carpetas_antes = (set(os.listdir(presets.BANCO)), set(os.listdir(proyectos)))
            try:
                paquetes.importar(presets, io.BytesIO(sin_referencia.getvalue()), proyectos)
                ok(False, "un ZIP sin sus referencias se rechaza")
            except paquetes.ErrorPaquete:
                ok(True, "un ZIP sin sus referencias se rechaza")
            igual((set(os.listdir(presets.BANCO)), set(os.listdir(proyectos))), carpetas_antes,
                  "un fallo tardio retira el banco y el taller incompletos")

            for nombre, transformar in (
                    ("ruta fuera del ZIP", lambda z: z.writestr("../fuera.txt", "no")),
                    ("ZIP incompleto", lambda z: None),
                    ("version desconocida", lambda z: z.writestr("estilo.json", json.dumps({
                        "formato": paquetes.FORMATO, "version": 999})))):
                malo = io.BytesIO()
                with zipfile.ZipFile(malo, "w") as z:
                    transformar(z)
                antes_total = presets.listar()["total"]
                try:
                    paquetes.importar(presets, io.BytesIO(malo.getvalue()), proyectos)
                    ok(False, f"{nombre} se rechaza")
                except paquetes.ErrorPaquete:
                    ok(True, f"{nombre} se rechaza")
                igual(presets.listar()["total"], antes_total, "un fallo no publica estilos a medias")
        finally:
            presets.FICHERO, presets.BANCO = fichero, banco


def main():
    shutil.rmtree(CARPETA, ignore_errors=True)
    os.makedirs(CARPETA, exist_ok=True)
    # el almacen y el banco se apuntan a la carpeta de la prueba: una suite no
    # puede heredar el contenido de la configuracion de produccion
    presets.FICHERO = os.path.join(CARPETA, "presets.json")
    presets.BANCO = os.path.join(CARPETA, "banco")

    igual(presets.listar()["total"], 0, "se empieza sin ningun preset")
    prueba_catalogo()
    prueba_claves_cerradas()
    guion = prueba_guion()
    estilo = prueba_estilo()
    prueba_fusion(estilo)
    voz = prueba_voz()
    canal = prueba_canal(guion, estilo, voz)
    prueba_canal_conserva_lo_suyo(canal)
    prueba_papelera(canal)
    prueba_actualizar(guion)
    prueba_renombrar(guion)
    prueba_renombrar_estilo(estilo)
    prueba_ids_no_chocan()
    prueba_grafismo_guarda_el_subtitulo()
    prueba_paquetes()

    print("\n" + "=" * 70)
    if _fallos:
        print(f"FALLAN {len(_fallos)} de {_comprobaciones[0]} comprobaciones:")
        for fallo in _fallos:
            print(f"  - {fallo}")
        return 1
    print(f"PRESETS OK: {_comprobaciones[0]} comprobaciones pasan")
    shutil.rmtree(CARPETA, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
