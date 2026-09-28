"""Adaptadores de formato para representar tiempos en la interfaz Qt.

Este modulo pertenece a la capa de presentacion: convierte texto y milisegundos
sin modificar las entidades del dominio ni el formato persistido en JSON.
"""


from domain.time_utils import (
    format_hh_mm,
    format_hh_mm_ss,
    format_milliseconds,
    parse_milliseconds,
)


def format_timer_milliseconds(milliseconds: int) -> tuple[str, str]:
    """Devuelve la parte principal y los milisegundos del reloj de sesion."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}", f".{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}", f".{millis:03d}"


def format_timer_units(milliseconds: int) -> tuple[int, int, int]:
    """Devuelve (horas, minutos, segundos) de una duración en milisegundos."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, _ = divmod(remainder, 1_000)
    return hours, minutes, seconds


def timer_markup(milliseconds: int | str, show_hours_always: bool = True) -> str:
    """Crea la representación tipográfica de los contadores con unidades inline suaves.

    Formato: 00h 25m 14s (o 25m 14s si show_hours_always=False y hours == 0).
    Las letras de unidad ('h', 'm', 's') se presentan con tamaño relativo (52%) y
    opacidad atenuada (65%) para una lectura inequívoca sin competir visualmente
    con los dígitos principales.
    """
    if isinstance(milliseconds, str):
        clean = milliseconds.split(".")[0].strip()
        parts = clean.split(":")
        if len(parts) == 3:
            try:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                return clean
        elif len(parts) == 2:
            try:
                hours, minutes, seconds = 0, int(parts[0]), int(parts[1])
            except ValueError:
                return clean
        else:
            try:
                hours, minutes, seconds = format_timer_units(int(milliseconds))
            except (ValueError, TypeError):
                return str(milliseconds)
    else:
        hours, minutes, seconds = format_timer_units(int(milliseconds))

    unit_h = '<span style="font-size: 52%; opacity: 0.65; font-weight: 500;">h</span>'
    unit_m = '<span style="font-size: 52%; opacity: 0.65; font-weight: 500;">m</span>'
    unit_s = '<span style="font-size: 52%; opacity: 0.65; font-weight: 500;">s</span>'

    if hours > 0 or show_hours_always:
        return f"{hours:02d}{unit_h} {minutes:02d}{unit_m} {seconds:02d}{unit_s}"

    return f"{minutes:02d}{unit_m} {seconds:02d}{unit_s}"
