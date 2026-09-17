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
class TagDefinition:
    """Definición de una etiqueta o marcador visual a nivel de materia/registro."""

    id: str
    name: str
    color: str  # Código hexadecimal ej: "#ef4444"

    def to_dict(self) -> dict[str, Any]:
        """Serializa la definición de etiqueta a un diccionario."""
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagDefinition":
        """Reconstruye una etiqueta desde un diccionario JSON."""
        return cls(
            id=str(data.get("id") or str(uuid4())[:8]),
            name=str(data.get("name") or "Etiqueta"),
            color=str(data.get("color") or "#3b82f6"),
        )


def default_tags() -> list[TagDefinition]:
    """Genera el catálogo de etiquetas predeterminadas para un nuevo registro."""
    return [
        TagDefinition(id="tag-redo", name="Rehacer", color="#ef4444"),
        TagDefinition(id="tag-doubt", name="Duda para clase", color="#f59e0b"),
        TagDefinition(id="tag-consulted", name="Consulté respuesta", color="#3b82f6"),
        TagDefinition(id="tag-key", name="Clave / Importante", color="#a855f7"),
    ]


@dataclass
class PlannedSection:
    """Configuración planificada de una sección de estudio (guía, práctica, etc.)."""

    section_type: str = "Guía"
    section_number: int = 1
    title: str = ""
    total_exercises: int = 1
    exercise_configs: dict[int, int] = field(default_factory=dict)
    exercise_tags: dict[str, list[str]] = field(default_factory=dict)
    exercise_notes: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _make_exercise_key(exercise: int, inciso: int | None = None) -> str:
        return f"{exercise}.{inciso}" if (inciso is not None and inciso > 0) else str(exercise)

    def get_incisos_count(self, exercise: int) -> int:
        """Devuelve la cantidad de incisos configurada para un ejercicio específico (0 si no tiene)."""
        return self.exercise_configs.get(exercise, 0)

    def set_incisos_count(self, exercise: int, count: int) -> None:
        """Configura la cantidad de incisos para un ejercicio (si es <= 0, se elimina del mapeo)."""
        if count <= 0:
            self.exercise_configs.pop(exercise, None)
        else:
            self.exercise_configs[exercise] = count

    def get_exercise_tags(self, exercise: int, inciso: int | None = None) -> list[str]:
        """Devuelve la lista de IDs de etiquetas asociadas al ejercicio o inciso."""
        key = self._make_exercise_key(exercise, inciso)
        return list(self.exercise_tags.get(key, []))

    def set_exercise_tags(
        self, exercise: int, inciso: int | None = None, tag_ids: list[str] | None = None
    ) -> None:
        """Asigna o elimina las etiquetas para un ejercicio o inciso específico."""
        key = self._make_exercise_key(exercise, inciso)
        if not tag_ids:
            self.exercise_tags.pop(key, None)
        else:
            # Preservar unicidad manteniendo el orden
            seen = set()
            cleaned = []
            for t in tag_ids:
                if t not in seen:
                    seen.add(t)
                    cleaned.append(t)
            self.exercise_tags[key] = cleaned

    def get_note(self, exercise: int, inciso: int | None = None) -> str:
        """Devuelve el texto del apunte/nota asociado al ejercicio o inciso (o cadena vacía)."""
        key = self._make_exercise_key(exercise, inciso)
        return self.exercise_notes.get(key, "")

    def set_note(self, exercise: int, inciso: int | None = None, note: str = "") -> None:
        """Asigna o elimina el apunte/nota de un ejercicio o inciso específico."""
        key = self._make_exercise_key(exercise, inciso)
        cleaned = note.strip()
        if not cleaned:
            self.exercise_notes.pop(key, None)
        else:
            self.exercise_notes[key] = cleaned

    def to_dict(self) -> dict[str, Any]:
        """Serializa la sección planificada a un diccionario."""
        return {
            "section_type": self.section_type,
            "section_number": self.section_number,
            "title": self.title,
            "total_exercises": self.total_exercises,
            "exercise_configs": {str(k): v for k, v in self.exercise_configs.items()},
            "exercise_tags": self.exercise_tags,
            "exercise_notes": self.exercise_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannedSection":
        """Reconstruye una sección planificada desde un diccionario JSON."""
        raw_configs = data.get("exercise_configs") or {}
        exercise_configs = {int(k): int(v) for k, v in raw_configs.items()}
        raw_exercise_tags = data.get("exercise_tags") or {}
        exercise_tags = {
            str(k): [str(tid) for tid in v] if isinstance(v, list) else []
            for k, v in raw_exercise_tags.items()
        }
        raw_exercise_notes = data.get("exercise_notes") or {}
        exercise_notes = {
            str(k): str(v)
            for k, v in raw_exercise_notes.items()
            if isinstance(v, str) and v.strip()
        }
        return cls(
            section_type=str(data.get("section_type") or "Guía"),
            section_number=int(data.get("section_number") or 1),
            title=str(data.get("title") or ""),
            total_exercises=max(1, int(data.get("total_exercises") or 1)),
            exercise_configs=exercise_configs,
            exercise_tags=exercise_tags,
            exercise_notes=exercise_notes,
        )


@dataclass
class Milestone:
    """Representa un hito evaluativo dentro del período de cursada."""

    name: str
    date: str  # Formato ISO YYYY-MM-DD
    type: str = "parcial"  # "parcial", "recuperatorio", "final", "entrega", o personalizado
    color: str = "#ef4444"  # Color HEX para el mapa de calor
    icon: str = "🎯"  # Emoji o ícono representativo

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Milestone":
        m_type = str(data.get("type") or "parcial")
        default_color = (
            "#ef4444" if "parcial" in m_type.lower()
            else ("#f59e0b" if "recup" in m_type.lower()
            else ("#a855f7" if "final" in m_type.lower()
            else ("#3b82f6" if "entrega" in m_type.lower() else "#10b981")))
        )
        default_icon = (
            "🎯" if "parcial" in m_type.lower()
            else ("🔄" if "recup" in m_type.lower()
            else ("🏁" if "final" in m_type.lower()
            else ("💻" if "entrega" in m_type.lower() else "📝")))
        )
        return cls(
            name=str(data.get("name") or "Examen"),
            date=str(data.get("date") or ""),
            type=m_type,
            color=str(data.get("color") or default_color),
            icon=str(data.get("icon") or default_icon),
        )


@dataclass
class PlannerSchedule:
    """Configuración del período de cursada e hitos evaluativos."""

    period_type: str = "Cuatrimestral"  # "Bimestral", "Cuatrimestral", "Semestral", "Personalizado"
    start_date: str = ""  # Formato YYYY-MM-DD
    end_date: str = ""  # Formato YYYY-MM-DD
    milestones: list[Milestone] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_type": self.period_type,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "milestones": [m.to_dict() for m in self.milestones],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannerSchedule":
        raw_milestones = data.get("milestones", [])
        milestones = [
            Milestone.from_dict(m)
            for m in raw_milestones
            if isinstance(m, dict)
        ] if isinstance(raw_milestones, list) else []

        return cls(
            period_type=str(data.get("period_type") or "Cuatrimestral"),
            start_date=str(data.get("start_date") or ""),
            end_date=str(data.get("end_date") or ""),
            milestones=milestones,
        )


@dataclass
class Record:
    """Agrupa todos los items y la planificación de un fichero de registro de la aplicación."""

    record_name: str = "StudyTimetrial"
    items: list[TimerItem] = field(default_factory=list)
    planner_sections: list[PlannedSection] = field(default_factory=list)
    tags: list[TagDefinition] = field(default_factory=default_tags)
    planner_schedule: PlannerSchedule | None = None
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
            "tags": [tag.to_dict() for tag in self.tags],
            "planner_schedule": self.planner_schedule.to_dict() if self.planner_schedule else None,
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

        raw_tags = data.get("tags")
        if raw_tags is None:
            tags = default_tags()
        else:
            tags = [
                TagDefinition.from_dict(t)
                for t in raw_tags
                if isinstance(t, dict)
            ]

        raw_schedule = data.get("planner_schedule")
        planner_schedule = (
            PlannerSchedule.from_dict(raw_schedule)
            if isinstance(raw_schedule, dict)
            else None
        )

        return cls(
            record_name=str(data.get("record_name") or "StudyTimetrial"),
            items=[TimerItem.from_dict(item) for item in data["items"]],
            planner_sections=planner_sections,
            tags=tags,
            planner_schedule=planner_schedule,
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )