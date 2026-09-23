"""Utilidades puras de conversión y formateo de tiempo en milisegundos."""

from __future__ import annotations


def format_milliseconds(milliseconds: int) -> str:
    """Convierte milisegundos al formato completo HH:MM:SS:mmm."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{millis:03d}"


def format_hh_mm(milliseconds: int) -> str:
    """Convierte milisegundos al formato compacto hh:mm."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes = remainder // 60_000
    return f"{hours:02d}:{minutes:02d}"


def format_hh_mm_ss(milliseconds: int) -> str:
    """Convierte milisegundos al formato estándar hh:mm:ss."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds = remainder // 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_milliseconds(value: str) -> int:
    """Parsea una cadena de tiempo (SS:SSS, MM:SS:SSS o HH:MM:SS:SSS) a milisegundos."""
    parts = value.strip().split(":")
    if len(parts) not in (2, 3, 4):
        raise ValueError("Use SS:SSS, MM:SS:SSS o HH:MM:SS:SSS")

    try:
        values = [int(part) for part in parts]
    except ValueError as error:
        raise ValueError("El tiempo solo puede contener números") from error

    if len(values) == 2:
        hours, minutes, seconds, millis = 0, 0, *values
    elif len(values) == 3:
        hours, minutes, seconds, millis = 0, *values
    else:
        hours, minutes, seconds, millis = values

    if min(hours, minutes, seconds, millis) < 0 or minutes > 59 or seconds > 59 or millis > 999:
        raise ValueError("Tiempo inválido")

    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis
