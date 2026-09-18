"""Motor multicanal de mezcla de audio para ambientación sonora adaptativa."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from domain.models import AmbiencePreset, AmbienceStateMix
from domain.timer_service import TimerMode
from infrastructure.ambient_storage import AmbientStorageService

MAX_ACTIVE_TRACKS = 8
FPS = 30
TICK_INTERVAL_MS = int(1000 / FPS)


class TrackPlayer(QObject):
    """Encapsula una pista individual con su QMediaPlayer y QAudioOutput."""

    volume_changed = Signal(str, float)
    status_changed = Signal(str, str)  # "playing", "paused", "error", "ready"

    def __init__(self, filename: str, file_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.filename = filename
        self.file_path = file_path
        self.current_volume: float = 0.0
        self.target_volume: float = 0.0
        self.is_muted: bool = False
        self.error_message: str | None = None
        self._is_playing: bool = False
        self._last_emitted_status: str = ""

        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.0)

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setLoops(QMediaPlayer.Infinite)
        self.player.setSource(QUrl.fromLocalFile(file_path))

        self.player.errorOccurred.connect(self._on_player_error)

    def _emit_status(self, status: str) -> None:
        if self._last_emitted_status != status:
            self._last_emitted_status = status
            try:
                self.status_changed.emit(self.filename, status)
            except Exception:
                pass

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.error_message = f"{error}: {error_string}"
        self._is_playing = False
        self._emit_status("error")

    def set_target_volume(self, target: float) -> None:
        try:
            val = float(target)
            import math
            if math.isnan(val) or math.isinf(val):
                val = 0.0
            self.target_volume = max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            self.target_volume = 0.0

    def apply_current_volume(self, master_volume: float, master_muted: bool) -> None:
        try:
            import math
            mv = 0.0 if (math.isnan(master_volume) or math.isinf(master_volume)) else master_volume
            cv = 0.0 if (math.isnan(self.current_volume) or math.isinf(self.current_volume)) else self.current_volume
            effective_vol = 0.0 if (master_muted or self.is_muted) else (cv * mv)
            clamped_effective = max(0.0, min(1.0, float(effective_vol)))

            if clamped_effective <= 0.001:
                self.audio_output.setVolume(0.0)
                if self._is_playing:
                    self.player.pause()
                    self._is_playing = False
                if self.error_message is None:
                    self._emit_status("paused")
            else:
                self.audio_output.setVolume(clamped_effective)
                if self.error_message is None:
                    if not self._is_playing:
                        self.player.play()
                        self._is_playing = True
                    self._emit_status("playing")
                else:
                    self._emit_status("error")

            self.volume_changed.emit(self.filename, self.current_volume)
        except Exception as err:
            self.error_message = str(err)
            self._is_playing = False
            self._emit_status("error")

    def stop(self) -> None:
        self.current_volume = 0.0
        self.target_volume = 0.0
        try:
            self.audio_output.setVolume(0.0)
            if self._is_playing or self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
        except Exception:
            pass
        self._is_playing = False
        if self.error_message is None:
            self._emit_status("paused")
        try:
            self.volume_changed.emit(self.filename, 0.0)
        except Exception:
            pass


class AudioMixerEngine(QObject):
    """Motor multicanal que coordina la biblioteca de pistas y las transiciones suaves."""

    scene_changed = Signal(str)  # "study", "break_state", "main_state"
    master_volume_changed = Signal(float)
    master_muted_changed = Signal(bool)
    fade_duration_changed = Signal(float)  # Retrocompatibilidad
    fade_in_changed = Signal(float)
    fade_out_changed = Signal(float)
    preset_loaded = Signal(str)  # nombre o ID del preset
    track_status_changed = Signal(str, str)
    tracks_refreshed = Signal()

    def __init__(self, storage: AmbientStorageService | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.storage = storage or AmbientStorageService()
        self.presets: list[AmbiencePreset] = []
        self.active_preset_id: str = ""
        self.current_preset: AmbiencePreset | None = None

        self.master_volume: float = 0.8
        self.is_master_muted: bool = False
        self.fade_duration_sec: float = 1.5
        self.fade_in_sec: float = 1.5
        self.fade_out_sec: float = 1.5

        self.current_scene: str = "main_state"
        self.is_auditioning: bool = False
        self.audition_scene: str | None = None

        self.players: dict[str, TrackPlayer] = {}

        # Temporizador para interpolación suave de volumen (30 FPS)
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(TICK_INTERVAL_MS)
        self._fade_timer.timeout.connect(self._on_fade_tick)

        # Cargar datos iniciales
        self.load_presets_and_tracks()

    def load_presets_and_tracks(self) -> None:
        """Inicializa los presets persistidos y la biblioteca de archivos de audio."""
        self.presets, self.active_preset_id = self.storage.load_presets()
        if not self.presets:
            from domain.models import default_ambient_presets
            self.presets = default_ambient_presets()

        for p in self.presets:
            if p.id == self.active_preset_id:
                self.current_preset = p
                break
        if not self.current_preset and self.presets:
            self.current_preset = self.presets[0]
            self.active_preset_id = self.current_preset.id

        if self.current_preset:
            self.master_volume = self.current_preset.master_volume
            self.fade_duration_sec = self.current_preset.fade_duration_sec
            self.fade_in_sec = getattr(self.current_preset, "fade_in_sec", self.fade_duration_sec)
            self.fade_out_sec = getattr(self.current_preset, "fade_out_sec", self.fade_duration_sec)

        self.refresh_tracks()

    def refresh_tracks(self) -> None:
        """Escanea la carpeta data/ambient/ y actualiza el pool de reproductores."""
        try:
            track_info_list = self.storage.scan_audio_tracks()
        except Exception:
            track_info_list = []
        scanned_filenames = {t["filename"] for t in track_info_list}

        # Eliminar reproductores de pistas borradas
        to_remove = [fn for fn in list(self.players.keys()) if fn not in scanned_filenames]
        for fn in to_remove:
            player = self.players.pop(fn, None)
            if player:
                try:
                    player.stop()
                    player.deleteLater()
                except Exception:
                    pass

        # Agregar reproductores nuevos
        for info in track_info_list:
            fn = info["filename"]
            if fn not in self.players:
                try:
                    tp = TrackPlayer(fn, info["path"], self)
                    tp.status_changed.connect(self._forward_track_status)
                    self.players[fn] = tp
                except Exception:
                    pass

        self.tracks_refreshed.emit()

    def _forward_track_status(self, filename: str, status: str) -> None:
        try:
            self.track_status_changed.emit(filename, status)
        except Exception:
            pass

    @property
    def active_scene_name(self) -> str:
        if self.is_auditioning and self.audition_scene:
            return self.audition_scene
        return self.current_scene

    def get_track_scene_volume(self, filename: str, scene: str) -> float:
        """Obtiene el volumen configurado (0.0 a 1.0) para una pista en una escena."""
        if not self.current_preset:
            return 0.0
        mixes = self.current_preset.mixes
        mix_dict = getattr(mixes, scene, {})
        if not isinstance(mix_dict, dict):
            return 0.0
        try:
            return float(mix_dict.get(filename, 0.0))
        except (ValueError, TypeError):
            return 0.0

    def set_track_scene_volume(self, filename: str, scene: str, volume: float, immediate: bool = False) -> bool:
        """Ajusta el volumen configurado para una pista en la escena especificada.

        Devuelve True si el cambio fue aceptado, o False si se rechazó por exceder el límite seguro de pistas activas.
        """
        if not self.current_preset:
            return False
        mixes = self.current_preset.mixes
        mix_dict = getattr(mixes, scene, None)
        if mix_dict is not None and isinstance(mix_dict, dict):
            try:
                val = float(volume)
                import math
                if math.isnan(val) or math.isinf(val):
                    val = 0.0
                vol = max(0.0, min(1.0, val))
            except (ValueError, TypeError):
                vol = 0.0

            if vol > 0.001:
                # Verificar límite de seguridad de 8 pistas activas
                active_count = sum(1 for k, v in mix_dict.items() if v > 0.001 and k != filename)
                if active_count >= MAX_ACTIVE_TRACKS:
                    return False  # No superar el límite de seguridad
                mix_dict[filename] = vol
            else:
                mix_dict.pop(filename, None)

            # Si la escena modificada es la que está sonando actualmente, aplicar volumen
            if scene == self.active_scene_name and filename in self.players:
                tp = self.players[filename]
                tp.set_target_volume(vol)
                if immediate:
                    tp.current_volume = vol
                    tp.apply_current_volume(self.master_volume, self.is_master_muted)
                else:
                    self._start_fade_timer()
            self.save_presets()
            return True
        return False

    def set_master_volume(self, volume: float) -> None:
        try:
            val = float(volume)
            import math
            if math.isnan(val) or math.isinf(val):
                val = 0.8
            self.master_volume = max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            self.master_volume = 0.8

        if self.current_preset:
            self.current_preset.master_volume = self.master_volume
        self.master_volume_changed.emit(self.master_volume)
        # Aplicar inmediatamente a todas las pistas
        for tp in list(self.players.values()):
            tp.apply_current_volume(self.master_volume, self.is_master_muted)
        self.save_presets()

    def set_master_muted(self, muted: bool) -> None:
        self.is_master_muted = bool(muted)
        for tp in list(self.players.values()):
            tp.apply_current_volume(self.master_volume, self.is_master_muted)
        self.master_muted_changed.emit(self.is_master_muted)

    def set_fade_in(self, duration_sec: float) -> None:
        try:
            val = float(duration_sec)
            import math
            if math.isnan(val) or math.isinf(val):
                val = 1.5
            self.fade_in_sec = max(0.5, min(5.0, val))
        except (ValueError, TypeError):
            self.fade_in_sec = 1.5

        if self.current_preset:
            self.current_preset.fade_in_sec = self.fade_in_sec
        self.fade_in_changed.emit(self.fade_in_sec)
        self.save_presets()

    def set_fade_out(self, duration_sec: float) -> None:
        try:
            val = float(duration_sec)
            import math
            if math.isnan(val) or math.isinf(val):
                val = 1.5
            self.fade_out_sec = max(0.5, min(5.0, val))
        except (ValueError, TypeError):
            self.fade_out_sec = 1.5

        if self.current_preset:
            self.current_preset.fade_out_sec = self.fade_out_sec
        self.fade_out_changed.emit(self.fade_out_sec)
        self.save_presets()

    def set_fade_duration(self, duration_sec: float) -> None:
        """Configura simétricamente Fade In y Fade Out (compatibilidad)."""
        try:
            val = float(duration_sec)
            import math
            if math.isnan(val) or math.isinf(val):
                val = 1.5
            clamped = max(0.5, min(5.0, val))
        except (ValueError, TypeError):
            clamped = 1.5

        self.fade_duration_sec = clamped
        if self.current_preset:
            self.current_preset.fade_duration_sec = clamped
        self.fade_duration_changed.emit(clamped)
        self.set_fade_in(clamped)
        self.set_fade_out(clamped)

    def set_track_muted(self, filename: str, muted: bool) -> None:
        if filename in self.players:
            self.players[filename].is_muted = bool(muted)
            self.players[filename].apply_current_volume(self.master_volume, self.is_master_muted)

    def on_timer_mode_changed(self, mode: TimerMode | None, is_paused: bool = False) -> None:
        """Adapta la escena automáticamente ante cambios de estado del cronómetro."""
        try:
            if not is_paused and mode is TimerMode.PLAY:
                target_scene = "study"
            elif not is_paused and mode is TimerMode.BREAK:
                target_scene = "break_state"
            else:
                target_scene = "main_state"

            if target_scene != self.current_scene:
                self.current_scene = target_scene
                self.scene_changed.emit(self.current_scene)
                if not self.is_auditioning:
                    self.apply_scene(self.current_scene)
        except Exception:
            pass

    def apply_scene(self, scene: str, immediate: bool = False) -> None:
        """Aplica la escena configurada ajustando los volúmenes objetivo de cada pista."""
        if not self.current_preset:
            return

        mixes = self.current_preset.mixes
        mix_dict = getattr(mixes, scene, {}) or {}

        for fn, player in list(self.players.items()):
            try:
                target = float(mix_dict.get(fn, 0.0))
            except (ValueError, TypeError):
                target = 0.0
            player.set_target_volume(target)
            if immediate:
                player.current_volume = target
                player.apply_current_volume(self.master_volume, self.is_master_muted)

        if not immediate:
            self._start_fade_timer()

    def start_audition(self, scene: str) -> None:
        """Inicia el modo de audición para preescuchar una escena."""
        if scene not in ("study", "break_state", "main_state"):
            scene = "main_state"
        self.is_auditioning = True
        self.audition_scene = scene
        self.apply_scene(scene)

    def stop_audition(self) -> None:
        """Detiene la audición y regresa a la escena que dicte el cronómetro."""
        self.is_auditioning = False
        self.audition_scene = None
        self.apply_scene(self.current_scene)

    def _start_fade_timer(self) -> None:
        if not self._fade_timer.isActive():
            self._fade_timer.start()

    def _on_fade_tick(self) -> None:
        """Paso de interpolación asimétrico para Fade In y Fade Out."""
        try:
            steps_in = max(1.0, (self.fade_in_sec if self.fade_in_sec > 0 else 1.5) * FPS)
            steps_out = max(1.0, (self.fade_out_sec if self.fade_out_sec > 0 else 1.5) * FPS)
            delta_in = 1.0 / steps_in
            delta_out = 1.0 / steps_out

            all_settled = True
            for player in list(self.players.values()):
                diff = player.target_volume - player.current_volume
                if abs(diff) > 0.001:
                    all_settled = False
                    if diff > 0:
                        player.current_volume = min(player.target_volume, player.current_volume + delta_in)
                    else:
                        player.current_volume = max(player.target_volume, player.current_volume - delta_out)
                else:
                    player.current_volume = player.target_volume

                player.apply_current_volume(self.master_volume, self.is_master_muted)

            if all_settled:
                self._fade_timer.stop()
        except Exception:
            pass

    def select_preset(self, preset_id: str) -> None:
        """Cambia el preset activo y actualiza los volúmenes en tiempo real."""
        found = False
        for p in self.presets:
            if p.id == preset_id:
                self.current_preset = p
                self.active_preset_id = p.id
                found = True
                break
        if not found and self.presets:
            self.current_preset = self.presets[0]
            self.active_preset_id = self.current_preset.id

        if self.current_preset:
            self.master_volume = self.current_preset.master_volume
            self.fade_duration_sec = self.current_preset.fade_duration_sec
            self.fade_in_sec = getattr(self.current_preset, "fade_in_sec", self.fade_duration_sec)
            self.fade_out_sec = getattr(self.current_preset, "fade_out_sec", self.fade_duration_sec)
            self.preset_loaded.emit(self.current_preset.name)
            self.apply_scene(self.active_scene_name)
            self.save_presets()

    def save_current_preset(self) -> None:
        """Guarda en disco los cambios realizados en el preset activo."""
        self.save_presets()

    def create_preset(self, name: str) -> AmbiencePreset:
        """Crea un nuevo preset duplicando la mezcla actual y lo activa."""
        import uuid
        new_mixes = AmbienceStateMix(
            study=dict(self.current_preset.mixes.study) if self.current_preset else {},
            break_state=dict(self.current_preset.mixes.break_state) if self.current_preset else {},
            main_state=dict(self.current_preset.mixes.main_state) if self.current_preset else {},
        )
        new_preset = AmbiencePreset(
            id=f"preset-{uuid.uuid4().hex[:8]}",
            name=(name or "").strip() or "Nuevo Preset",
            master_volume=self.master_volume,
            fade_duration_sec=self.fade_duration_sec,
            fade_in_sec=self.fade_in_sec,
            fade_out_sec=self.fade_out_sec,
            mixes=new_mixes,
        )
        self.presets.append(new_preset)
        self.select_preset(new_preset.id)
        return new_preset

    def delete_preset(self, preset_id: str) -> bool:
        """Elimina un preset si no es el único restante."""
        if len(self.presets) <= 1:
            return False
        self.presets = [p for p in self.presets if p.id != preset_id]
        if not self.presets:
            from domain.models import default_ambient_presets
            self.presets = default_ambient_presets()
        if self.active_preset_id == preset_id:
            self.select_preset(self.presets[0].id)
        else:
            self.save_presets()
        return True

    def save_presets(self) -> None:
        """Persiste todos los presets en disco."""
        try:
            self.storage.save_presets(self.presets, self.active_preset_id)
        except Exception:
            pass

    def stop_all(self) -> None:
        """Detiene de inmediato toda la reproducción (ej. al salir de la aplicación)."""
        try:
            self._fade_timer.stop()
        except Exception:
            pass
        for player in list(self.players.values()):
            try:
                player.stop()
                player.player.stop()
            except Exception:
                pass
