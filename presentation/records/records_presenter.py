"""Presenter puro (MVP) para la vista analítica de Registros de Estudio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from application.record_query import ColumnFilterRule, apply_column_filters_and_sort
from domain.models import TimerItem
from presentation.records.interfaces import IRecordsView

if TYPE_CHECKING:
    from application.application_service import StudyApplicationService


class RecordsPresenter:
    """Presenter desacoplado que coordina el filtrado, ordenamiento y edición de registros."""

    def __init__(self, view: IRecordsView, application: StudyApplicationService) -> None:
        self.view = view
        self.application = application

    def refresh_records(
        self,
        column_filters: dict[str, ColumnFilterRule] | None = None,
        active_sorts_ordered: list[tuple[str, str]] | None = None,
        global_query: str = "",
    ) -> None:
        """Aplica filtros y ordenamiento sobre los registros y actualiza la vista pasiva."""
        if not self.application.is_record_open:
            self.view.set_empty_state(True)
            return

        self.view.set_empty_state(False)
        all_items = list(self.application.record.items)

        filters = column_filters or {}
        sorts = active_sorts_ordered or []

        processed = apply_column_filters_and_sort(
            items=all_items,
            column_filters=filters,
            active_sorts_ordered=sorts,
            global_query=global_query,
        )

        active_filters_count = len([k for k, v in filters.items() if v and v.is_active()])
        self.view.render_items(processed)
        self.view.update_filter_summary(active_filters_count, len(processed), len(all_items))

    def delete_item(self, item_or_id: str | TimerItem) -> bool:
        """Elimina un intento por su instancia o identificador UUID y persiste los cambios."""
        if not self.application.is_record_open:
            return False

        target: TimerItem | None = None
        if isinstance(item_or_id, str):
            for it in self.application.record.items:
                if it.id == item_or_id:
                    target = it
                    break
        else:
            target = item_or_id

        if target is not None:
            self.application.delete_item(target)
            self.refresh_records()
            return True
        return False
