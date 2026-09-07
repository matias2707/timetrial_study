"""Pruebas unitarias para el servicio de estadísticas sin interfaz gráfica."""

from datetime import date
import unittest

from application.statistics_service import compute_statistics, format_exercise_label
from domain.models import Record, TimerItem


class StatisticsServiceTests(unittest.TestCase):
    def test_empty_record_returns_zeroed_metrics_and_seven_days(self) -> None:
        record = Record(record_name="Vacio", items=[])
        ref_date = date(2026, 9, 7)
        stats = compute_statistics(record, reference_date=ref_date)

        self.assertEqual(stats.record_name, "Vacio")
        self.assertEqual(stats.total_exercise_time_ms, 0)
        self.assertEqual(stats.total_break_time_ms, 0)
        self.assertEqual(stats.avg_exercise_time_ms, 0)
        self.assertEqual(stats.avg_break_time_ms, 0)
        self.assertEqual(stats.longest_exercise_time_ms, 0)
        self.assertEqual(stats.longest_exercise_name, "Ninguno")
        self.assertEqual(stats.total_unique_exercises, 0)
        self.assertEqual(stats.completed_unique_exercises, 0)
        self.assertEqual(stats.completion_percentage, 0.0)
        self.assertEqual(stats.total_attempts, 0)
        self.assertEqual(len(stats.daily_stats), 7)
        self.assertEqual(stats.daily_stats[-1].date, ref_date)
        self.assertEqual(stats.daily_stats[-1].exercise_time_ms, 0)

    def test_statistics_with_multiple_items_and_duplicate_exercises(self) -> None:
        items = [
            # Ejercicio 1 hecho 2 veces: primero incompleto, luego completo
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=60_000,
                break_time_ms=10_000,
                completed=False,
                created_at="2026-09-06T10:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=120_000,
                break_time_ms=20_000,
                completed=True,
                created_at="2026-09-07T11:00:00",
            ),
            # Ejercicio 2 hecho 1 vez: incompleto
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=1,
                exercise_time_ms=300_000,  # Este es el más largo: 5 min
                break_time_ms=30_000,
                completed=False,
                created_at="2026-09-07T12:00:00",
            ),
            # Ejercicio en otra sección: completo
            TimerItem(
                section_type="Parcial",
                section_number=2,
                exercise=5,
                inciso=None,
                exercise_time_ms=180_000,
                break_time_ms=0,
                completed=True,
                created_at="2026-09-05T09:00:00",
            ),
        ]
        record = Record(record_name="Prueba", items=items)
        ref_date = date(2026, 9, 7)
        stats = compute_statistics(record, reference_date=ref_date)

        # Totales
        self.assertEqual(stats.total_exercise_time_ms, 660_000)
        self.assertEqual(stats.total_break_time_ms, 60_000)
        self.assertEqual(stats.total_time_ms, 720_000)
        self.assertEqual(stats.total_attempts, 4)
        self.assertEqual(stats.completed_attempts, 2)

        # Promedios
        self.assertEqual(stats.avg_exercise_time_ms, 660_000 // 4)
        self.assertEqual(stats.avg_break_time_ms, 60_000 // 4)

        # Ejercicio más largo
        self.assertEqual(stats.longest_exercise_time_ms, 300_000)
        self.assertEqual(stats.longest_exercise_name, "Guía 1 · Ejercicio 2 · Inciso 1")

        # Ejercicios únicos y completados (Total únicos: 3 -> Guía 1 Ex 1, Guía 1 Ex 2 Inc 1, Parcial 2 Ex 5)
        # Completados únicos: 2 (Guía 1 Ex 1 y Parcial 2 Ex 5)
        self.assertEqual(stats.total_unique_exercises, 3)
        self.assertEqual(stats.completed_unique_exercises, 2)
        self.assertAlmostEqual(stats.completion_percentage, (2 / 3) * 100.0)

        # Ventana semanal de 7 días (del 01/09 al 07/09)
        self.assertEqual(len(stats.daily_stats), 7)
        self.assertEqual(stats.daily_stats[-1].date, date(2026, 9, 7))
        # 07/09: 120_000 + 300_000 = 420_000
        self.assertEqual(stats.daily_stats[-1].exercise_time_ms, 420_000)
        # 06/09: 60_000
        self.assertEqual(stats.daily_stats[-2].exercise_time_ms, 60_000)
        # 05/09: 180_000
        self.assertEqual(stats.daily_stats[-3].exercise_time_ms, 180_000)
        # 04/09: 0
        self.assertEqual(stats.daily_stats[-4].exercise_time_ms, 0)

        # Secciones
        self.assertEqual(len(stats.section_summaries), 2)
        guia_sec = next(s for s in stats.section_summaries if s.section_key == "Guía 1")
        self.assertEqual(guia_sec.attempts, 3)
        self.assertEqual(guia_sec.total_unique, 2)
        self.assertEqual(guia_sec.completed_unique, 1)

    def test_format_exercise_label(self) -> None:
        self.assertEqual(format_exercise_label("Guía", 1, 3), "Guía 1 · Ejercicio 3")
        self.assertEqual(format_exercise_label("Práctico", 2, 4, 1), "Práctico 2 · Ejercicio 4 · Inciso 1")

    def test_compute_today_study_time_ms(self) -> None:
        from application.statistics_service import compute_today_study_time_ms

        items = [
            TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=60_000, break_time_ms=0, completed=True, created_at="2026-09-06T10:00:00"),
            TimerItem(section_type="Guía", section_number=1, exercise=2, inciso=None, exercise_time_ms=120_000, break_time_ms=0, completed=True, created_at="2026-09-07T11:00:00"),
            TimerItem(section_type="Guía", section_number=1, exercise=3, inciso=None, exercise_time_ms=180_000, break_time_ms=0, completed=True, created_at="2026-09-07T12:00:00"),
        ]
        record = Record(record_name="Test", items=items)
        # For 2026-09-07: 120_000 + 180_000 = 300_000 ms
        self.assertEqual(compute_today_study_time_ms(record, reference_date=date(2026, 9, 7)), 300_000)
        # For 2026-09-06: 60_000 ms
        self.assertEqual(compute_today_study_time_ms(record, reference_date=date(2026, 9, 6)), 60_000)
        # For another day: 0 ms
        self.assertEqual(compute_today_study_time_ms(record, reference_date=date(2026, 9, 5)), 0)


if __name__ == "__main__":
    unittest.main()
