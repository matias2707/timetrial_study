"""Pruebas unitarias para PlannerPresenter y RecordsPresenter en aislamiento (sin Qt)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from application.application_service import StudyApplicationService
from application.planner_service import PlannedSectionStatus
from domain.models import PlannedSection, TimerItem
from infrastructure.storage_service import StorageService
from presentation.planner.planner_presenter import PlannerPresenter
from presentation.records.records_presenter import RecordsPresenter


class MockPlannerView:
    def __init__(self) -> None:
        self.sections: list[PlannedSectionStatus] = []
        self.completion_rate: float = 0.0
        self.empty_state: bool = False
        self.boundary_warning: str = ""

    def render_sections_overview(self, sections: list[PlannedSectionStatus], completion_rate: float) -> None:
        self.sections = sections
        self.completion_rate = completion_rate

    def show_boundary_warning(self, message: str) -> None:
        self.boundary_warning = message

    def set_empty_state(self, is_empty: bool) -> None:
        self.empty_state = is_empty


class MockRecordsView:
    def __init__(self) -> None:
        self.items: list[TimerItem] = []
        self.summary: tuple[int, int, int] = (0, 0, 0)
        self.empty_state: bool = False

    def render_items(self, items: list[TimerItem]) -> None:
        self.items = items

    def update_filter_summary(self, active_filters_count: int, filtered_count: int, total_count: int) -> None:
        self.summary = (active_filters_count, filtered_count, total_count)

    def set_empty_state(self, is_empty: bool) -> None:
        self.empty_state = is_empty


class TestPlannerAndRecordsPresenters(unittest.TestCase):
    """Verifica los presenters de Planner y Records en memoria sin loop de Qt."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(default_dir=Path(self.tmp_dir.name))
        self.app_service = StudyApplicationService(storage=self.storage)

        self.planner_view = MockPlannerView()
        self.planner_presenter = PlannerPresenter(self.planner_view, self.app_service)

        self.records_view = MockRecordsView()
        self.records_presenter = RecordsPresenter(self.records_view, self.app_service)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_planner_presenter_refresh(self) -> None:
        self.app_service.record.planner_sections.append(
            PlannedSection(section_type="Guía", section_number=1, total_exercises=5)
        )
        self.planner_presenter.refresh_planner()
        self.assertFalse(self.planner_view.empty_state)
        self.assertEqual(len(self.planner_view.sections), 1)

    def test_records_presenter_refresh_and_delete(self) -> None:
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=60_000,
            break_time_ms=0,
            completed=True,
        )
        self.app_service.record.items.append(item)
        self.records_presenter.refresh_records()

        self.assertEqual(len(self.records_view.items), 1)
        self.assertEqual(self.records_view.summary[1], 1)

        # Eliminar item
        deleted = self.records_presenter.delete_item(item.id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.records_view.items), 0)


if __name__ == "__main__":
    unittest.main()
