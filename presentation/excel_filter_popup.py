"""Diálogo emergente de filtro y ordenamiento de columna estilo Excel."""

from __future__ import annotations

from typing import Any, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

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
    get_column_unique_values,
)
from domain.models import TimerItem


class ExcelColumnFilterPopup(QDialog):
    """Popup emergente para filtrar y ordenar una columna específica estilo Excel."""

    filter_applied = Signal(str, object)  # column_key, ColumnFilterRule
    sort_requested = Signal(str, str)  # column_key, "asc" | "desc" | "none"

    def __init__(
        self,
        column_key: str,
        items: Sequence[TimerItem],
        current_rule: ColumnFilterRule | None,
        current_sort_direction: str | None,  # "asc", "desc", or None
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.column_key = column_key
        self.items = items
        self.current_rule = current_rule or ColumnFilterRule()
        self.current_sort_direction = current_sort_direction
        self.unique_values = get_column_unique_values(items, column_key)

        self.setObjectName("excelFilterPopup")
        self.setMinimumWidth(260)
        self.setMaximumWidth(320)
        self.setMinimumHeight(340)

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Cabecera con título
        title_row = QHBoxLayout()
        col_title = COLUMN_TITLES.get(self.column_key, self.column_key.capitalize())
        lbl_title = QLabel(f"Filtro: {col_title}")
        lbl_title.setObjectName("filter_popup_title")
        title_row.addWidget(lbl_title)
        title_row.addStretch()

        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times", color="#94a3b8"))
        close_btn.setObjectName("table_action_icon")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.reject)
        title_row.addWidget(close_btn)
        main_layout.addLayout(title_row)

        # 2. Acciones de Ordenamiento
        sort_box = QVBoxLayout()
        sort_box.setSpacing(4)

        btn_asc = QPushButton(" Ordenar de menor a mayor (A ➔ Z)")
        btn_asc.setIcon(qta.icon("fa5s.sort-amount-down-alt", color="#3b82f6"))
        btn_asc.setObjectName("filter_sort_btn")
        btn_asc.clicked.connect(lambda: self._on_sort_clicked("asc"))
        sort_box.addWidget(btn_asc)

        btn_desc = QPushButton(" Ordenar de mayor a menor (Z ➔ A)")
        btn_desc.setIcon(qta.icon("fa5s.sort-amount-down", color="#3b82f6"))
        btn_desc.setObjectName("filter_sort_btn")
        btn_desc.clicked.connect(lambda: self._on_sort_clicked("desc"))
        sort_box.addWidget(btn_desc)

        if self.current_sort_direction:
            btn_clear_sort = QPushButton(" Quitar orden de esta columna")
            btn_clear_sort.setIcon(qta.icon("fa5s.times", color="#ef4444"))
            btn_clear_sort.setObjectName("filter_sort_btn")
            btn_clear_sort.clicked.connect(lambda: self._on_sort_clicked("none"))
            sort_box.addWidget(btn_clear_sort)

        main_layout.addLayout(sort_box)

        # Separador
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setObjectName("filter_sep")
        main_layout.addWidget(sep1)

        # 3. Filtro por Condición (si aplica)
        self.cond_combo = QComboBox()
        self.cond_combo.addItem("Condición: Ninguna", None)
        if self.column_key in (COL_SECTION, COL_COMMENT):
            self.cond_combo.addItem("Contiene...", "CONTAINS")
            self.cond_combo.addItem("Es igual a...", "EQUALS")
        elif self.column_key in (COL_EXERCISE, COL_TIME, COL_BREAK):
            self.cond_combo.addItem("Mayor que...", "GT")
            self.cond_combo.addItem("Menor que...", "LT")
        elif self.column_key == COL_DATE:
            self.cond_combo.addItem("Hoy", "DATE_TODAY")
            self.cond_combo.addItem("Últimos 7 días", "DATE_LAST_7_DAYS")
            self.cond_combo.addItem("Este mes", "DATE_THIS_MONTH")

        # Configurar valor previo de condición si existe
        if self.current_rule.condition_type:
            idx = self.cond_combo.findData(self.current_rule.condition_type)
            if idx >= 0:
                self.cond_combo.setCurrentIndex(idx)

        main_layout.addWidget(self.cond_combo)

        self.cond_input = QLineEdit()
        self.cond_input.setPlaceholderText("Valor de condición...")
        if self.current_rule.condition_value is not None:
            self.cond_input.setText(str(self.current_rule.condition_value))
        self.cond_input.setVisible(self.cond_combo.currentData() in ("CONTAINS", "EQUALS", "GT", "LT"))
        self.cond_combo.currentIndexChanged.connect(self._on_cond_combo_changed)
        main_layout.addWidget(self.cond_input)

        # Separador
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setObjectName("filter_sep")
        main_layout.addWidget(sep2)

        # 4. Buscador de valores
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar valores...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_list_items)
        main_layout.addWidget(self.search_input)

        # 5. Lista con Checkboxes (Valores Únicos de Excel)
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("excelFilterList")

        # Checkbox "Seleccionar todo"
        self.select_all_item = QListWidgetItem("(Seleccionar todo)")
        self.select_all_item.setFlags(self.select_all_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.list_widget.addItem(self.select_all_item)

        # Items de valores únicos
        self.value_items: list[tuple[str, QListWidgetItem]] = []
        selected_set = self.current_rule.selected_values

        all_checked = True
        for val, count in self.unique_values:
            item_text = f"{val}  ({count})"
            it = QListWidgetItem(item_text)
            it.setData(Qt.ItemDataRole.UserRole, val)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            # Si selected_values es None, todos están marcados inicialmente
            is_checked = True if selected_set is None else (val in selected_set)
            it.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            if not is_checked:
                all_checked = False

            self.list_widget.addItem(it)
            self.value_items.append((val, it))

        self.select_all_item.setCheckState(Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        main_layout.addWidget(self.list_widget)

        # 6. Botonera inferior
        btn_row = QHBoxLayout()
        btn_clear = QPushButton("Limpiar")
        btn_clear.setObjectName("filter_reset_btn")
        btn_clear.clicked.connect(self._on_clear_clicked)
        btn_row.addWidget(btn_clear)

        btn_row.addStretch()

        btn_apply = QPushButton("Aplicar")
        btn_apply.setObjectName("toolbar_primary")
        btn_apply.clicked.connect(self._on_apply_clicked)
        btn_row.addWidget(btn_apply)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("filter_reset_btn")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        main_layout.addLayout(btn_row)

    def _on_cond_combo_changed(self, index: int) -> None:
        cond = self.cond_combo.currentData()
        self.cond_input.setVisible(cond in ("CONTAINS", "EQUALS", "GT", "LT"))

    def _on_sort_clicked(self, direction: str) -> None:
        self.sort_requested.emit(self.column_key, direction)
        self.accept()

    def _on_item_changed(self, changed_item: QListWidgetItem) -> None:
        self.list_widget.blockSignals(True)
        try:
            if changed_item is self.select_all_item:
                state = self.select_all_item.checkState()
                for _, it in self.value_items:
                    if not it.isHidden():
                        it.setCheckState(state)
            else:
                # Comprobar si todos los visibles están marcados
                all_checked = True
                for _, it in self.value_items:
                    if it.checkState() == Qt.CheckState.Unchecked:
                        all_checked = False
                        break
                self.select_all_item.setCheckState(Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
        finally:
            self.list_widget.blockSignals(False)

    def _filter_list_items(self, query: str) -> None:
        query = query.strip().lower()
        for val, it in self.value_items:
            it.setHidden(query not in val.lower())

    def _on_clear_clicked(self) -> None:
        # Restablecer filtro de esta columna
        rule = ColumnFilterRule(selected_values=None, condition_type=None, condition_value=None)
        self.filter_applied.emit(self.column_key, rule)
        self.accept()

    def _on_apply_clicked(self) -> None:
        # Recolectar valores seleccionados
        selected = set()
        for val, it in self.value_items:
            if it.checkState() == Qt.CheckState.Checked:
                selected.add(val)

        total_unique = len(self.value_items)
        selected_rule_set: set[str] | None = selected if len(selected) < total_unique else None

        # Recolectar condición
        cond_type = self.cond_combo.currentData()
        cond_val: Any = None
        if cond_type:
            raw_input = self.cond_input.text().strip()
            if cond_type in ("GT", "LT"):
                try:
                    cond_val = float(raw_input)
                except ValueError:
                    cond_val = None
            elif cond_type in ("CONTAINS", "EQUALS"):
                cond_val = raw_input if raw_input else None

        rule = ColumnFilterRule(
            selected_values=selected_rule_set,
            condition_type=cond_type,
            condition_value=cond_val,
        )
        self.filter_applied.emit(self.column_key, rule)
        self.accept()
