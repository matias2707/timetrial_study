"""Widget principal de la pestaña Planificador en Study Timetrial.

Muestra de manera gráfica y unificada todas las guías y secciones configuradas,
sus ejercicios e incisos con sus respectivos estados (hecho, fallado, pendiente),
resumen global y herramientas de gestión del universo de estudio.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from application.application_service import StudyApplicationService
from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    ExerciseNodeStatus,
    PlannedSectionStatus,
    PlannerOverview,
)
from domain.models import PlannedSection
from presentation.flow_layout import FlowLayout
from presentation.planner_dialogs import (
    ExerciseDetailPopup,
    PlannedSectionDialog,
)
from presentation.presentation_formatters import format_milliseconds


class ExerciseCellButton(QPushButton):
    """Botón gráfico individual para un ejercicio simple o inciso."""

    def __init__(
        self,
        node: ExerciseNodeStatus,
        is_dark: bool = True,
        is_sub_inciso: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.node = node
        self.is_dark = is_dark
        self.is_sub_inciso = is_sub_inciso

        self.setText(node.display_label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setFixedSize(QSize(46, 44))

        self._apply_style()
        self._set_tooltip()

    def sizeHint(self) -> QSize:
        return QSize(46, 44)

    def _apply_style(self) -> None:
        status = self.node.status

        if status == STATUS_COMPLETED:
            if self.is_dark:
                bg = "#14532d"
                hover_bg = "#166534"
                text = "#86efac"
                border = "#22c55e"
            else:
                bg = "#dcfce7"
                hover_bg = "#bbf7d0"
                text = "#15803d"
                border = "#86efac"
        elif status == STATUS_FAILED:
            if self.is_dark:
                bg = "#7f1d1d"
                hover_bg = "#991b1b"
                text = "#fca5a5"
                border = "#ef4444"
            else:
                bg = "#fee2e2"
                hover_bg = "#fecaca"
                text = "#b91c1c"
                border = "#fca5a5"
        else:  # STATUS_PENDING
            if self.is_dark:
                bg = "#1e293b"
                hover_bg = "#334155"
                text = "#94a3b8"
                border = "#334155"
            else:
                bg = "#f1f5f9"
                hover_bg = "#e2e8f0"
                text = "#64748b"
                border = "#cbd5e1"

        font_size = "11px" if len(self.node.display_label) >= 4 else "12px"
        font_weight = "700" if status != STATUS_PENDING else "600"

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1.5px solid {border};
                border-radius: 6px;
                font-size: {font_size};
                font-weight: {font_weight};
                padding: 2px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border-color: #bef264;
            }}
            """
        )

    def _set_tooltip(self) -> None:
        st_desc = {
            STATUS_COMPLETED: "Completado ✅",
            STATUS_FAILED: "En dificultad / Fallado ⚠️",
            STATUS_PENDING: "No hecho ⏳",
        }.get(self.node.status, "Desconocido")

        lines = [
            f"<b>{self.node.full_label}</b>",
            f"Estado: {st_desc}",
            f"Intentos: {self.node.attempts}",
        ]
        if self.node.attempts > 0:
            lines.append(f"Tiempo: {format_milliseconds(self.node.exercise_time_ms)}")
            if self.node.latest_comment:
                lines.append(f"Comentario: {self.node.latest_comment}")

        self.setToolTip("<br>".join(lines))


class CompositeExerciseGroup(QFrame):
    """Contenedor visual para ejercicios que contienen múltiples incisos numéricos.

    Muestra un marco delimitador sutil alrededor de los incisos (ej: 7.1, 7.2, 7.3, 7.4),
    dejando claro que pertenecen al mismo ejercicio sin necesidad de un cuadro 'Ej. {n}'.
    """

    def __init__(
        self,
        node: ExerciseNodeStatus,
        is_dark: bool = True,
        on_sub_clicked=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.node = node
        self.is_dark = is_dark
        self.on_sub_clicked = on_sub_clicked

        self.setFrameShape(QFrame.Shape.StyledPanel)
        border_color = "#334155" if is_dark else "#cbd5e1"
        bg_color = "#111827" if is_dark else "#f8fafc"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px dashed {border_color};
                border-radius: 8px;
                padding: 1px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 2, 3, 2)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sub-botones para cada inciso (sin cuadro duplicado 'Ej. {n}')
        for sub_node in node.incisos:
            btn_sub = ExerciseCellButton(
                sub_node,
                is_dark=is_dark,
                is_sub_inciso=True,
                parent=self,
            )
            if on_sub_clicked:
                btn_sub.clicked.connect(lambda _, n=sub_node: on_sub_clicked(n))
            layout.addWidget(btn_sub)

        self.setToolTip(f"Ejercicio {node.exercise} · {len(node.incisos)} incisos")


