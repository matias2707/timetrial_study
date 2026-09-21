"""Pruebas de integración visual y reactiva para el rediseño del Cronómetro (TASK-014).

Verifica la estructura de dos niveles de la botonera, Récord Personal (PB),
tríada de KPIs diarios, Activity Strip 24h y depuración de títulos redundantes.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from PySide6.QtWidgets import QApplication

from application.application_service import SessionLocation, StudyApplicationService
from domain.models import Record, TimerItem
from domain.timer_service import TimerMode
from infrastructure.storage_service import StorageService
from presentation.audio_service import AudioService
from presentation.home_view import HomeViewWidget
from presentation.today_activity_strip_widget import TodayActivityStripWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestHomeViewRedesign(unittest.TestCase):
    """Verifica todos los componentes y comportamientos introducidos en TASK-014."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(default_dir=Path(self.tmp_dir.name))
        self.app_service = StudyApplicationService(storage=self.storage)
        self.audio_service = AudioService()
        self.home_view = HomeViewWidget(
            application=self.app_service,
            audio_service=self.audio_service,
            is_dark_mode=False,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_activity_strip_widget_structure_and_cells(self) -> None:
        """Verifica la inicialización de las 24 celdas y su actualización con datos."""
        strip = TodayActivityStripWidget(is_dark_mode=False)
        self.assertEqual(len(strip._cells), 24)

        # Celdas vacías inicialmente
        self.assertIn("Sin actividad", strip._cells[0].toolTip())

        # Actualizar con buckets
        sample_buckets = [
            {
                "hour": h,
                "exercise_time_ms": 600_000 if h == 10 else 0,
                "attempts_count": 1 if h == 10 else 0,
                "intensity_level": 1 if h == 10 else 0,
                "is_current_hour": (h == 10),
            }
            for h in range(24)
        ]
        strip.update_buckets(sample_buckets)
        self.assertIn("10:00 – 11:00", strip._cells[10].toolTip())
        self.assertIn("10:00", strip._cells[10].toolTip())

        # Alternar modo oscuro
        strip.is_dark_mode = True
        self.assertTrue(strip.is_dark_mode)

    def test_top_bar_and_daily_kpis(self) -> None:
        """Verifica que no exista el subtítulo redundante y que los 3 KPIs existan y se refresquen."""
        # Título principal de materia
        self.assertIsNotNone(self.home_view.home_title)
        # El texto técnico de subtítulo no debe existir como atributo de clase
        self.assertFalse(hasattr(self.home_view, "record_meta"))

        # Tres micro-tarjetas KPI
        self.assertTrue(hasattr(self.home_view, "kpi_today_study"))
        self.assertTrue(hasattr(self.home_view, "kpi_today_completed"))
        self.assertTrue(hasattr(self.home_view, "kpi_today_attempts"))

        # Simular intentos completados hoy
        self.app_service.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=120_000,
                break_time_ms=30_000,
                completed=True,
            )
        )
        self.home_view.refresh_clock()

        self.assertEqual(self.home_view.today_study_label.text(), "00:02:00")
        self.assertEqual(self.home_view.today_completed_label.text(), "1")
        self.assertEqual(self.home_view.today_attempts_label.text(), "1")

    def test_personal_best_badge_updates_reactively(self) -> None:
        """Verifica que el badge de récord personal responda a cambios de ubicación y guardados."""
        # Inicialmente sin marcas
        self.home_view.sync_location(force=True)
        self.assertIn("Primer intento", self.home_view.personal_best_badge.text())

        # Agregar intento completado para Guía 1 Ejercicio 1
        self.app_service.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=75_000,
                break_time_ms=0,
                completed=True,
            )
        )

        self.home_view.sync_location(force=True)
        self.assertIn("Récord: 00:01:15", self.home_view.personal_best_badge.text())

        # Cambiar a Ejercicio 2 (sin intentos)
        self.home_view.exercise_input.setValue(2)
        self.home_view.sync_location(force=True)
        self.assertIn("Primer intento", self.home_view.personal_best_badge.text())

    def test_two_level_controls_and_hero_break_button(self) -> None:
        """Verifica la botonera con Enfoque y Descanso unificados y anchos contenidos (sin pausa)."""
        # Altura hero y secundarias
        self.assertEqual(self.home_view.session_button.height(), 44)
        self.assertEqual(self.home_view.complete_button.height(), 38)
        self.assertEqual(self.home_view.incomplete_button.height(), 38)
        self.assertEqual(self.home_view.stop_button.height(), 38)

        # Anchos contenidos (no excesivamente anchos)
        self.assertLessEqual(self.home_view.session_button.maximumWidth(), 240)
        self.assertLessEqual(self.home_view.complete_button.maximumWidth(), 160)

        # Estado inicial (WAITING)
        self.assertIn("INICIAR", self.home_view.session_button.text())

        # Iniciar sesión (pasa a PLAY / Enfoque)
        self.home_view.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.PLAY)
        self.assertIn("TOMAR DESCANSO", self.home_view.session_button.text())
        self.assertFalse(self.app_service.is_timer_paused)

        # Conmutar descanso (pasa a BREAK / Descanso)
        self.home_view.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.BREAK)
        self.assertIn("CONTINUAR ENFOQUE", self.home_view.session_button.text())
        self.assertFalse(self.app_service.is_timer_paused)

        # Conmutar de vuelta a enfoque (pasa a PLAY)
        self.home_view.toggle_session()
        self.assertEqual(self.app_service.mode, TimerMode.PLAY)
        self.assertIn("TOMAR DESCANSO", self.home_view.session_button.text())

        # Detener
        self.home_view.stop_timer()
        self.assertEqual(self.app_service.mode, TimerMode.WAITING)
        self.assertIn("INICIAR", self.home_view.session_button.text())

    def test_empty_state_toggles_all_redesigned_widgets(self) -> None:
        """Verifica que el estado vacío oculte y muestre el activity strip y el hero card."""
        self.home_view.set_empty_state(True)
        self.assertTrue(self.home_view.activity_strip.isHidden())
        self.assertTrue(self.home_view.hero_card.isHidden())
        self.assertFalse(self.home_view.session_button.isEnabled())
        self.assertFalse(self.home_view.break_button.isEnabled())

        self.home_view.set_empty_state(False)
        self.assertFalse(self.home_view.activity_strip.isHidden())
        self.assertFalse(self.home_view.hero_card.isHidden())
        self.assertTrue(self.home_view.session_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
