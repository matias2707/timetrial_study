"""Diálogos específicos de la funcionalidad de Planificador en Study Timetrial."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    ExerciseNodeStatus,
)
from domain.models import Milestone, PlannedSection, PlannerSchedule, TagDefinition
from presentation.presentation_formatters import format_milliseconds

ACTION_CANCEL = "cancel"


class PlannedSectionDialog(QDialog):
    """Formulario para agregar o editar una sección o guía en la planificación."""

    def __init__(
        self,
        parent: QWidget | None = None,
        section: PlannedSection | None = None,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.is_dark = is_dark
        self.section_data: PlannedSection | None = None
        self.setWindowTitle("Editar Sección Planificada" if section else "Nueva Sección / Guía")
        self.resize(520, 520)

        # Copia local de configuraciones de incisos: {exercise_num: incisos_count}
        self.exercise_configs: dict[int, int] = (
            dict(section.exercise_configs) if section else {}
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Datos básicos
        info_group = QGroupBox("Información de la Sección")
        info_layout = QGridLayout(info_group)
        info_layout.setSpacing(10)

        info_layout.addWidget(QLabel("Tipo de Sección:"), 0, 0)
        self.combo_type = QComboBox()
        self.combo_type.setEditable(True)
        self.combo_type.addItems(["Guía", "Sección", "Práctica", "Módulo", "Unidad", "Capítulo", "Apunte"])
        if section:
            self.combo_type.setCurrentText(section.section_type)
        else:
            self.combo_type.setCurrentText("Guía")
        info_layout.addWidget(self.combo_type, 0, 1)

        info_layout.addWidget(QLabel("Número:"), 1, 0)
        self.spin_number = QSpinBox()
        self.spin_number.setRange(1, 9999)
        self.spin_number.setValue(section.section_number if section else 1)
        info_layout.addWidget(self.spin_number, 1, 1)

        info_layout.addWidget(QLabel("Título / Descripción:"), 2, 0)
        self.edit_title = QLineEdit()
        self.edit_title.setPlaceholderText("Opcional (ej: Álgebra Lineal, Cinemática)")
        if section:
            self.edit_title.setText(section.title)
        info_layout.addWidget(self.edit_title, 2, 1)

        info_layout.addWidget(QLabel("Cantidad de Ejercicios:"), 3, 0)
        self.spin_total = QSpinBox()
        self.spin_total.setRange(1, 9999)
        self.spin_total.setValue(section.total_exercises if section else 20)
        self.spin_total.valueChanged.connect(self._on_total_exercises_changed)
        info_layout.addWidget(self.spin_total, 3, 1)

        layout.addWidget(info_group)

        # Configuración de incisos
        incisos_group = QGroupBox("Incisos por Ejercicio (Opcional)")
        incisos_layout = QVBoxLayout(incisos_group)
        incisos_layout.setSpacing(8)

        lbl_desc = QLabel(
            "Por defecto los ejercicios no tienen incisos. "
            "Si algún ejercicio específico contiene incisos, indícalo aquí:"
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        incisos_layout.addWidget(lbl_desc)

        # Controles para añadir excepción
        add_inciso_layout = QHBoxLayout()
        add_inciso_layout.addWidget(QLabel("Ejercicio:"))
        self.spin_inciso_ex = QSpinBox()
        self.spin_inciso_ex.setRange(1, self.spin_total.value())
        add_inciso_layout.addWidget(self.spin_inciso_ex)

        add_inciso_layout.addWidget(QLabel("Incisos:"))
        self.spin_inciso_count = QSpinBox()
        self.spin_inciso_count.setRange(1, 30)
        self.spin_inciso_count.setValue(4)
        add_inciso_layout.addWidget(self.spin_inciso_count)

        self.btn_set_inciso = QPushButton("Establecer")
        self.btn_set_inciso.setIcon(qta.icon("fa5s.plus", color="#bef264" if self.is_dark else "#4d7c0f"))
        self.btn_set_inciso.clicked.connect(self._add_or_update_inciso)
        add_inciso_layout.addWidget(self.btn_set_inciso)
        incisos_layout.addLayout(add_inciso_layout)

        # Tabla de incisos configurados
        self.table_incisos = QTableWidget(0, 3)
        self.table_incisos.setHorizontalHeaderLabels(["Ejercicio", "Incisos Configurados", "Acción"])
        self.table_incisos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_incisos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_incisos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_incisos.verticalHeader().setVisible(False)
        self.table_incisos.setMaximumHeight(160)
        incisos_layout.addWidget(self.table_incisos)

        layout.addWidget(incisos_group)

        # Botones de guardar / cancelar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Sección")
        btn_save.setIcon(qta.icon("fa5s.check", color="#bef264" if self.is_dark else "#4d7c0f"))
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._validate_and_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

        self._refresh_incisos_table()

    def _on_total_exercises_changed(self, val: int) -> None:
        self.spin_inciso_ex.setMaximum(val)

    def _add_or_update_inciso(self) -> None:
        ex = self.spin_inciso_ex.value()
        count = self.spin_inciso_count.value()
        if count <= 0:
            self.exercise_configs.pop(ex, None)
        else:
            self.exercise_configs[ex] = count
        self._refresh_incisos_table()

    def _remove_inciso(self, ex: int) -> None:
        self.exercise_configs.pop(ex, None)
        self._refresh_incisos_table()

    def _refresh_incisos_table(self) -> None:
        self.table_incisos.setRowCount(len(self.exercise_configs))
        sorted_ex = sorted(self.exercise_configs.keys())
        for row, ex in enumerate(sorted_ex):
            cnt = self.exercise_configs[ex]
            item_ex = QTableWidgetItem(f"Ejercicio {ex}")
            item_ex.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_incisos.setItem(row, 0, item_ex)

            # Muestra los números de incisos: ej. 1, 2, 3, 4 (o 4.1 .. 4.4)
            inciso_labels = ", ".join(f"{ex}.{i}" for i in range(1, cnt + 1))
            item_cnt = QTableWidgetItem(f"{cnt} incisos ({inciso_labels})")
            self.table_incisos.setItem(row, 1, item_cnt)

            btn_del = QPushButton("Eliminar")
            btn_del.setStyleSheet("padding: 2px 6px; font-size: 11px;")
            btn_del.clicked.connect(lambda _, e=ex: self._remove_inciso(e))
            self.table_incisos.setCellWidget(row, 2, btn_del)

    def _validate_and_save(self) -> None:
        sec_type = self.combo_type.currentText().strip()
        if not sec_type:
            QMessageBox.warning(self, "Campo requerido", "El tipo de sección no puede estar vacío.")
            return

        total = self.spin_total.value()
        # Filtrar configuraciones de incisos que superen el nuevo total
        cleaned_configs = {
            ex: cnt for ex, cnt in self.exercise_configs.items() if ex <= total
        }

        self.section_data = PlannedSection(
            section_type=sec_type,
            section_number=self.spin_number.value(),
            title=self.edit_title.text().strip(),
            total_exercises=total,
            exercise_configs=cleaned_configs,
        )
        self.accept()


class ExerciseDetailPopup(QDialog):
    """Ventana emergente que muestra la información detallada de un ejercicio y opciones."""

    action_triggered = Signal(str, object)  # (action_name, node)

    def __init__(
        self,
        parent: QWidget | None,
        node: ExerciseNodeStatus,
        app_service: Any = None,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.node = node
        self.is_dark = is_dark
        self.app_service = app_service or getattr(parent, "app_service", None)
        self.chosen_action = ACTION_CANCEL

        self.setWindowTitle(f"Detalle · {node.full_label}")
        self.resize(480, 460)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Encabezado con estado
        header_card = QFrame()
        header_card.setObjectName("detail_header_card")
        header_card.setStyleSheet(
            f"""
            QFrame#detail_header_card {{
                background-color: {"#131d2e" if is_dark else "#f1f5f9"};
                border: 1px solid {"#1e293b" if is_dark else "#cbd5e1"};
                border-radius: 10px;
                padding: 12px;
            }}
            """
        )
        h_layout = QHBoxLayout(header_card)

        v_title = QVBoxLayout()
        lbl_title = QLabel(node.full_label)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        v_title.addWidget(lbl_title)

        if node.has_incisos:
            lbl_sub = QLabel(f"Compuesto por {len(node.incisos)} incisos numéricos")
            lbl_sub.setStyleSheet("color: #94a3b8; font-size: 11px;")
            v_title.addWidget(lbl_sub)
        h_layout.addLayout(v_title)

        h_layout.addStretch()

        # Badge de estado
        badge = QLabel()
        if node.status == STATUS_COMPLETED:
            badge.setText("  Completado  ")
            badge.setStyleSheet(
                "background-color: #14532d; color: #86efac; border: 1px solid #22c55e; "
                "border-radius: 12px; padding: 4px 10px; font-weight: 700; font-size: 12px;"
            )
        elif node.status == STATUS_FAILED:
            badge.setText("  En dificultad  ")
            badge.setStyleSheet(
                "background-color: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; "
                "border-radius: 12px; padding: 4px 10px; font-weight: 700; font-size: 12px;"
            )
        else:
            badge.setText("  No hecho  ")
            badge.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; border: 1px solid #475569; "
                "border-radius: 12px; padding: 4px 10px; font-weight: 600; font-size: 12px;"
            )
        h_layout.addWidget(badge)

        layout.addWidget(header_card)

        # Métricas principales en Bento Grid
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(8)

        def make_metric_card(label: str, value: str) -> QFrame:
            f = QFrame()
            f.setStyleSheet(
                f"""
                background-color: {"#0f172a" if is_dark else "#f8fafc"};
                border: 1px solid {"#1e293b" if is_dark else "#e2e8f0"};
                border-radius: 8px;
                padding: 8px;
                """
            )
            v = QVBoxLayout(f)
            v.setContentsMargins(4, 4, 4, 4)
            v.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
            val = QLabel(value)
            val.setStyleSheet("font-size: 14px; font-weight: 700;")
            v.addWidget(lbl)
            v.addWidget(val)
            return f

        attempts_text = f"{node.attempts} intentos"
        if node.attempts > 0:
            attempts_text += f" ({node.completed_attempts} hechos, {node.failed_attempts} fallados)"

        metrics_grid.addWidget(make_metric_card("Intentos Registrados", attempts_text), 0, 0)
        metrics_grid.addWidget(
            make_metric_card("Tiempo Ejercicio", format_milliseconds(node.exercise_time_ms)), 0, 1
        )
        metrics_grid.addWidget(
            make_metric_card("Tiempo Descanso", format_milliseconds(node.break_time_ms)), 1, 0
        )
        metrics_grid.addWidget(
            make_metric_card("Tiempo Total Invertido", format_milliseconds(node.total_time_ms)), 1, 1
        )

        layout.addLayout(metrics_grid)

        # Marcadores / Etiquetas
        if self.app_service:
            tag_group = QGroupBox("Marcadores / Etiquetas")
            tag_layout = QVBoxLayout(tag_group)
            tag_layout.setSpacing(6)

            self.tag_checkboxes_layout = QHBoxLayout()
            self.tag_checkboxes_layout.setSpacing(10)
            self.tag_checkboxes: dict[str, QCheckBox] = {}
            self._render_detail_tags()
            tag_layout.addLayout(self.tag_checkboxes_layout)

            btn_manage_tags = QPushButton("⚙️ Gestionar Catálogo de Etiquetas...")
            btn_manage_tags.setStyleSheet("font-size: 11px; text-align: left; padding: 2px;")
            btn_manage_tags.clicked.connect(self._on_manage_catalog_from_detail)
            tag_layout.addWidget(btn_manage_tags)

            layout.addWidget(tag_group)

        # Si el ejercicio tiene incisos, lista de incisos
        if node.has_incisos and node.incisos:
            inc_group = QGroupBox("Estado de los Incisos")
            inc_layout = QVBoxLayout(inc_group)
            inc_layout.setSpacing(4)
            for sub in node.incisos:
                row_h = QHBoxLayout()
                row_h.addWidget(QLabel(f"Inciso {sub.inciso}:"))
                if sub.status == STATUS_COMPLETED:
                    st_lbl = QLabel("✅ Completado")
                    st_lbl.setStyleSheet("color: #86efac; font-weight: 600;")
                elif sub.status == STATUS_FAILED:
                    st_lbl = QLabel("⚠️ Fallado")
                    st_lbl.setStyleSheet("color: #fca5a5; font-weight: 600;")
                else:
                    st_lbl = QLabel("⏳ No hecho")
                    st_lbl.setStyleSheet("color: #94a3b8;")
                row_h.addWidget(st_lbl)
                row_h.addStretch()
                row_h.addWidget(QLabel(format_milliseconds(sub.exercise_time_ms)))
                inc_layout.addLayout(row_h)
            layout.addWidget(inc_group)

        # Notas y Apuntes del Ejercicio
        notes_group = QGroupBox("Notas y Apuntes del Ejercicio")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setSpacing(6)

        current_note = ""
        if self.app_service:
            current_note = self.app_service.get_exercise_note(
                node.section_type, node.section_number, node.exercise, node.inciso
            )
        if not current_note and node.note:
            current_note = node.note

        # Visor Markdown y Editor
        self.notes_browser = QTextBrowser()
        self.notes_browser.setMinimumHeight(65)
        self.notes_browser.setMaximumHeight(110)
        self.notes_browser.setStyleSheet(
            f"""
            QTextBrowser {{
                background-color: {"#0f172a" if is_dark else "#f8fafc"};
                color: {"#f1f5f9" if is_dark else "#0f172a"};
                border: 1px solid {"#334155" if is_dark else "#cbd5e1"};
                border-radius: 6px;
                padding: 6px;
                font-size: 12px;
            }}
            """
        )
        if current_note:
            self.notes_browser.setMarkdown(current_note)
        else:
            self.notes_browser.setHtml(
                "<p style='color: #64748b; font-style: italic; font-size: 11px;'>Sin notas registradas para este ejercicio.</p>"
            )
        notes_layout.addWidget(self.notes_browser)

        # Editor rápido para compatibilidad
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(
            "Escribe notas, fórmulas clave, advertencias o dudas sobre este ejercicio..."
        )
        self.notes_edit.setPlainText(current_note)
        self.notes_edit.setVisible(False)
        notes_layout.addWidget(self.notes_edit)

        notes_bar = QHBoxLayout()
        self.notes_feedback_label = QLabel("")
        self.notes_feedback_label.setStyleSheet("color: #10b981; font-weight: 600; font-size: 11px;")
        notes_bar.addWidget(self.notes_feedback_label)
        notes_bar.addStretch()

        btn_edit_markdown = QPushButton("✏️ Editar con Formato (Markdown)")
        btn_edit_markdown.setStyleSheet(
            """
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            """
        )
        btn_edit_markdown.clicked.connect(self._on_open_markdown_editor)
        notes_bar.addWidget(btn_edit_markdown)

        btn_save_note = QPushButton("💾 Guardar Apunte")
        btn_save_note.setStyleSheet(
            """
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            """
        )
        btn_save_note.setVisible(False)
        btn_save_note.clicked.connect(self._on_save_note)
        notes_bar.addWidget(btn_save_note)
        notes_layout.addLayout(notes_bar)

        if node.comments:
            comm_sub_group = QGroupBox(f"Historial de Comentarios de Intentos ({len(node.comments)})")
            comm_sub_layout = QVBoxLayout(comm_sub_group)
            comm_sub_layout.setContentsMargins(4, 4, 4, 4)
            comm_scroll = QScrollArea()
            comm_scroll.setWidgetResizable(True)
            comm_scroll.setMaximumHeight(60)
            comm_inner = QWidget()
            comm_in_lay = QVBoxLayout(comm_inner)
            comm_in_lay.setContentsMargins(4, 4, 4, 4)
            comm_in_lay.setSpacing(2)
            for c in node.comments:
                c_lbl = QLabel(f"• {c}")
                c_lbl.setWordWrap(True)
                c_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
                comm_in_lay.addWidget(c_lbl)
            comm_scroll.setWidget(comm_inner)
            comm_sub_layout.addWidget(comm_scroll)
            notes_layout.addWidget(comm_sub_group)

        layout.addWidget(notes_group)

        # Botones de acción
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_timer = QPushButton("⏱️ Cargar en Cronómetro")
        btn_timer.setStyleSheet(
            """
            QPushButton {
                background-color: #bef264;
                color: #0f172a;
                font-weight: 700;
                padding: 8px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #a3e635;
            }
            """
        )
        btn_timer.clicked.connect(self._on_load_timer)
        actions_layout.addWidget(btn_timer)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.reject)
        actions_layout.addWidget(btn_close)

        layout.addLayout(actions_layout)

    def _on_open_markdown_editor(self) -> None:
        if not self.app_service:
            return
        dlg = ExerciseNoteDialog(
            parent=self,
            app_service=self.app_service,
            section_type=self.node.section_type,
            section_number=self.node.section_number,
            exercise=self.node.exercise,
            inciso=self.node.inciso,
            is_dark=self.is_dark,
        )
        if dlg.exec() == ExerciseNoteDialog.DialogCode.Accepted:
            updated = self.app_service.get_exercise_note(
                self.node.section_type,
                self.node.section_number,
                self.node.exercise,
                self.node.inciso,
            )
            self.notes_edit.setPlainText(updated)
            if updated.strip():
                self.notes_browser.setMarkdown(updated)
            else:
                self.notes_browser.setHtml(
                    "<p style='color: #64748b; font-style: italic; font-size: 11px;'>Sin notas registradas para este ejercicio.</p>"
                )
            self.node.note = updated
            self.node.has_note = bool(updated.strip())
            self.notes_feedback_label.setText("✓ Apunte guardado")

    def _on_save_note(self) -> None:
        if not self.app_service:
            return
        text = self.notes_edit.toPlainText().strip()
        self.app_service.set_exercise_note(
            self.node.section_type,
            self.node.section_number,
            self.node.exercise,
            self.node.inciso,
            text,
        )
        self.node.note = text
        self.node.has_note = bool(text)
        if text:
            self.notes_browser.setMarkdown(text)
        else:
            self.notes_browser.setHtml(
                "<p style='color: #64748b; font-style: italic; font-size: 11px;'>Sin notas registradas para este ejercicio.</p>"
            )
        self.notes_feedback_label.setText("✓ Apunte guardado")

    def _render_detail_tags(self) -> None:
        if not self.app_service:
            return
        while self.tag_checkboxes_layout.count():
            it = self.tag_checkboxes_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.tag_checkboxes.clear()

        catalog = self.app_service.get_tag_catalog()
        current_tags = set(
            self.app_service.get_exercise_tags(
                self.node.section_type,
                self.node.section_number,
                self.node.exercise,
                self.node.inciso,
            )
        )

        for tag in catalog:
            cb = QCheckBox(f"● {tag.name}")
            cb.setStyleSheet(f"QCheckBox {{ font-size: 12px; font-weight: 600; color: {tag.color}; }}")
            cb.setChecked(tag.id in current_tags)
            cb.toggled.connect(self._on_tag_toggled)
            self.tag_checkboxes_layout.addWidget(cb)
            self.tag_checkboxes[tag.id] = cb

        self.tag_checkboxes_layout.addStretch()

    def _on_tag_toggled(self) -> None:
        if not self.app_service:
            return
        selected_ids = [tid for tid, cb in self.tag_checkboxes.items() if cb.isChecked()]
        self.app_service.set_exercise_tags(
            self.node.section_type,
            self.node.section_number,
            self.node.exercise,
            self.node.inciso,
            selected_ids,
        )
        tag_map = {t.id: t for t in self.app_service.get_tag_catalog()}
        self.node.tags = [tag_map[tid] for tid in selected_ids if tid in tag_map]

    def _on_manage_catalog_from_detail(self) -> None:
        dlg = TagManagerDialog(self, self.app_service, is_dark=self.is_dark)
        dlg.exec()
        self._render_detail_tags()

    def _on_load_timer(self) -> None:
        self.chosen_action = "load_timer"
        self.accept()


class TagManagerDialog(QDialog):
    """Diálogo para configurar el catálogo de etiquetas y marcadores de la materia."""

    def __init__(
        self,
        parent: QWidget | None,
        app_service: Any,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.app_service = app_service
        self.is_dark = is_dark
        self.setWindowTitle("Catálogo de Marcadores y Etiquetas")
        self.resize(520, 440)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl_info = QLabel("Personaliza los nombres y colores de las etiquetas de estudio para esta materia:")
        lbl_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(lbl_info)

        # Tabla de etiquetas
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Color", "Nombre", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_table_item_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table)

        # Panel para agregar nueva etiqueta
        add_group = QGroupBox("Añadir Nueva Etiqueta")
        add_lay = QHBoxLayout(add_group)
        add_lay.setSpacing(8)

        self.edit_new_name = QLineEdit()
        self.edit_new_name.setPlaceholderText("Nombre de la etiqueta (ej. Consultar docente)")
        add_lay.addWidget(self.edit_new_name, 1)

        self.selected_color = "#3b82f6"
        self.btn_color_pick = QPushButton("  Color  ")
        self._update_color_pick_button()
        self.btn_color_pick.clicked.connect(self._on_pick_color)
        add_lay.addWidget(self.btn_color_pick)

        btn_add = QPushButton("Añadir")
        btn_add.setIcon(qta.icon("fa5s.plus", color="#bef264" if is_dark else "#4d7c0f"))
        btn_add.clicked.connect(self._on_add_tag)
        add_lay.addWidget(btn_add)

        layout.addWidget(add_group)

        # Botón cerrar
        btn_close_lay = QHBoxLayout()
        btn_close_lay.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_close_lay.addWidget(btn_close)
        layout.addLayout(btn_close_lay)

        self._refresh_table()

    def _update_color_pick_button(self) -> None:
        self.btn_color_pick.setStyleSheet(
            f"background-color: {self.selected_color}; color: #ffffff; font-weight: 700; border-radius: 4px; padding: 4px 10px;"
        )

    def _on_pick_color(self) -> None:
        c = QColorDialog.getColor(QColor(self.selected_color), self, "Seleccionar Color de Etiqueta")
        if c.isValid():
            self.selected_color = c.name()
            self._update_color_pick_button()

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        tags = self.app_service.get_tag_catalog()
        for row_idx, tag in enumerate(tags):
            self.table.insertRow(row_idx)

            # Botón / badge de color para cambiar color
            btn_col = QPushButton("●")
            btn_col.setStyleSheet(f"color: {tag.color}; font-size: 20px; border: none; background: transparent;")
            btn_col.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_col.setToolTip("Haz clic para cambiar el color")
            btn_col.clicked.connect(lambda _, t=tag: self._on_change_tag_color(t))
            self.table.setCellWidget(row_idx, 0, btn_col)

            # Nombre (editable directamente en celda o con doble clic)
            item_name = QTableWidgetItem(tag.name)
            item_name.setData(Qt.ItemDataRole.UserRole, tag.id)
            item_name.setData(Qt.ItemDataRole.UserRole + 1, tag.name)
            item_name.setToolTip("Doble clic para editar en la tabla o usa el botón Editar")
            self.table.setItem(row_idx, 1, item_name)

            # Acciones: Editar, Eliminar
            w_actions = QWidget()
            h_act = QHBoxLayout(w_actions)
            h_act.setContentsMargins(4, 2, 4, 2)
            h_act.setSpacing(4)

            btn_edit = QPushButton()
            btn_edit.setIcon(qta.icon("fa5s.edit", color="#94a3b8"))
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setToolTip("Renombrar etiqueta (un clic)")
            btn_edit.clicked.connect(lambda _, t=tag: self._on_edit_tag_name(t))
            h_act.addWidget(btn_edit)

            btn_del = QPushButton()
            btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#ef4444"))
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setToolTip("Eliminar etiqueta")
            btn_del.clicked.connect(lambda _, t=tag: self._on_delete_tag(t))
            h_act.addWidget(btn_del)

            self.table.setCellWidget(row_idx, 2, w_actions)
        self.table.blockSignals(False)

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Persiste inmediatamente cambios hechos escribiendo directamente en la celda de nombre."""
        if item.column() != 1:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        if not tag_id:
            return
        new_name = item.text().strip()
        old_name = item.data(Qt.ItemDataRole.UserRole + 1) or ""
        if not new_name:
            # Revertir al nombre anterior si se deja vacío
            self.table.blockSignals(True)
            item.setText(old_name)
            self.table.blockSignals(False)
            return
        if new_name == old_name:
            return
        catalog = {t.id: t for t in self.app_service.get_tag_catalog()}
        tag = catalog.get(tag_id)
        if tag:
            self.app_service.update_tag_definition(tag_id, new_name, tag.color)
            item.setData(Qt.ItemDataRole.UserRole + 1, new_name)
            self.table.blockSignals(True)
            item.setText(new_name)
            self.table.blockSignals(False)

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        """Gestiona la interacción de doble clic según la columna pulsada."""
        if col == 0:
            tags = self.app_service.get_tag_catalog()
            if 0 <= row < len(tags):
                self._on_change_tag_color(tags[row])
        elif col == 1:
            item = self.table.item(row, col)
            if item:
                self.table.editItem(item)

    def _on_change_tag_color(self, tag: TagDefinition) -> None:
        c = QColorDialog.getColor(QColor(tag.color), self, f"Color para '{tag.name}'")
        if c.isValid():
            self.app_service.update_tag_definition(tag.id, tag.name, c.name())
            self._refresh_table()

    def _on_edit_tag_name(self, tag: TagDefinition) -> None:
        new_name, ok = QInputDialog.getText(self, "Renombrar Etiqueta", "Nuevo nombre:", text=tag.name)
        if ok and new_name.strip():
            self.app_service.update_tag_definition(tag.id, new_name.strip(), tag.color)
            self._refresh_table()

    def _on_delete_tag(self, tag: TagDefinition) -> None:
        confirm = QMessageBox.question(
            self,
            "Eliminar Etiqueta",
            f"¿Deseas eliminar la etiqueta '{tag.name}' del catálogo?\n\n"
            "Se quitará de todos los ejercicios donde esté asignada.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.app_service.delete_tag_definition(tag.id)
            self._refresh_table()

    def _on_add_tag(self) -> None:
        name = self.edit_new_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Campo Vacío", "Por favor ingresa un nombre para la etiqueta.")
            return
        self.app_service.add_tag_definition(name, self.selected_color)
        self.edit_new_name.clear()
        self._refresh_table()


class TagSelectionDialog(QDialog):
    """Diálogo compacto para seleccionar etiquetas asignadas a una ubicación de ejercicio."""

    def __init__(
        self,
        parent: QWidget | None,
        app_service: Any,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.app_service = app_service
        self.section_type = section_type
        self.section_number = section_number
        self.exercise = exercise
        self.inciso = inciso
        self.is_dark = is_dark

        label_target = f"{section_type} {section_number} · Ejercicio {exercise}"
        if inciso:
            label_target += f".{inciso}"

        self.setWindowTitle(f"Marcadores · {label_target}")
        self.resize(380, 320)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_desc = QLabel(f"Asigna o desasigna marcadores para:\n<b>{label_target}</b>")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        # Área de checkboxes con scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.v_checks = QVBoxLayout(self.scroll_content)
        self.v_checks.setSpacing(8)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        self.checkboxes: dict[str, QCheckBox] = {}
        self._populate_checkboxes()

        # Botón para gestionar catálogo
        btn_manage = QPushButton("⚙️ Gestionar Catálogo de Etiquetas...")
        btn_manage.setStyleSheet("font-size: 11px; text-align: left; padding: 4px;")
        btn_manage.clicked.connect(self._on_manage_catalog)
        layout.addWidget(btn_manage)

        # Botones inferiores
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Marcadores")
        btn_save.setStyleSheet(
            """
            QPushButton {
                background-color: #bef264;
                color: #0f172a;
                font-weight: 700;
                padding: 6px 14px;
                border-radius: 6px;
            }
            """
        )
        btn_save.clicked.connect(self._on_save)
        btn_lay.addWidget(btn_save)

        layout.addLayout(btn_lay)

    def _populate_checkboxes(self) -> None:
        while self.v_checks.count():
            item = self.v_checks.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes.clear()

        catalog = self.app_service.get_tag_catalog()
        current_tags = set(
            self.app_service.get_exercise_tags(
                self.section_type, self.section_number, self.exercise, self.inciso
            )
        )

        for tag in catalog:
            cb = QCheckBox(f"  ●  {tag.name}")
            cb.setStyleSheet(f"QCheckBox {{ font-size: 13px; font-weight: 600; color: {tag.color}; }}")
            cb.setChecked(tag.id in current_tags)
            self.v_checks.addWidget(cb)
            self.checkboxes[tag.id] = cb

        self.v_checks.addStretch()

    def _on_manage_catalog(self) -> None:
        dlg = TagManagerDialog(self, self.app_service, is_dark=self.is_dark)
        dlg.exec()
        self._populate_checkboxes()

    def _on_save(self) -> None:
        selected_ids = [tag_id for tag_id, cb in self.checkboxes.items() if cb.isChecked()]
        self.app_service.set_exercise_tags(
            self.section_type, self.section_number, self.exercise, self.inciso, selected_ids
        )
        self.accept()


class ExerciseNoteDialog(QDialog):
    """Diálogo modal para editar el bloc de notas / apuntes de un ejercicio o inciso con soporte Markdown."""

    def __init__(
        self,
        parent: QWidget | None,
        app_service: Any,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None = None,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.app_service = app_service
        self.section_type = section_type
        self.section_number = section_number
        self.exercise = exercise
        self.inciso = inciso
        self.is_dark = is_dark

        label_target = f"{section_type} {section_number} · Ejercicio {exercise}"
        if inciso is not None and inciso > 0:
            label_target += f".{inciso}"

        self.setWindowTitle(f"Notas · {label_target}")
        self.resize(540, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_desc = QLabel(f"📝 <b>Apuntes del ejercicio: {label_target}</b>")
        lbl_desc.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl_desc)

        # Pestañas: Editor y Vista Previa
        self.tabs = QTabWidget()
        self.tabs.setObjectName("markdown_note_tabs")

        # --- Pestaña 1: Editor con Barra de Herramientas ---
        tab_edit = QWidget()
        edit_layout = QVBoxLayout(tab_edit)
        edit_layout.setContentsMargins(8, 8, 8, 8)
        edit_layout.setSpacing(6)

        # Barra de herramientas Markdown
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)

        tb_style = f"""
            QPushButton {{
                background-color: {"#1e293b" if is_dark else "#f1f5f9"};
                color: {"#f1f5f9" if is_dark else "#1e293b"};
                border: 1px solid {"#334155" if is_dark else "#cbd5e1"};
                border-radius: 4px;
                font-size: 12px;
                min-width: 28px;
                max-width: 32px;
                height: 26px;
                padding: 0px 2px;
            }}
            QPushButton:hover {{
                background-color: {"#334155" if is_dark else "#e2e8f0"};
                border-color: #38bdf8;
            }}
        """

        self.btn_h = QPushButton("H")
        self.btn_h.setToolTip("Encabezado / Título (### )")
        self.btn_h.setStyleSheet(tb_style + "QPushButton { font-weight: 800; }")
        self.btn_h.clicked.connect(lambda: self._apply_line_prefix("### "))
        toolbar.addWidget(self.btn_h)

        self.btn_bold = QPushButton("B")
        self.btn_bold.setToolTip("Negrita (**texto**)")
        self.btn_bold.setStyleSheet(tb_style + "QPushButton { font-weight: 800; }")
        self.btn_bold.clicked.connect(lambda: self._apply_inline_format("**", "**", "texto en negrita"))
        toolbar.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setToolTip("Cursiva (*texto*)")
        self.btn_italic.setStyleSheet(tb_style + "QPushButton { font-style: italic; font-weight: 700; }")
        self.btn_italic.clicked.connect(lambda: self._apply_inline_format("*", "*", "texto en cursiva"))
        toolbar.addWidget(self.btn_italic)

        self.btn_strike = QPushButton("S")
        self.btn_strike.setToolTip("Tachado (~~texto~~)")
        self.btn_strike.setStyleSheet(tb_style)
        self.btn_strike.clicked.connect(lambda: self._apply_inline_format("~~", "~~", "texto tachado"))
        toolbar.addWidget(self.btn_strike)

        toolbar.addSpacing(6)

        self.btn_bullet = QPushButton("•")
        self.btn_bullet.setToolTip("Lista con viñetas (- )")
        self.btn_bullet.setStyleSheet(tb_style + "QPushButton { font-size: 14px; font-weight: 800; }")
        self.btn_bullet.clicked.connect(lambda: self._apply_line_prefix("- "))
        toolbar.addWidget(self.btn_bullet)

        self.btn_number = QPushButton("1.")
        self.btn_number.setToolTip("Lista numerada (1. )")
        self.btn_number.setStyleSheet(tb_style + "QPushButton { font-weight: 700; }")
        self.btn_number.clicked.connect(lambda: self._apply_line_prefix("1. "))
        toolbar.addWidget(self.btn_number)

        self.btn_quote = QPushButton(">")
        self.btn_quote.setToolTip("Cita / Destacado (> )")
        self.btn_quote.setStyleSheet(tb_style + "QPushButton { font-weight: 800; }")
        self.btn_quote.clicked.connect(lambda: self._apply_line_prefix("> "))
        toolbar.addWidget(self.btn_quote)

        toolbar.addSpacing(6)

        self.btn_code = QPushButton("</>")
        self.btn_code.setToolTip("Código inline (`código`) o bloque de código")
        self.btn_code.setStyleSheet(tb_style + "QPushButton { font-weight: 700; }")
        self.btn_code.clicked.connect(self._apply_code_format)
        toolbar.addWidget(self.btn_code)

        self.btn_hr = QPushButton("—")
        self.btn_hr.setToolTip("Separador horizontal (---)")
        self.btn_hr.setStyleSheet(tb_style)
        self.btn_hr.clicked.connect(self._insert_hr)
        toolbar.addWidget(self.btn_hr)

        toolbar.addStretch()
        edit_layout.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Escribe notas, fórmulas, recordatorios o dudas en Markdown...\n"
            "Usa la barra de herramientas para aplicar títulos, negrita, listas o código."
        )
        existing = ""
        if self.app_service:
            existing = self.app_service.get_exercise_note(
                self.section_type, self.section_number, self.exercise, self.inciso
            )
        self.editor.setPlainText(existing)
        self.editor.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background-color: {"#0f172a" if is_dark else "#f8fafc"};
                color: {"#f1f5f9" if is_dark else "#0f172a"};
                border: 1.5px solid {"#334155" if is_dark else "#cbd5e1"};
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }}
            QPlainTextEdit:focus {{
                border-color: #38bdf8;
            }}
            """
        )
        edit_layout.addWidget(self.editor, 1)
        self.tabs.addTab(tab_edit, "✏️ Redactar")

        # --- Pestaña 2: Vista Previa Markdown ---
        tab_preview = QWidget()
        preview_layout = QVBoxLayout(tab_preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet(
            f"""
            QTextBrowser {{
                background-color: {"#0f172a" if is_dark else "#f8fafc"};
                color: {"#f1f5f9" if is_dark else "#0f172a"};
                border: 1.5px solid {"#334155" if is_dark else "#cbd5e1"};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }}
            """
        )
        preview_layout.addWidget(self.preview_browser, 1)
        self.tabs.addTab(tab_preview, "👁️ Vista previa")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 1)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)

        btn_save = QPushButton("Guardar Apuntes")
        btn_save.setStyleSheet(
            """
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 700;
                padding: 6px 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            """
        )
        btn_save.clicked.connect(self._on_save)
        btn_lay.addWidget(btn_save)

        layout.addLayout(btn_lay)

    def _apply_inline_format(self, prefix: str, suffix: str, placeholder: str = "texto") -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(f"{prefix}{selected}{suffix}")
        else:
            pos = cursor.position()
            cursor.insertText(f"{prefix}{placeholder}{suffix}")
            cursor.setPosition(pos + len(prefix))
            cursor.setPosition(pos + len(prefix) + len(placeholder), QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _apply_line_prefix(self, prefix: str) -> None:
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(prefix)
        self.editor.setFocus()

    def _apply_code_format(self) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            if "\n" in selected or "\u2029" in selected:
                cursor.insertText(f"```\n{selected}\n```\n")
            else:
                cursor.insertText(f"`{selected}`")
        else:
            self._apply_inline_format("`", "`", "código")
        self.editor.setFocus()

    def _insert_hr(self) -> None:
        cursor = self.editor.textCursor()
        cursor.insertText("\n---\n")
        self.editor.setFocus()

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            raw = self.editor.toPlainText().strip()
            if not raw:
                self.preview_browser.setHtml(
                    "<p style='color: #64748b; font-style: italic;'>Sin contenido para previsualizar. Escribe notas en la pestaña 'Redactar'.</p>"
                )
            else:
                from infrastructure.compatibility import convert_plain_text_to_markdown
                self.preview_browser.setMarkdown(convert_plain_text_to_markdown(raw))

    def _on_save(self) -> None:
        note_text = self.editor.toPlainText().strip()
        if self.app_service:
            self.app_service.set_exercise_note(
                self.section_type, self.section_number, self.exercise, self.inciso, note_text
            )
        self.accept()


class ScheduleConfigDialog(QDialog):
    """Diálogo modal para configurar el período de cursada y los hitos evaluativos."""

    def __init__(
        self,
        parent: QWidget | None = None,
        schedule: PlannerSchedule | None = None,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.is_dark = is_dark
        self.schedule = schedule or PlannerSchedule()
        self.milestones: list[Milestone] = [
            Milestone(m.name, m.date, m.type, m.color, m.icon) for m in self.schedule.milestones
        ]

        self.setWindowTitle("Cronograma de Cursada")
        self.resize(680, 540)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # 1. Cabecera
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel()
        icon_color = "#38bdf8" if self.is_dark else "#0284c7"
        icon_lbl.setPixmap(qta.icon("fa5s.calendar-alt", color=icon_color).pixmap(32, 32))
        header.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignTop)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        title_lbl = QLabel("Cronograma y Período de Cursada")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        v_head.addWidget(title_lbl)

        sub_lbl = QLabel(
            "Configura el período de cursada y tus fechas de examen para activar el mapa de calor adaptativo y la cuenta regresiva."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        v_head.addWidget(sub_lbl)
        header.addLayout(v_head)
        layout.addLayout(header)

        # 2. Grupo: Período Académico
        period_group = QGroupBox("Período Académico")
        period_grid = QGridLayout(period_group)
        period_grid.setHorizontalSpacing(16)
        period_grid.setVerticalSpacing(10)

        period_grid.addWidget(QLabel("Modalidad:"), 0, 0)
        self.combo_period = QComboBox()
        self.combo_period.addItems(["Cuatrimestral", "Bimestral", "Semestral", "Personalizado"])
        self.combo_period.setCurrentText(self.schedule.period_type or "Cuatrimestral")
        self.combo_period.currentTextChanged.connect(self._on_period_type_changed)
        period_grid.addWidget(self.combo_period, 0, 1)

        period_grid.addWidget(QLabel("Fecha de inicio:"), 1, 0)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        if self.schedule.start_date:
            self.date_start.setDate(QDate.fromString(self.schedule.start_date, "yyyy-MM-dd"))
        else:
            self.date_start.setDate(QDate.currentDate())
        self.date_start.dateChanged.connect(self._on_start_date_changed)
        period_grid.addWidget(self.date_start, 1, 1)

        period_grid.addWidget(QLabel("Fecha de finalización:"), 1, 2)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        if self.schedule.end_date:
            self.date_end.setDate(QDate.fromString(self.schedule.end_date, "yyyy-MM-dd"))
        else:
            self.date_end.setDate(self.date_start.date().addDays(112))  # 16 semanas por defecto
        period_grid.addWidget(self.date_end, 1, 3)

        layout.addWidget(period_group)

        # 3. Grupo: Hitos Evaluativos y Exámenes
        milestones_group = QGroupBox("Hitos Evaluativos y Exámenes (Parciales, Recuperatorios, Finales, TPs)")
        m_layout = QVBoxLayout(milestones_group)
        m_layout.setSpacing(8)

        # Toolbar para hitos
        m_toolbar = QHBoxLayout()
        m_toolbar.setSpacing(8)

        self.btn_add_milestone = QPushButton(" Agregar Hito...")
        self.btn_add_milestone.setIcon(qta.icon("fa5s.plus", color="#bef264"))
        self.btn_add_milestone.clicked.connect(self._on_add_milestone)
        m_toolbar.addWidget(self.btn_add_milestone)

        self.btn_remove_milestone = QPushButton(" Eliminar")
        self.btn_remove_milestone.setIcon(qta.icon("fa5s.trash-alt", color="#ef4444"))
        self.btn_remove_milestone.clicked.connect(self._on_remove_milestone)
        m_toolbar.addWidget(self.btn_remove_milestone)

        m_toolbar.addStretch()
        m_layout.addLayout(m_toolbar)

        # Tabla de hitos (5 columnas: Nombre, Fecha, Ícono, Color, Tipo)
        self.table_milestones = QTableWidget(0, 5)
        self.table_milestones.setHorizontalHeaderLabels(["Nombre del Hito", "Fecha", "Ícono", "Color", "Tipo"])
        self.table_milestones.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_milestones.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_milestones.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_milestones.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_milestones.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_milestones.verticalHeader().setVisible(False)
        self.table_milestones.setMinimumHeight(140)
        m_layout.addWidget(self.table_milestones)

        layout.addWidget(milestones_group)

        self._populate_milestones_table()

        # 4. Botones de acción inferiores
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_clear = QPushButton("Desactivar Cronograma")
        self.btn_clear.setToolTip("Elimina la configuración de cursada de este registro")
        self.btn_clear.clicked.connect(self._on_clear_schedule)
        btn_layout.addWidget(self.btn_clear)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Guardar Cronograma")
        primary_color = "#bef264" if self.is_dark else "#65a30d"
        text_color = "#090d16" if self.is_dark else "#ffffff"
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary_color};
                color: {text_color};
                font-weight: 700;
                padding: 6px 18px;
                border-radius: 6px;
            }}
        """)
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def _on_period_type_changed(self, period_type: str) -> None:
        start = self.date_start.date()
        if period_type == "Bimestral":
            self.date_end.setDate(start.addDays(56))  # 8 semanas
        elif period_type == "Cuatrimestral":
            self.date_end.setDate(start.addDays(112))  # 16 semanas
        elif period_type == "Semestral":
            self.date_end.setDate(start.addDays(168))  # 24 semanas

    def _on_start_date_changed(self, start: QDate) -> None:
        period_type = self.combo_period.currentText()
        if period_type != "Personalizado":
            self._on_period_type_changed(period_type)

    def _populate_milestones_table(self) -> None:
        icons_list = [
            ("🎯", "🎯 Parcial / Objetivo"),
            ("📝", "📝 Examen / Evaluación"),
            ("🔄", "🔄 Recuperatorio"),
            ("🏁", "🏁 Examen Final"),
            ("💻", "💻 Entrega / TP"),
            ("🔬", "🔬 Laboratorio"),
            ("🗣️", "🗣️ Oral / Coloquio"),
            ("⭐", "⭐ Hito Clave"),
            ("⚠️", "⚠️ Fecha Límite"),
            ("📚", "📚 Cierre de Cursada"),
        ]

        self.table_milestones.setRowCount(0)
        for row, m in enumerate(self.milestones):
            self.table_milestones.insertRow(row)

            # Col 0: Nombre
            item_name = QTableWidgetItem(m.name)
            self.table_milestones.setItem(row, 0, item_name)

            # Col 1: Fecha (QDateEdit)
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            if m.date:
                date_edit.setDate(QDate.fromString(m.date, "yyyy-MM-dd"))
            else:
                date_edit.setDate(self.date_start.date().addDays(30))
            self.table_milestones.setCellWidget(row, 1, date_edit)

            # Col 2: Ícono (QComboBox)
            combo_icon = QComboBox()
            matched_icon_idx = 0
            for i, (ic, label) in enumerate(icons_list):
                combo_icon.addItem(label, ic)
                if ic == m.icon:
                    matched_icon_idx = i
            combo_icon.setCurrentIndex(matched_icon_idx)
            self.table_milestones.setCellWidget(row, 2, combo_icon)

            # Col 3: Color (QPushButton con selector QColorDialog)
            btn_color = QPushButton("  Color  ")
            color_hex = m.color or "#ef4444"
            btn_color.setProperty("color_hex", color_hex)
            btn_color.setStyleSheet(
                f"background-color: {color_hex}; color: #ffffff; font-weight: 700; "
                "border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; padding: 3px 8px;"
            )
            btn_color.setToolTip(f"Color: {color_hex} (clic para cambiar)")

            def make_color_picker(btn=btn_color):
                def pick():
                    current = btn.property("color_hex") or "#ef4444"
                    c = QColorDialog.getColor(QColor(current), self, "Seleccionar Color del Hito")
                    if c.isValid():
                        new_hex = c.name()
                        btn.setProperty("color_hex", new_hex)
                        btn.setStyleSheet(
                            f"background-color: {new_hex}; color: #ffffff; font-weight: 700; "
                            "border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 4px; padding: 3px 8px;"
                        )
                        btn.setToolTip(f"Color: {new_hex} (clic para cambiar)")
                return pick

            btn_color.clicked.connect(make_color_picker())
            self.table_milestones.setCellWidget(row, 3, btn_color)

            # Col 4: Tipo (QComboBox editable)
            combo_type = QComboBox()
            combo_type.setEditable(True)
            combo_type.addItems(["Parcial", "Recuperatorio", "Final", "Entrega", "Coloquio", "Otro"])
            combo_type.setCurrentText(m.type.capitalize())
            self.table_milestones.setCellWidget(row, 4, combo_type)

            self.table_milestones.setRowHeight(row, 30)

    def _collect_milestones_from_table(self) -> list[Milestone]:
        result: list[Milestone] = []
        for row in range(self.table_milestones.rowCount()):
            name_item = self.table_milestones.item(row, 0)
            name = name_item.text().strip() if name_item else "Examen"
            if not name:
                name = f"Hito {row + 1}"

            date_widget = self.table_milestones.cellWidget(row, 1)
            m_date = date_widget.date().toString("yyyy-MM-dd") if isinstance(date_widget, QDateEdit) else ""

            icon_widget = self.table_milestones.cellWidget(row, 2)
            if isinstance(icon_widget, QComboBox):
                m_icon = icon_widget.currentData() or icon_widget.currentText()[:2].strip() or "🎯"
            else:
                m_icon = "🎯"

            color_widget = self.table_milestones.cellWidget(row, 3)
            m_color = color_widget.property("color_hex") if color_widget else "#ef4444"

            type_widget = self.table_milestones.cellWidget(row, 4)
            m_type = type_widget.currentText().strip() if isinstance(type_widget, QComboBox) else "Parcial"
            if not m_type:
                m_type = "Parcial"

            result.append(Milestone(name=name, date=m_date, type=m_type, color=m_color, icon=m_icon))
        return result

    def _on_add_milestone(self) -> None:
        self.milestones = self._collect_milestones_from_table()
        default_configs = [
            ("Primer Parcial", "parcial", "🎯", "#ef4444"),
            ("Segundo Parcial", "parcial", "🎯", "#ef4444"),
            ("Recuperatorio", "recuperatorio", "🔄", "#f59e0b"),
            ("Examen Final", "final", "🏁", "#a855f7"),
        ]
        idx = min(len(self.milestones), len(default_configs) - 1)
        name, m_type, m_icon, m_color = default_configs[idx]
        if len(self.milestones) >= len(default_configs):
            name = f"Hito {len(self.milestones) + 1}"
            m_type = "personalizado"
            m_icon = "⭐"
            m_color = "#3b82f6"

        default_date = self.date_start.date().addDays(30 * (len(self.milestones) + 1)).toString("yyyy-MM-dd")
        self.milestones.append(Milestone(name=name, date=default_date, type=m_type, color=m_color, icon=m_icon))
        self._populate_milestones_table()
        self.table_milestones.selectRow(len(self.milestones) - 1)

    def _on_remove_milestone(self) -> None:
        row = self.table_milestones.currentRow()
        if row >= 0:
            self.table_milestones.removeRow(row)


    def _on_clear_schedule(self) -> None:
        ans = QMessageBox.question(
            self,
            "Desactivar Cronograma",
            "¿Deseas quitar la configuración del cronograma para esta materia?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self.schedule = None
            self.accept()

    def _on_save(self) -> None:
        start_qdate = self.date_start.date()
        end_qdate = self.date_end.date()

        if end_qdate < start_qdate:
            QMessageBox.warning(
                self,
                "Fecha inválida",
                "La fecha de finalización debe ser posterior o igual a la fecha de inicio.",
            )
            return

        milestones = self._collect_milestones_from_table()
        self.schedule = PlannerSchedule(
            period_type=self.combo_period.currentText(),
            start_date=start_qdate.toString("yyyy-MM-dd"),
            end_date=end_qdate.toString("yyyy-MM-dd"),
            milestones=milestones,
        )
        self.accept()




