"""Audita una entrega y, con --generar, compara el flujo nuevo en una copia minima.

No modifica el proyecto original ni genera voces, imagenes o animaciones.
La generacion usa el CLI y cuota reales. Sin --generar solo prepara la auditoria.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import textwrap


def leer(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proyecto", required=True, type=Path)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--generar", action="store_true")
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    os.environ["ESTUDIO_ESTADISTICAS"] = str(args.salida / "estadisticas.json")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from nucleo import Estado, Proyecto
    from pasos import comun, fuentes, marcas_tts, p3_guion, personajes

    original = Proyecto(str(args.proyecto.resolve()))
    version = args.proyecto / "pasos" / "guion" / f"v{args.version}"
    doc = leer(version / "guion.json")
    prompt = (version / "instruccion_1.txt").read_text(encoding="utf-8")
    brief = comun.leer_salida(original, "brief", "brief.json")
    ingesta = comun.leer_salida(original, "ingesta", "ingesta.json")
    material = "\n\n".join(t["texto"] for t in ingesta["transcript"])
    if brief["instrucciones"] not in prompt or any(t["texto"] not in prompt for t in ingesta["transcript"]):
        raise RuntimeError("el brief o el material activos ya no coinciden con la version; no es una comparacion controlada")
    estado_original = Estado(original)
    params = estado_original.params("guion")
    # Congela los ajustes efectivos de la entrega, no los defectos del dia.
    params.update({k: doc[k] for k in ("modelo", "esfuerzo", "prompt_general", "anotaciones_voz") if k in doc})
    params.update(escaleta_previa=True, regenerar_desde_cero=True, bloques={})
    auditoria = dict(modelo=doc["modelo"], esfuerzo=doc["esfuerzo"],
        duracion_objetivo_s=brief["duracion_objetivo_s"],
        presupuesto_palabras=brief["presupuesto_palabras"],
        palabras_material=comun.contar_palabras(material), palabras_anterior=doc["palabras"],
        caracteres_prompt_anterior=len(prompt), material=material,
        material_sha256=hashlib.sha256(material.encode()).hexdigest(),
        guia=brief["instrucciones"], indicaciones=doc.get("prompt_general") or "",
        original_solo_lectura=str(version.resolve()))
    comun.escribir_json(str(args.salida / "auditoria.json"), auditoria)
    (args.salida / "anterior.txt").write_text("\n\n".join(
        marcas_tts.limpiar(b["texto"]) for b in doc["guion"]), encoding="utf-8")
    print(json.dumps({k: v for k, v in auditoria.items() if k not in ("guia", "material")}, ensure_ascii=False, indent=2), flush=True)
    print("Guia efectiva:\n" + textwrap.fill(brief["instrucciones"], 100), flush=True)
    if not args.generar:
        return

    copia = Proyecto.crear(str(args.salida), "Comparacion editorial")
    estado = Estado(copia)
    for paso, nombre, contenido in (("ingesta", "ingesta.json", ingesta), ("brief", "brief.json", brief)):
        comun.escribir_json(os.path.join(copia.ruta_trabajo(paso), nombre), contenido)
        estado.completar(paso, {})
    assets = estado_original.params("assets")
    estado.actualizar_params("assets", {k: assets[k] for k in (
        "generar_personajes", "estilo", "incorporar_dialogos") if k in assets})
    voz = estado_original.params("voz")
    estado.actualizar_params("voz", {k: voz[k] for k in ("voz_id", "incorporar_voz") if k in voz})
    # Contexto efectivo de la modalidad, sin copiar assets ni unidades pagadas.
    params["sistema_personajes"] = personajes.contexto(assets, voz)
    estado.actualizar_params("guion", params)
    mensajes = set()
    ultima_fase = [None]

    def avisar(valor, mensaje=""):
        fase = mensaje.split(";", 1)[0]
        if mensaje and mensaje not in mensajes and fase != ultima_fase[0]:
            print(mensaje, flush=True)
            mensajes.add(mensaje)
            ultima_fase[0] = fase

    try:
        salidas = p3_guion.ejecutar(copia, params, avisar)
    except Exception as fallo:
        comun.escribir_json(str(args.salida / "fallo.json"), dict(error=str(fallo),
            trabajo=copia.ruta_trabajo("guion", crear=False)))
        raise
    trabajo = Path(copia.ruta_trabajo("guion", crear=False))
    nuevo = leer(trabajo / "guion.json")
    (args.salida / "nuevo.txt").write_text("\n\n".join(
        marcas_tts.limpiar(b["texto"]) for b in nuevo["guion"]), encoding="utf-8")
    resumen = dict(palabras=nuevo["palabras"], modelo=nuevo["modelo"], esfuerzo=nuevo["esfuerzo"],
        fases=nuevo.get("fases_guion"), tokens=salidas["tokens"], segundos=salidas["segundos"],
        dentro_de_horquilla=salidas["dentro_de_horquilla"], avisos=salidas["avisos"],
        caracteres_prompt_narracion=len((trabajo / "instruccion_1.txt").read_text(encoding="utf-8")),
        trabajo=str(trabajo))
    comun.escribir_json(str(args.salida / "resultado.json"), resumen)
    print(json.dumps(resumen, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
