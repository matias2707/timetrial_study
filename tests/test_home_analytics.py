"""Pruebas unitarias para las analíticas del Home (TASK-014).

Cálculo de récord personal (Personal Best), métricas de resumen de hoy y buckets de 24 horas.
"""

from __future__ import annotations

from datetime import date, datetime
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

    def test_today_timeline_buckets_splits_exercise_longer_than_one_hour(self) -> None:
        """Verifica que un ejercicio de 1h20m (80 min) se distribuya correctamente entre las horas que abarca."""
        target_date = date(2026, 9, 20)
        # Ejercicio de 1h20m iniciado a las 14:10 -> abarca 14:10 a 15:30
        # Hora 14 (14:10 a 15:00): 50 min
        # Hora 15 (15:00 a 15:30): 30 min
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=80 * 60 * 1000,
                break_time_ms=0,
                created_at="2026-09-20T14:10:00",
                completed=True,
            )
        )

        buckets = compute_today_timeline_buckets(self.record, reference_date=target_date)

        # Ninguna celda puede exceder 60 min (3.600.000 ms)
        for b in buckets:
            self.assertLessEqual(b["exercise_time_ms"], 3_600_000)

        # Hora 14: exactamente 50 min
        self.assertEqual(buckets[14]["exercise_time_ms"], 50 * 60 * 1000)
        self.assertEqual(buckets[14]["intensity_level"], 4)  # > 45 min
        self.assertEqual(buckets[14]["attempts_count"], 1)

        # Hora 15: exactamente 30 min
        self.assertEqual(buckets[15]["exercise_time_ms"], 30 * 60 * 1000)
        self.assertEqual(buckets[15]["intensity_level"], 2)  # 16..30 min
        self.assertEqual(buckets[15]["attempts_count"], 1)

        # Total agregado entre ambas horas debe ser 80 min
        total_bucket_ms = buckets[14]["exercise_time_ms"] + buckets[15]["exercise_time_ms"]
        self.assertEqual(total_bucket_ms, 80 * 60 * 1000)

    def test_today_timeline_buckets_exercise_spanning_multiple_hours(self) -> None:
        """Verifica que un ejercicio de 2h30m (150 min) no exceda 60 min por hora."""
        target_date = date(2026, 9, 20)
        # Inicio a las 10:00 -> 10:00 a 12:30 (150 min)
        # Hora 10: 60 min
        # Hora 11: 60 min
        # Hora 12: 30 min
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=150 * 60 * 1000,
                break_time_ms=0,
                created_at="2026-09-20T10:00:00",
                completed=True,
            )
        )

        buckets = compute_today_timeline_buckets(self.record, reference_date=target_date)

        self.assertEqual(buckets[10]["exercise_time_ms"], 60 * 60 * 1000)
        self.assertEqual(buckets[11]["exercise_time_ms"], 60 * 60 * 1000)
        self.assertEqual(buckets[12]["exercise_time_ms"], 30 * 60 * 1000)

        for b in buckets:
            self.assertLessEqual(b["exercise_time_ms"], 3_600_000)

    def test_today_timeline_buckets_exercise_with_breaks_proportional_slicing(self) -> None:
        """Verifica distribución proporcional del tiempo neto cuando existen descansos."""
        target_date = date(2026, 9, 20)
        # 80 min estudio + 40 min receso = 120 min total (2 horas reloj completas de 14:00 a 16:00)
        # Ratio = 80/120 = 2/3
        # Hora 14 (60 min reloj): 40 min estudio
        # Hora 15 (60 min reloj): 40 min estudio
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=80 * 60 * 1000,
                break_time_ms=40 * 60 * 1000,
                created_at="2026-09-20T14:00:00",
                completed=True,
            )
        )

        buckets = compute_today_timeline_buckets(self.record, reference_date=target_date)
        self.assertEqual(buckets[14]["exercise_time_ms"], 40 * 60 * 1000)
        self.assertEqual(buckets[15]["exercise_time_ms"], 40 * 60 * 1000)
        self.assertEqual(buckets[14]["exercise_time_ms"] + buckets[15]["exercise_time_ms"], 80 * 60 * 1000)

    def test_today_timeline_buckets_exercise_crossing_midnight(self) -> None:
        """Verifica que un ejercicio que cruza la medianoche asigne el tiempo correspondiente a cada día."""
        d1 = date(2026, 9, 20)
        d2 = date(2026, 9, 21)
        # Inicio 23:20 del día 20, duración 80 min -> finaliza a las 00:40 del día 21
        # Día 20, Hora 23 (23:20 a 24:00): 40 min
        # Día 21, Hora 00 (00:00 a 00:40): 40 min
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=80 * 60 * 1000,
                break_time_ms=0,
                created_at="2026-09-20T23:20:00",
                completed=True,
            )
        )

        buckets_d1 = compute_today_timeline_buckets(self.record, reference_date=d1)
        self.assertEqual(buckets_d1[23]["exercise_time_ms"], 40 * 60 * 1000)

        buckets_d2 = compute_today_timeline_buckets(self.record, reference_date=d2)
        self.assertEqual(buckets_d2[0]["exercise_time_ms"], 40 * 60 * 1000)

    def test_today_timeline_buckets_completion_stamped_item_and_current_hour_elapsed_cap(self) -> None:
        """Verifica que un intento guardado al finalizar (retroactivo) no supere los minutos transcurridos."""
        now = datetime.now()
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=58 * 60 * 1000,
                break_time_ms=0,
                created_at=now.isoformat(timespec="seconds"),
                completed=True,
            )
        )

        buckets = compute_today_timeline_buckets(self.record, reference_date=now.date())

        current_bucket = buckets[now.hour]
        # El tiempo de la hora actual NUNCA puede superar los minutos transcurridos en esta hora
        minutes_in_current_hour = now.minute + now.second / 60.0
        max_possible_ms = int(minutes_in_current_hour * 60 * 1000) + 1000
        self.assertLessEqual(current_bucket["exercise_time_ms"], max_possible_ms)
        self.assertLessEqual(current_bucket["exercise_time_ms"], 3_600_000)

        # Las horas futuras deben ser estrictamente 0
        for h in range(now.hour + 1, 24):
            self.assertEqual(buckets[h]["exercise_time_ms"], 0)

    def test_today_timeline_buckets_historical_completion_item_does_not_spill_to_next_day(self) -> None:
        """Verifica que un item completado antes de medianoche no se desborde al día siguiente."""
        # Sesión guardada a las 23:24:57 con duración de 1h33m (inició a las 21:51:35)
        # El archivo fue cerrado y actualizado a las 23:25:22
        self.record.updated_at = "2026-09-25T23:25:22"
        self.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=4,
                exercise=7,
                inciso=None,
                exercise_time_ms=5602539,  # ~1h 33m 22s
                break_time_ms=0,
                created_at="2026-09-25T23:24:57",
                completed=True,
            )
        )

        # En el día siguiente (2026-09-26), la hora 00:00 debe tener CERO actividad y CERO intentos
        buckets_next_day = compute_today_timeline_buckets(self.record, reference_date=date(2026, 9, 26))
        self.assertEqual(buckets_next_day[0]["exercise_time_ms"], 0)
        self.assertEqual(buckets_next_day[0]["attempts_count"], 0)
        self.assertEqual(buckets_next_day[0]["intensity_level"], 0)

        # En el día de estudio (2026-09-25), el tiempo se distribuye en las horas 21, 22 y 23
        buckets_study_day = compute_today_timeline_buckets(self.record, reference_date=date(2026, 9, 25))
        total_study_ms = sum(b["exercise_time_ms"] for b in buckets_study_day)
        self.assertEqual(total_study_ms, 5602539)
        self.assertGreater(buckets_study_day[21]["exercise_time_ms"], 0)
        self.assertGreater(buckets_study_day[22]["exercise_time_ms"], 0)
        self.assertGreater(buckets_study_day[23]["exercise_time_ms"], 0)


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

    def test_session_started_at_recorded_on_finish_item(self) -> None:
        """Verifica que al finalizar un item el created_at corresponda al inicio de la sesión."""
        service = StudyApplicationService()
        service.toggle_session()  # Pasa de WAITING a PLAY
        self.assertIsNotNone(service.session_started_at)
        start_time = service.session_started_at

        # Simular snapshot de tiempo en timer
        service.timer.exercise_time_ms = 60_000
        service.finish_item(completed=True)

        self.assertEqual(len(service.record.items), 1)
        item = service.record.items[0]
        self.assertEqual(item.created_at, start_time.isoformat(timespec="seconds"))
        self.assertIsNone(service.session_started_at)


if __name__ == "__main__":
    unittest.main()
