"""Pruebas unitarias para las funciones de analítica temporal y acumulativa."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta

from application.statistics_service import (
    compute_cumulative_evolution,
    compute_daily_stats_summary,
    compute_streak_days,
    compute_weekly_stats_summary,
    get_top_effort_exercises_advanced,
)
from domain.models import Record, TimerItem


class TestStatisticsTemporal(unittest.TestCase):
    """Pruebas unitarias de cálculo para las tres dimensiones temporales."""

    def test_compute_streak_days_consecutive(self) -> None:
        """Verifica el cálculo de racha cuando hay estudio hoy y en días consecutivos previos."""
        today = date.today()
        d_yesterday = today - timedelta(days=1)
        d_two_days_ago = today - timedelta(days=2)

        rec = Record(record_name="TestStreak")
        rec.items.extend([
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=60_000,
                break_time_ms=0,
                completed=True,
                created_at=today.isoformat(),
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=50_000,
                break_time_ms=0,
                completed=True,
                created_at=d_yesterday.isoformat(),
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=3,
                inciso=None,
                exercise_time_ms=40_000,
                break_time_ms=0,
                completed=True,
                created_at=d_two_days_ago.isoformat(),
            ),
        ])

        streak, total_days = compute_streak_days(rec, reference_date=today)
        self.assertEqual(streak, 3)
        self.assertEqual(total_days, 3)

    def test_compute_streak_days_broken(self) -> None:
        """Verifica que un día sin estudio corte la racha actual."""
        today = date.today()
        d_three_days_ago = today - timedelta(days=3)

        rec = Record(record_name="TestBrokenStreak")
        rec.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=60_000,
                break_time_ms=0,
                completed=True,
                created_at=d_three_days_ago.isoformat(),
            )
        )

        streak, total_days = compute_streak_days(rec, reference_date=today)
        self.assertEqual(streak, 0)
        self.assertEqual(total_days, 1)

    def test_top_effort_exercises_advanced_criteria(self) -> None:
        """Verifica los tres criterios de clasificación: time, retries y pb."""
        rec = Record(record_name="TestTopEffort")
        rec.items.extend([
            # Ej 1: 1 intento de 300s, completado
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=300_000,
                break_time_ms=0,
                completed=True,
            ),
            # Ej 2: 3 intentos de 50s cada uno = 150s total, completado en 50s
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=50_000,
                break_time_ms=0,
                completed=False,
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=50_000,
                break_time_ms=0,
                completed=False,
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=50_000,
                break_time_ms=0,
                completed=True,
            ),
        ])

        # 1. Por tiempo acumulado: Ej 1 (300s) > Ej 2 (150s)
        by_time = get_top_effort_exercises_advanced(rec, criteria="time", limit=2)
        self.assertEqual(by_time[0].exercise, 1)
        self.assertEqual(by_time[1].exercise, 2)

        # 2. Por reintentos: Ej 2 (3 intentos) > Ej 1 (1 intento)
        by_retries = get_top_effort_exercises_advanced(rec, criteria="retries", limit=2)
        self.assertEqual(by_retries[0].exercise, 2)
        self.assertEqual(by_retries[1].exercise, 1)

        # 3. Por mejor marca personal (más rápido): Ej 2 (50s) < Ej 1 (300s)
        by_pb = get_top_effort_exercises_advanced(rec, criteria="pb", limit=2)
        self.assertEqual(by_pb[0].exercise, 2)
        self.assertEqual(by_pb[1].exercise, 1)

    def test_compute_cumulative_evolution(self) -> None:
        """Verifica la construcción de la curva acumulativa."""
        d1 = date(2026, 9, 20)
        d2 = date(2026, 9, 21)

        rec = Record(record_name="TestEvolution")
        rec.items.extend([
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=100_000,
                break_time_ms=0,
                completed=True,
                created_at=f"{d1.isoformat()}T10:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=150_000,
                break_time_ms=0,
                completed=False,
                created_at=f"{d1.isoformat()}T11:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=3,
                inciso=None,
                exercise_time_ms=200_000,
                break_time_ms=0,
                completed=True,
                created_at=f"{d2.isoformat()}T14:00:00",
            ),
        ])

        evol = compute_cumulative_evolution(rec)
        self.assertEqual(len(evol.points), 2)
        self.assertEqual(evol.total_study_time_ms, 450_000)
        self.assertEqual(evol.total_completed, 2)
        self.assertEqual(evol.total_failed, 1)

        # Punto 1 (d1)
        p1 = evol.points[0]
        self.assertEqual(p1.cumulative_exercise_time_ms, 250_000)
        self.assertEqual(p1.cumulative_completed, 1)
        self.assertEqual(p1.cumulative_failed, 1)

        # Punto 2 (d2)
        p2 = evol.points[1]
        self.assertEqual(p2.cumulative_exercise_time_ms, 450_000)
        self.assertEqual(p2.cumulative_completed, 2)
        self.assertEqual(p2.cumulative_failed, 1)

    def test_compute_daily_stats_summary(self) -> None:
        """Verifica el cálculo del resumen diario y la bitácora de intentos."""
        target_d = date(2026, 9, 22)
        rec = Record(record_name="TestDaily")
        rec.items.extend([
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=4,
                inciso=1,
                exercise_time_ms=120_000,
                break_time_ms=30_000,
                completed=True,
                comment="Duda aclarada",
                created_at="2026-09-22T09:15:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=5,
                inciso=None,
                exercise_time_ms=180_000,
                break_time_ms=20_000,
                completed=False,
                comment="Incompleto por tiempo",
                created_at="2026-09-22T10:00:00",
            ),
            # Item de otro día (no debe sumarse)
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=6,
                inciso=None,
                exercise_time_ms=90_000,
                break_time_ms=10_000,
                completed=True,
                created_at="2026-09-23T08:00:00",
            ),
        ])

        summary = compute_daily_stats_summary(rec, target_d)
        self.assertEqual(summary.target_date, "2026-09-22")
        self.assertEqual(summary.total_exercise_time_ms, 300_000)
        self.assertEqual(summary.total_break_time_ms, 50_000)
        self.assertEqual(summary.completed_count, 1)
        self.assertEqual(summary.failed_count, 1)
        self.assertEqual(len(summary.attempts), 2)
        self.assertEqual(summary.attempts[0].notes, "Duda aclarada")
        self.assertEqual(summary.attempts[0].start_time_str, "09:15")
        self.assertAlmostEqual(summary.focus_ratio, (300_000 / 350_000) * 100.0, places=1)

    def test_compute_weekly_stats_summary(self) -> None:
        """Verifica la agregación de una semana completa (Lunes a Domingo)."""
        ref_d = date(2026, 9, 23)  # Miércoles
        rec = Record(record_name="TestWeekly")
        rec.items.extend([
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=60_000,
                break_time_ms=10_000,
                completed=True,
                created_at="2026-09-21T10:00:00",  # Lunes
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=120_000,
                break_time_ms=20_000,
                completed=True,
                created_at="2026-09-23T11:00:00",  # Miércoles
            ),
        ])

        summary = compute_weekly_stats_summary(rec, ref_d)
        self.assertEqual(summary.week_start_str, "2026-09-21")  # Lunes
        self.assertEqual(summary.week_end_str, "2026-09-27")    # Domingo
        self.assertEqual(summary.total_exercise_time_ms, 180_000)
        self.assertEqual(summary.total_break_time_ms, 30_000)
        self.assertEqual(summary.active_days_count, 2)
        self.assertEqual(len(summary.days), 7)
        self.assertEqual(summary.completed_count, 2)
        self.assertEqual(len(summary.exercises), 2)


if __name__ == "__main__":
    unittest.main()
