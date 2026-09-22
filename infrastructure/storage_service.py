from __future__ import annotations

"""Persistencia local de registros y gestión de archivos recientes."""

import json
from datetime import datetime
from pathlib import Path

from domain.models import Record


class RecentFilesManager:
    """Mantiene una lista de archivos abiertos recientemente en disco."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        else:
            data_recent = Path.cwd() / "data" / ".study_timetrial_recent.json"
            root_recent = Path.cwd() / ".study_timetrial_recent.json"
            if data_recent.exists():
                self.path = data_recent
            elif root_recent.exists():
                self.path = root_recent
            elif (Path.cwd() / "data").exists():
                self.path = data_recent
            else:
                self.path = root_recent
        self._paths: list[Path] = []
        self.load()

    @property
    def paths(self) -> list[Path]:
        return list(self._paths)

    def load(self) -> None:
        if not self.path.exists():
            self._paths = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._paths = []
            return
        entries = data if isinstance(data, list) else []
        resolved: list[Path] = []
        for value in entries:
            if not isinstance(value, str):
                continue
            candidate = Path(value).expanduser()
            if candidate.exists() and candidate.is_file():
                resolved.append(candidate)
        self._paths = resolved[:10]

    def save(self) -> None:
        payload = [str(path) for path in self._paths[:10]]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, path: str | Path) -> None:
        candidate = Path(path).expanduser().resolve()
        existing = [item for item in self._paths if item.resolve() == candidate]
        if existing:
            self._paths = [existing[0], *[item for item in self._paths if item.resolve() != candidate]]
        else:
            self._paths = [candidate, *self._paths]
        self._paths = self._paths[:10]
        self.save()


class StorageService:
    """Gestiona el almacenamiento local del registro en formato JSON."""

    def __init__(
        self,
        recent_files_path: Path | str | None = None,
        default_dir: Path | str | None = None,
    ) -> None:
        self.path: Path | None = None
        self._default_dir = Path(default_dir) if default_dir is not None else None
        self.recent_files = RecentFilesManager(recent_files_path)

    @property
    def default_directory(self) -> Path:
        """Devuelve el directorio estándar para almacenar registros."""
        if self._default_dir is not None:
            return self._default_dir
        records_dir = Path.cwd() / "data" / "records"
        if records_dir.exists():
            return records_dir
        return Path.cwd()

    @property
    def is_open(self) -> bool:
        """Indica si hay un archivo activo asociado al servicio."""
        return self.path is not None

    def create_automatic(self) -> Record:
        """Crea un registro nuevo con un nombre basado en la fecha actual."""
        stamp = datetime.now().strftime("%Y%m%d")
        target_dir = self.default_directory
        target_dir.mkdir(parents=True, exist_ok=True)
        self.path = target_dir / f"StudyTimetrial_{stamp}.json"
        return Record(record_name=self.path.stem)

    def save(self, record: Record, path: Path | None = None) -> None:
        """Guarda el registro actual en el fichero activo o en uno explícito."""
        if path is not None:
            self.path = path

        if self.path is None:
            raise ValueError("No hay un archivo activo")

        payload = json.dumps(record.to_dict(), ensure_ascii=False, indent=2)
        self.path.write_text(payload, encoding="utf-8")
        if self.path.exists():
            self.recent_files.add(self.path)

    def load(self, path: Path) -> Record:
        """Carga un registro desde disco y lo deja como activo."""
        record = self.read(path)
        self.path = path
        self.recent_files.add(path)
        return record

    def read(self, path: Path) -> Record:
        """Lee un registro sin cambiar el archivo activo y migra notas/comentarios a Markdown si es necesario."""
        data = json.loads(path.read_text(encoding="utf-8"))
        record = Record.from_dict(data)
        from infrastructure.compatibility import migrate_record_notes_to_markdown
        migrate_record_notes_to_markdown(record)
        return record