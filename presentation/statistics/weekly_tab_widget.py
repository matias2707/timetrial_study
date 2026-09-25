"""Sub-pestaña Semanal: Análisis de 7 días, ritmo de estudio y ejercicios de la semana."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.statistics_service import DailyStatistic, WeeklyStatsSummary
from presentation.presentation_formatters import format_hh_mm
from presentation.weekly_chart_widget import WeeklyChartWidget


class WeeklyTabWidget(QWidget):
    """Componente que proyecta la carga y hábitos semanales con navegador temporal."""

    request_navigate_week = Signal(int)  # -1 (prev), +1 (next)
    request_current_week = Signal()
    request_load_timer = Signal(str, int, int, object)  # (sec_type, sec_num, ex, inc)

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_dark_mode = is_dark_mode
        self._summary: WeeklyStatsSummary | None = None
        self._build_ui()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark
        self.weekly_chart.set_dark_mode(is_dark)

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 20, 32, 32)
        layout.setSpacing(18)

        # -------------------------------------------------------------
        # 1. Barra de Navegación de Semanas
        # -------------------------------------------------------------
        nav_card = QFrame()
        nav_card.setObjectName("sectionCard")
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(16, 12, 16, 12)
        nav_layout.setSpacing(12)

        self.btn_prev_week = QPushButton("◀ Semana Anterior")
        self.btn_prev_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_week.clicked.connect(lambda: self.request_navigate_week.emit(-1))
        nav_layout.addWidget(self.btn_prev_week)

        nav_layout.addStretch()

        self.lbl_week_range = QLabel("Semana")
        self.lbl_week_range.setObjectName("stat_hero_value")
        self.lbl_week_range.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.lbl_week_range)

        self.badge_curr_week = QLabel("SEMANA ACTUAL")
        self.badge_curr_week.setObjectName("badge_tag")
        self.badge_curr_week.setStyleSheet(
            "background-color: #065f46; color: #ecfdf5; font-weight: bold; border-radius: 4px; padding: 2px 8px;"
        )
        nav_layout.addWidget(self.badge_curr_week)

        nav_layout.addStretch()

        self.btn_this_week = QPushButton("Semana Actual")
        self.btn_this_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_this_week.clicked.connect(self.request_current_week.emit)
        nav_layout.addWidget(self.btn_this_week)

        self.btn_next_week = QPushButton("Semana Siguiente ▶")
        self.btn_next_week.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_week.clicked.connect(lambda: self.request_navigate_week.emit(1))
        nav_layout.addWidget(self.btn_next_week)

        layout.addWidget(nav_card)

        # -------------------------------------------------------------
        # 2. KPIs de la Semana
        # -------------------------------------------------------------
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(14)

        # Total semana
        card_total = QFrame()
        card_total.setObjectName("metricCard")
        c1 = QVBoxLayout(card_total)
        c1.setContentsMargins(18, 14, 18, 14)
        c1.setSpacing(4)
        l1 = QLabel("TIEMPO ESTUDIADO EN LA SEMANA")
        l1.setObjectName("eyebrow")
        self.lbl_week_exercise = QLabel("00:00")
        self.lbl_week_exercise.setObjectName("stat_hero_value")
        l1_sub = QLabel("TOTAL RECESOS EN LA SEMANA")
        l1_sub.setObjectName("eyebrow")
        self.lbl_week_break = QLabel("00:00")
        self.lbl_week_break.setObjectName("stat_sub_value")
        c1.addWidget(l1)
        c1.addWidget(self.lbl_week_exercise)
        c1.addWidget(l1_sub)
        c1.addWidget(self.lbl_week_break)
        kpi_grid.addWidget(card_total, 0, 0)

        # Días activos
        card_days = QFrame()
        card_days.setObjectName("metricCard")
        c2 = QVBoxLayout(card_days)
        c2.setContentsMargins(18, 14, 18, 14)
        c2.setSpacing(4)
        l2 = QLabel("DÍAS ACTIVOS EN LA SEMANA")
        l2.setObjectName("eyebrow")
        self.lbl_active_days = QLabel("0 / 7")
        self.lbl_active_days.setObjectName("stat_hero_value")
        l2_sub = QLabel("FRECUENCIA SEMANAL")
        l2_sub.setObjectName("eyebrow")
        self.lbl_frequency_note = QLabel("0% de la semana")
        self.lbl_frequency_note.setObjectName("status")
        c2.addWidget(l2)
        c2.addWidget(self.lbl_active_days)
        c2.addWidget(l2_sub)
        c2.addWidget(self.lbl_frequency_note)
        kpi_grid.addWidget(card_days, 0, 1)

        # Promedio por día activo
        card_avg = QFrame()
        card_avg.setObjectName("metricCard")
        c3 = QVBoxLayout(card_avg)
        c3.setContentsMargins(18, 14, 18, 14)
        c3.setSpacing(4)
        l3 = QLabel("PROMEDIO DIARIO (DÍAS ACTIVOS)")
        l3.setObjectName("eyebrow")
        self.lbl_daily_avg = QLabel("00:00")
        self.lbl_daily_avg.setObjectName("stat_hero_value")
        l3_sub = QLabel("EJERCICIOS COMPLETADOS")
        l3_sub.setObjectName("eyebrow")
        self.lbl_week_completed = QLabel("0 completados")
        self.lbl_week_completed.setObjectName("stat_sub_value")
        c3.addWidget(l3)
        c3.addWidget(self.lbl_daily_avg)
        c3.addWidget(l3_sub)
        c3.addWidget(self.lbl_week_completed)
        kpi_grid.addWidget(card_avg, 0, 2)

        layout.addLayout(kpi_grid)

        # -------------------------------------------------------------
        # 3. Gráfico Semanal Diario (WeeklyChartWidget)
        # -------------------------------------------------------------
        chart_card = QFrame()
        chart_card.setObjectName("sectionCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(20, 16, 20, 18)
        chart_layout.setSpacing(10)

        chart_head = QHBoxLayout()
        ch_title = QLabel("DISTRIBUCIÓN DIARIA DE LA SEMANA (LUNES A DOMINGO)")
        ch_title.setObjectName("eyebrow")
        chart_head.addWidget(ch_title)
        chart_head.addStretch()
        chart_layout.addLayout(chart_head)

        self.weekly_chart = WeeklyChartWidget()
        self.weekly_chart.set_dark_mode(self._is_dark_mode)
        chart_layout.addWidget(self.weekly_chart)
        layout.addWidget(chart_card)

        # -------------------------------------------------------------
        # 4. Tabla de Ejercicios Trabajados en la Semana
        # -------------------------------------------------------------
        table_card = QFrame()
        table_card.setObjectName("sectionCard")
        tbl_layout = QVBoxLayout(table_card)
        tbl_layout.setContentsMargins(20, 16, 20, 16)
        tbl_layout.setSpacing(10)

        tbl_head = QHBoxLayout()
        tbl_title = QLabel("EJERCICIOS ABORDADOS EN ESTA SEMANA")
        tbl_title.setObjectName("eyebrow")
        tbl_head.addWidget(tbl_title)
        tbl_head.addStretch()
        self.lbl_exercises_count = QLabel("0 ejercicios")
        self.lbl_exercises_count.setObjectName("status")
        tbl_head.addWidget(self.lbl_exercises_count)
        tbl_layout.addLayout(tbl_head)

        self.week_exercises_table = QTableWidget(0, 5)
        self.week_exercises_table.setHorizontalHeaderLabels([
            "Sección / Guía",
            "Ejercicio / Inciso",
            "Tiempo Neto Total",
            "Intentos",
            "Estado / Acción",
        ])
        self.week_exercises_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.week_exercises_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.week_exercises_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.week_exercises_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.week_exercises_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.week_exercises_table.setAlternatingRowColors(True)
        self.week_exercises_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.week_exercises_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.week_exercises_table.verticalHeader().setVisible(False)
        self.week_exercises_table.setMinimumHeight(160)
        self.week_exercises_table.cellDoubleClicked.connect(self._on_table_double_clicked)
        tbl_layout.addWidget(self.week_exercises_table)

        layout.addWidget(table_card)

        scroll.setWidget(container)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

    def _on_table_double_clicked(self, row: int, col: int) -> None:
        if self._summary and 0 <= row < len(self._summary.exercises):
            ex = self._summary.exercises[row]
            self.request_load_timer.emit(ex.section_type, ex.section_number, ex.exercise, ex.inciso)

    def render_data(self, summary: WeeklyStatsSummary) -> None:
        self._summary = summary

        self.lbl_week_range.setText(summary.display_range)
        self.badge_curr_week.setVisible(summary.is_current_week)
        self.lbl_week_exercise.setText(format_hh_mm(summary.total_exercise_time_ms))
        self.lbl_week_break.setText(format_hh_mm(summary.total_break_time_ms))

        self.lbl_active_days.setText(f"{summary.active_days_count} / 7 días")
        pct_days = int(round((summary.active_days_count / 7.0) * 100.0))
        self.lbl_frequency_note.setText(f"{pct_days}% de los días con estudio")

        avg_daily_ms = (
            summary.total_exercise_time_ms // summary.active_days_count
            if summary.active_days_count > 0
            else 0
        )
        self.lbl_daily_avg.setText(format_hh_mm(avg_daily_ms))
        self.lbl_week_completed.setText(
            f"{summary.completed_count} completados · {summary.failed_count} incompletos"
        )

        # Gráfico semanal
        chart_stats: list[DailyStatistic] = []
        for d in summary.days:
            from datetime import date
            try:
                dt_obj = date.fromisoformat(d.date_str)
            except Exception:
                dt_obj = date.today()
            chart_stats.append(
                DailyStatistic(
                    date=dt_obj,
                    day_name=d.day_name,
                    date_str=d.date_str[5:],  # MM-DD
                    exercise_time_ms=d.exercise_time_ms,
                    break_time_ms=d.break_time_ms,
                )
            )
        self.weekly_chart.set_stats(chart_stats)

        # Tabla de ejercicios
        ex_list = summary.exercises
        self.lbl_exercises_count.setText(f"{len(ex_list)} ejercicios trabajados")
        self.week_exercises_table.setRowCount(len(ex_list))

        for row, ex in enumerate(ex_list):
            it_sec = QTableWidgetItem(ex.section_display)
            it_sec.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            inc_txt = f" · Inciso {ex.inciso}" if ex.inciso else ""
            it_ex = QTableWidgetItem(f"Ejercicio {ex.exercise}{inc_txt}")

            it_time = QTableWidgetItem(format_hh_mm(ex.total_exercise_time_ms))
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            it_att = QTableWidgetItem(str(ex.attempts_count))
            it_att.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.week_exercises_table.setItem(row, 0, it_sec)
            self.week_exercises_table.setItem(row, 1, it_ex)
            self.week_exercises_table.setItem(row, 2, it_time)
            self.week_exercises_table.setItem(row, 3, it_att)

            status_btn = QPushButton("✓ Completado" if ex.is_completed else "Cargar")
            status_btn.setProperty("small", True)
            status_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            status_btn.clicked.connect(
                lambda checked=False, s=ex.section_type, sn=ex.section_number, e=ex.exercise, inc=ex.inciso: (
                    self.request_load_timer.emit(s, sn, e, inc)
                )
            )
            self.week_exercises_table.setCellWidget(row, 4, status_btn)
