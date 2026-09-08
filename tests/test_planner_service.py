import unittest
from domain.models import PlannedSection, Record, TimerItem
from application.planner_service import (
    PlannerService,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
)


class TestPlannerService(unittest.TestCase):
    def setUp(self):
        self.record = Record(record_name="TestSync")
        self.sec = PlannedSection(
            section_type="Guía",
            section_number=4,
            title="Álgebra",
            total_exercises=5,
            exercise_configs={2: 3},  # Ejercicio 2 tiene 3 incisos: 1, 2, 3
        )
        self.record.planner_sections.append(self.sec)

    def test_overview_initial_pending(self):
        overview = PlannerService.compute_overview(self.record)
        # Total units: ex 1 (1 unit), ex 2 (3 incisos = 3 units), ex 3 (1), ex 4 (1), ex 5 (1) = 7 units
        self.assertEqual(overview.total_units, 7)
        self.assertEqual(overview.pending_units, 7)
        self.assertEqual(overview.completed_units, 0)
        self.assertEqual(overview.failed_units, 0)
        self.assertEqual(overview.global_completion_percentage, 0.0)

    def test_overview_with_completed_and_failed_items(self):
        # Ejercicio 1 completado
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=1,
                inciso=None,
                exercise_time_ms=1000,
                break_time_ms=100,
                completed=True,
            )
        )
        # Ejercicio 2 inciso 1 fallado
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=2,
                inciso=1,
                exercise_time_ms=500,
                break_time_ms=0,
                completed=False,
            )
        )
        # Ejercicio 2 inciso 2 completado
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=2,
                inciso=2,
                exercise_time_ms=800,
                break_time_ms=50,
                completed=True,
            )
        )

        overview = PlannerService.compute_overview(self.record)
        self.assertEqual(overview.total_units, 7)
        self.assertEqual(overview.completed_units, 2)  # Ej 1 y Ej 2.2
        self.assertEqual(overview.failed_units, 1)     # Ej 2.1
        self.assertEqual(overview.pending_units, 4)    # Ej 2.3, Ej 3, Ej 4, Ej 5

        sec_status = overview.sections[0]
        self.assertEqual(len(sec_status.exercise_nodes), 5)
        # Check node for exercise 2 (has incisos)
        node_ex2 = sec_status.exercise_nodes[1]
        self.assertTrue(node_ex2.has_incisos)
        self.assertEqual(len(node_ex2.incisos), 3)
        self.assertEqual(node_ex2.incisos[0].status, STATUS_FAILED)
        self.assertEqual(node_ex2.incisos[1].status, STATUS_COMPLETED)
        self.assertEqual(node_ex2.incisos[2].status, STATUS_PENDING)

    def test_sync_planner_with_records(self):
        # Agregar un item de Guía 4 Ejercicio 8 (supera los 5 planificados)
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=8,
                inciso=None,
                exercise_time_ms=600,
                break_time_ms=0,
                completed=True,
            )
        )
        # Agregar un item de Guía 5 (no estaba planificada)
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=5,
                exercise=3,
                inciso=2,
                exercise_time_ms=900,
                break_time_ms=0,
                completed=True,
            )
        )

        modified = PlannerService.sync_planner_with_records(self.record)
        self.assertTrue(modified)
        self.assertEqual(self.sec.total_exercises, 8)  # ampliado a 8
        self.assertEqual(len(self.record.planner_sections), 2)  # Guía 5 agregada

        sec5 = [s for s in self.record.planner_sections if s.section_number == 5][0]
        self.assertEqual(sec5.total_exercises, 3)
        self.assertEqual(sec5.get_incisos_count(3), 2)

    def test_is_location_within_plan(self):
        ok, _ = PlannerService.is_location_within_plan(self.record, "Guía", 4, 3, None)
        self.assertTrue(ok)

        # Fuera de rango de ejercicios
        ok, msg = PlannerService.is_location_within_plan(self.record, "Guía", 4, 6, None)
        self.assertFalse(ok)
        self.assertIn("supera los 5 ejercicios", msg)

        # Inciso en ejercicio que no tiene incisos
        ok, msg = PlannerService.is_location_within_plan(self.record, "Guía", 4, 1, 2)
        self.assertFalse(ok)
        self.assertIn("no tiene incisos", msg)

        # Inciso que supera el máximo (ejercicio 2 tiene 3)
        ok, msg = PlannerService.is_location_within_plan(self.record, "Guía", 4, 2, 4)
        self.assertFalse(ok)
        self.assertIn("supera los 3 incisos", msg)

        # Guía inexistente
        ok, msg = PlannerService.is_location_within_plan(self.record, "Guía", 99, 1, None)
        self.assertFalse(ok)
        self.assertIn("no forma parte", msg)


if __name__ == "__main__":
    unittest.main()
