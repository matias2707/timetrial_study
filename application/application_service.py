"""Casos de uso y estado de sesion, independientes de PySide6.

Este modulo coordina dominio e infraestructura mediante dependencias
inyectables. La interfaz solo traduce eventos y muestra sus resultados.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass
from pathlib import Path

from application.planner_service import PlannerOverview, PlannerService
from application.statistics_service import (
    RecordStatistics,
    compute_statistics,
    compute_today_study_time_ms,
    get_24h_hourly_distribution,
    get_course_heatmap_data,
    get_top_effort_exercises,
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