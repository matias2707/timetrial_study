"""Pruebas unitarias para los 5 chips de ejercicios, autoincremento inteligente y reasignación en caliente."""

from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from PySide6.QtWidgets import QApplication

from application.application_service import SessionLocation, StudyApplicationService
from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
)
from domain.models import PlannedSection, Record, TimerItem
from domain.timer_service import TimerMode
from infrastructure.storage_service import StorageService
from presentation.audio_service import AudioService
from presentation.home_view import HomeViewWidget


class TestExerciseChipsAndAutoAdvance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.record_path = Path(self.temp_dir.name) / "test_record.json"
        self.storage = StorageService(self.record_path)
        self.application = StudyApplicationService(storage=self.storage)
        self.application.record = Record(record_name="TestRecord")
        self.application.storage.save(self.application.record, self.record_path)
        self.audio_service = AudioService()
        self.audio_service.is_muted = True

        self.home_view = HomeViewWidget(
            application=self.application,
            audio_service=self.audio_service,
            is_dark_mode=True,
        )

    def tearDown(self) -> None:
        self.home_view.deleteLater()
        self.temp_dir.cleanup()

    # --- 1. get_exercise_status y get_or_create_exercise_node sin y con plan ---

    def test_exercise_status_free_study_mode(self) -> None:
        """Verifica el cálculo de estados en modo estudio libre (sin secciones planificadas)."""
        # Sin items -> PENDING
        self.assertEqual(
            self.application.get_exercise_status("Guía", 1, 10),
            STATUS_PENDING,
        )

        # Agregar intento incompleto -> FAILED
        item_failed = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=10,
            inciso=None,
            exercise_time_ms=5000,
            break_time_ms=0,
            completed=False,
        )
        self.application.add_item(item_failed)
        self.assertEqual(
            self.application.get_exercise_status("Guía", 1, 10),
            STATUS_FAILED,
        )

        # Agregar intento completado -> COMPLETED
        item_completed = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=10,
            inciso=None,
            exercise_time_ms=10000,
            break_time_ms=0,
            completed=True,
        )
        self.application.add_item(item_completed)
        self.assertEqual(
            self.application.get_exercise_status("Guía", 1, 10),
            STATUS_COMPLETED,
        )

    def test_get_or_create_exercise_node_without_plan(self) -> None:
        """Verifica que get_or_create_exercise_node construya un nodo válido sin planificador."""
        self.application.set_exercise_note("Guía", 1, 5, None, "Nota de prueba")
        node = self.application.get_or_create_exercise_node("Guía", 1, 5, None)
        self.assertEqual(node.exercise, 5)
        self.assertEqual(node.section_type, "Guía")
        self.assertEqual(node.note, "Nota de prueba")
        self.assertTrue(node.has_note)
        self.assertEqual(node.status, STATUS_PENDING)

    def test_get_or_create_exercise_node_with_plan(self) -> None:
        """Verifica que get_or_create_exercise_node devuelva el nodo preexistente de la planificación."""
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=15,
        )
        sec.set_note(3, None, "Nota planificada")
        self.application.record.planner_sections.append(sec)

        node = self.application.get_or_create_exercise_node("Guía", 1, 3, None)
        self.assertEqual(node.exercise, 3)
        self.assertEqual(node.note, "Nota planificada")

    # --- 2. Comportamiento y etiquetas de los 5 chips ---

    def test_exercise_chips_values_centered_on_exercise(self) -> None:
        """Verifica que el 3° chip sea siempre el actual y los valores sean [E-2, E-1, E, E+1, E+2]."""
        self.home_view.exercise_input.setValue(20)
        self.home_view.sync_location()

        chips = self.home_view.exercise_chips
        self.assertEqual(len(chips), 5)
        self.assertEqual(chips[0].text(), "18")
        self.assertEqual(chips[1].text(), "19")
        self.assertEqual(chips[2].text(), "20")  # 3° chip
        self.assertEqual(chips[3].text(), "21")
        self.assertEqual(chips[4].text(), "22")

        # Verificar que el 3° chip tenga estilo con borde activo
        self.assertIn("2.5px solid", chips[2].styleSheet())

    def test_exercise_chips_edge_cases_when_e_is_1_and_2(self) -> None:
        """Verifica que cuando E=1 o E=2 los slots anteriores muestren '—' y queden inactivos."""
        # Caso E = 1
        self.home_view.exercise_input.setValue(1)
        self.home_view.sync_location()

        chips = self.home_view.exercise_chips
        self.assertEqual(chips[0].text(), "—")
        self.assertFalse(chips[0].isEnabled())
        self.assertEqual(chips[1].text(), "—")
        self.assertFalse(chips[1].isEnabled())
        self.assertEqual(chips[2].text(), "1")  # 3° chip
        self.assertTrue(chips[2].isEnabled())
        self.assertEqual(chips[3].text(), "2")
        self.assertEqual(chips[4].text(), "3")

        # Caso E = 2
        self.home_view.exercise_input.setValue(2)
        self.home_view.sync_location()

        self.assertEqual(chips[0].text(), "—")
        self.assertFalse(chips[0].isEnabled())
        self.assertEqual(chips[1].text(), "1")
        self.assertTrue(chips[1].isEnabled())
        self.assertEqual(chips[2].text(), "2")  # 3° chip
        self.assertTrue(chips[2].isEnabled())
        self.assertEqual(chips[3].text(), "3")
        self.assertEqual(chips[4].text(), "4")

    # --- 3. Reasignación en caliente durante la sesión activa ---

    def test_in_flight_reassignment_during_timer(self) -> None:
        """Verifica que durante TimerMode.PLAY se pueda cambiar el ejercicio en caliente sin perder tiempo."""
        self.home_view.exercise_input.setValue(20)
        self.home_view.sync_location()

        # Iniciar sesión
        self.home_view.toggle_session()
        self.assertEqual(self.application.mode, TimerMode.PLAY)

        # Los controles de ejercicio deben seguir habilitados
        self.assertTrue(self.home_view.exercise_input.isEnabled())
        self.assertTrue(self.home_view.inciso_input.isEnabled())

        # Cambiar ejercicio a 21 mientras el cronómetro corre
        self.home_view.exercise_input.setValue(21)
        # sync_location se dispara por valueChanged
        self.assertEqual(self.application.location.exercise, 21)
        self.assertIn("Ejercicio 21", self.home_view.location_label.text())

        # El reloj sigue en PLAY
        self.assertEqual(self.application.mode, TimerMode.PLAY)

        # Los chips se actualizaron para centrar el 21
        self.assertEqual(self.home_view.exercise_chips[2].text(), "21")

        # Finalizar ítem y verificar que se guarda como 21
        self.home_view.finish_item(completed=True)
        saved_items = self.application.record.items
        self.assertEqual(len(saved_items), 1)
        self.assertEqual(saved_items[0].exercise, 21)

    # --- 4. Autoincremento inteligente al completar ---

    def test_auto_advance_enabled_advances_exercise(self) -> None:
        """Verifica que al completar con auto-avanzar activo, el selector pase a E+1."""
        self.home_view.auto_advance_checkbox.setChecked(True)
        self.home_view.exercise_input.setValue(15)
        self.home_view.sync_location()

        self.home_view.toggle_session()
        self.home_view.finish_item(completed=True)

        # Debe haber avanzado a 16
        self.assertEqual(self.home_view.exercise_input.value(), 16)
        self.assertEqual(self.application.location.exercise, 16)
        self.assertEqual(self.home_view.exercise_chips[2].text(), "16")

    def test_auto_advance_disabled_keeps_same_exercise(self) -> None:
        """Verifica que si auto-avanzar está deshabilitado, el selector no cambie."""
        self.home_view.auto_advance_checkbox.setChecked(False)
        self.home_view.exercise_input.setValue(15)
        self.home_view.sync_location()

        self.home_view.toggle_session()
        self.home_view.finish_item(completed=True)

        self.assertEqual(self.home_view.exercise_input.value(), 15)

    def test_incomplete_item_does_not_auto_advance(self) -> None:
        """Verifica que marcar un ítem como incompleto NO avance el ejercicio."""
        self.home_view.auto_advance_checkbox.setChecked(True)
        self.home_view.exercise_input.setValue(15)
        self.home_view.sync_location()

        self.home_view.toggle_session()
        self.home_view.finish_item(completed=False)

        # Sigue en 15 para permitir reintento
        self.assertEqual(self.home_view.exercise_input.value(), 15)

    def test_auto_advance_with_planned_incisos(self) -> None:
        """Verifica que el auto-avance respete los incisos planificados antes de pasar de ejercicio."""
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=5,
            exercise_configs={2: 2},  # Ejercicio 2 tiene 2 incisos
        )
        self.application.record.planner_sections.append(sec)

        self.home_view.auto_advance_checkbox.setChecked(True)
        self.home_view.exercise_input.setValue(2)
        self.home_view.inciso_input.setValue(1)
        self.home_view.sync_location()

        # Completar inciso 1 -> Debe avanzar a inciso 2
        self.home_view.toggle_session()
        self.home_view.finish_item(completed=True)
        self.assertEqual(self.home_view.exercise_input.value(), 2)
        self.assertEqual(self.home_view.inciso_input.value(), 2)

        # Completar inciso 2 -> Debe avanzar a ejercicio 3 (sin inciso)
        self.home_view.toggle_session()
        self.home_view.finish_item(completed=True)
        self.assertEqual(self.home_view.exercise_input.value(), 3)
        self.assertEqual(self.home_view.inciso_input.value(), 0)

    # --- 5. Detalle de color en el título del ejercicio ---

    def test_exercise_title_color_detail_status(self) -> None:
        """Verifica que el título del ejercicio refleje visualmente los 3 estados: pendiente, falla y completado."""
        self.home_view.auto_advance_checkbox.setChecked(False)
        self.home_view.exercise_input.setValue(10)
        self.home_view.sync_location()

        # 1. Estado inicial: Sin realizar (Pendiente)
        self.assertNotIn("●", self.home_view.location_label.text())
        self.assertEqual("Guía 1 · Ejercicio 10", self.home_view.location_label.text())
        self.assertIn("Sin realizar", self.home_view.location_label.toolTip())
        self.assertIn("border: 2px solid #334155", self.home_view.location_label.styleSheet())
        self.assertIn("background-color: #1e293b", self.home_view.location_label.styleSheet())
        self.assertIn("color: #94a3b8", self.home_view.location_label.styleSheet())

        # 2. Estado en falla / dificultad
        self.home_view.toggle_session()
        self.home_view.finish_item(completed=False)
        self.assertNotIn("●", self.home_view.location_label.text())
        self.assertEqual("Guía 1 · Ejercicio 10", self.home_view.location_label.text())
        self.assertIn("En dificultad", self.home_view.location_label.toolTip())
        self.assertIn("border: 2px solid #7f1d1d", self.home_view.location_label.styleSheet())
        self.assertIn("background-color: #450a0a", self.home_view.location_label.styleSheet())
        self.assertIn("color: #fca5a5", self.home_view.location_label.styleSheet())

        # 3. Estado completado
        self.home_view.toggle_session()
        self.home_view.finish_item(completed=True)
        self.assertNotIn("●", self.home_view.location_label.text())
        self.assertEqual("Guía 1 · Ejercicio 10", self.home_view.location_label.text())
        self.assertIn("Completado", self.home_view.location_label.toolTip())
        self.assertIn("border: 2px solid #059669", self.home_view.location_label.styleSheet())
        self.assertIn("background-color: #064e3b", self.home_view.location_label.styleSheet())
        self.assertIn("color: #6ee7b7", self.home_view.location_label.styleSheet())

    def test_location_label_click_opens_chip_modal(self) -> None:
        """Verifica que clickear el título del ejercicio abra el modal de detalle como el 3° chip."""
        from PySide6.QtCore import Qt
        from unittest.mock import MagicMock

        # Verificar cursor interactivo
        self.assertEqual(self.home_view.location_label.cursor().shape(), Qt.CursorShape.PointingHandCursor)

        # Verificar que el click delegue a _on_chip_clicked(2)
        mock_chip_click = MagicMock()
        self.home_view._on_chip_clicked = mock_chip_click

        self.home_view._on_location_label_clicked()
        mock_chip_click.assert_called_once_with(2)

    def test_location_selectors_enlarged_font_styles(self) -> None:
        """Verifica que los selectores y encabezados inferiores usen las clases de fuente agrandada."""
        from presentation.theme import get_theme_stylesheet, THEME_DARK, THEME_LIGHT

        # Verificar objectNames asignados
        self.assertEqual(self.home_view.section_input.objectName(), "location_selector_input")
        self.assertEqual(self.home_view.section_number_input.objectName(), "location_selector_input")
        self.assertEqual(self.home_view.exercise_input.objectName(), "location_selector_input")
        self.assertEqual(self.home_view.inciso_input.objectName(), "location_selector_input")

        # Verificar reglas en el QSS para ambos temas
        for theme_name in (THEME_DARK, THEME_LIGHT):
            css = get_theme_stylesheet(theme_name)
            self.assertIn("QLabel#location_selector_label", css)
            self.assertIn("font-size: 13px", css)
            self.assertIn("QLineEdit#location_selector_input", css)
            self.assertIn("font-size: 16px", css)


if __name__ == "__main__":
    unittest.main()

