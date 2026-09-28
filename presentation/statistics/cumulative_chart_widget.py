"""Widget interactivo con QPainter para visualizar la evolución acumulativa del estudio.

Este componente renderiza la curva de horas acumuladas a lo largo de las semanas
y la progresión de ejercicios completados versus intentos incompletos/fallados.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from application.statistics_service import CumulativeEvolutionData
from presentation.presentation_formatters import format_hh_mm


class CumulativeEvolutionChartWidget(QWidget):
    """Componente gráfico que renderiza la curva de aprendizaje y esfuerzo acumulativo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: CumulativeEvolutionData | None = None
        self._dark_mode: bool = False
        self._current_theme: str = "dark" if self._dark_mode else "light"
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)

    def set_data(self, data: CumulativeEvolutionData) -> None:
        """Asigna los datos acumulativos de evolución y solicita repintado."""
        self._data = data
        self.update()

    def set_theme(self, theme: str) -> None:
        """Configura el tema visual y solicita repintado."""
        self._current_theme = theme
        from presentation.theme_tokens import get_theme_tokens
        tokens = get_theme_tokens(theme)
        self._dark_mode = tokens.is_dark
        self.update()

    def set_dark_mode(self, is_dark: bool) -> None:
        """Actualiza la paleta visual para adaptarse al tema activo."""
        self.set_theme("dark" if is_dark else "light")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        from presentation.theme_tokens import get_theme_tokens
        tokens = get_theme_tokens(getattr(self, "_current_theme", "dark" if self._dark_mode else "light"))
        is_dark = tokens.is_dark

        bg_color = QColor(tokens.bg_chart or tokens.bg_card or ("#0f172a" if is_dark else "#ffffff"))
        border_color = QColor(tokens.card_border or ("#334155" if is_dark else "#e2e8f0"))
        text_primary = QColor(tokens.text_primary or ("#f8fafc" if is_dark else "#0f172a"))
        text_muted = QColor(tokens.text_muted or ("#94a3b8" if is_dark else "#64748b"))
        grid_color = QColor(tokens.chart_gridline or tokens.card_border or ("#1e293b" if is_dark else "#f1f5f9"))
        time_curve_color = QColor(tokens.chart_time_curve or tokens.accent_primary or ("#38bdf8" if is_dark else "#0284c7"))

        if tokens.chart_time_area:
            time_area_color = QColor(tokens.chart_time_area)
        else:
            time_area_color = QColor(time_curve_color.red(), time_curve_color.green(), time_curve_color.blue(), 40 if is_dark else 35)

        completed_color = QColor(tokens.success_text or ("#10b981" if is_dark else "#059669"))
        failed_color = QColor(tokens.danger_text or ("#ef4444" if is_dark else "#dc2626"))

        # Fondo del card
        card_rect = QRectF(0, 0, w, h)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(card_rect.adjusted(1, 1, -1, -1), 10.0, 10.0)

        # Si no hay datos o puntos
        if not self._data or not self._data.points:
            painter.setPen(text_muted)
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                card_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Aún no hay suficientes sesiones para graficar la evolución acumulada.\n"
                "¡Completa tus primeros ejercicios para proyectar tu curva de aprendizaje!",
            )
            return

        points = self._data.points
        n_points = len(points)

        # Márgenes del gráfico
        left_m = 65.0
        right_m = 65.0
        top_m = 48.0
        bottom_m = 42.0

        plot_w = w - left_m - right_m
        plot_h = h - top_m - bottom_m

        if plot_w <= 20 or plot_h <= 20:
            return

        # Escalas
        max_time_ms = max(self._data.total_study_time_ms, 3_600_000)  # Mínimo 1 hora
        max_time_hours = max_time_ms / 3_600_000.0

        total_ex = self._data.total_completed + self._data.total_failed
        max_count = max(total_ex, 5)

        # Leyenda superior
        font_legend = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_legend)

        # Leyenda: Tiempo neto
        painter.setPen(time_curve_color)
        painter.drawText(QRectF(left_m, 12, 180, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"⏱️ Tiempo: {format_hh_mm(self._data.total_study_time_ms)}")

        # Leyenda: Completados
        painter.setPen(completed_color)
        painter.drawText(QRectF(left_m + 190, 12, 160, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"✓ Completados: {self._data.total_completed}")

        # Leyenda: Incompletos
        painter.setPen(failed_color)
        painter.drawText(QRectF(left_m + 360, 12, 160, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"✗ Incompletos: {self._data.total_failed}")

        # Líneas de rejilla horizontales (4 divisiones)
        painter.setFont(QFont("Segoe UI", 8))
        grid_pen = QPen(grid_color, 1, Qt.PenStyle.DashLine)
        for i in range(5):
            ratio = i / 4.0
            y = top_m + plot_h - (ratio * plot_h)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(left_m, y), QPointF(left_m + plot_w, y))

            # Eje Y Izquierdo (Horas de estudio)
            val_h = ratio * max_time_hours
            painter.setPen(text_muted)
            painter.drawText(QRectF(0, y - 8, left_m - 8, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{val_h:.1f}h")

            # Eje Y Derecho (Cantidad de ejercicios)
            val_cnt = int(round(ratio * max_count))
            painter.drawText(QRectF(left_m + plot_w + 8, y - 8, right_m - 8, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{val_cnt} ej")

        # Coordenadas X para los puntos
        def get_x(idx: int) -> float:
            if n_points == 1:
                return left_m + plot_w / 2.0
            return left_m + (idx / (n_points - 1)) * plot_w

        # 1. Trazar Curva y Área de Tiempo Acumulado
        path_time = QPainterPath()
        path_area = QPainterPath()

        start_x = get_x(0)
        start_y = top_m + plot_h - (points[0].cumulative_exercise_time_ms / max_time_ms) * plot_h

        path_time.moveTo(start_x, start_y)
        path_area.moveTo(start_x, top_m + plot_h)
        path_area.lineTo(start_x, start_y)

        for i in range(1, n_points):
            px = get_x(i)
            py = top_m + plot_h - (points[i].cumulative_exercise_time_ms / max_time_ms) * plot_h
            path_time.lineTo(px, py)
            path_area.lineTo(px, py)

        path_area.lineTo(get_x(n_points - 1), top_m + plot_h)
        path_area.closeSubpath()

        # Dibujar área bajo la curva
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(time_area_color))
        painter.drawPath(path_area)

        # Dibujar línea de tiempo
        painter.setPen(QPen(time_curve_color, 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path_time)

        # 2. Trazar Líneas de Completados e Incompletos
        path_comp = QPainterPath()
        path_fail = QPainterPath()

        comp_y0 = top_m + plot_h - (points[0].cumulative_completed / max_count) * plot_h
        fail_y0 = top_m + plot_h - (points[0].cumulative_failed / max_count) * plot_h

        path_comp.moveTo(start_x, comp_y0)
        path_fail.moveTo(start_x, fail_y0)

        for i in range(1, n_points):
            px = get_x(i)
            cy = top_m + plot_h - (points[i].cumulative_completed / max_count) * plot_h
            fy = top_m + plot_h - (points[i].cumulative_failed / max_count) * plot_h
            path_comp.lineTo(px, cy)
            path_fail.lineTo(px, fy)

        # Línea de completados (verde esmeralda discontinua o continua)
        painter.setPen(QPen(completed_color, 2, Qt.PenStyle.SolidLine))
        painter.drawPath(path_comp)

        # Línea de fallados (rojo suave)
        painter.setPen(QPen(failed_color, 1.5, Qt.PenStyle.DashLine))
        painter.drawPath(path_fail)

        # 3. Puntos de nodo y Etiquetas X
        font_x = QFont("Segoe UI", 8)
        painter.setFont(font_x)

        # Para no saturar el eje X si hay muchos puntos
        step_x = max(1, n_points // 7)

        for i, pt in enumerate(points):
            px = get_x(i)
            py_time = top_m + plot_h - (pt.cumulative_exercise_time_ms / max_time_ms) * plot_h

            # Punto destacado en tiempo
            painter.setPen(QPen(bg_color, 1.5))
            painter.setBrush(QBrush(time_curve_color))
            painter.drawEllipse(QPointF(px, py_time), 3.5, 3.5)

            # Etiqueta de fecha
            if i % step_x == 0 or i == n_points - 1:
                painter.setPen(text_muted)
                date_rect = QRectF(px - 35, top_m + plot_h + 8, 70, 20)
                painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, pt.display_date)
