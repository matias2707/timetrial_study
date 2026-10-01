from __future__ import annotations

"""Pruebas unitarias para el sistema de Deshacer y Rehacer (Undo / Redo)."""

import unittest
from pathlib import Path

from application.application_service import StudyApplicationService
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
from domain.models import Milestone, OrganizedSection, OrganizerSchedule, Record, TimerItem


class MemoryStorage:
    def __init__(self) -> None:
        self.path = Path("memory.json")
        self.saved_records: list[Record] = []

    @property
    def is_open(self) -> bool:
        return self.path is not None

    def create_automatic(self) -> Record:
        return Record(record_name="memory")

    def save(self, record: Record, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
        self.saved_records.append(record)


class TestUndoRedoSystem(unittest.TestCase):
    """Verifica el funcionamiento determinista de UndoManager y los comandos reversibles."""

    def setUp(self) -> None:
        self.record = Record(record_name="test_record")
        self.manager = UndoManager(max_depth=5)

    def test_undo_manager_initial_state(self) -> None:
        self.assertFalse(self.manager.can_undo)
        self.assertFalse(self.manager.can_redo)
        self.assertEqual(self.manager.undo_description, "")
        self.assertEqual(self.manager.redo_description, "")
        self.assertIsNone(self.manager.undo())
        self.assertIsNone(self.manager.redo())

    def test_add_item_command_lifecycle(self) -> None:
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=1000,
            break_time_ms=0,
            completed=True,
        )
        cmd = AddItemCommand(self.record, item)
        self.manager.push_and_execute(cmd)

        self.assertEqual(len(self.record.items), 1)
        self.assertTrue(self.manager.can_undo)
        self.assertFalse(self.manager.can_redo)
        self.assertIn("1", self.manager.undo_description)

        # Deshacer
        undone = self.manager.undo()
        self.assertIs(undone, cmd)
        self.assertEqual(len(self.record.items), 0)
        self.assertFalse(self.manager.can_undo)
        self.assertTrue(self.manager.can_redo)

        # Rehacer
        redone = self.manager.redo()
        self.assertIs(redone, cmd)
        self.assertEqual(len(self.record.items), 1)
        self.assertTrue(self.manager.can_undo)
        self.assertFalse(self.manager.can_redo)

    def test_delete_item_command_preserves_exact_index_and_data(self) -> None:
        item1 = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=True)
        item2 = TimerItem(section_type="Guía", section_number=1, exercise=2, inciso=None, exercise_time_ms=2000, break_time_ms=0, completed=True)
        item3 = TimerItem(section_type="Guía", section_number=1, exercise=3, inciso=None, exercise_time_ms=3000, break_time_ms=0, completed=True)
        self.record.items.extend([item1, item2, item3])

        cmd = DeleteItemCommand(self.record, item2)
        self.manager.push_and_execute(cmd)

        self.assertEqual(len(self.record.items), 2)
        self.assertEqual(self.record.items[0].exercise, 1)
        self.assertEqual(self.record.items[1].exercise, 3)

        # Deshacer restaura en la posición exacta (índice 1)
        self.manager.undo()
        self.assertEqual(len(self.record.items), 3)
        self.assertEqual(self.record.items[1].exercise, 2)
        self.assertEqual(self.record.items[1].id, item2.id)

        # Rehacer vuelve a eliminarlo
        self.manager.redo()
        self.assertEqual(len(self.record.items), 2)
        self.assertEqual(self.record.items[0].exercise, 1)
        self.assertEqual(self.record.items[1].exercise, 3)

    def test_replace_item_command(self) -> None:
        item = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=False)
        self.record.items.append(item)

        replacement = TimerItem(
            id=item.id,
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=5000,
            break_time_ms=500,
            completed=True,
            comment="Completado",
        )
        cmd = ReplaceItemCommand(self.record, item, replacement)
        self.manager.push_and_execute(cmd)

        self.assertEqual(self.record.items[0].exercise_time_ms, 5000)
        self.assertTrue(self.record.items[0].completed)

        self.manager.undo()
        self.assertEqual(self.record.items[0].exercise_time_ms, 1000)
        self.assertFalse(self.record.items[0].completed)

        self.manager.redo()
        self.assertEqual(self.record.items[0].exercise_time_ms, 5000)
        self.assertTrue(self.record.items[0].completed)

    def test_update_comment_command(self) -> None:
        item = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=True, comment="Viejo")
        cmd = UpdateCommentCommand(item, "Nuevo comentario")
        self.manager.push_and_execute(cmd)

        self.assertEqual(item.comment, "Nuevo comentario")
        self.manager.undo()
        self.assertEqual(item.comment, "Viejo")
        self.manager.redo()
        self.assertEqual(item.comment, "Nuevo comentario")

    def test_promote_inciso_command(self) -> None:
        item1 = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=True)
        item2 = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=2000, break_time_ms=0, completed=True)
        cmd = PromoteIncisoCommand([item1, item2], 1)
        self.manager.push_and_execute(cmd)

        self.assertEqual(item1.inciso, 1)
        self.assertEqual(item2.inciso, 1)

        self.manager.undo()
        self.assertIsNone(item1.inciso)
        self.assertIsNone(item2.inciso)

        self.manager.redo()
        self.assertEqual(item1.inciso, 1)
        self.assertEqual(item2.inciso, 1)

    def test_add_and_delete_section_commands(self) -> None:
        sec = OrganizedSection(section_type="Guía", section_number=2, total_exercises=15, title="Matrices")
        add_cmd = AddOrUpdateSectionCommand(self.record, sec)
        self.manager.push_and_execute(add_cmd)

        self.assertEqual(len(self.record.organizer_sections), 1)
        self.assertEqual(self.record.organizer_sections[0].title, "Matrices")

        del_cmd = DeleteSectionCommand(self.record, "Guía", 2)
        self.manager.push_and_execute(del_cmd)
        self.assertEqual(len(self.record.organizer_sections), 0)

        # Deshacer eliminación restaura la sección
        self.manager.undo()
        self.assertEqual(len(self.record.organizer_sections), 1)
        self.assertEqual(self.record.organizer_sections[0].title, "Matrices")

        # Deshacer creación la remueve
        self.manager.undo()
        self.assertEqual(len(self.record.organizer_sections), 0)

    def test_exercise_notes_and_tags_commands(self) -> None:
        sec = OrganizedSection(section_type="Guía", section_number=1, total_exercises=5)
        self.record.organizer_sections.append(sec)

        note_cmd = SetExerciseNoteCommand(self.record, "Guía", 1, 3, None, "Nota importante de cálculo")
        self.manager.push_and_execute(note_cmd)
        self.assertEqual(sec.exercise_notes.get("3"), "Nota importante de cálculo")

        self.manager.undo()
        self.assertEqual(sec.exercise_notes.get("3", ""), "")

        self.manager.redo()
        self.assertEqual(sec.exercise_notes.get("3"), "Nota importante de cálculo")

        tags_cmd = SetExerciseTagsCommand(self.record, "Guía", 1, 3, None, ["tag-redo", "tag-key"])
        self.manager.push_and_execute(tags_cmd)
        self.assertEqual(sec.exercise_tags.get("3"), ["tag-redo", "tag-key"])

        self.manager.undo()
        self.assertEqual(sec.exercise_tags.get("3", []), [])

    def test_schedule_command(self) -> None:
        sched = OrganizerSchedule(
            period_type="Cuatrimestral",
            start_date="2026-08-01",
            end_date="2026-12-01",
            milestones=[Milestone(name="Parcial 1", date="2026-10-15")],
        )
        cmd = SetScheduleCommand(self.record, sched)
        self.manager.push_and_execute(cmd)
        self.assertIsNotNone(self.record.organizer_schedule)
        self.assertEqual(len(self.record.organizer_schedule.milestones), 1)

        self.manager.undo()
        self.assertIsNone(self.record.organizer_schedule)

        self.manager.redo()
        self.assertIsNotNone(self.record.organizer_schedule)

    def test_max_depth_truncation(self) -> None:
        for i in range(10):
            item = TimerItem(section_type="Guía", section_number=1, exercise=i, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=True)
            self.manager.push_and_execute(AddItemCommand(self.record, item))

        # Max depth is 5, so only 5 items in undo stack
        self.assertEqual(len(self.manager._undo_stack), 5)


