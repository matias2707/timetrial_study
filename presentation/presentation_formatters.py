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


def timer_markup(milliseconds: int) -> str:
    """Crea el reloj con milisegundos visualmente secundarios."""
    main, millis = format_timer_milliseconds(milliseconds)
    return f'{main}<span style="font-size: 52%;">{millis}</span>'
