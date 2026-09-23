"""Puente de compatibilidad para el motor multicanal de mezcla de audio.

NOTA: La implementación central de bajo nivel ha sido reubicada en `infrastructure.audio.mixer_engine`.
Este módulo se preserva para garantizar retrocompatibilidad absoluta con imports y tests existentes.
"""

from __future__ import annotations

from infrastructure.audio.mixer_engine import (
    FPS,
    MAX_ACTIVE_TRACKS,
    TICK_INTERVAL_MS,
    AudioMixerEngine,
    TrackPlayer,
)

__all__ = [
    "TrackPlayer",
    "AudioMixerEngine",
    "MAX_ACTIVE_TRACKS",
    "FPS",
    "TICK_INTERVAL_MS",
]
