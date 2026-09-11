"""Widget personalizado para renderizar el gráfico de barras semanal de horas de estudio.

Este componente pertenece a la capa de presentación y dibuja directamente
sobre un canvas QPainter usando antialiasing y temas claro/oscuro.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from application.statistics_service import DailyStatistic
from presentation.presentation_formatters import format_hh_mm


class WeeklyChartWidget(QWidget):
    """Componente visual que renderiza las barras de horas de estudio para 7 días."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.daily_stats: list[DailyStatistic] = []
        self.dark_mode: bool = False
        self.setMinimumHeight(175)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_stats(self, daily_stats: list[DailyStatistic]) -> None:
        """Asigna las estadísticas diarias y repinta el gráfico."""
        self.daily_stats = daily_stats
        self.update()

    def set_dark_mode(self, dark_mode: bool) -> None:
        """Configura la paleta de colores para modo claro u oscuro y repinta."""
        self.dark_mode = dark_mode
        self.update()

    def paintEvent(self, event) -> None:
        """Dibuja las columnas, barras coloreadas, etiquetas y marcas temporales."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = float(self.width())
        height = float(self.height())

        if not self.daily_stats:
            return

        n_days = len(self.daily_stats)
        col_width = width / n_days
        bar_width = min(42.0, max(24.0, col_width * 0.50))

        max_ms = max([d.exercise_time_ms for d in self.daily_stats] + [3_600_000])

        top_margin = 32.0
        bottom_margin = 46.0
        available_bar_height = height - top_margin - bottom_margin

        bar_bg_color = QColor("#1e293b" if self.dark_mode else "#edf3ed")
        text_primary = QColor("#f8fafc" if self.dark_mode else "#0f172a")
        text_muted = QColor("#94a3b8" if self.dark_mode else "#64748b")
        text_zero = QColor("#64748b" if self.dark_mode else "#94a3b8")

        for i, stat in enumerate(self.daily_stats):
            center_x = i * col_width + (col_width / 2.0)
            bar_x = center_x - (bar_width / 2.0)

            bg_rect = QRectF(bar_x, top_margin, bar_width, available_bar_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bar_bg_color))
            painter.drawRoundedRect(bg_rect, 6.0, 6.0)

            if stat.exercise_time_ms > 0:
                ratio = min(1.0, stat.exercise_time_ms / max_ms)
                bar_h = max(8.0, ratio * available_bar_height)
                bar_y = height - bottom_margin - bar_h
                bar_rect = QRectF(bar_x, bar_y, bar_width, bar_h)
                painter.setBrush(QBrush(QColor("#84cc16")))
                painter.drawRoundedRect(bar_rect, 6.0, 6.0)

            time_text = format_hh_mm(stat.exercise_time_ms)
            font_time = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font_time)
            painter.setPen(text_primary if stat.exercise_time_ms > 0 else text_zero)
            time_rect = QRectF(center_x - (col_width / 2.0), top_margin - 24.0, col_width, 18.0)
            painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_text)

            font_day = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font_day)
            painter.setPen(text_primary)
            day_rect = QRectF(center_x - (col_width / 2.0), height - bottom_margin + 5.0, col_width, 16.0)
            painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, stat.day_name)

            font_date = QFont("Segoe UI", 8)
            painter.setFont(font_date)
            painter.setPen(text_muted)
            date_rect = QRectF(center_x - (col_width / 2.0), height - bottom_margin + 22.0, col_width, 14.0)
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, stat.date_str)
