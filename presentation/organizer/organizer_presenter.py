"""Presenter puro (MVP) para la vista del Organizador de Estudio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from presentation.organizer.interfaces import IOrganizerView, IPlannerView

if TYPE_CHECKING:
    from application.application_service import StudyApplicationService


class OrganizerPresenter:
    """Presenter desacoplado que coordina la lógica y métricas del organizador."""

    def __init__(self, view: IOrganizerView, application: StudyApplicationService) -> None:
        self.view = view
        self.application = application

    def refresh_organizer(self) -> None:
        """Sincroniza y recalcula el estado de todas las secciones organizadas."""
        if not self.application.is_record_open:
            self.view.set_empty_state(True)
            return

        self.view.set_empty_state(False)
        overview = self.application.get_organizer_overview()
        sections = getattr(overview, "sections", [])
        completion_rate = getattr(overview, "global_completion_percentage", 0.0)

        self.view.render_sections_overview(sections, completion_rate)

    # Alias de retrocompatibilidad
    refresh_planner = refresh_organizer

    def check_boundaries(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
    ) -> tuple[bool, str]:
        """Verifica si la coordenada se encuentra dentro de los límites organizados."""
        return self.application.check_navigation_boundary(
            section_type=section_type,
            section_number=section_number,
            exercise=exercise,
            inciso=inciso,
        )


# Alias de retrocompatibilidad
PlannerPresenter = OrganizerPresenter