class PlannedSectionCard(QFrame):
    """Tarjeta gráfica que representa una guía o sección completa con su cuadrícula de ejercicios."""

    def __init__(
        self,
        sec_status: PlannedSectionStatus,
        is_dark: bool = True,
        on_node_click=None,
        on_edit_click=None,
        on_delete_click=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.sec_status = sec_status
        self.is_dark = is_dark
        self.on_node_click = on_node_click
        self.on_edit_click = on_edit_click
        self.on_delete_click = on_delete_click

        self.setFrameShape(QFrame.Shape.StyledPanel)
        card_bg = "#0f172a" if is_dark else "#ffffff"
        card_border = "#1e293b" if is_dark else "#e2e8f0"
        self.setStyleSheet(
            f"""
            PlannedSectionCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
                margin-bottom: 12px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)

        # Header de la sección
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Título y badges
        v_title = QVBoxLayout()
        v_title.setSpacing(2)

        title_h = QHBoxLayout()
        sec_name = f"{sec_status.section.section_type} {sec_status.section.section_number}"
        lbl_name = QLabel(sec_name)
        lbl_name.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_h.addWidget(lbl_name)

        if sec_status.section.title:
            lbl_desc = QLabel(f"·  {sec_status.section.title}")
            lbl_desc.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: 500;")
            title_h.addWidget(lbl_desc)

        title_h.addStretch()
        v_title.addLayout(title_h)

        # Barra de progreso y contador
        prog_h = QHBoxLayout()
        prog_h.setSpacing(10)

        prog_bar = QProgressBar()
        prog_bar.setRange(0, 100)
        prog_bar.setValue(int(sec_status.completion_percentage))
        prog_bar.setTextVisible(False)
        prog_bar.setFixedHeight(8)
        prog_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {"#1e293b" if is_dark else "#e2e8f0"};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: #bef264;
                border-radius: 4px;
            }}
            """
        )
        prog_h.addWidget(prog_bar, 1)

        lbl_progress = QLabel(
            f"{sec_status.completed_units} / {sec_status.total_units} hechos ({sec_status.completion_percentage:.1f}%)"
        )
        lbl_progress.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        prog_h.addWidget(lbl_progress)

        v_title.addLayout(prog_h)
        header_layout.addLayout(v_title, 1)

        # Botones de gestión para esta sección
        btn_edit = QPushButton("Editar")
        btn_edit.setIcon(qta.icon("fa5s.edit", color="#94a3b8"))
        btn_edit.setStyleSheet("padding: 5px 10px; font-size: 11px; border-radius: 6px;")
        if on_edit_click:
            btn_edit.clicked.connect(lambda: on_edit_click(sec_status.section))
        header_layout.addWidget(btn_edit)

        btn_del = QPushButton("Eliminar")
        btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#ef4444"))
        btn_del.setStyleSheet("padding: 5px 10px; font-size: 11px; border-radius: 6px;")
        if on_delete_click:
            btn_del.clicked.connect(lambda: on_delete_click(sec_status.section))
        header_layout.addWidget(btn_del)

        layout.addLayout(header_layout)

        # Separador sutil
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {'#1e293b' if is_dark else '#e2e8f0'}; max-height: 1px;")
        layout.addWidget(sep)

        # Contenedor interactivo de ejercicios con FlowLayout (distribución fluida sin columnas rígidas)
        exercises_container = QWidget()
        exercises_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        flow_layout = FlowLayout(exercises_container, margin=0, h_spacing=8, v_spacing=8)

        for node in sec_status.exercise_nodes:
            if node.has_incisos:
                group = CompositeExerciseGroup(
                    node,
                    is_dark=is_dark,
                    on_sub_clicked=self.on_node_click,
                    parent=self,
                )
                flow_layout.addWidget(group)
            else:
                btn_single = ExerciseCellButton(
                    node,
                    is_dark=is_dark,
                    is_sub_inciso=False,
                    parent=self,
                )
                if self.on_node_click:
                    btn_single.clicked.connect(lambda _, n=node: self.on_node_click(n))
                flow_layout.addWidget(btn_single)

        layout.addWidget(exercises_container)


class PlannerWidget(QWidget):
    """Pestaña Planificador: vista general unificada con scroll de todas las guías."""

    request_load_timer = Signal(str, int, int, object)  # (section_type, section_number, exercise, inciso)

    def __init__(
        self,
        app_service: StudyApplicationService,
        is_dark_mode: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_service = app_service
        self.is_dark = is_dark_mode

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # 1. Cabecera principal: Título "Planificador" y Acciones Globales
        top_bar = QHBoxLayout()
        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)

        lbl_title = QLabel("Planificador")
        lbl_title.setObjectName("planner_main_title")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: 800;")
        v_titles.addWidget(lbl_title)

        lbl_sub = QLabel("Universo de estudio configurado, progreso de ejercicios y detección de dificultades")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        v_titles.addWidget(lbl_sub)
        top_bar.addLayout(v_titles)

        top_bar.addStretch()

        # Botones de acción globales
        self.btn_sync = QPushButton("Sincronizar con Registros")
        self.btn_sync.setIcon(qta.icon("fa5s.sync-alt", color="#38bdf8"))
        self.btn_sync.setToolTip("Añade automáticamente a la planificación los ejercicios de registros no contemplados.")
        self.btn_sync.clicked.connect(self._on_sync_records)
        top_bar.addWidget(self.btn_sync)

        self.btn_add_section = QPushButton("Nueva Sección / Guía")
        self.btn_add_section.setIcon(qta.icon("fa5s.plus-circle", color="#0f172a" if not is_dark_mode else "#0f172a"))
        self.btn_add_section.setStyleSheet(
            """
            QPushButton {
                background-color: #bef264;
                color: #0f172a;
                font-weight: 700;
                padding: 7px 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #a3e635;
            }
            """
        )
        self.btn_add_section.clicked.connect(self._on_add_section)
        top_bar.addWidget(self.btn_add_section)

        main_layout.addLayout(top_bar)

        # 2. Resumen Global (Chips / Bento Cards)
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("planner_summary_frame")
        self.summary_frame.setStyleSheet(
            f"""
            QFrame#planner_summary_frame {{
                background-color: {"#0f172a" if is_dark_mode else "#ffffff"};
                border: 1px solid {"#1e293b" if is_dark_mode else "#e2e8f0"};
                border-radius: 12px;
                padding: 12px 16px;
            }}
            """
        )
        sum_layout = QHBoxLayout(self.summary_frame)
        sum_layout.setSpacing(20)

        self.lbl_card_total = self._make_stat_badge("Total Planificado", "0", "#38bdf8")
        self.lbl_card_completed = self._make_stat_badge("Hechos", "0", "#bef264")
        self.lbl_card_failed = self._make_stat_badge("En Dificultad", "0", "#ef4444")
        self.lbl_card_pending = self._make_stat_badge("Pendientes", "0", "#94a3b8")

        sum_layout.addLayout(self.lbl_card_total)
        sum_layout.addLayout(self.lbl_card_completed)
        sum_layout.addLayout(self.lbl_card_failed)
        sum_layout.addLayout(self.lbl_card_pending)

        # Barra de progreso global
        v_prog = QVBoxLayout()
        v_prog.setSpacing(4)
        lbl_global_p = QLabel("Progreso Global:")
        lbl_global_p.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        v_prog.addWidget(lbl_global_p)

        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setRange(0, 100)
        self.global_progress_bar.setValue(0)
        self.global_progress_bar.setTextVisible(True)
        self.global_progress_bar.setFixedHeight(16)
        self.global_progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {"#1e293b" if is_dark_mode else "#e2e8f0"};
                border-radius: 8px;
                text-align: center;
                color: #0f172a;
                font-weight: 700;
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: #bef264;
                border-radius: 8px;
            }}
            """
        )
        v_prog.addWidget(self.global_progress_bar)
        sum_layout.addLayout(v_prog, 1)

        main_layout.addWidget(self.summary_frame)

        # 3. Área de Scroll vertical unificada para todas las guías
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 8, 0, 8)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.refresh_view()

    def _make_stat_badge(self, title: str, value: str, color_hex: str) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(1)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        v_lbl = QLabel(value)
        v_lbl.setObjectName(f"stat_val_{title.lower().replace(' ', '_')}")
        v_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color_hex};")
        v.addWidget(t_lbl)
        v.addWidget(v_lbl)
        return v

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.refresh_view()

    def refresh_view(self) -> None:
        """Calcula el estado del planificador y redibuja todas las secciones y tarjetas."""
        overview: PlannerOverview = self.app_service.get_planner_overview()

        # Actualizar chips globales
        self._update_stat_badge("total_planificado", f"{overview.total_units}")
        self._update_stat_badge("hechos", f"{overview.completed_units}")
        self._update_stat_badge("en_dificultad", f"{overview.failed_units}")
        self._update_stat_badge("pendientes", f"{overview.pending_units}")

        pct = int(overview.global_completion_percentage)
        self.global_progress_bar.setValue(pct)
        self.global_progress_bar.setFormat(f"{overview.global_completion_percentage:.1f}%")

        # Limpiar tarjetas anteriores
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Si no hay secciones, mostrar Empty State amigable
        if not overview.sections:
            empty_widget = self._create_empty_state()
            self.cards_layout.addWidget(empty_widget)
            self.cards_layout.addStretch()
            return

        # Dibujar cada sección planificada
        for sec_status in overview.sections:
            card = PlannedSectionCard(
                sec_status=sec_status,
                is_dark=self.is_dark,
                on_node_click=self._on_node_clicked,
                on_edit_click=self._on_edit_section,
                on_delete_click=self._on_delete_section,
                parent=self.scroll_content,
            )
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _update_stat_badge(self, key: str, val: str) -> None:
        w = self.summary_frame.findChild(QLabel, f"stat_val_{key}")
        if w:
            w.setText(val)

    def _create_empty_state(self) -> QWidget:
        empty = QFrame()
        empty.setStyleSheet(
            f"""
            QFrame {{
                background-color: {"#0f172a" if self.is_dark else "#ffffff"};
                border: 2px dashed {"#1e293b" if self.is_dark else "#cbd5e1"};
                border-radius: 12px;
                padding: 40px 20px;
            }}
            """
        )
        lay = QVBoxLayout(empty)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon("fa5s.clipboard-list", color="#64748b").pixmap(48, 48))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        msg_title = QLabel("No hay secciones planificadas todavía")
        msg_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #94a3b8;")
        msg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg_title)

        msg_desc = QLabel(
            "Crea una nueva guía indicando la cantidad de ejercicios, o presiona "
            "'Sincronizar con Registros' para importar automáticamente lo que ya has realizado."
        )
        msg_desc.setStyleSheet("color: #64748b; font-size: 12px;")
        msg_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg_desc)

        btn = QPushButton("➕ Crear Primera Guía")
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #bef264;
                color: #0f172a;
                font-weight: 700;
                padding: 8px 18px;
                border-radius: 8px;
            }
            """
        )
        btn.clicked.connect(self._on_add_section)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return empty

    def _on_node_clicked(self, node: ExerciseNodeStatus) -> None:
        """Abre la ventana emergente de detalle para el ejercicio seleccionado."""
        popup = ExerciseDetailPopup(self, node, is_dark=self.is_dark)
        if popup.exec() == ExerciseDetailPopup.DialogCode.Accepted:
            if popup.chosen_action == "load_timer":
                self.request_load_timer.emit(
                    node.section_type,
                    node.section_number,
                    node.exercise,
                    node.inciso,
                )

    def _on_add_section(self) -> None:
        dlg = PlannedSectionDialog(self, is_dark=self.is_dark)
        if dlg.exec() == PlannedSectionDialog.DialogCode.Accepted and dlg.section_data:
            self.app_service.add_or_update_planned_section(dlg.section_data)
            self.refresh_view()

    def _on_edit_section(self, section: PlannedSection) -> None:
        dlg = PlannedSectionDialog(self, section=section, is_dark=self.is_dark)
        if dlg.exec() == PlannedSectionDialog.DialogCode.Accepted and dlg.section_data:
            self.app_service.add_or_update_planned_section(dlg.section_data)
            self.refresh_view()

    def _on_delete_section(self, section: PlannedSection) -> None:
        confirm = QMessageBox.question(
            self,
            "Eliminar Sección de la Planificación",
            f"¿Deseas eliminar '{section.section_type} {section.section_number}' de la planificación?\n\n"
            "Nota: Los registros de tiempo existentes NO se eliminarán.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.app_service.delete_planned_section(section.section_type, section.section_number)
            self.refresh_view()

    def _on_sync_records(self) -> None:
        modified = self.app_service.sync_planner_with_records()
        if modified:
            QMessageBox.information(
                self,
                "Sincronización Completa",
                "Se han incorporado a la planificación los ejercicios encontrados en tus registros.",
            )
        else:
            QMessageBox.information(
                self,
                "Sincronización Completa",
                "La planificación ya contiene todos los ejercicios presentes en los registros.",
            )
        self.refresh_view()
