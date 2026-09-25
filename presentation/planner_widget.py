"""Widget principal de la pestaña Planificador en Study Timetrial.

Muestra de manera gráfica y unificada todas las guías y secciones configuradas,
sus ejercicios e incisos con sus respectivos estados (hecho, fallado, pendiente),
resumen global y herramientas de gestión del universo de estudio.
"""

from __future__ import annotations

import html
import qtawesome as qta
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
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
    ScheduleConfigDialog,
    TagManagerDialog,
)
from presentation.presentation_formatters import format_milliseconds


class SegmentedProgressBar(QProgressBar):
    """Barra de progreso unificada que muestra segmentos de completado (verde) y dificultad (rojo) en la misma barra."""

    def __init__(
        self,
        is_dark: bool = True,
        corner_radius: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.is_dark = is_dark
        self.corner_radius = corner_radius
        self.completed_val: float = 0.0
        self.failed_val: float = 0.0
        self.total_val: float = 100.0

        self.setTextVisible(False)
        self.setRange(0, 100)
        self.setValue(0)
        self.setStyleSheet("QProgressBar { border: none; background: transparent; }")

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def set_segmented_values(self, completed: float, failed: float, total: float = 100.0) -> None:
        self.completed_val = max(0.0, float(completed))
        self.failed_val = max(0.0, float(failed))
        self.total_val = max(0.0001, float(total))
        pct = int(round((self.completed_val / self.total_val) * 100.0))
        super().setValue(min(100, max(0, pct)))
        self.update()

    @property
    def completed_percentage(self) -> float:
        if self.total_val <= 0:
            return 0.0
        return (self.completed_val / self.total_val) * 100.0

    @property
    def failed_percentage(self) -> float:
        if self.total_val <= 0:
            return 0.0
        return (self.failed_val / self.total_val) * 100.0

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()
        if w <= 0 or h <= 0:
            return

        r = self.corner_radius

        # Clip redondeado para garantizar bordes suaves
        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, 0, w, h, r, r)
        painter.setClipPath(clip_path)

        # Fondo del canal
        bg_color = QColor("#1e293b" if self.is_dark else "#e2e8f0")
        painter.fillRect(rect, bg_color)

        if self.total_val > 0:
            tot = self.total_val
            c_val = self.completed_val
            f_val = self.failed_val

            # Si la suma de valores excede el total, normalizar la escala
            if c_val + f_val > tot:
                scale = tot / (c_val + f_val)
                c_val *= scale
                f_val *= scale

            w_comp = int(round((c_val / tot) * w))
            w_failed = int(round((f_val / tot) * w))

            # Si un valor es > 0, asegurar al menos 1 píxel si hay espacio disponible
            if c_val > 0 and w_comp == 0 and w > 0:
                w_comp = 1
            if f_val > 0 and w_failed == 0 and w > 0:
                w_failed = 1

            # Ajustar para que la suma no sobrepase el ancho total
            if w_comp + w_failed > w:
                w_failed = max(0, w - w_comp)

            # Segmento verde: Hechos / Completados (#059669)
            if w_comp > 0:
                painter.fillRect(0, 0, w_comp, h, QColor("#059669"))

            # Segmento rojo: En dificultad / Fallados (#b91c1c)
            if w_failed > 0:
                painter.fillRect(w_comp, 0, w_failed, h, QColor("#b91c1c"))


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
        self._opacity_effect: QGraphicsOpacityEffect | None = None

        self.setText(node.display_label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setFixedSize(QSize(52, 48))

        self._apply_style()
        self._set_tooltip()

    def sizeHint(self) -> QSize:
        return QSize(52, 48)

    def set_dimmed(self, dimmed: bool) -> None:
        """Atenúa visualmente el botón cuando no coincide con un filtro activo."""
        if dimmed:
            if self._opacity_effect is None:
                self._opacity_effect = QGraphicsOpacityEffect(self)
                self._opacity_effect.setOpacity(0.18)
                self.setGraphicsEffect(self._opacity_effect)
        else:
            if self._opacity_effect is not None:
                self.setGraphicsEffect(None)
                self._opacity_effect = None

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.node.tags and not self.node.has_note:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        # Clip redondeado acorde al botón
        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, 0, w, h, 6, 6)
        painter.setClipPath(clip_path)

        outline_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        if self.node.tags:
            tags = self.node.tags
            k = len(tags)
            gap = 2
            # Ajustar dinámicamente el ancho si hay muchas etiquetas para que no desborden
            max_avail_w = max(10, w - 8)
            bw = min(10, max(6, (max_avail_w - (k - 1) * gap) // k)) if k > 0 else 10
            bh = 13
            total_w = k * bw + (k - 1) * gap
            start_x = w - 4 - total_w

            outline_bm = qta.icon("fa5s.bookmark", color="rgba(0, 0, 0, 180)")

            for i, tag in enumerate(tags):
                x_pos = start_x + i * (bw + gap)
                y_pos = 2
                color = tag.color or "#a855f7"

                # Contorno negro sutil para maximizar el contraste
                for ox, oy in outline_offsets:
                    outline_bm.paint(
                        painter, QRect(int(x_pos + ox), int(y_pos + oy), int(bw), int(bh))
                    )

                # Ícono relleno con el color del marcador
                qta.icon("fa5s.bookmark", color=color).paint(
                    painter, QRect(int(x_pos), int(y_pos), int(bw), int(bh))
                )

        if self.node.has_note:
            note_color = "#38bdf8" if self.is_dark else "#0284c7"
            nx, ny, nw, nh = w - 14, h - 14, 11, 11
            note_outline = qta.icon("fa5s.sticky-note", color="rgba(0, 0, 0, 180)")
            for ox, oy in outline_offsets:
                note_outline.paint(painter, QRect(nx + ox, ny + oy, nw, nh))
            qta.icon("fa5s.sticky-note", color=note_color).paint(
                painter, QRect(nx, ny, nw, nh)
            )

    def _apply_style(self) -> None:
        status = self.node.status

        if status == STATUS_COMPLETED:
            if self.is_dark:
                bg = "#064e3b"
                hover_bg = "#065f46"
                text = "#6ee7b7"
                border = "#059669"
            else:
                bg = "#ecfdf5"
                hover_bg = "#d1fae5"
                text = "#047857"
                border = "#a7f3d0"
        elif status == STATUS_FAILED:
            if self.is_dark:
                bg = "#450a0a"
                hover_bg = "#5c1010"
                text = "#fca5a5"
                border = "#7f1d1d"
            else:
                bg = "#fef2f2"
                hover_bg = "#fee2e2"
                text = "#b91c1c"
                border = "#fecaca"
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

        hover_border = "#10b981" if self.is_dark else "#059669"
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
                border-color: {hover_border};
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

        if self.node.tags:
            tag_lines = ["<b>Marcadores:</b>"]
            for tag in self.node.tags:
                tag_lines.append(f"<span style='color: {tag.color}; font-size: 13px;'>●</span> <b>{tag.name}</b>")
            lines.append("<br>".join(tag_lines))

        if self.node.has_note and self.node.note:
            note_escaped = html.escape(self.node.note)
            lines.append(
                f"<hr style='margin: 3px 0; border: 0; border-top: 1px solid #475569;'>"
                f"<span style='color: #38bdf8; font-weight: bold;'>📝 Apuntes / Nota:</span><br>"
                f"<span style='font-style: italic; color: {'#cbd5e1' if self.is_dark else '#334155'};'>{note_escaped}</span>"
            )

        self.setToolTip("<br>".join(lines))


class GroupHeaderCellButton(QPushButton):
    """Botón cabecera para un grupo de ejercicios con incisos (ej: '1' para incisos 1.1, 1.2, ...).

    Tiene la misma apariencia gráfica que ExerciseCellButton, pero en lugar de abrir modal,
    conmuta la contracción/expansión del grupo. En modo contraído muestra íconos consolidados
    y su color se calcula según la jerarquía estricta: gris > rojo > verde.
    """

    def __init__(
        self,
        node: ExerciseNodeStatus,
        is_dark: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.node = node
        self.is_dark = is_dark
        self.is_collapsed = False
        self._opacity_effect: QGraphicsOpacityEffect | None = None

        self.setText(str(node.exercise))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QSize(52, 48))

        self._apply_style()
        self._set_tooltip()

    def sizeHint(self) -> QSize:
        return QSize(52, 48)

    def set_collapsed(self, collapsed: bool) -> None:
        self.is_collapsed = collapsed
        self._set_tooltip()
        self.update()

    def set_dimmed(self, dimmed: bool) -> None:
        """Atenúa visualmente el botón cuando no coincide con un filtro activo."""
        if dimmed:
            if self._opacity_effect is None:
                self._opacity_effect = QGraphicsOpacityEffect(self)
                self._opacity_effect.setOpacity(0.18)
                self.setGraphicsEffect(self._opacity_effect)
        else:
            if self._opacity_effect is not None:
                self.setGraphicsEffect(None)
                self._opacity_effect = None

    def _apply_style(self) -> None:
        # Prioridad estricta de color: gris > rojo > verde
        status = self.node.group_color_status

        if status == STATUS_COMPLETED:
            if self.is_dark:
                bg = "#064e3b"
                hover_bg = "#065f46"
                text = "#6ee7b7"
                border = "#059669"
            else:
                bg = "#ecfdf5"
                hover_bg = "#d1fae5"
                text = "#047857"
                border = "#a7f3d0"
        elif status == STATUS_FAILED:
            if self.is_dark:
                bg = "#450a0a"
                hover_bg = "#5c1010"
                text = "#fca5a5"
                border = "#7f1d1d"
            else:
                bg = "#fef2f2"
                hover_bg = "#fee2e2"
                text = "#b91c1c"
                border = "#fecaca"
        else:  # STATUS_PENDING (gris)
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

        font_size = "11px" if len(str(self.node.exercise)) >= 4 else "12px"
        font_weight = "700" if status != STATUS_PENDING else "600"
        hover_border = "#10b981" if self.is_dark else "#059669"

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
                border-color: {hover_border};
            }}
            """
        )

    def _set_tooltip(self) -> None:
        status = self.node.group_color_status
        st_desc = {
            STATUS_COMPLETED: "Completado ✅",
            STATUS_FAILED: "En dificultad / Fallado ⚠️",
            STATUS_PENDING: "No hecho ⏳",
        }.get(status, "Desconocido")

        c_sub = sum(1 for s in self.node.incisos if s.status == STATUS_COMPLETED)
        f_sub = sum(1 for s in self.node.incisos if s.status == STATUS_FAILED)
        p_sub = sum(1 for s in self.node.incisos if s.status == STATUS_PENDING)

        lines = [
            f"<b>{self.node.section_type} {self.node.section_number} · Ejercicio {self.node.exercise}</b>",
            f"Estado general: {st_desc}",
            f"Incisos ({len(self.node.incisos)}): {c_sub} hechos · {f_sub} en dificultad · {p_sub} pendientes",
        ]

        if self.is_collapsed:
            lines.append("<i>(Contraído · Clic para expandir incisos)</i>")
            tags = self.node.aggregated_tags
            if tags:
                tag_lines = ["<b>Marcadores en incisos:</b>"]
                for tag in tags:
                    tag_lines.append(f"<span style='color: {tag.color}; font-size: 13px;'>●</span> <b>{tag.name}</b>")
                lines.append("<br>".join(tag_lines))
            if self.node.aggregated_has_note:
                lines.append(
                    "<hr style='margin: 3px 0; border: 0; border-top: 1px solid #475569;'>"
                    "<span style='color: #38bdf8; font-weight: bold;'>📝 Contiene notas o apuntes en sus incisos</span>"
                )
        else:
            lines.append("<i>(Expandido · Clic para contraer incisos)</i>")

        self.setToolTip("<br>".join(lines))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        # De manera comprimida, este mostrará íconos que sus incisos poseen
        if not self.is_collapsed:
            return

        tags = self.node.aggregated_tags
        has_note = self.node.aggregated_has_note
        if not tags and not has_note:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, 0, w, h, 6, 6)
        painter.setClipPath(clip_path)

        outline_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        if tags:
            k = len(tags)
            gap = 2
            max_avail_w = max(10, w - 8)
            bw = min(10, max(6, (max_avail_w - (k - 1) * gap) // k)) if k > 0 else 10
            bh = 13
            total_w = k * bw + (k - 1) * gap
            start_x = w - 4 - total_w

            outline_bm = qta.icon("fa5s.bookmark", color="rgba(0, 0, 0, 180)")

            for i, tag in enumerate(tags):
                x_pos = start_x + i * (bw + gap)
                y_pos = 2
                color = tag.color or "#a855f7"

                for ox, oy in outline_offsets:
                    outline_bm.paint(
                        painter, QRect(int(x_pos + ox), int(y_pos + oy), int(bw), int(bh))
                    )

                qta.icon("fa5s.bookmark", color=color).paint(
                    painter, QRect(int(x_pos), int(y_pos), int(bw), int(bh))
                )

        if has_note:
            note_color = "#38bdf8" if self.is_dark else "#0284c7"
            nx, ny, nw, nh = w - 14, h - 14, 11, 11
            note_outline = qta.icon("fa5s.sticky-note", color="rgba(0, 0, 0, 180)")
            for ox, oy in outline_offsets:
                note_outline.paint(painter, QRect(nx + ox, ny + oy, nw, nh))
            qta.icon("fa5s.sticky-note", color=note_color).paint(
                painter, QRect(nx, ny, nw, nh)
            )


class CompositeExerciseGroup(QFrame):
    """Contenedor visual para ejercicios que contienen múltiples incisos numéricos.

    Muestra un botón cabecera con el número del ejercicio que permite contraer/expandir
    el grupo, seguido por los botones de sus incisos individuales (ej: [1] [1.1] [1.2]...).
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
        self.is_collapsed = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        border_color = "#334155" if is_dark else "#cbd5e1"
        bg_color = "#111827" if is_dark else "#f8fafc"
        self.setStyleSheet(
            f"""
            CompositeExerciseGroup {{
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

        # 1. Botón cabecera de grupo con el número base del ejercicio (ej: "1")
        self.header_btn = GroupHeaderCellButton(
            node,
            is_dark=is_dark,
            parent=self,
        )
        self.header_btn.clicked.connect(self.toggle_collapsed)
        layout.addWidget(self.header_btn)

        # 2. Sub-botones para cada inciso (sin cuadro duplicado 'Ej. {n}')
        self.sub_buttons: list[ExerciseCellButton] = []
        for sub_node in node.incisos:
            btn_sub = ExerciseCellButton(
                sub_node,
                is_dark=is_dark,
                is_sub_inciso=True,
                parent=self,
            )
            if on_sub_clicked:
                btn_sub.clicked.connect(lambda _, n=sub_node: on_sub_clicked(n))
            self.sub_buttons.append(btn_sub)
            layout.addWidget(btn_sub)

        self._update_group_tooltip()

    def _update_group_tooltip(self) -> None:
        if self.is_collapsed:
            self.setToolTip(
                f"Ejercicio {self.node.exercise} · {len(self.node.incisos)} incisos (contraído · clic para expandir)"
            )
        else:
            self.setToolTip(
                f"Ejercicio {self.node.exercise} · {len(self.node.incisos)} incisos (expandido · clic en [{self.node.exercise}] para contraer)"
            )

    def set_collapsed(self, collapsed: bool) -> None:
        """Contrae u oculta los sub-botones de incisos, mostrando únicamente el botón cabecera."""
        self.is_collapsed = collapsed
        self.header_btn.set_collapsed(collapsed)
        for btn in self.sub_buttons:
            btn.setVisible(not collapsed)
        self._update_group_tooltip()
        self.updateGeometry()
        self.adjustSize()
        p = self.parentWidget()
        if p:
            if p.layout():
                p.layout().invalidate()
            p.updateGeometry()
            p.adjustSize()

    def toggle_collapsed(self) -> None:
        """Conmuta entre expandido y contraído."""
        self.set_collapsed(not self.is_collapsed)



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
        header_layout.setSpacing(10)

        # Botón conmutador de colapso de sección (Chevron)
        self.is_collapsed = False
        self.btn_collapse = QPushButton()
        self.btn_collapse.setObjectName("btn_collapse_section")
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.setFixedSize(26, 26)
        self._update_collapse_icon()
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.btn_collapse)

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

        # Barra de progreso unificada (Hechos en verde + En Dificultad en rojo en la misma barra)
        prog_h = QHBoxLayout()
        prog_h.setSpacing(10)

        prog_bar = SegmentedProgressBar(is_dark=is_dark, corner_radius=4)
        prog_bar.setObjectName("sec_progress_bar")
        prog_bar.setFixedHeight(8)
        prog_bar.set_segmented_values(
            completed=sec_status.completed_weight,
            failed=sec_status.failed_units,
            total=sec_status.total_units,
        )
        prog_bar.setToolTip(
            f"Hechos: {sec_status.completed_display} / {sec_status.total_units} ({sec_status.completion_percentage:.1f}%) · "
            f"En dificultad: {sec_status.failed_units} / {sec_status.total_units} ({sec_status.failed_percentage:.1f}%) · "
            f"Pendientes: {sec_status.pending_units} / {sec_status.total_units}"
        )
        prog_h.addWidget(prog_bar, 1)

        if sec_status.failed_units > 0:
            comp_col = "#bef264" if is_dark else "#15803d"
            fail_col = "#f87171" if is_dark else "#ef4444"
            lbl_progress = QLabel(
                f"<span style='color: {comp_col}; font-weight: 700;'>{sec_status.completed_display} hechos</span> "
                f"({sec_status.completion_percentage:.1f}%) · "
                f"<span style='color: {fail_col}; font-weight: 700;'>{sec_status.failed_units} en dificultad</span> "
                f"({sec_status.failed_percentage:.1f}%)"
            )
        else:
            lbl_progress = QLabel(
                f"{sec_status.completed_display} / {sec_status.total_units} hechos ({sec_status.completion_percentage:.1f}%)"
            )
            lbl_progress.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")

        lbl_progress.setObjectName("lbl_sec_progress")
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
        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.Shape.HLine)
        self.sep.setStyleSheet(f"color: {'#1e293b' if is_dark else '#e2e8f0'}; max-height: 1px;")
        layout.addWidget(self.sep)

        # Contenedor interactivo de ejercicios con FlowLayout (distribución fluida sin columnas rígidas)
        self.exercises_container = QWidget()
        self.exercises_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.flow_layout = FlowLayout(self.exercises_container, margin=0, h_spacing=8, v_spacing=8)

        for node in sec_status.exercise_nodes:
            if node.has_incisos:
                group = CompositeExerciseGroup(
                    node,
                    is_dark=is_dark,
                    on_sub_clicked=self.on_node_click,
                    parent=self,
                )
                self.flow_layout.addWidget(group)
            else:
                btn_single = ExerciseCellButton(
                    node,
                    is_dark=is_dark,
                    is_sub_inciso=False,
                    parent=self,
                )
                if self.on_node_click:
                    btn_single.clicked.connect(lambda _, n=node: self.on_node_click(n))
                self.flow_layout.addWidget(btn_single)

        layout.addWidget(self.exercises_container)

    def _update_collapse_icon(self) -> None:
        icon_name = "fa5s.chevron-right" if self.is_collapsed else "fa5s.chevron-down"
        icon_color = "#94a3b8" if self.is_dark else "#64748b"
        self.btn_collapse.setIcon(qta.icon(icon_name, color=icon_color))
        self.btn_collapse.setToolTip("Expandir sección" if self.is_collapsed else "Contraer sección")
        self.btn_collapse.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: rgba(148, 163, 184, 0.2);
            }
            """
        )

    def set_collapsed(self, collapsed: bool) -> None:
        """Contrae u oculta los ejercicios de la sección, reduciendo la altura de la tarjeta."""
        self.is_collapsed = collapsed
        self._update_collapse_icon()
        self.exercises_container.setVisible(not collapsed)
        self.sep.setVisible(not collapsed)
        self.updateGeometry()
        self.adjustSize()
        p = self.parentWidget()
        if p:
            if p.layout():
                p.layout().invalidate()
            p.updateGeometry()
            p.adjustSize()

    def toggle_collapse(self) -> None:
        """Alterna el estado de contracción de la sección."""
        self.set_collapsed(not self.is_collapsed)

    def set_all_groups_collapsed(self, collapsed: bool) -> None:
        """Contrae o expande todos los grupos de ejercicios compuestos con incisos de la sección."""
        for group in self.findChildren(CompositeExerciseGroup):
            group.set_collapsed(collapsed)
        if hasattr(self, "exercises_container"):
            if self.exercises_container.layout():
                self.exercises_container.layout().invalidate()
            self.exercises_container.updateGeometry()
            self.exercises_container.adjustSize()
        self.updateGeometry()
        self.adjustSize()
        p = self.parentWidget()
        if p:
            if p.layout():
                p.layout().invalidate()
            p.updateGeometry()
            p.adjustSize()

    def apply_tag_filter(self, mode: str, tag_id: str | None = None) -> None:
        """Aplica el filtro de etiquetas sobre los botones de ejercicio de esta sección."""
        buttons = self.findChildren(ExerciseCellButton)
        for btn in buttons:
            if mode == "all":
                btn.set_dimmed(False)
            elif mode == "only_tagged":
                btn.set_dimmed(len(btn.node.tags) == 0)
            elif mode == "by_tag":
                btn.set_dimmed(not any(t.id == tag_id for t in btn.node.tags))

        header_buttons = self.findChildren(GroupHeaderCellButton)
        for h_btn in header_buttons:
            tags = h_btn.node.aggregated_tags
            if mode == "all":
                h_btn.set_dimmed(False)
            elif mode == "only_tagged":
                h_btn.set_dimmed(len(tags) == 0)
            elif mode == "by_tag":
                h_btn.set_dimmed(not any(t.id == tag_id for t in tags))



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
        self.active_filter_mode = "all"
        self.active_filter_tag_id: str | None = None
        self.all_incisos_collapsed = False

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

        # Filtro rápido por marcadores
        lbl_filter = QLabel("Filtrar:")
        lbl_filter.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        top_bar.addWidget(lbl_filter)

        self.combo_tag_filter = QComboBox()
        self.combo_tag_filter.setObjectName("planner_tag_filter_combo")
        self.combo_tag_filter.setStyleSheet("padding: 4px 8px; font-size: 12px; border-radius: 6px;")
        self.combo_tag_filter.currentIndexChanged.connect(self._on_filter_changed)
        top_bar.addWidget(self.combo_tag_filter)

        self.btn_manage_tags = QPushButton("Marcadores...")
        self.btn_manage_tags.setIcon(qta.icon("fa5s.tags", color="#a855f7"))
        self.btn_manage_tags.setToolTip("Administrar el catálogo de etiquetas y marcadores")
        self.btn_manage_tags.clicked.connect(self._on_manage_tags)
        top_bar.addWidget(self.btn_manage_tags)

        self.btn_schedule = QPushButton("Cronograma...")
        self.btn_schedule.setIcon(qta.icon("fa5s.calendar-alt", color="#38bdf8"))
        self.btn_schedule.setToolTip("Configurar período de cursada y fechas de examen")
        self.btn_schedule.clicked.connect(self._on_manage_schedule)
        top_bar.addWidget(self.btn_schedule)

        # Botón general para contraer y expandir todas las secciones
        self.all_sections_collapsed = False
        self.btn_toggle_sections = QPushButton("Contraer secciones")
        self.btn_toggle_sections.setObjectName("planner_btn_toggle_sections")
        self._update_btn_sections_style()
        self.btn_toggle_sections.clicked.connect(self._on_toggle_sections)
        top_bar.addWidget(self.btn_toggle_sections)

        # Botón general para contraer y expandir todos los ejercicios con incisos
        self.btn_toggle_expand_all = QPushButton("Contraer todos")
        self.btn_toggle_expand_all.setObjectName("planner_btn_toggle_expand_all")
        self._update_btn_expand_all_style()
        self.btn_toggle_expand_all.clicked.connect(self._on_toggle_expand_all)
        top_bar.addWidget(self.btn_toggle_expand_all)

        # Botones de acción globales
        self.btn_sync = QPushButton("Sincronizar con Registros")
        self.btn_sync.setIcon(qta.icon("fa5s.sync-alt", color="#38bdf8"))
        self.btn_sync.setToolTip("Añade automáticamente a la planificación los ejercicios de registros no contemplados.")
        self.btn_sync.clicked.connect(self._on_sync_records)
        top_bar.addWidget(self.btn_sync)

        self.btn_add_section = QPushButton("Nueva Sección / Guía")
        self._update_btn_add_section_style()
        self.btn_add_section.clicked.connect(self._on_add_section)
        top_bar.addWidget(self.btn_add_section)

        main_layout.addLayout(top_bar)

        # 2. Resumen Global (Chips / Bento Cards)
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName("planner_summary_frame")
        self.summary_frame.setStyleSheet(
            f"""
            QFrame#planner_summary_frame {{
                background-color: {"#111827" if is_dark_mode else "#fdfcf7"};
                border: 1px solid {"#1e293b" if is_dark_mode else "#e4ded4"};
                border-radius: 12px;
                padding: 12px 16px;
            }}
            """
        )
        sum_layout = QHBoxLayout(self.summary_frame)
        sum_layout.setSpacing(20)

        self.lbl_card_total = self._make_stat_badge("Total Planificado", "0", "total_planificado")
        self.lbl_card_completed = self._make_stat_badge("Hechos", "0", "hechos")
        self.lbl_card_failed = self._make_stat_badge("En Dificultad", "0", "en_dificultad")
        self.lbl_card_pending = self._make_stat_badge("Pendientes", "0", "pendientes")

        sum_layout.addLayout(self.lbl_card_total)
        sum_layout.addLayout(self.lbl_card_completed)
        sum_layout.addLayout(self.lbl_card_failed)
        sum_layout.addLayout(self.lbl_card_pending)

        # Barra de progreso global unificada
        v_prog = QVBoxLayout()
        v_prog.setSpacing(4)
        v_prog.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        h_labels = QHBoxLayout()
        lbl_global_p = QLabel("Progreso Global:")
        lbl_global_p.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        h_labels.addWidget(lbl_global_p)

        self.lbl_global_breakdown = QLabel("")
        self.lbl_global_breakdown.setObjectName("planner_global_breakdown")
        self.lbl_global_breakdown.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8;")
        self.lbl_global_breakdown.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        h_labels.addWidget(self.lbl_global_breakdown, 1)
        v_prog.addLayout(h_labels)

        self.global_progress_bar = SegmentedProgressBar(is_dark=is_dark_mode, corner_radius=7)
        self.global_progress_bar.setObjectName("planner_global_progress_bar")
        self.global_progress_bar.setFixedHeight(14)
        v_prog.addWidget(self.global_progress_bar)

        sum_layout.addLayout(v_prog, 1)

        main_layout.addWidget(self.summary_frame)

        # 3. Área de Scroll vertical unificada para todas las guías
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setContentsMargins(0, 8, 0, 8)
        self.scroll_content_layout.setSpacing(0)

        # Contenedor para el estado vacío
        self.empty_state_container = QWidget()
        self.empty_state_layout = QVBoxLayout(self.empty_state_container)
        self.empty_state_layout.setContentsMargins(0, 0, 0, 0)
        self.empty_state_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_container.hide()
        self.scroll_content_layout.addWidget(self.empty_state_container)

        # Contenedor multi-columna para las tarjetas
        self.cards_columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.cards_columns_widget)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(14)
        self.columns_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_content_layout.addWidget(self.cards_columns_widget, 1)

        self.cards_layout = self.columns_layout  # alias de compatibilidad
        self.column_layouts: list[QVBoxLayout] = []
        self._current_column_count: int = 1
        self._section_cards: list[PlannedSectionCard] = []

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.refresh_view()

    def _update_btn_add_section_style(self) -> None:
        if self.is_dark:
            self.btn_add_section.setIcon(qta.icon("fa5s.plus-circle", color="#0b0f17"))
            self.btn_add_section.setStyleSheet(
                """
                QPushButton {
                    background-color: #10b981;
                    color: #0b0f17;
                    font-weight: 700;
                    padding: 7px 14px;
                    border-radius: 8px;
                    border: 1px solid #10b981;
                }
                QPushButton:hover {
                    background-color: #059669;
                    border-color: #059669;
                }
                """
            )
        else:
            self.btn_add_section.setIcon(qta.icon("fa5s.plus-circle", color="#ffffff"))
            self.btn_add_section.setStyleSheet(
                """
                QPushButton {
                    background-color: #059669;
                    color: #ffffff;
                    font-weight: 700;
                    padding: 7px 14px;
                    border-radius: 8px;
                    border: 1px solid #047857;
                }
                QPushButton:hover {
                    background-color: #047857;
                    border-color: #047857;
                }
                """
            )

    def _update_btn_expand_all_style(self) -> None:
        if not hasattr(self, "btn_toggle_expand_all"):
            return
        if getattr(self, "all_incisos_collapsed", False):
            self.btn_toggle_expand_all.setText("Expandir todos")
            self.btn_toggle_expand_all.setIcon(qta.icon("fa5s.expand-arrows-alt", color="#38bdf8"))
            self.btn_toggle_expand_all.setToolTip("Expandir todos los ejercicios con incisos")
        else:
            self.btn_toggle_expand_all.setText("Contraer todos")
            self.btn_toggle_expand_all.setIcon(qta.icon("fa5s.compress-arrows-alt", color="#38bdf8"))
            self.btn_toggle_expand_all.setToolTip("Contraer todos los ejercicios con incisos")

        self.btn_toggle_expand_all.setStyleSheet("padding: 5px 10px; font-size: 11px; border-radius: 6px;")

    def _on_toggle_expand_all(self) -> None:
        """Conmuta globalmente la contracción/expansión de todos los incisos."""
        self.all_incisos_collapsed = not getattr(self, "all_incisos_collapsed", False)
        self._update_btn_expand_all_style()
        for card in self.findChildren(PlannedSectionCard):
            card.set_all_groups_collapsed(self.all_incisos_collapsed)

    def _update_btn_sections_style(self) -> None:
        if not hasattr(self, "btn_toggle_sections"):
            return
        if getattr(self, "all_sections_collapsed", False):
            self.btn_toggle_sections.setText("Expandir secciones")
            self.btn_toggle_sections.setIcon(qta.icon("fa5s.expand", color="#a855f7"))
            self.btn_toggle_sections.setToolTip("Expandir todas las secciones de la planificación")
        else:
            self.btn_toggle_sections.setText("Contraer secciones")
            self.btn_toggle_sections.setIcon(qta.icon("fa5s.compress", color="#a855f7"))
            self.btn_toggle_sections.setToolTip("Contraer todas las secciones a su cabecera")

        self.btn_toggle_sections.setStyleSheet("padding: 5px 10px; font-size: 11px; border-radius: 6px;")

    def _on_toggle_sections(self) -> None:
        """Conmuta globalmente la contracción/expansión de todas las secciones."""
        self.all_sections_collapsed = not getattr(self, "all_sections_collapsed", False)
        self._update_btn_sections_style()
        for card in self._section_cards:
            card.set_collapsed(self.all_sections_collapsed)

    def _calculate_optimal_columns(self, available_width: int) -> int:
        """Calcula el número óptimo de columnas según el ancho disponible en el viewport."""
        if available_width <= 0:
            if hasattr(self, "scroll_area") and self.scroll_area.viewport():
                available_width = self.scroll_area.viewport().width()
        if available_width <= 0:
            available_width = max(100, self.width() - 40)

        spacing = 14
        target_col_w = 460
        cols = max(1, (available_width + spacing) // (target_col_w + spacing))
        return min(8, max(1, cols))

    def _rebuild_columns(self) -> None:
        """Reconstruye las N columnas del layout y distribuye las tarjetas existentes."""
        for card in self._section_cards:
            card.setParent(None)

        while self.columns_layout.count() > 0:
            item = self.columns_layout.takeAt(0)
            if item.layout():
                sub_lay = item.layout()
                while sub_lay.count() > 0:
                    sub_item = sub_lay.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        self.column_layouts.clear()

        col_count = max(1, self._current_column_count)
        for _ in range(col_count):
            col_lay = QVBoxLayout()
            col_lay.setContentsMargins(0, 0, 0, 0)
            col_lay.setSpacing(12)
            col_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.columns_layout.addLayout(col_lay, 1)
            self.column_layouts.append(col_lay)

        for i, card in enumerate(self._section_cards):
            card.setParent(self.cards_columns_widget)
            card.show()
            col_idx = i % col_count
            self.column_layouts[col_idx].addWidget(card)

        for col_lay in self.column_layouts:
            col_lay.addStretch()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        new_w = self.scroll_area.viewport().width() if hasattr(self, "scroll_area") else self.width()
        optimal_cols = self._calculate_optimal_columns(new_w)
        if optimal_cols != self._current_column_count and self._section_cards:
            self._current_column_count = optimal_cols
            self._rebuild_columns()

    def _get_badge_color(self, key: str) -> str:
        colors = {
            "total_planificado": "#38bdf8" if self.is_dark else "#0284c7",
            "hechos": "#10b981" if self.is_dark else "#059669",
            "en_dificultad": "#f87171" if self.is_dark else "#dc2626",
            "pendientes": "#cbd5e1" if self.is_dark else "#57534e",
        }
        return colors.get(key, "#10b981" if self.is_dark else "#059669")

    def _make_stat_badge(self, title: str, value: str, key: str) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(1)
        t_lbl = QLabel(title)
        t_lbl.setObjectName(f"stat_title_{key}")
        t_lbl.setStyleSheet(f"color: {'#94a3b8' if self.is_dark else '#78716c'}; font-size: 11px; font-weight: 600;")
        v_lbl = QLabel(value)
        v_lbl.setObjectName(f"stat_val_{key}")
        color = self._get_badge_color(key)
        v_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")
        v.addWidget(t_lbl)
        v.addWidget(v_lbl)
        return v

    def _update_stat_badge_styles(self) -> None:
        muted = "#94a3b8" if self.is_dark else "#78716c"
        for key in ("total_planificado", "hechos", "en_dificultad", "pendientes"):
            color = self._get_badge_color(key)
            w_val = self.summary_frame.findChild(QLabel, f"stat_val_{key}")
            if w_val:
                w_val.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")
            w_title = self.summary_frame.findChild(QLabel, f"stat_title_{key}")
            if w_title:
                w_title.setStyleSheet(f"color: {muted}; font-size: 11px; font-weight: 600;")

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.summary_frame.setStyleSheet(
            f"""
            QFrame#planner_summary_frame {{
                background-color: {"#111827" if is_dark else "#fdfcf7"};
                border: 1px solid {"#1e293b" if is_dark else "#e4ded4"};
                border-radius: 12px;
                padding: 12px 16px;
            }}
            """
        )
        self.global_progress_bar.set_dark_mode(is_dark)
        if hasattr(self, "btn_add_section"):
            self._update_btn_add_section_style()
        if hasattr(self, "btn_toggle_expand_all"):
            self._update_btn_expand_all_style()
        if hasattr(self, "btn_toggle_sections"):
            self._update_btn_sections_style()
        self._update_stat_badge_styles()
        if self.app_service.is_record_open:
            self.refresh_view()

    def set_empty_state(self, is_empty: bool) -> None:
        """Habilita o deshabilita acciones de planificación según si hay proyecto activo."""
        self.btn_sync.setEnabled(not is_empty)
        self.btn_add_section.setEnabled(not is_empty)
        if hasattr(self, "btn_toggle_expand_all"):
            self.btn_toggle_expand_all.setEnabled(not is_empty)
        if hasattr(self, "btn_toggle_sections"):
            self.btn_toggle_sections.setEnabled(not is_empty)
        if hasattr(self, "combo_tag_filter"):
            self.combo_tag_filter.setEnabled(not is_empty)
        if hasattr(self, "btn_manage_tags"):
            self.btn_manage_tags.setEnabled(not is_empty)
        if hasattr(self, "btn_schedule"):
            self.btn_schedule.setEnabled(not is_empty)
        if is_empty:
            self._update_stat_badge("total_planificado", "-")
            self._update_stat_badge("hechos", "-")
            self._update_stat_badge("en_dificultad", "-")
            self._update_stat_badge("pendientes", "-")
            self.global_progress_bar.set_segmented_values(0, 0, 100)
            self.lbl_global_breakdown.setText("Sin proyecto activo")
            for card in self._section_cards:
                card.deleteLater()
            self._section_cards.clear()
            self.cards_columns_widget.hide()
            self.empty_state_container.hide()
        else:
            self.refresh_view()

    def refresh_view(self) -> None:
        """Calcula el estado del planificador y redibuja todas las secciones y tarjetas."""
        if not self.app_service.is_record_open:
            self.set_empty_state(True)
            return

        self._populate_filter_combo()
        overview: PlannerOverview = self.app_service.get_planner_overview()

        # Actualizar chips globales
        self._update_stat_badge("total_planificado", f"{overview.total_units}")
        self._update_stat_badge("hechos", f"{overview.completed_display}")
        self._update_stat_badge("en_dificultad", f"{overview.failed_units}")
        self._update_stat_badge("pendientes", f"{overview.pending_units}")

        # Actualizar barra de progreso global unificada
        self.global_progress_bar.set_segmented_values(
            completed=overview.completed_weight,
            failed=overview.failed_units,
            total=overview.total_units,
        )

        if overview.failed_units > 0:
            comp_col = "#bef264" if self.is_dark else "#15803d"
            fail_col = "#f87171" if self.is_dark else "#ef4444"
            self.lbl_global_breakdown.setText(
                f"<span style='color: {comp_col}; font-weight: 700;'>"
                f"{overview.global_completion_percentage:.1f}% hechos</span> · "
                f"<span style='color: {fail_col}; font-weight: 700;'>"
                f"{overview.global_failed_percentage:.1f}% en dificultad</span>"
            )
        else:
            self.lbl_global_breakdown.setText(
                f"{overview.global_completion_percentage:.1f}% hechos"
            )

        self.global_progress_bar.setToolTip(
            f"Hechos: {overview.completed_display} de {overview.total_units} ({overview.global_completion_percentage:.1f}%)\n"
            f"En dificultad: {overview.failed_units} de {overview.total_units} ({overview.global_failed_percentage:.1f}%)\n"
            f"Pendientes: {overview.pending_units} de {overview.total_units}"
        )

        # Limpiar tarjetas anteriores
        for card in self._section_cards:
            card.deleteLater()
        self._section_cards.clear()

        # Limpiar empty state previo
        while self.empty_state_layout.count() > 0:
            child = self.empty_state_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Si no hay secciones, mostrar Empty State amigable
        if not overview.sections:
            empty_widget = self._create_empty_state()
            self.empty_state_layout.addWidget(empty_widget)
            self.cards_columns_widget.hide()
            self.empty_state_container.show()
            return

        self.empty_state_container.hide()
        self.cards_columns_widget.show()

        # Dibujar cada sección planificada
        for sec_status in overview.sections:
            card = PlannedSectionCard(
                sec_status=sec_status,
                is_dark=self.is_dark,
                on_node_click=self._on_node_clicked,
                on_edit_click=self._on_edit_section,
                on_delete_click=self._on_delete_section,
                parent=self.cards_columns_widget,
            )
            if getattr(self, "all_incisos_collapsed", False):
                card.set_all_groups_collapsed(True)
            if getattr(self, "all_sections_collapsed", False):
                card.set_collapsed(True)
            self._section_cards.append(card)

        # Determinar número óptimo de columnas y construir la cuadrícula
        available_w = self.scroll_area.viewport().width() if hasattr(self, "scroll_area") else self.width()
        self._current_column_count = self._calculate_optimal_columns(available_w)
        self._rebuild_columns()
        self._apply_current_filter()


    def _populate_filter_combo(self) -> None:
        if not hasattr(self, "combo_tag_filter"):
            return
        current_data = self.combo_tag_filter.currentData()
        self.combo_tag_filter.blockSignals(True)
        self.combo_tag_filter.clear()
        self.combo_tag_filter.addItem("Todos los ejercicios", ("all", None))
        self.combo_tag_filter.addItem("Solo con marcadores", ("only_tagged", None))

        catalog = self.app_service.get_tag_catalog()
        for tag in catalog:
            self.combo_tag_filter.addItem(f"● {tag.name}", ("by_tag", tag.id))

        restored = False
        if current_data:
            for idx in range(self.combo_tag_filter.count()):
                if self.combo_tag_filter.itemData(idx) == current_data:
                    self.combo_tag_filter.setCurrentIndex(idx)
                    restored = True
                    break
        if not restored:
            self.combo_tag_filter.setCurrentIndex(0)
            self.active_filter_mode = "all"
            self.active_filter_tag_id = None
        self.combo_tag_filter.blockSignals(False)

    def _on_filter_changed(self, index: int) -> None:
        data = self.combo_tag_filter.itemData(index)
        if not data:
            self.active_filter_mode = "all"
            self.active_filter_tag_id = None
        else:
            self.active_filter_mode, self.active_filter_tag_id = data
        self._apply_current_filter()

    def _apply_current_filter(self) -> None:
        cards = self.findChildren(PlannedSectionCard)
        for card in cards:
            card.apply_tag_filter(self.active_filter_mode, self.active_filter_tag_id)

    def _on_manage_tags(self) -> None:
        if not self.app_service.is_record_open:
            return
        dlg = TagManagerDialog(self, self.app_service, is_dark=self.is_dark)
        dlg.exec()
        self.refresh_view()

    def _on_manage_schedule(self) -> None:
        if not self.app_service.is_record_open:
            return
        dlg = ScheduleConfigDialog(
            parent=self.window(),
            schedule=self.app_service.get_schedule(),
            is_dark=self.is_dark,
        )
        if dlg.exec() == ScheduleConfigDialog.DialogCode.Accepted:
            self.app_service.set_schedule(dlg.schedule)
            self.refresh_view()

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
        popup = ExerciseDetailPopup(self, node, app_service=self.app_service, is_dark=self.is_dark)
        if popup.exec() == ExerciseDetailPopup.DialogCode.Accepted:
            if popup.chosen_action == "load_timer":
                self.request_load_timer.emit(
                    node.section_type,
                    node.section_number,
                    node.exercise,
                    node.inciso,
                )
        self.refresh_view()

    def _on_add_section(self) -> None:
        if not self.app_service.is_record_open:
            return
        dlg = PlannedSectionDialog(self, is_dark=self.is_dark)
        if dlg.exec() == PlannedSectionDialog.DialogCode.Accepted and dlg.section_data:
            self.app_service.add_or_update_planned_section(dlg.section_data)
            self.refresh_view()

    def _on_edit_section(self, section: PlannedSection) -> None:
        if not self.app_service.is_record_open:
            return
        dlg = PlannedSectionDialog(self, section=section, is_dark=self.is_dark)
        if dlg.exec() == PlannedSectionDialog.DialogCode.Accepted and dlg.section_data:
            self.app_service.add_or_update_planned_section(dlg.section_data)
            self.refresh_view()

    def _on_delete_section(self, section: PlannedSection) -> None:
        if not self.app_service.is_record_open:
            return
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
        if not self.app_service.is_record_open:
            return
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
