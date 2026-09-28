"""Pruebas unitarias para TimerService y recarga de tiempos acumulados."""

import time
import unittest

from domain.timer_service import TimerMode, TimerService


class TimerServiceTests(unittest.TestCase):
    def test_load_accumulated_times_sets_times_and_waiting_mode(self) -> None:
        timer = TimerService()
        timer.load_accumulated_times(exercise_ms=120000, break_ms=15000)

        self.assertEqual(timer.exercise_time_ms, 120000)
        self.assertEqual(timer.break_time_ms, 15000)
        self.assertEqual(timer.mode, TimerMode.WAITING)
        self.assertFalse(timer.is_paused)
        self.assertTrue(timer.has_accumulated_time)

    def test_has_accumulated_time_property(self) -> None:
        timer = TimerService()
        self.assertFalse(timer.has_accumulated_time)

        timer.exercise_time_ms = 500
        self.assertTrue(timer.has_accumulated_time)

        timer.reset()
        self.assertFalse(timer.has_accumulated_time)

        timer.break_time_ms = 300
        self.assertTrue(timer.has_accumulated_time)

    def test_start_after_load_accumulated_times_increments_exercise_time(self) -> None:
        timer = TimerService()
        timer.load_accumulated_times(exercise_ms=5000, break_ms=1000)
        timer.start()

        self.assertEqual(timer.mode, TimerMode.PLAY)
        time.sleep(0.05)
        ex_ms, br_ms = timer.snapshot()

        self.assertGreaterEqual(ex_ms, 5040)
        self.assertEqual(br_ms, 1000)

    def test_toggle_break_after_load_accumulated_times_increments_break_time(self) -> None:
        timer = TimerService()
        timer.load_accumulated_times(exercise_ms=5000, break_ms=2000)
        timer.start()
        timer.toggle_break()

        self.assertEqual(timer.mode, TimerMode.BREAK)
        time.sleep(0.05)
        ex_ms, br_ms = timer.snapshot()

        self.assertGreaterEqual(br_ms, 2040)
        self.assertGreaterEqual(ex_ms, 5000)

    def test_pause_and_resume_preserves_accumulated_time(self) -> None:
        timer = TimerService()
        timer.start()
        time.sleep(0.04)
        timer.pause()
        self.assertTrue(timer.is_paused)
        ex_paused, _ = timer.snapshot()
        self.assertGreaterEqual(ex_paused, 35)

        # Durante la pausa no debe acumular tiempo
        time.sleep(0.03)
        self.assertEqual(timer.snapshot()[0], ex_paused)

        # Reanudación debe continuar sumando
        timer.resume()
        self.assertFalse(timer.is_paused)
        time.sleep(0.04)
        ex_resumed, _ = timer.snapshot()
        self.assertGreater(ex_resumed, ex_paused)

    def test_zero_clock_drift_over_thousands_of_ticks(self) -> None:
        """Verifica que el anclaje fraccional evita cualquier deriva tras miles de ticks."""
        from unittest.mock import patch

        timer = TimerService()
        current_fake_time = 1000.0

        def fake_perf_counter() -> float:
            return current_fake_time

        with patch("domain.timer_service.time.perf_counter", side_effect=fake_perf_counter):
            timer.start()

            # Simular 10.000 llamadas a _sync con ticks reales irregulares (50.4 ms)
            # En el algoritmo anterior, 0.4 ms x 10.000 = 4.000 ms perdidos (4 segundos de drift)
            for _ in range(10_000):
                current_fake_time += 0.0504
                timer._sync()

            ex_ms, _ = timer.snapshot()

            # Tiempo total real transcurrido: 10.000 * 0.0504 = 504.0 segundos = 504.000 ms
            expected_total_ms = 504_000
            self.assertEqual(ex_ms, expected_total_ms)

    def test_reset_clears_accumulated_times(self) -> None:
        timer = TimerService()
        timer.load_accumulated_times(10000, 5000)
        timer.reset()

        self.assertEqual(timer.exercise_time_ms, 0)
        self.assertEqual(timer.break_time_ms, 0)
        self.assertEqual(timer.mode, TimerMode.WAITING)
        self.assertFalse(timer.has_accumulated_time)


if __name__ == "__main__":
    unittest.main()

