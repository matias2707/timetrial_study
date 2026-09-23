"""Módulo de la vista de Registros de Estudio con arquitectura MVP."""

from __future__ import annotations

from presentation.records.interfaces import IRecordsView
from presentation.records.records_presenter import RecordsPresenter

__all__ = [
    "IRecordsView",
    "RecordsPresenter",
]
