"""Vista de Registros de Study Timetrial."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import StudyApplicationService
from application.record_query import (
    COL_BREAK,
    COL_COMMENT,
    COL_DATE,
    COL_EXERCISE,
    COL_INCISO,
    COL_SECTION,
    COL_STATUS,
    COL_TIME,
    COLUMN_TITLES,
    ColumnFilterRule,
    apply_column_filters_and_sort,
    get_column_unique_values,
)
from domain.models import TimerItem
from presentation.excel_filter_popup import ExcelColumnFilterPopup
from presentation.presentation_dialogs import ItemDialog
from presentation.presentation_formatters import format_hh_mm, format_milliseconds


class RecordsViewWidget(QWidget):
    """Vista interactiva para consultar, filtrar y gestionar los registros guardados."""

    data_modified = Signal()
    resume_item_requested = Signal(object)
    request_open_record = Signal()
    request_import_records = Signal()
    request_save_as = Signal()
    request_rename_record = Signal()
    request_close_record = Signal()
    request_export = Signal(object)

    def __init__(
        self,
        application: StudyApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.application = application

        self.column_sort_states: dict[str, str] = {}
        self.column_filter_rules: dict[str, ColumnFilterRule] = {}
        self._current_displayed_items: list[TimerItem] = []
        self.LOGICAL_COL_KEYS = {
            0: COL_SECTION,
            1: COL_EXERCISE,
            2: COL_INCISO,
            3: COL_DATE,
            4: COL_BREAK,
            5: COL_TIME,
            6: COL_STATUS,
            7: COL_COMMENT,
        }

        self._is_dirty: bool = True
        self._cache_action_icons()
        self._build_ui()

    def _cache_action_icons(self) -> None:
        """Pre-cachea los iconos de las acciones para evitar llamadas repetitivas a qta.icon."""
        self._icon_comment = qta.icon("fa5s.comment-dots", color="#3b82f6")
        self._icon_edit = qta.icon("fa5s.edit", color="#6366f1")
        self._icon_resume = qta.icon("fa5s.play-circle", color="#10b981")
        self._icon_delete = qta.icon("fa5s.trash-alt", color="#ef4444")

    def mark_dirty(self) -> None:
        """Marca que los datos de la tabla requieren recarga."""
        self._is_dirty = True

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(14)

        # Heading
        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Registros")
        title.setObjectName("brand")
        self.records_summary = QLabel("0 intentos guardados")
        self.records_summary.setObjectName("record_meta")
        title_box.addWidget(title)
        title_box.addWidget(self.records_summary)
        heading.addLayout(title_box)
        heading.addStretch()
        layout.addLayout(heading)

        # Quick KPI Metrics Cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        def make_kpi(icon_name: str, icon_color: str, card_title: str) -> tuple[QFrame, QLabel]:
            card = QFrame()
            card.setObjectName("kpiCard")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 10, 14, 10)
            c_layout.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
            c_layout.addWidget(icon_lbl)

            t_layout = QVBoxLayout()
            t_layout.setContentsMargins(0, 0, 0, 0)
            t_layout.setSpacing(1)
            t_lbl = QLabel(card_title)
            t_lbl.setObjectName("kpi_title")
            v_lbl = QLabel("-")
            v_lbl.setObjectName("kpi_value")
            t_layout.addWidget(t_lbl)
            t_layout.addWidget(v_lbl)
            c_layout.addLayout(t_layout)
            return card, v_lbl

        card_att, self.rec_stat_attempts = make_kpi("fa5s.history", "#3b82f6", "TOTAL INTENTOS")
        card_ex, self.rec_stat_exercise_time = make_kpi("fa5s.clock", "#10b981", "TIEMPO ESTUDIO")
        card_br, self.rec_stat_break_time = make_kpi("fa5s.coffee", "#f59e0b", "TIEMPO RECESO")
        card_eff, self.rec_stat_effectiveness = make_kpi("fa5s.check-circle", "#84cc16", "EFECTIVIDAD")

        for c in (card_att, card_ex, card_br, card_eff):
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
            kpi_row.addWidget(c)
        layout.addLayout(kpi_row)

        # Toolbar and Search
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.open_button = QPushButton(" Abrir")
        self.open_button.setIcon(qta.icon("fa5s.folder-open", color="#334155"))
        self.open_button.setObjectName("secondary_action")
        self.recent_files_menu = QMenu(self)
        self.open_button.setMenu(self.recent_files_menu)
        self.open_button.clicked.connect(self.request_open_record.emit)
        toolbar.addWidget(self.open_button)

        self.import_button = QPushButton(" Importar")
        self.import_button.setObjectName("secondary_action")
        self.import_button.setIcon(qta.icon("fa5s.file-import", color="#334155"))
        self.import_button.clicked.connect(self.request_import_records.emit)
        toolbar.addWidget(self.import_button)

        self.export_button = QPushButton(" Exportar")
        self.export_button.setObjectName("secondary_action")
        self.export_button.setIcon(qta.icon("fa5s.file-export", color="#334155"))
        self.export_button.clicked.connect(self._on_export_clicked)
        toolbar.addWidget(self.export_button)

        self.save_as_button = QPushButton(" Guardar como")
        self.save_as_button.setObjectName("secondary_action")
        self.save_as_button.setIcon(qta.icon("fa5s.save", color="#334155"))
        self.save_as_button.clicked.connect(self.request_save_as.emit)
        toolbar.addWidget(self.save_as_button)

        self.rename_button = QPushButton(" Renombrar")
        self.rename_button.setObjectName("secondary_action")
        self.rename_button.setIcon(qta.icon("fa5s.pen", color="#334155"))
        self.rename_button.clicked.connect(self.request_rename_record.emit)
        toolbar.addWidget(self.rename_button)

        self.close_button = QPushButton(" Cerrar")
        self.close_button.setObjectName("secondary_action")
        self.close_button.setIcon(qta.icon("fa5s.times", color="#ef4444"))
        self.close_button.clicked.connect(self.request_close_record.emit)
        toolbar.addWidget(self.close_button)

        toolbar.addStretch()

        # Search Bar
        self.record_search_input = QLineEdit()
        self.record_search_input.setPlaceholderText("Buscar sección, ejercicio o comentario...")
        self.record_search_input.setClearButtonEnabled(True)
        self.record_search_input.setMinimumWidth(260)
        self.record_search_input.addAction(qta.icon("fa5s.search", color="#94a3b8"), QLineEdit.ActionPosition.LeadingPosition)
        self.record_search_input.textChanged.connect(self.filter_records_table)
        toolbar.addWidget(self.record_search_input)

        self.add_item_button = QPushButton(" Agregar intento")
        self.add_item_button.setObjectName("toolbar_primary")
        self.add_item_button.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_item_button.clicked.connect(self.add_item)
        toolbar.addWidget(self.add_item_button)

        # Botón para limpiar todos los filtros activos
        self.clear_all_filters_btn = QPushButton(" Limpiar filtros")
        self.clear_all_filters_btn.setObjectName("filter_reset_btn")
        self.clear_all_filters_btn.setIcon(qta.icon("fa5s.filter", color="#94a3b8"))
        self.clear_all_filters_btn.setToolTip("Restablecer todos los filtros y órdenes de columna")
        self.clear_all_filters_btn.clicked.connect(self.reset_all_filters)
        self.clear_all_filters_btn.setVisible(False)
        toolbar.addWidget(self.clear_all_filters_btn)

        layout.addLayout(toolbar)

        # Table (12 columnas)
        self.table = QTableWidget(0, 12)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        header = self.table.horizontalHeader()

        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDropIndicatorShown(True)
        header.setSortIndicatorShown(False)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        header.sectionClicked.connect(self._on_header_section_clicked)
        header.customContextMenuRequested.connect(self._on_header_context_menu)
        header.sectionMoved.connect(self._on_column_moved)

        self.update_header_labels()

        for col, width in (
            (0, 110),  # Sección
            (1, 75),   # Ejercicio
            (2, 65),   # Inciso
            (3, 135),  # Fecha
            (4, 90),   # Receso
            (5, 90),   # Tiempo
            (6, 125),  # Estado
        ):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(col, width)

        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        for col in (8, 9, 10, 11):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, 48)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self.show_comment_alert)
        layout.addWidget(self.table)

    def update_header_labels(self) -> None:
        for col_idx, col_key in self.LOGICAL_COL_KEYS.items():
            title = COLUMN_TITLES.get(col_key, "")
            rule = self.column_filter_rules.get(col_key)
            all_items = self.application.record.items
            unique_vals = {v for v, _ in get_column_unique_values(all_items, col_key)}
            is_filtered = rule is not None and rule.is_active(unique_vals)
            sort_dir = self.column_sort_states.get(col_key)

            indicators = []
            if sort_dir == "asc":
                indicators.append("▲")
            elif sort_dir == "desc":
                indicators.append("▼")
            if is_filtered:
                indicators.append("🔍")

            suffix = (" " + " ".join(indicators)) if indicators else ""
            header_item = QTableWidgetItem(f"{title}{suffix}")
            self.table.setHorizontalHeaderItem(col_idx, header_item)

    def get_active_sorts_by_hierarchy(self) -> list[tuple[str, str]]:
        if not self.column_sort_states:
            return []
        header = self.table.horizontalHeader()
        visual_order = []
        for log_idx in range(header.count()):
            vis_idx = header.visualIndex(log_idx)
            col_key = self.LOGICAL_COL_KEYS.get(log_idx)
            if col_key and col_key in self.column_sort_states:
                visual_order.append((vis_idx, col_key, self.column_sort_states[col_key]))

        visual_order.sort(key=lambda x: x[0])
        return [(col_key, direction) for _, col_key, direction in visual_order]

    def _on_header_section_clicked(self, logical_index: int) -> None:
        col_key = self.LOGICAL_COL_KEYS.get(logical_index)
        if not col_key:
            return

        curr_dir = self.column_sort_states.get(col_key)
        if curr_dir is None:
            self.column_sort_states[col_key] = "asc"
        elif curr_dir == "asc":
            self.column_sort_states[col_key] = "desc"
        else:
            self.column_sort_states.pop(col_key, None)

        self.update_header_labels()
        self.mark_dirty()
        self.refresh_table(force=True)

    def _on_column_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int) -> None:
        if self.column_sort_states:
            self.mark_dirty()
            self.refresh_table(force=True)

    def _on_header_context_menu(self, pos) -> None:
        logical_index = self.table.horizontalHeader().logicalIndexAt(pos)
        col_key = self.LOGICAL_COL_KEYS.get(logical_index)
        if col_key:
            self.open_excel_filter_popup(logical_index, col_key)

    def open_excel_filter_popup(self, logical_index: int, col_key: str) -> None:
        popup = ExcelColumnFilterPopup(
            column_key=col_key,
            items=self.application.record.items,
            current_rule=self.column_filter_rules.get(col_key),
            current_sort_direction=self.column_sort_states.get(col_key),
            parent=self.window(),
        )
        popup.filter_applied.connect(self._on_popup_filter_applied)
        popup.sort_requested.connect(self._on_popup_sort_requested)

        header = self.table.horizontalHeader()
        section_pos = header.mapToGlobal(header.pos())
        section_x = section_pos.x() + header.sectionPosition(logical_index)
        section_y = section_pos.y() + header.height()
        popup.move(section_x, section_y)
        popup.exec()

    def _on_popup_filter_applied(self, col_key: str, rule: ColumnFilterRule) -> None:
        all_items = self.application.record.items
        unique_vals = {v for v, _ in get_column_unique_values(all_items, col_key)}
        if rule.is_active(unique_vals):
            self.column_filter_rules[col_key] = rule
        else:
            self.column_filter_rules.pop(col_key, None)
        self.update_header_labels()
        self.mark_dirty()
        self.refresh_table(force=True)

    def _on_popup_sort_requested(self, col_key: str, direction: str) -> None:
        if direction in ("asc", "desc"):
            self.column_sort_states[col_key] = direction
        else:
            self.column_sort_states.pop(col_key, None)
        self.update_header_labels()
        self.mark_dirty()
        self.refresh_table(force=True)

    def reset_all_filters(self) -> None:
        self.column_filter_rules.clear()
        self.column_sort_states.clear()
        if hasattr(self, "record_search_input"):
            self.record_search_input.clear()
        self.update_header_labels()
        self.mark_dirty()
        self.refresh_table(force=True)

    def set_empty_state(self, is_empty: bool) -> None:
        """Habilita o deshabilita acciones de la vista según si hay proyecto activo."""
        for btn in (
            getattr(self, "import_button", None),
            getattr(self, "export_button", None),
            getattr(self, "save_as_button", None),
            getattr(self, "rename_button", None),
            getattr(self, "close_button", None),
            getattr(self, "add_item_button", None),
            getattr(self, "clear_all_filters_btn", None),
            getattr(self, "record_search_input", None),
        ):
            if btn is not None:
                btn.setEnabled(not is_empty)

    def _on_export_clicked(self) -> None:
        """Emite la solicitud de exportación pasando la lista actual de registros filtrados."""
        self.request_export.emit(self._current_displayed_items)

        if is_empty:
            self.records_summary.setText("Sin proyecto activo")
            self.rec_stat_attempts.setText("-")
            self.rec_stat_exercise_time.setText("-")
            self.rec_stat_break_time.setText("-")
            self.rec_stat_effectiveness.setText("-")
            self.table.setRowCount(0)
            self.mark_dirty()
        else:
            self.mark_dirty()
            self.refresh_table(force=True)

    def filter_records_table(self, _query: str = "") -> None:
        self.mark_dirty()
        self.refresh_table(force=True)

    def refresh_table(self, force: bool = True) -> None:
        if not force and not self._is_dirty:
            return

        all_items = self.application.record.items
        active_sorts = self.get_active_sorts_by_hierarchy()
        search_text = self.record_search_input.text() if hasattr(self, "record_search_input") else ""

        all_col_values = {}
        for col_key in self.LOGICAL_COL_KEYS.values():
            all_col_values[col_key] = {val for val, _ in get_column_unique_values(all_items, col_key)}

        self._current_displayed_items = apply_column_filters_and_sort(
            all_items,
            column_filters=self.column_filter_rules,
            active_sorts_ordered=active_sorts,
            global_query=search_text,
            all_column_values_map=all_col_values,
        )

        total_items = len(all_items)
        displayed_count = len(self._current_displayed_items)

        has_active_filters = (
            any(rule.is_active(all_col_values.get(k)) for k, rule in self.column_filter_rules.items())
            or bool(self.column_sort_states)
            or bool(search_text.strip())
        )
        if hasattr(self, "clear_all_filters_btn"):
            self.clear_all_filters_btn.setVisible(has_active_filters)

        if displayed_count != total_items:
            self.records_summary.setText(f"Mostrando {displayed_count} de {total_items} intento{'s' if total_items != 1 else ''} (filtrado)")
        else:
            self.records_summary.setText(f"{total_items} intento{'s' if total_items != 1 else ''} guardado{'s' if total_items != 1 else ''}")

        # Update KPI cards
        stats = self.application.get_statistics()
        if hasattr(self, "rec_stat_attempts"):
            self.rec_stat_attempts.setText(str(stats.total_attempts))
            self.rec_stat_exercise_time.setText(format_hh_mm(stats.total_exercise_time_ms))
            self.rec_stat_break_time.setText(format_hh_mm(stats.total_break_time_ms))
            eff_pct = int(round((stats.completed_attempts / stats.total_attempts * 100.0))) if stats.total_attempts else 0
            self.rec_stat_effectiveness.setText(f"{eff_pct}%")

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.clearContents()
            self.table.setRowCount(displayed_count)

            for index, item in enumerate(self._current_displayed_items):
                self.table.setRowHeight(index, 38)

                location_text = f"{item.section_type} {item.section_number}"
                loc_item = QTableWidgetItem(location_text)
                loc_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(index, 0, loc_item)

                ex_item = QTableWidgetItem(str(item.exercise))
                ex_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, 1, ex_item)

                inc_item = QTableWidgetItem(str(item.inciso or "-"))
                inc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, 2, inc_item)

                # Columna 3: Fecha
                try:
                    dt_obj = datetime.fromisoformat(item.created_at)
                    date_str = dt_obj.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    date_str = item.created_at[:16] if len(item.created_at) >= 16 else item.created_at
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, 3, date_item)

                br_item = QTableWidgetItem(format_milliseconds(item.break_time_ms))
                br_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, 4, br_item)

                t_item = QTableWidgetItem(format_milliseconds(item.exercise_time_ms))
                t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, 5, t_item)

                # Columna 6: Estado badge
                status_badge = QLabel("✓ Completado" if item.completed else "✕ Incompleto")
                status_badge.setObjectName("table_badge_completed" if item.completed else "table_badge_incomplete")
                status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setCellWidget(index, 6, status_badge)

                # Columna 7: Comentario
                comm_item = QTableWidgetItem(item.comment)
                comm_item.setToolTip(item.comment or "Sin comentario")
                self.table.setItem(index, 7, comm_item)

                # Botones de acción compactos
                comm_btn = QPushButton()
                comm_btn.setIcon(self._icon_comment)
                comm_btn.setObjectName("table_action_icon")
                comm_btn.setToolTip("Comentar registro")
                comm_btn.clicked.connect(lambda _, it=item: self.comment_item(it))
                self.table.setCellWidget(index, 8, comm_btn)

                edit_btn = QPushButton()
                edit_btn.setIcon(self._icon_edit)
                edit_btn.setObjectName("table_action_icon")
                edit_btn.setToolTip("Editar registro")
                edit_btn.clicked.connect(lambda _, it=item: self.edit_item(it))
                self.table.setCellWidget(index, 9, edit_btn)

                resume_btn = QPushButton()
                resume_btn.setIcon(self._icon_resume)
                resume_btn.setObjectName("table_action_icon")
                resume_btn.setToolTip("Continuar en cronómetro")
                resume_btn.clicked.connect(lambda _, it=item: self.resume_item(it))
                self.table.setCellWidget(index, 10, resume_btn)

                del_btn = QPushButton()
                del_btn.setIcon(self._icon_delete)
                del_btn.setObjectName("table_delete_icon")
                del_btn.setToolTip("Eliminar registro")
                del_btn.clicked.connect(lambda _, it=item: self.delete_item(it))
                self.table.setCellWidget(index, 11, del_btn)
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)
            self._is_dirty = False

    def show_comment_alert(self, row: int, column: int) -> None:
        if column != 7:
            return
        if row < len(self._current_displayed_items):
            item = self._current_displayed_items[row]
            QMessageBox.information(
                self.window(),
                "Comentario del registro",
                item.comment or "Este registro no tiene comentario.",
            )

    def comment_item(self, target: int | TimerItem) -> None:
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        comment, accepted = QInputDialog.getMultiLineText(
            self.window(),
            "Comentario del registro",
            "Comentario:",
            item.comment,
        )
        if accepted:
            self.application.update_comment(item, comment)
            self.mark_dirty()
            self.refresh_table(force=True)
            self.data_modified.emit()

    def add_item(self) -> None:
        dialog = ItemDialog(self.window())
        if dialog.exec() == ItemDialog.DialogCode.Accepted:
            if dialog.validated_item is not None:
                item = dialog.validated_item
                gap_items = self.application.find_inciso_gap_candidates(
                    item.section_type,
                    item.section_number,
                    item.exercise,
                    item.inciso,
                )
                if gap_items:
                    from presentation.inciso_dialog import ACTION_CANCEL, ACTION_CUSTOM_VALUES

                    prompt_fn = getattr(self.window(), "_prompt_inciso_gap_dialog", None)
                    if prompt_fn:
                        action, sec_type, sec_num, ex, inc = prompt_fn(
                            item.section_type,
                            item.section_number,
                            item.exercise,
                            item.inciso,
                            gap_items,
                            always_resume=True,
                        )
                        if action == ACTION_CANCEL:
                            return
                        elif action == ACTION_CUSTOM_VALUES:
                            item.section_type = sec_type
                            item.section_number = sec_num
                            item.exercise = ex
                            item.inciso = inc

                self.application.add_item(item)
                self.application.sync_planner_with_records()
                self.mark_dirty()
                self.refresh_table(force=True)
                self.data_modified.emit()

    def edit_item(self, target: int | TimerItem) -> None:
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        dialog = ItemDialog(self.window(), item)
        code = dialog.exec()
        if code == ItemDialog.DialogCode.Accepted:
            if dialog.validated_item is not None:
                self.application.replace_item(item, dialog.validated_item)
                self.mark_dirty()
                self.refresh_table(force=True)
                self.data_modified.emit()
        elif getattr(dialog, "load_in_timer_requested", False):
            if dialog.validated_item is not None:
                self.application.replace_item(item, dialog.validated_item)
                self.mark_dirty()
                self.refresh_table(force=True)
                self.data_modified.emit()
                self.resume_item(dialog.validated_item)
            else:
                self.resume_item(item)

    def reset_item(self, target: int | TimerItem) -> None:
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        if QMessageBox.question(
            self.window(),
            "Confirmar reset",
            "¿Está seguro de reiniciar este registro?",
        ) == QMessageBox.StandardButton.Yes:
            self.application.reset_item(item)
            self.mark_dirty()
            self.refresh_table(force=True)
            self.data_modified.emit()

    def delete_item(self, target: int | TimerItem) -> None:
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        if QMessageBox.question(
            self.window(),
            "Confirmar eliminación",
            "¿Está seguro de eliminar este registro?\nEsta acción no se puede deshacer.",
        ) == QMessageBox.StandardButton.Yes:
            self.application.delete_item(item)
            self.mark_dirty()
            self.refresh_table(force=True)
            self.data_modified.emit()

    def resume_item(self, target: int | TimerItem) -> None:
        """Emite la señal para reanudar / continuar el item en el cronómetro."""
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        self.resume_item_requested.emit(item)

    def _on_table_context_menu(self, pos) -> None:
        row = self.table.rowAt(pos.y())
        if not (0 <= row < len(self._current_displayed_items)):
            return

        target_item = self._current_displayed_items[row]
        menu = QMenu(self)

        resume_action = menu.addAction(qta.icon("fa5s.play-circle", color="#10b981"), "Continuar intento en el cronómetro")
        menu.addSeparator()
        comment_action = menu.addAction(qta.icon("fa5s.comment-dots", color="#3b82f6"), "Comentario...")
        edit_action = menu.addAction(qta.icon("fa5s.edit", color="#6366f1"), "Editar registro...")
        reset_action = menu.addAction(qta.icon("fa5s.redo-alt", color="#f59e0b"), "Reiniciar tiempo...")
        menu.addSeparator()
        del_action = menu.addAction(qta.icon("fa5s.trash-alt", color="#ef4444"), "Eliminar registro")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == resume_action:
            self.resume_item(target_item)
        elif action == comment_action:
            self.comment_item(target_item)
        elif action == edit_action:
            self.edit_item(target_item)
        elif action == reset_action:
            self.reset_item(target_item)
        elif action == del_action:
            self.delete_item(target_item)

