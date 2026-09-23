"""Entidades, reglas de dominio y excepciones canónicas independientes de Qt."""

from domain.exceptions import (
    BoundaryExceededError,
    InvalidSectionError,
    MilestoneDateError,
    RecordCorruptedError,
    RecordError,
    RecordNotFoundError,
    RecordValidationError,
    StudyTimetrialError,
    TimerConflictError,
    TimerDomainError,
)

__all__ = [
    "StudyTimetrialError",
    "RecordError",
    "RecordCorruptedError",
    "RecordNotFoundError",
    "RecordValidationError",
    "TimerDomainError",
    "TimerConflictError",
    "BoundaryExceededError",
    "InvalidSectionError",
    "MilestoneDateError",
]
