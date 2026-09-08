import os
import unittest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["STUDY_TIMETRIAL_TEST"] = "1"

from domain.models import PlannedSection
from presentation.main_window import MainWindow


class TestMainWindowPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def test_planner_tab_exists(self):
        # The window must have 4 tabs
        self.assertEqual(self.window.tabs.count(), 4)
        self.assertIn("Planificador", self.window.tabs.tabText(3))
        self.assertTrue(hasattr(self.window, "planner"))

    def test_planner_load_timer_action(self):
        # Simulate loading exercise 5 inciso 2 of Guía 4 from planner
        self.window._on_planner_load_timer("Guía", 4, 5, 2)
        self.assertEqual(self.window.section_input.text(), "Guía")
        self.assertEqual(self.window.section_number_input.value(), 4)
        self.assertEqual(self.window.exercise_input.value(), 5)
        self.assertEqual(self.window.inciso_input.value(), 2)
        self.assertEqual(self.window.tabs.currentIndex(), 0)

    def test_boundary_check_when_within_and_exceeded(self):
        # Configure a planned section with 10 exercises
        self.window.application.add_or_update_planned_section(
            PlannedSection(section_type="Guía", section_number=1, total_exercises=10)
        )
        # Inside bounds (exercise 5) -> returns True without dialog
        from application.application_service import SessionLocation

        within_loc = SessionLocation(section_type="Guía", section_number=1, exercise=5, inciso=None)
        self.assertTrue(self.window.application.check_location_boundary(within_loc)[0])

        # Exceeded bounds (exercise 15) -> returns False with detail message
        exceeded_loc = SessionLocation(section_type="Guía", section_number=1, exercise=15, inciso=None)
        ok, msg = self.window.application.check_location_boundary(exceeded_loc)
        self.assertFalse(ok)
        self.assertIn("supera los 10 ejercicios", msg)

    def test_composite_exercise_group_no_ej_label_and_uses_flow_layout(self):
        from presentation.flow_layout import FlowLayout
        from presentation.planner_widget import CompositeExerciseGroup, PlannedSectionCard
        from PySide6.QtWidgets import QLabel

        sec = PlannedSection(
            section_type="Guía",
            section_number=2,
            total_exercises=8,
            exercise_configs={7: 4},
        )
        self.window.application.add_or_update_planned_section(sec)
        self.window.planner.refresh_view()

        cards = self.window.planner.findChildren(PlannedSectionCard)
        target_card = [c for c in cards if c.sec_status.section.section_number == 2][0]

        # Verificar que el contenedor de ejercicios usa FlowLayout
        flow_layouts = target_card.findChildren(FlowLayout)
        self.assertTrue(len(flow_layouts) >= 1)

        # Verificar que el grupo compuesto no tiene una etiqueta "Ej. 7"
        comp_groups = target_card.findChildren(CompositeExerciseGroup)
        self.assertEqual(len(comp_groups), 1)
        group = comp_groups[0]

        labels = group.findChildren(QLabel)
        ej_labels = [l for l in labels if "Ej." in l.text()]
        self.assertEqual(len(ej_labels), 0, "No debe haber etiquetas de 'Ej.{n}' en el grupo con incisos")

        # Verificar que contiene los botones de incisos 7.1, 7.2, 7.3, 7.4
        from presentation.planner_widget import ExerciseCellButton

        sub_btns = group.findChildren(ExerciseCellButton)
        self.assertEqual(len(sub_btns), 4)
        labels_text = [b.text() for b in sub_btns]
        self.assertEqual(labels_text, ["7.1", "7.2", "7.3", "7.4"])

    def test_composite_exercises_and_single_exercises_vertically_aligned_in_row(self):
        from presentation.planner_widget import CompositeExerciseGroup, ExerciseCellButton, PlannedSectionCard

        sec = PlannedSection(
            section_type="Guía",
            section_number=3,
            total_exercises=6,
            exercise_configs={2: 2},
        )
        self.window.application.add_or_update_planned_section(sec)
        self.window.tabs.setCurrentIndex(3)
        self.window.resize(1000, 700)
        self.window.show()
        for _ in range(5):
            QApplication.processEvents()

        cards = self.window.planner.findChildren(PlannedSectionCard)
        target_card = [c for c in cards if c.sec_status.section.section_number == 3][0]

        btn_single = [b for b in target_card.findChildren(ExerciseCellButton) if b.text() == "1"][0]
        btn_inciso = [b for b in target_card.findChildren(ExerciseCellButton) if b.text() == "2.1"][0]
        comp_group = target_card.findChildren(CompositeExerciseGroup)[0]

        pos_single = btn_single.mapTo(target_card, btn_single.rect().topLeft())
        pos_inciso = btn_inciso.mapTo(target_card, btn_inciso.rect().topLeft())
        pos_group = comp_group.mapTo(target_card, comp_group.rect().topLeft())

        # Ambos botones deben estar a la misma altura vertical en la fila
        self.assertEqual(pos_single.y(), pos_inciso.y())
        # El centro vertical del grupo punteado y los botones debe coincidir
        center_y_single = pos_single.y() + btn_single.height() // 2
        center_y_group = pos_group.y() + comp_group.height() // 2
        self.assertEqual(center_y_single, center_y_group)


if __name__ == "__main__":
    unittest.main()


