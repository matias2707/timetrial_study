"""Pruebas unitarias para HomePresenter en aislamiento (Mock View, sin Qt)."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from application.application_service import StudyApplicationService
from domain.timer_service import TimerMode
from infrastructure.storage_service import StorageService
from presentation.home.home_presenter import HomePresenter
from presentation.home.interfaces import IHomeView


class MockHomeView:
    """Implementación en memoria de IHomeView para pruebas ultra-rápidas."""

    def __init__(self) -> None:
        self.clock_display = ("", "")
        self.session_state = ("", False, False)
        self.personal_best = ""
        self.daily_kpis = ("", 0, 0)
        self.location_inputs = ("", 1, 1, None)
        self.controls_locked = False
        self.status_message = ""
        self.empty_state = False

    def update_clock_display(self, exercise_formatted: str, break_formatted: str) -> None:
        self.clock_display = (exercise_formatted, break_formatted)

    def update_session_state(self, mode: str, is_paused: bool, is_editing: bool) -> None:
        self.session_state = (mode, is_paused, is_editing)

    def update_personal_best(self, pb_text: str) -> None:
        self.personal_best = pb_text

    def update_daily_kpis(self, study_time: str, completed_count: int, attempts_count: int) -> None:
        self.daily_kpis = (study_time, completed_count, attempts_count)

    def set_location_inputs(self, section_type: str, section_number: int, exercise: int, inciso: int | None) -> None:
        self.location_inputs = (section_type, section_number, exercise, inciso)

    def set_controls_locked(self, locked: bool) -> None:
        self.controls_locked = locked

    def set_status_message(self, message: str) -> None:
        self.status_message = message

    def set_empty_state(self, is_empty: bool) -> None:
        self.empty_state = is_empty


class MockAudioService:
    def __init__(self) -> None:
        self.played_start = False
        self.played_complete = False
        self.played_fail = False

    def play_start(self) -> None:
        self.played_start = True

    def play_complete(self) -> None:
        self.played_complete = True

    def play_fail(self) -> None:
        self.played_fail = True


class TestHomePresenter(unittest.TestCase):
    """Verifica la lógica pura del orquestador de Home sin inicializar widgets de Qt."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(default_dir=Path(self.tmp_dir.name))
        self.app_service = StudyApplicationService(storage=self.storage)
        self.view = MockHomeView()
        self.audio = MockAudioService()
        self.presenter = HomePresenter(
            view=self.view,
            application=self.app_service,
            audio_service=self.audio,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_toggle_session_lifecycle(self) -> None:
        # Estado inicial
        self.assertEqual(self.app_service.mode, TimerMode.WAITING)
        self.assertFalse(self.view.controls_locked)

        # Iniciar sesión
        self.presenter.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.PLAY)
        self.assertTrue(self.view.controls_locked)
        self.assertTrue(self.audio.played_start)
        self.assertEqual(self.view.status_message, "En estudio")
        self.assertEqual(self.view.session_state[0], "play")

        # Conmutar a descanso
        self.presenter.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.BREAK)
        self.assertEqual(self.view.status_message, "En receso")
        self.assertEqual(self.view.session_state[0], "break")

        # Conmutar de vuelta a estudio
        self.presenter.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.PLAY)
        self.assertEqual(self.view.status_message, "En estudio")

    def test_finish_attempt_lifecycle(self) -> None:
        self.presenter.toggle_session()
        self.assertTrue(self.view.controls_locked)

        # Finalizar intento como completado
        success = self.presenter.finish_attempt(completed=True, comment="Hecho")
        self.assertTrue(success)
        self.assertEqual(self.app_service.mode, TimerMode.WAITING)
        self.assertFalse(self.view.controls_locked)
        self.assertTrue(self.audio.played_complete)
        self.assertEqual(self.view.status_message, "Listo para comenzar")
        self.assertEqual(len(self.app_service.record.items), 1)
        self.assertEqual(self.app_service.record.items[0].comment, "Hecho")

    def test_finish_attempt_incomplete_lifecycle(self) -> None:
        self.presenter.toggle_session()
        self.assertTrue(self.view.controls_locked)

        # Finalizar intento como incompleto
        success = self.presenter.finish_attempt(completed=False, comment="Incompleto")
        self.assertTrue(success)
        self.assertEqual(self.app_service.mode, TimerMode.WAITING)
        self.assertFalse(self.view.controls_locked)
        self.assertFalse(self.audio.played_complete)
        self.assertTrue(self.audio.played_fail)
        self.assertEqual(self.view.status_message, "Listo para comenzar")
        self.assertEqual(len(self.app_service.record.items), 1)
        self.assertFalse(self.app_service.record.items[0].completed)

    def test_stop_session_discards_attempt(self) -> None:
        self.presenter.toggle_session()
        self.presenter.stop_session()
        self.assertEqual(self.app_service.mode, TimerMode.WAITING)
        self.assertFalse(self.view.controls_locked)
        self.assertEqual(len(self.app_service.record.items), 0)


if __name__ == "__main__":
    unittest.main()
