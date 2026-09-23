"""Contratos de interfaz abstracta para la vista del Planificador de Estudio."""

from __future__ import annotations

from typing import Any, Protocol

from application.planner_service import PlannedSectionStatus


class IPlannerView(Protocol):
    """Protocolo de Vista Pasiva para el Planificador."""

    def render_sections_overview(self, sections: list[PlannedSectionStatus], completion_rate: float) -> None:
        """Renderiza la lista de secciones planificadas y la barra de progreso global."""
        ...

    def show_boundary_warning(self, message: str) -> None:
        """Muestra una advertencia cuando la navegación excede los límites planificados."""
        ...

    def set_empty_state(self, is_empty: bool) -> None:
        """Muestra u oculta la interfaz según si existe un registro activo."""
        ...
