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
