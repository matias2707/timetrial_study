from __future__ import annotations

"""Gestor de pila de Deshacer y Rehacer (Undo / Redo) en memoria."""

from typing import Callable

from application.undo.command_protocol import ICommand


class UndoManager:
    """Gestiona las pilas de Deshacer y Rehacer con límite de profundidad."""

    def __init__(self, max_depth: int = 50) -> None:
        self.max_depth = max_depth
        self._undo_stack: list[ICommand] = []
        self._redo_stack: list[ICommand] = []
        self.on_stack_changed: list[Callable[[], None]] = []

    @property
    def can_undo(self) -> bool:
        """Indica si hay al menos una acción disponible para deshacer."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Indica si hay al menos una acción disponible para rehacer."""
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """Texto descriptivo de la acción al tope de la pila de deshacer."""
        return self._undo_stack[-1].description if self._undo_stack else ""

    @property
    def redo_description(self) -> str:
        """Texto descriptivo de la acción al tope de la pila de rehacer."""
        return self._redo_stack[-1].description if self._redo_stack else ""

    def push_and_execute(self, command: ICommand) -> None:
        """Ejecuta el comando, lo agrega a la pila de deshacer y limpia la de rehacer."""
        command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify_changed()

    def push_executed(self, command: ICommand) -> None:
        """Registra un comando cuya ejecución ya ocurrió previamente."""
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify_changed()

    def undo(self) -> ICommand | None:
        """Revierte la última acción ejecutada."""
        if not self.can_undo:
            return None
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._notify_changed()
        return command

    def redo(self) -> ICommand | None:
        """Reaplica la última acción deshecha."""
        if not self.can_redo:
            return None
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        self._notify_changed()
        return command

    def clear(self) -> None:
        """Vacía las pilas de historial."""
        if self._undo_stack or self._redo_stack:
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._notify_changed()

    def _notify_changed(self) -> None:
        for callback in self.on_stack_changed:
            try:
                callback()
            except Exception:
                pass
