"""Interfaces y protocolos abstractos (MVP) para la vista de estadísticas."""

from __future__ import annotations

from typing import Any, Protocol

from application.statistics_service import (
    CumulativeEvolutionData,
    DailyStatsSummary,
    RecordStatistics,
    TopEffortExercise,
    WeeklyStatsSummary,
)


class IStatisticsView(Protocol):
    """Protocolo pasivo para la vista de estadísticas de Study Timetrial."""

    def set_empty_state(self, is_empty: bool) -> None:
        """Muestra u oculta el estado vacío cuando no hay materia activa cargada."""
        ...

    def render_general_tab(
        self,
        stats: RecordStatistics,
        streak_days: int,
        total_study_days: int,
        evolution_data: CumulativeEvolutionData,
        top_effort: list[TopEffortExercise],
        heatmap_data: dict[str, Any],
        hourly_data: dict[int, int],
        file_name: str,
    ) -> None:
        """Renderiza la dimensión General (KPIs macro, evolución, heatmap, ranking, 24h)."""
        ...

    def render_weekly_tab(
        self,
        summary: WeeklyStatsSummary,
    ) -> None:
        """Renderiza la dimensión Semanal (selector, KPIs de 7 días, gráfico semanal y lista)."""
        ...

    def render_daily_tab(
        self,
        summary: DailyStatsSummary,
    ) -> None:
        """Renderiza la dimensión Diaria (selector de fecha, KPIs de jornada y log cronológico)."""
        ...

    def set_active_subtab(self, index: int) -> None:
        """Establece visualmente la sub-pestaña activa (0: General, 1: Semanal, 2: Diario)."""
        ...
