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

    def test_main_window_toolbar_config_menu(self) -> None:
        window = MainWindow()
        self.assertTrue(hasattr(window, "config_button"))
        self.assertTrue(hasattr(window, "view_button"))
        self.assertIn("Configuración", window.config_button.text())

        self.assertTrue(hasattr(window, "config_menu"))
        self.assertEqual(window.config_menu.title(), "Configuración")

        self.assertTrue(hasattr(window, "themes_menu"))
        self.assertEqual(window.themes_menu.title(), "Temas")

        self.assertTrue(hasattr(window, "sound_action"))
        self.assertIn("sonidos", window.sound_action.text().lower())

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

    def test_sound_mute_toggle(self) -> None:
        window = MainWindow()
        # Default state: unmuted
        window.set_sound_muted(False)
        self.assertFalse(window.is_sound_muted)
        self.assertFalse(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Silenciar sonidos")
        self.assertFalse(window.start_sound.isMuted())
        self.assertFalse(window.complete_sound.isMuted())

        # Toggle to muted
        window.sound_action.trigger()
        self.assertTrue(window.is_sound_muted)
        self.assertTrue(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Activar sonidos")
        self.assertTrue(window.start_sound.isMuted())
        self.assertTrue(window.complete_sound.isMuted())

        # Toggle back to unmuted
        window.sound_action.trigger()
        self.assertFalse(window.is_sound_muted)
        self.assertFalse(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Silenciar sonidos")
        self.assertFalse(window.start_sound.isMuted())
        self.assertFalse(window.complete_sound.isMuted())

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

    def test_steppers_and_navigation_pods(self) -> None:
        window = MainWindow()

        # Stylesheet checks
        light_css = get_theme_stylesheet(THEME_LIGHT)
        dark_css = get_theme_stylesheet(THEME_DARK)
        self.assertIn("QPushButton#stepper_button", light_css)
        self.assertIn("QPushButton#stepper_button", dark_css)
        self.assertIn("QFrame#nav_pod", light_css)
        self.assertIn("QFrame#nav_pod", dark_css)

        # Steppers exist and click logic
        self.assertTrue(hasattr(window, "stepper_buttons"))
        self.assertEqual(len(window.stepper_buttons), 6)  # 2 per spinbox (3 spinboxes)

        # Exercise stepper: minus is button 2, plus is button 3
        window.exercise_input.setValue(1)
        btn_exercise_plus = window.stepper_buttons[3]
        btn_exercise_minus = window.stepper_buttons[2]

        btn_exercise_plus.click()
        self.assertEqual(window.exercise_input.value(), 2)
        btn_exercise_minus.click()
        self.assertEqual(window.exercise_input.value(), 1)

        # Inciso stepper: minus is 4, plus is 5
        window.inciso_input.setValue(0)
        btn_inciso_plus = window.stepper_buttons[5]
        btn_inciso_minus = window.stepper_buttons[4]
        btn_inciso_plus.click()
        self.assertEqual(window.inciso_input.value(), 1)
        btn_inciso_minus.click()
        self.assertEqual(window.inciso_input.value(), 0)

        # Lock controls test
        window.set_locked(True)
        self.assertFalse(window.exercise_input.isEnabled())
        for btn in window.stepper_buttons:
            self.assertFalse(btn.isEnabled())

        window.set_locked(False)
        self.assertTrue(window.exercise_input.isEnabled())
        for btn in window.stepper_buttons:
            self.assertTrue(btn.isEnabled())

        # Navigation pods test
        self.assertTrue(hasattr(window, "nav_pod_section"))
        self.assertTrue(hasattr(window, "nav_pod_exercise"))
        self.assertTrue(hasattr(window, "nav_pod_inciso"))
        self.assertEqual(len(window.navigation_buttons), 6)

        # Primary controls arrangement
        self.assertTrue(hasattr(window, "primary_controls"))
        self.assertTrue(hasattr(window, "stop_button"))
        self.assertTrue(hasattr(window, "complete_button"))
        self.assertTrue(hasattr(window, "incomplete_button"))
        self.assertTrue(hasattr(window, "comment_button"))

        # Test arrangement modes without exception
        window._arrange_session_controls(compact=False, very_compact=False)
        window._arrange_session_controls(compact=True, very_compact=False)
        window._arrange_session_controls(compact=True, very_compact=True)
        window._arrange_navigation_pods(compact=False)
        window._arrange_navigation_pods(compact=True)


if __name__ == "__main__":
    unittest.main()

