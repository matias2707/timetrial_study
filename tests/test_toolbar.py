"""Pruebas unitarias completas para la barra de herramientas AppToolbar y su integración."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from presentation.app_toolbar import AppToolbar
from presentation.main_window import MainWindow
from presentation.theme import get_theme_stylesheet
from presentation.theme_tokens import THEME_DARK, THEME_LIGHT


class TestAppToolbar(unittest.TestCase):
    """Batería de pruebas exhaustivas para AppToolbar."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["STUDY_TIMETRIAL_TEST"] = "1"
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.toolbar = AppToolbar(
            is_dark_mode=False,
            auto_open_recent=True,
            current_theme=THEME_LIGHT,
            is_sound_muted=False,
        )

    def tearDown(self) -> None:
        self.toolbar.deleteLater()

    def test_two_tier_layout_structure(self) -> None:
        """Verifica la disposición en dos niveles del Toolbar: Nivel 1 (Menús) y Nivel 2 (Acciones)."""
        self.assertEqual(self.toolbar.objectName(), "main_toolbar")
        self.assertEqual(self.toolbar.toolbar_container.objectName(), "toolbar_container")
        self.assertEqual(self.toolbar.menu_row.objectName(), "toolbar_menu_row")
        self.assertEqual(self.toolbar.actions_row.objectName(), "toolbar_actions_row")

        # Nivel 1: Archivo, Edición, Configuración
        self.assertEqual(self.toolbar.file_button.objectName(), "file_toolbar_button")
        self.assertEqual(self.toolbar.edit_button.objectName(), "edit_toolbar_button")
        self.assertEqual(self.toolbar.config_button.objectName(), "config_toolbar_button")

        # Nivel 2: Acciones rápidas rectangulares
        self.assertEqual(self.toolbar.quick_new_button.objectName(), "quick_new_button")
        self.assertEqual(self.toolbar.quick_open_button.objectName(), "quick_open_button")
        self.assertEqual(self.toolbar.quick_save_button.objectName(), "quick_save_button")
        self.assertEqual(self.toolbar.quick_save_as_button.objectName(), "quick_save_as_button")
        self.assertEqual(self.toolbar.quick_undo_button.objectName(), "quick_undo_button")
        self.assertEqual(self.toolbar.quick_redo_button.objectName(), "quick_redo_button")

        # Estilo rectangular con texto e icono
        for btn in (
            self.toolbar.file_button,
            self.toolbar.edit_button,
            self.toolbar.config_button,
            self.toolbar.quick_new_button,
            self.toolbar.quick_open_button,
            self.toolbar.quick_save_button,
            self.toolbar.quick_save_as_button,
            self.toolbar.quick_undo_button,
            self.toolbar.quick_redo_button,
        ):
            self.assertEqual(btn.toolButtonStyle(), Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def test_shortcuts_assigned_and_registered(self) -> None:
        """Verifica que las acciones tengan atajos estándar de teclado."""
        self.assertEqual(self.toolbar.new_file_action.shortcut().toString(), "Ctrl+N")
        self.assertEqual(self.toolbar.open_file_action.shortcut().toString(), "Ctrl+O")
        self.assertEqual(self.toolbar.save_action.shortcut().toString(), "Ctrl+S")
        self.assertEqual(self.toolbar.save_as_action.shortcut().toString(), "Ctrl+Shift+S")
        self.assertEqual(self.toolbar.close_file_action.shortcut().toString(), "Ctrl+W")
        self.assertEqual(self.toolbar.close_program_action.shortcut().toString(), "Ctrl+Q")
        self.assertEqual(self.toolbar.undo_action.shortcut().toString(), "Ctrl+Z")
        self.assertEqual(self.toolbar.redo_action.shortcut().toString(), "Ctrl+Y")

    def test_save_action_and_quick_save_reactivity(self) -> None:
        """Verifica que los botones rápidos de guardado respondan al estado sucio."""
        # Sin archivo abierto
        self.toolbar.update_save_action(is_record_open=False, is_dirty=False)
        self.assertFalse(self.toolbar.save_action.isEnabled())
        self.assertFalse(self.toolbar.quick_save_button.isEnabled())
        self.assertFalse(self.toolbar.quick_save_as_button.isEnabled())

        # Archivo abierto pero limpio (sin cambios)
        self.toolbar.update_save_action(is_record_open=True, is_dirty=False)
        self.assertFalse(self.toolbar.save_action.isEnabled())
        self.assertFalse(self.toolbar.quick_save_button.isEnabled())
        self.assertTrue(self.toolbar.quick_save_as_button.isEnabled())
        self.assertIn("Sin cambios", self.toolbar.quick_save_button.toolTip())

        # Archivo abierto con cambios sin guardar
        self.toolbar.update_save_action(is_record_open=True, is_dirty=True)
        self.assertTrue(self.toolbar.save_action.isEnabled())
        self.assertTrue(self.toolbar.quick_save_button.isEnabled())
        self.assertTrue(self.toolbar.quick_save_as_button.isEnabled())
        self.assertIn("Guardar cambios", self.toolbar.quick_save_button.toolTip())

    def test_quick_action_buttons_emission(self) -> None:
        """Verifica que los botones rápidos de Nivel 2 emitan sus respectivas señales."""
        new_emitted = []
        open_emitted = []
        save_as_emitted = []

        self.toolbar.request_new_record.connect(lambda: new_emitted.append(True))
        self.toolbar.request_open_record.connect(lambda: open_emitted.append(True))
        self.toolbar.request_save_as.connect(lambda: save_as_emitted.append(True))

        self.toolbar.quick_new_button.click()
        self.assertEqual(len(new_emitted), 1)

        self.toolbar.quick_open_button.click()
        self.assertEqual(len(open_emitted), 1)

        self.toolbar.quick_save_as_button.setEnabled(True)
        self.toolbar.quick_save_as_button.click()
        self.assertEqual(len(save_as_emitted), 1)

    def test_undo_redo_actions_and_tooltips(self) -> None:
        """Verifica que los botones rápidos de Deshacer y Rehacer se sincronicen."""
        self.toolbar.update_undo_redo_actions(can_undo=True, can_redo=False, undo_text="Sesión 1")
        self.assertTrue(self.toolbar.quick_undo_button.isEnabled())
        self.assertFalse(self.toolbar.quick_redo_button.isEnabled())
        self.assertIn("Deshacer Sesión 1", self.toolbar.quick_undo_button.toolTip())

        self.toolbar.update_undo_redo_actions(can_undo=False, can_redo=True, redo_text="Sesión 2")
        self.assertFalse(self.toolbar.quick_undo_button.isEnabled())
        self.assertTrue(self.toolbar.quick_redo_button.isEnabled())
        self.assertIn("Rehacer Sesión 2", self.toolbar.quick_redo_button.toolTip())

    def test_sound_and_theme_actions(self) -> None:
        """Verifica la respuesta de sonido y tema."""
        self.toolbar.update_sound_action(is_muted=True)
        self.assertIn("Activar", self.toolbar.sound_action.text())
        self.toolbar.update_sound_action(is_muted=False)
        self.assertIn("Silenciar", self.toolbar.sound_action.text())

    def test_no_overlapping_or_extra_visual_actions(self) -> None:
        """Verifica que la barra solo expone el widget contenedor de 2 niveles y ningún botón flotante."""
        self.assertEqual(len(self.toolbar.actions()), 1)
        self.assertEqual(self.toolbar.widgetForAction(self.toolbar.actions()[0]), self.toolbar.toolbar_container)
        self.assertIsNone(self.toolbar.quick_sound_button.parent())
        self.assertIsNone(self.toolbar.quick_theme_button.parent())
        self.assertIsNone(self.toolbar.spacer.parent())
        self.assertTrue(self.toolbar.quick_sound_button.isHidden())
        self.assertTrue(self.toolbar.quick_theme_button.isHidden())


    def test_theme_stylesheet_contains_all_toolbar_selectors(self) -> None:
        """Verifica que las reglas CSS del tema contengan todos los selectores de la barra."""
        for theme_key in (THEME_LIGHT, THEME_DARK):
            css = get_theme_stylesheet(theme_key)
            self.assertIn("QToolBar#main_toolbar", css)
            self.assertIn("QWidget#toolbar_container", css)
            self.assertIn("QWidget#toolbar_menu_row", css)
            self.assertIn("QWidget#toolbar_actions_row", css)
            self.assertIn("QToolButton#file_toolbar_button", css)
            self.assertIn("QToolButton#edit_toolbar_button", css)
            self.assertIn("QToolButton#config_toolbar_button", css)
            self.assertIn("QToolButton#quick_new_button", css)
            self.assertIn("QToolButton#quick_open_button", css)
            self.assertIn("QToolButton#quick_save_button", css)
            self.assertIn("QToolButton#quick_save_as_button", css)
            self.assertIn("QToolButton#quick_undo_button", css)
            self.assertIn("QToolButton#quick_redo_button", css)
            self.assertIn("QFrame#toolbar_row_separator", css)


class TestMainWindowToolbarIntegration(unittest.TestCase):
    """Verifica la integración completa del Toolbar con MainWindow."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["STUDY_TIMETRIAL_TEST"] = "1"
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_has_all_toolbar_properties(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertTrue(hasattr(window, "toolbar"))
        self.assertTrue(hasattr(window, "file_button"))
        self.assertTrue(hasattr(window, "edit_button"))
        self.assertTrue(hasattr(window, "config_button"))
        self.assertTrue(hasattr(window, "quick_new_button"))
        self.assertTrue(hasattr(window, "quick_open_button"))
        self.assertTrue(hasattr(window, "quick_save_button"))
        self.assertTrue(hasattr(window, "quick_save_as_button"))
        self.assertTrue(hasattr(window, "quick_undo_button"))
        self.assertTrue(hasattr(window, "quick_redo_button"))


if __name__ == "__main__":
    unittest.main()
