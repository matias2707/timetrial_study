"""Contratos de interfaz abstracta para la vista del Organizador de Estudio."""

from __future__ import annotations

from typing import Any, Protocol

from application.organizer_service import OrganizedSectionStatus, PlannedSectionStatus


class IOrganizerView(Protocol):
    """Protocolo de Vista Pasiva para el Organizador."""

    def render_sections_overview(self, sections: list[OrganizedSectionStatus], completion_rate: float) -> None:
        """Renderiza la lista de secciones organizadas y la barra de progreso global."""
        ...

    def show_boundary_warning(self, message: str) -> None:
        """Muestra una advertencia cuando la navegación excede los límites organizados."""
        ...

    def set_empty_state(self, is_empty: bool) -> None:
        """Muestra u oculta la interfaz según si existe un registro activo."""
        ...


# Alias de retrocompatibilidad
IPlannerView = IOrganizerView
