"""Vista de Estadísticas y Gráficos de Study Timetrial."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.application_service import StudyApplicationService
from presentation.presentation_formatters import format_hh_mm
from presentation.weekly_chart_widget import WeeklyChartWidget


class StatisticsViewWidget(QWidget):
    """Vista con indicadores cuantitativos, proporciones y gráfico semanal."""

    def __init__(
        self,
        application: StudyApplicationService,
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.application = application
        self._is_dark_mode = is_dark_mode

        self._build_ui()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark
        self.weekly_chart.set_dark_mode(is_dark)

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("statsScroll")

        container = QWidget()
        container.setObjectName("statsContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(42, 28, 42, 36)
        layout.setSpacing(18)

        heading = QHBoxLayout()
        title = QLabel("Estadísticas")
        title.setObjectName("brand")
        heading.addWidget(title)
        heading.addStretch()
        self.stats_source_label = QLabel("REGISTRO ACTIVO")
        self.stats_source_label.setObjectName("record_meta")
        heading.addWidget(self.stats_source_label)
        layout.addLayout(heading)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(12)

        hero_top = QHBoxLayout()
        hero_title = QLabel("HORAS AL DÍA · FORMATO SEMANAL")
        hero_title.setObjectName("eyebrow")
        hero_top.addWidget(hero_title)
        hero_top.addStretch()
        hero_hint = QLabel("Últimos 7 días · Un día nuevo pisa el último")
        hero_hint.setObjectName("status")
        hero_top.addWidget(hero_hint)
        hero_layout.addLayout(hero_top)

        self.weekly_chart = WeeklyChartWidget()
        self.weekly_chart.set_dark_mode(self._is_dark_mode)
        hero_layout.addWidget(self.weekly_chart)
        layout.addWidget(hero)

        metrics_grid = QGridLayout()
        metrics_grid.setHorizontalSpacing(14)
        metrics_grid.setVerticalSpacing(14)

        card_total = QFrame()
        card_total.setObjectName("metricCard")
        card_total_layout = QVBoxLayout(card_total)
        card_total_layout.setContentsMargins(20, 16, 20, 16)
        card_total_layout.setSpacing(4)
        lbl_tot = QLabel("TIEMPO TOTAL DE EJERCICIOS")
        lbl_tot.setObjectName("eyebrow")
        self.stat_total_exercise = QLabel("00:00")
        self.stat_total_exercise.setObjectName("stat_hero_value")
        lbl_break_tot = QLabel("TIEMPO TOTAL DE RECESO")
        lbl_break_tot.setObjectName("eyebrow")
        self.stat_total_break = QLabel("00:00")
        self.stat_total_break.setObjectName("stat_sub_value")
        card_total_layout.addWidget(lbl_tot)
        card_total_layout.addWidget(self.stat_total_exercise)
        card_total_layout.addWidget(lbl_break_tot)
        card_total_layout.addWidget(self.stat_total_break)
        metrics_grid.addWidget(card_total, 0, 0)

        card_avg = QFrame()
        card_avg.setObjectName("metricCard")
        card_avg_layout = QVBoxLayout(card_avg)
        card_avg_layout.setContentsMargins(20, 16, 20, 16)
        card_avg_layout.setSpacing(4)
        lbl_avg = QLabel("TIEMPO PROMEDIO DE EJERCICIOS")
        lbl_avg.setObjectName("eyebrow")
        self.stat_avg_exercise = QLabel("00:00")
        self.stat_avg_exercise.setObjectName("stat_hero_value")
        lbl_break_avg = QLabel("TIEMPO PROMEDIO DE RECESO")
        lbl_break_avg.setObjectName("eyebrow")
        self.stat_avg_break = QLabel("00:00")
        self.stat_avg_break.setObjectName("stat_sub_value")
        card_avg_layout.addWidget(lbl_avg)
        card_avg_layout.addWidget(self.stat_avg_exercise)
        card_avg_layout.addWidget(lbl_break_avg)
        card_avg_layout.addWidget(self.stat_avg_break)
        metrics_grid.addWidget(card_avg, 0, 1)

        card_longest = QFrame()
        card_longest.setObjectName("metricCard")
        card_longest_layout = QVBoxLayout(card_longest)
        card_longest_layout.setContentsMargins(20, 16, 20, 16)
        card_longest_layout.setSpacing(4)
        lbl_longest = QLabel("TIEMPO MÁS LARGO DE EJERCICIO")
        lbl_longest.setObjectName("eyebrow")
        self.stat_longest_time = QLabel("00:00")
        self.stat_longest_time.setObjectName("stat_hero_value")
        lbl_longest_sub = QLabel("EJERCICIO")
        lbl_longest_sub.setObjectName("eyebrow")
        self.stat_longest_name = QLabel("Ninguno")
        self.stat_longest_name.setObjectName("stat_sub_text")
        self.stat_longest_name.setWordWrap(True)
        card_longest_layout.addWidget(lbl_longest)
        card_longest_layout.addWidget(self.stat_longest_time)
        card_longest_layout.addWidget(lbl_longest_sub)
        card_longest_layout.addWidget(self.stat_longest_name)
        metrics_grid.addWidget(card_longest, 1, 0)

        card_comp = QFrame()
        card_comp.setObjectName("metricCard")
        card_comp_layout = QVBoxLayout(card_comp)
        card_comp_layout.setContentsMargins(20, 16, 20, 16)
        card_comp_layout.setSpacing(6)
        lbl_comp = QLabel("EJERCICIOS COMPLETADOS")
        lbl_comp.setObjectName("eyebrow")
        self.stat_completed_count = QLabel("0 / 0")
        self.stat_completed_count.setObjectName("stat_hero_value")
        self.stat_progress_bar = QProgressBar()
        self.stat_progress_bar.setRange(0, 100)
        self.stat_progress_bar.setValue(0)
        self.stat_completed_note = QLabel("0% de ejercicios únicos completados")
        self.stat_completed_note.setObjectName("status")
        self.stat_completed_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_comp_layout.addWidget(lbl_comp)
        card_comp_layout.addWidget(self.stat_completed_count)
        card_comp_layout.addWidget(self.stat_progress_bar)
        card_comp_layout.addWidget(self.stat_completed_note)
        metrics_grid.addWidget(card_comp, 1, 1)

        layout.addLayout(metrics_grid)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        sec_card = QFrame()
        sec_card.setObjectName("sectionCard")
        sec_layout = QVBoxLayout(sec_card)
        sec_layout.setContentsMargins(20, 16, 20, 16)
        sec_layout.setSpacing(10)
        sec_title = QLabel("DESGLOSE POR SECCIÓN")
        sec_title.setObjectName("eyebrow")
        sec_layout.addWidget(sec_title)

        self.stats_section_table = QTableWidget(0, 5)
        self.stats_section_table.setHorizontalHeaderLabels([
            "Sección",
            "T. Ejercicio",
            "T. Receso",
            "Completados",
            "Intentos",
        ])
        self.stats_section_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_section_table.setAlternatingRowColors(True)
        self.stats_section_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stats_section_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_section_table.verticalHeader().setVisible(False)
        self.stats_section_table.setMinimumHeight(140)
        sec_layout.addWidget(self.stats_section_table)
        bottom_row.addWidget(sec_card, 3)

        dist_card = QFrame()
        dist_card.setObjectName("sectionCard")
        dist_layout = QVBoxLayout(dist_card)
        dist_layout.setContentsMargins(20, 16, 20, 16)
        dist_layout.setSpacing(10)
        dist_title = QLabel("PROPORCIÓN ESTUDIO / RECESO")
        dist_title.setObjectName("eyebrow")
        dist_layout.addWidget(dist_title)

        self.stat_distribution_bar = QProgressBar()
        self.stat_distribution_bar.setRange(0, 100)
        self.stat_distribution_bar.setValue(0)
        self.stat_distribution_bar.setFormat("Estudio %p%")
        dist_layout.addWidget(self.stat_distribution_bar)

        self.stat_dist_label = QLabel("Estudio: 00:00 (0%) · Receso: 00:00 (0%)")
        self.stat_dist_label.setObjectName("status")
        dist_layout.addWidget(self.stat_dist_label)

        dist_layout.addSpacing(6)
        att_title = QLabel("ACTIVIDAD GENERAL")
        att_title.setObjectName("eyebrow")
        dist_layout.addWidget(att_title)

        self.stat_activity_label = QLabel("0 intentos registrados en total")
        self.stat_activity_label.setObjectName("status")
        dist_layout.addWidget(self.stat_activity_label)
        dist_layout.addStretch()

        bottom_row.addWidget(dist_card, 2)
        layout.addLayout(bottom_row)

        scroll.setWidget(container)
        page_layout.addWidget(scroll)

    def refresh_statistics(self) -> None:
        stats = self.application.get_statistics()

        file_name = self.application.record_path.stem if self.application.is_record_open and self.application.record_path else self.application.record.record_name
        self.stats_source_label.setText(f"FUENTE: {file_name.upper()}  ·  {stats.total_attempts} INTENTOS")

        self.weekly_chart.set_stats(stats.daily_stats)

        self.stat_total_exercise.setText(format_hh_mm(stats.total_exercise_time_ms))
        self.stat_total_break.setText(format_hh_mm(stats.total_break_time_ms))
        self.stat_avg_exercise.setText(format_hh_mm(stats.avg_exercise_time_ms))
        self.stat_avg_break.setText(format_hh_mm(stats.avg_break_time_ms))

        self.stat_longest_time.setText(format_hh_mm(stats.longest_exercise_time_ms))
        self.stat_longest_name.setText(stats.longest_exercise_name)

        if stats.has_planner and stats.planned_total_units > 0:
            comp_display = stats.planned_completed_display
            self.stat_completed_count.setText(f"{comp_display} / {stats.planned_total_units}")
            pct_int = int(round(stats.planned_completion_percentage))
            self.stat_progress_bar.setValue(pct_int)
            self.stat_completed_note.setText(
                f"{pct_int}% completado del universo planificado ({comp_display} de {stats.planned_total_units} ejercicios)"
            )
        else:
            self.stat_completed_count.setText(f"{stats.completed_unique_exercises} / {stats.total_unique_exercises}")
            pct_int = int(round(stats.completion_percentage))
            self.stat_progress_bar.setValue(pct_int)
            self.stat_completed_note.setText(
                f"{pct_int}% de ejercicios únicos completados ({stats.completed_unique_exercises} de {stats.total_unique_exercises})"
            )

        ex_pct = int(round(stats.exercise_ratio_percentage))
        br_pct = int(round(stats.break_ratio_percentage))
        self.stat_distribution_bar.setValue(ex_pct)
        self.stat_dist_label.setText(
            f"Estudio: {format_hh_mm(stats.total_exercise_time_ms)} ({ex_pct}%)  ·  Receso: {format_hh_mm(stats.total_break_time_ms)} ({br_pct}%)"
        )
        success_pct = int(round((stats.completed_attempts / stats.total_attempts * 100.0))) if stats.total_attempts else 0
        self.stat_activity_label.setText(
            f"{stats.total_attempts} intentos totales ({stats.completed_attempts} completos · {success_pct}% efectividad)"
        )

        self.stats_section_table.setRowCount(0)
        for row, sec in enumerate(stats.section_summaries):
            self.stats_section_table.insertRow(row)
            self.stats_section_table.setItem(row, 0, QTableWidgetItem(sec.section_key))
            self.stats_section_table.setItem(row, 1, QTableWidgetItem(format_hh_mm(sec.exercise_time_ms)))
            self.stats_section_table.setItem(row, 2, QTableWidgetItem(format_hh_mm(sec.break_time_ms)))
            if sec.planned_total is not None:
                comp_display = f"{sec.planned_completed_display} / {sec.planned_total} ({sec.planned_completion_pct or 0.0:.0f}%)"
            else:
                comp_display = f"{sec.completed_unique} / {sec.total_unique}"
            self.stats_section_table.setItem(row, 3, QTableWidgetItem(comp_display))
            self.stats_section_table.setItem(row, 4, QTableWidgetItem(str(sec.attempts)))
