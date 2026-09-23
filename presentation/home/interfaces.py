"""Contrato de interfaz abstracta para la vista principal del cronómetro (Home).

Define los métodos que el Presenter invoca sobre la vista pasiva, completamente
desacoplado de la implementación en PySide6.
"""

from __future__ import annotations

from typing import Any, Protocol


class IHomeView(Protocol):
    """Protocolo de Vista Pasiva para la pantalla del cronómetro."""

    def update_clock_display(self, exercise_formatted: str, break_formatted: str) -> None:
        """Actualiza el texto de los dígitos de estudio y descanso."""
        ...

    def update_session_state(self, mode: str, is_paused: bool, is_editing: bool) -> None:
        """Actualiza los estilos visuales y textos de los botones según el modo activo."""
        ...

    def update_personal_best(self, pb_text: str) -> None:
        """Muestra el récord personal o indicador de primer intento."""
        ...

    def update_daily_kpis(self, study_time: str, completed_count: int, attempts_count: int) -> None:
        """Actualiza las micro-tarjetas de métricas de la jornada actual."""
        ...

    def set_location_inputs(self, section_type: str, section_number: int, exercise: int, inciso: int | None) -> None:
        """Sincroniza los controles numéricos con las coordenadas de la sesión."""
        ...

    def set_controls_locked(self, locked: bool) -> None:
        """Bloquea o desbloquea los selectores de ubicación durante la sesión activa."""
        ...

    def set_status_message(self, message: str) -> None:
        """Actualiza la etiqueta de estado textual."""
        ...

    def set_empty_state(self, is_empty: bool) -> None:
        """Muestra u oculta los controles principales si no hay ningún archivo abierto."""
        ...
