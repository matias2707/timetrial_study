"""Servicio de persistencia de presets y escaneo de pistas de ambientación sonora."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain.models import AmbiencePreset, default_ambient_presets

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}


class AmbientStorageService:
    """Gestiona el archivo data/ambient_presets.json y el directorio data/ambient/."""

    def __init__(
        self,
        base_dir: Path | None = None,
        presets_filename: str = "ambient_presets.json",
        audio_dirname: str = "ambient",
        presets_path: Path | None = None,
        audio_dir: Path | None = None,
    ) -> None:
        if base_dir is None:
            # d:/Proyectos/study_timetrial_demo/data
            base_dir = Path(__file__).resolve().parent.parent / "data"
        self.data_dir = Path(base_dir)
        self.presets_file = Path(presets_path) if presets_path else (self.data_dir / presets_filename)
        self.audio_dir = Path(audio_dir) if audio_dir else (self.data_dir / audio_dirname)

        # Asegurar que el directorio de audios exista
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def load_presets(self) -> tuple[list[AmbiencePreset], str]:
        """Carga los presets persistidos y el ID del preset activo.

        Si el archivo no existe o está corrupto, devuelve los presets por defecto.
        """
        if not self.presets_file.exists():
            defaults = default_ambient_presets()
            active_id = defaults[0].id
            self.save_presets(defaults, active_id)
            return defaults, active_id

        try:
            data = json.loads(self.presets_file.read_text(encoding="utf-8"))
            raw_presets = data.get("presets", [])
            presets = [
                AmbiencePreset.from_dict(p)
                for p in raw_presets
                if isinstance(p, dict)
            ]
            if not presets:
                presets = default_ambient_presets()

            active_id = str(data.get("active_preset_id") or presets[0].id)
            # Asegurar que el active_id exista entre los presets
            if not any(p.id == active_id for p in presets):
                active_id = presets[0].id

            return presets, active_id
        except Exception:
            defaults = default_ambient_presets()
            return defaults, defaults[0].id

    def save_presets(self, presets: list[AmbiencePreset], active_preset_id: str | None = None) -> None:
        """Guarda la lista de presets y el preset activo en disco de forma atómica."""
        if not presets:
            presets = default_ambient_presets()
        if not active_preset_id or not any(p.id == active_preset_id for p in presets):
            active_preset_id = presets[0].id

        payload: dict[str, Any] = {
            "schema_version": 1,
            "active_preset_id": active_preset_id,
            "presets": [p.to_dict() for p in presets],
        }

        self.presets_file.parent.mkdir(parents=True, exist_ok=True)
        # Escritura segura con protección ante bloqueos transitorios en Windows
        temp_file = self.presets_file.with_suffix(".tmp")
        try:
            temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(self.presets_file)
        except OSError:
            # Fallback en caso de que otro proceso bloquee temporalmente el archivo
            try:
                self.presets_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    def scan_audio_tracks(self) -> list[dict[str, Any]]:
        """Escanea el directorio data/ambient/ en busca de pistas de audio soportadas."""
        if not self.audio_dir.exists():
            return []

        tracks: list[dict[str, Any]] = []
        try:
            entries = list(self.audio_dir.iterdir())
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
