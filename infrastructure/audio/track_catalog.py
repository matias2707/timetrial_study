"""Catálogo y descubrimiento de pistas de audio ambiental."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}


def scan_audio_tracks(audio_dir: Path) -> list[dict[str, Any]]:
    """Escanea un directorio en busca de pistas de audio con extensiones soportadas."""
    if not audio_dir.is_dir():
        return []

    tracks: list[dict[str, Any]] = []
    try:
        entries = list(audio_dir.iterdir())
    except OSError:
        return []

    for entry in sorted(entries, key=lambda p: p.name.lower()):
        try:
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
                tracks.append({
                    "filename": entry.name,
                    "path": str(entry.resolve()),
                    "name": entry.stem,
                    "extension": entry.suffix.lower(),
                    "size_bytes": entry.stat().st_size,
                })
        except (OSError, PermissionError):
            continue
    return tracks
