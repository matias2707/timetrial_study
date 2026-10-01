"""Módulo de gestión de Deshacer y Rehacer (Undo / Redo) con Command Pattern."""

from application.undo.command_protocol import ICommand
from application.undo.commands import (
    AddItemCommand,
    AddOrUpdateSectionCommand,
    DeleteItemCommand,
    DeleteSectionCommand,
    PromoteIncisoCommand,
    ReplaceItemCommand,
    SetExerciseNoteCommand,
    SetExerciseTagsCommand,
    SetScheduleCommand,
    UpdateCommentCommand,
)
from application.undo.undo_manager import UndoManager

__all__ = [
    "ICommand",
    "UndoManager",
    "AddItemCommand",
    "DeleteItemCommand",
    "ReplaceItemCommand",
    "UpdateCommentCommand",
    "PromoteIncisoCommand",
    "AddOrUpdateSectionCommand",
    "DeleteSectionCommand",
    "SetExerciseNoteCommand",
    "SetExerciseTagsCommand",
    "SetScheduleCommand",
]
