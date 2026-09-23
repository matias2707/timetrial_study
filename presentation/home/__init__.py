"""Módulo de la vista principal del cronómetro (Home) con arquitectura MVP."""

from __future__ import annotations

from presentation.home.home_presenter import HomePresenter
from presentation.home.interfaces import IHomeView

__all__ = [
    "IHomeView",
    "HomePresenter",
]
