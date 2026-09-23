"""Jerarquía canónica de excepciones de dominio de Study Timetrial.

Define los errores semánticos independientes de la infraestructura y de los frameworks de UI.
"""

from __future__ import annotations


class StudyTimetrialError(Exception):
    """Excepción base para todos los errores de dominio de Study Timetrial."""

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" if self.message else self.code


# --- Errores relacionados con Registros (Records & Items) ---


class RecordError(StudyTimetrialError):
    """Excepción base para operaciones fallidas sobre registros de estudio."""


class RecordCorruptedError(RecordError):
    """Se lanza cuando un registro contiene datos malformados o no supera la validación estructural."""


class RecordNotFoundError(RecordError):
    """Se lanza cuando se intenta acceder a un registro o ítem inexistente."""


class RecordValidationError(RecordError):
    """Se lanza cuando los valores de una sesión o ítem violan invariantes del modelo."""


# --- Errores relacionados con el Cronómetro (Timer Engine) ---


class TimerDomainError(StudyTimetrialError):
    """Excepción base para anomalías en la máquina de estados o cálculo del cronómetro."""


class TimerConflictError(TimerDomainError):
    """Se lanza ante una transición de estado ilegal en el cronómetro (ej. pausar estando detenido)."""


class BoundaryExceededError(TimerDomainError):
    """Se lanza cuando un valor temporal o de división (split) excede los límites físicos o lógicos admitidos."""


# --- Errores relacionados con la Planificación (Planner) ---


class PlannerDomainError(StudyTimetrialError):
    """Excepción base para errores en la configuración de metas y secciones del planificador."""


class InvalidSectionError(PlannerDomainError):
    """Se lanza cuando una sección planificada tiene valores o identificadores inválidos."""


class MilestoneDateError(PlannerDomainError):
    """Se lanza cuando la fecha de un hito no respeta el formato ISO o el intervalo de cursada."""
