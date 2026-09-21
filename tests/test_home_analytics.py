"""Pruebas unitarias para las analíticas del Home (TASK-014).

Cálculo de récord personal (Personal Best), métricas de resumen de hoy y buckets de 24 horas.
"""

from __future__ import annotations

from datetime import date
import unittest

from application.application_service import StudyApplicationService
from application.statistics_service import (
    compute_exercise_personal_best_ms,
    compute_today_summary_metrics,
    compute_today_timeline_buckets,
)
from domain.models import Record, TimerItem


class TestHomeAnalytics(unittest.TestCase):
    """Verifica las funciones puras de cálculo para el cronómetro rediseñado."""

    def setUp(self) -> None:
        self.record = Record(record_name="TestCourse")

    def test_personal_best_returns_none_when_empty(self) -> None:
        pb = compute_exercise_personal_best_ms(self.record, "Guía", 1, 1, None)
        self.assertIsNone(pb)

    def test_personal_best_ignores_incomplete_attempts(self) -> None:
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=60_000,
                break_time_ms=0,
                completed=False,
            )
        )
        pb = compute_exercise_personal_best_ms(self.record, "Guía", 1, 1, None)
        self.assertIsNone(pb)

    def test_personal_best_finds_minimum_completed_time(self) -> None:
        self.record.items.extend(
            [
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=180_000,
                    break_time_ms=0,
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=120_000,
                    break_time_ms=0,
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=90_000,
                    break_time_ms=0,
                    completed=False,  # Más corto pero incompleto
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=2,  # Diferente ejercicio
                    inciso=None,
                    exercise_time_ms=45_000,
                    break_time_ms=0,
                    completed=True,
                ),
            ]
        )
        pb = compute_exercise_personal_best_ms(self.record, "Guía", 1, 1, None)
        self.assertEqual(pb, 120_000)

    def test_personal_best_respects_incisos(self) -> None:
        self.record.items.extend(
            [
                TimerItem(
                    section_type="Guía",
                    section_number=2,
                    exercise=3,
                    inciso=1,
                    exercise_time_ms=100_000,
                    break_time_ms=0,
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=2,
                    exercise=3,
                    inciso=2,
                    exercise_time_ms=50_000,
                    break_time_ms=0,
                    completed=True,
                ),
            ]
        )
        pb_inciso_1 = compute_exercise_personal_best_ms(self.record, "Guía", 2, 3, 1)
        pb_inciso_2 = compute_exercise_personal_best_ms(self.record, "Guía", 2, 3, 2)
        pb_without_inciso = compute_exercise_personal_best_ms(self.record, "Guía", 2, 3, None)

        self.assertEqual(pb_inciso_1, 100_000)
        self.assertEqual(pb_inciso_2, 50_000)
        self.assertIsNone(pb_without_inciso)

    def test_today_summary_metrics(self) -> None:
        target_date = date(2026, 9, 20)

        self.record.items.extend(
            [
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=60_000,
                    break_time_ms=10_000,
                    created_at="2026-09-20T10:00:00",
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,  # Mismo ejercicio repetido
                    inciso=None,
                    exercise_time_ms=40_000,
                    break_time_ms=5_000,
                    created_at="2026-09-20T11:00:00",
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=2,  # Segundo ejercicio distinto
                    inciso=None,
                    exercise_time_ms=30_000,
                    break_time_ms=0,
                    created_at="2026-09-20T12:00:00",
                    completed=False,  # Incompleto
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=3,
                    inciso=None,
                    exercise_time_ms=50_000,
                    break_time_ms=0,
                    created_at="2026-09-19T10:00:00",  # Día anterior
                    completed=True,
                ),
            ]
        )

        metrics = compute_today_summary_metrics(self.record, reference_date=target_date)

        self.assertEqual(metrics["study_time_ms"], 130_000)  # 60k + 40k + 30k
        self.assertEqual(metrics["break_time_ms"], 15_000)   # 10k + 5k
        self.assertEqual(metrics["total_attempts"], 3)
        self.assertEqual(metrics["completed_unique_count"], 1)  # Solo Ejercicio 1 completado

    def test_today_timeline_buckets_structure_and_intensities(self) -> None:
        target_date = date(2026, 9, 20)
        self.record.items.extend(
            [
                # Hora 9: 10 min (Nivel 1: 1..15 min)
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=10 * 60 * 1000,
                    break_time_ms=0,
                    created_at="2026-09-20T09:15:00",
                    completed=True,
                ),
                # Hora 14: 25 min (Nivel 2: 16..30 min) en 2 intentos
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=2,
                    inciso=None,
                    exercise_time_ms=15 * 60 * 1000,
                    break_time_ms=0,
                    created_at="2026-09-20T14:10:00",
                    completed=True,
                ),
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=3,
                    inciso=None,
                    exercise_time_ms=10 * 60 * 1000,
                    break_time_ms=0,
                    created_at="2026-09-20T14:35:00",
                    completed=True,
                ),
                # Hora 16: 50 min (Nivel 4: >45 min)
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=4,
                    inciso=None,
                    exercise_time_ms=50 * 60 * 1000,
                    break_time_ms=0,
                    created_at="2026-09-20T16:05:00",
                    completed=True,
                ),
            ]
        )

        buckets = compute_today_timeline_buckets(self.record, reference_date=target_date)

        self.assertEqual(len(buckets), 24)
        self.assertEqual(buckets[0]["intensity_level"], 0)
        self.assertEqual(buckets[0]["attempts_count"], 0)

        # Hora 9
        self.assertEqual(buckets[9]["intensity_level"], 1)
        self.assertEqual(buckets[9]["attempts_count"], 1)
        self.assertEqual(buckets[9]["exercise_time_ms"], 10 * 60 * 1000)

        # Hora 14
        self.assertEqual(buckets[14]["intensity_level"], 2)
        self.assertEqual(buckets[14]["attempts_count"], 2)
        self.assertEqual(buckets[14]["exercise_time_ms"], 25 * 60 * 1000)

        # Hora 16
        self.assertEqual(buckets[16]["intensity_level"], 4)
        self.assertEqual(buckets[16]["attempts_count"], 1)


class TestApplicationServiceHomeFacade(unittest.TestCase):
    """Verifica que StudyApplicationService delegue correctamente en las funciones de analítica."""

    def test_facade_methods_with_open_and_closed_record(self) -> None:
        service = StudyApplicationService()
        # Con registro abierto automático
        pb = service.get_exercise_personal_best_ms("Guía", 1, 1, None)
        self.assertIsNone(pb)

        timeline = service.get_today_timeline_buckets()
        self.assertEqual(len(timeline), 24)

        metrics = service.get_today_summary_metrics()
        self.assertEqual(metrics["study_time_ms"], 0)
        self.assertEqual(metrics["total_attempts"], 0)

        # Cerrar registro
        service.close_record()
        self.assertIsNone(service.get_exercise_personal_best_ms("Guía", 1, 1, None))
        self.assertEqual(len(service.get_today_timeline_buckets()), 24)
        self.assertEqual(service.get_today_summary_metrics()["total_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
