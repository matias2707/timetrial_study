"""Módulo de la vista del Planificador de Estudio con arquitectura MVP."""

from __future__ import annotations

from presentation.planner.interfaces import IPlannerView
from presentation.planner.planner_presenter import PlannerPresenter

__all__ = [
    "IPlannerView",
    "PlannerPresenter",
]
