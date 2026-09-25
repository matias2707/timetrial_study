"""Pruebas unitarias para StatisticsPresenter (MVP en Python puro)."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from application.application_service import StudyApplicationService
from application.statistics_service import (
    CumulativeEvolutionData,
    DailyStatsSummary,
    RecordStatistics,
    TopEffortExercise,
    WeeklyStatsSummary,
)
from domain.models import Record, TimerItem
from domain.timer_service import TimerService
from infrastructure.storage_service import StorageService
from presentation.statistics.interfaces import IStatisticsView
from presentation.statistics.statistics_presenter import StatisticsPresenter


class MockStatisticsView:
    """Implementación simulada en memoria de IStatisticsView para pruebas del Presenter."""

    def __init__(self) -> None:
        self.set_empty_state_calls: list[bool] = []
        self.render_general_calls: list[dict[str, Any]] = []
        self.render_weekly_calls: list[WeeklyStatsSummary] = []
        self.render_daily_calls: list[DailyStatsSummary] = []
        self.set_active_subtab_calls: list[int] = []

    def set_empty_state(self, is_empty: bool) -> None:
        self.set_empty_state_calls.append(is_empty)

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
        self.render_general_calls.append({
            "stats": stats,
            "streak_days": streak_days,
            "total_study_days": total_study_days,
            "evolution_data": evolution_data,
            "top_effort": top_effort,
            "heatmap_data": heatmap_data,
            "hourly_data": hourly_data,
            "file_name": file_name,
        })

    def render_weekly_tab(self, summary: WeeklyStatsSummary) -> None:
        self.render_weekly_calls.append(summary)

    def render_daily_tab(self, summary: DailyStatsSummary) -> None:
        self.render_daily_calls.append(summary)

    def set_active_subtab(self, index: int) -> None:
        self.set_active_subtab_calls.append(index)


class TestStatisticsPresenter(unittest.TestCase):
    """Batería de pruebas unitarias sobre StatisticsPresenter."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_service = StorageService(default_dir=Path(self.temp_dir.name))
        self.timer_service = TimerService()
        self.application = StudyApplicationService(
            storage=self.storage_service,
            timer=self.timer_service,
        )
        self.mock_view = MockStatisticsView()
        self.presenter = StatisticsPresenter(view=self.mock_view, application=self.application)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_refresh_all_when_record_closed(self) -> None:
        """Verifica que si no hay archivo abierto, se activa el estado vacío."""
        self.application.close_record()
        self.presenter.refresh_all()
        self.assertEqual(self.mock_view.set_empty_state_calls, [True])
        self.assertEqual(len(self.mock_view.render_general_calls), 0)

    def test_refresh_all_when_record_open(self) -> None:
        """Verifica que con un archivo abierto se renderizan las tres dimensiones."""
        rec = Record(record_name="Física I")
        today_iso = datetime.now().isoformat()
        rec.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=120_000,
                break_time_ms=30_000,
                completed=True,
                created_at=today_iso,
            )
        )
        file_path = Path(self.temp_dir.name) / "fisica_1.json"
        self.storage_service.save(rec, file_path)
        self.application.load(file_path)

        self.presenter.refresh_all()

        self.assertEqual(self.mock_view.set_empty_state_calls, [False])
        self.assertEqual(len(self.mock_view.render_general_calls), 1)
        self.assertEqual(len(self.mock_view.render_weekly_calls), 1)
        self.assertEqual(len(self.mock_view.render_daily_calls), 1)

        gen_data = self.mock_view.render_general_calls[0]
        self.assertEqual(gen_data["file_name"], "fisica_1")
        self.assertEqual(gen_data["streak_days"], 1)
        self.assertEqual(gen_data["total_study_days"], 1)
        self.assertEqual(len(gen_data["evolution_data"].points), 1)

    def test_set_subtab_navigation(self) -> None:
        """Verifica la conmutación entre sub-pestañas y el renderizado bajo demanda."""
        rec = Record(record_name="Álgebra")
        file_path = Path(self.temp_dir.name) / "algebra.json"
        self.storage_service.save(rec, file_path)
        self.application.load(file_path)

        self.presenter.set_subtab(1)
        self.assertEqual(self.presenter.active_subtab, 1)
        self.assertIn(1, self.mock_view.set_active_subtab_calls)
        self.assertGreaterEqual(len(self.mock_view.render_weekly_calls), 1)

        self.presenter.set_subtab(2)
        self.assertEqual(self.presenter.active_subtab, 2)
        self.assertIn(2, self.mock_view.set_active_subtab_calls)
        self.assertGreaterEqual(len(self.mock_view.render_daily_calls), 1)

        self.presenter.set_subtab(99)
        self.assertEqual(self.presenter.active_subtab, 2)

    def test_week_navigation(self) -> None:
        """Verifica el desplazamiento de semanas hacia atrás, adelante y restablecimiento."""
        rec = Record(record_name="Química")
        file_path = Path(self.temp_dir.name) / "quimica.json"
        self.storage_service.save(rec, file_path)
        self.application.load(file_path)

        initial_week = self.presenter.current_week_date
        self.presenter.navigate_week(-1)
        self.assertEqual(self.presenter.current_week_date, initial_week - timedelta(days=7))

        self.presenter.navigate_week(2)
        self.assertEqual(self.presenter.current_week_date, initial_week + timedelta(days=7))

        self.presenter.go_to_current_week()
        self.assertEqual(self.presenter.current_week_date, date.today())

    def test_day_navigation(self) -> None:
        """Verifica el desplazamiento de días hacia atrás, adelante y fecha específica."""
        rec = Record(record_name="Biología")
        file_path = Path(self.temp_dir.name) / "biologia.json"
        self.storage_service.save(rec, file_path)
        self.application.load(file_path)

        initial_day = self.presenter.current_day_date
        self.presenter.navigate_day(-1)
        self.assertEqual(self.presenter.current_day_date, initial_day - timedelta(days=1))

        self.presenter.navigate_day(2)
        self.assertEqual(self.presenter.current_day_date, initial_day + timedelta(days=1))

        custom_date = date(2026, 5, 20)
        self.presenter.set_day_date(custom_date)
        self.assertEqual(self.presenter.current_day_date, custom_date)

        self.presenter.go_to_today()
        self.assertEqual(self.presenter.current_day_date, date.today())

    def test_top_effort_criteria_change(self) -> None:
        """Verifica el cambio de criterio de clasificación de esfuerzo."""
        rec = Record(record_name="Matemática")
        file_path = Path(self.temp_dir.name) / "matematica.json"
        self.storage_service.save(rec, file_path)
        self.application.load(file_path)

        self.presenter.set_top_effort_criteria("retries")
        self.assertEqual(self.presenter.top_effort_criteria, "retries")

        self.presenter.set_top_effort_criteria("pb")
        self.assertEqual(self.presenter.top_effort_criteria, "pb")

        self.presenter.set_top_effort_criteria("unknown")
        self.assertEqual(self.presenter.top_effort_criteria, "pb")


if __name__ == "__main__":
    unittest.main()
