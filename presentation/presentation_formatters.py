"""Adaptadores de formato para representar tiempos en la interfaz Qt.

Este modulo pertenece a la capa de presentacion: convierte texto y milisegundos
sin modificar las entidades del dominio ni el formato persistido en JSON.
"""


def format_milliseconds(milliseconds: int) -> str:
    """Convierte milisegundos al formato completo usado en registros."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{millis:03d}"


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


def parse_milliseconds(value: str) -> int:
    """Parsea un tiempo compacto o completo y lo convierte en milisegundos."""
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
