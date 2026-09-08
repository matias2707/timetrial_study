from __future__ import annotations

"""Entidades del dominio y contrato de serialización JSON versionado."""

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
class PlannedSection:
    """Configuración planificada de una sección de estudio (guía, práctica, etc.)."""

    section_type: str = "Guía"
    section_number: int = 1
    title: str = ""
    total_exercises: int = 1
    exercise_configs: dict[int, int] = field(default_factory=dict)

    def get_incisos_count(self, exercise: int) -> int:
        """Devuelve la cantidad de incisos configurada para un ejercicio específico (0 si no tiene)."""
        return self.exercise_configs.get(exercise, 0)

    def set_incisos_count(self, exercise: int, count: int) -> None:
        """Configura la cantidad de incisos para un ejercicio (si es <= 0, se elimina del mapeo)."""
        if count <= 0:
            self.exercise_configs.pop(exercise, None)
        else:
            self.exercise_configs[exercise] = count

    def to_dict(self) -> dict[str, Any]:
        """Serializa la sección planificada a un diccionario."""
        return {
            "section_type": self.section_type,
            "section_number": self.section_number,
            "title": self.title,
            "total_exercises": self.total_exercises,
            "exercise_configs": {str(k): v for k, v in self.exercise_configs.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannedSection":
        """Reconstruye una sección planificada desde un diccionario JSON."""
        raw_configs = data.get("exercise_configs") or {}
        exercise_configs = {int(k): int(v) for k, v in raw_configs.items()}
        return cls(
            section_type=str(data.get("section_type") or "Guía"),
            section_number=int(data.get("section_number") or 1),
            title=str(data.get("title") or ""),
            total_exercises=max(1, int(data.get("total_exercises") or 1)),
            exercise_configs=exercise_configs,
        )


@dataclass
class Record:
    """Agrupa todos los items y la planificación de un fichero de registro de la aplicación."""

    record_name: str = "StudyTimetrial"
    items: list[TimerItem] = field(default_factory=list)
    planner_sections: list[PlannedSection] = field(default_factory=list)
    schema_version: int = 1
    application: str = "Study Timetrial"
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el registro con marca temporal actualizada y secciones planificadas."""
        self.updated_at = now_iso()
        return {
            "schema_version": self.schema_version,
            "application": self.application,
            "record_name": self.record_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "items": [item.to_dict() for item in self.items],
            "planner_sections": [sec.to_dict() for sec in self.planner_sections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Record":
        """Carga un registro desde el formato JSON persistido en disco."""
        if data.get("schema_version") != 1 or not isinstance(data.get("items"), list):
            raise ValueError("El archivo no usa el esquema compatible")

        raw_sections = data.get("planner_sections", [])
        planner_sections = [
            PlannedSection.from_dict(s)
            for s in raw_sections
            if isinstance(s, dict)
        ] if isinstance(raw_sections, list) else []

        return cls(
            record_name=str(data.get("record_name") or "StudyTimetrial"),
            items=[TimerItem.from_dict(item) for item in data["items"]],
            planner_sections=planner_sections,
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )