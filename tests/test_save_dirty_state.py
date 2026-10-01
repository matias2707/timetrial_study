from __future__ import annotations

"""Pruebas unitarias e integrales para el control de guardado y estado dirty (TASK-028)."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from application.application_service import SessionLocation, StudyApplicationService
from application.save_policy import SavePolicy
from domain.models import OrganizedSection, OrganizerSchedule, Record, TimerItem
from domain.timer_service import TimerMode
from infrastructure.storage_service import StorageService
from presentation.main_window import MainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class MemoryStorage:
    def __init__(self) -> None:
        self.path = Path("memory_test.json")
        self.saved_records: list[Record] = []

    @property
    def is_open(self) -> bool:
        return self.path is not None

    def create_automatic(self) -> Record:
        return Record(record_name="memory_test")

    def save(self, record: Record, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
        self.saved_records.append(record)

    def load(self, path: Path) -> Record:
        self.path = path
        return Record(record_name=path.stem)


class TestDirtyStateTracking(unittest.TestCase):
    """Verifica que StudyApplicationService gestione de forma reactiva y precisa el estado is_dirty."""

    def setUp(self) -> None:
        self.storage = MemoryStorage()
        self.app = StudyApplicationService(
            storage=self.storage,
            save_policy=SavePolicy.AUTO_PERIODIC,
        )

    def test_initial_state_is_not_dirty(self) -> None:
        self.assertFalse(self.app.is_dirty)

    def test_add_item_marks_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.assertTrue(self.app.is_dirty)

    def test_delete_item_marks_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.app.save()
        self.assertFalse(self.app.is_dirty)

        self.app.delete_item(item)
        self.assertTrue(self.app.is_dirty)

    def test_replace_and_reset_item_marks_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.app.save()

        # Reemplazar
        new_item = TimerItem("Guía", 1, 1, None, 2000, 0, True)
        self.app.replace_item(item, new_item)
        self.assertTrue(self.app.is_dirty)
        self.app.save()

        # Reiniciar
        self.app.reset_item(new_item)
        self.assertTrue(self.app.is_dirty)

    def test_finish_item_marks_dirty(self) -> None:
        self.app.toggle_session(SessionLocation("Guía", 1, 1, None))
        self.app.timer.exercise_time_ms = 5000
        self.app.finish_item(completed=True)
        self.assertTrue(self.app.is_dirty)

    def test_update_comment_marks_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.app.save()

        self.app.update_comment(item, "Nuevo comentario")
        self.assertTrue(self.app.is_dirty)

    def test_organizer_mutations_mark_dirty(self) -> None:
        sec = OrganizedSection("Guía", 1, total_exercises=5)
        self.app.add_or_update_organized_section(sec)
        self.assertTrue(self.app.is_dirty)
        self.app.save()

        self.app.set_exercise_note("Guía", 1, 2, None, "Nota dirty")
        self.assertTrue(self.app.is_dirty)
        self.app.save()

        self.app.set_exercise_tags("Guía", 1, 2, None, ["tag1"])
        self.assertTrue(self.app.is_dirty)
        self.app.save()

        sched = OrganizerSchedule(period_type="Anual")
        self.app.set_schedule(sched)
        self.assertTrue(self.app.is_dirty)
        self.app.save()

        self.app.delete_organized_section("Guía", 1)
        self.assertTrue(self.app.is_dirty)

    def test_undo_and_redo_mark_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.app.save()
        self.assertFalse(self.app.is_dirty)

        self.assertTrue(self.app.undo())
        self.assertTrue(self.app.is_dirty)

        self.app.save()
        self.assertFalse(self.app.is_dirty)

        self.assertTrue(self.app.redo())
        self.assertTrue(self.app.is_dirty)

    def test_save_and_save_as_clear_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.assertTrue(self.app.is_dirty)

        self.app.save()
        self.assertFalse(self.app.is_dirty)

        self.app.add_item(item)
        self.assertTrue(self.app.is_dirty)

        self.app.save_as(Path("new_path.json"))
        self.assertFalse(self.app.is_dirty)

    def test_load_and_close_clear_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.assertTrue(self.app.is_dirty)

        self.app.close_record()
        self.assertFalse(self.app.is_dirty)

        # Cargar archivo existente limpia el flag dirty
        self.app.load(Path("existing.json"))
        self.assertFalse(self.app.is_dirty)

    def test_dirty_listener_notifications(self) -> None:
        notifications: list[bool] = []
        listener = lambda dirty: notifications.append(dirty)

        self.app.add_dirty_listener(listener)
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.app.add_item(item)
        self.assertEqual(notifications, [True])

        # Guardar notifica False
        self.app.save()
        self.assertEqual(notifications, [True, False])

        # Remover listener no genera más eventos
        self.app.remove_dirty_listener(listener)
        self.app.add_item(item)
        self.assertEqual(notifications, [True, False])

    def test_save_policy_auto_immediate_saves_synchronously(self) -> None:
        app_immediate = StudyApplicationService(
            storage=self.storage,
            save_policy=SavePolicy.AUTO_IMMEDIATE,
        )
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        app_immediate.add_item(item)

        # En política inmediata, se persiste de forma directa y queda limpio
        self.assertFalse(app_immediate.is_dirty)
        self.assertTrue(len(self.storage.saved_records) > 0)


class TestMainWindowDirtyUIIntegration(unittest.TestCase):
    """Verifica la respuesta visual e interactiva de MainWindow y Toolbar ante el estado dirty."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.window = MainWindow()
        self.window.application.new_record("Algebra", directory=Path(self.temp_dir.name))
        self.window.set_empty_project_state(False)

    def tearDown(self) -> None:
        self.window.application._is_dirty = False
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            self.window.close()
        self.temp_dir.cleanup()

    def test_window_title_shows_asterisk_when_dirty(self) -> None:
        # Estado inicial guardado: sin asterisco
        self.assertNotIn("*", self.window.windowTitle())

        # Mutación
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.window.application.add_item(item)

        # Título debe contener asterisco
        self.assertIn("*", self.window.windowTitle())
        self.assertIn("Algebra", self.window.windowTitle())

        # Guardar debe remover el asterisco
        self.window.save_record()
        self.assertNotIn("*", self.window.windowTitle())

    def test_toolbar_save_action_reacts_to_dirty_state(self) -> None:
        # Inicialmente limpio -> botón guardar deshabilitado
        self.assertFalse(self.window.toolbar.save_action.isEnabled())
        self.assertFalse(self.window.toolbar.quick_save_button.isEnabled())

        # Al mutar -> acciones se habilitan
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.window.application.add_item(item)

        self.assertTrue(self.window.toolbar.save_action.isEnabled())
        self.assertTrue(self.window.toolbar.quick_save_button.isEnabled())

        # Al guardar -> se deshabilitan
        self.window.save_record()
        self.assertFalse(self.window.toolbar.save_action.isEnabled())
        self.assertFalse(self.window.toolbar.quick_save_button.isEnabled())

    def test_close_record_prompts_when_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.window.application.add_item(item)
        self.assertTrue(self.window.application.is_dirty)

        # 1. Simular cancelar el cierre
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.close_record()
            self.assertTrue(self.window.application.is_record_open)
            self.assertTrue(self.window.application.is_dirty)

        # 2. Simular guardar y cerrar
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save), \
             patch("presentation.main_window.WelcomeDialog.exec_welcome", return_value=("cancel", None, True)):
            self.window.close_record()
            self.assertFalse(self.window.application.is_record_open)
            self.assertFalse(self.window.application.is_dirty)

    def test_close_event_prompts_when_dirty(self) -> None:
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        self.window.application.add_item(item)
        self.assertTrue(self.window.application.is_dirty)

        event = QCloseEvent()

        # 1. Cancelar el cierre
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.closeEvent(event)
            self.assertFalse(event.isAccepted())

        # 2. Descartar cambios y salir
        event2 = QCloseEvent()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            self.window.closeEvent(event2)
            self.assertTrue(event2.isAccepted())
            self.window.application._is_dirty = False


if __name__ == "__main__":
    unittest.main()
