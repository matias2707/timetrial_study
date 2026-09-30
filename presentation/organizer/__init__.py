"""Capa de presentación para el módulo de Organización Curricular (MVP)."""

from __future__ import annotations

from presentation.organizer.interfaces import IOrganizerView, IPlannerView
from presentation.organizer.organizer_presenter import OrganizerPresenter, PlannerPresenter

__all__ = [
    "IOrganizerView",
    "IPlannerView",
    "OrganizerPresenter",
    "PlannerPresenter",
]
