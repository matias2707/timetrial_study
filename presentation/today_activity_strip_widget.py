"""Widget del Activity Strip de 24 horas para el Home (TASK-014).

Renderiza una franja horizontal compacta con 24 celdas correspondientes a las horas
del día (00 a 23 hs), mostrando intensidad de estudio, hora actual, aguja vertical
indicadora del paso del tiempo y tooltips detallados.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from presentation.presentation_formatters import format_hh_mm_ss


class _TimelineNeedleOverlay(QWidget):
    """Capa transparente superpuesta que dibuja la aguja indicadora de la hora actual."""

    def __init__(self, strip: TodayActivityStripWidget, parent: QWidget) -> None:
        super().__init__(parent)
        self._strip = strip
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def calculate_needle_x(self) -> float:
        """Calcula la coordenada X exacta de la aguja sobre la pista de celdas."""
        cells = self._strip._cells
        if not cells or len(cells) < 24:
            return 0.0

        g0 = cells[0].geometry()
        g23 = cells[23].geometry()
        if g0.width() <= 0 or g23.width() <= 0:
            w = float(self.width() or self._strip.width() or 600.0)
            return self._strip.needle_progress * w

        now = self._strip.current_time
        h = max(0, min(23, now.hour))
        m = now.minute
        s = now.second
        us = now.microsecond

        # Fracción transcurrida dentro de la hora actual [0.0, 1.0)
        fraction_hour = (m * 60.0 + s + us / 1_000_000.0) / 3600.0
        fraction_hour = max(0.0, min(1.0, fraction_hour))

        cell_h = cells[h].geometry()
        x_start = float(cell_h.x())

        if h < 23:
            cell_next = cells[h + 1].geometry()
            x_next = float(cell_next.x())
            needle_x = x_start + fraction_hour * (x_next - x_start)
        else:
            x_end = float(cell_h.x() + cell_h.width())
            needle_x = x_start + fraction_hour * (x_end - x_start)

        return needle_x

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._strip.show_needle:
            return

        cells = self._strip._cells
        if not cells or len(cells) < 24:
            return

        needle_x = self.calculate_needle_x()
        if needle_x <= 0:
            return

        g0 = cells[0].geometry()
        top_y = float(g0.y())
        bottom_y = float(g0.y() + g0.height())
        if bottom_y <= top_y:
            top_y = 2.0
            bottom_y = float(max(2.0, self.height() - 2.0))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = self._strip.is_dark_mode
        accent_color_str = getattr(self._strip, "_current_hour_color", None)
        if not accent_color_str:
            accent_color_str = "#38bdf8" if is_dark else "#0284c7"

        needle_color = QColor(accent_color_str)

        # 1. Halo / silueta oscura para contraste en modo oscuro o clara en modo claro
        halo_color = QColor(0, 0, 0, 160) if is_dark else QColor(255, 255, 255, 220)
        halo_pen = QPen(halo_color, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(halo_pen)
        painter.drawLine(QPointF(needle_x, top_y), QPointF(needle_x, bottom_y))

        # 2. Resplandor tenue (glow)
        glow_alpha = 60 if is_dark else 40
        glow_color = QColor(needle_color.red(), needle_color.green(), needle_color.blue(), glow_alpha)
        glow_pen = QPen(glow_color, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(glow_pen)
        painter.drawLine(QPointF(needle_x, top_y), QPointF(needle_x, bottom_y))

        # 3. Línea central de la aguja (2px, nítida)
        needle_pen = QPen(needle_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(needle_pen)
        painter.drawLine(QPointF(needle_x, top_y), QPointF(needle_x, bottom_y))

        # 4. Cabezal indicador superior (pequeño marcador triangular apuntando hacia abajo)
        head_width = 8.0
        head_height = 5.0
        head_top = max(0.0, top_y - 2.0)
        triangle = QPolygonF([
            QPointF(needle_x - head_width / 2.0, head_top),
            QPointF(needle_x + head_width / 2.0, head_top),
            QPointF(needle_x, head_top + head_height),
        ])
        painter.setBrush(QBrush(needle_color))
        painter.setPen(QPen(halo_color, 1.0))
        painter.drawPolygon(triangle)

        # 5. Pequeño punto terminador inferior
        painter.setBrush(QBrush(needle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(needle_x, bottom_y), 1.5, 1.5)

        painter.end()


class _ActivityTrackWidget(QWidget):
    """Contenedor de las 24 celdas horarias con overlay de aguja temporal."""

    def __init__(self, strip: TodayActivityStripWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strip = strip
        self.setObjectName("activityTrackContainer")
        self.needle_overlay = _TimelineNeedleOverlay(strip, self)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.needle_overlay.setGeometry(0, 0, event.size().width(), event.size().height())
        self.needle_overlay.raise_()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.needle_overlay.setGeometry(0, 0, self.width(), self.height())
        self.needle_overlay.raise_()
        self.needle_overlay.update()


class TodayActivityStripWidget(QFrame):
    """Componente gráfico que exhibe el heatmap de 24 horas del día de hoy y su aguja temporal."""

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityStripCard")
        self._is_dark_mode = is_dark_mode
        self._show_needle = True
        self._reference_time: datetime | None = None
        self._current_hour_color = "#38bdf8" if is_dark_mode else "#0284c7"
        self._buckets: list[dict[str, Any]] = []
        self._cells: list[QFrame] = []
        self._last_minute_str = ""
        self._last_hour = -1

        self._build_ui()

        # Temporizador periódico de actualización de la aguja y hora (1 segundo)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    @property
    def is_dark_mode(self) -> bool:
        return self._is_dark_mode

    @is_dark_mode.setter
    def is_dark_mode(self, value: bool) -> None:
        self._is_dark_mode = bool(value)
        self._apply_theme()

    @property
    def show_needle(self) -> bool:
        """Determina si la aguja vertical indicadora de tiempo se visualiza."""
        return self._show_needle

    @show_needle.setter
    def show_needle(self, value: bool) -> None:
        self._show_needle = bool(value)
        self.refresh_needle()

    @property
    def current_time(self) -> datetime:
        """Retorna la hora actual del sistema o la hora de referencia configurada."""
        return self._reference_time or datetime.now()

    def set_reference_time(self, dt: datetime | None) -> None:
        """Establece una hora de referencia (útil para pruebas y simulaciones)."""
        self._reference_time = dt
        self._update_now_label()
        self.refresh_needle()

    @property
    def needle_progress(self) -> float:
        """Retorna la fracción del día transcurrida [0.0, 1.0]."""
        now = self.current_time
        seconds_today = (
            now.hour * 3600.0
            + now.minute * 60.0
            + now.second
            + now.microsecond / 1_000_000.0
        )
        return max(0.0, min(1.0, seconds_today / 86400.0))

    def get_needle_x(self) -> float:
        """Retorna la coordenada X actual de la aguja respecto al contenedor de celdas."""
        if hasattr(self, "track_container") and hasattr(self.track_container, "needle_overlay"):
            return self.track_container.needle_overlay.calculate_needle_x()
        return 0.0

    def refresh_needle(self) -> None:
        """Fuerza la actualización gráfica de la aguja en el overlay."""
        if hasattr(self, "track_container") and hasattr(self.track_container, "needle_overlay"):
            self.track_container.needle_overlay.update()

    def _on_tick(self) -> None:
        """Callback periódico del temporizador interno para mover la aguja."""
        if not self.isVisible() and self.parentWidget() is not None:
            return

        now = self.current_time
        current_minute_str = now.strftime("%H:%M")
        if self._last_minute_str != current_minute_str:
            self._last_minute_str = current_minute_str
            self._update_now_label()

        if self._last_hour != now.hour:
            self._last_hour = now.hour
            self._apply_theme()

        self.refresh_needle()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Fila de Cabecera: Título e indicador de hora actual
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.title_label = QLabel("ACTIVIDAD DE HOY")
        self.title_label.setObjectName("eyebrow")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.now_label = QLabel()
        self.now_label.setObjectName("activity_strip_now")
        header_layout.addWidget(self.now_label)

        layout.addLayout(header_layout)

        # Fila de Celdas (24 bloques) alojados en el track container con aguja superpuesta
        self.track_container = _ActivityTrackWidget(self, parent=self)
        self.cells_layout = QHBoxLayout(self.track_container)
        self.cells_layout.setContentsMargins(0, 2, 0, 2)
        self.cells_layout.setSpacing(3)

        self._cells = []
        for h in range(24):
            cell = QFrame()
            cell.setObjectName(f"activity_cell_{h}")
            cell.setFixedHeight(18)
            cell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cell.setToolTip(f"{h:02d}:00 – {h+1:02d}:00: Sin actividad")
            self.cells_layout.addWidget(cell)
            self._cells.append(cell)

        layout.addWidget(self.track_container)

        # Fila de Marcas de Tiempo Inferiores (00:00, 06:00, 12:00, 18:00, 23:00)
        marks_layout = QHBoxLayout()
        marks_layout.setContentsMargins(0, 0, 0, 0)
        marks = ["00:00", "06:00", "12:00", "18:00", "23:00"]
        for i, mark in enumerate(marks):
            mark_lbl = QLabel(mark)
            mark_lbl.setObjectName("activity_mark_label")
            if i == 0:
                mark_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
                marks_layout.addWidget(mark_lbl)
            elif i == len(marks) - 1:
                marks_layout.addStretch()
                mark_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                marks_layout.addWidget(mark_lbl)
            else:
                marks_layout.addStretch()
                mark_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                marks_layout.addWidget(mark_lbl)

        layout.addLayout(marks_layout)

        self._update_now_label()
        self._apply_theme()

    def _update_now_label(self) -> None:
        now_str = self.current_time.strftime("%H:%M")
        self.now_label.setText(f"HORA ACTUAL: {now_str}")

    def update_buckets(self, buckets: list[dict[str, Any]]) -> None:
        """Actualiza los datos de las 24 celdas y refresca la interfaz."""
        self._buckets = buckets
        self._update_now_label()
        self._apply_theme()

    def _apply_theme(self) -> None:
        is_dark = self._is_dark_mode

        # Paleta de colores para niveles 0 a 4
        if is_dark:
            bg_card = "#18181b"  # zinc-900
            border_card = "#27272a"
            now_color = "#94a3b8"
            mark_color = "#64748b"

            level_colors = {
                0: {"bg": "#27272a", "border": "#3f3f46"},
                1: {"bg": "#064e3b", "border": "#065f46"},
                2: {"bg": "#047857", "border": "#059669"},
                3: {"bg": "#059669", "border": "#10b981"},
                4: {"bg": "#10b981", "border": "#34d399"},
            }
            current_hour_border = "#38bdf8"  # halo celeste
        else:
            bg_card = "#ffffff"
            border_card = "#e2e8f0"
            now_color = "#64748b"
            mark_color = "#94a3b8"

            level_colors = {
                0: {"bg": "#f1f5f9", "border": "#e2e8f0"},
                1: {"bg": "#a7f3d0", "border": "#6ee7b7"},
                2: {"bg": "#6ee7b7", "border": "#34d399"},
                3: {"bg": "#34d399", "border": "#10b981"},
                4: {"bg": "#10b981", "border": "#059669"},
            }
            current_hour_border = "#0284c7"  # halo azul cielo

        self._current_hour_color = current_hour_border

        self.setStyleSheet(
            f"""
            QFrame#activityStripCard {{
                background: {bg_card};
                border: 1px solid {border_card};
                border-radius: 12px;
            }}
            QLabel#activity_strip_now {{
                color: {now_color};
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
            QLabel#activity_mark_label {{
                color: {mark_color};
                font-size: 9px;
                font-weight: 700;
                font-family: 'Consolas', monospace;
            }}
            """
        )

        bucket_map = {b["hour"]: b for b in self._buckets} if self._buckets else {}
        now_h = self.current_time.hour

        for h, cell in enumerate(self._cells):
            b = bucket_map.get(h)
            level = b["intensity_level"] if b else 0
            is_current = (b.get("is_current_hour", False) if b else (h == now_h))
            palette = level_colors.get(level, level_colors[0])

            bg = palette["bg"]
            border = current_hour_border if is_current else palette["border"]
            border_width = 2 if is_current else 1

            cell.setStyleSheet(
                f"""
                QFrame#activity_cell_{h} {{
                    background-color: {bg};
                    border: {border_width}px solid {border};
                    border-radius: 4px;
                }}
                """
            )

            # Tooltip
            next_h = (h + 1) % 24
            if b and b.get("exercise_time_ms", 0) > 0:
                t_str = format_hh_mm_ss(b["exercise_time_ms"])
                att = b.get("attempts_count", 0)
                att_str = f"{att} {'intento' if att == 1 else 'intentos'}"
                current_tag = " [HORA ACTUAL]" if is_current else ""
                cell.setToolTip(f"{h:02d}:00 – {next_h:02d}:00{current_tag}\n⏱️ {t_str} netos\n⚡ {att_str}")
            else:
                current_tag = " [HORA ACTUAL]" if is_current else ""
                cell.setToolTip(f"{h:02d}:00 – {next_h:02d}:00{current_tag}\nSin actividad de estudio")

        self.refresh_needle()
