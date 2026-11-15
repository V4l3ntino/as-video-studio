"""Contratos editoriales previos a la locucion; sin HTTP ni llamadas al modelo."""
import copy
import json
import math
from pasos import capitulos_guion


PAUTA = """Selecciona un recorrido para el espectador, no un indice del tema.
Entrega pronto una primera respuesta y desarrolla despues preguntas distintas:
conducta observable, mecanismo, evidencia, consecuencia, segun el material.
Una escena distinta que repite la tesis no es otro descubrimiento. El contexto
historico entra solo donde ayuda a responder la pregunta activa. El cierre
entrega una conclusion concreta, sin otra lista ni recapitulaciones sucesivas.
Un caso o experimento va junto a su pregunta. No reserves un dato solo porque
es curioso: si la guia pide una revelacion final, elige una que pague la promesa,
sin aplazar la respuesta principal. No conviertas asociaciones o ejemplos en
causas demostradas ni en reglas sobre todas las personas.
Comprueba que la recompensa reservada no se haya explicado ya en otro tramo.
Si ya esta explicada, elimina el anuncio y usa una conclusion util, sin fingir
un secreto. No conviertas conceptos relacionados en un unico diagnostico ni
en polos de una sola escala cuando el material no respalda esa equivalencia.
Las indicaciones expresas del video mandan; la guia del canal es una preferencia
adaptable al genero, material y duracion. No inventes fuentes, cifras o estudios.
"""


def instruccion_escaleta(material, guia, indicaciones, presupuesto, idioma, escaso=False,
                          contexto=None):
    base = ("El material solo aporta un tema o notas muy breves, no un dosier verificado. "
            "Planea una explicacion prudente de conocimientos generales; no inventes "
            "fechas, porcentajes ni atribuciones bibliograficas para darle autoridad. "
            "Registra en limites lo que necesitaria fuentes y no lo uses como evidencia."
            if escaso else
            "Los hechos proceden del material. Selecciona los necesarios sin alterar su certeza.")
    return ("Eres editor de un video de YouTube. Decide la escaleta ANTES de redactar. "
            "No escribas narracion, bloques Bxxx, SSML ni descripciones visuales.\n"
            + PAUTA + "\n" + base + "\n"
            + (capitulos_guion.INSTRUCCION if (contexto or {}).get('capitulos_visuales') else '')
            + json.dumps(dict(material=material, guia_del_canal=guia,
                indicaciones_del_video=indicaciones, palabras_objetivo=presupuesto,
                idioma=idioma, restricciones=contexto or {}), ensure_ascii=False)
            + '\nDevuelve SOLO JSON: {"titulo":"...","pregunta_central":"...",'
              '"respuesta_temprana":"...","promesa_final":"o cadena vacia",'
              '"recompensa_final":"...","voz":"sintesis breve del registro solicitado",'
              '"limites":["..."],"descartes":["contenido que no entra y por que"],'
              '"tramos":[{"id":"T01","pregunta":"...","aporte_nuevo":"...",'
              '"recurso":"situacion, contraste, explicacion, evidencia o aplicacion",'
              '"hechos":["hechos o ideas que se explican aqui"],'
              '"palabras":100,"puente":"duda concreta o cadena vacia"}]}. '
              'Los presupuestos de los tramos deben sumar el objetivo. '
              'La cantidad de tramos depende del relato, no de una plantilla fija. '
              'Declara solo los descubrimientos que los hechos de ese tramo permiten contar.'
            + ('\nAñade capitulos:[{numero:1,titulo:"Título breve del punto",estilo:"arctic|ember|mixto|sakura|retro",'
               'tramos:["T02","T03"]}]. Agrupa varios tramos si responden a la misma pregunta. '
               'Todo el desarrollo queda asignado en orden, sin compartir tramos; solo el primer tramo '
               '(gancho) y el último (cierre) pueden quedar fuera si corresponde. La cantidad de capítulos '
               'depende del material, duración y estructura pedida; no impongas cuatro capítulos por copiar un ejemplo.'
               if (contexto or {}).get('capitulos_visuales') else ''))


