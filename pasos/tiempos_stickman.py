"""Tiempos locales: tolerancia de un microsegundo, nunca de un fotograma."""
import math


def tiempo(valor, minimo, maximo, ruta):
    if (isinstance(valor, bool) or not isinstance(valor, (int, float))
            or not math.isfinite(valor) or valor < minimo - 1e-6 or valor > maximo + 1e-6):
        raise ValueError(f'{ruta}: tiempo {valor!r} fuera del intervalo {minimo:g}–{maximo:g} s')
    return min(maximo, max(minimo, valor))
