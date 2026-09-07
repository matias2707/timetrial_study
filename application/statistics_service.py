"""Servicio de cálculo de estadísticas para registros de estudio.

Este módulo procesa los items de un Record y genera agregaciones, métricas
semanales y resúmenes de rendimiento sin depender de bibliotecas gráficas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Sequence

from domain.models import Record, TimerItem

SPANISH_WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@dataclass
class DailyStatistic:
    """Métricas agregadas para un día calendario específico."""

    date: date
    day_name: str
    date_str: str
    exercise_time_ms: int = 0
    break_time_ms: int = 0

    @property
    def total_time_ms(self) -> int:
        return self.exercise_time_ms + self.break_time_ms


@dataclass
class SectionSummary:
    """Métricas agrupadas por sección de estudio."""

    section_key: str
    exercise_time_ms: int = 0
    break_time_ms: int = 0
    attempts: int = 0
    completed_unique: int = 0
    total_unique: int = 0


@dataclass
class RecordStatistics:
    """Conjunto completo de métricas calculadas a partir de un registro."""

    record_name: str
    total_exercise_time_ms: int = 0
    total_break_time_ms: int = 0
    avg_exercise_time_ms: int = 0
    avg_break_time_ms: int = 0
    longest_exercise_time_ms: int = 0
    longest_exercise_name: str = "Ninguno"
    total_unique_exercises: int = 0
    completed_unique_exercises: int = 0
    completion_percentage: float = 0.0
    total_attempts: int = 0
    completed_attempts: int = 0
    daily_stats: list[DailyStatistic] = field(default_factory=list)
    section_summaries: list[SectionSummary] = field(default_factory=list)

    @property
    def total_time_ms(self) -> int:
        return self.total_exercise_time_ms + self.total_break_time_ms

    @property
    def exercise_ratio_percentage(self) -> float:
        if self.total_time_ms == 0:
            return 0.0
        return (self.total_exercise_time_ms / self.total_time_ms) * 100.0

    @property
    def break_ratio_percentage(self) -> float:
        if self.total_time_ms == 0:
            return 0.0
        return (self.total_break_time_ms / self.total_time_ms) * 100.0


def _parse_item_date(created_at_str: str) -> date | None:
    """Intenta parsear la fecha de creación ISO del item."""
    if not created_at_str:
        return None
    try:
        return datetime.fromisoformat(created_at_str).date()
    except (ValueError, TypeError):
        return None


def format_exercise_label(section_type: str, section_number: int, exercise: int, inciso: int | None = None) -> str:
    """Genera la representación legible de un ejercicio."""
    suffix = f" · Inciso {inciso}" if inciso else ""
    return f"{section_type} {section_number} · Ejercicio {exercise}{suffix}"


def compute_today_study_time_ms(record: Record, reference_date: date | None = None) -> int:
    """Calcula la suma de milisegundos de ejercicio completados en la fecha de referencia (o hoy)."""
    target_date = reference_date or date.today()
    return sum(
        item.exercise_time_ms
        for item in record.items
        if _parse_item_date(item.created_at) == target_date
    )


def compute_statistics(record: Record, reference_date: date | None = None) -> RecordStatistics:
    """Calcula todas las métricas estadísticas a partir del registro dado.

    Si se proporciona reference_date, la ventana de 7 días terminará en esa fecha;
    de lo contrario, finalizará en la fecha más reciente encontrada entre los items
    o en la fecha actual (date.today()).
    """
    items: Sequence[TimerItem] = record.items
    total_attempts = len(items)

    if not items:
        end_date = reference_date or date.today()
        seven_days = [
            DailyStatistic(
                date=day,
                day_name=SPANISH_WEEKDAYS[day.weekday()],
                date_str=day.strftime("%d/%m"),
            )
            for day in (end_date - timedelta(days=i) for i in range(6, -1, -1))
        ]
        return RecordStatistics(
            record_name=record.record_name or "StudyTimetrial",
            daily_stats=seven_days,
        )

    total_exercise_time_ms = 0
    total_break_time_ms = 0
    completed_attempts = 0

    longest_ms = 0
    longest_name = "Ninguno"

    # Estructuras para seguimiento de ejercicios únicos: (section_type, section_number, exercise, inciso)
    unique_all: set[tuple[str, int, int, int | None]] = set()
    unique_completed: set[tuple[str, int, int, int | None]] = set()

    # Agrupaciones diarias y por sección
    day_exercise_map: dict[date, int] = {}
    day_break_map: dict[date, int] = {}
    valid_dates: list[date] = []

    # Secciones
    sections_map: dict[str, dict[str, Any]] = {}

    for item in items:
        total_exercise_time_ms += item.exercise_time_ms
        total_break_time_ms += item.break_time_ms
        if item.completed:
            completed_attempts += 1

        # Ejercicio más largo
        if item.exercise_time_ms > longest_ms:
            longest_ms = item.exercise_time_ms
            longest_name = format_exercise_label(
                item.section_type,
                item.section_number,
                item.exercise,
                item.inciso,
            )

        # Seguimiento de unicidad
        ex_key = (item.section_type, item.section_number, item.exercise, item.inciso)
        unique_all.add(ex_key)
        if item.completed:
            unique_completed.add(ex_key)

        # Fecha
        item_date = _parse_item_date(item.created_at)
        if item_date:
            valid_dates.append(item_date)
            day_exercise_map[item_date] = day_exercise_map.get(item_date, 0) + item.exercise_time_ms
            day_break_map[item_date] = day_break_map.get(item_date, 0) + item.break_time_ms

        # Agrupación por sección
        sec_name = f"{item.section_type} {item.section_number}"
        if sec_name not in sections_map:
            sections_map[sec_name] = {
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "attempts": 0,
                "unique_exercises": set(),
                "completed_unique": set(),
            }
        sec_entry = sections_map[sec_name]
        sec_entry["exercise_time_ms"] += item.exercise_time_ms
        sec_entry["break_time_ms"] += item.break_time_ms
        sec_entry["attempts"] += 1
        sec_entry["unique_exercises"].add((item.exercise, item.inciso))
        if item.completed:
            sec_entry["completed_unique"].add((item.exercise, item.inciso))

    avg_exercise_time_ms = total_exercise_time_ms // total_attempts if total_attempts else 0
    avg_break_time_ms = total_break_time_ms // total_attempts if total_attempts else 0

    total_unique_count = len(unique_all)
    completed_unique_count = len(unique_completed)
    completion_pct = (completed_unique_count / total_unique_count * 100.0) if total_unique_count else 0.0

    # Ventana semanal de 7 días
    if reference_date is not None:
        end_date = reference_date
    else:
        latest_item_date = max(valid_dates) if valid_dates else date.today()
        end_date = max(latest_item_date, date.today())

    seven_days: list[DailyStatistic] = []
    for day_offset in range(6, -1, -1):
        curr_day = end_date - timedelta(days=day_offset)
        seven_days.append(
            DailyStatistic(
                date=curr_day,
                day_name=SPANISH_WEEKDAYS[curr_day.weekday()],
                date_str=curr_day.strftime("%d/%m"),
                exercise_time_ms=day_exercise_map.get(curr_day, 0),
                break_time_ms=day_break_map.get(curr_day, 0),
            )
        )

    # Resumen por secciones
    section_summaries: list[SectionSummary] = []
    for sec_name, sec_data in sorted(sections_map.items()):
        section_summaries.append(
            SectionSummary(
                section_key=sec_name,
                exercise_time_ms=sec_data["exercise_time_ms"],
                break_time_ms=sec_data["break_time_ms"],
                attempts=sec_data["attempts"],
                completed_unique=len(sec_data["completed_unique"]),
                total_unique=len(sec_data["unique_exercises"]),
            )
        )

    return RecordStatistics(
        record_name=record.record_name or "StudyTimetrial",
        total_exercise_time_ms=total_exercise_time_ms,
        total_break_time_ms=total_break_time_ms,
        avg_exercise_time_ms=avg_exercise_time_ms,
        avg_break_time_ms=avg_break_time_ms,
        longest_exercise_time_ms=longest_ms,
        longest_exercise_name=longest_name,
        total_unique_exercises=total_unique_count,
        completed_unique_exercises=completed_unique_count,
        completion_percentage=completion_pct,
        total_attempts=total_attempts,
        completed_attempts=completed_attempts,
        daily_stats=seven_days,
        section_summaries=section_summaries,
    )
