"""Subpaquete de presentación para el módulo de Estadísticas (MVP)."""

from __future__ import annotations

from presentation.statistics.interfaces import IStatisticsView
from presentation.statistics.statistics_presenter import StatisticsPresenter

__all__ = ["IStatisticsView", "StatisticsPresenter"]
