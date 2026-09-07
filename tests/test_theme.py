import os
import unittest
from PySide6.QtWidgets import QApplication

from presentation.main_window import MainWindow
from presentation.theme import THEME_DARK, THEME_LIGHT, get_theme_stylesheet, get_dialog_stylesheet

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_theme_stylesheets_generated(self) -> None:
        light_css = get_theme_stylesheet(THEME_LIGHT)
        dark_css = get_theme_stylesheet(THEME_DARK)
        self.assertIn("MODO CLARO", light_css)
        self.assertIn("MODO OSCURO", dark_css)
        self.assertIn("QToolButton#view_toolbar_button", light_css)
        self.assertIn("QToolButton#view_toolbar_button", dark_css)

    def test_dialog_stylesheets_generated(self) -> None:
        light_dialog = get_dialog_stylesheet(THEME_LIGHT)
        dark_dialog = get_dialog_stylesheet(THEME_DARK)
        self.assertIn("#f8fafc", light_dialog)
        self.assertIn("#0f172a", dark_dialog)

    def test_main_window_toolbar_view_menu(self) -> None:
        window = MainWindow()
        self.assertTrue(hasattr(window, "view_button"))
        self.assertIn("Vista", window.view_button.text())

        self.assertTrue(hasattr(window, "themes_menu"))
        self.assertEqual(window.themes_menu.title(), "Temas")

        self.assertTrue(hasattr(window, "theme_dark_action"))
        self.assertTrue(hasattr(window, "theme_light_action"))
        self.assertEqual(window.theme_dark_action.text(), "Modo oscuro")
        self.assertEqual(window.theme_light_action.text(), "Modo claro")

        # Test switching to dark
        window.set_theme(THEME_DARK)
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.theme_dark_action.isChecked())
        self.assertFalse(window.theme_light_action.isChecked())
        self.assertTrue(window.weekly_chart.dark_mode)

        # Test switching to light
        window.set_theme(THEME_LIGHT)
        self.assertFalse(window.is_dark_mode)
        self.assertFalse(window.theme_dark_action.isChecked())
        self.assertTrue(window.theme_light_action.isChecked())
        self.assertFalse(window.weekly_chart.dark_mode)

    def test_timer_states_and_table_badges(self) -> None:
        window = MainWindow()
        # Idle state in light mode
        window.set_theme(THEME_LIGHT)
        window.update_timer_visual_state()
        self.assertIn("LISTO PARA COMENZAR", window.status_pill.text())
        self.assertIn("#f1f5f9", window.status_pill.styleSheet())

        # Idle state in dark mode
        window.set_theme(THEME_DARK)
        window.update_timer_visual_state()
        self.assertIn("LISTO PARA COMENZAR", window.status_pill.text())
        self.assertIn("#1e293b", window.status_pill.styleSheet())


if __name__ == "__main__":
    unittest.main()

