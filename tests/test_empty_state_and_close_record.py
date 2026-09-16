"""Pruebas para el estado vacío y la gestión de cierre de proyectos (TASK-005)."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from application.application_service import SessionLocation, StudyApplicationService
from domain.models import PlannedSection, Record, TimerItem
from domain.timer_service import TimerMode, TimerService
from infrastructure.storage_service import StorageService
from presentation.main_window import MainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestEmptyStateAndCloseRecord(unittest.TestCase):
    """Verifica la robustez de la aplicación ante el cierre de archivos y estado vacío."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_application_service_close_record_atomic(self) -> None:
        """Verifica que close_record resetee de manera limpia y atómica el estado de sesión."""
        service = StudyApplicationService()
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=2,
            inciso=None,
            exercise_time_ms=5000,
            break_time_ms=0,
            completed=True,
        )
        service.record.items.append(item)
        service.load_item_into_session(item)
        service.set_comment("Nota de prueba")

        self.assertTrue(service.is_editing)
        self.assertEqual(service.pending_comment, "Nota de prueba")

        service.close_record()

        self.assertFalse(service.is_record_open)
        self.assertIsNone(service.record_path)
        self.assertEqual(service.record.record_name, "")
        self.assertEqual(len(service.record.items), 0)
        self.assertIsNone(service.editing_item_id)
        self.assertEqual(service.pending_comment, "")
        self.assertEqual(service.mode, TimerMode.WAITING)

    def test_empty_state_prevents_value_error_on_all_operations(self) -> None:
        """Comprueba que ninguna operación lance ValueError: No hay un archivo activo en estado vacío."""
        window = MainWindow()
        window.application.close_record()
        window.set_empty_project_state(True)

        self.assertFalse(window.application.is_record_open)

        # Operaciones en ApplicationService
        try:
            window.application.save()
            dummy_item = TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=1000,
                break_time_ms=0,
                completed=True,
            )
            window.application.add_item(dummy_item)
            window.application.replace_item(dummy_item, dummy_item)
            window.application.reset_item(dummy_item)
            window.application.update_comment(dummy_item, "test")
            window.application.delete_item(dummy_item)
            self.assertFalse(window.application.finish_item(True))
            self.assertEqual(window.application.import_items(Path("nonexistent.json"), [0]), 0)
            self.assertFalse(window.application.sync_planner_with_records())
            window.application.add_or_update_planned_section(PlannedSection(section_type="Guía", section_number=1))
            self.assertFalse(window.application.delete_planned_section("Guía", 1))
            window.application.promote_gap_items([dummy_item])
        except ValueError as err:
            self.fail(f"ApplicationService lanzó ValueError inesperado: {err}")

        # Operaciones en MainWindow / HomeView
        try:
            window.finish_item(True)
            window.finish_item(False)
            window.add_home_comment()
            window.autosave()
        except ValueError as err:
            self.fail(f"MainWindow lanzó ValueError inesperado: {err}")

        window.close()

    def test_close_record_transitions_to_empty_state_when_welcome_cancelled(self) -> None:
        """Verifica que al cerrar un registro y cancelar WelcomeDialog se active el estado vacío."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "TestProject.json"
            window = MainWindow()
            window.application.new_record("TestProject", directory=Path(temp_dir))
            window.set_empty_project_state(False)

            self.assertTrue(window.application.is_record_open)
            self.assertTrue(window.toolbar.close_file_action.isEnabled())
            self.assertTrue(window.toolbar.save_file_action.isEnabled())

            # Simular confirmar el cierre y cancelar el diálogo de bienvenida
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
                 patch("presentation.main_window.WelcomeDialog.exec_welcome", return_value=("cancel", None, True)):
                window.close_record()

            self.assertFalse(window.application.is_record_open)
            self.assertIn("[Sin proyecto activo]", window.windowTitle())
            self.assertEqual(window.home_view.home_title.text(), "[Sin proyecto activo]")

            # Acciones de toolbar deshabilitadas
            self.assertFalse(window.toolbar.close_file_action.isEnabled())
            self.assertFalse(window.toolbar.save_file_action.isEnabled())

            # Panel de estado vacío activo en el cronómetro
            self.assertFalse(window.home_view.empty_state_widget.isHidden())
            self.assertTrue(window.home_view.hero_card.isHidden())
            self.assertFalse(window.home_view.session_button.isEnabled())
            self.assertFalse(window.home_view.comment_button.isEnabled())
            self.assertFalse(window.home_view.exercise_input.isEnabled())

            # Controles en Registros y Planificador deshabilitados
            self.assertFalse(window.records_view.close_button.isEnabled())
            self.assertFalse(window.records_view.save_as_button.isEnabled())
            self.assertFalse(window.records_view.rename_button.isEnabled())
            self.assertFalse(window.records_view.import_button.isEnabled())
            self.assertFalse(window.planner.btn_sync.isEnabled())
            self.assertFalse(window.planner.btn_add_section.isEnabled())

            window.close()

    def test_open_or_create_restores_active_state(self) -> None:
        """Verifica que al abrir o crear un registro se salga del estado vacío y se reactiven controles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            window = MainWindow()
            window.application.close_record()
            window.set_empty_project_state(True)

            self.assertFalse(window.application.is_record_open)
            self.assertFalse(window.home_view.session_button.isEnabled())

            # Crear un nuevo archivo desde el servicio y salir de estado vacío
            new_file = window.application.new_record("Reactivado", directory=Path(temp_dir))
            window.set_empty_project_state(False)

            self.assertTrue(window.application.is_record_open)
            self.assertIn("Reactivado", window.windowTitle())
            self.assertEqual(window.home_view.home_title.text(), "Reactivado")

            self.assertTrue(window.toolbar.close_file_action.isEnabled())
            self.assertTrue(window.toolbar.save_file_action.isEnabled())
            self.assertTrue(window.home_view.empty_state_widget.isHidden())
            self.assertFalse(window.home_view.hero_card.isHidden())
            self.assertTrue(window.home_view.session_button.isEnabled())
            self.assertTrue(window.home_view.comment_button.isEnabled())
            self.assertTrue(window.home_view.exercise_input.isEnabled())
            self.assertTrue(window.records_view.close_button.isEnabled())
            self.assertTrue(window.planner.btn_sync.isEnabled())
            self.assertTrue(window.planner.btn_add_section.isEnabled())

            window.close()


if __name__ == "__main__":
    unittest.main()
