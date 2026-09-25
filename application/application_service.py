"""Casos de uso y estado de sesion, independientes de PySide6.

Este modulo coordina dominio e infraestructura mediante dependencias
inyectables. La interfaz solo traduce eventos y muestra sus resultados.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from infrastructure.export_service import ExportResult

from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    ExerciseNodeStatus,
    PlannerOverview,
    PlannerService,
)
from application.statistics_service import (
    CumulativeEvolutionData,
    DailyStatsSummary,
    RecordStatistics,
    TopEffortExercise,
    WeeklyStatsSummary,
    compute_cumulative_evolution,
    compute_daily_stats_summary,
    compute_exercise_personal_best_ms,
    compute_statistics,
    compute_streak_days,
    compute_today_study_time_ms,
    compute_today_summary_metrics,
    compute_today_timeline_buckets,
    compute_weekly_stats_summary,
    get_24h_hourly_distribution,
    get_course_heatmap_data,
    get_top_effort_exercises,
    get_top_effort_exercises_advanced,
)
from domain.models import Milestone, PlannedSection, PlannerSchedule, Record, TagDefinition, TimerItem
from domain.timer_service import TimerMode, TimerService
from infrastructure.storage_service import StorageService


@dataclass
class SessionLocation:
    """Ubicación editable del intento actual."""

    section_type: str = "Guía"
    section_number: int = 1
    exercise: int = 1
    inciso: int | None = None


class StudyApplicationService:
    """Coordina los casos de uso de la aplicación sin depender de Qt.

    La interfaz gráfica adapta eventos y valores de widgets a esta fachada.
    Las reglas de sesión, navegación, registro y persistencia permanecen aquí
    para que puedan probarse sin levantar una ventana.
    """

    def __init__(self, storage: StorageService | None = None, timer: TimerService | None = None) -> None:
        self.storage = storage or StorageService()
        self.timer = timer or TimerService()
        self.record = self.storage.create_automatic()
        self.location = SessionLocation()
        self.pending_comment = ""
        self.editing_item_id: str | None = None
        self.editing_initial_exercise_ms: int = 0

    @property
    def is_editing(self) -> bool:
        """Indica si el cronómetro está en modo continuación / edición de un registro."""
        return self.editing_item_id is not None

    @property
    def editing_item(self) -> TimerItem | None:
        """Devuelve la entidad TimerItem que se está editando actualmente, o None."""
        if not self.editing_item_id:
            return None
        for item in self.record.items:
            if item.id == self.editing_item_id:
                return item
        return None

    @property
    def is_record_open(self) -> bool:
        return self.storage.is_open

    @property
    def record_path(self) -> Path | None:
        return self.storage.path

    @property
    def mode(self) -> TimerMode:
        return self.timer.mode

    def set_location(self, location: SessionLocation, force: bool = False) -> None:
        """Actualiza la ubicación solo cuando no hay una sesión activa, salvo que force=True."""
        if not force and self.mode is not TimerMode.WAITING:
            return
        loc_changed = (
            self.location.section_type != location.section_type
            or self.location.section_number != location.section_number
            or self.location.exercise != location.exercise
            or self.location.inciso != location.inciso
        )
        self.location = location
        if loc_changed and not self.is_editing:
            self.pending_comment = self.get_exercise_note(
                location.section_type, location.section_number, location.exercise, location.inciso
            )

    def toggle_session(self, location: SessionLocation | None = None) -> TimerMode:
        """Inicia, pausa o reanuda la sesión y devuelve el modo resultante."""
        if self.mode is TimerMode.WAITING:
            if location is not None:
                self.set_location(location)
            self.timer.start()
        else:
            self.timer.toggle_break()
        return self.mode

    def stop_session(self) -> None:
        """Descarta el intento en curso sin crear un registro."""
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.timer.reset()
        self.pending_comment = ""

    def load_item_into_session(self, item: TimerItem) -> None:
        """Carga un item previamente guardado para continuar su conteo o actualizarlo."""
        self.editing_item_id = item.id
        self.editing_initial_exercise_ms = item.exercise_time_ms
        self.location = SessionLocation(
            section_type=item.section_type,
            section_number=item.section_number,
            exercise=item.exercise,
            inciso=item.inciso,
        )
        self.pending_comment = item.comment
        self.timer.load_accumulated_times(item.exercise_time_ms, item.break_time_ms)

    def cancel_editing_session(self) -> None:
        """Cancela el modo edición y reinicia el cronómetro a un estado limpio."""
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.timer.reset()
        self.pending_comment = ""

    def pause_timer(self) -> None:
        """Pausa / congela los cronómetros de la sesión actual."""
        self.timer.pause()

    def resume_timer(self) -> None:
        """Reanuda los cronómetros de la sesión actual."""
        self.timer.resume()

    @property
    def is_timer_paused(self) -> bool:
        """Indica si el cronómetro se encuentra en pausa temporal."""
        return self.timer.is_paused

    def set_comment(self, comment: str) -> None:
        """Define el comentario que se guardará con el intento actual."""
        self.pending_comment = comment.strip()

    def finish_item(self, completed: bool, overwrite: bool = True) -> bool:
        """Guarda el intento activo y reinicia el cronómetro.

        Si overwrite=True y se estaba en modo edición, actualiza los datos del item existente.
        En caso contrario, inserta un nuevo item en el registro.
        """
        if not self.is_record_open:
            return False

        if self.mode is TimerMode.WAITING and not self.editing_item_id:
            return False

        exercise_ms, break_ms = self.timer.snapshot()

        if self.editing_item_id and overwrite:
            target = self.editing_item
            if target is not None:
                target.section_type = self.location.section_type
                target.section_number = self.location.section_number
                target.exercise = self.location.exercise
                target.inciso = self.location.inciso
                target.exercise_time_ms = exercise_ms
                target.break_time_ms = break_ms
                target.completed = completed
                target.comment = self.pending_comment
            else:
                self.record.items.append(
                    TimerItem(
                        section_type=self.location.section_type,
                        section_number=self.location.section_number,
                        exercise=self.location.exercise,
                        inciso=self.location.inciso,
                        exercise_time_ms=exercise_ms,
                        break_time_ms=break_ms,
                        completed=completed,
                        comment=self.pending_comment,
                    )
                )
        else:
            self.record.items.append(
                TimerItem(
                    section_type=self.location.section_type,
                    section_number=self.location.section_number,
                    exercise=self.location.exercise,
                    inciso=self.location.inciso,
                    exercise_time_ms=exercise_ms,
                    break_time_ms=break_ms,
                    completed=completed,
                    comment=self.pending_comment,
                )
            )

        self.save()
        self.timer.reset()
        self.pending_comment = ""
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        return True


    def save(self) -> None:
        if not self.is_record_open:
            return
        self.storage.save(self.record)

    def new_record(self, record_name: str | None = None, directory: Path | None = None) -> Path:
        """Crea un registro nuevo con un nombre único en el directorio especificado o estándar."""
        requested_name = (record_name or self.record.record_name or "StudyTimetrial").strip()
        if not requested_name:
            requested_name = self.record.record_name or "StudyTimetrial"

        base_name = requested_name.removesuffix(".json")
        candidate_name = base_name
        suffix = 1
        base_dir = directory
        if base_dir is None:
            base_dir = getattr(self.storage, "default_directory", Path.cwd())
        base_dir.mkdir(parents=True, exist_ok=True)

        while True:
            path = base_dir / f"{candidate_name}.json"
            if not path.exists():
                self.record = Record(record_name=candidate_name)
                self.storage.path = path
                self.storage.save(self.record, path)
                return path
            candidate_name = f"{base_name}_{suffix}"
            suffix += 1

    def save_as(self, path: Path) -> None:
        self.storage.save(self.record, path)
        self.record.record_name = path.stem
        self.save()

    def load(self, path: Path) -> None:
        self.record = self.storage.load(path)
        if PlannerService.migrate_legacy_comments_to_notes(self.record) > 0:
            self.save()

    def import_items(self, path: Path, item_indexes: list[int]) -> int:
        """Añade copias de los items seleccionados sin cambiar el archivo activo."""
        if not self.is_record_open:
            return 0
        imported_record = self.storage.read(path)
        selected_items = [imported_record.items[index] for index in item_indexes]
        for item in selected_items:
            item_data = item.to_dict()
            item_data["id"] = None
            self.record.items.append(TimerItem.from_dict(item_data))

        if selected_items:
            self.save()
        return len(selected_items)

    def rename(self, path: Path) -> None:
        if self.storage.path is None:
            raise ValueError("No hay un archivo activo")
        self.storage.path.rename(path)
        self.storage.path = path
        self.record.record_name = path.stem
        self.save()

    def close_record(self) -> None:
        self.storage.path = None
        self.record = Record(record_name="")
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.timer.reset()
        self.pending_comment = ""

    def ordered_items(self) -> list[TimerItem]:
        return sorted(self.record.items, key=lambda item: item.created_at, reverse=True)

    def add_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.record.items.append(item)
        self.save()

    def replace_item(self, current: TimerItem, replacement: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.record.items[self.record.items.index(current)] = replacement
        self.save()

    def reset_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        item.exercise_time_ms = 0
        item.break_time_ms = 0
        self.save()

    def update_comment(self, item: TimerItem, comment: str) -> None:
        """Actualiza el comentario de un item ya guardado."""
        if not self.is_record_open:
            return
        item.comment = comment.strip()
        self.save()

    def delete_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.record.items.remove(item)
        self.save()

    def find_inciso_gap_candidates(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        new_inciso: int | None,
    ) -> list[TimerItem]:
        """Detecta si al registrar un inciso existen intentos previos sin inciso o con desfasaje para ese ejercicio.

        Devuelve la lista de TimerItems sin inciso correspondientes a ese ejercicio.
        """
        if new_inciso is None or new_inciso < 1:
            return []

        norm_type = section_type.strip().lower()
        matching = [
            item
            for item in self.record.items
            if item.section_type.strip().lower() == norm_type
            and item.section_number == section_number
            and item.exercise == exercise
        ]

        unincisoed = [item for item in matching if item.inciso is None or item.inciso == 0]
        return unincisoed

    def promote_gap_items(self, items: list[TimerItem], target_inciso: int = 1) -> None:
        """Actualiza el inciso de los items indicados (generalmente de None a 1) y persiste."""
        if not self.is_record_open or not items:
            return
        for item in items:
            item.inciso = target_inciso
        self.save()

    def get_statistics(self, reference_date: date | None = None) -> RecordStatistics:
        """Calcula y devuelve el resumen estadístico del registro actual."""
        return compute_statistics(self.record, reference_date=reference_date)

    def get_today_study_time_ms(self, include_current: bool = True, reference_date: date | None = None) -> int:
        """Calcula los milisegundos totales estudiados en el día de hoy (incluyendo sesión activa)."""
        total = compute_today_study_time_ms(self.record, reference_date=reference_date)
        if include_current and self.mode is not TimerMode.WAITING:
            exercise_ms, _ = self.timer.snapshot()
            current_delta = max(0, exercise_ms - self.editing_initial_exercise_ms)
            total += current_delta
        return total

    def get_planner_overview(self) -> PlannerOverview:
        """Calcula el resumen del universo planificado y estados de ejercicios."""
        return PlannerService.compute_overview(self.record)

    def sync_planner_with_records(self) -> bool:
        """Sincroniza la planificación agregando ejercicios no planificados que existan en registros."""
        if not self.is_record_open:
            return False
        changed = PlannerService.sync_planner_with_records(self.record)
        if changed:
            self.save()
        return changed

    def add_or_update_planned_section(self, section: PlannedSection) -> None:
        """Añade o edita una sección en la planificación y guarda el registro."""
        if not self.is_record_open:
            return
        PlannerService.add_or_update_section(self.record, section)
        self.save()

    def delete_planned_section(self, section_type: str, section_number: int) -> bool:
        """Elimina una sección de la planificación y guarda el registro."""
        if not self.is_record_open:
            return False
        deleted = PlannerService.delete_section(self.record, section_type, section_number)
        if deleted:
            self.save()
        return deleted

    def check_location_boundary(self, location: SessionLocation) -> tuple[bool, str]:
        """Comprueba si la ubicación indicada está dentro de la planificación configurada."""
        return PlannerService.is_location_within_plan(
            self.record,
            location.section_type,
            location.section_number,
            location.exercise,
            location.inciso,
        )

    def get_tag_catalog(self) -> list[TagDefinition]:
        """Devuelve el catálogo de etiquetas del registro activo."""
        if not self.is_record_open:
            return []
        return PlannerService.get_tag_catalog(self.record)

    def add_tag_definition(self, name: str, color: str) -> TagDefinition | None:
        """Añade una nueva etiqueta al catálogo y persiste."""
        if not self.is_record_open:
            return None
        tag = PlannerService.add_tag_definition(self.record, name, color)
        self.save()
        return tag

    def update_tag_definition(self, tag_id: str, name: str, color: str) -> bool:
        """Actualiza una etiqueta en el catálogo y persiste."""
        if not self.is_record_open:
            return False
        updated = PlannerService.update_tag_definition(self.record, tag_id, name, color)
        if updated:
            self.save()
        return updated

    def delete_tag_definition(self, tag_id: str) -> bool:
        """Elimina una etiqueta del catálogo, limpia referencias y persiste."""
        if not self.is_record_open:
            return False
        deleted = PlannerService.delete_tag_definition(self.record, tag_id)
        if deleted:
            self.save()
        return deleted

    def get_exercise_tags(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None = None
    ) -> list[str]:
        """Devuelve los IDs de etiquetas asociadas a un ejercicio o inciso."""
        if not self.is_record_open:
            return []
        return PlannerService.get_exercise_tags(
            self.record, section_type, section_number, exercise, inciso
        )

    def set_exercise_tags(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        tag_ids: list[str],
    ) -> None:
        """Asigna etiquetas a un ejercicio o inciso y persiste los cambios."""
        if not self.is_record_open:
            return
        PlannerService.set_exercise_tags(
            self.record, section_type, section_number, exercise, inciso, tag_ids
        )
        self.save()

    def get_exercise_note(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None = None
    ) -> str:
        """Devuelve la nota asignada a un ejercicio o inciso."""
        if not self.is_record_open:
            return ""
        return PlannerService.get_exercise_note(
            self.record, section_type, section_number, exercise, inciso
        )

    def set_exercise_note(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        note: str,
    ) -> None:
        """Asigna o actualiza la nota de un ejercicio o inciso y persiste los cambios."""
        if not self.is_record_open:
            return
        PlannerService.set_exercise_note(
            self.record, section_type, section_number, exercise, inciso, note
        )
        loc = self.location
        if (
            loc.section_type.strip().lower() == section_type.strip().lower()
            and loc.section_number == section_number
            and loc.exercise == exercise
            and loc.inciso == inciso
        ):
            self.pending_comment = note.strip()
        self.save()

    def get_schedule(self) -> PlannerSchedule | None:
        """Devuelve la configuración del cronograma de cursada del registro activo."""
        if not self.is_record_open:
            return None
        return self.record.planner_schedule

    def set_schedule(self, schedule: PlannerSchedule | None) -> None:
        """Configura o actualiza el cronograma de cursada y persiste los cambios."""
        if not self.is_record_open:
            return
        self.record.planner_schedule = schedule
        self.save()

    def get_course_heatmap_data(self, reference_date: date | None = None) -> dict[str, Any]:
        """Calcula los datos del mapa de calor de cursada para el registro activo."""
        if not self.is_record_open:
            return {
                "has_schedule": False,
                "streak_days": 0,
                "next_milestone": None,
                "days_until_next_milestone": None,
                "weeks": [],
                "start_date": None,
                "end_date": None,
                "total_weeks": 0,
                "max_day_ms": 0,
            }
        return get_course_heatmap_data(self.record, reference_date=reference_date)

    def get_top_effort_exercises(self, limit: int = 5) -> list[dict[str, Any]]:
        """Devuelve el ranking de ejercicios de mayor tiempo neto de estudio."""
        if not self.is_record_open:
            return []
        return get_top_effort_exercises(self.record, limit=limit)

    def get_24h_hourly_distribution(self) -> dict[int, int]:
        """Devuelve la distribución horaria de estudio acumulado (0..23 hs)."""
        if not self.is_record_open:
            return {h: 0 for h in range(24)}
        return get_24h_hourly_distribution(self.record)

    def get_top_effort_exercises_advanced(self, criteria: str = "time", limit: int = 5) -> list[TopEffortExercise]:
        """Devuelve el ranking de ejercicios según el criterio especificado ('time', 'retries', 'pb')."""
        if not self.is_record_open:
            return []
        return get_top_effort_exercises_advanced(self.record, criteria=criteria, limit=limit)

    def get_cumulative_evolution_data(self) -> CumulativeEvolutionData:
        """Devuelve la serie temporal acumulativa de tiempo neto y completitud."""
        if not self.is_record_open:
            return CumulativeEvolutionData(points=[], total_study_time_ms=0, total_completed=0, total_failed=0)
        return compute_cumulative_evolution(self.record)

    def get_daily_stats_summary(self, target_date: date | None = None) -> DailyStatsSummary:
        """Devuelve el resumen y log de intentos para la fecha dada (o hoy)."""
        t_date = target_date or date.today()
        if not self.is_record_open:
            return compute_daily_stats_summary(Record(record_name=""), t_date)
        return compute_daily_stats_summary(self.record, t_date)

    def get_weekly_stats_summary(self, reference_date: date | None = None) -> WeeklyStatsSummary:
        """Devuelve el resumen de la semana (Lunes a Domingo) que contiene reference_date."""
        ref_date = reference_date or date.today()
        if not self.is_record_open:
            return compute_weekly_stats_summary(Record(record_name=""), ref_date)
        return compute_weekly_stats_summary(self.record, ref_date)

    def get_streak_days(self, reference_date: date | None = None) -> tuple[int, int]:
        """Devuelve (racha_actual, total_dias_estudio)."""
        if not self.is_record_open:
            return (0, 0)
        return compute_streak_days(self.record, reference_date=reference_date)

    def get_exercise_personal_best_ms(
        self,
        section_type: str | None = None,
        section_number: int | None = None,
        exercise: int | None = None,
        inciso: int | None = None,
    ) -> int | None:
        """Devuelve el menor tiempo neto completado para la ubicación especificada o actual."""
        if not self.is_record_open:
            return None
        sec_type = section_type if section_type is not None else self.location.section_type
        sec_num = section_number if section_number is not None else self.location.section_number
        ex = exercise if exercise is not None else self.location.exercise
        inc = inciso if inciso is not None else self.location.inciso
        return compute_exercise_personal_best_ms(self.record, sec_type, sec_num, ex, inc)

    def get_today_timeline_buckets(
        self, reference_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Devuelve 24 buckets horarios con actividad y nivel de intensidad para hoy."""
        if not self.is_record_open:
            return [
                {
                    "hour": h,
                    "exercise_time_ms": 0,
                    "attempts_count": 0,
                    "intensity_level": 0,
                    "is_current_hour": False,
                }
                for h in range(24)
            ]
        return compute_today_timeline_buckets(self.record, reference_date=reference_date)

    def get_today_summary_metrics(
        self, reference_date: date | None = None
    ) -> dict[str, Any]:
        """Devuelve las métricas consolidadas del día de hoy."""
        if not self.is_record_open:
            return {
                "study_time_ms": 0,
                "break_time_ms": 0,
                "completed_unique_count": 0,
                "total_attempts": 0,
            }
        return compute_today_summary_metrics(self.record, reference_date=reference_date)

    def get_exercise_status(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
    ) -> str:
        """Devuelve el estado de un ejercicio: STATUS_COMPLETED, STATUS_FAILED o STATUS_PENDING.

        Funciona tanto si el ejercicio está planificado como en modo estudio libre.
        """
        if not self.is_record_open:
            return STATUS_PENDING

        norm_type = section_type.strip().lower()
        matching = [
            it
            for it in self.record.items
            if it.section_type.strip().lower() == norm_type
            and it.section_number == section_number
            and it.exercise == exercise
            and (inciso is None or it.inciso == inciso or (inciso == 1 and it.inciso is None))
        ]
        if not matching:
            return STATUS_PENDING
        if any(it.completed for it in matching):
            return STATUS_COMPLETED
        return STATUS_FAILED

    def get_max_incisos_for_exercise(
        self, section_type: str, section_number: int, exercise: int
    ) -> int:
        """Devuelve la cantidad de incisos configurada en la planificación para un ejercicio (0 si no tiene)."""
        if not self.is_record_open:
            return 0
        norm_type = section_type.strip().lower()
        for sec in self.record.planner_sections:
            if (
                sec.section_type.strip().lower() == norm_type
                and sec.section_number == section_number
            ):
                return sec.get_incisos_count(exercise)
        return 0

    def get_or_create_exercise_node(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
    ) -> ExerciseNodeStatus:
        """Obtiene el ExerciseNodeStatus de la planificación o lo construye al vuelo si no hay plan."""
        # 1. Si existe en la planificación, buscarlo
        overview = self.get_planner_overview()
        norm_type = section_type.strip().lower()
        for sec in overview.sections:
            if (
                sec.section.section_type.strip().lower() == norm_type
                and sec.section.section_number == section_number
            ):
                for node in sec.exercise_nodes:
                    if node.exercise == exercise:
                        if inciso is None:
                            return node
                        if node.has_incisos:
                            for sub in node.incisos:
                                if sub.inciso == inciso:
                                    return sub
                            return node
                        return node

        # 2. Si no hay planificación para esta sección/ejercicio, construirlo al vuelo con los datos reales
        items = [
            it
            for it in self.record.items
            if it.section_type.strip().lower() == norm_type
            and it.section_number == section_number
            and it.exercise == exercise
            and (inciso is None or it.inciso == inciso or (inciso == 1 and it.inciso is None))
        ]
        tag_ids = self.get_exercise_tags(section_type, section_number, exercise, inciso)
        tag_catalog = {t.id: t for t in self.get_tag_catalog()}
        tags = [tag_catalog[tid] for tid in tag_ids if tid in tag_catalog]
        note = self.get_exercise_note(section_type, section_number, exercise, inciso)
        status = self.get_exercise_status(section_type, section_number, exercise, inciso)

        ex_time = sum(it.exercise_time_ms for it in items)
        br_time = sum(it.break_time_ms for it in items)
        comp_attempts = sum(1 for it in items if it.completed)
        failed_attempts = len(items) - comp_attempts
        comments = [it.comment.strip() for it in items if it.comment and it.comment.strip()]

        return ExerciseNodeStatus(
            section_type=section_type,
            section_number=section_number,
            exercise=exercise,
            inciso=inciso,
            status=status,
            attempts=len(items),
            failed_attempts=failed_attempts,
            completed_attempts=comp_attempts,
            exercise_time_ms=ex_time,
            break_time_ms=br_time,
            comments=comments,
            latest_comment=comments[-1] if comments else "",
            has_incisos=False,
            incisos=[],
            tags=tags,
            note=note,
            has_note=bool(note.strip()),
        )

    def export_items_to_csv(
        self,
        file_path: Path | str,
        items: Sequence[TimerItem] | None = None,
        delimiter: str = ";",
    ) -> ExportResult:
        """Exporta el historial detallado de intentos a CSV (RFC 4180 / utf-8-sig)."""
        from infrastructure.export_service import export_items_to_csv

        target_items = items if items is not None else (self.record.items if self.is_record_open else [])
        tag_catalog = self.get_tag_catalog() if self.is_record_open else []
        planner_sections = self.record.planner_sections if self.is_record_open else []

        return export_items_to_csv(
            file_path=file_path,
            items=target_items,
            delimiter=delimiter,
            tag_catalog=tag_catalog,
            planner_sections=planner_sections,
        )

    def export_summary_to_csv(
        self,
        file_path: Path | str,
        delimiter: str = ";",
    ) -> ExportResult:
        """Exporta el reporte consolidado curricular por ejercicios e incisos a CSV."""
        from infrastructure.export_service import export_summary_to_csv

        if not self.is_record_open:
            return export_summary_to_csv(file_path=file_path, summary_rows=[], delimiter=delimiter)

        overview = self.get_planner_overview()
        summary_rows: list[dict[str, Any]] = []

        for sec_status in overview.sections:
            for node in sec_status.exercise_nodes:
                if node.has_incisos and node.incisos:
                    for sub in node.incisos:
                        summary_rows.append(self._build_summary_row_dict(sub))
                else:
                    summary_rows.append(self._build_summary_row_dict(node))

        return export_summary_to_csv(file_path=file_path, summary_rows=summary_rows, delimiter=delimiter)

    def _build_summary_row_dict(self, node: ExerciseNodeStatus) -> dict[str, Any]:
        """Construye el diccionario de fila de resumen para un ExerciseNodeStatus."""
        from infrastructure.export_service import format_ms_to_hhmmss

        if node.status == STATUS_COMPLETED:
            status_display = "Resuelto"
        elif node.status == STATUS_FAILED:
            status_display = "Incompleto"
        else:
            status_display = "Sin Intentos"

        success_rate = (
            f"{(node.completed_attempts / node.attempts * 100):.1f}%"
            if node.attempts > 0
            else "0.0%"
        )
        avg_ms = (node.exercise_time_ms // node.attempts) if node.attempts > 0 else 0
        pb_ms = compute_exercise_personal_best_ms(
            self.record, node.section_type, node.section_number, node.exercise, node.inciso
        )

        tags_str = " | ".join(t.name for t in node.tags)

        return {
            "section_type": node.section_type,
            "section_number": node.section_number,
            "exercise": node.exercise,
            "inciso": node.inciso if (node.inciso is not None and node.inciso > 0) else "",
            "identifier": node.full_label,
            "resolution_status": status_display,
            "total_attempts": node.attempts,
            "completed_attempts": node.completed_attempts,
            "failed_attempts": node.failed_attempts,
            "success_rate": success_rate,
            "total_time_hhmmss": format_ms_to_hhmmss(node.exercise_time_ms),
            "total_time_s": f"{node.exercise_time_ms / 1000.0:.2f}",
            "avg_time_hhmmss": format_ms_to_hhmmss(avg_ms),
            "pb_time_hhmmss": format_ms_to_hhmmss(pb_ms) if pb_ms is not None else "-",
            "tags": tags_str,
            "notes": node.note,
        }