"""Identidades del vídeo: configuración editable y contrato de intervenciones.

La configuración vive en guion.params.personajes. Las imágenes son referencias
relativas e inmutables de medios_usuario, incluidas en copias y paquetes.
Cada bloque es una intervención de un único hablante; su texto sigue siendo
la fuente de narración, subtítulos y cortes, sin nombres locutados ni duplicados.
"""
import copy
import io
import os
import re

from PIL import Image

try:
    from . import medios, imagenes_animacion
except ImportError:
    import medios
    import imagenes_animacion

CAMPOS_INTERVENCION = ("personaje_id", "personaje_nombre", "categoria", "voz_id",
                       "personajes_visibles", "descripcion_visual", "escenas_visuales", "capitulo")


def normalizar(crudo, proyecto=None, pendientes=False):
    if not isinstance(crudo, dict) or set(crudo) - {"activo", "items", "incorporar_dialogos"}:
        raise ValueError("personajes debe contener activo e items")
    if "incorporar_dialogos" in crudo and not isinstance(crudo["incorporar_dialogos"], bool):
        raise ValueError("incorporar_dialogos debe ser una casilla activada o desactivada")
    if not isinstance(crudo.get("activo", False), bool) or not isinstance(crudo.get("items", []), list):
        raise ValueError("elige Personalizar personajes y una lista de personajes")
    resultado, ids, nombres = [], set(), set()
    narradores = 0
    perspectivas = 0
    for ficha in crudo.get("items", []):
        if not isinstance(ficha, dict) or set(ficha) - {"id", "nombre", "descripcion", "categoria", "imagen", "subida", "voz_id", "voz_nombre", "primera_persona", "stickman"}:
            raise ValueError("la ficha del personaje tiene campos desconocidos")
        f = copy.deepcopy(ficha)
        if 'stickman' in f:
            from pasos import stickman
            f['stickman'] = stickman.variante(f['stickman'])
            if f.get('primera_persona'):
                raise ValueError('la primera persona no se aplica a personajes Stickman')
        if not isinstance(f.get("id"), str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", f["id"]):
            raise ValueError("el personaje necesita un identificador estable")
        for clave, maximo in (("nombre", 120), ("descripcion", 4000)):
            if not isinstance(f.get(clave), str) or not 1 <= len(f[clave].strip()) <= maximo:
                raise ValueError(f"{clave} del personaje: entre 1 y {maximo} caracteres")
            f[clave] = f[clave].strip()
        if f["id"] in ids or f["nombre"].casefold() in nombres:
            raise ValueError("ya existe un personaje con ese identificador o nombre")
        ids.add(f["id"])
        nombres.add(f["nombre"].casefold())
        if f.get("categoria") not in ("narrador", "personaje"):
            raise ValueError("elige Narrador o Personaje")
        if "primera_persona" in f and not isinstance(f["primera_persona"], bool):
            raise ValueError("primera_persona debe ser una casilla activada o desactivada")
        perspectivas += f.get("primera_persona") is True
        if perspectivas > 1:
            raise ValueError("solo un personaje o narrador puede tener activada la primera persona por vídeo")
        narradores += f["categoria"] == "narrador"
        if narradores > 1:
            raise ValueError("solo se puede incorporar un narrador por vídeo")
        for clave in ("imagen", "subida", "voz_id", "voz_nombre"):
            if not isinstance(f.get(clave, ""), str) or len(f.get(clave, "")) > 300:
                raise ValueError(f"{clave} del personaje no es válido")
        imagen = f.get("imagen") or ""
        subida = f.get("subida") or ""
        if imagen and not re.fullmatch(r"medios_usuario/animaciones/[a-f0-9]{32}\.png", imagen):
            raise ValueError("elige una imagen del personaje guardada en este vídeo")
        if subida and (not pendientes or not re.fullmatch(r"[a-zA-Z0-9_.-]+", subida)):
            raise ValueError("la imagen pendiente del personaje no es válida")
        if not imagen and not (pendientes and subida):
            raise ValueError("genera o sube la imagen antes de agregar el personaje")
        if imagen and proyecto:
            imagenes_animacion.ruta_de(proyecto, imagen)
            if f.get('stickman'):
                recibo = medios.leer_json(proyecto.ruta(imagen) + '.json', {}) or {}
                if recibo.get('stickman') != f['stickman']:
                    raise ValueError('genera el personaje Stickman con Claude antes de guardarlo')
        if f["categoria"] == "narrador":
            # Nunca almacenar una copia de la voz general: cambiarla debe ser
            # inmediato y no puede dejar una voz independiente en el narrador.
            f.pop("voz_id", None)
            f.pop("voz_nombre", None)
        if not subida:
            f.pop("subida", None)
        resultado.append(f)
    config = {"activo": crudo.get("activo", False), "items": resultado}
    if "incorporar_dialogos" in crudo:
        config["incorporar_dialogos"] = crudo["incorporar_dialogos"]
    return config


def params_de(proyecto, paso):
    documento = medios.leer_json(os.path.join(proyecto.raiz, "estado.json"), {}) or {}
    return ((documento.get("pasos") or {}).get(paso) or {}).get("params") or {}


def contexto(assets, voz):
    return {**({'stickman': True} if (assets.get('estilo') or {}).get('stickman') else {}),
            "generar_personajes": assets.get("generar_personajes") is not False,
            "incorporar_voz": voz.get("incorporar_voz") is not False,
            "voz_id": voz.get("voz_id") or ""}


def activos(opciones):
    if not (opciones.get("sistema_personajes") or {}).get("generar_personajes"):
        return []
    config = opciones.get("personajes") or {}
    return copy.deepcopy(config.get("items") or []) if config.get("activo") else []


def dialogos_habilitados(opciones):
    # La ausencia conserva el contrato de los proyectos anteriores a la casilla.
    return (opciones.get("personajes") or {}).get("incorporar_dialogos", True)


def solo_personajes(opciones):
    modo = opciones.get("sistema_personajes") or {}
    return bool(modo.get("generar_personajes") and modo.get("incorporar_voz") is False
                and dialogos_habilitados(opciones))


def validar_voces(opciones):
    """Antes de pedir un guion sin narrador: todo actor necesita voz propia."""
    if not solo_personajes(opciones):
        return
    actores = [p for p in activos(opciones) if p.get("categoria") == "personaje"]
    if not actores:
        raise ValueError("Sin voz del narrador, activa Personalizar personajes y agrega al menos un personaje con voz asignada antes de generar el guion.")
    faltan = [p["nombre"] for p in actores if not str(p.get("voz_id") or "").strip()]
    if faltan:
        raise ValueError("Asigna una voz propia a estos personajes antes de generar el guion: " + ", ".join(faltan) + ".")


def opciones_del_proyecto(proyecto, voz=None):
    opciones = dict(params_de(proyecto, "guion"))
    assets = params_de(proyecto, "assets")
    opciones["sistema_personajes"] = contexto(assets, voz if voz is not None else params_de(proyecto, "voz"))
    if assets.get("generar_personajes") is not True and "sistema_personajes" not in params_de(proyecto, "guion"):
        opciones["sistema_personajes"]["generar_personajes"] = False
    return opciones


def personaje_pov(opciones):
    if (opciones.get('sistema_personajes') or {}).get('stickman'):
        return None
    seleccionados = [p for p in activos(opciones) if p.get("primera_persona") is True]
    if len(seleccionados) > 1:
        raise ValueError("solo un personaje o narrador puede tener activada la primera persona por vídeo")
    return seleccionados[0] if seleccionados else None


def instruccion_pov(personaje):
    if not personaje:
        return ""
    return (f"PERSPECTIVA OBLIGATORIA EN PRIMERA PERSONA (POV) de {personaje['nombre']} "
            f"(ID {personaje['id']}): TODAS las escenas se ven directamente a través de sus ojos, "
            "también durante los diálogos de otros personajes. Adapta el guion y cada descripción visual "
            "a lo que ve y vive este personaje, sea de categoría Personaje o Narrador. La cámara ES su mirada, "
            "nunca una cámara externa ni un plano en tercera persona de este personaje. Pueden aparecer sus manos, brazos, piernas, "
            "ropa, objetos que sostiene o su reflejo en espejos y superficies cuando corresponda, "
            "sin forzar su presencia en todas las imágenes. Mantén su apariencia según su referencia "
            "completa de rostro, cuerpo y vestimenta; esa hoja de referencia sigue siendo obligatoria "
            "y de cuerpo entero, no es una escena POV. Esta perspectiva prevalece sobre encuadres "
            "genéricos y no cambia quién habla ni las voces asignadas.")


def instruccion(opciones):
    modo = opciones.get("sistema_personajes") or {}
    if not modo.get("generar_personajes"):
        return ""
    import json
    reparto = activos(opciones)
    con_voz = modo.get("incorporar_voz", True)
    dialogos = dialogos_habilitados(opciones)
    return "\n".join([
        "== PERSONAJES E INTERVENCIONES (contrato adicional obligatorio) ==",
        "Los personajes personalizados tienen prioridad. Respeta sus IDs, nombres, personalidad, función y apariencia; no los dupliques.",
        json.dumps(reparto, ensure_ascii=False),
        (("SIN DIÁLOGOS: utiliza únicamente la narración habitual, sin intervenciones habladas de los personajes. Los personajes pueden aparecer y actuar visualmente, pero no hablar. Usa personaje_id del narrador personalizado o cadena vacía para narración general."
          + (" La locución está desactivada: conserva el guion narrativo habitual como base visual y temporal; no lo conviertas en conversaciones." if not con_voz else ""))
         if not dialogos else
         "Combina narración y diálogos naturales, coherentes y cinematográficos. El narrador lleva principalmente el relato; decide cuándo intercalar intervenciones de los personajes para desarrollar la historia de forma natural, sin forzarlas. El narrador personalizado es la figura narrativa principal y puede aparecer explicando al espectador."
         if con_voz else
         "SIN VOZ DEL NARRADOR: escribe una historia especializada en DIÁLOGOS entre personajes. Explica los acontecimientos, ideas, pensamientos y emociones mediante sus conversaciones y reacciones. NO uses narración en off ni intervenciones de categoría narrador. El narrador guardado queda inactivo. SÍ se generará audio, exclusivamente con las voces propias asignadas a los personajes personalizados. Solo esos personajes pueden hablar; los adicionales automáticos solo pueden aparecer visualmente, sin intervenciones."),
        "Puedes crear personajes adicionales necesarios, sin duplicar a los personalizados. Devuelve personajes_automaticos: [{id: auto_nombre_estable, nombre, descripcion, categoria: personaje}]. Conserva sus IDs si ya estaban en el guion anterior.",
        "Cada bloque es UNA intervención de UN hablante (puede tener varias frases completas). Nunca mezcles voces en el mismo bloque. texto contiene SOLO sus palabras, sin prefijos de nombre ni acotaciones escénicas. Mantén el resto del formato JSON solicitado.",
        "Añade a CADA bloque personaje_id (ID existente, o cadena vacía SOLO para narración general), personajes_visibles (lista de IDs que aparecen) y descripcion_visual (acción, postura, expresión y entorno, separada del texto hablado). Los diálogos deben desarrollar la historia sin intervenciones forzadas.",
        "Cuando el narrador aparece visualmente, inclúyelo en personajes_visibles. Una voz no implica presencia visual. Cada bloque conserva su id Bxxx, que identifica también la escena de la intervención; el montaje lo vinculará a sus escenas Sxxx.",
        ("La aplicación resolverá nombre, categoría y voz desde el ID: narración y narrador usan SIEMPRE la voz general; personajes con voz propia usan esa voz y el resto la general. No inventes IDs de voces."
         if not solo_personajes(opciones) else "La aplicación resolverá la voz desde el ID personalizado. Usa solo hablantes con voz propia asignada; nunca uses la voz general ni inventes voces."),
        "Este contrato de hablantes prevalece sobre las instrucciones genéricas de narración en off; si el usuario aporta un guion propio, respeta sus palabras y etiqueta sus intervenciones sin reescribirlo.",
        instruccion_pov(personaje_pov(opciones)),
        instruccion_visual_stickman(opciones.get("estilo_visual")) if modo.get("stickman") else "",
    ])


def instruccion_tiempo_visual():
    return """== TIEMPO DISPONIBLE PARA LA ACCIÓN VISUAL ==
La duración de pantalla de CADA frase es el presupuesto de su animación, no la del bloque ni el tiempo ficticio del relato.
Si hay duracion_s, úsala; duracion_estimada indica si es provisional. Antes de tener audio, estima el tiempo de lectura
de cada frase según el idioma y la velocidad de voz indicados; una frase breve no permite una secuencia larga.
En hasta 3 segundos: situación ya establecida en el primer fotograma y UNA acción o reacción breve, legible y completa.
De 3 a 6 segundos: una acción principal y una reacción sencilla, sin encadenar entradas, trayectos y acciones secundarias.
En planos más largos: desarrolla preparación, acción y resultado de forma proporcionada, con movimiento natural durante
el tiempo disponible; no termines todo al principio para dejar el resto inmóvil ni añadas acciones ajenas para rellenar.
Describe tiempos locales aproximados cuando conozcas duracion_s y reserva tiempo para percibir el resultado.
Reduce la cantidad de acciones, nunca aceleres artificialmente gestos, caminatas o lecturas para meterlo todo.
Las horas o días mencionados por la voz no son segundos de animación: sugiérelos con una sola señal visual clara.
Por ejemplo, «Las respuestas tardan horas» en 2 s: personaje ya sentado con el móvil sin respuesta; lo mira y baja
los hombros. No dejar/coger el móvil repetidas veces ni encadenar mediodía, tarde y noche en esos dos segundos.
Mantén escenario y continuidad; no repitas la presentación ni adelantes acciones que pertenecen a la frase siguiente.
"""


def instruccion_utileria_stickman():
    return """== UTILERÍA FÁCIL DE REPRESENTAR EN STICKMAN ==
No describas personajes llevando chaquetas, bolsos u otros objetos al hombro, echados sobre la espalda
o colgados del cuello: esas superposiciones con el cuerpo resultan visualmente ambiguas en este motor.
Evita también ponerse/quitarse ropa como acción secundaria. Mantén las prendas puestas normalmente.
Si el objeto importa al relato, colócalo sobre una mesa o sostenido en una mano, separado del torso y del rostro.
Si solo adorna una salida o una actitud, omítelo: expresa la intención con postura, expresión y desplazamiento.
Ejemplo: «Andrés desliza sus tareas hasta la mesa de Clara y se marcha; Clara sigue trabajando bajo la lámpara».
No añadas «con la chaqueta al hombro». Al adaptar descripciones anteriores, conserva la acción y elimina ese adorno.
"""


def instruccion_visual_stickman(estilo=None):
    from pasos import direccion_color, capitulos_guion
    return """== DIRECCIÓN VISUAL STICKMAN 2D ==
La narración explica la idea; la imagen muestra una acción concreta que la hace comprensible.
El motor dispone del kit completo: figuras articuladas, expresiones, utilería por piezas, escenarios reutilizables,
primeros planos con fondo desenfocado, pantallas divididas, tipografía editorial, documentos, listas progresivas,
gráficos de barras, diales, matrices de población, cronologías, luces y atmósfera. También planos espaciales 3D.
Realiza un ensayo visual: alterna escena cotidiana, detalle, emoción, evidencia y síntesis cuando aporte significado.
Selecciona el recurso según la idea: conducta = interacción; emoción = primer plano; magnitud = gráfico;
distinción = comparación; patrón = cronología; definición = documento; mecanismo = metáfora simple.
No fuerces actores en todos los gráficos, ni gráficos en toda frase. Una relación dominante por momento.
Escribe escenas sencillas: situación inicial, UNA acción principal o revelado y resultado legible.
En una interacción, un gesto de señalar no sustituye a abrazar, rechazar o alejarse.
No inventes móviles, relojes ni decoración para llenar huecos. Evita objetos dentro del pecho y metáforas anidadas
(escudo con gota, espejo dentro de una figura). Sí admite UNA metáfora clara: máscara que se aparta,
interruptor que se apaga, termómetro que sube, recipiente que se repara; debe tener una transformación visible.
Para comparar, elige pantalla dividida con dos condiciones equivalentes, dos magnitudes comparables o acciones
por turnos si es una interacción. No dupliques el mismo actor. Texto breve y selectivo, no toda la locución.
Reutiliza los mismos lugares (nombre estable), ropa, paleta y utilería cuando regresen varios bloques después.
Cada secuencia puede abarcar varias frases: conservar el mundo y avanzar estado o encuadre, no reiniciar.
Una escena contextual tiene lugar reconocible, luz y suelo; un esquema tiene espacio y jerarquía de lectura.
Alterna planos generales, medios, caras y detalles según el foco; no presentes siempre cuerpos enteros.
Las cantidades y afirmaciones en gráficos proceden del material, no inventes medidas o evidencia.
Por ejemplo, distancia y actitud defensiva: una figura retrocede ante otra y cruza los brazos; no tres iconos sin acción.
Consuelo infantil: el cuidador se acerca, se arrodilla junto al niño y extiende los brazos; la ausencia de respuesta
se representa en otra frase con el cuidador alejado, mirando al lado opuesto. No pidas duplicar al mismo actor en pantalla.
Si necesitas una pizarra, describe marco, bandeja de tiza y contenido dispuesto DENTRO de ella; no un rectángulo verde
con rótulos flotantes. Todo elemento importante debe ser grande, reconocible y estar ligado a la acción.
OBLIGATORIO: además del resumen descripcion_visual del bloque, añade escenas_visuales, una entrada por CADA frase
completa de texto, en el mismo orden: [{"texto":"Frase literal completa.","descripcion_visual":"Acción concreta de ESTA frase.",
"personajes_visibles":["ID"]}]. Copia la frase literal, sin anotaciones de voz. No resumas varias frases en una entrada.
Las escenas consecutivas deben avanzar: conserva identidades y contexto, pero no reinicies la misma animación
ni repitas la descripción con distinta velocidad. Cada entrada se anima solo durante su propia frase.
Estas reglas de representabilidad prevalecen sobre sugerencias visuales genéricas del tono; conserva el sentido del relato.
""" + instruccion_utileria_stickman() + instruccion_tiempo_visual() + direccion_color.instruccion(estilo) + capitulos_guion.INSTRUCCION


def preparar_intervenciones(datos, bloques, opciones):
    """Valida el reparto antes de TTS. No permite voces o IDs inventados por IA."""
    modo = opciones.get("sistema_personajes") or {}
    if not modo.get("generar_personajes"):
        return []
    manuales = activos(opciones)
    reparto = {p["id"]: p for p in manuales}
    nombres = {p["nombre"].casefold() for p in manuales}
    automaticos = []
    crudos = datos.get("personajes_automaticos") or []
    if not isinstance(crudos, list):
        raise ValueError("personajes_automaticos debe ser una lista")
    for f in crudos:
        if not isinstance(f, dict) or not re.fullmatch(r"auto_[a-zA-Z0-9_-]{1,70}", str(f.get("id") or "")):
            raise ValueError("el guion devolvió un identificador de personaje automático no válido")
        if f["id"] in reparto or str(f.get("nombre") or "").strip().casefold() in nombres:
            raise ValueError("el guion duplicó un personaje; utiliza su identificador original")
        if f.get("categoria", "personaje") != "personaje":
            raise ValueError("el reparto automático solo puede añadir personajes; el narrador personalizado es único")
        if not str(f.get("nombre") or "").strip() or not str(f.get("descripcion") or "").strip():
            raise ValueError("el personaje automático necesita nombre y descripción")
        limpio = {"id": f["id"], "nombre": str(f["nombre"]).strip()[:120],
                  "descripcion": str(f["descripcion"]).strip()[:4000], "categoria": "personaje"}
        automaticos.append(limpio)
        reparto[limpio["id"]] = limpio
        nombres.add(limpio["nombre"].casefold())
    for b in bloques:
        if any(k not in b for k in ("personaje_id", "personajes_visibles", "descripcion_visual")):
            raise ValueError(f"{b['id']}: identifica el hablante, los personajes_visibles y la descripcion_visual de cada intervención")
        ident = b.get("personaje_id", "")
        if not isinstance(ident, str) or not isinstance(b.get("descripcion_visual", ""), str):
            raise ValueError(f"{b['id']}: el ID y la descripción visual deben ser texto")
        if not ident and not solo_personajes(opciones):
            ident = next((p["id"] for p in manuales if p["categoria"] == "narrador"), "")
        if ident and ident not in reparto:
            raise ValueError(f"{b['id']}: personaje desconocido {ident}; usa un ID del reparto")
        f = reparto.get(ident) or {}
        if not dialogos_habilitados(opciones) and f.get("categoria") == "personaje":
            raise ValueError(f"{b['id']}: Incorporar diálogos está desactivado; solo se permite narración, sin intervenciones habladas de personajes")
        if solo_personajes(opciones) and (not ident or f.get("categoria") == "narrador"):
            raise ValueError(f"{b['id']}: el modo sin voz general requiere diálogo identificado de un personaje, sin narrador")
        if solo_personajes(opciones) and not str(f.get("voz_id") or "").strip():
            raise ValueError(f"{b['id']}: {f.get('nombre') or ident} no tiene voz propia asignada; solo pueden hablar personajes con voz asignada")
        visibles = b.get("personajes_visibles") or []
        if not isinstance(visibles, list) or any(not isinstance(p, str) or p not in reparto for p in visibles):
            raise ValueError(f"{b['id']}: referencia visual a un personaje desconocido")
        if not modo.get("incorporar_voz", True):
            visibles = [p for p in visibles if reparto[p].get("categoria") != "narrador"]
        b.update(personaje_id=ident, personaje_nombre=f.get("nombre") or "Narración",
                 categoria=f.get("categoria") or "narrador", personajes_visibles=list(dict.fromkeys(visibles)),
                 voz_id=(f.get("voz_id") if f.get("categoria") == "personaje" else "") or modo.get("voz_id") or "")
        if modo.get("stickman") and "escenas_visuales" not in b:
            raise ValueError(f'{b["id"]}: Stickman necesita escenas_visuales, una descripción por frase')
        if "escenas_visuales" in b:
            from pasos import marcas_tts
            frases = medios.motor("guion/segmentar.py").frases_del_texto(marcas_tts.limpiar(b["texto"]))
            visuales = b["escenas_visuales"]
            if not isinstance(visuales, list) or len(visuales) != len(frases):
                raise ValueError(f'{b["id"]}: escenas_visuales necesita una entrada por frase completa')
            descripciones = set()
            for frase, visual in zip(frases, visuales):
                if (not isinstance(visual, dict) or visual.get("texto") != frase
                        or not isinstance(visual.get("descripcion_visual"), str) or not visual["descripcion_visual"].strip()):
                    raise ValueError(f'{b["id"]}: cada escena visual necesita su frase literal y una descripción no vacía')
                ids = visual.get("personajes_visibles")
                if not isinstance(ids, list) or any(not isinstance(p, str) or p not in reparto for p in ids):
                    raise ValueError(f'{b["id"]}: personajes desconocidos en escenas_visuales')
                descripcion = medios.normalizar_texto(visual["descripcion_visual"])
                if descripcion in descripciones:
                    raise ValueError(f'{b["id"]}: las frases deben avanzar visualmente, sin repetir la misma descripción')
                descripciones.add(descripcion)
                if opciones.get('_exigir_colores_escena') and not visual.get('colores'):
                    raise ValueError(f'{b["id"]}: cada escena visual necesita colores principales separados por comas')
                if 'colores' in visual:
                    from pasos import direccion_color
                    visual['colores'] = direccion_color.normalizar(visual['colores'])
                    if opciones.get('_exigir_colores_escena') and not visual['colores']:
                        raise ValueError(f'{b["id"]}: colores no puede estar vacío')
    return automaticos


def metadatos(bloque):
    return {k: copy.deepcopy(bloque[k]) for k in CAMPOS_INTERVENCION if k in bloque}


def aplicar_voces(bloques, opciones, voz_general):
    validar_voces(opciones)
    reparto = {p["id"]: p for p in activos(opciones)}
    for b in bloques:
        if solo_personajes(opciones):
            f = reparto.get(b.get("personaje_id")) or {}
            if f.get("categoria") != "personaje" or not str(f.get("voz_id") or "").strip():
                raise ValueError(f"{b['id']}: regenera el guion para usar únicamente personajes con voz propia, sin narrador.")
        if "personaje_id" not in b:
            continue
        f = reparto.get(b["personaje_id"]) or {}
        b["voz_id"] = ((f.get("voz_id") if f.get("categoria") == "personaje" else "") or voz_general)
        if f:
            b["personaje_nombre"] = f["nombre"]
            b["categoria"] = f["categoria"]
    return bloques


def integrar_catalogo(catalogo, documento, opciones):
    resultado = copy.deepcopy(catalogo)
    if not (opciones.get("sistema_personajes") or {}).get("generar_personajes"):
        return resultado
    reparto = resultado.setdefault("reparto", {})
    identidades = activos(opciones) + (documento.get("personajes_automaticos") or [])
    alias = {}
    for f in identidades:
        for clave, spec in list(reparto.items()):
            if clave == f["id"] or medios.normalizar_texto(clave.replace("_", " ")) == medios.normalizar_texto(f["nombre"]) or medios.normalizar_texto(spec.get("nombre") or "") == medios.normalizar_texto(f["nombre"]):
                alias[clave] = f["id"]
                reparto.pop(clave)
        reparto[f["id"]] = dict(f, palabras=[f["nombre"].lower()], grupo=False)
    for beat in resultado.get("beats") or []:
        if isinstance(beat.get("personajes"), list):
            beat["personajes"] = list(dict.fromkeys(alias.get(p, p) for p in beat["personajes"]))
    return resultado


def aplicar_a_escenas(escenas, documento, opciones=None):
    bloques = {b["id"]: b for b in documento.get("guion") or []}
    observador = personaje_pov(opciones or {})
    ocurrencias = {}
    for e in escenas:
        if observador:
            # Conserva la clave de los planes ya guardados: ahora admite ambas categorías.
            e["perspectiva_narrador"] = {k: observador[k] for k in ("id", "nombre", "descripcion")}
        b = bloques.get((e.get("origen") or {}).get("bloque")) or {}
        if "personaje_id" not in b:
            continue
        direccion_catalogo = e.get("prompt") or ""
        actores_catalogo = list(e.get("personajes") or [])
        e.update(metadatos(b))
        # El bloque puede contener varias frases: nunca repartir su secuencia
        # visual completa en cada una, reiniciándola a distinta velocidad.
        visuales = b.get("escenas_visuales") or []
        if visuales:
            clave = medios.normalizar_texto(e.get("narracion") or "")
            candidatos = [v for v in visuales if medios.normalizar_texto(v["texto"]) == clave]
            repeticion = ocurrencias.get((b["id"], clave), 0)
            ocurrencias[b["id"], clave] = repeticion + 1
            if repeticion < len(candidatos):
                e.update(descripcion_visual=candidatos[repeticion]["descripcion_visual"],
                         personajes_visibles=list(candidatos[repeticion]["personajes_visibles"]))
                if 'colores' in candidatos[repeticion]:
                    e['colores'] = candidatos[repeticion]['colores']
            else:
                # Una edición posterior de la voz puede dejar el ancla antigua.
                # Conserva la dirección del catálogo, no otra frase del bloque.
                e.update(descripcion_visual=direccion_catalogo, personajes_visibles=actores_catalogo)
            e.pop("escenas_visuales", None)
        e["intervencion"] = dict(metadatos(e), texto=e.get("narracion") or "", escena_id=e["id"], bloque_id=b["id"])
        e["personajes"] = list(e.get("personajes_visibles") or [])
        if e.get("descripcion_visual"):
            e["prompt"] = e["descripcion_visual"]


def exigir_visuales_ia(proyecto, plan, carpeta):
    """Un montaje tampoco puede recuperar stock de una versión anterior."""
    if params_de(proyecto, "assets").get("generar_personajes") is not True:
        return
    for escena in plan.get("escenas") or []:
        if escena.get("medio_usuario"):
            continue
        ficha = medios.leer_json(os.path.join(carpeta, "escenas", escena["id"] + ".json"), {}) or {}
        if any(f.get(k) for f in (escena, ficha) for k in ("medio_biblioteca", "recurso_biblioteca")):
            raise RuntimeError("Generar personajes requiere imágenes IA. Sustituye los recursos de "
                               "biblioteca pendientes antes de montar el vídeo.")


def generar_imagen(descripcion, destino, referencias=(), tiene_personaje=False):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if os.environ.get("ESTUDIO_SIMULAR") == "1":
        imagen = Image.new("RGB", (768, 1152), "#657a91")
    else:
        png, _ = medios.motor("imagen_openai/imagen.py").generar(
            "Create a single full-body character reference, entire body from head to feet inside the frame, "
            "neutral uncluttered background, no text, no panels. Preserve facial features, clothing, colours, accessories and proportions "
            "of the character reference when provided; apply the requested changes. Follow the supplied visual style references. "
            + ("Reference image 1 is the current character: preserve its identity. Remaining references specify only the drawing style. "
               if tiene_personaje else "All attached references specify only the visual style; create the new character described below, without copying their identities. ")
            + "Character description: " + descripcion, list(referencias), quality="medium", tamano="vertical")
        with Image.open(io.BytesIO(png)) as original:
            imagen = original.convert("RGB")
    try:
        imagen.save(destino, "PNG")
    finally:
        imagen.close()
