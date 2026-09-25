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
        # The window must have 5 tabs (Cronómetro, Registros, Estadísticas, Planificador, Ambientación)
        self.assertEqual(self.window.tabs.count(), 5)
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

    def test_planner_single_segmented_progress_bar_for_completed_and_failed(self):
        from domain.models import TimerItem
        from presentation.planner_widget import PlannedSectionCard, SegmentedProgressBar
        from PySide6.QtWidgets import QProgressBar

        # Verificar que el planificador tiene una barra global unificada (tipo SegmentedProgressBar y QProgressBar)
        self.assertTrue(hasattr(self.window.planner, "global_progress_bar"))
        self.assertIsInstance(self.window.planner.global_progress_bar, SegmentedProgressBar)
        self.assertIsInstance(self.window.planner.global_progress_bar, QProgressBar)

        # Configurar una sección de 4 ejercicios
        sec = PlannedSection(
            section_type="Guía",
            section_number=10,
            total_exercises=4,
        )
        self.window.application.add_or_update_planned_section(sec)

        # Agregar Ejercicio 1 completado y Ejercicio 2 fallado
        self.window.application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=10,
                exercise=1,
                inciso=None,
                exercise_time_ms=1000,
                break_time_ms=0,
                completed=True,
            )
        )
        self.window.application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=10,
                exercise=2,
                inciso=None,
                exercise_time_ms=800,
                break_time_ms=0,
                completed=False,
            )
        )

        self.window.planner.refresh_view()

        # Barra global unificada (1 de 4 completado = 25%, 1 de 4 en dificultad = 25%)
        g_bar = self.window.planner.global_progress_bar
        self.assertAlmostEqual(g_bar.completed_percentage, 25.0)
        self.assertAlmostEqual(g_bar.failed_percentage, 25.0)
        self.assertEqual(g_bar.value(), 25)

        # Verificar barra de progreso en la tarjeta (debe ser una sola barra unificada)
        cards = self.window.planner.findChildren(PlannedSectionCard)
        target_card = [c for c in cards if c.sec_status.section.section_number == 10][0]

        card_bars = target_card.findChildren(SegmentedProgressBar)
        self.assertEqual(len(card_bars), 1)
        sec_bar = card_bars[0]
        self.assertEqual(sec_bar.objectName(), "sec_progress_bar")
        self.assertAlmostEqual(sec_bar.completed_percentage, 25.0)
        self.assertAlmostEqual(sec_bar.failed_percentage, 25.0)
        self.assertEqual(sec_bar.value(), 25)

    def test_inciso_group_header_button_and_collapse_expand_toggle(self):
        """Verifica que el botón cabecera [ n ] contrae y expande los incisos individuales."""
        from presentation.planner_widget import CompositeExerciseGroup, GroupHeaderCellButton, PlannedSectionCard
        from PySide6.QtCore import QSize

        sec = PlannedSection(
            section_type="Guía",
            section_number=5,
            total_exercises=4,
            exercise_configs={2: 4},  # Ejercicio 2 tiene 4 incisos: 2.1, 2.2, 2.3, 2.4
        )
        self.window.application.add_or_update_planned_section(sec)
        self.window.planner.refresh_view()

        cards = self.window.planner.findChildren(PlannedSectionCard)
        target_card = [c for c in cards if c.sec_status.section.section_number == 5][0]
        comp_group = target_card.findChildren(CompositeExerciseGroup)[0]

        # Verificar botón cabecera
        header_btn = comp_group.header_btn
        self.assertIsInstance(header_btn, GroupHeaderCellButton)
        self.assertEqual(header_btn.text(), "2")
        self.assertEqual(header_btn.sizeHint(), QSize(52, 48))

        # Estado inicial: expandido (sub-botones no ocultos)
        self.assertFalse(comp_group.is_collapsed)
        self.assertEqual(len(comp_group.sub_buttons), 4)
        for btn in comp_group.sub_buttons:
            self.assertFalse(btn.isHidden())

        # 1er Clic en la cabecera: contraer
        header_btn.click()
        self.assertTrue(comp_group.is_collapsed)
        self.assertTrue(header_btn.is_collapsed)
        for btn in comp_group.sub_buttons:
            self.assertTrue(btn.isHidden())

        # 2do Clic en la cabecera: expandir nuevamente
        header_btn.click()
        self.assertFalse(comp_group.is_collapsed)
        self.assertFalse(header_btn.is_collapsed)
        for btn in comp_group.sub_buttons:
            self.assertFalse(btn.isHidden())

    def test_global_expand_all_button_toggles_all_groups(self):
        """Verifica que el botón general en la barra superior contrae y expande todos los grupos."""
        from presentation.planner_widget import CompositeExerciseGroup

        sec1 = PlannedSection(section_type="Guía", section_number=6, total_exercises=3, exercise_configs={1: 2})
        sec2 = PlannedSection(section_type="Guía", section_number=7, total_exercises=3, exercise_configs={2: 3})
        self.window.application.add_or_update_planned_section(sec1)
        self.window.application.add_or_update_planned_section(sec2)
        self.window.planner.refresh_view()

        btn_toggle = self.window.planner.btn_toggle_expand_all
        self.assertIsNotNone(btn_toggle)
        self.assertIn("Contraer", btn_toggle.text())

        groups = self.window.planner.findChildren(CompositeExerciseGroup)
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(not g.is_collapsed for g in groups))

        # Clic para contraer todos
        btn_toggle.click()
        self.assertTrue(self.window.planner.all_incisos_collapsed)
        self.assertIn("Expandir", btn_toggle.text())
        self.assertTrue(all(g.is_collapsed for g in groups))
        for g in groups:
            for b in g.sub_buttons:
                self.assertTrue(b.isHidden())

        # Clic para expandir todos
        btn_toggle.click()
        self.assertFalse(self.window.planner.all_incisos_collapsed)
        self.assertIn("Contraer", btn_toggle.text())
        self.assertTrue(all(not g.is_collapsed for g in groups))
        for g in groups:
            for b in g.sub_buttons:
                self.assertFalse(b.isHidden())

    def test_group_header_button_color_priority_and_compressed_icons(self):
        """Verifica la jerarquía de color (gris > rojo > verde) y el pintado en modo comprimido."""
        from domain.models import TimerItem
        from presentation.planner_widget import CompositeExerciseGroup, PlannedSectionCard
        from application.planner_service import STATUS_COMPLETED, STATUS_FAILED, STATUS_PENDING

        sec = PlannedSection(
            section_type="Guía",
            section_number=8,
            total_exercises=3,
            exercise_configs={1: 2},
            exercise_tags={"1.1": ["tag-doubt"]},
            exercise_notes={"1.2": "Fórmula importante"},
        )
        self.window.application.add_or_update_planned_section(sec)

        # Caso A: 1.1 completado (verde), 1.2 pendiente (gris) -> Prioridad Gris
        self.window.application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=8,
                exercise=1,
                inciso=1,
                exercise_time_ms=1000,
                break_time_ms=0,
                completed=True,
            )
        )
        self.window.planner.refresh_view()
        QApplication.processEvents()

        cards = [c for c in self.window.planner.findChildren(PlannedSectionCard) if c.sec_status.section.section_number == 8]
        target_card = cards[-1]
        group = target_card.findChildren(CompositeExerciseGroup)[0]

        # Gris > Verde -> group_color_status es STATUS_PENDING
        self.assertEqual(group.header_btn.node.group_color_status, STATUS_PENDING)

        # Caso B: 1.2 fallado (rojo), 1.1 completado (verde), ninguno pendiente -> Prioridad Rojo
        self.window.application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=8,
                exercise=1,
                inciso=2,
                exercise_time_ms=800,
                break_time_ms=0,
                completed=False,
            )
        )
        self.window.planner.refresh_view()
        QApplication.processEvents()
        cards = [c for c in self.window.planner.findChildren(PlannedSectionCard) if c.sec_status.section.section_number == 8]
        target_card = cards[-1]
        group = target_card.findChildren(CompositeExerciseGroup)[0]
        self.assertEqual(group.header_btn.node.group_color_status, STATUS_FAILED)


        # En modo contraído, el botón cabecera consolida marcadores y notas
        group.set_collapsed(True)
        self.assertEqual(len(group.header_btn.node.aggregated_tags), 1)
        self.assertTrue(group.header_btn.node.aggregated_has_note)

    def test_planner_multi_column_responsive_layout(self):
        """Verifica la adaptabilidad multi-columna de la cuadrícula según el ancho disponible."""
        planner = self.window.planner
        # Verificar función matemática de cálculo de columnas óptimas
        self.assertEqual(planner._calculate_optimal_columns(700), 1)
        self.assertEqual(planner._calculate_optimal_columns(1000), 2)
        self.assertEqual(planner._calculate_optimal_columns(1900), 4)
        self.assertEqual(planner._calculate_optimal_columns(3400), 7)

        # Configurar 4 secciones y verificar distribución
        for i in range(1, 5):
            self.window.application.add_or_update_planned_section(
                PlannedSection(section_type="Guía", section_number=20 + i, total_exercises=4)
            )
        planner.refresh_view()

        # Simular ancho de 1000px (2 columnas)
        planner._current_column_count = 2
        planner._rebuild_columns()
        self.assertEqual(len(planner.column_layouts), 2)

        # Con 4 tarjetas y 2 columnas, cada columna debe contener 2 tarjetas (+ 1 stretch)
        cards_col0 = [planner.column_layouts[0].itemAt(j).widget() for j in range(planner.column_layouts[0].count()) if planner.column_layouts[0].itemAt(j).widget()]
        cards_col1 = [planner.column_layouts[1].itemAt(j).widget() for j in range(planner.column_layouts[1].count()) if planner.column_layouts[1].itemAt(j).widget()]
        self.assertEqual(len(cards_col0), 2)
        self.assertEqual(len(cards_col1), 2)

    def test_section_card_individual_collapse_and_expand_toggle(self):
        """Verifica el botón chevron individual para contraer y expandir una sección."""
        from presentation.planner_widget import PlannedSectionCard
        from PySide6.QtWidgets import QPushButton

        sec = PlannedSection(section_type="Guía", section_number=30, total_exercises=6)
        self.window.application.add_or_update_planned_section(sec)
        self.window.planner.refresh_view()

        cards = [c for c in self.window.planner.findChildren(PlannedSectionCard) if c.sec_status.section.section_number == 30]
        self.assertTrue(len(cards) >= 1)
        card = cards[0]

        btn_collapse = card.findChild(QPushButton, "btn_collapse_section")
        self.assertIsNotNone(btn_collapse)
        self.assertFalse(card.is_collapsed)
        self.assertFalse(card.exercises_container.isHidden())
        self.assertFalse(card.sep.isHidden())

        # 1er Clic: contraer sección
        btn_collapse.click()
        self.assertTrue(card.is_collapsed)
        self.assertTrue(card.exercises_container.isHidden())
        self.assertTrue(card.sep.isHidden())

        # 2do Clic: expandir sección
        btn_collapse.click()
        self.assertFalse(card.is_collapsed)
        self.assertFalse(card.exercises_container.isHidden())
        self.assertFalse(card.sep.isHidden())

    def test_global_sections_collapse_toggle(self):
        """Verifica el botón global para contraer y expandir todas las secciones a la vez."""
        from presentation.planner_widget import PlannedSectionCard

        for i in range(1, 4):
            self.window.application.add_or_update_planned_section(
                PlannedSection(section_type="Guía", section_number=40 + i, total_exercises=5)
            )
        self.window.planner.refresh_view()

        btn_toggle_sec = self.window.planner.btn_toggle_sections
        self.assertIsNotNone(btn_toggle_sec)
        self.assertIn("Contraer", btn_toggle_sec.text())

        # Clic para contraer todas las secciones
        btn_toggle_sec.click()
        self.assertTrue(self.window.planner.all_sections_collapsed)
        self.assertIn("Expandir", btn_toggle_sec.text())
        cards = self.window.planner.findChildren(PlannedSectionCard)
        self.assertTrue(all(c.is_collapsed for c in cards))
        self.assertTrue(all(c.exercises_container.isHidden() for c in cards))

        # Clic para expandir todas las secciones
        btn_toggle_sec.click()
        self.assertFalse(self.window.planner.all_sections_collapsed)
        self.assertIn("Contraer", btn_toggle_sec.text())
        self.assertTrue(all(not c.is_collapsed for c in cards))
        self.assertTrue(all(not c.exercises_container.isHidden() for c in cards))


if __name__ == "__main__":
    unittest.main()



