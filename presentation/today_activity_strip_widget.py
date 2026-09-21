"""Widget del Activity Strip de 24 horas para el Home (TASK-014).

Renderiza una franja horizontal compacta con 24 celdas correspondientes a las horas
del día (00 a 23 hs), mostrando intensidad de estudio, hora actual y tooltips detallados.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from presentation.presentation_formatters import format_hh_mm_ss


class TodayActivityStripWidget(QFrame):
    """Componente gráfico que exhibe el heatmap de 24 horas del día de hoy."""

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityStripCard")
        self._is_dark_mode = is_dark_mode
        self._buckets: list[dict[str, Any]] = []
        self._cells: list[QFrame] = []

        self._build_ui()

    @property
    def is_dark_mode(self) -> bool:
        return self._is_dark_mode

    @is_dark_mode.setter
    def is_dark_mode(self, value: bool) -> None:
        self._is_dark_mode = bool(value)
        self._apply_theme()

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

        # Fila de Celdas (24 bloques)
        self.cells_layout = QHBoxLayout()
        self.cells_layout.setContentsMargins(0, 0, 0, 0)
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

        layout.addLayout(self.cells_layout)

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
        now_str = datetime.now().strftime("%H:%M")
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
        now_h = datetime.now().hour

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
