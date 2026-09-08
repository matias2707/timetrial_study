"""Diálogos específicos de la funcionalidad de Planificador en Study Timetrial."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    ExerciseNodeStatus,
)
from domain.models import PlannedSection
from presentation.presentation_formatters import format_milliseconds

ACTION_CANCEL = "cancel"
ACTION_GO_PLANNER = "go_planner"
ACTION_CONTINUE = "continue"


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
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.node = node
        self.is_dark = is_dark
        self.chosen_action = ACTION_CANCEL

        self.setWindowTitle(f"Detalle · {node.full_label}")
        self.resize(460, 420)

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

        # Comentarios
        comm_group = QGroupBox("Comentarios de Intentos")
        comm_layout = QVBoxLayout(comm_group)
        if node.comments:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(80)
            inner = QWidget()
            in_lay = QVBoxLayout(inner)
            in_lay.setContentsMargins(4, 4, 4, 4)
            in_lay.setSpacing(4)
            for c in node.comments:
                c_lbl = QLabel(f"• {c}")
                c_lbl.setWordWrap(True)
                c_lbl.setStyleSheet("font-size: 12px;")
                in_lay.addWidget(c_lbl)
            scroll.setWidget(inner)
            comm_layout.addWidget(scroll)
        else:
            no_comm = QLabel("Sin comentarios registrados para este ejercicio.")
            no_comm.setStyleSheet("color: #64748b; font-style: italic; font-size: 11px;")
            comm_layout.addWidget(no_comm)

        layout.addWidget(comm_group)

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

    def _on_load_timer(self) -> None:
        self.chosen_action = "load_timer"
        self.accept()


class BoundaryWarningDialog(QDialog):
    """Diálogo emergente cuando la navegación excede el rango planificado."""

    def __init__(
        self,
        parent: QWidget | None,
        boundary_message: str,
        is_dark: bool = True,
    ) -> None:
        super().__init__(parent)
        self.result_action = ACTION_CANCEL
        self.setWindowTitle("Aviso de Planificación")
        self.resize(480, 240)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.exclamation-triangle", color="#f59e0b").pixmap(36, 36))
        header_layout.addWidget(icon_lbl)

        msg_layout = QVBoxLayout()
        title_lbl = QLabel("Ejercicio fuera del rango planificado")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        msg_layout.addWidget(title_lbl)

        detail_lbl = QLabel(boundary_message)
        detail_lbl.setWordWrap(True)
        detail_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        msg_layout.addWidget(detail_lbl)
        header_layout.addLayout(msg_layout)
        layout.addLayout(header_layout)

        info_lbl = QLabel(
            "¿Cómo deseas proceder?\n"
            "• Modificar la planificación: Abre el Planificador para ajustar la guía.\n"
            "• Continuar sin modificar: Avanza y el Planificador incorporará el ejercicio automáticamente.\n"
            "• Cancelar: Permanece en el ejercicio actual."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-size: 11px; color: #cbd5e1;")
        layout.addWidget(info_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(btn_cancel)

        btn_plan = QPushButton("Ir a la Planificación")
        btn_plan.setIcon(qta.icon("fa5s.tasks", color="#38bdf8"))
        btn_plan.clicked.connect(self._on_go_plan)
        btn_layout.addWidget(btn_plan)

        btn_continue = QPushButton("Continuar sin modificar")
        btn_continue.setStyleSheet("font-weight: 600;")
        btn_continue.clicked.connect(self._on_continue)
        btn_layout.addWidget(btn_continue)

        layout.addLayout(btn_layout)

    def _on_cancel(self) -> None:
        self.result_action = ACTION_CANCEL
        self.reject()

    def _on_go_plan(self) -> None:
        self.result_action = ACTION_GO_PLANNER
        self.accept()

    def _on_continue(self) -> None:
        self.result_action = ACTION_CONTINUE
        self.accept()
