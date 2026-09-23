"""Servicio para la gestión y reproducción de efectos de sonido en Study Timetrial."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QUrl, Signal
from PySide6.QtMultimedia import QSoundEffect


class AudioService(QObject):
    """Administra la configuración, silenciamiento y reproducción de sonidos."""

    mute_state_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = QSettings("StudyTimetrial", "Preferences")
        self._sound_muted: bool = self.settings.value("sound_muted", False, type=bool)

        media_dir = Path(__file__).resolve().parent / "media"
        start_wav = media_dir / "universfield-new-notification-040-493469.wav"
        complete_wav = media_dir / "universfield-new-notification-051-494246.wav"
        fail_wav = media_dir / "fail.wav"

        self.start_sound = QSoundEffect(self)
        if start_wav.exists():
            self.start_sound.setSource(QUrl.fromLocalFile(str(start_wav)))
        self.start_sound.setVolume(1.0)
        self.start_sound.setMuted(self._sound_muted)

        self.complete_sound = QSoundEffect(self)
        if complete_wav.exists():
            self.complete_sound.setSource(QUrl.fromLocalFile(str(complete_wav)))
        self.complete_sound.setVolume(1.0)
        self.complete_sound.setMuted(self._sound_muted)

        self.fail_sound = QSoundEffect(self)
        if fail_wav.exists():
            self.fail_sound.setSource(QUrl.fromLocalFile(str(fail_wav)))
        self.fail_sound.setVolume(1.0)
        self.fail_sound.setMuted(self._sound_muted)

    @property
    def is_muted(self) -> bool:
        """Indica si el audio está silenciado actualmente."""
        return bool(self._sound_muted)

    @is_muted.setter
    def is_muted(self, value: bool) -> None:
        self.set_muted(value)

    def set_muted(self, muted: bool) -> None:
        """Establece el estado de silenciamiento y lo persiste en QSettings."""
        try:
            self._sound_muted = bool(muted)
            self.settings.setValue("sound_muted", self._sound_muted)
            self.start_sound.setMuted(self._sound_muted)
            self.complete_sound.setMuted(self._sound_muted)
            self.fail_sound.setMuted(self._sound_muted)
            self.mute_state_changed.emit(self._sound_muted)
        except Exception:
            pass

    def toggle_muted(self) -> None:
        """Alterna el estado de silenciamiento."""
        self.set_muted(not self._sound_muted)

    def play_start(self) -> None:
        """Reproduce el sonido de inicio si no está silenciado."""
        if not self._sound_muted:
            try:
                self.start_sound.play()
            except Exception:
                pass

    def play_complete(self) -> None:
        """Reproduce el sonido de finalización si no está silenciado."""
        if not self._sound_muted:
            try:
                self.complete_sound.play()
            except Exception:
                pass

    def play_fail(self) -> None:
        """Reproduce el sonido de fallo/incompleto si no está silenciado."""
        if not self._sound_muted:
            try:
                self.fail_sound.play()
            except Exception:
                pass
