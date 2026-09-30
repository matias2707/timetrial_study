"""Pruebas unitarias para el servicio de aplicación del Organizador."""

from __future__ import annotations

import unittest
from domain.models import OrganizedSection, Record, TimerItem
from application.organizer_service import (
    OrganizerService,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
)


class TestOrganizerService(unittest.TestCase):
    def setUp(self):
        self.record = Record(record_name="TestSync")
        self.sec = OrganizedSection(
            section_type="Guía",
            section_number=4,
            title="Álgebra",
            total_exercises=5,
            exercise_configs={2: 3},  # Ejercicio 2 tiene 3 incisos: 1, 2, 3
        )
        self.record.organizer_sections.append(self.sec)

    def test_overview_initial_pending(self):
        overview = OrganizerService.compute_overview(self.record)
        self.assertEqual(overview.total_units, 5)
        self.assertEqual(overview.pending_units, 5)
        self.assertEqual(overview.completed_units, 0)
        self.assertEqual(overview.completed_weight, 0.0)
        self.assertEqual(overview.failed_units, 0)
        self.assertEqual(overview.global_completion_percentage, 0.0)
        self.assertEqual(overview.global_failed_percentage, 0.0)
        self.assertEqual(overview.sections[0].failed_percentage, 0.0)

    def test_overview_with_completed_and_failed_items(self):
        # Ejercicio 1 completado (1.0 peso)
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
        # Ejercicio 2 inciso 2 completado (1/3 peso)
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

        overview = OrganizerService.compute_overview(self.record)
        self.assertAlmostEqual(overview.completed_weight, 1.0 + 1 / 3, places=2)
        self.assertEqual(overview.failed_units, 1)

        sec_status = overview.sections[0]
        # Ejercicio 1
        e1 = sec_status.exercise_nodes[0]
        self.assertEqual(e1.status, STATUS_COMPLETED)
        # Ejercicio 2 incisos
        node_ex2 = sec_status.exercise_nodes[1]
        self.assertTrue(node_ex2.has_incisos)
        self.assertEqual(len(node_ex2.incisos), 3)
        self.assertEqual(node_ex2.incisos[0].status, STATUS_FAILED)
        self.assertEqual(node_ex2.incisos[1].status, STATUS_COMPLETED)
        self.assertEqual(node_ex2.incisos[2].status, STATUS_PENDING)

    def test_sync_with_records(self):
        # Añadir item no contemplado: Ejercicio 8 inciso 2
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=8,
                inciso=2,
                exercise_time_ms=500,
                break_time_ms=0,
                completed=True,
            )
        )
        modified = OrganizerService.sync_organizer_with_records(self.record)
        self.assertTrue(modified)
        self.assertEqual(self.sec.total_exercises, 8)
        self.assertEqual(self.sec.get_incisos_count(8), 2)


if __name__ == "__main__":
    unittest.main()
