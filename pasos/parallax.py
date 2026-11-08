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


def seleccionar(escenas, opciones, semilla=0):
    from pasos import cartelas
    p = normalizar(opciones)
    elegidas = {}
    if not p["activo"]:
        return elegidas
    numero = 0
    # Orden reproducible y reparto equilibrado entre las imágenes ANIMADAS.
    # Los proyectos con el antiguo selector único mantienen su movimiento.
    movimientos = sorted(p.get("movimientos") or [],
                         key=lambda m: huella(f"{semilla}:movimiento:{m}"))
    for escena in escenas:
        medio = escena.get("medio_usuario") or escena.get("medio_biblioteca") or {}
        if medio.get("tipo") == "video" or cartelas.sin_imagen(escena):
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
    return elegidas
