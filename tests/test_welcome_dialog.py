"""Pruebas para WelcomeDialog y el flujo de inicio desacoplado."""

import os
from pathlib import Path
import tempfile
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from domain.models import Record
from infrastructure.storage_service import StorageService
from presentation.main_window import MainWindow
from presentation.welcome_dialog import WelcomeDialog
from presentation.window_utils import ensure_dialog_taskbar_presence, force_activate_window, get_app_icon

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestWelcomeDialogAndStartup(unittest.TestCase):
    """Verifica el comportamiento del diálogo de bienvenida y el flujo de inicio."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_window_utils_get_app_icon(self) -> None:
        icon = get_app_icon()
        self.assertFalse(icon.isNull(), "El icono oficial de la aplicación debe existir y ser válido")

    def test_welcome_dialog_flags_without_parent(self) -> None:
        dialog = WelcomeDialog(recent_paths=[], auto_open_recent=True, parent=None)
        flags = dialog.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowType.Window), "Debe tener bandera Qt.Window para figurar en la barra de tareas")
        self.assertFalse(dialog.windowIcon().isNull(), "Debe tener icono asignado")
        dialog.close()

    def test_welcome_dialog_populate_recent_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "Registro1.json"
            file2 = Path(temp_dir) / "Registro2.json"
            file1.write_text("{}", encoding="utf-8")
            file2.write_text("{}", encoding="utf-8")

            dialog = WelcomeDialog(
                recent_paths=[file1, file2],
                auto_open_recent=True,
                parent=None,
            )

            self.assertEqual(dialog.recent_list.count(), 2)
            item = dialog.recent_list.item(0)
            self.assertIn("Registro1.json", item.text())
            self.assertEqual(item.data(Qt.ItemDataRole.UserRole), str(file1))
            dialog.close()

    def test_welcome_dialog_empty_recent_files(self) -> None:
        dialog = WelcomeDialog(recent_paths=[], auto_open_recent=False, parent=None)
        self.assertEqual(dialog.recent_list.count(), 1)
        self.assertFalse(dialog.open_recent_button.isEnabled(), "El botón de abrir reciente debe estar deshabilitado si no hay archivos")
        self.assertFalse(dialog.auto_open_checkbox.isChecked())
        dialog.close()

    def test_welcome_dialog_actions(self) -> None:
        dialog = WelcomeDialog(recent_paths=[], auto_open_recent=True, parent=None)

        dialog._on_new_clicked()
        self.assertEqual(dialog.selected_action, "new")

        dialog._on_open_clicked()
        self.assertEqual(dialog.selected_action, "open")

        dialog._on_cancel_clicked()
        self.assertEqual(dialog.selected_action, "cancel")
        dialog.close()

    def test_main_window_auto_open_recent_toggle(self) -> None:
        window = MainWindow()

        # Probar cambiar estado
        window.set_auto_open_recent(False)
        self.assertFalse(window.auto_open_recent)
        self.assertFalse(window.toolbar.auto_open_action.isChecked())

        window.set_auto_open_recent(True)
        self.assertTrue(window.auto_open_recent)
        self.assertTrue(window.toolbar.auto_open_action.isChecked())

        window.close()

    def test_main_window_startup_flow_with_recent_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rec_file = Path(temp_dir) / "TestAutoLoad.json"
            storage = StorageService()
            rec = Record(record_name="TestAutoLoad", items=[])
            storage.save(rec, rec_file)

            window = MainWindow()
            window.application.storage.recent_files.add(rec_file)
            window.auto_open_recent = True

            # Ejecutar manualmente el flujo de inicio con force=True
            window._handle_startup_flow(force=True)

            self.assertEqual(window.application.record.record_name, "TestAutoLoad")
            self.assertEqual(window.application.record_path, rec_file)
            window.close()


if __name__ == "__main__":
    unittest.main()
