from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from models import Record


class StorageService:
    """Gestiona el almacenamiento local del registro en formato JSON."""

    def __init__(self) -> None:
        self.path: Path | None = None

    @property
    def is_open(self) -> bool:
        """Indica si hay un archivo activo asociado al servicio."""
        return self.path is not None

    def create_automatic(self) -> Record:
        """Crea un registro nuevo con un nombre basado en la fecha actual."""
        stamp = datetime.now().strftime("%Y%m%d")
        self.path = Path.cwd() / f"StudyTimetrial_{stamp}.json"
        return Record(record_name=self.path.stem)

    def save(self, record: Record, path: Path | None = None) -> None:
        """Guarda el registro actual en el fichero activo o en uno explícito."""
        if path is not None:
            self.path = path

        if self.path is None:
            raise ValueError("No hay un archivo activo")

        payload = json.dumps(record.to_dict(), ensure_ascii=False, indent=2)
        self.path.write_text(payload, encoding="utf-8")

    def load(self, path: Path) -> Record:
        """Carga un registro desde disco y lo deja como activo."""
        data = json.loads(path.read_text(encoding="utf-8"))
        record = Record.from_dict(data)
        self.path = path
        return record