def validar_escaleta(datos, presupuesto, exigir_capitulos=False):
    """Valida estructura y normaliza el reparto sin repetir por aritmetica."""
    if not isinstance(datos, dict):
        raise ValueError("la escaleta debe ser un objeto")
    salida = {}
    for campo in ("titulo", "pregunta_central", "respuesta_temprana", "promesa_final",
                  "recompensa_final", "voz"):
        texto = datos.get(campo)
        if not isinstance(texto, str) or (campo != "promesa_final" and not texto.strip()):
            raise ValueError(f"escaleta: falta {campo}")
        salida[campo] = texto.strip()
    for campo in ("limites", "descartes"):
        lista = datos.get(campo)
        if not isinstance(lista, list) or not all(isinstance(t, str) for t in lista):
            raise ValueError(f"escaleta: {campo} debe ser una lista de textos")
        salida[campo] = [t.strip() for t in lista if t.strip()]
    tramos = datos.get("tramos")
    objetivo = max(1, int(presupuesto))
    if not isinstance(tramos, list) or not tramos or len(tramos) > objetivo:
        raise ValueError("escaleta: faltan tramos o hay mas tramos que palabras")
    salida["tramos"] = []
    pesos = []
    for numero, tramo in enumerate(tramos, 1):
        if not isinstance(tramo, dict):
            raise ValueError("escaleta: cada tramo debe ser un objeto")
        limpio = {"id": f"T{numero:02d}"}
        for campo in ("pregunta", "aporte_nuevo", "recurso", "puente"):
            texto = tramo.get(campo)
            if not isinstance(texto, str) or (campo != "puente" and not texto.strip()):
                raise ValueError(f"escaleta: tramo {numero} sin {campo}")
            limpio[campo] = texto.strip()
        hechos = tramo.get("hechos")
        if not isinstance(hechos, list) or not hechos or not all(isinstance(h, str) and h.strip() for h in hechos):
            raise ValueError(f"escaleta: tramo {numero} sin hechos o ideas")
        limpio["hechos"] = [h.strip() for h in hechos]
        peso = tramo.get("palabras")
        if type(peso) is not int or peso <= 0:
            raise ValueError(f"escaleta: tramo {numero} sin presupuesto positivo")
        pesos.append(peso)
        salida["tramos"].append(limpio)
    # Un minimo por tramo y restos mayores: suma exacta, estable y sin ceros.
    libre = objetivo - len(tramos)
    cuotas = [libre * p / sum(pesos) for p in pesos]
    reparto = [1 + math.floor(c) for c in cuotas]
    orden = sorted(range(len(tramos)), key=lambda i: cuotas[i] - math.floor(cuotas[i]), reverse=True)
    for i in orden[:objetivo - sum(reparto)]:
        reparto[i] += 1
    for tramo, palabras in zip(salida["tramos"], reparto):
        tramo["palabras"] = palabras
    if exigir_capitulos or 'capitulos' in datos:
        salida['capitulos'] = capitulos_guion.validar_plan(datos.get('capitulos'), salida['tramos'])
    return salida


def plan_del_texto(escaleta, bloques):
    """Asocia la escaleta previa a bloques reales, sin pedir otra autoevaluacion."""
    ids = [t["id"] for t in escaleta["tramos"]]
    asignados = [b.get("tramo") for b in bloques]
    if any(t not in ids for t in asignados):
        raise ValueError("cada bloque necesita un tramo de la escaleta")
    if list(dict.fromkeys(asignados)) != ids or asignados != sorted(asignados, key=ids.index):
        raise ValueError("los bloques deben recorrer todos los tramos en el orden de la escaleta")
    plan = {k: escaleta[k] for k in ("pregunta_central", "respuesta_temprana", "promesa_final", "recompensa_final")}
    plan["tramos"] = [dict(
        **{k: t[k] for k in ("pregunta", "aporte_nuevo", "recurso", "puente")},
        bloques=[b["id"] for b in bloques if b["tramo"] == t["id"]])
        for t in escaleta["tramos"]]
    return plan


def aplicar_direccion(datos, bloques, respuesta):
    """La direccion agrega metadatos, nunca cambia palabras, orden ni hablantes."""
    if not isinstance(respuesta, dict) or not isinstance(respuesta.get("bloques"), list):
        raise ValueError("la direccion debe entregar una lista de bloques")
    visuales = respuesta["bloques"]
    if [v.get("id") if isinstance(v, dict) else None for v in visuales] != [b["id"] for b in bloques]:
        raise ValueError("la direccion debe conservar todos los IDs y su orden")
    salida = copy.deepcopy(bloques)
    for bloque, visual in zip(salida, visuales):
        for campo in ("texto", "personaje_id", "capitulo"):
            if campo in visual and visual[campo] != bloque.get(campo):
                raise ValueError(f"la direccion no puede cambiar {campo} en {bloque['id']}")
        for campo in ("personajes_visibles", "descripcion_visual", "escenas_visuales"):
            if campo in visual:
                bloque[campo] = copy.deepcopy(visual[campo])
        if not isinstance(bloque.get("descripcion_visual"), str) or not bloque["descripcion_visual"].strip():
            raise ValueError(f"falta la direccion visual de {bloque['id']}")
    automaticos = copy.deepcopy(datos.get("personajes_automaticos") or [])
    nuevos = respuesta.get("personajes_automaticos") or []
    if not isinstance(nuevos, list):
        raise ValueError("el reparto visual debe ser una lista")
    por_id = {p["id"]: p for p in automaticos}
    for p in nuevos:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str):
            raise ValueError("personaje visual sin ID")
        if p["id"] in por_id and p != por_id[p["id"]]:
            raise ValueError("la direccion no puede cambiar identidades ya publicadas por el redactor")
        if p["id"] not in por_id:
            automaticos.append(copy.deepcopy(p))
            por_id[p["id"]] = p
    return salida, automaticos
