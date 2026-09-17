"""Diálogo para resolver y corregir desfasajes de incisos al guardar registros."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from presentation.presentation_formatters import format_hh_mm_ss

if TYPE_CHECKING:
    from domain.models import TimerItem

ACTION_CORRECT_ALL = "correct_all"
ACTION_KEEP_MANUAL = "keep_manual"
ACTION_CUSTOM_VALUES = "custom_values"
ACTION_CANCEL = "cancel"


class IncisoCorrectionDialog(QDialog):
    """Diálogo interactivo de 3 opciones para resolver desfasajes de incisos:

    1. Guardar y actualizar incisos (corrige los '-' a 1).
    2. Solo guardar y corregir manualmente (marcada por defecto).
    3. Personalizar valor actual (nombre de sección, N° de sección, ejercicio e inciso).
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        section_type: str = "Guía",
        section_number: int = 1,
        exercise: int = 1,
        current_inciso: int = 2,
        affected_count: int = 1,
        is_dark: bool = True,
        gap_items: list[TimerItem] | None = None,
    ) -> None:
        super().__init__(parent)
        self.section_type = section_type
        self.section_number = section_number
        self.exercise = exercise
        self.current_inciso = current_inciso
        self.gap_items = list(gap_items) if gap_items else []
        self.affected_count = len(self.gap_items) if self.gap_items else affected_count
        self.is_dark = is_dark

        self.result_action = ACTION_CANCEL
        self.selected_section_type = section_type
        self.selected_section_number = section_number
        self.selected_exercise = exercise
        self.selected_inciso = current_inciso

        self.setWindowTitle("Corrección de Incisos")
        if len(self.gap_items) == 1:
            self.resize(580, 520)
        elif len(self.gap_items) > 1:
            self.resize(600, 550)
        else:
            self.resize(560, 430)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Encabezado con icono y contexto
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_color = "#38bdf8" if self.is_dark else "#0284c7"
        icon_lbl.setPixmap(qta.icon("fa5s.lightbulb", color=icon_color).pixmap(36, 36))
        header_layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        title_lbl = QLabel("Desfasaje de incisos detectado")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_layout.addWidget(title_lbl)

        loc_text = (
            f"Se está registrando: <b>{self.section_type} {self.section_number} · "
            f"Ejercicio {self.exercise} · Inciso {self.current_inciso or '-'}</b>"
        )
        loc_lbl = QLabel(loc_text)
        loc_lbl.setStyleSheet("font-size: 13px;")
        title_layout.addWidget(loc_lbl)

        header_layout.addLayout(title_layout)
        layout.addLayout(header_layout)

        # Panel de alerta con cantidad de registros afectados y aviso de pausa
        badge_frame = QFrame()
        badge_frame.setFrameShape(QFrame.Shape.StyledPanel)
        badge_bg = "rgba(56, 189, 248, 0.12)" if self.is_dark else "#e0f2fe"
        badge_border = "#0284c7" if not self.is_dark else "#0369a1"
        badge_text_color = "#e2e8f0" if self.is_dark else "#0f172a"
        badge_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {badge_bg};
                border: 1px solid {badge_border};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        badge_layout = QHBoxLayout(badge_frame)
        badge_layout.setContentsMargins(10, 8, 10, 8)

        plural_s = "s" if self.affected_count > 1 else ""
        detected_str = "Se detectaron" if self.affected_count > 1 else "Se detectó"
        badge_info = QLabel(
            f"⚠️ <b>Atención:</b> {detected_str} <b>{self.affected_count}</b> registro{plural_s} previo{plural_s} "
            f"del Ejercicio {self.exercise} guardado{plural_s} como <i>'Sin inciso (-)'</i>.<br>"
            f"El cronómetro se encuentra en pausa mientras decides cómo registrarlo."
        )
        badge_info.setWordWrap(True)
        badge_info.setStyleSheet(f"color: {badge_text_color}; font-size: 12px; border: none; background: transparent;")
        badge_layout.addWidget(badge_info)
        layout.addWidget(badge_frame)

        conflict_preview = self._build_conflict_preview()
        if conflict_preview is not None:
            layout.addWidget(conflict_preview)

        # Opciones
        options_lbl = QLabel("Selecciona cómo deseas proceder:")
        options_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(options_lbl)

        self.btn_group = QButtonGroup(self)

        # Opción 1: Solo guardar y corregir manualmente (Marcada por defecto)
        self.radio_manual = QRadioButton("Solo guardar y corregir manualmente")
        self.radio_manual.setChecked(True)
        self.radio_manual.setStyleSheet("font-weight: 700;")
        self.btn_group.addButton(self.radio_manual)
        layout.addWidget(self.radio_manual)

        inciso_val = str(self.current_inciso) if self.current_inciso else "-"
        hint_manual_text = (
            f"    Guardar como <b>{self.section_type} {self.section_number} - Ejercicio {self.exercise} - Inciso {inciso_val}</b>.<br>"
            f"    No se modificarán anteriores."
        )
        hint_manual = QLabel(hint_manual_text)
        hint_manual.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(hint_manual)

        # Opción 2: Guardar y actualizar incisos
        self.radio_correct = QRadioButton("Guardar y actualizar incisos")
        self.radio_correct.setStyleSheet("font-weight: 600;")
        self.btn_group.addButton(self.radio_correct)
        layout.addWidget(self.radio_correct)

        plural_act = "Se actualizarán" if self.affected_count > 1 else "Se actualizará"
        reg_plural = f"{self.affected_count} registros" if self.affected_count > 1 else "1 registro"
        curr_inc_str = str(self.current_inciso) if self.current_inciso else "1"
        hint_correct_text = (
            f"    {plural_act} {reg_plural} de "
            f"<b>{self.section_type} {self.section_number} - Ejercicio {self.exercise} (Sin inciso)</b> a <b>Inciso 1</b> "
            f"y el actual como <b>Inciso {curr_inc_str}</b>."
        )
        hint_correct = QLabel(hint_correct_text)
        hint_correct.setStyleSheet("font-size: 11px; color: #94a3b8;")
        layout.addWidget(hint_correct)

        # Opción 3: Personalizar valor actual
        self.radio_custom = QRadioButton("Personalizar valor actual")
        self.radio_custom.setStyleSheet("font-weight: 600;")
        self.btn_group.addButton(self.radio_custom)
        layout.addWidget(self.radio_custom)

        custom_container = QWidget()
        custom_layout = QGridLayout(custom_container)
        custom_layout.setContentsMargins(24, 2, 0, 4)
        custom_layout.setHorizontalSpacing(10)
        custom_layout.setVerticalSpacing(6)

        # Fila 0: Nombre de sección y N° de sección
        custom_layout.addWidget(QLabel("Nombre de sección:"), 0, 0)
        self.combo_section_type = QComboBox()
        self.combo_section_type.setEditable(True)
        self.combo_section_type.addItems(["Guía", "Sección", "Práctica", "Módulo", "Unidad", "Capítulo", "Apunte", "Parcial"])
        self.combo_section_type.setCurrentText(self.section_type)
        self.combo_section_type.setEnabled(False)
        custom_layout.addWidget(self.combo_section_type, 0, 1)

        custom_layout.addWidget(QLabel("N° de sección:"), 0, 2)
        self.spin_section_number = QSpinBox()
        self.spin_section_number.setRange(1, 9999)
        self.spin_section_number.setValue(self.section_number)
        self.spin_section_number.setEnabled(False)
        custom_layout.addWidget(self.spin_section_number, 0, 3)

        # Fila 1: Ejercicio e Inciso
        custom_layout.addWidget(QLabel("Ejercicio:"), 1, 0)
        self.spin_custom_exercise = QSpinBox()
        self.spin_custom_exercise.setRange(1, 9999)
        self.spin_custom_exercise.setValue(self.exercise)
        self.spin_custom_exercise.setEnabled(False)
        custom_layout.addWidget(self.spin_custom_exercise, 1, 1)

        custom_layout.addWidget(QLabel("Inciso:"), 1, 2)
        self.spin_custom_inciso = QSpinBox()
        self.spin_custom_inciso.setRange(0, 9999)
        self.spin_custom_inciso.setSpecialValueText("Sin inciso")
        self.spin_custom_inciso.setValue(self.current_inciso or 0)
        self.spin_custom_inciso.setEnabled(False)
        custom_layout.addWidget(self.spin_custom_inciso, 1, 3)

        layout.addWidget(custom_container)

        self.radio_custom.toggled.connect(self._on_custom_toggled)

        layout.addStretch()

        # Botones de acción
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch()

        self.btn_accept = QPushButton("Aplicar y Guardar")
        primary_color = "#bef264" if self.is_dark else "#65a30d"
        text_color = "#090d16" if self.is_dark else "#ffffff"
        self.btn_accept.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary_color};
                color: {text_color};
                font-weight: 700;
                padding: 6px 18px;
                border-radius: 6px;
            }}
        """)
        self.btn_accept.clicked.connect(self._on_accept)
        btn_layout.addWidget(self.btn_accept)

        layout.addLayout(btn_layout)

    def _on_custom_toggled(self, checked: bool) -> None:
        self.combo_section_type.setEnabled(checked)
        self.spin_section_number.setEnabled(checked)
        self.spin_custom_exercise.setEnabled(checked)
        self.spin_custom_inciso.setEnabled(checked)

    def reject(self) -> None:
        self.result_action = ACTION_CANCEL
        super().reject()

    def _on_cancel(self) -> None:
        self.reject()

    def _on_accept(self) -> None:
        if self.radio_correct.isChecked():
            self.result_action = ACTION_CORRECT_ALL
            self.selected_section_type = self.section_type
            self.selected_section_number = self.section_number
            self.selected_exercise = self.exercise
            self.selected_inciso = self.current_inciso
        elif self.radio_manual.isChecked():
            self.result_action = ACTION_KEEP_MANUAL
            self.selected_section_type = self.section_type
            self.selected_section_number = self.section_number
            self.selected_exercise = self.exercise
            self.selected_inciso = self.current_inciso
        else:
            self.result_action = ACTION_CUSTOM_VALUES
            self.selected_section_type = self.combo_section_type.currentText().strip() or self.section_type
            self.selected_section_number = self.spin_section_number.value()
            self.selected_exercise = self.spin_custom_exercise.value()
            custom_inc = self.spin_custom_inciso.value()
            self.selected_inciso = None if custom_inc == 0 else custom_inc
        self.accept()

    def _format_item_datetime(self, item: TimerItem) -> str:
        try:
            dt = datetime.fromisoformat(item.created_at)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return item.created_at[:16].replace("T", " ")

    def _format_item_location(self, item: TimerItem) -> str:
        inciso_part = f"Inciso {item.inciso}" if item.inciso else "(Sin inciso)"
        return f"{item.section_type} {item.section_number} · Ej. {item.exercise} · {inciso_part}"

    def _create_status_badge(self, completed: bool) -> QLabel:
        status_text = "Completado" if completed else "Incompleto"
        status_color = "#22c55e" if completed else ("#f59e0b" if self.is_dark else "#d97706")
        status_bg = "rgba(34, 197, 94, 0.15)" if completed else ("rgba(245, 158, 11, 0.15)" if self.is_dark else "#fef3c7")
        status_border = "#16a34a" if completed else ("#b45309" if self.is_dark else "#f59e0b")

        badge = QLabel(f" {status_text} ")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {status_bg};
                color: {status_color};
                border: 1px solid {status_border};
                border-radius: 4px;
                font-weight: 700;
                font-size: 11px;
                padding: 1px 6px;
            }}
        """)
        return badge

    def _build_conflict_preview(self) -> QWidget | None:
        if not self.gap_items:
            return None

        if len(self.gap_items) == 1:
            return self._build_single_item_card(self.gap_items[0])
        return self._build_multiple_items_table(self.gap_items)

    def _build_single_item_card(self, item: TimerItem) -> QWidget:
        card = QFrame()
        card.setObjectName("conflict_preview_card")
        card_bg = "#1e293b" if self.is_dark else "#f8fafc"
        card_border = "#334155" if self.is_dark else "#cbd5e1"
        label_muted = "#94a3b8" if self.is_dark else "#64748b"

        card.setStyleSheet(f"""
            QFrame#conflict_preview_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 6px 10px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)

        title_lbl = QLabel("REGISTRO PREVIO EN CONFLICTO")
        title_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {label_muted}; letter-spacing: 0.5px; border: none; background: transparent;")
        card_layout.addWidget(title_lbl)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        date_str = self._format_item_datetime(item)
        loc_str = self._format_item_location(item)
        time_str = format_hh_mm_ss(item.exercise_time_ms)

        # Fila 0: Fecha y Tiempo neto
        lbl_date = QLabel(f"<span style='color: {label_muted};'>Fecha:</span> <b>{date_str}</b>")
        lbl_date.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        grid.addWidget(lbl_date, 0, 0)

        lbl_time = QLabel(f"<span style='color: {label_muted};'>Tiempo neto:</span> <b>{time_str}</b>")
        lbl_time.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        grid.addWidget(lbl_time, 0, 1)

        # Fila 1: Identificador y Estado
        lbl_loc = QLabel(f"<span style='color: {label_muted};'>Identificador:</span> <b>{loc_str}</b>")
        lbl_loc.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        grid.addWidget(lbl_loc, 1, 0)

        status_box = QHBoxLayout()
        status_box.setContentsMargins(0, 0, 0, 0)
        status_box.setSpacing(6)
        lbl_status_prefix = QLabel(f"<span style='color: {label_muted};'>Estado:</span>")
        lbl_status_prefix.setStyleSheet("font-size: 12px; border: none; background: transparent;")
        status_box.addWidget(lbl_status_prefix)
        status_box.addWidget(self._create_status_badge(item.completed))
        status_box.addStretch()

        grid.addLayout(status_box, 1, 1)

        card_layout.addLayout(grid)
        return card

    def _build_multiple_items_table(self, items: list[TimerItem]) -> QWidget:
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        label_muted = "#94a3b8" if self.is_dark else "#64748b"
        title_lbl = QLabel(f"REGISTROS PREVIOS EN CONFLICTO ({len(items)})")
        title_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {label_muted}; letter-spacing: 0.5px;")
        container_layout.addWidget(title_lbl)

        table = QTableWidget(len(items), 4)
        table.setObjectName("conflict_preview_table")
        table.setHorizontalHeaderLabels(["Fecha y Hora", "Identificador", "Tiempo neto", "Estado"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setShowGrid(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        table_bg = "#1e293b" if self.is_dark else "#ffffff"
        header_bg = "#0f172a" if self.is_dark else "#f1f5f9"
        grid_color = "#334155" if self.is_dark else "#e2e8f0"
        text_color = "#e2e8f0" if self.is_dark else "#0f172a"
        border_color = "#334155" if self.is_dark else "#cbd5e1"

        table.setStyleSheet(f"""
            QTableWidget#conflict_preview_table {{
                background-color: {table_bg};
                color: {text_color};
                gridline-color: {grid_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {label_muted};
                border: none;
                border-bottom: 1px solid {border_color};
                font-weight: 700;
                font-size: 10px;
                padding: 4px 6px;
            }}
        """)

        for row_idx, item in enumerate(items):
            date_item = QTableWidgetItem(self._format_item_datetime(item))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row_idx, 0, date_item)

            loc_item = QTableWidgetItem(self._format_item_location(item))
            loc_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row_idx, 1, loc_item)

            time_item = QTableWidgetItem(format_hh_mm_ss(item.exercise_time_ms))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row_idx, 2, time_item)

            badge_container = QWidget()
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(4, 2, 4, 2)
            badge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(self._create_status_badge(item.completed))
            table.setCellWidget(row_idx, 3, badge_container)

            table.setRowHeight(row_idx, 28)

        calc_height = min(140, 26 + len(items) * 28 + 4)
        table.setFixedHeight(calc_height)
        container_layout.addWidget(table)

        return container
