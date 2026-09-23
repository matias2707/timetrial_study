"""Presenter puro (MVP) para la vista del cronómetro (Home).

Contiene toda la orquestación, reglas de transición y manejo de eventos de usuario
sin depender de ningún componente de PySide6 ni del bucle de eventos de Qt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from domain.timer_service import TimerMode
from presentation.home.interfaces import IHomeView
from presentation.presentation_formatters import format_hh_mm_ss

if TYPE_CHECKING:
    from application.application_service import StudyApplicationService


class HomePresenter:
    """Presenter que orquesta la vista pasiva del cronómetro."""

    def __init__(
        self,
        view: IHomeView,
        application: StudyApplicationService,
        audio_service: Any | None = None,
    ) -> None:
        self.view = view
        self.application = application
        self.audio_service = audio_service

    def on_tick(self) -> None:
        """Invocado por el temporizador periódicamente para refrescar los dígitos."""
        if not self.application.is_record_open:
            return
        exercise_ms, break_ms = self.application.timer.snapshot()
        self.view.update_clock_display(
            format_hh_mm_ss(exercise_ms),
            format_hh_mm_ss(break_ms),
        )

    def toggle_session(self) -> None:
        """Inicia la sesión o conmuta entre Enfoque y Descanso."""
        if not self.application.is_record_open:
            return

        current_mode = self.application.mode
        if current_mode is TimerMode.WAITING:
            if self.audio_service and hasattr(self.audio_service, "play_start"):
                self.audio_service.play_start()
            self.application.toggle_session()
            self.view.set_controls_locked(True)
            self.view.set_status_message("En estudio")
        elif current_mode is TimerMode.PLAY:
            self.application.toggle_session()
            self.view.set_status_message("En receso")
        elif current_mode is TimerMode.BREAK:
            self.application.toggle_session()
            self.view.set_status_message("En estudio")

        self._sync_view_state()

    def stop_session(self) -> None:
        """Detiene el cronómetro y descarta el intento en curso sin persistir."""
        if not self.application.is_record_open:
            return
        self.application.stop_session()
        self.view.set_controls_locked(False)
        self.view.set_status_message("Listo para comenzar")
        self._sync_view_state()
        self.refresh_metrics()

    def finish_attempt(self, completed: bool, comment: str = "") -> bool:
        """Finaliza el intento actual, guardando el registro."""
        if not self.application.is_record_open:
            return False

        if comment:
            self.application.pending_comment = comment

        success = self.application.finish_item(completed=completed)
        if success:
            if completed and self.audio_service and hasattr(self.audio_service, "play_complete"):
                self.audio_service.play_complete()
            elif not completed and self.audio_service and hasattr(self.audio_service, "play_fail"):
                self.audio_service.play_fail()

            self.view.set_controls_locked(False)
            self.view.set_status_message("Listo para comenzar")
            self._sync_view_state()
            self.refresh_metrics()

        return success

    def refresh_metrics(self) -> None:
        """Calcula y refresca las métricas de la jornada y el récord personal."""
        if not self.application.is_record_open:
            self.view.update_daily_kpis("00:00:00", 0, 0)
            self.view.update_personal_best("Sin archivo")
            return

        # KPIs del día
        today_metrics = self.application.get_today_summary_metrics()
        today_study_ms = today_metrics.get("today_study_time_ms", 0)
        completed_count = today_metrics.get("today_completed_count", 0)
        attempts_count = today_metrics.get("today_attempts_count", 0)

        self.view.update_daily_kpis(
            format_hh_mm_ss(today_study_ms),
            completed_count,
            attempts_count,
        )

        # Récord Personal (Personal Best)
        loc = self.application.location
        pb_ms = self.application.get_exercise_personal_best_ms(
            loc.section_type,
            loc.section_number,
            loc.exercise,
            loc.inciso,
        )
        if pb_ms is not None and pb_ms > 0:
            pb_text = f"Récord: {format_hh_mm_ss(pb_ms)}"
        else:
            pb_text = "Primer intento"

        self.view.update_personal_best(pb_text)

    def _sync_view_state(self) -> None:
        mode_str = self.application.mode.value
        is_paused = getattr(self.application, "is_timer_paused", False)
        is_editing = getattr(self.application, "is_editing", False)
        self.view.update_session_state(mode_str, is_paused, is_editing)
