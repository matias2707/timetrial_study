"""Pruebas unitarias e integración para el mezclador de ambientación sonora (TASK-004)."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["STUDY_TIMETRIAL_TEST"] = "1"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from domain.models import AmbiencePreset, AmbienceStateMix, default_ambient_presets
from domain.timer_service import TimerMode
from infrastructure.ambient_storage import AmbientStorageService
from presentation.ambience_view import AmbienceViewWidget, TrackCardWidget
from presentation.audio_mixer_engine import AudioMixerEngine, MAX_ACTIVE_TRACKS, TrackPlayer
from presentation.main_window import MainWindow
from presentation.theme import THEME_DARK, THEME_LIGHT


class TestAmbientModelsAndStorage(unittest.TestCase):
    """Pruebas para modelos de datos y almacenamiento de presets y pistas."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.presets_file = Path(self.temp_dir) / "ambient_presets.json"
        self.audio_dir = Path(self.temp_dir) / "audio"
        self.audio_dir.mkdir()
        self.storage = AmbientStorageService(presets_path=self.presets_file, audio_dir=self.audio_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_presets(self) -> None:
        presets = default_ambient_presets()
        self.assertGreaterEqual(len(presets), 2)
        p_ids = [p.id for p in presets]
        self.assertIn("preset-default", p_ids)
        self.assertIn("preset-focus", p_ids)

        p = presets[0]
        self.assertEqual(p.master_volume, 0.8)
        self.assertEqual(p.fade_duration_sec, 1.5)
        self.assertIsInstance(p.mixes, AmbienceStateMix)

    def test_preset_serialization_roundtrip(self) -> None:
        preset = AmbiencePreset(
            id="test-1",
            name="Test Mix",
            master_volume=0.75,
            fade_duration_sec=3.5,
            mixes=AmbienceStateMix(
                study={"rain.mp3": 0.5, "noise.mp3": 0.2},
                break_state={"birds.mp3": 0.8},
                main_state={},
            ),
        )
        data = preset.to_dict()
        restored = AmbiencePreset.from_dict(data)
        self.assertEqual(restored.id, "test-1")
        self.assertEqual(restored.name, "Test Mix")
        self.assertAlmostEqual(restored.master_volume, 0.75)
        self.assertAlmostEqual(restored.fade_duration_sec, 3.5)
        self.assertEqual(restored.mixes.study, {"rain.mp3": 0.5, "noise.mp3": 0.2})
        self.assertEqual(restored.mixes.break_state, {"birds.mp3": 0.8})
        self.assertEqual(restored.mixes.main_state, {})

    def test_storage_loads_defaults_when_file_missing(self) -> None:
        presets, active_id = self.storage.load_presets()
        self.assertGreaterEqual(len(presets), 2)
        self.assertEqual(active_id, "preset-default")

    def test_storage_save_and_load(self) -> None:
        custom_presets = [
            AmbiencePreset(
                id="custom-1",
                name="Custom Preset",
                master_volume=0.6,
                fade_duration_sec=1.5,
                mixes=AmbienceStateMix(study={"track1.mp3": 0.4}),
            )
        ]
        self.storage.save_presets(custom_presets, active_preset_id="custom-1")
        self.assertTrue(self.presets_file.exists())

        loaded_presets, active_id = self.storage.load_presets()
        self.assertEqual(len(loaded_presets), 1)
        self.assertEqual(loaded_presets[0].name, "Custom Preset")
        self.assertEqual(active_id, "custom-1")

    def test_scan_audio_tracks_and_title_formatting(self) -> None:
        # Create dummy audio files
        (self.audio_dir / "Air Conditioner Premium.m4a").write_text("dummy")
        (self.audio_dir / "Ruido Marron.mp3").write_text("dummy")
        (self.audio_dir / "white_noise_ocean.wav").write_text("dummy")
        (self.audio_dir / "notes.txt").write_text("ignore me")

        tracks = self.storage.scan_audio_tracks()
        self.assertEqual(len(tracks), 3)

        filenames = [t["filename"] for t in tracks]
        self.assertIn("Air Conditioner Premium.m4a", filenames)
        self.assertIn("Ruido Marron.mp3", filenames)
        self.assertIn("white_noise_ocean.wav", filenames)

        names = [t["name"] for t in tracks]
        self.assertIn("Air Conditioner Premium", names)
        self.assertIn("Ruido Marron", names)
        self.assertIn("white_noise_ocean", names)


class TestAudioMixerEngine(unittest.TestCase):
    """Pruebas para el motor de audio y transiciones."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.presets_file = Path(self.temp_dir) / "ambient_presets.json"
        self.audio_dir = Path(self.temp_dir) / "audio"
        self.audio_dir.mkdir()
        # Crear 3 archivos de prueba
        (self.audio_dir / "t1.mp3").write_text("dummy")
        (self.audio_dir / "t2.mp3").write_text("dummy")
        (self.audio_dir / "t3.mp3").write_text("dummy")

        self.storage = AmbientStorageService(presets_path=self.presets_file, audio_dir=self.audio_dir)
        self.engine = AudioMixerEngine(storage=self.storage)

    def tearDown(self) -> None:
        self.engine.stop_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_master_volume_controls(self) -> None:
        self.engine.set_master_volume(0.5)
        self.assertAlmostEqual(self.engine.master_volume, 0.5)

        # Clamping
        self.engine.set_master_volume(1.5)
        self.assertAlmostEqual(self.engine.master_volume, 1.0)
        self.engine.set_master_volume(-0.5)
        self.assertAlmostEqual(self.engine.master_volume, 0.0)

    def test_fade_duration_clamping(self) -> None:
        self.engine.set_fade_duration(2.5)
        self.assertAlmostEqual(self.engine.fade_duration_sec, 2.5)

        # Clamped between 0.5 and 5.0
        self.engine.set_fade_duration(0.1)
        self.assertAlmostEqual(self.engine.fade_duration_sec, 0.5)
        self.engine.set_fade_duration(10.0)
        self.assertAlmostEqual(self.engine.fade_duration_sec, 5.0)

    def test_independent_fade_in_and_fade_out(self) -> None:
        self.engine.set_fade_in(2.2)
        self.engine.set_fade_out(3.8)
        self.assertAlmostEqual(self.engine.fade_in_sec, 2.2)
        self.assertAlmostEqual(self.engine.fade_out_sec, 3.8)
        self.assertAlmostEqual(self.engine.current_preset.fade_in_sec, 2.2)
        self.assertAlmostEqual(self.engine.current_preset.fade_out_sec, 3.8)

        # Clamping
        self.engine.set_fade_in(0.1)
        self.assertAlmostEqual(self.engine.fade_in_sec, 0.5)
        self.engine.set_fade_in(9.9)
        self.assertAlmostEqual(self.engine.fade_in_sec, 5.0)

        self.engine.set_fade_out(0.1)
        self.assertAlmostEqual(self.engine.fade_out_sec, 0.5)
        self.engine.set_fade_out(9.9)
        self.assertAlmostEqual(self.engine.fade_out_sec, 5.0)

    def test_master_volume_immediate_scaling_and_persistence(self) -> None:
        self.engine.set_track_scene_volume("t1.mp3", "main_state", 0.8, immediate=True)
        player = self.engine.players["t1.mp3"]
        self.assertAlmostEqual(player.current_volume, 0.8)

        # Modifying master scales effective volume immediately
        self.engine.set_master_volume(0.5)
        self.assertAlmostEqual(self.engine.master_volume, 0.5)
        self.assertAlmostEqual(self.engine.current_preset.master_volume, 0.5)
        self.assertAlmostEqual(player.audio_output.volume(), 0.4)

    def test_immediate_slider_response_in_active_scene(self) -> None:
        self.engine.current_scene = "study"
        self.engine.set_track_scene_volume("t2.mp3", "study", 0.65, immediate=True)
        player = self.engine.players["t2.mp3"]
        self.assertAlmostEqual(player.current_volume, 0.65)
        self.assertAlmostEqual(player.target_volume, 0.65)

    def test_rapid_audition_toggling(self) -> None:
        self.engine.set_track_scene_volume("t1.mp3", "study", 0.7, immediate=True)
        player = self.engine.players["t1.mp3"]

        # Toggling audition multiple times
        for _ in range(5):
            self.engine.start_audition("study")
            self.assertTrue(self.engine.is_auditioning)
            self.engine.stop_audition()
            self.assertFalse(self.engine.is_auditioning)

        # Verify final state is silent in main_state
        self.assertEqual(self.engine.current_scene, "main_state")
        self.assertAlmostEqual(player.target_volume, 0.0)

    def test_status_change_throttling(self) -> None:
        player = self.engine.players["t1.mp3"]
        status_emissions = []
        player.status_changed.connect(lambda fn, st: status_emissions.append((fn, st)))

        player.current_volume = 0.5
        # First call when transitioning to audible emits once
        player.apply_current_volume(master_volume=1.0, master_muted=False)
        self.assertEqual(len(status_emissions), 1)
        self.assertEqual(status_emissions[0][1], "playing")

        # Second and third calls with the same state do NOT emit again!
        player.apply_current_volume(master_volume=1.0, master_muted=False)
        player.apply_current_volume(master_volume=1.0, master_muted=False)
        self.assertEqual(len(status_emissions), 1)

        # Transition to silence emits paused once
        player.current_volume = 0.0
        player.apply_current_volume(master_volume=1.0, master_muted=False)
        self.assertEqual(len(status_emissions), 2)
        self.assertEqual(status_emissions[1][1], "paused")

        # Further silent ticks do not re-emit
        player.apply_current_volume(master_volume=1.0, master_muted=False)
        self.assertEqual(len(status_emissions), 2)

    def test_set_track_scene_volume(self) -> None:
        self.engine.set_track_scene_volume("t1.mp3", "study", 0.7)
        self.assertAlmostEqual(self.engine.get_track_scene_volume("t1.mp3", "study"), 0.7)

        # Track volume 0 removes it from mix dict
        self.engine.set_track_scene_volume("t1.mp3", "study", 0.0)
        self.assertAlmostEqual(self.engine.get_track_scene_volume("t1.mp3", "study"), 0.0)

    def test_max_active_tracks_limit(self) -> None:
        # Pre-fill with MAX_ACTIVE_TRACKS tracks
        for i in range(MAX_ACTIVE_TRACKS):
            fn = f"mock_{i}.mp3"
            self.engine.current_preset.mixes.study[fn] = 0.5

        # Attempt to add another track
        self.engine.set_track_scene_volume("overflow.mp3", "study", 0.6)
        # Should not be added because it exceeds limit
        self.assertNotIn("overflow.mp3", self.engine.current_preset.mixes.study)

    def test_timer_mode_transitions(self) -> None:
        # PLAY -> "study"
        self.engine.on_timer_mode_changed(TimerMode.PLAY, is_paused=False)
        self.assertEqual(self.engine.current_scene, "study")

        # BREAK -> "break_state"
        self.engine.on_timer_mode_changed(TimerMode.BREAK, is_paused=False)
        self.assertEqual(self.engine.current_scene, "break_state")

        # WAITING -> "main_state"
        self.engine.on_timer_mode_changed(TimerMode.WAITING, is_paused=False)
        self.assertEqual(self.engine.current_scene, "main_state")

        # PLAY but is_paused=True -> "main_state"
        self.engine.on_timer_mode_changed(TimerMode.PLAY, is_paused=True)
        self.assertEqual(self.engine.current_scene, "main_state")

    def test_audition_mode(self) -> None:
        self.engine.current_scene = "study"
        self.engine.start_audition("break_state")
        self.assertTrue(self.engine.is_auditioning)
        self.assertEqual(self.engine.audition_scene, "break_state")
        self.assertEqual(self.engine.active_scene_name, "break_state")

        self.engine.stop_audition()
        self.assertFalse(self.engine.is_auditioning)
        self.assertEqual(self.engine.active_scene_name, "study")

    def test_preset_creation_and_deletion(self) -> None:
        initial_count = len(self.engine.presets)
        new_p = self.engine.create_preset("Mi Nuevo Preset")
        self.assertEqual(len(self.engine.presets), initial_count + 1)
        self.assertEqual(self.engine.active_preset_id, new_p.id)

        # Deleting newly created preset
        deleted = self.engine.delete_preset(new_p.id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.engine.presets), initial_count)

        # Cannot delete if only 1 preset exists
        while len(self.engine.presets) > 1:
            self.engine.delete_preset(self.engine.presets[-1].id)
        self.assertEqual(len(self.engine.presets), 1)
        can_delete_last = self.engine.delete_preset(self.engine.presets[0].id)
        self.assertFalse(can_delete_last)


class TestAmbienceViewWidget(unittest.TestCase):
    """Pruebas para el componente visual AmbienceViewWidget y TrackCardWidget."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.presets_file = Path(self.temp_dir) / "ambient_presets.json"
        self.audio_dir = Path(self.temp_dir) / "audio"
        self.audio_dir.mkdir()
        (self.audio_dir / "ambient_rain.mp3").write_text("dummy")

        self.storage = AmbientStorageService(presets_path=self.presets_file, audio_dir=self.audio_dir)
        self.engine = AudioMixerEngine(storage=self.storage)
        self.widget = AmbienceViewWidget(engine=self.engine, is_dark_mode=True)

    def tearDown(self) -> None:
        self.widget.engine.stop_all()
        self.widget.deleteLater()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ui_components_initialized(self) -> None:
        self.assertIsNotNone(self.widget.master_slider)
        self.assertIsNotNone(self.widget.master_mute_btn)
        self.assertIsNotNone(self.widget.preset_combo)
        self.assertIsNotNone(self.widget.btn_scene_study)
        self.assertIsNotNone(self.widget.btn_scene_break)
        self.assertIsNotNone(self.widget.btn_scene_main)
        self.assertIsNotNone(self.widget.btn_audition)

        self.assertIn("ambient_rain.mp3", self.widget.cards)

    def test_scene_button_selection(self) -> None:
        self.widget._select_scene("break_state")
        self.assertEqual(self.widget.selected_scene, "break_state")
        self.assertTrue(self.widget.btn_scene_break.isChecked())
        self.assertFalse(self.widget.btn_scene_study.isChecked())

    def test_audition_toggle_button(self) -> None:
        self.widget.btn_audition.setChecked(True)
        self.widget._toggle_audition()
        self.assertTrue(self.widget.engine.is_auditioning)

        self.widget.btn_audition.setChecked(False)
        self.widget._toggle_audition()
        self.assertFalse(self.widget.engine.is_auditioning)

    def test_master_mute_toggle_button(self) -> None:
        self.assertFalse(self.widget.engine.is_master_muted)
        self.widget._toggle_master_mute()
        self.assertTrue(self.widget.engine.is_master_muted)
        self.widget._toggle_master_mute()
        self.assertFalse(self.widget.engine.is_master_muted)

    def test_dark_mode_propagation(self) -> None:
        self.widget.set_dark_mode(False)
        self.assertFalse(self.widget.is_dark)
        for card in self.widget.cards.values():
            self.assertFalse(card.is_dark)

        self.widget.set_dark_mode(True)
        self.assertTrue(self.widget.is_dark)
        for card in self.widget.cards.values():
            self.assertTrue(card.is_dark)

    def test_fade_sliders_and_sync_ui_state(self) -> None:
        self.assertIsNotNone(self.widget.fade_in_slider)
        self.assertIsNotNone(self.widget.fade_out_slider)

        # Move sliders
        self.widget.fade_in_slider.setValue(25)  # 2.5s
        self.assertAlmostEqual(self.engine.fade_in_sec, 2.5)
        self.assertEqual(self.widget.fade_in_val_lbl.text(), "2.5s")

        self.widget.fade_out_slider.setValue(35)  # 3.5s
        self.assertAlmostEqual(self.engine.fade_out_sec, 3.5)
        self.assertEqual(self.widget.fade_out_val_lbl.text(), "3.5s")

        # Programmatic engine changes reflect via sync_ui_state
        self.engine.set_master_volume(0.42)
        self.engine.set_fade_in(1.8)
        self.engine.set_fade_out(2.8)
        self.widget.sync_ui_state()

        self.assertEqual(self.widget.master_slider.value(), 42)
        self.assertEqual(self.widget.master_vol_val.text(), "42%")
        self.assertEqual(self.widget.fade_in_slider.value(), 18)
        self.assertEqual(self.widget.fade_out_slider.value(), 28)

    def test_track_card_immediate_volume_in_active_scene(self) -> None:
        # Active scene is main_state by default
        self.widget._select_scene("main_state")
        card = self.widget.cards["ambient_rain.mp3"]
        # Trigger slider change on card
        card.slider.setValue(75)
        self.assertAlmostEqual(self.engine.get_track_scene_volume("ambient_rain.mp3", "main_state"), 0.75)
        player = self.engine.players["ambient_rain.mp3"]
        self.assertAlmostEqual(player.current_volume, 0.75)


class TestMainWindowAmbienceIntegration(unittest.TestCase):
    """Pruebas de integración entre MainWindow y la pestaña de ambientación."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()

    def tearDown(self) -> None:
        self.window.close()

    def test_ambient_tab_in_main_window(self) -> None:
        self.assertEqual(self.window.tabs.count(), 5)
        self.assertIn("Ambientación", self.window.tabs.tabText(4))
        self.assertTrue(hasattr(self.window, "ambience_view"))
        self.assertIsInstance(self.window.ambience_view, AmbienceViewWidget)

    def test_tab_switch_to_ambience(self) -> None:
        self.window.tabs.setCurrentIndex(4)
        self.assertEqual(self.window.tabs.currentIndex(), 4)

    def test_theme_propagation_to_ambience(self) -> None:
        self.window.set_theme(THEME_DARK)
        self.assertTrue(self.window.ambience_view.is_dark)

        self.window.set_theme(THEME_LIGHT)
        self.assertFalse(self.window.ambience_view.is_dark)

    def test_clock_refresh_notifies_ambience_engine(self) -> None:
        # Iniciar sesión de estudio -> modo PLAY
        self.window.application.timer.start()
        self.window.refresh_clock()
        self.assertEqual(self.window.ambience_view.engine.current_scene, "study")

        # Pausar cronómetro -> escena pasa a main_state
        self.window.application.pause_timer()
        self.window.refresh_clock()
        self.assertEqual(self.window.ambience_view.engine.current_scene, "main_state")

        # Reanudar cronómetro -> vuelve a study
        self.window.application.resume_timer()
        self.window.refresh_clock()
        self.assertEqual(self.window.ambience_view.engine.current_scene, "study")

        # Cambiar a receso -> break_state
        self.window.application.timer.toggle_break()
        self.window.refresh_clock()
        self.assertEqual(self.window.ambience_view.engine.current_scene, "break_state")

        # Detener sesión -> main_state
        self.window.application.stop_session()
        self.window.refresh_clock()
        self.assertEqual(self.window.ambience_view.engine.current_scene, "main_state")

    def test_bidirectional_mute_sync(self) -> None:
        # Silenciar desde la ventana principal / toolbar
        self.window.set_sound_muted(True)
        self.assertTrue(self.window.audio_service.is_muted)
        self.assertTrue(self.window.ambience_view.engine.is_master_muted)

        # Reactivar sonido desde el motor de ambientación (ej. botón en la pestaña de audio)
        self.window.ambience_view.engine.set_master_muted(False)
        self.assertFalse(self.window.ambience_view.engine.is_master_muted)
        self.assertFalse(self.window.audio_service.is_muted)
        self.assertFalse(self.window.is_sound_muted)


class TestAudioCrashHardeningAndEdgeCases(unittest.TestCase):
    """Pruebas rigurosas de tolerancia a fallos, datos corruptos y concurrencia."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.presets_file = Path(self.temp_dir) / "ambient_presets.json"
        self.audio_dir = Path(self.temp_dir) / "ambient"
        self.audio_dir.mkdir()
        self.storage = AmbientStorageService(presets_path=self.presets_file, audio_dir=self.audio_dir)
        self.engine = AudioMixerEngine(storage=self.storage)

    def tearDown(self) -> None:
        self.engine.stop_all()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupted_preset_json_recovers_to_defaults(self) -> None:
        # JSON con sintaxis completamente rota
        self.presets_file.write_text("{ broken json: [", encoding="utf-8")
        presets, active_id = self.storage.load_presets()
        self.assertGreaterEqual(len(presets), 2)
        self.assertEqual(active_id, "preset-default")

        # JSON válido pero estructura inválida
        self.presets_file.write_text(json.dumps({"presets": "not-a-list", "active_preset_id": None}), encoding="utf-8")
        presets, active_id = self.storage.load_presets()
        self.assertGreaterEqual(len(presets), 2)

    def test_malformed_preset_fields_from_dict(self) -> None:
        # Presets con datos de tipo incorrecto (strings en vez de floats, None, NaN)
        malformed_dict = {
            "id": "bad-preset",
            "name": "Malformed",
            "master_volume": "not_a_float",
            "fade_duration_sec": None,
            "fade_in_sec": "bad",
            "fade_out_sec": float("nan"),
            "mixes": {
                "study": {"track1.mp3": "invalid_vol", "track2.mp3": 0.5},
                "break_state": "not_a_dict",
                "main_state": None,
            },
        }
        preset = AmbiencePreset.from_dict(malformed_dict)
        self.assertEqual(preset.id, "bad-preset")
        self.assertEqual(preset.master_volume, 0.8)
        self.assertEqual(preset.fade_duration_sec, 1.5)
        self.assertEqual(preset.fade_in_sec, 1.5)
        self.assertEqual(preset.fade_out_sec, 1.5)
        self.assertEqual(preset.mixes.study, {"track2.mp3": 0.5})
        self.assertEqual(preset.mixes.break_state, {})
        self.assertEqual(preset.mixes.main_state, {})

    def test_unreadable_or_missing_audio_dir(self) -> None:
        missing_dir = Path(self.temp_dir) / "does_not_exist"
        custom_storage = AmbientStorageService(presets_path=self.presets_file, audio_dir=missing_dir)
        tracks = custom_storage.scan_audio_tracks()
        self.assertEqual(tracks, [])

    def test_nan_and_inf_inputs_to_engine_setters(self) -> None:
        import math
        # Master volume con NaN / Inf
        self.engine.set_master_volume(float("nan"))
        self.assertFalse(math.isnan(self.engine.master_volume))
        self.assertEqual(self.engine.master_volume, 0.8)

        self.engine.set_master_volume(float("inf"))
        self.assertFalse(math.isinf(self.engine.master_volume))

        # Fade in y Fade out con NaN / Inf
        self.engine.set_fade_in(float("nan"))
        self.assertEqual(self.engine.fade_in_sec, 1.5)

        self.engine.set_fade_out(float("inf"))
        self.assertEqual(self.engine.fade_out_sec, 1.5)

        # Track scene volume con NaN
        ok = self.engine.set_track_scene_volume("any.mp3", "study", float("nan"))
        self.assertTrue(ok)
        vol = self.engine.get_track_scene_volume("any.mp3", "study")
        self.assertEqual(vol, 0.0)

    def test_nonexistent_preset_id_fallback(self) -> None:
        initial_id = self.engine.active_preset_id
        self.engine.select_preset("non-existent-random-id-1234")
        # No crashea y mantiene o asigna un preset válido existente
        self.assertIsNotNone(self.engine.current_preset)
        self.assertEqual(self.engine.active_preset_id, self.engine.presets[0].id)

    def test_rapid_audition_toggling_stress(self) -> None:
        # Estrés de 100 alternancias rápidas sin crasheo
        for i in range(100):
            if i % 2 == 0:
                self.engine.start_audition("study")
            else:
                self.engine.stop_audition()
        self.assertFalse(self.engine.is_auditioning)

    def test_fade_tick_handles_concurrent_dictionary_changes(self) -> None:
        # Simular pista en el motor
        test_file = self.audio_dir / "test_ambient.mp3"
        test_file.write_text("dummy")
        self.engine.refresh_tracks()
        self.assertIn("test_ambient.mp3", self.engine.players)

        # Disparar tick y durante el proceso modificar el diccionario players
        self.engine.players["test_ambient.mp3"].target_volume = 0.8
        self.engine._on_fade_tick()

        # Liberar archivo antes de eliminar en Windows
        from PySide6.QtCore import QUrl
        self.engine.players["test_ambient.mp3"].player.setSource(QUrl())
        self.engine.players["test_ambient.mp3"].stop()
        try:
            test_file.unlink()
        except OSError:
            pass
        self.engine.refresh_tracks()
        # El siguiente tick no debe levantar RuntimeError
        self.engine._on_fade_tick()

    def test_track_player_error_state_handling(self) -> None:
        dummy_path = str(self.audio_dir / "nonexistent.mp3")
        from PySide6.QtMultimedia import QMediaPlayer
        player = TrackPlayer("nonexistent.mp3", dummy_path)

        # Simular error de decodificación de Qt
        player._on_player_error(QMediaPlayer.Error.ResourceError, "Corrupt file")
        self.assertEqual(player.error_message, "Error.ResourceError: Corrupt file")
        self.assertFalse(player._is_playing)

        # Al intentar aplicar volumen, no debe intentar reproducir ni crashear
        player.current_volume = 0.5
        player.apply_current_volume(1.0, False)
        self.assertFalse(player._is_playing)
        player.stop()
        self.assertEqual(player.current_volume, 0.0)


if __name__ == "__main__":
    unittest.main()
