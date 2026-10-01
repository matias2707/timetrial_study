from __future__ import annotations

"""Catálogo de comandos reversibles para el estado del registro de estudio."""

import copy
from typing import Sequence

from application.organizer_service import OrganizerService
from domain.models import OrganizedSection, OrganizerSchedule, Record, TimerItem


class AddItemCommand:
    """Agrega un nuevo TimerItem al registro de estudio."""

    def __init__(self, record: Record, item: TimerItem, description: str = "") -> None:
        self.record = record
        self.item = item
        self._description = description or f"Registrar intento Ej. {item.exercise}" + (
            f".{item.inciso}" if item.inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        if self.item not in self.record.items:
            self.record.items.append(self.item)

    def undo(self) -> None:
        if self.item in self.record.items:
            self.record.items.remove(self.item)

    def redo(self) -> None:
        self.execute()


class DeleteItemCommand:
    """Elimina un TimerItem del registro, preservando su índice exacto al deshacer."""

    def __init__(self, record: Record, item: TimerItem, description: str = "") -> None:
        self.record = record
        self.item = item
        self.index: int = record.items.index(item) if item in record.items else -1
        self._description = description or f"Eliminar intento Ej. {item.exercise}" + (
            f".{item.inciso}" if item.inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        if self.item in self.record.items:
            self.index = self.record.items.index(self.item)
            self.record.items.remove(self.item)

    def undo(self) -> None:
        if self.item not in self.record.items:
            if 0 <= self.index <= len(self.record.items):
                self.record.items.insert(self.index, self.item)
            else:
                self.record.items.append(self.item)

    def redo(self) -> None:
        self.execute()


class ReplaceItemCommand:
    """Reemplaza un TimerItem por una versión modificada."""

    def __init__(
        self,
        record: Record,
        current: TimerItem,
        replacement: TimerItem,
        description: str = "",
    ) -> None:
        self.record = record
        self.current = current
        self.replacement = replacement
        self._description = description or f"Modificar intento Ej. {replacement.exercise}" + (
            f".{replacement.inciso}" if replacement.inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        if self.current in self.record.items:
            idx = self.record.items.index(self.current)
            self.record.items[idx] = self.replacement

    def undo(self) -> None:
        if self.replacement in self.record.items:
            idx = self.record.items.index(self.replacement)
            self.record.items[idx] = self.current

    def redo(self) -> None:
        self.execute()


class UpdateCommentCommand:
    """Actualiza el comentario de un TimerItem existente."""

    def __init__(self, item: TimerItem, new_comment: str, description: str = "") -> None:
        self.item = item
        self.old_comment = item.comment
        self.new_comment = new_comment.strip()
        self._description = description or f"Editar comentario Ej. {item.exercise}" + (
            f".{item.inciso}" if item.inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        self.item.comment = self.new_comment

    def undo(self) -> None:
        self.item.comment = self.old_comment

    def redo(self) -> None:
        self.execute()


class PromoteIncisoCommand:
    """Asigna un inciso unificado a un conjunto de TimerItems."""

    def __init__(self, items: Sequence[TimerItem], target_inciso: int, description: str = "") -> None:
        self.items = list(items)
        self.old_incisos = [it.inciso for it in self.items]
        self.target_inciso = target_inciso
        self._description = description or f"Asignar inciso {target_inciso}"

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        for it in self.items:
            it.inciso = self.target_inciso

    def undo(self) -> None:
        for it, old_inc in zip(self.items, self.old_incisos):
            it.inciso = old_inc

    def redo(self) -> None:
        self.execute()


class AddOrUpdateSectionCommand:
    """Añade o edita una sección en la organización curricular."""

    def __init__(self, record: Record, new_section: OrganizedSection, description: str = "") -> None:
        self.record = record
        self.new_section = copy.deepcopy(new_section)
        self.old_section: OrganizedSection | None = None
        for s in record.organizer_sections:
            if (
                s.section_type.strip().lower() == new_section.section_type.strip().lower()
                and s.section_number == new_section.section_number
            ):
                self.old_section = copy.deepcopy(s)
                break
        action_verb = "Editar" if self.old_section else "Crear"
        self._description = description or f"{action_verb} sección {new_section.section_type} {new_section.section_number}"

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        OrganizerService.add_or_update_section(self.record, copy.deepcopy(self.new_section))

    def undo(self) -> None:
        if self.old_section is not None:
            OrganizerService.add_or_update_section(self.record, copy.deepcopy(self.old_section))
        else:
            OrganizerService.delete_section(
                self.record, self.new_section.section_type, self.new_section.section_number
            )

    def redo(self) -> None:
        self.execute()


class DeleteSectionCommand:
    """Elimina una sección del organizador curricular conservando su contenido para undo."""

    def __init__(self, record: Record, section_type: str, section_number: int, description: str = "") -> None:
        self.record = record
        self.section_type = section_type
        self.section_number = section_number
        self.old_section: OrganizedSection | None = None
        for s in record.organizer_sections:
            if (
                s.section_type.strip().lower() == section_type.strip().lower()
                and s.section_number == section_number
            ):
                self.old_section = copy.deepcopy(s)
                break
        self._description = description or f"Eliminar sección {section_type} {section_number}"

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        OrganizerService.delete_section(self.record, self.section_type, self.section_number)

    def undo(self) -> None:
        if self.old_section is not None:
            OrganizerService.add_or_update_section(self.record, copy.deepcopy(self.old_section))

    def redo(self) -> None:
        self.execute()


class SetExerciseNoteCommand:
    """Asigna o modifica la nota de un ejercicio o inciso."""

    def __init__(
        self,
        record: Record,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        new_note: str,
        description: str = "",
    ) -> None:
        self.record = record
        self.section_type = section_type
        self.section_number = section_number
        self.exercise = exercise
        self.inciso = inciso
        self.old_note = OrganizerService.get_exercise_note(
            record, section_type, section_number, exercise, inciso
        )
        self.new_note = new_note
        self._description = description or f"Editar apunte Ej. {exercise}" + (
            f".{inciso}" if inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        OrganizerService.set_exercise_note(
            self.record,
            self.section_type,
            self.section_number,
            self.exercise,
            self.inciso,
            self.new_note,
        )

    def undo(self) -> None:
        OrganizerService.set_exercise_note(
            self.record,
            self.section_type,
            self.section_number,
            self.exercise,
            self.inciso,
            self.old_note,
        )

    def redo(self) -> None:
        self.execute()


class SetExerciseTagsCommand:
    """Asigna o modifica las etiquetas de un ejercicio o inciso."""

    def __init__(
        self,
        record: Record,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        new_tags: Sequence[str],
        description: str = "",
    ) -> None:
        self.record = record
        self.section_type = section_type
        self.section_number = section_number
        self.exercise = exercise
        self.inciso = inciso
        self.old_tags = list(
            OrganizerService.get_exercise_tags(
                record, section_type, section_number, exercise, inciso
            )
        )
        self.new_tags = list(new_tags)
        self._description = description or f"Modificar etiquetas Ej. {exercise}" + (
            f".{inciso}" if inciso else ""
        )

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        OrganizerService.set_exercise_tags(
            self.record,
            self.section_type,
            self.section_number,
            self.exercise,
            self.inciso,
            self.new_tags,
        )

    def undo(self) -> None:
        OrganizerService.set_exercise_tags(
            self.record,
            self.section_type,
            self.section_number,
            self.exercise,
            self.inciso,
            self.old_tags,
        )

    def redo(self) -> None:
        self.execute()


class SetScheduleCommand:
    """Asigna o actualiza el cronograma de cursada e hitos evaluativos."""

    def __init__(
        self,
        record: Record,
        new_schedule: OrganizerSchedule | None,
        description: str = "",
    ) -> None:
        self.record = record
        self.old_schedule = copy.deepcopy(record.organizer_schedule) if record.organizer_schedule else None
        self.new_schedule = copy.deepcopy(new_schedule) if new_schedule else None
        self._description = description or "Modificar cronograma de cursada"

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        self.record.organizer_schedule = copy.deepcopy(self.new_schedule)

    def undo(self) -> None:
        self.record.organizer_schedule = copy.deepcopy(self.old_schedule)

    def redo(self) -> None:
        self.execute()
