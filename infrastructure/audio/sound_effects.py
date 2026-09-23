"""Reproducción y control de efectos sonoros discretos (campana, inicio, finalización)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QSoundEffect


class SoundEffectsPlayer(QObject):
    """Reproductor de efectos de sonido discretos mediante QSoundEffect."""

    mute_state_changed = Signal(bool)

    def __init__(self, media_dir: Path | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        target_dir = media_dir or (Path(__file__).resolve().parent.parent.parent / "presentation" / "media")
        start_wav = target_dir / "universfield-new-notification-040-493469.wav"
        complete_wav = target_dir / "universfield-new-notification-051-494246.wav"
        fail_wav = target_dir / "fail.wav"

        self._muted: bool = False

        self.start_sound = QSoundEffect(self)
        if start_wav.exists():
            self.start_sound.setSource(QUrl.fromLocalFile(str(start_wav)))
        self.start_sound.setVolume(1.0)
        self.start_sound.setMuted(self._muted)

        self.complete_sound = QSoundEffect(self)
        if complete_wav.exists():
            self.complete_sound.setSource(QUrl.fromLocalFile(str(complete_wav)))
        self.complete_sound.setVolume(1.0)
        self.complete_sound.setMuted(self._muted)

        self.fail_sound = QSoundEffect(self)
        if fail_wav.exists():
            self.fail_sound.setSource(QUrl.fromLocalFile(str(fail_wav)))
        self.fail_sound.setVolume(1.0)
        self.fail_sound.setMuted(self._muted)

    @property
    def is_muted(self) -> bool:
        return self._muted

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        self.start_sound.setMuted(self._muted)
        self.complete_sound.setMuted(self._muted)
        self.fail_sound.setMuted(self._muted)
        self.mute_state_changed.emit(self._muted)

    def play_start(self) -> None:
        if not self._muted:
            try:
                self.start_sound.play()
            except Exception:
                pass

    def play_complete(self) -> None:
        if not self._muted:
            try:
                self.complete_sound.play()
            except Exception:
                pass

    def play_fail(self) -> None:
        if not self._muted:
            try:
                self.fail_sound.play()
            except Exception:
                pass
