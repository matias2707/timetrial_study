"""Casos de uso y estado de sesion, independientes de PySide6.

Este modulo coordina dominio e infraestructura mediante dependencias
inyectables. La interfaz solo traduce eventos y muestra sus resultados.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from application.save_policy import SavePolicy
from infrastructure.export_service import ExportResult

from application.organizer_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    ExerciseNodeStatus,
    OrganizedSectionStatus,
    OrganizedSectionStatus as PlannedSectionStatus,
    OrganizerOverview,
    OrganizerOverview as PlannerOverview,
    OrganizerService,
    OrganizerService as PlannerService,
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
from domain.models import (
    Milestone,
    OrganizedSection,
    OrganizerSchedule,
    PlannedSection,
    PlannerSchedule,
    Record,
    TagDefinition,
    TimerItem,
)
from domain.timer_service import TimerMode, TimerService
from infrastructure.storage_service import StorageService
from application.undo import (
    AddItemCommand,
    AddOrUpdateSectionCommand,
    DeleteItemCommand,
    DeleteSectionCommand,
    PromoteIncisoCommand,
    ReplaceItemCommand,
    SetExerciseNoteCommand,
    SetExerciseTagsCommand,
    SetScheduleCommand,
    UndoManager,
    UpdateCommentCommand,
)


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

    def __init__(
        self,
        storage: StorageService | None = None,
        timer: TimerService | None = None,
        save_policy: SavePolicy = SavePolicy.AUTO_PERIODIC,
    ) -> None:
        self.storage = storage or StorageService()
        self.timer = timer or TimerService()
        self.save_policy = save_policy
        self.record = self.storage.create_automatic()
        self.location = SessionLocation()
        self.pending_comment = ""
        self.editing_item_id: str | None = None
        self.editing_initial_exercise_ms: int = 0
        self.session_started_at: datetime | None = None
        self.undo_manager = UndoManager(max_depth=50)
        self._is_dirty: bool = False
        self._dirty_listeners: list[Callable[[bool], None]] = []

    @property
    def is_dirty(self) -> bool:
        """Indica si existen modificaciones en memoria pendientes de persistir en disco."""
        return self._is_dirty

    def add_dirty_listener(self, listener: Callable[[bool], None]) -> None:
        """Registra un callback que recibe el nuevo estado booleano de is_dirty."""
        if listener not in self._dirty_listeners:
            self._dirty_listeners.append(listener)

    def remove_dirty_listener(self, listener: Callable[[bool], None]) -> None:
        """Elimina un callback registrado para cambios de dirty state."""
        if listener in self._dirty_listeners:
            self._dirty_listeners.remove(listener)

    def _notify_dirty_changed(self) -> None:
        for listener in list(self._dirty_listeners):
            try:
                listener(self._is_dirty)
            except Exception:
                pass

    def _mark_dirty(self) -> None:
        """Marca el estado como sucio y ejecuta guardado inmediato si la política lo exige."""
        if not self._is_dirty:
            self._is_dirty = True
            self._notify_dirty_changed()
        if self.save_policy == SavePolicy.AUTO_IMMEDIATE:
            self.save()

    @property
    def can_undo(self) -> bool:
        """Indica si hay al menos una acción disponible para deshacer."""
        return self.undo_manager.can_undo

    @property
    def can_redo(self) -> bool:
        """Indica si hay al menos una acción disponible para rehacer."""
        return self.undo_manager.can_redo

    @property
    def undo_description(self) -> str:
        """Descripción de la acción que se desharía."""
        return self.undo_manager.undo_description

    @property
    def redo_description(self) -> str:
        """Descripción de la acción que se reharía."""
        return self.undo_manager.redo_description

    def undo(self) -> bool:
        """Revierte la última acción y marca el estado como modificado."""
        if not self.is_record_open or not self.can_undo:
            return False
        cmd = self.undo_manager.undo()
        if cmd is not None:
            self._mark_dirty()
            return True
        return False

    def redo(self) -> bool:
        """Reaplica la última acción deshecha y marca el estado como modificado."""
        if not self.is_record_open or not self.can_redo:
            return False
        cmd = self.undo_manager.redo()
        if cmd is not None:
            self._mark_dirty()
            return True
        return False

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
            self.session_started_at = datetime.now().replace(microsecond=0)
            self.timer.start()
        else:
            self.timer.toggle_break()
        return self.mode

    def stop_session(self) -> None:
        """Descarta el intento en curso sin crear un registro."""
        self.discard_session_draft()
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.session_started_at = None
        self.timer.reset()
        self.pending_comment = ""

    def load_item_into_session(self, item: TimerItem) -> None:
        """Carga un item previamente guardado para continuar su conteo o actualizarlo."""
        self.editing_item_id = item.id
        self.editing_initial_exercise_ms = item.exercise_time_ms
        self.session_started_at = None
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
        self.discard_session_draft()
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.session_started_at = None
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
        # Redondeo exacto a segundos (múltiplos de 1.000 ms) para consistencia limpia sin residuos sub-segundo
        exercise_ms = int(round(exercise_ms / 1000.0) * 1000)
        break_ms = int(round(break_ms / 1000.0) * 1000)
        total_duration_ms = exercise_ms + break_ms
        started_dt = (
            self.session_started_at or (datetime.now() - timedelta(milliseconds=total_duration_ms))
        ).replace(microsecond=0)
        item_created_at = started_dt.isoformat(timespec="seconds")

        if self.editing_item_id and overwrite:
            target = self.editing_item
            if target is not None:
                old_copy = TimerItem(
                    id=target.id,
                    section_type=target.section_type,
                    section_number=target.section_number,
                    exercise=target.exercise,
                    inciso=target.inciso,
                    exercise_time_ms=target.exercise_time_ms,
                    break_time_ms=target.break_time_ms,
                    completed=target.completed,
                    comment=target.comment,
                    created_at=target.created_at,
                )
                target.section_type = self.location.section_type
                target.section_number = self.location.section_number
                target.exercise = self.location.exercise
                target.inciso = self.location.inciso
                target.exercise_time_ms = exercise_ms
                target.break_time_ms = break_ms
                target.completed = completed
                target.comment = self.pending_comment
                self.undo_manager.push_executed(
                    ReplaceItemCommand(
                        self.record,
                        old_copy,
                        target,
                        description=f"Actualizar intento Ej. {target.exercise}"
                        + (f".{target.inciso}" if target.inciso else ""),
                    )
                )
            else:
                new_item = TimerItem(
                    section_type=self.location.section_type,
                    section_number=self.location.section_number,
                    exercise=self.location.exercise,
                    inciso=self.location.inciso,
                    exercise_time_ms=exercise_ms,
                    break_time_ms=break_ms,
                    completed=completed,
                    comment=self.pending_comment,
                    created_at=item_created_at,
                )
                self.record.items.append(new_item)
                self.undo_manager.push_executed(
                    AddItemCommand(
                        self.record,
                        new_item,
                        description=f"Completar Ej. {new_item.exercise}"
                        if completed
                        else f"Intento Ej. {new_item.exercise}",
                    )
                )
        else:
            new_item = TimerItem(
                section_type=self.location.section_type,
                section_number=self.location.section_number,
                exercise=self.location.exercise,
                inciso=self.location.inciso,
                exercise_time_ms=exercise_ms,
                break_time_ms=break_ms,
                completed=completed,
                comment=self.pending_comment,
                created_at=item_created_at,
            )
            self.record.items.append(new_item)
            self.undo_manager.push_executed(
                AddItemCommand(
                    self.record,
                    new_item,
                    description=f"Completar Ej. {new_item.exercise}"
                    if completed
                    else f"Intento Ej. {new_item.exercise}",
                )
            )

        self.discard_session_draft()
        self._mark_dirty()
        self.timer.reset()
        self.pending_comment = ""
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.session_started_at = None
        return True

    def save(self, force: bool = False) -> None:
        """Persiste los cambios pendientes en el archivo abierto."""
        if not self.is_record_open:
            return
        try:
            self.storage.save(self.record, force=force)
        except TypeError:
            self.storage.save(self.record)
        if self._is_dirty:
            self._is_dirty = False
            self._notify_dirty_changed()

    def has_external_modification(self) -> bool:
        """Indica si el archivo en disco ha sufrido cambios externos respecto a la versión en memoria."""
        if not self.is_record_open:
            return False
        if hasattr(self.storage, "has_external_modification"):
            return bool(self.storage.has_external_modification())
        return False

    def reload_from_disk(self) -> None:
        """Recarga el archivo activo desde disco descartando las modificaciones en memoria."""
        if not self.is_record_open or self.record_path is None:
            return
        self.record = self.storage.read(self.record_path)
        if hasattr(self.storage, "watcher") and self.storage.watcher:
            self.storage.watcher.update_snapshot()
        self.undo_manager.clear()
        if self._is_dirty:
            self._is_dirty = False
            self._notify_dirty_changed()

    def save_session_draft(self) -> bool:
        """Persiste un borrador de la sesión activa en curso para Crash Recovery."""
        if not self.is_record_open or not self.record_path:
            return False
        draft_mgr = getattr(self.storage, "draft_manager", None)
        if draft_mgr is None:
            return False
        if self.mode is TimerMode.WAITING and not self.editing_item_id:
            draft_mgr.discard_draft(self.record_path)
            return False

        exercise_ms, break_ms = self.timer.snapshot()
        loc = {
            "section_type": self.location.section_type,
            "section_number": self.location.section_number,
            "exercise": self.location.exercise,
            "inciso": self.location.inciso,
        }
        draft_mgr.save_draft(
            record_path=self.record_path,
            timer_mode=self.mode.value,
            is_paused=self.is_timer_paused,
            exercise_time_ms=exercise_ms,
            break_time_ms=break_ms,
            location=loc,
            comment=self.pending_comment,
            session_started_at=self.session_started_at.isoformat() if self.session_started_at else None,
            editing_item_id=self.editing_item_id,
        )
        return True

    def check_session_draft(self, record_path: Path | None = None) -> dict[str, Any] | None:
        """Comprueba si existe un borrador de sesión previa no guardada para el archivo."""
        target = record_path or self.record_path
        draft_mgr = getattr(self.storage, "draft_manager", None)
        if not target or draft_mgr is None:
            return None
        return draft_mgr.load_draft(target)

    def restore_session_draft(self, draft: dict[str, Any]) -> None:
        """Restaura el estado de cronómetro y ubicación desde un borrador de Crash Recovery."""
        loc = draft.get("location", {})
        self.location = SessionLocation(
            section_type=str(loc.get("section_type", "Guía")),
            section_number=int(loc.get("section_number", 1)),
            exercise=int(loc.get("exercise", 1)),
            inciso=loc.get("inciso"),
        )
        self.pending_comment = str(draft.get("comment", ""))
        self.editing_item_id = draft.get("editing_item_id")
        exercise_ms = int(draft.get("exercise_time_ms", 0))
        break_ms = int(draft.get("break_time_ms", 0))
        mode_str = str(draft.get("timer_mode", "PLAY"))
        is_paused = bool(draft.get("is_paused", False))
        started_iso = draft.get("session_started_at")
        if started_iso:
            try:
                self.session_started_at = datetime.fromisoformat(started_iso)
            except Exception:
                self.session_started_at = None

        self.timer.load_accumulated_times(exercise_ms, break_ms)
        if mode_str == "BREAK":
            self.timer.start()
            self.timer.toggle_break()
        elif mode_str == "PLAY":
            self.timer.start()
        if is_paused:
            self.timer.pause()

    def discard_session_draft(self, record_path: Path | None = None) -> None:
        """Elimina el borrador de sesión activa del disco."""
        target = record_path or self.record_path
        draft_mgr = getattr(self.storage, "draft_manager", None)
        if target and draft_mgr is not None:
            draft_mgr.discard_draft(target)

    def new_record(self, record_name: str | None = None, directory: Path | None = None) -> Path:
        """Crea un registro nuevo con un nombre único en el directorio especificado o estándar."""
        self.discard_session_draft()
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
                lock_mgr = getattr(self.storage, "lock_manager", None)
                if lock_mgr is not None:
                    lock_mgr.set_target(path)
                    lock_mgr.acquire(force=True)
                watcher = getattr(self.storage, "watcher", None)
                if watcher is not None:
                    watcher.set_path(path)
                self.undo_manager.clear()
                self.storage.save(self.record, path)
                if self._is_dirty:
                    self._is_dirty = False
                    self._notify_dirty_changed()
                return path
            candidate_name = f"{base_name}_{suffix}"
            suffix += 1

    def save_as(self, path: Path) -> None:
        self.storage.save(self.record, path)
        self.record.record_name = path.stem
        self.storage.path = path
        if self._is_dirty:
            self._is_dirty = False
            self._notify_dirty_changed()

    def load(self, path: Path, force_lock: bool = False) -> None:
        try:
            self.record = self.storage.load(path, force_lock=force_lock)
        except TypeError:
            self.record = self.storage.load(path)
        self.undo_manager.clear()
        if self._is_dirty:
            self._is_dirty = False
            self._notify_dirty_changed()
        if OrganizerService.migrate_legacy_comments_to_notes(self.record) > 0:
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
            new_item = TimerItem.from_dict(item_data)
            self.undo_manager.push_and_execute(AddItemCommand(self.record, new_item, description=f"Importar Ej. {new_item.exercise}"))

        if selected_items:
            self._mark_dirty()
        return len(selected_items)

    def rename(self, path: Path) -> None:
        if self.storage.path is None:
            raise ValueError("No hay un archivo activo")
        self.storage.path.rename(path)
        self.storage.path = path
        self.record.record_name = path.stem
        self.save()

    def close_record(self) -> None:
        self.discard_session_draft()
        if hasattr(self.storage, "close"):
            self.storage.close()
        else:
            self.storage.path = None
        self.record = Record(record_name="")
        self.undo_manager.clear()
        self.editing_item_id = None
        self.editing_initial_exercise_ms = 0
        self.timer.reset()
        self.pending_comment = ""
        if self._is_dirty:
            self._is_dirty = False
            self._notify_dirty_changed()


    def ordered_items(self) -> list[TimerItem]:
        return sorted(self.record.items, key=lambda item: item.created_at, reverse=True)

    def add_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(AddItemCommand(self.record, item))
        self._mark_dirty()

    def replace_item(self, current: TimerItem, replacement: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(ReplaceItemCommand(self.record, current, replacement))
        self._mark_dirty()

    def reset_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        old_copy = TimerItem(
            id=item.id,
            section_type=item.section_type,
            section_number=item.section_number,
            exercise=item.exercise,
            inciso=item.inciso,
            exercise_time_ms=item.exercise_time_ms,
            break_time_ms=item.break_time_ms,
            completed=item.completed,
            comment=item.comment,
            created_at=item.created_at,
        )
        item.exercise_time_ms = 0
        item.break_time_ms = 0
        self.undo_manager.push_executed(
            ReplaceItemCommand(self.record, old_copy, item, description=f"Reiniciar tiempos Ej. {item.exercise}")
        )
        self._mark_dirty()

    def update_comment(self, item: TimerItem, comment: str) -> None:
        """Actualiza el comentario de un item ya guardado."""
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(UpdateCommentCommand(item, comment))
        self._mark_dirty()

    def delete_item(self, item: TimerItem) -> None:
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(DeleteItemCommand(self.record, item))
        self._mark_dirty()

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
        self.undo_manager.push_and_execute(PromoteIncisoCommand(items, target_inciso))
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

    def get_organizer_overview(self) -> OrganizerOverview:
        """Calcula el resumen del universo organizado y estados de ejercicios."""
        return OrganizerService.compute_overview(self.record)

    def sync_organizer_with_records(self) -> bool:
        """Sincroniza la organización agregando ejercicios no organizados que existan en registros."""
        if not self.is_record_open:
            return False
        changed = OrganizerService.sync_organizer_with_records(self.record)
        if changed:
            self._mark_dirty()
        return changed

    def add_or_update_organized_section(self, section: OrganizedSection) -> None:
        """Añade o edita una sección en la organización y marca dirty."""
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(AddOrUpdateSectionCommand(self.record, section))
        self._mark_dirty()

    def delete_organized_section(self, section_type: str, section_number: int) -> bool:
        """Elimina una sección de la organización y marca dirty."""
        if not self.is_record_open:
            return False
        # Verificar que la sección existe antes de registrar el comando
        exists = any(
            s.section_type.strip().lower() == section_type.strip().lower() and s.section_number == section_number
            for s in self.record.organizer_sections
        )
        if not exists:
            return False
        self.undo_manager.push_and_execute(DeleteSectionCommand(self.record, section_type, section_number))
        self._mark_dirty()
        return True

    # Alias de compatibilidad
    get_planner_overview = get_organizer_overview
    sync_planner_with_records = sync_organizer_with_records
    add_or_update_planned_section = add_or_update_organized_section
    delete_planned_section = delete_organized_section

    def check_location_boundary(self, location: SessionLocation) -> tuple[bool, str]:
        """Comprueba si la ubicación indicada está dentro de la organización configurada."""
        return OrganizerService.is_location_within_organizer(
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
        return OrganizerService.get_tag_catalog(self.record)

    def add_tag_definition(self, name: str, color: str) -> TagDefinition | None:
        """Añade una nueva etiqueta al catálogo y persiste."""
        if not self.is_record_open:
            return None
        tag = OrganizerService.add_tag_definition(self.record, name, color)
        self._mark_dirty()
        return tag

    def update_tag_definition(self, tag_id: str, name: str, color: str) -> bool:
        """Actualiza una etiqueta en el catálogo y persiste."""
        if not self.is_record_open:
            return False
        updated = OrganizerService.update_tag_definition(self.record, tag_id, name, color)
        if updated:
            self._mark_dirty()
        return updated

    def delete_tag_definition(self, tag_id: str) -> bool:
        """Elimina una etiqueta del catálogo, limpia referencias y persiste."""
        if not self.is_record_open:
            return False
        deleted = OrganizerService.delete_tag_definition(self.record, tag_id)
        if deleted:
            self._mark_dirty()
        return deleted

    def get_exercise_tags(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None = None
    ) -> list[str]:
        """Devuelve los IDs de etiquetas asociadas a un ejercicio o inciso."""
        if not self.is_record_open:
            return []
        return OrganizerService.get_exercise_tags(
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
        self.undo_manager.push_and_execute(
            SetExerciseTagsCommand(self.record, section_type, section_number, exercise, inciso, tag_ids)
        )
        self._mark_dirty()

    def get_exercise_note(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None = None
    ) -> str:
        """Devuelve la nota asignada a un ejercicio o inciso."""
        if not self.is_record_open:
            return ""
        return OrganizerService.get_exercise_note(
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
        self.undo_manager.push_and_execute(
            SetExerciseNoteCommand(self.record, section_type, section_number, exercise, inciso, note)
        )
        loc = self.location
        if (
            loc.section_type.strip().lower() == section_type.strip().lower()
            and loc.section_number == section_number
            and loc.exercise == exercise
            and loc.inciso == inciso
        ):
            self.pending_comment = note.strip()
        self._mark_dirty()

    def get_schedule(self) -> OrganizerSchedule | None:
        """Devuelve la configuración del cronograma de cursada del registro activo."""
        if not self.is_record_open:
            return None
        return self.record.organizer_schedule

    def set_schedule(self, schedule: OrganizerSchedule | None) -> None:
        """Configura o actualiza el cronograma de cursada y persiste los cambios."""
        if not self.is_record_open:
            return
        self.undo_manager.push_and_execute(SetScheduleCommand(self.record, schedule))
        self._mark_dirty()

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
        for sec in self.record.organizer_sections:
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
        """Obtiene el ExerciseNodeStatus del organizador o lo construye al vuelo si no hay plan."""
        # 1. Si existe en el organizador, buscarlo
        overview = self.get_organizer_overview()
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

        # 2. Si no hay organización para esta sección/ejercicio, construirlo al vuelo con los datos reales
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
        organizer_sections = self.record.organizer_sections if self.is_record_open else []

        return export_items_to_csv(
            file_path=file_path,
            items=target_items,
            delimiter=delimiter,
            tag_catalog=tag_catalog,
            planner_sections=organizer_sections,
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

        overview = self.get_organizer_overview()
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