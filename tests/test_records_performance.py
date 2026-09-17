import os
import unittest
from PySide6.QtWidgets import QApplication, QHeaderView

from application.application_service import StudyApplicationService
from domain.models import TimerItem
from presentation.records_view import RecordsViewWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class RecordsPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.service = StudyApplicationService()
        self.service.new_record("PerfTest")
        self.records_view = RecordsViewWidget(application=self.service)

    def test_cached_action_icons_initialized(self) -> None:
        """Verifica que los 4 iconos de acciones esten precacheados y sean validos."""
        self.assertIsNotNone(self.records_view._icon_comment)
        self.assertFalse(self.records_view._icon_comment.isNull())
        self.assertIsNotNone(self.records_view._icon_edit)
        self.assertFalse(self.records_view._icon_edit.isNull())
        self.assertIsNotNone(self.records_view._icon_resume)
        self.assertFalse(self.records_view._icon_resume.isNull())
        self.assertIsNotNone(self.records_view._icon_delete)
        self.assertFalse(self.records_view._icon_delete.isNull())

    def test_columns_are_interactive_with_precalculated_widths(self) -> None:
        """Verifica que las columnas 0 a 6 usen Interactive en lugar de ResizeToContents."""
        header = self.records_view.table.horizontalHeader()
        for col in range(7):
            self.assertEqual(header.sectionResizeMode(col), QHeaderView.ResizeMode.Interactive)
        self.assertEqual(header.sectionResizeMode(7), QHeaderView.ResizeMode.Stretch)
        for col in (8, 9, 10, 11):
            self.assertEqual(header.sectionResizeMode(col), QHeaderView.ResizeMode.Fixed)

    def test_dirty_checking_prevents_unnecessary_refresh(self) -> None:
        """Verifica que cuando _is_dirty es False y force=False, refresh_table no repuebla."""
        self.service.record.items = [
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=50000,
                break_time_ms=5000,
                completed=True,
            )
        ]
        self.records_view.mark_dirty()
        self.records_view.refresh_table(force=True)
        self.assertFalse(self.records_view._is_dirty)
        self.assertEqual(self.records_view.table.rowCount(), 1)

        self.service.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=30000,
                break_time_ms=2000,
                completed=False,
            )
        )
        self.records_view.refresh_table(force=False)
        self.assertEqual(self.records_view.table.rowCount(), 1)

        self.records_view.mark_dirty()
        self.records_view.refresh_table(force=False)
        self.assertEqual(self.records_view.table.rowCount(), 2)

    def test_refresh_table_does_not_emit_data_modified(self) -> None:
        """Verifica que la mera lectura/refresco de la tabla NO emita data_modified."""
        emitted = []
        self.records_view.data_modified.connect(lambda: emitted.append(True))

        self.records_view.refresh_table(force=True)
        self.assertEqual(len(emitted), 0)

    def test_mark_dirty_is_set_on_data_mutation(self) -> None:
        """Verifica que al eliminar un item se marque dirty y se emita data_modified."""
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=50000,
            break_time_ms=5000,
            completed=True,
        )
        self.service.record.items = [item]
        self.records_view.refresh_table(force=True)

        emitted = []
        self.records_view.data_modified.connect(lambda: emitted.append(True))

        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.records_view.delete_item(item)

        self.assertEqual(len(emitted), 1)
        self.assertEqual(self.records_view.table.rowCount(), 0)
