"""Opciones de montaje y selección reproducible de imágenes para DepthFlow."""
import hashlib

MOVIMIENTOS = ("zoom_delante", "zoom_atras", "lateral", "vertical", "diagonal",
               "orbita", "combinado", "aleatorio")
DEFECTOS = {"activo": False, "movimiento": "zoom_delante", "seleccion": "todas",
            "cada": 3, "intensidad": "suave"}


def normalizar(valor=None):
    if valor is None:
        return dict(DEFECTOS)
    if not isinstance(valor, dict) or set(valor) - (set(DEFECTOS) | {"movimientos"}):
        raise ValueError("parallax debe ser un objeto con opciones conocidas")
    p = dict(DEFECTOS, **valor)
    if not isinstance(p["activo"], bool):
        raise ValueError("parallax.activo debe ser un booleano")
    if p["movimiento"] not in MOVIMIENTOS:
        raise ValueError("Movimiento de parallax desconocido")
    if "movimientos" in p:
        valores = p["movimientos"]
        if not isinstance(valores, list) or not valores or any(
                not isinstance(v, str) or v not in MOVIMIENTOS[:-1] for v in valores):
            raise ValueError("Elige al menos un movimiento de parallax conocido")
        p["movimientos"] = list(dict.fromkeys(valores))
        p.pop("movimiento")
    if p["seleccion"] not in ("todas", "cada", "aleatorias"):
        raise ValueError("Selección de imágenes de parallax desconocida")
    if type(p["cada"]) is not int or not 1 <= p["cada"] <= 1000:
        raise ValueError("Animar cada N imágenes requiere un entero entre 1 y 1000")
    if p["intensidad"] not in ("suave", "media", "alta"):
        raise ValueError("Intensidad de parallax desconocida")
    return p


def huella(texto):
    return int(hashlib.sha256(str(texto).encode("utf-8")).hexdigest(), 16)


def ancla_de(escena):
    return " ".join(str(escena.get("narracion") or "").split())


def admite(escena):
    from pasos import cartelas
    medio = escena.get("medio_usuario") or escena.get("medio_biblioteca") or {}
    return medio.get("tipo") != "video" and not cartelas.sin_imagen(escena)


def validar_edicion(datos, escena):
    if not isinstance(datos, dict) or set(datos) - {"activo", "movimiento", "intensidad", "ancla"}:
        raise ValueError("Opciones de parallax por imagen desconocidas")
    if datos.get("ancla") != ancla_de(escena):
        raise ValueError("La escena ha cambiado; vuelve a abrir su efecto parallax")
    if not isinstance(datos.get("activo"), bool):
        raise ValueError("activo debe ser un booleano")
    if datos.get("movimiento") not in MOVIMIENTOS[:-1]:
        raise ValueError("Elige un movimiento de cámara conocido")
    if datos.get("intensidad") not in ("suave", "media", "alta"):
        raise ValueError("Elige una intensidad conocida")
    return {k: datos[k] for k in ("activo", "movimiento", "intensidad", "ancla")}


def ediciones_de(params):
    return {uid.split(":", 1)[1]: unidad["parallax"]
            for uid, unidad in ((params or {}).get("unidades") or {}).items()
            if uid.startswith("escena:") and isinstance(unidad, dict)
            and isinstance(unidad.get("parallax"), dict)}


def seleccionar(escenas, opciones, semilla=0, unidades=None):
    p = normalizar(opciones)
    elegidas = {}
    numero = 0
    # Orden reproducible y reparto equilibrado entre las imágenes ANIMADAS.
    # Los proyectos con el antiguo selector único mantienen su movimiento.
    movimientos = sorted(p.get("movimientos") or [],
                         key=lambda m: huella(f"{semilla}:movimiento:{m}"))
    for escena in escenas:
        if not p["activo"] or not admite(escena):
            continue
        numero += 1
        azar = huella(f"{semilla}:{escena['id']}")
        if p["seleccion"] == "cada" and numero % p["cada"]:
            continue
        if p["seleccion"] == "aleatorias" and azar % 2:
            continue
        movimiento = p.get("movimiento", "zoom_delante")
        if movimientos:
            movimiento = movimientos[len(elegidas) % len(movimientos)]
        elif movimiento == "aleatorio":
            movimiento = MOVIMIENTOS[azar % (len(MOVIMIENTOS) - 1)]
        elegidas[escena["id"]] = dict(p, movimiento=movimiento)
    # Aplicar DESPUÉS del reparto: quitar/añadir una escena no cambia el
    # movimiento asignado a las demás ni invalida sus clips.
    ediciones = ediciones_de({"unidades": unidades})
    for escena in escenas:
        edicion = ediciones.get(escena["id"])
        if not edicion or not admite(escena) or edicion.get("ancla") != ancla_de(escena):
            continue
        if edicion.get("activo"):
            elegidas[escena["id"]] = dict(p, **{k: edicion[k]
                for k in ("activo", "movimiento", "intensidad")})
        else:
            elegidas.pop(escena["id"], None)
    return elegidas
