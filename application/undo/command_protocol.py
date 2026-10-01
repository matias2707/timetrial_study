from __future__ import annotations

"""Protocolo abstracto para comandos reversibles."""

from typing import Protocol


class ICommand(Protocol):
    """Contrato base para todo comando ejecutable y reversible."""

    @property
    def description(self) -> str:
        """Descripción legible en lenguaje natural de la acción realizada."""
        ...

    def execute(self) -> None:
        """Aplica la modificación sobre el estado."""
        ...

    def undo(self) -> None:
        """Revierte la modificación exacta, restaurando el estado previo."""
        ...

    def redo(self) -> None:
        """Vuelve a aplicar la modificación revertida."""
        ...