class TestApplicationServiceUndoIntegration(unittest.TestCase):
    """Verifica la integración fluida de UndoManager en StudyApplicationService."""

    def setUp(self) -> None:
        self.storage = MemoryStorage()
        self.app = StudyApplicationService(storage=self.storage)

    def test_app_service_delete_item_and_undo(self) -> None:
        item = TimerItem(section_type="Guía", section_number=1, exercise=5, inciso=None, exercise_time_ms=12000, break_time_ms=0, completed=True)
        self.app.add_item(item)
        self.assertEqual(len(self.app.record.items), 1)

        self.app.delete_item(item)
        self.assertEqual(len(self.app.record.items), 0)
        self.assertTrue(self.app.can_undo)

        self.assertTrue(self.app.undo())
        self.assertEqual(len(self.app.record.items), 1)
        self.assertEqual(self.app.record.items[0].id, item.id)

        self.assertTrue(self.app.redo())
        self.assertEqual(len(self.app.record.items), 0)

    def test_app_service_notes_and_undo(self) -> None:
        sec = OrganizedSection(section_type="Guía", section_number=1, total_exercises=10)
        self.app.add_or_update_organized_section(sec)

        self.app.set_exercise_note("Guía", 1, 2, None, "Nota inicial")
        self.assertEqual(self.app.get_exercise_note("Guía", 1, 2, None), "Nota inicial")

        self.assertTrue(self.app.undo())
        self.assertEqual(self.app.get_exercise_note("Guía", 1, 2, None), "")

        self.assertTrue(self.app.redo())
        self.assertEqual(self.app.get_exercise_note("Guía", 1, 2, None), "Nota inicial")

    def test_app_service_finish_item_and_undo(self) -> None:
        self.app.toggle_session()  # Iniciar sesión
        self.app.timer.exercise_time_ms = 45000
        self.app.finish_item(completed=True)

        self.assertEqual(len(self.app.record.items), 1)
        self.assertTrue(self.app.can_undo)
        self.assertIn("Completar", self.app.undo_description)

        self.assertTrue(self.app.undo())
        self.assertEqual(len(self.app.record.items), 0)

        self.assertTrue(self.app.redo())
        self.assertEqual(len(self.app.record.items), 1)

    def test_close_record_clears_undo_stack(self) -> None:
        item = TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=1000, break_time_ms=0, completed=True)
        self.app.add_item(item)
        self.assertTrue(self.app.can_undo)

        self.app.close_record()
        self.assertFalse(self.app.can_undo)
        self.assertFalse(self.app.can_redo)


if __name__ == "__main__":
    unittest.main()
