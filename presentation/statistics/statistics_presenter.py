"""Presenter puro (MVP) para la vista de estadísticas y analítica temporal.

Este módulo implementa el patrón Model-View-Presenter (Passive View) para la pestaña
de Estadísticas en Python puro, sin ninguna dependencia de Qt o PySide6.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.application_service import StudyApplicationService
    from presentation.statistics.interfaces import IStatisticsView


class StatisticsPresenter:
    """Presenter desacoplado que orquesta las tres dimensiones analíticas (General, Semanal, Diario)."""

    def __init__(self, view: IStatisticsView, application: StudyApplicationService) -> None:
        self.view = view
        self.application = application

        self._active_subtab: int = 0  # 0: General, 1: Semanal, 2: Diario
        self._current_week_date: date = date.today()
        self._current_day_date: date = date.today()
        self._top_effort_criteria: str = "time"  # "time", "retries", "pb"

    @property
    def active_subtab(self) -> int:
        return self._active_subtab

    @property
    def current_week_date(self) -> date:
        return self._current_week_date

    @property
    def current_day_date(self) -> date:
        return self._current_day_date

    @property
    def top_effort_criteria(self) -> str:
        return self._top_effort_criteria

    def refresh_all(self) -> None:
        """Sincroniza y refresca la vista según el estado actual de la aplicación."""
        if not self.application.is_record_open:
            self.view.set_empty_state(True)
            return

        self.view.set_empty_state(False)
        self.refresh_general()
        self.refresh_weekly()
        self.refresh_daily()

    def set_subtab(self, index: int) -> None:
        """Cambia la sub-pestaña activa (0: General, 1: Semanal, 2: Diario)."""
        if index not in (0, 1, 2):
            return
        self._active_subtab = index
        self.view.set_active_subtab(index)
        if not self.application.is_record_open:
            self.view.set_empty_state(True)
            return

        if index == 0:
            self.refresh_general()
        elif index == 1:
            self.refresh_weekly()
        elif index == 2:
            self.refresh_daily()

    def refresh_general(self) -> None:
        """Calcula y proyecta las métricas de la dimensión General."""
        if not self.application.is_record_open:
            return

        stats = self.application.get_statistics()
        streak_days, total_study_days = self.application.get_streak_days()
        evolution_data = self.application.get_cumulative_evolution_data()
        top_effort = self.application.get_top_effort_exercises_advanced(
            criteria=self._top_effort_criteria,
            limit=5,
        )
        heatmap_data = self.application.get_course_heatmap_data()
        hourly_data = self.application.get_24h_hourly_distribution()

        file_name = (
            self.application.record_path.stem
            if self.application.record_path
            else self.application.record.record_name
        )

        self.view.render_general_tab(
            stats=stats,
            streak_days=streak_days,
            total_study_days=total_study_days,
            evolution_data=evolution_data,
            top_effort=top_effort,
            heatmap_data=heatmap_data,
            hourly_data=hourly_data,
            file_name=file_name,
        )

    def refresh_weekly(self) -> None:
        """Calcula y proyecta las métricas de la semana activa."""
        if not self.application.is_record_open:
            return

        summary = self.application.get_weekly_stats_summary(self._current_week_date)
        self.view.render_weekly_tab(summary)

    def refresh_daily(self) -> None:
        """Calcula y proyecta las métricas y log de intentos del día activo."""
        if not self.application.is_record_open:
            return

        summary = self.application.get_daily_stats_summary(self._current_day_date)
        self.view.render_daily_tab(summary)

    def navigate_week(self, offset_weeks: int) -> None:
        """Navega a semanas anteriores (-1) o siguientes (+1)."""
        self._current_week_date += timedelta(days=7 * offset_weeks)
        self.refresh_weekly()

    def go_to_current_week(self) -> None:
        """Restablece la navegación semanal a la semana actual."""
        self._current_week_date = date.today()
        self.refresh_weekly()

    def navigate_day(self, offset_days: int) -> None:
        """Navega a días anteriores (-1) o posteriores (+1)."""
        self._current_day_date += timedelta(days=offset_days)
        self.refresh_daily()

    def go_to_today(self) -> None:
        """Restablece la navegación diaria a la fecha de hoy."""
        self._current_day_date = date.today()
        self.refresh_daily()

    def set_day_date(self, target_date: date) -> None:
        """Establece explícitamente una fecha de consulta para la vista diaria."""
        self._current_day_date = target_date
        self.refresh_daily()

    def set_top_effort_criteria(self, criteria: str) -> None:
        """Cambia el criterio de ordenamiento del ranking Top 5 ('time', 'retries', 'pb')."""
        if criteria not in ("time", "retries", "pb"):
            return
        self._top_effort_criteria = criteria
        self.refresh_general()
