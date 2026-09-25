"""Servicio de cálculo de estadísticas para registros de estudio.

Este módulo procesa los items de un Record y genera agregaciones, métricas
semanales y resúmenes de rendimiento sin depender de bibliotecas gráficas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Sequence

from domain.models import Milestone, Record, TimerItem

SPANISH_WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
SPANISH_DAYS_FULL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
SPANISH_MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


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
    planned_total: int | None = None
    planned_completed: int | None = None
    planned_completed_weight: float | None = None
    planned_completion_pct: float | None = None

    @property
    def planned_completed_display(self) -> str:
        if self.planned_completed_weight is not None:
            if self.planned_completed_weight.is_integer():
                return str(int(self.planned_completed_weight))
            return f"{self.planned_completed_weight:.1f}".rstrip("0").rstrip(".")
        if self.planned_completed is not None:
            return str(self.planned_completed)
        return "0"


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
    has_planner: bool = False
    planned_total_units: int = 0
    planned_completed_units: int = 0
    planned_completed_weight: float = 0.0
    planned_completion_percentage: float = 0.0

    @property
    def planned_completed_display(self) -> str:
        if self.planned_completed_weight.is_integer():
            return str(int(self.planned_completed_weight))
        return f"{self.planned_completed_weight:.1f}".rstrip("0").rstrip(".")

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


@dataclass(frozen=True)
class DailyAttemptLogEntry:
    item_id: str
    timestamp: str
    start_time_str: str
    section_display: str
    section_type: str
    section_number: int
    exercise: int
    inciso: int | None
    exercise_time_ms: int
    break_time_ms: int
    completed: bool
    notes: str = ""


@dataclass(frozen=True)
class DailyStatsSummary:
    target_date: str  # YYYY-MM-DD
    display_date: str
    is_today: bool
    total_exercise_time_ms: int
    total_break_time_ms: int
    attempts: list[DailyAttemptLogEntry]
    completed_count: int
    failed_count: int
    focus_ratio: float  # 0.0 a 100.0


@dataclass(frozen=True)
class WeeklyDaySummary:
    date_str: str  # YYYY-MM-DD
    day_name: str  # Lun, Mar...
    exercise_time_ms: int
    break_time_ms: int
    completed_count: int
    failed_count: int


@dataclass(frozen=True)
class WeeklyExerciseItem:
    section_type: str
    section_number: int
    exercise: int
    inciso: int | None
    section_display: str
    total_exercise_time_ms: int
    attempts_count: int
    is_completed: bool


@dataclass(frozen=True)
class WeeklyStatsSummary:
    week_start_str: str
    week_end_str: str
    display_range: str
    is_current_week: bool
    total_exercise_time_ms: int
    total_break_time_ms: int
    active_days_count: int
    days: list[WeeklyDaySummary]
    exercises: list[WeeklyExerciseItem]
    completed_count: int
    failed_count: int


@dataclass(frozen=True)
class CumulativePoint:
    date_str: str
    display_date: str
    cumulative_exercise_time_ms: int
    cumulative_completed: int
    cumulative_failed: int


@dataclass(frozen=True)
class CumulativeEvolutionData:
    points: list[CumulativePoint]
    total_study_time_ms: int
    total_completed: int
    total_failed: int


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
        has_planner = bool(record.planner_sections)
        planned_total_units = 0
        planned_completed_units = 0
        planned_completed_weight = 0.0
        planned_completion_percentage = 0.0
        empty_section_summaries: list[SectionSummary] = []

        if has_planner:
            from application.planner_service import PlannerService

            overview = PlannerService.compute_overview(record)
            planned_total_units = overview.total_units
            planned_completed_units = overview.completed_units
            planned_completed_weight = overview.completed_weight
            planned_completion_percentage = overview.global_completion_percentage
            for s in overview.sections:
                sec_name = f"{s.section.section_type} {s.section.section_number}"
                empty_section_summaries.append(
                    SectionSummary(
                        section_key=sec_name,
                        planned_total=s.total_units,
                        planned_completed=s.completed_units,
                        planned_completed_weight=s.completed_weight,
                        planned_completion_pct=s.completion_percentage,
                    )
                )

        return RecordStatistics(
            record_name=record.record_name or "StudyTimetrial",
            daily_stats=seven_days,
            section_summaries=empty_section_summaries,
            has_planner=has_planner,
            planned_total_units=planned_total_units,
            planned_completed_units=planned_completed_units,
            planned_completed_weight=planned_completed_weight,
            planned_completion_percentage=planned_completion_percentage,
        )

    total_exercise_time_ms = 0
    total_break_time_ms = 0
    completed_attempts = 0

    # Agrupación de items por ejercicio base: (section_type, section_number, exercise) -> list[TimerItem]
    exercise_groups: dict[tuple[str, int, int], list[TimerItem]] = {}

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

        norm_sec_type = item.section_type.strip()
        base_key = (norm_sec_type, item.section_number, item.exercise)
        exercise_groups.setdefault(base_key, []).append(item)

        # Fecha
        item_date = _parse_item_date(item.created_at)
        if item_date:
            valid_dates.append(item_date)
            day_exercise_map[item_date] = day_exercise_map.get(item_date, 0) + item.exercise_time_ms
            day_break_map[item_date] = day_break_map.get(item_date, 0) + item.break_time_ms

        # Agrupación por sección
        sec_name = f"{norm_sec_type} {item.section_number}"
        if sec_name not in sections_map:
            sections_map[sec_name] = {
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "attempts": 0,
                "unique_exercises": set(),
                "completed_exercises": set(),
            }
        sec_entry = sections_map[sec_name]
        sec_entry["exercise_time_ms"] += item.exercise_time_ms
        sec_entry["break_time_ms"] += item.break_time_ms
        sec_entry["attempts"] += 1
        sec_entry["unique_exercises"].add(item.exercise)

    longest_ms = 0
    longest_name = "Ninguno"
    completed_unique_exercises_set: set[tuple[str, int, int]] = set()

    for (s_type, s_num, ex_num), ex_items in exercise_groups.items():
        ex_time = sum(it.exercise_time_ms for it in ex_items)
        if ex_time > longest_ms:
            longest_ms = ex_time
            longest_name = format_exercise_label(s_type, s_num, ex_num)

        # Determinar si el ejercicio se considera completado
        matched_sec = None
        for s in record.planner_sections:
            if s.section_type.strip().lower() == s_type.lower() and s.section_number == s_num:
                matched_sec = s
                break

        if matched_sec and matched_sec.get_incisos_count(ex_num) > 0:
            req_incisos = matched_sec.get_incisos_count(ex_num)
            completed_incisos = {it.inciso for it in ex_items if it.completed and it.inciso is not None}
            is_completed = all(i in completed_incisos for i in range(1, req_incisos + 1))
        else:
            distinct_incisos = {it.inciso for it in ex_items if it.inciso is not None and it.inciso > 0}
            if distinct_incisos:
                completed_incisos = {it.inciso for it in ex_items if it.completed and it.inciso is not None}
                is_completed = (distinct_incisos == completed_incisos)
            else:
                is_completed = any(it.completed for it in ex_items)

        if is_completed:
            completed_unique_exercises_set.add((s_type, s_num, ex_num))
            sec_name = f"{s_type} {s_num}"
            if sec_name in sections_map:
                sections_map[sec_name]["completed_exercises"].add(ex_num)

    total_unique_count = len(exercise_groups)
    completed_unique_count = len(completed_unique_exercises_set)
    completion_pct = (completed_unique_count / total_unique_count * 100.0) if total_unique_count else 0.0

    avg_exercise_time_ms = total_exercise_time_ms // total_unique_count if total_unique_count else 0
    avg_break_time_ms = total_break_time_ms // total_unique_count if total_unique_count else 0

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

    # Resumen por secciones y cruce con planificador
    has_planner = bool(record.planner_sections)
    planned_total_units = 0
    planned_completed_units = 0
    planned_completed_weight = 0.0
    planned_completion_percentage = 0.0
    planned_sec_map = {}

    if has_planner:
        from application.planner_service import PlannerService

        overview = PlannerService.compute_overview(record)
        planned_total_units = overview.total_units
        planned_completed_units = overview.completed_units
        planned_completed_weight = overview.completed_weight
        planned_completion_percentage = overview.global_completion_percentage
        for s in overview.sections:
            k = f"{s.section.section_type} {s.section.section_number}"
            planned_sec_map[k] = s

    section_summaries: list[SectionSummary] = []
    all_sec_keys = sorted(set(sections_map.keys()) | set(planned_sec_map.keys()))

    for sec_name in all_sec_keys:
        sec_data = sections_map.get(
            sec_name,
            {
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "attempts": 0,
                "unique_exercises": set(),
                "completed_exercises": set(),
            },
        )
        p_sec = planned_sec_map.get(sec_name)
        p_tot = p_sec.total_units if p_sec else None
        p_comp = p_sec.completed_units if p_sec else None
        p_weight = p_sec.completed_weight if p_sec else None
        p_pct = p_sec.completion_percentage if p_sec else None

        section_summaries.append(
            SectionSummary(
                section_key=sec_name,
                exercise_time_ms=sec_data["exercise_time_ms"],
                break_time_ms=sec_data["break_time_ms"],
                attempts=sec_data["attempts"],
                completed_unique=len(sec_data["completed_exercises"]),
                total_unique=len(sec_data["unique_exercises"]),
                planned_total=p_tot,
                planned_completed=p_comp,
                planned_completed_weight=p_weight,
                planned_completion_pct=p_pct,
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
        has_planner=has_planner,
        planned_total_units=planned_total_units,
        planned_completed_units=planned_completed_units,
        planned_completed_weight=planned_completed_weight,
        planned_completion_percentage=planned_completion_percentage,
    )


class CourseHeatmapData(dict):
    """Estructura de datos para el mapa de calor con compatibilidad de diccionario y atributos."""

    @property
    def has_schedule(self) -> bool:
        return bool(self.get("has_schedule", False))

    @property
    def current_streak(self) -> int:
        return int(self.get("streak_days", 0))

    @property
    def total_study_days(self) -> int:
        return int(self.get("total_study_days", 0))

    @property
    def days_until_next_exam(self) -> int | None:
        return self.get("days_until_next_milestone")

    @property
    def next_exam_title(self) -> str | None:
        nm = self.get("next_milestone")
        if nm:
            return nm.get("title") or nm.get("name")
        return None

    @property
    def day_cells(self) -> list[dict[str, Any]]:
        cells: list[dict[str, Any]] = []
        for w in self.get("weeks", []):
            cells.extend(w)
        return cells


@dataclass
class TopEffortExercise:
    """Representa un ejercicio destacado en el ranking de mayor esfuerzo neto."""

    section_type: str
    section_number: int
    exercise: int
    inciso: int | None = None
    exercise_time_ms: int = 0
    break_time_ms: int = 0
    attempts: int = 0
    completed: bool = False
    rank: int = 1

    @property
    def total_time_ms(self) -> int:
        return self.exercise_time_ms + self.break_time_ms

    @property
    def status(self) -> str:
        return "completed" if self.completed else "pending"

    @property
    def display_label(self) -> str:
        suffix = f".{self.inciso}" if self.inciso is not None else ""
        return f"{self.section_type} {self.section_number} · Ej. {self.exercise}{suffix}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "section_type": self.section_type,
            "section_number": self.section_number,
            "exercise": self.exercise,
            "inciso": self.inciso,
            "identifier": self.display_label,
            "exercise_time_ms": self.exercise_time_ms,
            "break_time_ms": self.break_time_ms,
            "attempts": self.attempts,
            "completed": self.completed,
            "status": self.status,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


@dataclass
class HourlySlot:
    """Franja de una hora específica (0 a 23 hs)."""

    hour: int
    count: int = 0
    exercise_time_ms: int = 0
    percentage: float = 0.0


class HourlyDistribution(dict):
    """Distribución horaria de 24 horas con acceso por índice de hora o atributos."""

    def __init__(
        self,
        hourly_map: dict[int, int],
        slots: list[HourlySlot],
        total_sessions: int,
        peak_hour: int,
        peak_count: int,
    ) -> None:
        super().__init__(hourly_map)
        self.slots = slots
        self.total_sessions = total_sessions
        self.peak_hour = peak_hour
        self.peak_count = peak_count


def get_course_heatmap_data(record: Record, reference_date: date | None = None) -> CourseHeatmapData:
    """Calcula la matriz de semanas, días, hitos evaluativos y rachas para el mapa de calor de cursada."""
    today = reference_date or date.today()
    schedule = record.planner_schedule

    # Fechas de inicio y fin
    start_d: date | None = None
    end_d: date | None = None
    has_schedule = False

    if schedule and schedule.start_date and schedule.end_date:
        try:
            start_d = date.fromisoformat(schedule.start_date)
            end_d = date.fromisoformat(schedule.end_date)
            if end_d >= start_d:
                has_schedule = True
        except Exception:
            has_schedule = False

    # Agrupar tiempos por fecha de los items
    daily_exercise_map: dict[date, int] = {}
    for item in record.items:
        d = _parse_item_date(item.created_at)
        if d:
            daily_exercise_map[d] = daily_exercise_map.get(d, 0) + item.exercise_time_ms

    # Total de días con estudio registrado
    total_study_days = sum(1 for ms in daily_exercise_map.values() if ms > 0)

    # Calcular racha (streak) actual
    studied_dates = {d for d, ms in daily_exercise_map.items() if ms > 0}
    streak_days = 0
    check_date = today
    if check_date in studied_dates:
        while check_date in studied_dates:
            streak_days += 1
            check_date -= timedelta(days=1)
    elif (check_date - timedelta(days=1)) in studied_dates:
        check_date -= timedelta(days=1)
        while check_date in studied_dates:
            streak_days += 1
            check_date -= timedelta(days=1)

    # Próximo examen / hito
    milestones_list = schedule.milestones if schedule else []
    parsed_milestones: list[tuple[date, Milestone]] = []
    for m in milestones_list:
        try:
            m_d = date.fromisoformat(m.date)
            parsed_milestones.append((m_d, m))
        except Exception:
            continue
    parsed_milestones.sort(key=lambda x: x[0])

    next_milestone_obj: Milestone | None = None
    days_until_next: int | None = None
    for m_d, m in parsed_milestones:
        if m_d >= today:
            next_milestone_obj = m
            days_until_next = (m_d - today).days
            break

    if not has_schedule or not start_d or not end_d:
        return CourseHeatmapData({
            "has_schedule": False,
            "streak_days": streak_days,
            "total_study_days": total_study_days,
            "next_milestone": next_milestone_obj.to_dict() if next_milestone_obj else None,
            "days_until_next_milestone": days_until_next,
            "weeks": [],
            "start_date": None,
            "end_date": None,
            "total_weeks": 0,
            "max_day_ms": 0,
        })

    # Alinear al lunes de la primera semana
    first_monday = start_d - timedelta(days=start_d.weekday())
    # Alinear al domingo de la última semana
    last_sunday = end_d + timedelta(days=(6 - end_d.weekday()))

    # Mapa de hitos por fecha
    milestone_by_date: dict[date, Milestone] = {m_d: m for m_d, m in parsed_milestones}

    weeks: list[list[dict[str, Any]]] = []
    curr_monday = first_monday
    period_ms_list = [ms for d, ms in daily_exercise_map.items() if start_d <= d <= end_d]
    max_day_ms = max(period_ms_list + [3_600_000])

    while curr_monday <= last_sunday:
        week_days: list[dict[str, Any]] = []
        for day_offset in range(7):
            day_d = curr_monday + timedelta(days=day_offset)
            ex_ms = daily_exercise_map.get(day_d, 0)
            is_within = start_d <= day_d <= end_d
            m_found = milestone_by_date.get(day_d)

            week_days.append({
                "date": day_d.isoformat(),
                "day_of_week": day_offset,
                "exercise_time_ms": ex_ms,
                "is_today": day_d == today,
                "is_past": day_d < today,
                "is_future": day_d > today,
                "is_within_period": is_within,
                "milestone": m_found.to_dict() if m_found else None,
            })
        weeks.append(week_days)
        curr_monday += timedelta(days=7)

    return CourseHeatmapData({
        "has_schedule": True,
        "streak_days": streak_days,
        "total_study_days": total_study_days,
        "next_milestone": next_milestone_obj.to_dict() if next_milestone_obj else None,
        "days_until_next_milestone": days_until_next,
        "weeks": weeks,
        "start_date": start_d.isoformat(),
        "end_date": end_d.isoformat(),
        "total_weeks": len(weeks),
        "max_day_ms": max_day_ms,
    })


def get_top_effort_exercises(record: Record, limit: int = 5) -> list[TopEffortExercise]:
    """Calcula el ranking de ejercicios que mayor esfuerzo (tiempo neto de ejercicio) han requerido."""
    exercises_map: dict[tuple[str, int, int, int | None], dict[str, Any]] = {}

    for item in record.items:
        key = (item.section_type, item.section_number, item.exercise, item.inciso)
        if key not in exercises_map:
            exercises_map[key] = {
                "section_type": item.section_type,
                "section_number": item.section_number,
                "exercise": item.exercise,
                "inciso": item.inciso,
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "attempts": 0,
                "completed": False,
            }
        data = exercises_map[key]
        data["exercise_time_ms"] += item.exercise_time_ms
        data["break_time_ms"] += item.break_time_ms
        data["attempts"] += 1
        if item.completed:
            data["completed"] = True

    sorted_exercises = sorted(
        exercises_map.values(),
        key=lambda x: x["exercise_time_ms"],
        reverse=True,
    )

    result: list[TopEffortExercise] = []
    for i, ex in enumerate(sorted_exercises[:limit]):
        result.append(
            TopEffortExercise(
                rank=i + 1,
                section_type=ex["section_type"],
                section_number=ex["section_number"],
                exercise=ex["exercise"],
                inciso=ex["inciso"],
                exercise_time_ms=ex["exercise_time_ms"],
                break_time_ms=ex["break_time_ms"],
                attempts=ex["attempts"],
                completed=ex["completed"],
            )
        )
    return result


def get_24h_hourly_distribution(record: Record) -> HourlyDistribution:
    """Agrega los intentos y milisegundos netos dedicados al estudio según la hora del día (0 a 23 hs)."""
    hourly_time: dict[int, int] = {h: 0 for h in range(24)}
    hourly_counts: dict[int, int] = {h: 0 for h in range(24)}
    total_sessions = 0

    for item in record.items:
        if not item.created_at:
            continue
        try:
            dt = datetime.fromisoformat(item.created_at)
            hour = dt.hour
            if 0 <= hour <= 23:
                hourly_time[hour] += item.exercise_time_ms
                hourly_counts[hour] += 1
                total_sessions += 1
        except (ValueError, TypeError):
            continue

    slots: list[HourlySlot] = []
    peak_hour = 0
    peak_count = 0
    peak_time_ms = 0

    for h in range(24):
        c = hourly_counts[h]
        t = hourly_time[h]
        pct = (c / total_sessions * 100.0) if total_sessions > 0 else 0.0
        slots.append(
            HourlySlot(
                hour=h,
                count=c,
                exercise_time_ms=t,
                percentage=pct,
            )
        )
        if c > peak_count or (c == peak_count and t > peak_time_ms):
            peak_hour = h
            peak_count = c
            peak_time_ms = t

    return HourlyDistribution(
        hourly_map=hourly_time,
        slots=slots,
        total_sessions=total_sessions,
        peak_hour=peak_hour,
        peak_count=peak_count,
    )


def compute_exercise_personal_best_ms(
    record: Record,
    section_type: str,
    section_number: int,
    exercise: int,
    inciso: int | None = None,
) -> int | None:
    """Calcula el menor tiempo neto completado (completed=True) para un ejercicio e inciso específico."""
    norm_sec = section_type.strip().lower()
    matching_times = [
        item.exercise_time_ms
        for item in record.items
        if item.section_type.strip().lower() == norm_sec
        and item.section_number == section_number
        and item.exercise == exercise
        and item.inciso == inciso
        and item.completed
    ]
    if not matching_times:
        return None
    return min(matching_times)


def compute_today_timeline_buckets(
    record: Record,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Genera 24 franjas horarias (0 a 23 hs) para la fecha de referencia con métricas de actividad."""
    target_date = reference_date or date.today()
    hourly_time: dict[int, int] = {h: 0 for h in range(24)}
    hourly_attempts: dict[int, int] = {h: 0 for h in range(24)}

    for item in record.items:
        if not item.created_at:
            continue
        try:
            dt = datetime.fromisoformat(item.created_at)
            if dt.date() == target_date:
                h = dt.hour
                if 0 <= h <= 23:
                    hourly_time[h] += item.exercise_time_ms
                    hourly_attempts[h] += 1
        except (ValueError, TypeError):
            continue

    is_today = target_date == date.today()
    now_hour = datetime.now().hour if is_today else -1

    buckets: list[dict[str, Any]] = []
    for h in range(24):
        time_ms = hourly_time[h]
        minutes = time_ms / 60_000
        if time_ms == 0:
            level = 0
        elif minutes <= 15:
            level = 1
        elif minutes <= 30:
            level = 2
        elif minutes <= 45:
            level = 3
        else:
            level = 4

        buckets.append(
            {
                "hour": h,
                "exercise_time_ms": time_ms,
                "attempts_count": hourly_attempts[h],
                "intensity_level": level,
                "is_current_hour": (h == now_hour),
            }
        )

    return buckets


