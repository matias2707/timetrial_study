"""Subsistema de audio dedicado de Study Timetrial."""

from __future__ import annotations

from infrastructure.audio.mixer_engine import (
    AudioMixerEngine,
    MAX_ACTIVE_TRACKS,
    TICK_INTERVAL_MS,
    TrackPlayer,
)
from infrastructure.audio.sound_effects import SoundEffectsPlayer
from infrastructure.audio.track_catalog import scan_audio_tracks

__all__ = [
    "AudioMixerEngine",
    "TrackPlayer",
    "SoundEffectsPlayer",
    "scan_audio_tracks",
    "MAX_ACTIVE_TRACKS",
    "TICK_INTERVAL_MS",
]
