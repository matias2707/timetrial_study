"""Módulo de compatibilidad para presentation.planner_widget.

Reexporta todos los componentes migrados a presentation.organizer_widget.
"""

from __future__ import annotations

from presentation.organizer_widget import (
    CompositeExerciseGroup,
    ExerciseCellButton,
    GroupHeaderCellButton,
    OrganizedSectionCard,
    OrganizedSectionCard as PlannedSectionCard,
    OrganizerWidget,
    OrganizerWidget as PlannerWidget,
    SegmentedProgressBar,
)

__all__ = [
    "CompositeExerciseGroup",
    "ExerciseCellButton",
    "GroupHeaderCellButton",
    "OrganizedSectionCard",
    "PlannedSectionCard",
    "OrganizerWidget",
    "PlannerWidget",
    "SegmentedProgressBar",
]