def compute_today_summary_metrics(
    record: Record,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Calcula las métricas consolidadas de la jornada: tiempo de estudio, ejercicios únicos y total intentos."""
    target_date = reference_date or date.today()
    study_time_ms = 0
    break_time_ms = 0
    total_attempts = 0
    completed_unique_exercises: set[tuple[str, int, int, int | None]] = set()

    for item in record.items:
        item_date = _parse_item_date(item.created_at)
        if item_date == target_date:
            study_time_ms += item.exercise_time_ms
            break_time_ms += item.break_time_ms
            total_attempts += 1
            if item.completed:
                completed_unique_exercises.add(
                    (
                        item.section_type.strip().lower(),
                        item.section_number,
                        item.exercise,
                        item.inciso,
                    )
                )

    return {
        "study_time_ms": study_time_ms,
        "break_time_ms": break_time_ms,
        "completed_unique_count": len(completed_unique_exercises),
        "total_attempts": total_attempts,
    }


def compute_streak_days(record: Record, reference_date: date | None = None) -> tuple[int, int]:
    """Calcula la racha actual de días consecutivos estudiados y el total de días de estudio."""
    today = reference_date or date.today()
    daily_exercise_map: dict[date, int] = {}
    for item in record.items:
        d = _parse_item_date(item.created_at)
        if d:
            daily_exercise_map[d] = daily_exercise_map.get(d, 0) + item.exercise_time_ms

    total_study_days = sum(1 for ms in daily_exercise_map.values() if ms > 0)
    studied_dates = {d for d, ms in daily_exercise_map.items() if ms > 0}
    streak_days = 0
    check_date = today

    if check_date in studied_dates:
        while check_date in studied_dates:
            streak_days += 1
            check_date -= timedelta(days=1)
    elif (check_date - timedelta(days=1)) in studied_dates:
        check_date -= timedelta(days=1)
        while check_date in studied_dates:
            streak_days += 1
            check_date -= timedelta(days=1)

    return streak_days, total_study_days


def get_top_effort_exercises_advanced(
    record: Record,
    criteria: str = "time",
    limit: int = 5,
) -> list[TopEffortExercise]:
    """Calcula el ranking de ejercicios según el criterio:

    - 'time': Mayor tiempo neto acumulado.
    - 'retries': Mayor cantidad de intentos / reintentos.
    - 'pb': Mejor marca personal / tiempo récord más veloz (solo completados).
    """
    exercises_map: dict[tuple[str, int, int, int | None], dict[str, Any]] = {}

    for item in record.items:
        key = (item.section_type, item.section_number, item.exercise, item.inciso)
        if key not in exercises_map:
            exercises_map[key] = {
                "section_type": item.section_type,
                "section_number": item.section_number,
                "exercise": item.exercise,
                "inciso": item.inciso,
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "attempts": 0,
                "completed": False,
                "best_time_ms": None,
            }
        data = exercises_map[key]
        data["exercise_time_ms"] += item.exercise_time_ms
        data["break_time_ms"] += item.break_time_ms
        data["attempts"] += 1
        if item.completed:
            data["completed"] = True
            if data["best_time_ms"] is None or item.exercise_time_ms < data["best_time_ms"]:
                data["best_time_ms"] = item.exercise_time_ms

    if criteria == "retries":
        sorted_exercises = sorted(
            exercises_map.values(),
            key=lambda x: (x["attempts"], x["exercise_time_ms"]),
            reverse=True,
        )
    elif criteria == "pb":
        completed_only = [ex for ex in exercises_map.values() if ex["best_time_ms"] is not None]
        sorted_exercises = sorted(
            completed_only,
            key=lambda x: x["best_time_ms"],
        )
    else:
        sorted_exercises = sorted(
            exercises_map.values(),
            key=lambda x: x["exercise_time_ms"],
            reverse=True,
        )

    result: list[TopEffortExercise] = []
    for i, ex in enumerate(sorted_exercises[:limit]):
        result.append(
            TopEffortExercise(
                rank=i + 1,
                section_type=ex["section_type"],
                section_number=ex["section_number"],
                exercise=ex["exercise"],
                inciso=ex["inciso"],
                exercise_time_ms=ex["exercise_time_ms"],
                break_time_ms=ex["break_time_ms"],
                attempts=ex["attempts"],
                completed=ex["completed"],
            )
        )
    return result


def compute_cumulative_evolution(record: Record) -> CumulativeEvolutionData:
    """Calcula la serie temporal acumulativa del tiempo neto, completados e incompletos."""
    daily_data: dict[date, dict[str, int]] = {}

    for item in record.items:
        d = _parse_item_date(item.created_at)
        if not d:
            continue
        if d not in daily_data:
            daily_data[d] = {
                "exercise_time_ms": 0,
                "completed": 0,
                "failed": 0,
            }
        daily_data[d]["exercise_time_ms"] += item.exercise_time_ms
        if item.completed:
            daily_data[d]["completed"] += 1
        else:
            daily_data[d]["failed"] += 1

    sorted_dates = sorted(daily_data.keys())
    points: list[CumulativePoint] = []
    cum_time = 0
    cum_completed = 0
    cum_failed = 0

    for d in sorted_dates:
        data = daily_data[d]
        cum_time += data["exercise_time_ms"]
        cum_completed += data["completed"]
        cum_failed += data["failed"]
        disp = f"{d.day} {SPANISH_MONTHS[d.month - 1][:3]}"
        points.append(
            CumulativePoint(
                date_str=d.isoformat(),
                display_date=disp,
                cumulative_exercise_time_ms=cum_time,
                cumulative_completed=cum_completed,
                cumulative_failed=cum_failed,
            )
        )

    return CumulativeEvolutionData(
        points=points,
        total_study_time_ms=cum_time,
        total_completed=cum_completed,
        total_failed=cum_failed,
    )


def compute_daily_stats_summary(
    record: Record,
    target_date: date,
) -> DailyStatsSummary:
    """Calcula las métricas consolidadas y el desglose de intentos para un día específico."""
    attempts: list[DailyAttemptLogEntry] = []
    total_exercise_time_ms = 0
    total_break_time_ms = 0
    completed_count = 0
    failed_count = 0

    for item in record.items:
        d = _parse_item_date(item.created_at)
        if d != target_date:
            continue

        start_time_str = "--:--"
        if item.created_at:
            try:
                dt = datetime.fromisoformat(item.created_at)
                start_time_str = dt.strftime("%H:%M")
            except (ValueError, TypeError):
                pass

        total_exercise_time_ms += item.exercise_time_ms
        total_break_time_ms += item.break_time_ms
        if item.completed:
            completed_count += 1
        else:
            failed_count += 1

        sec_disp = f"{item.section_type} {item.section_number}"
        attempts.append(
            DailyAttemptLogEntry(
                item_id=item.id,
                timestamp=item.created_at or "",
                start_time_str=start_time_str,
                section_display=sec_disp,
                section_type=item.section_type,
                section_number=item.section_number,
                exercise=item.exercise,
                inciso=item.inciso,
                exercise_time_ms=item.exercise_time_ms,
                break_time_ms=item.break_time_ms,
                completed=item.completed,
                notes=getattr(item, "comment", "") or getattr(item, "notes", "") or "",
            )
        )

    attempts.sort(key=lambda x: x.timestamp)

    total_time = total_exercise_time_ms + total_break_time_ms
    focus_ratio = (total_exercise_time_ms / total_time * 100.0) if total_time > 0 else 0.0
    display_date = f"{SPANISH_DAYS_FULL[target_date.weekday()]}, {target_date.day} de {SPANISH_MONTHS[target_date.month - 1]} de {target_date.year}"

    return DailyStatsSummary(
        target_date=target_date.isoformat(),
        display_date=display_date,
        is_today=(target_date == date.today()),
        total_exercise_time_ms=total_exercise_time_ms,
        total_break_time_ms=total_break_time_ms,
        attempts=attempts,
        completed_count=completed_count,
        failed_count=failed_count,
        focus_ratio=focus_ratio,
    )


def compute_weekly_stats_summary(
    record: Record,
    reference_date: date,
) -> WeeklyStatsSummary:
    """Calcula las métricas de la semana (Lunes a Domingo) que contiene a reference_date."""
    start_of_week = reference_date - timedelta(days=reference_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    items_by_date: dict[date, list[TimerItem]] = {
        start_of_week + timedelta(days=i): [] for i in range(7)
    }

    for item in record.items:
        d = _parse_item_date(item.created_at)
        if d and start_of_week <= d <= end_of_week:
            items_by_date[d].append(item)

    days_summary: list[WeeklyDaySummary] = []
    total_week_exercise_ms = 0
    total_week_break_ms = 0
    active_days_count = 0
    week_completed = 0
    week_failed = 0

    for i in range(7):
        curr_d = start_of_week + timedelta(days=i)
        day_items = items_by_date[curr_d]
        d_ex_ms = sum(x.exercise_time_ms for x in day_items)
        d_br_ms = sum(x.break_time_ms for x in day_items)
        d_comp = sum(1 for x in day_items if x.completed)
        d_fail = sum(1 for x in day_items if not x.completed)

        total_week_exercise_ms += d_ex_ms
        total_week_break_ms += d_br_ms
        week_completed += d_comp
        week_failed += d_fail
        if d_ex_ms > 0:
            active_days_count += 1

        days_summary.append(
            WeeklyDaySummary(
                date_str=curr_d.isoformat(),
                day_name=SPANISH_WEEKDAYS[i],
                exercise_time_ms=d_ex_ms,
                break_time_ms=d_br_ms,
                completed_count=d_comp,
                failed_count=d_fail,
            )
        )

    exercises_map: dict[tuple[str, int, int, int | None], dict[str, Any]] = {}
    for day_items in items_by_date.values():
        for it in day_items:
            key = (it.section_type, it.section_number, it.exercise, it.inciso)
            if key not in exercises_map:
                exercises_map[key] = {
                    "section_type": it.section_type,
                    "section_number": it.section_number,
                    "exercise": it.exercise,
                    "inciso": it.inciso,
                    "section_display": f"{it.section_type} {it.section_number}",
                    "total_exercise_time_ms": 0,
                    "attempts_count": 0,
                    "is_completed": False,
                }
            exercises_map[key]["total_exercise_time_ms"] += it.exercise_time_ms
            exercises_map[key]["attempts_count"] += 1
            if it.completed:
                exercises_map[key]["is_completed"] = True

    exercises_list = sorted(
        exercises_map.values(),
        key=lambda x: x["total_exercise_time_ms"],
        reverse=True,
    )

    exercise_items = [
        WeeklyExerciseItem(
            section_type=ex["section_type"],
            section_number=ex["section_number"],
            exercise=ex["exercise"],
            inciso=ex["inciso"],
            section_display=ex["section_display"],
            total_exercise_time_ms=ex["total_exercise_time_ms"],
            attempts_count=ex["attempts_count"],
            is_completed=ex["is_completed"],
        )
        for ex in exercises_list
    ]

    today_date = date.today()
    is_curr_week = start_of_week <= today_date <= end_of_week
    display_range = (
        f"{start_of_week.day} {SPANISH_MONTHS[start_of_week.month - 1][:3]} - "
        f"{end_of_week.day} {SPANISH_MONTHS[end_of_week.month - 1][:3]} {end_of_week.year}"
    )

    return WeeklyStatsSummary(
        week_start_str=start_of_week.isoformat(),
        week_end_str=end_of_week.isoformat(),
        display_range=display_range,
        is_current_week=is_curr_week,
        total_exercise_time_ms=total_week_exercise_ms,
        total_break_time_ms=total_week_break_ms,
        active_days_count=active_days_count,
        days=days_summary,
        exercises=exercise_items,
        completed_count=week_completed,
        failed_count=week_failed,
    )


