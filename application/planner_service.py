"""Servicio de planificación y análisis del universo de ejercicios.

Gestiona las secciones planificadas, la sincronización automática con los registros,
el cálculo de estados (hecho, fallado, pendiente) para cada ejercicio e inciso,
y la verificación de límites de navegación.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models import PlannedSection, Record, TimerItem

STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_PENDING = "pending"


@dataclass
class ExerciseNodeStatus:
    """Estado y métricas de un ejercicio o inciso planificado."""

    section_type: str
    section_number: int
    exercise: int
    inciso: int | None = None
    status: str = STATUS_PENDING
    attempts: int = 0
    failed_attempts: int = 0
    completed_attempts: int = 0
    exercise_time_ms: int = 0
    break_time_ms: int = 0
    comments: list[str] = field(default_factory=list)
    latest_comment: str = ""
    has_incisos: bool = False
    incisos: list[ExerciseNodeStatus] = field(default_factory=list)

    @property
    def total_time_ms(self) -> int:
        return self.exercise_time_ms + self.break_time_ms

    @property
    def display_label(self) -> str:
        if self.inciso is not None:
            return f"{self.exercise}.{self.inciso}"
        return str(self.exercise)

    @property
    def full_label(self) -> str:
        if self.inciso is not None:
            return f"{self.section_type} {self.section_number} · Ej. {self.exercise}.{self.inciso}"
        return f"{self.section_type} {self.section_number} · Ejercicio {self.exercise}"


@dataclass
class PlannedSectionStatus:
    """Métricas y cuadrícula de ejercicios para una sección planificada."""

    section: PlannedSection
    total_units: int = 0
    completed_units: int = 0
    failed_units: int = 0
    pending_units: int = 0
    completed_weight: float = 0.0
    total_exercise_time_ms: int = 0
    total_break_time_ms: int = 0
    exercise_nodes: list[ExerciseNodeStatus] = field(default_factory=list)

    @property
    def total_time_ms(self) -> int:
        return self.total_exercise_time_ms + self.total_break_time_ms

    @property
    def completion_percentage(self) -> float:
        if self.total_units == 0:
            return 0.0
        return (self.completed_weight / self.total_units) * 100.0

    @property
    def completed_display(self) -> str:
        """Representación amigable del progreso completado (ej: '2' o '1.5')."""
        if self.completed_weight.is_integer():
            return str(int(self.completed_weight))
        return f"{self.completed_weight:.1f}".rstrip("0").rstrip(".")


@dataclass
class PlannerOverview:
    """Panorama general de todo el universo de ejercicios planificados."""

    sections: list[PlannedSectionStatus] = field(default_factory=list)
    total_units: int = 0
    completed_units: int = 0
    failed_units: int = 0
    pending_units: int = 0
    completed_weight: float = 0.0

    @property
    def global_completion_percentage(self) -> float:
        if self.total_units == 0:
            return 0.0
        return (self.completed_weight / self.total_units) * 100.0

    @property
    def completed_display(self) -> str:
        """Representación amigable del total completado global."""
        if self.completed_weight.is_integer():
            return str(int(self.completed_weight))
        return f"{self.completed_weight:.1f}".rstrip("0").rstrip(".")


class PlannerService:
    """Coordina el universo planificado y cruza los intentos registrados."""

    @staticmethod
    def sync_planner_with_records(record: Record) -> bool:
        """Incorpora automáticamente en la planificación los ejercicios de items no contemplados.

        Devuelve True si se modificó alguna sección de la planificación.
        """
        modified = False
        # Mapeo de (section_type, section_number) a la sección planificada
        sections_map = {
            (s.section_type, s.section_number): s for s in record.planner_sections
        }

        for item in record.items:
            key = (item.section_type, item.section_number)
            if key not in sections_map:
                new_sec = PlannedSection(
                    section_type=item.section_type,
                    section_number=item.section_number,
                    total_exercises=max(1, item.exercise),
                )
                if item.inciso is not None and item.inciso > 0:
                    new_sec.set_incisos_count(item.exercise, item.inciso)
                record.planner_sections.append(new_sec)
                sections_map[key] = new_sec
                modified = True
            else:
                sec = sections_map[key]
                if item.exercise > sec.total_exercises:
                    sec.total_exercises = item.exercise
                    modified = True
                if item.inciso is not None and item.inciso > 0:
                    current_inc = sec.get_incisos_count(item.exercise)
                    if item.inciso > current_inc:
                        sec.set_incisos_count(item.exercise, item.inciso)
                        modified = True

        return modified

    @staticmethod
    def is_location_within_plan(
        record: Record,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
    ) -> tuple[bool, str]:
        """Verifica si una ubicación de sesión está dentro de los rangos configurados.

        Devuelve (True, "") si está dentro de rango o si no hay planificación definida.
        Devuelve (False, mensaje_detalle) si excede la planificación.
        """
        if not record.planner_sections:
            return True, ""

        matched = [
            s
            for s in record.planner_sections
            if s.section_type.strip().lower() == section_type.strip().lower()
            and s.section_number == section_number
        ]
        if not matched:
            return False, f"La sección '{section_type} {section_number}' no forma parte de la planificación configurada."

        sec = matched[0]
        if exercise > sec.total_exercises:
            return (
                False,
                f"El Ejercicio {exercise} supera los {sec.total_exercises} ejercicios planificados para {section_type} {section_number}.",
            )

        configured_incisos = sec.get_incisos_count(exercise)
        if inciso is not None and inciso > 0:
            if configured_incisos == 0:
                return (
                    False,
                    f"El Ejercicio {exercise} de {section_type} {section_number} no tiene incisos configurados.",
                )
            if inciso > configured_incisos:
                return (
                    False,
                    f"El Inciso {inciso} supera los {configured_incisos} incisos configurados para el Ejercicio {exercise}.",
                )

        return True, ""

    @classmethod
    def compute_overview(cls, record: Record) -> PlannerOverview:
        """Calcula el estado visual de cada sección y el resumen global del universo planificado."""
        # Agrupar items por clave: (section_type, section_number, exercise, inciso)
        item_groups: dict[tuple[str, int, int, int | None], list[TimerItem]] = {}
        for it in record.items:
            # Normalizar tipo
            norm_type = it.section_type.strip()
            key = (norm_type, it.section_number, it.exercise, it.inciso)
            item_groups.setdefault(key, []).append(it)

        # Ordenar secciones por tipo y número
        sorted_sections = sorted(
            record.planner_sections, key=lambda s: (s.section_type, s.section_number)
        )

        overview_sections: list[PlannedSectionStatus] = []
        global_total_units = 0
        global_completed_units = 0
        global_completed_weight = 0.0
        global_failed_units = 0
        global_pending_units = 0

        for sec in sorted_sections:
            sec_type = sec.section_type.strip()
            nodes: list[ExerciseNodeStatus] = []
            sec_units = sec.total_exercises
            sec_completed_weight = 0.0
            sec_completed_full = 0
            sec_failed = 0
            sec_pending = 0
            sec_ex_time = 0
            sec_br_time = 0

            for ex_num in range(1, sec.total_exercises + 1):
                incisos_count = sec.get_incisos_count(ex_num)
                if incisos_count > 0:
                    # Ejercicio compuesto de incisos: 1..incisos_count
                    sub_nodes: list[ExerciseNodeStatus] = []
                    sub_completed_count = 0
                    sub_failed_count = 0
                    sub_pending_count = 0
                    node_ex_time = 0
                    node_br_time = 0
                    node_attempts = 0
                    node_failed_attempts = 0
                    node_completed_attempts = 0
                    node_comments: list[str] = []

                    for inc_num in range(1, incisos_count + 1):
                        sub_items = item_groups.get((sec_type, sec.section_number, ex_num, inc_num), [])
                        # También considerar si hubo intentos sin especificar inciso
                        if not sub_items and inc_num == 1:
                            sub_items = item_groups.get((sec_type, sec.section_number, ex_num, None), [])

                        sub_node = cls._build_node(
                            sec_type, sec.section_number, ex_num, inc_num, sub_items
                        )
                        sub_nodes.append(sub_node)

                        node_ex_time += sub_node.exercise_time_ms
                        node_br_time += sub_node.break_time_ms
                        node_attempts += sub_node.attempts
                        node_failed_attempts += sub_node.failed_attempts
                        node_completed_attempts += sub_node.completed_attempts
                        if sub_node.comments:
                            node_comments.extend(sub_node.comments)

                        if sub_node.status == STATUS_COMPLETED:
                            sub_completed_count += 1
                        elif sub_node.status == STATUS_FAILED:
                            sub_failed_count += 1
                        else:
                            sub_pending_count += 1

                    # Ponderación del ejercicio: el ejercicio completo pesa 1 unidad
                    # Cada inciso aporta 1.0 / incisos_count a su avance
                    sec_completed_weight += sub_completed_count / incisos_count

                    # Estado del ejercicio padre:
                    if sub_completed_count == incisos_count:
                        parent_status = STATUS_COMPLETED
                        sec_completed_full += 1
                    elif sub_failed_count > 0 or (node_attempts > 0 and sub_completed_count < incisos_count):
                        parent_status = STATUS_FAILED
                        sec_failed += 1
                    else:
                        parent_status = STATUS_PENDING
                        sec_pending += 1

                    parent_node = ExerciseNodeStatus(
                        section_type=sec_type,
                        section_number=sec.section_number,
                        exercise=ex_num,
                        inciso=None,
                        status=parent_status,
                        attempts=node_attempts,
                        failed_attempts=node_failed_attempts,
                        completed_attempts=node_completed_attempts,
                        exercise_time_ms=node_ex_time,
                        break_time_ms=node_br_time,
                        comments=node_comments,
                        latest_comment=node_comments[-1] if node_comments else "",
                        has_incisos=True,
                        incisos=sub_nodes,
                    )
                    nodes.append(parent_node)
                    sec_ex_time += node_ex_time
                    sec_br_time += node_br_time
                else:
                    # Ejercicio simple sin incisos
                    ex_items = item_groups.get((sec_type, sec.section_number, ex_num, None), [])
                    # O tal vez items con inciso 1 guardados previamente
                    if not ex_items:
                        ex_items = item_groups.get((sec_type, sec.section_number, ex_num, 1), [])

                    single_node = cls._build_node(
                        sec_type, sec.section_number, ex_num, None, ex_items
                    )
                    nodes.append(single_node)

                    sec_ex_time += single_node.exercise_time_ms
                    sec_br_time += single_node.break_time_ms

                    if single_node.status == STATUS_COMPLETED:
                        sec_completed_weight += 1.0
                        sec_completed_full += 1
                    elif single_node.status == STATUS_FAILED:
                        sec_failed += 1
                    else:
                        sec_pending += 1

            sec_status = PlannedSectionStatus(
                section=sec,
                total_units=sec_units,
                completed_units=sec_completed_full,
                completed_weight=sec_completed_weight,
                failed_units=sec_failed,
                pending_units=sec_pending,
                total_exercise_time_ms=sec_ex_time,
                total_break_time_ms=sec_br_time,
                exercise_nodes=nodes,
            )
            overview_sections.append(sec_status)

            global_total_units += sec_units
            global_completed_units += sec_completed_full
            global_completed_weight += sec_completed_weight
            global_failed_units += sec_failed
            global_pending_units += sec_pending

        return PlannerOverview(
            sections=overview_sections,
            total_units=global_total_units,
            completed_units=global_completed_units,
            completed_weight=global_completed_weight,
            failed_units=global_failed_units,
            pending_units=global_pending_units,
        )

    @staticmethod
    def _build_node(
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        items: list[TimerItem],
    ) -> ExerciseNodeStatus:
        attempts = len(items)
        if attempts == 0:
            return ExerciseNodeStatus(
                section_type=section_type,
                section_number=section_number,
                exercise=exercise,
                inciso=inciso,
                status=STATUS_PENDING,
            )

        completed_count = sum(1 for it in items if it.completed)
        failed_count = attempts - completed_count
        ex_time = sum(it.exercise_time_ms for it in items)
        br_time = sum(it.break_time_ms for it in items)
        comments = [it.comment.strip() for it in items if it.comment.strip()]
        latest_comment = comments[-1] if comments else ""

        if completed_count > 0:
            status = STATUS_COMPLETED
        else:
            status = STATUS_FAILED

        return ExerciseNodeStatus(
            section_type=section_type,
            section_number=section_number,
            exercise=exercise,
            inciso=inciso,
            status=status,
            attempts=attempts,
            failed_attempts=failed_count,
            completed_attempts=completed_count,
            exercise_time_ms=ex_time,
            break_time_ms=br_time,
            comments=comments,
            latest_comment=latest_comment,
            has_incisos=False,
            incisos=[],
        )

    @classmethod
    def add_or_update_section(cls, record: Record, section: PlannedSection) -> None:
        """Añade o reemplaza una sección planificada por su tipo y número."""
        existing_index = -1
        for i, s in enumerate(record.planner_sections):
            if (
                s.section_type.strip().lower() == section.section_type.strip().lower()
                and s.section_number == section.section_number
            ):
                existing_index = i
                break

        if existing_index >= 0:
            record.planner_sections[existing_index] = section
        else:
            record.planner_sections.append(section)

    @classmethod
    def delete_section(cls, record: Record, section_type: str, section_number: int) -> bool:
        """Elimina una sección planificada de la lista sin tocar los registros de items."""
        initial_len = len(record.planner_sections)
        record.planner_sections = [
            s
            for s in record.planner_sections
            if not (
                s.section_type.strip().lower() == section_type.strip().lower()
                and s.section_number == section_number
            )
        ]
        return len(record.planner_sections) < initial_len
