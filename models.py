from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    """Devuelve la fecha y hora actual en formato ISO con precisión de segundos."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class TimerItem:
    """Representa una sesión de trabajo registrada por el cronómetro.

    Cada item contiene la ubicación del ejercicio, el tiempo dedicado al
    ejercicio, el tiempo de descanso acumulado y el estado de finalización.
    """

    section_type: str
    section_number: int
    exercise: int
    inciso: int | None
    exercise_time_ms: int
    break_time_ms: int
    completed: bool
    comment: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el modelo para persistirlo como JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TimerItem":
        """Reconstruye un item desde un diccionario JSON válido."""
        required = (
            "section_type",
            "section_number",
            "exercise",
            "exercise_time_ms",
            "break_time_ms",
            "completed",
        )
        if any(key not in data for key in required):
            raise ValueError("Faltan campos obligatorios en un item")

        inciso = data.get("inciso")
        if inciso == 0:
            inciso = None

        return cls(
            id=str(data.get("id") or uuid4()),
            section_type=str(data["section_type"]),
            section_number=int(data["section_number"]),
            exercise=int(data["exercise"]),
            inciso=None if inciso is None else int(inciso),
            exercise_time_ms=int(data["exercise_time_ms"]),
            break_time_ms=int(data["break_time_ms"]),
            completed=bool(data["completed"]),
            comment=str(data.get("comment") or ""),
            created_at=str(data.get("created_at") or now_iso()),
        )


@dataclass
class Record:
    """Agrupa todos los items de un fichero de registro de la aplicación."""

    record_name: str = "StudyTimetrial"
    items: list[TimerItem] = field(default_factory=list)
    schema_version: int = 1
    application: str = "Study Timetrial"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el registro con marca temporal actualizada."""
        self.updated_at = now_iso()
        return {
            "schema_version": self.schema_version,
            "application": self.application,
            "record_name": self.record_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Record":
        """Carga un registro desde el formato JSON persistido en disco."""
        if data.get("schema_version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("El archivo no usa el esquema compatible")

        return cls(
            record_name=str(data.get("record_name") or "StudyTimetrial"),
            items=[TimerItem.from_dict(item) for item in data["items"]],
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )