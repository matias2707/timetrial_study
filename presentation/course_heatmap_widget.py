"""Widget gráfico de mapa de calor de constancia y camino al examen (Course Heatmap).

Renderiza la cuadrícula completa de semanas de cursada con estados de estudio diarios,
resaltado del día actual, siluetas de días futuros y marcadores de hitos evaluativos personalizables.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from presentation.presentation_formatters import format_hh_mm_ss

DAY_LETTERS = ["L", "M", "X", "J", "V", "S", "D"]
DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


class CourseHeatmapCanvas(QWidget):
    """Canvas de dibujo puro con QPainter para la cuadrícula del mapa de calor."""

    cell_hovered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.weeks: list[list[dict[str, Any]]] = []
        self.max_day_ms: int = 3_600_000
        self.is_dark: bool = True
        self.hovered_cell: tuple[int, int] | None = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setMinimumHeight(220)

    def set_data(self, weeks: list[list[dict[str, Any]]], max_day_ms: int, is_dark: bool = True) -> None:
        self.weeks = weeks
        self.max_day_ms = max(max_day_ms, 3_600_000)
        self.is_dark = is_dark
        self._update_canvas_height()
        self.update()

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def _calc_geometry(self) -> tuple[float, float, float, float, float]:
        """Calcula el offset y tamaño de celdas según el ancho disponible."""
        num_weeks = max(1, len(self.weeks))
        left_margin = 32.0
        top_margin = 24.0
        bottom_margin = 24.0
        available_w = max(100.0, float(self.width()) - left_margin - 24.0)

        # Determinar tamaño de celda cuadrado con espaciado
        raw_cell_w = available_w / num_weeks
        cell_size = min(22.0, max(12.0, raw_cell_w - 4.0))
        remaining_w = max(0.0, available_w - (cell_size * num_weeks))
        spacing = max(2.0, min(5.0, remaining_w / max(1, num_weeks - 1)))
        return left_margin, top_margin, bottom_margin, cell_size, spacing

    def get_required_height(self) -> int:
        """Devuelve la altura total exacta requerida para pintar los 7 días sin recortar."""
        _, top_m, bottom_m, cell_sz, sp = self._calc_geometry()
        # 7 días: de Lunes (índice 0) a Domingo (índice 6)
        total_h = top_m + 7.0 * cell_sz + 6.0 * sp + bottom_m
        return int(total_h + 4.0)

    def _update_canvas_height(self) -> None:
        req_h = self.get_required_height()
        if self.minimumHeight() != req_h:
            self.setMinimumHeight(req_h)
            self.updateGeometry()

    def sizeHint(self) -> QSize:
        return QSize(500, self.get_required_height())

    def minimumSizeHint(self) -> QSize:
        return QSize(300, self.get_required_height())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_canvas_height()

    def mouseMoveEvent(self, event) -> None:
        if not self.weeks:
            return
        left_m, top_m, _, cell_sz, sp = self._calc_geometry()
        pos = event.position()
        mx, my = pos.x(), pos.y()

        hovered = None
        for w_idx, week in enumerate(self.weeks):
            col_x = left_m + w_idx * (cell_sz + sp)
            if col_x <= mx <= col_x + cell_sz:
                for d_idx, day_info in enumerate(week):
                    row_y = top_m + d_idx * (cell_sz + sp)
                    if row_y <= my <= row_y + cell_sz:
                        hovered = (w_idx, d_idx)
                        self._show_cell_tooltip(day_info, event.globalPosition().toPoint())
                        break
            if hovered:
                break

        if hovered != self.hovered_cell:
            self.hovered_cell = hovered
            self.update()

    def leaveEvent(self, event) -> None:
        self.hovered_cell = None
        self.update()

    def _show_cell_tooltip(self, day_info: dict[str, Any], global_pos: QPoint) -> None:
        date_str = day_info.get("date", "")
        day_of_week = day_info.get("day_of_week", 0)
        day_name = DAY_NAMES[day_of_week] if 0 <= day_of_week < len(DAY_NAMES) else ""
        ex_ms = day_info.get("exercise_time_ms", 0)
        time_text = format_hh_mm_ss(ex_ms)
        milestone = day_info.get("milestone")

        lines = [f"<b>{day_name} {date_str}</b>"]
        if day_info.get("is_today"):
            lines.append("<i>(Hoy)</i>")

        if day_info.get("is_within_period"):
            if ex_ms > 0:
                lines.append(f"⏱️ Tiempo de estudio: <b>{time_text}</b>")
            elif day_info.get("is_past"):
                lines.append("⚪ Sin registros de estudio")
            else:
                lines.append("⏳ Día futuro de la cursada")
        else:
            lines.append("Día fuera del período")

        if milestone:
            m_name = milestone.get("name", "Examen")
            m_type = str(milestone.get("type", "")).capitalize()
            m_icon = milestone.get("icon") or "🎯"
            m_color = milestone.get("color") or "#ef4444"
            cat_suffix = f" · {m_type}" if m_type and m_type.lower() not in m_name.lower() else ""
            lines.append(
                f"<br><span style='color: {m_color};'>{m_icon}</span> "
                f"<b>{m_name}</b>{cat_suffix}"
            )

        QToolTip.showText(global_pos, "<br>".join(lines), self)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.weeks:
            return

        left_m, top_m, bottom_m, cell_sz, sp = self._calc_geometry()
        text_muted = QColor("#94a3b8" if self.is_dark else "#64748b")
        font_labels = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(font_labels)

        # 1. Etiquetas de días de la semana a la izquierda (Lunes a Domingo)
        for d_idx, letter in enumerate(DAY_LETTERS):
            row_y = top_m + d_idx * (cell_sz + sp)
            painter.setPen(text_muted)
            painter.drawText(
                QRectF(0, row_y, left_m - 8.0, cell_sz),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                letter,
            )

        # 2. Encabezados de semana arriba
        font_week = QFont("Segoe UI", 7)
        painter.setFont(font_week)
        for w_idx in range(len(self.weeks)):
            col_x = left_m + w_idx * (cell_sz + sp)
            if w_idx % 2 == 0 or len(self.weeks) <= 12:
                w_lbl = f"S{w_idx + 1}"
                painter.setPen(text_muted)
                painter.drawText(
                    QRectF(col_x - 4.0, 0, cell_sz + 8.0, top_m - 4.0),
                    Qt.AlignmentFlag.AlignCenter,
                    w_lbl,
                )

        # 3. Dibujar celdas de las semanas
        for w_idx, week in enumerate(self.weeks):
            col_x = left_m + w_idx * (cell_sz + sp)
            for d_idx, day_info in enumerate(week):
                row_y = top_m + d_idx * (cell_sz + sp)
                cell_rect = QRectF(col_x, row_y, cell_sz, cell_sz)
                self._draw_day_cell(painter, cell_rect, day_info, w_idx, d_idx)

    def _draw_day_cell(
        self,
        painter: QPainter,
        rect: QRectF,
        day: dict[str, Any],
        w_idx: int,
        d_idx: int,
    ) -> None:
        is_within = day.get("is_within_period", False)
        is_today = day.get("is_today", False)
        is_past = day.get("is_past", False)
        is_future = day.get("is_future", False)
        ex_ms = day.get("exercise_time_ms", 0)
        milestone = day.get("milestone")
        is_hovered = self.hovered_cell == (w_idx, d_idx)

        # Determinar color de relleno
        if not is_within:
            bg_color = QColor(0, 0, 0, 0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(rect, 3.0, 3.0)
            return

        if is_past or (is_today and ex_ms > 0):
            if ex_ms == 0:
                bg_color = QColor("#1e293b" if self.is_dark else "#e2e8f0")
            elif ex_ms < 3_600_000:  # < 1h
                bg_color = QColor("#365314" if self.is_dark else "#d9f99d")
            elif ex_ms < 7_200_000:  # 1-2h
                bg_color = QColor("#4d7c0f" if self.is_dark else "#a3e635")
            elif ex_ms < 10_800_000:  # 2-3h
                bg_color = QColor("#65a30d" if self.is_dark else "#84cc16")
            else:  # >= 3h
                bg_color = QColor("#84cc16" if self.is_dark else "#4d7c0f")
        else:
            # Días futuros: silueta tenue
            bg_color = QColor("#0f172a" if self.is_dark else "#f8fafc")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 3.0, 3.0)

        # Borde para días futuros dentro de la cursada
        if is_future:
            border_pen = QPen(QColor("#334155" if self.is_dark else "#cbd5e1"), 1.0, Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 3.0, 3.0)

        # Hito evaluativo personalizado (Examen, TP, etc.)
        if milestone:
            m_color_str = milestone.get("color")
            if not m_color_str:
                m_type = str(milestone.get("type", "")).lower()
                if "final" in m_type:
                    m_color_str = "#a855f7"
                elif "recup" in m_type:
                    m_color_str = "#f59e0b"
                else:
                    m_color_str = "#ef4444"
            m_color = QColor(m_color_str)

            # Anillo exterior del hito con el color seleccionado
            m_pen = QPen(m_color, 2.0)
            painter.setPen(m_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3.0, 3.0)

            # Marcador central del hito con el color seleccionado
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(m_color))
            center = rect.center()
            painter.drawEllipse(center, 2.5, 2.5)

        # Resaltado de HOY (borde azul brillante)
        if is_today:
            today_pen = QPen(QColor("#38bdf8"), 2.0)
            painter.setPen(today_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3.0, 3.0)

        # Hover highlight
        if is_hovered:
            hover_pen = QPen(QColor("#ffffff" if self.is_dark else "#0f172a"), 1.5)
            painter.setPen(hover_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 3.0, 3.0)


class CourseHeatmapWidget(QWidget):
    """Componente contenedor con banner de racha, canvas de heatmap y leyenda."""

    request_configure_schedule = Signal()

    def __init__(self, parent: QWidget | None = None, is_dark_mode: bool = True) -> None:
        super().__init__(parent)
        self.is_dark: bool = is_dark_mode
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Banner motivacional superior (Racha y Cuenta regresiva)
        self.banner_frame = QWidget()
        b_layout = QHBoxLayout(self.banner_frame)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(8)

        self.lbl_streak = QLabel("🔥 Racha actual: 0 días")
        self.lbl_streak.setStyleSheet("font-size: 13px; font-weight: 700; color: #f59e0b;")
        b_layout.addWidget(self.lbl_streak)

        self.lbl_separator = QLabel("·")
        self.lbl_separator.setStyleSheet("color: #64748b; font-weight: 700;")
        b_layout.addWidget(self.lbl_separator)

        self.lbl_countdown = QLabel("🎯 Sin exámenes próximos definidos")
        self.lbl_countdown.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8;")
        b_layout.addWidget(self.lbl_countdown)

        b_layout.addStretch()

        self.btn_config_schedule = QPushButton("📅 Configurar Cronograma")
        self.btn_config_schedule.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                font-weight: 600;
                padding: 3px 10px;
                border-radius: 6px;
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(56, 189, 248, 0.25);
            }
        """)
        self.btn_config_schedule.clicked.connect(self.request_configure_schedule.emit)
        b_layout.addWidget(self.btn_config_schedule)

        layout.addWidget(self.banner_frame)

        # 2. Estado vacío cuando no hay cronograma
        self.empty_prompt = QWidget()
        ep_layout = QHBoxLayout(self.empty_prompt)
        ep_layout.setContentsMargins(14, 12, 14, 12)
        self.lbl_empty_msg = QLabel(
            "📅 <b>Cronograma no configurado:</b> Define las fechas de inicio, fin y exámenes en el Planificador "
            "para activar el mapa de calor de constancia y el camino al examen."
        )
        self.lbl_empty_msg.setStyleSheet("color: #94a3b8; font-size: 12px;")
        ep_layout.addWidget(self.lbl_empty_msg)
        layout.addWidget(self.empty_prompt)

        # 3. Canvas del heatmap
        self.canvas = CourseHeatmapCanvas(self)
        layout.addWidget(self.canvas)

        # 4. Leyenda inferior
        self.legend_widget = QWidget()
        leg_layout = QHBoxLayout(self.legend_widget)
        leg_layout.setContentsMargins(4, 2, 4, 2)
        leg_layout.setSpacing(14)

        leg_text = QLabel(
            "<span style='color: #94a3b8;'>Intensidad de estudio:</span> "
            "<span style='color: #1e293b;'>■</span> "
            "<span style='color: #365314;'>■</span> "
            "<span style='color: #4d7c0f;'>■</span> "
            "<span style='color: #84cc16;'>■</span> "
            "&nbsp;&nbsp;·&nbsp;&nbsp;"
            "<span style='color: #38bdf8;'>⭕ Hoy</span> "
            "&nbsp;&nbsp;·&nbsp;&nbsp;"
            "<span style='color: #ef4444;'>●</span> "
            "<span style='color: #f59e0b;'>●</span> "
            "<span style='color: #a855f7;'>● Hitos y exámenes</span>"
        )
        leg_text.setStyleSheet("font-size: 11px;")
        leg_layout.addWidget(leg_text)
        leg_layout.addStretch()
        layout.addWidget(self.legend_widget)

    def sizeHint(self) -> QSize:
        canvas_h = self.canvas.get_required_height() if hasattr(self, "canvas") else 220
        return QSize(500, canvas_h + 85)

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.canvas.set_dark_mode(is_dark)

    def set_heatmap_data(self, data: dict[str, Any]) -> None:
        """Actualiza todos los subcomponentes con los datos calculados de cursada."""
        has_schedule = data.get("has_schedule", False)
        streak = data.get("streak_days", 0)
        self.lbl_streak.setText(f"🔥 Racha actual: <b>{streak}</b> día{'s' if streak != 1 else ''}")

        next_m = data.get("next_milestone")
        days_until = data.get("days_until_next_milestone")
        if next_m and days_until is not None:
            m_name = next_m.get("name", "Examen")
            m_icon = next_m.get("icon") or "🎯"
            m_color = next_m.get("color") or "#38bdf8"
            if days_until == 0:
                count_str = f"{m_icon} <b>¡HOY es {m_name}!</b>"
            elif days_until == 1:
                count_str = f"{m_icon} <b>¡Mañana es {m_name}!</b>"
            else:
                count_str = f"{m_icon} Faltan <b>{days_until}</b> días para <b>{m_name}</b>"
            self.lbl_countdown.setText(count_str)
            self.lbl_countdown.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {m_color};")
            self.lbl_countdown.setVisible(True)
            self.lbl_separator.setVisible(True)
        else:
            self.lbl_countdown.setVisible(False)
            self.lbl_separator.setVisible(False)

        if has_schedule:
            self.empty_prompt.setVisible(False)
            self.canvas.setVisible(True)
            self.legend_widget.setVisible(True)
            self.canvas.set_data(
                weeks=data.get("weeks", []),
                max_day_ms=data.get("max_day_ms", 3_600_000),
                is_dark=self.is_dark,
            )
        else:
            self.empty_prompt.setVisible(True)
            self.canvas.setVisible(False)
            self.legend_widget.setVisible(False)

    set_data = set_heatmap_data
