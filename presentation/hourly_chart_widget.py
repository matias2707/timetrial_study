"""Widget gráfico personalizado para representar el histograma de distribución horaria de 24 horas.

Muestra las 24 franjas horarias del día (0 a 23 hs) indicando el volumen acumulado de
tiempo de estudio para identificar hábitos de concentración y horas pico de rendimiento.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from presentation.presentation_formatters import format_hh_mm_ss


class Hourly24hChartWidget(QWidget):
    """Componente visual que renderiza las 24 barras horarias del día con QPainter."""

    def __init__(self, parent: QWidget | None = None, is_dark_mode: bool = True) -> None:
        super().__init__(parent)
        self.hourly_data: dict[int, int] = {h: 0 for h in range(24)}
        self.is_dark: bool = is_dark_mode
        self.hovered_hour: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, distribution: dict[int, int]) -> None:
        self.hourly_data = {h: distribution.get(h, 0) for h in range(24)}
        self.update()

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.update()

    def _calc_geometry(self) -> tuple[float, float, float, float, float]:
        width = float(self.width())
        height = float(self.height())
        top_margin = 22.0
        bottom_margin = 32.0
        left_margin = 12.0
        right_margin = 12.0

        available_w = max(100.0, width - left_margin - right_margin)
        available_h = max(30.0, height - top_margin - bottom_margin)
        col_w = available_w / 24.0
        bar_w = max(6.0, min(24.0, col_w * 0.70))
        return top_margin, bottom_margin, left_margin, col_w, bar_w, available_h

    def mouseMoveEvent(self, event) -> None:
        top_m, bottom_m, left_m, col_w, bar_w, avail_h = self._calc_geometry()
        mx = event.position().x()
        my = event.position().y()

        hovered = None
        for h in range(24):
            center_x = left_m + h * col_w + (col_w / 2.0)
            bar_x = center_x - (bar_w / 2.0)
            if bar_x <= mx <= bar_x + bar_w and top_m <= my <= self.height() - bottom_m + 10:
                hovered = h
                self._show_hour_tooltip(h, event.globalPosition().toPoint())
                break

        if hovered != self.hovered_hour:
            self.hovered_hour = hovered
            self.update()

    def leaveEvent(self, event) -> None:
        self.hovered_hour = None
        self.update()

    def _show_hour_tooltip(self, hour: int, global_pos: QPoint) -> None:
        ex_ms = self.hourly_data.get(hour, 0)
        time_text = format_hh_mm_ss(ex_ms)
        total_ms = sum(self.hourly_data.values())
        pct = (ex_ms / total_ms * 100.0) if total_ms > 0 else 0.0

        msg = (
            f"<b>Franja {hour:02d}:00 a {hour:02d}:59 hs</b><br>"
            f"⏱️ Tiempo estudiado: <b>{time_text}</b><br>"
            f"📊 Actividad: <b>{pct:.1f}%</b> del total"
        )
        QToolTip.showText(global_pos, msg, self)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = float(self.width())
        height = float(self.height())
        top_m, bottom_m, left_m, col_w, bar_w, avail_h = self._calc_geometry()

        max_ms = max(list(self.hourly_data.values()) + [3_600_000])

        bg_track_color = QColor("#1e293b" if self.is_dark else "#f1f5f9")
        bar_fill_color = QColor("#0284c7" if self.is_dark else "#0369a1")
        peak_fill_color = QColor("#059669" if self.is_dark else "#047857")
        text_muted = QColor("#94a3b8" if self.is_dark else "#64748b")
        text_highlight = QColor("#ffffff" if self.is_dark else "#0f172a")

        peak_hour = max(self.hourly_data, key=self.hourly_data.get) if max(self.hourly_data.values()) > 0 else -1

        font_labels = QFont("Segoe UI", 7)
        painter.setFont(font_labels)

        for h in range(24):
            center_x = left_m + h * col_w + (col_w / 2.0)
            bar_x = center_x - (bar_w / 2.0)
            ms = self.hourly_data.get(h, 0)
            is_hovered = self.hovered_hour == h
            is_peak = h == peak_hour and ms > 0

            # 1. Pista de fondo de cada barra
            track_rect = QRectF(bar_x, top_m, bar_w, avail_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_track_color))
            painter.drawRoundedRect(track_rect, 3.0, 3.0)

            # 2. Barra rellena con el tiempo
            if ms > 0:
                ratio = min(1.0, ms / max_ms)
                bar_h = max(4.0, ratio * avail_h)
                bar_y = height - bottom_m - bar_h
                fill_rect = QRectF(bar_x, bar_y, bar_w, bar_h)

                color = peak_fill_color if is_peak else bar_fill_color
                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(fill_rect, 3.0, 3.0)

                # Si es pico, dibujar pequeño indicador arriba
                if is_peak and bar_h >= 10:
                    painter.setPen(peak_fill_color)
                    font_peak = QFont("Segoe UI", 7, QFont.Weight.Bold)
                    painter.setFont(font_peak)
                    painter.drawText(
                        QRectF(center_x - 12.0, top_m - 16.0, 24.0, 14.0),
                        Qt.AlignmentFlag.AlignCenter,
                        "★",
                    )
                    painter.setFont(font_labels)

            # 3. Borde hover
            if is_hovered:
                hover_pen = QPen(text_highlight, 1.5)
                painter.setPen(hover_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(track_rect.adjusted(-1, -1, 1, 1), 4.0, 4.0)

            # 4. Etiquetas de hora (cada 3 horas o si es hovered)
            if h % 3 == 0 or h == 23 or is_hovered:
                lbl_text = f"{h:02d}"
                painter.setPen(text_highlight if is_hovered else text_muted)
                label_rect = QRectF(center_x - (col_w / 2.0), height - bottom_m + 6.0, col_w, 14.0)
                painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, lbl_text)
