"""Contratos de interfaz abstracta para la vista de Registros estilo Excel."""

from __future__ import annotations

from typing import Any, Protocol

from domain.models import TimerItem


class IRecordsView(Protocol):
    """Protocolo de Vista Pasiva para la tabla analítica de registros."""

    def render_items(self, items: list[TimerItem]) -> None:
        """Actualiza las filas visibles de la tabla con los items procesados."""
        ...

    def update_filter_summary(self, active_filters_count: int, filtered_count: int, total_count: int) -> None:
        """Actualiza el contador de registros filtrados vs total en la barra de estado."""
        ...

    def set_empty_state(self, is_empty: bool) -> None:
        """Muestra u oculta la tabla si no existe un registro activo."""
        ...
