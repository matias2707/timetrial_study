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
        # Cada ejercicio tiene peso 1 independientemente de sus incisos: 5 ejercicios = 5 units
        self.assertEqual(overview.total_units, 5)
        self.assertEqual(overview.pending_units, 5)
        self.assertEqual(overview.completed_units, 0)
        self.assertEqual(overview.completed_weight, 0.0)
        self.assertEqual(overview.failed_units, 0)
        self.assertEqual(overview.global_completion_percentage, 0.0)

    def test_overview_with_completed_and_failed_items(self):
        # Ejercicio 1 completado (aporta 1.0 de peso)
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
        # Ejercicio 2 inciso 2 completado (aporta 1/3 = ~0.333 de peso)
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
        self.assertEqual(overview.total_units, 5)
        self.assertEqual(overview.completed_units, 1)  # Sólo Ej 1 está 100% completo
        self.assertEqual(overview.failed_units, 1)     # Ej 2 está en dificultad
        self.assertEqual(overview.pending_units, 3)    # Ej 3, Ej 4, Ej 5
        self.assertAlmostEqual(overview.completed_weight, 1.0 + 1 / 3)
        self.assertAlmostEqual(overview.global_completion_percentage, ((1.0 + 1 / 3) / 5) * 100.0)

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

    def test_exercise_with_ten_incisos_has_weight_of_one_exercise(self):
        """Verifica que un ejercicio con 10 incisos rápidos no distorsione las barras de progreso."""
        rec = Record(record_name="Planner10Incisos")
        # Guía de 5 ejercicios: Ej 1, Ej 2 (con 10 incisos), Ej 3, Ej 4, Ej 5
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=5,
            exercise_configs={2: 10},
        )
        rec.planner_sections.append(sec)

        # 1. Al inicio: 5 unidades en total, 0 completadas
        ov1 = PlannerService.compute_overview(rec)
        self.assertEqual(ov1.total_units, 5)
        self.assertEqual(ov1.completed_weight, 0.0)
        self.assertEqual(ov1.global_completion_percentage, 0.0)

        # 2. Completar 5 de los 10 incisos del Ejercicio 2 (50% del Ejercicio 2 = 0.5 ejercicios de progreso)
        for i in range(1, 6):
            rec.items.append(
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=2,
                    inciso=i,
                    exercise_time_ms=60_000,
                    break_time_ms=0,
                    completed=True,
                )
            )
        ov2 = PlannerService.compute_overview(rec)
        self.assertEqual(ov2.total_units, 5)
        self.assertAlmostEqual(ov2.completed_weight, 0.5)
        # 0.5 / 5 = 10% de avance exacto (y no 5/14 = 35.7%)
        self.assertAlmostEqual(ov2.global_completion_percentage, 10.0)
        self.assertEqual(ov2.completed_display, "0.5")
        self.assertEqual(ov2.completed_units, 0)  # El Ejercicio 2 aún no está 100% terminado

        # 3. Completar los 5 incisos restantes del Ejercicio 2 (Ejercicio 2 queda 100% terminado)
        for i in range(6, 11):
            rec.items.append(
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=2,
                    inciso=i,
                    exercise_time_ms=60_000,
                    break_time_ms=0,
                    completed=True,
                )
            )
        ov3 = PlannerService.compute_overview(rec)
        self.assertEqual(ov3.total_units, 5)
        self.assertAlmostEqual(ov3.completed_weight, 1.0)
        # 1.0 / 5 = 20% de avance
        self.assertAlmostEqual(ov3.global_completion_percentage, 20.0)
        self.assertEqual(ov3.completed_display, "1")
        self.assertEqual(ov3.completed_units, 1)  # 1 ejercicio 100% completado


if __name__ == "__main__":
    unittest.main()
