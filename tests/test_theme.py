import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["STUDY_TIMETRIAL_TEST"] = "1"

import unittest
from PySide6.QtWidgets import QApplication, QWidget

from presentation.main_window import MainWindow
from presentation.theme import THEME_DARK, THEME_LIGHT, get_theme_stylesheet, get_dialog_stylesheet


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
        self.assertIn("#f7f4ed", light_dialog)
        self.assertIn("#0f172a", dark_dialog)

    def test_main_window_toolbar_config_menu(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
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
        self.addCleanup(window.close)
        # Default state: unmuted
        window.set_sound_muted(False)
        self.assertFalse(window.is_sound_muted)
        self.assertFalse(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Silenciar sonidos")
        self.assertFalse(window.start_sound.isMuted())
        self.assertFalse(window.complete_sound.isMuted())
        self.assertFalse(window.ambience_view.engine.is_master_muted)

        # Toggle to muted (affects all sounds: effects and ambient)
        window.sound_action.trigger()
        self.assertTrue(window.is_sound_muted)
        self.assertTrue(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Activar sonidos")
        self.assertTrue(window.start_sound.isMuted())
        self.assertTrue(window.complete_sound.isMuted())
        self.assertTrue(window.ambience_view.engine.is_master_muted)

        # Toggle back to unmuted
        window.sound_action.trigger()
        self.assertFalse(window.is_sound_muted)
        self.assertFalse(window.is_muted)
        self.assertEqual(window.sound_action.text(), "Silenciar sonidos")
        self.assertFalse(window.start_sound.isMuted())
        self.assertFalse(window.complete_sound.isMuted())
        self.assertFalse(window.ambience_view.engine.is_master_muted)

    def test_timer_states_and_table_badges(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)
        # Idle state in light mode
        window.set_theme(THEME_LIGHT)
        window.update_timer_visual_state()
        self.assertIn("LISTO PARA COMENZAR", window.status_pill.text())
        self.assertIn("#ede8dd", window.status_pill.styleSheet())

        # Idle state in dark mode
        window.set_theme(THEME_DARK)
        window.update_timer_visual_state()
        self.assertIn("LISTO PARA COMENZAR", window.status_pill.text())
        self.assertIn("#1e293b", window.status_pill.styleSheet())

    def test_steppers_and_session_controls(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)

        # Stylesheet checks
        light_css = get_theme_stylesheet(THEME_LIGHT)
        dark_css = get_theme_stylesheet(THEME_DARK)
        self.assertIn("QPushButton#stepper_button", light_css)
        self.assertIn("QPushButton#stepper_button", dark_css)

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
        self.assertFalse(window.section_input.isEnabled())
        self.assertFalse(window.section_number_input.isEnabled())
        # Reasignación en curso: exercise_input permanece habilitado
        self.assertTrue(window.exercise_input.isEnabled())

        window.set_locked(False)
        self.assertTrue(window.section_input.isEnabled())
        self.assertTrue(window.exercise_input.isEnabled())
        for btn in window.stepper_buttons:
            self.assertTrue(btn.isEnabled())

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

    def test_theme_tokens_and_timer_cards_style(self) -> None:
        from presentation.theme_tokens import LIGHT_TOKENS, DARK_TOKENS
        from presentation.theme import get_timer_cards_style

        # Anti-glare warm paper light canvas, anti-halation dark canvas
        self.assertEqual(LIGHT_TOKENS.bg_app, "#f7f4ed")
        self.assertEqual(DARK_TOKENS.bg_app, "#0b0f17")

        # Clock card backgrounds
        self.assertEqual(LIGHT_TOKENS.bg_clock_card, "#fdfcf7")
        self.assertEqual(DARK_TOKENS.bg_clock_card, "#162032")

        # Tab bar backgrounds
        self.assertEqual(LIGHT_TOKENS.bg_tab_bar, "#ede8dd")
        self.assertEqual(DARK_TOKENS.bg_tab_bar, "#080c14")

        # Check get_timer_cards_style
        light_ex_style, light_br_style = get_timer_cards_style("idle", is_dark=False)
        dark_ex_style, dark_br_style = get_timer_cards_style("idle", is_dark=True)
        self.assertNotIn("#090d16", light_ex_style)
        self.assertIn("#fdfcf7", light_ex_style)
        self.assertIn("#162032", dark_ex_style)

    def test_deep_theme_propagation_across_views(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)

        # Switch to Light Mode
        window.set_theme(THEME_LIGHT)
        self.assertFalse(window.is_dark_mode)
        self.assertFalse(window.planner_view.is_dark)
        self.assertFalse(window.statistics_view.course_heatmap.is_dark)
        self.assertFalse(window.statistics_view.hourly_chart.dark_mode)
        self.assertFalse(window.statistics_view.weekly_chart.dark_mode)
        self.assertFalse(window.ambience_view.is_dark)

        # Verify home timer clocks contrast in light mode
        window.home_view.update_timer_visual_state()
        self.assertIn("#1c1917", window.home_view.exercise_clock.styleSheet())

        # Switch to Dark Mode
        window.set_theme(THEME_DARK)
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.planner_view.is_dark)
        self.assertTrue(window.statistics_view.course_heatmap.is_dark)
        self.assertTrue(window.statistics_view.hourly_chart.dark_mode)
        self.assertTrue(window.statistics_view.weekly_chart.dark_mode)
        self.assertTrue(window.ambience_view.is_dark)

        # Verify home timer clocks contrast in dark mode
        window.home_view.update_timer_visual_state()
        self.assertIn("#f1f5f9", window.home_view.exercise_clock.styleSheet())

    def test_custom_skins_selection_and_propagation(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)

        # Verificar que la toolbar contiene todas las acciones de los skins
        all_expected_skins = [
            "light", "dark",
            "sakura", "winter", "spring", "bamboo", "midnight", "high_night",
            "classic_blue", "peach_fuzz", "marsala", "emerald", "illuminating", "nord",
            "black_sakura", "vampyr", "halloween",
        ]
        for skin in all_expected_skins:
            self.assertIn(skin, window.toolbar.theme_actions)

        # Probar selección de Sakura (Modo claro & dinámico)
        window.set_theme("sakura")
        self.assertEqual(window.current_theme, "sakura")
        self.assertFalse(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["sakura"].isChecked())
        self.assertIn("[Dinámico]", window.toolbar.theme_actions["sakura"].text())
        self.assertEqual(window.particle_overlay.current_effect, "sakura")
        self.assertFalse(window.theme_dark_action.isChecked())
        self.assertFalse(window.theme_light_action.isChecked())
        self.assertFalse(window.statistics_view.weekly_chart.dark_mode)

        # Probar selección de Vampyr (Modo oscuro & dinámico)
        window.set_theme("vampyr")
        self.assertEqual(window.current_theme, "vampyr")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["vampyr"].isChecked())
        self.assertIn("[Dinámico]", window.toolbar.theme_actions["vampyr"].text())
        self.assertEqual(window.particle_overlay.current_effect, "vampyr")

        # Probar selección de Halloween (Modo oscuro & dinámico)
        window.set_theme("halloween")
        self.assertEqual(window.current_theme, "halloween")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["halloween"].isChecked())
        self.assertIn("[Dinámico]", window.toolbar.theme_actions["halloween"].text())
        self.assertEqual(window.particle_overlay.current_effect, "halloween")

        # Probar selección de Black Sakura (Modo oscuro & dinámico)
        window.set_theme("black_sakura")
        self.assertEqual(window.current_theme, "black_sakura")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["black_sakura"].isChecked())
        self.assertIn("[Dinámico]", window.toolbar.theme_actions["black_sakura"].text())
        self.assertEqual(window.particle_overlay.current_effect, "sakura")

        # Probar selección de Midnight (Modo oscuro)
        window.set_theme("midnight")
        self.assertEqual(window.current_theme, "midnight")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["midnight"].isChecked())
        self.assertFalse(window.toolbar.theme_actions["sakura"].isChecked())
        self.assertTrue(window.statistics_view.weekly_chart.dark_mode)

        # Probar selección de High Night (Modo oscuro & dinámico)
        window.set_theme("high_night")
        self.assertEqual(window.current_theme, "high_night")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["high_night"].isChecked())
        self.assertIn("[Dinámico]", window.toolbar.theme_actions["high_night"].text())
        self.assertEqual(window.particle_overlay.current_effect, "high_night")
        # Simular avance y verificar propiedades de partículas
        window.particle_overlay.step_simulation()
        self.assertGreater(len(window.particle_overlay._particles), 0)
        for p in window.particle_overlay._particles:
            self.assertEqual(p.kind, "high_night")
            self.assertLessEqual(p.base_size, 3.5)

        # Probar selección de Winter (Modo oscuro)
        window.set_theme("winter")
        self.assertEqual(window.current_theme, "winter")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["winter"].isChecked())

        # Probar selección de Bamboo (Modo claro)
        window.set_theme("bamboo")
        self.assertEqual(window.current_theme, "bamboo")
        self.assertFalse(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["bamboo"].isChecked())

        # Probar selección de Peach Fuzz (Modo claro estático)
        window.set_theme("peach_fuzz")
        self.assertEqual(window.current_theme, "peach_fuzz")
        self.assertFalse(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["peach_fuzz"].isChecked())
        self.assertNotIn("[Dinámico]", window.toolbar.theme_actions["peach_fuzz"].text())
        self.assertEqual(window.particle_overlay.current_effect, "none")

        # Probar selección de Classic Blue (Modo oscuro)
        window.set_theme("classic_blue")
        self.assertEqual(window.current_theme, "classic_blue")
        self.assertTrue(window.is_dark_mode)
        self.assertTrue(window.toolbar.theme_actions["classic_blue"].isChecked())

        # Probar avance de simulación de partículas sin excepción
        window.particle_overlay.set_effect("sakura")
        window.particle_overlay.step_simulation()

        # Diálogo para skin personalizado
        sakura_dialog = get_dialog_stylesheet("sakura")
        self.assertIn("#fcf7f8", sakura_dialog)
        midnight_dialog = get_dialog_stylesheet("midnight")
        self.assertIn("#0e1224", midnight_dialog)
        high_night_dialog = get_dialog_stylesheet("high_night")
        self.assertIn("#0b0b0e", high_night_dialog)

    def test_high_night_particle_beat_animation(self) -> None:
        """Verifica la física, dimensiones y el ciclo de destello fugaz (beat) individual de High Night."""
        from presentation.theming.ambient_particle_overlay import AmbientParticleOverlay
        from PySide6.QtWidgets import QWidget

        container = QWidget()
        container.resize(800, 600)
        overlay = AmbientParticleOverlay(container)
        overlay.set_effect("high_night")

        self.assertEqual(overlay.current_effect, "high_night")
        self.assertGreater(len(overlay._particles), 0)

        # 1. Estrellas más pequeñas que las de Midnight (1.2 - 3.2 vs 2.5 - 6.0)
        for p in overlay._particles:
            self.assertEqual(p.kind, "high_night")
            self.assertGreaterEqual(p.base_size, 1.2)
            self.assertLessEqual(p.base_size, 3.2)
            # Paleta de tonos claros blanco/grisáceo cuarzo y perla
            self.assertIn(p.color_hex, ["#d8d8e8", "#e4e4ee", "#cfcfe0", "#edeef5", "#c8c4dc"])

        # 2. Forzar cuenta regresiva de destello a 1 y avanzar simulación
        overlay._flash_countdown = 1
        overlay.step_simulation()

        # Debe haberse seleccionado exactamente una estrella individual con flash activo
        flashing_stars = [p for p in overlay._particles if p.flash_timer > 0]
        self.assertEqual(len(flashing_stars), 1)
        flashing = flashing_stars[0]
        self.assertGreater(flashing.flash_duration, 0)
        # El color del destello debe ser claro (blanco/gris, no blanco puro)
        self.assertIn(flashing.flash_color_hex, ["#eef0f6", "#e8eaf2", "#f0f2f8", "#e5e7eb", "#ebebf2"])

        # El nuevo countdown debe estar en el intervalo de 2 a 5 segundos (60 a 150 frames a 30 FPS)
        self.assertGreaterEqual(overlay._flash_countdown, 60)
        self.assertLessEqual(overlay._flash_countdown, 150)

        # 3. Avanzar simulación hasta que termine el destello
        while flashing.flash_timer > 0:
            overlay.step_simulation()

        self.assertEqual(flashing.flash_timer, 0)

    def test_skins_refactor_semantic_tokens_and_propagation(self) -> None:
        """Verifica la carga de tokens semánticos (ausencia, gráficos, cronómetro, pestañas) y su propagación."""
        from presentation.theme_tokens import get_theme_tokens, list_available_themes
        from presentation.theme import get_timer_cards_style, get_status_pill_style

        # 1. Validar que todos los 17 temas cargan los nuevos atributos semánticos
        all_themes = list_available_themes()
        self.assertGreaterEqual(len(all_themes), 17)

        for th in all_themes:
            tok = get_theme_tokens(th)
            self.assertTrue(bool(tok.color_absence), f"Falta color_absence en {th}")
            self.assertTrue(bool(tok.color_absence_border), f"Falta color_absence_border en {th}")
            self.assertTrue(bool(tok.bg_chart), f"Falta bg_chart en {th}")
            self.assertTrue(bool(tok.chart_gridline), f"Falta chart_gridline en {th}")
            self.assertTrue(bool(tok.activity_bar_bg), f"Falta activity_bar_bg en {th}")
            self.assertTrue(bool(tok.activity_bar_fill), f"Falta activity_bar_fill en {th}")
            self.assertTrue(bool(tok.tab_icon_active), f"Falta tab_icon_active en {th}")
            self.assertTrue(bool(tok.tab_icon_inactive), f"Falta tab_icon_inactive en {th}")
            self.assertTrue(bool(tok.clock_card_active_exercise_bg), f"Falta clock_card_active_exercise_bg en {th}")
            self.assertTrue(bool(tok.clock_card_active_break_bg), f"Falta clock_card_active_break_bg en {th}")

        # 2. Validar generación de estilos de cronómetro con tokens
        sakura_tok = get_theme_tokens("sakura")
        ex_css, br_css = get_timer_cards_style("play", is_dark=False, tokens=sakura_tok)
        self.assertIn(sakura_tok.clock_card_active_exercise_bg, ex_css)
        self.assertIn(sakura_tok.clock_card_active_exercise_border, ex_css)

        ex_css_br, br_css_br = get_timer_cards_style("break", is_dark=False, tokens=sakura_tok)
        self.assertIn(sakura_tok.clock_card_active_break_bg, br_css_br)
        self.assertIn(sakura_tok.clock_card_active_break_border, br_css_br)

        # 3. Validar propagación en MainWindow y componentes pasivos
        window = MainWindow()
        self.addCleanup(window.close)

        window.set_theme("sakura")
        self.assertEqual(window.current_theme, "sakura")
        self.assertEqual(window.home_view.current_theme, "sakura")
        self.assertEqual(window.home_view.activity_strip.current_theme, "sakura")
        self.assertEqual(window.statistics_view._current_theme, "sakura")
        self.assertEqual(window.planner._current_theme, "sakura")

        # 4. Validar que los subtab scrolls en estadísticas tienen los objectNames asignados
        self.assertEqual(window.statistics_view.general_tab.findChild(QWidget, "statsScroll").objectName(), "statsScroll")
        self.assertEqual(window.statistics_view.general_tab.findChild(QWidget, "statsContainer").objectName(), "statsContainer")
        self.assertEqual(window.statistics_view.weekly_tab.findChild(QWidget, "statsScroll").objectName(), "statsScroll")
        self.assertEqual(window.statistics_view.weekly_tab.findChild(QWidget, "statsContainer").objectName(), "statsContainer")
        self.assertEqual(window.statistics_view.daily_tab.findChild(QWidget, "statsScroll").objectName(), "statsScroll")
        self.assertEqual(window.statistics_view.daily_tab.findChild(QWidget, "statsContainer").objectName(), "statsContainer")

        # 5. Validar que summary_frame en planificador no tiene inline stylesheet anulando el tema
        self.assertEqual(window.planner.summary_frame.styleSheet(), "")


if __name__ == "__main__":
    unittest.main()


