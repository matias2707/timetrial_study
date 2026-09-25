"""Sub-pestaña General: Visión global y evolución acumulativa de la cursada."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.statistics_service import CumulativeEvolutionData, RecordStatistics, TopEffortExercise
from presentation.course_heatmap_widget import CourseHeatmapWidget
from presentation.hourly_chart_widget import Hourly24hChartWidget
from presentation.presentation_formatters import format_hh_mm
from presentation.statistics.cumulative_chart_widget import CumulativeEvolutionChartWidget


class GeneralTabWidget(QWidget):
    """Componente que proyecta la dimensión macro de la cursada y la evolución acumulada."""

    request_load_timer = Signal(str, int, int, object)  # (sec_type, sec_num, ex, inc)
    request_configure_schedule = Signal()
    request_change_sort = Signal(str)  # "time", "retries", "pb"

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_dark_mode = is_dark_mode
        self._top_effort_data: list[TopEffortExercise] = []
        self._build_ui()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark
        self.cumulative_chart.set_dark_mode(is_dark)
        self.course_heatmap.set_dark_mode(is_dark)
        self.hourly_chart.set_dark_mode(is_dark)

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 20, 32, 32)
        layout.setSpacing(20)

        # -------------------------------------------------------------
        # 1. Cuadrícula Bento de Métricas Macro
        # -------------------------------------------------------------
        bento_grid = QGridLayout()
        bento_grid.setHorizontalSpacing(14)
        bento_grid.setVerticalSpacing(14)

        # Card 1: Tiempo Total y Receso
        card_total = QFrame()
        card_total.setObjectName("metricCard")
        c1_layout = QVBoxLayout(card_total)
        c1_layout.setContentsMargins(18, 14, 18, 14)
        c1_layout.setSpacing(4)
        lbl_tot = QLabel("TIEMPO TOTAL DE ESTUDIO")
        lbl_tot.setObjectName("eyebrow")
        self.stat_total_exercise = QLabel("00:00")
        self.stat_total_exercise.setObjectName("stat_hero_value")
        lbl_break_tot = QLabel("TIEMPO TOTAL DE RECESO")
        lbl_break_tot.setObjectName("eyebrow")
        self.stat_total_break = QLabel("00:00")
        self.stat_total_break.setObjectName("stat_sub_value")
        c1_layout.addWidget(lbl_tot)
        c1_layout.addWidget(self.stat_total_exercise)
        c1_layout.addWidget(lbl_break_tot)
        c1_layout.addWidget(self.stat_total_break)
        bento_grid.addWidget(card_total, 0, 0)

        # Card 2: Promedios
        card_avg = QFrame()
        card_avg.setObjectName("metricCard")
        c2_layout = QVBoxLayout(card_avg)
        c2_layout.setContentsMargins(18, 14, 18, 14)
        c2_layout.setSpacing(4)
        lbl_avg = QLabel("TIEMPO PROMEDIO POR EJERCICIO")
        lbl_avg.setObjectName("eyebrow")
        self.stat_avg_exercise = QLabel("00:00")
        self.stat_avg_exercise.setObjectName("stat_hero_value")
        lbl_break_avg = QLabel("PROMEDIO DE RECESO")
        lbl_break_avg.setObjectName("eyebrow")
        self.stat_avg_break = QLabel("00:00")
        self.stat_avg_break.setObjectName("stat_sub_value")
        c2_layout.addWidget(lbl_avg)
        c2_layout.addWidget(self.stat_avg_exercise)
        c2_layout.addWidget(lbl_break_avg)
        c2_layout.addWidget(self.stat_avg_break)
        bento_grid.addWidget(card_avg, 0, 1)

        # Card 3: Racha y Días Estudiados
        card_streak = QFrame()
        card_streak.setObjectName("metricCard")
        c3_layout = QVBoxLayout(card_streak)
        c3_layout.setContentsMargins(18, 14, 18, 14)
        c3_layout.setSpacing(4)
        lbl_streak = QLabel("RACHA ACTUAL DE CONSTANCIA")
        lbl_streak.setObjectName("eyebrow")
        self.stat_streak_value = QLabel("0 días")
        self.stat_streak_value.setObjectName("stat_hero_value")
        lbl_study_days = QLabel("TOTAL DÍAS DE ESTUDIO")
        lbl_study_days.setObjectName("eyebrow")
        self.stat_study_days_value = QLabel("0 días activos")
        self.stat_study_days_value.setObjectName("stat_sub_value")
        c3_layout.addWidget(lbl_streak)
        c3_layout.addWidget(self.stat_streak_value)
        c3_layout.addWidget(lbl_study_days)
        c3_layout.addWidget(self.stat_study_days_value)
        bento_grid.addWidget(card_streak, 0, 2)

        # Card 4: Avance de Materia / Universo
        card_comp = QFrame()
        card_comp.setObjectName("metricCard")
        c4_layout = QVBoxLayout(card_comp)
        c4_layout.setContentsMargins(18, 14, 18, 14)
        c4_layout.setSpacing(6)
        lbl_comp = QLabel("AVANCE DEL UNIVERSO DE ESTUDIO")
        lbl_comp.setObjectName("eyebrow")
        self.stat_completed_count = QLabel("0 / 0")
        self.stat_completed_count.setObjectName("stat_hero_value")
        self.stat_progress_bar = QProgressBar()
        self.stat_progress_bar.setRange(0, 100)
        self.stat_progress_bar.setValue(0)
        self.stat_completed_note = QLabel("0% del universo planificado")
        self.stat_completed_note.setObjectName("status")
        c4_layout.addWidget(lbl_comp)
        c4_layout.addWidget(self.stat_completed_count)
        c4_layout.addWidget(self.stat_progress_bar)
        c4_layout.addWidget(self.stat_completed_note)
        bento_grid.addWidget(card_comp, 1, 0)

        # Card 5: Ejercicio Más Exigente
        card_longest = QFrame()
        card_longest.setObjectName("metricCard")
        c5_layout = QVBoxLayout(card_longest)
        c5_layout.setContentsMargins(18, 14, 18, 14)
        c5_layout.setSpacing(4)
        lbl_longest = QLabel("EJERCICIO DE MAYOR ESFUERZO")
        lbl_longest.setObjectName("eyebrow")
        self.stat_longest_time = QLabel("00:00")
        self.stat_longest_time.setObjectName("stat_hero_value")
        lbl_longest_sub = QLabel("UBICACIÓN")
        lbl_longest_sub.setObjectName("eyebrow")
        self.stat_longest_name = QLabel("Ninguno")
        self.stat_longest_name.setObjectName("stat_sub_text")
        self.stat_longest_name.setWordWrap(True)
        c5_layout.addWidget(lbl_longest)
        c5_layout.addWidget(self.stat_longest_time)
        c5_layout.addWidget(lbl_longest_sub)
        c5_layout.addWidget(self.stat_longest_name)
        bento_grid.addWidget(card_longest, 1, 1)

        # Card 6: Ratio de Enfoque Global
        card_ratio = QFrame()
        card_ratio.setObjectName("metricCard")
        c6_layout = QVBoxLayout(card_ratio)
        c6_layout.setContentsMargins(18, 14, 18, 14)
        c6_layout.setSpacing(6)
        lbl_ratio = QLabel("BALANCE ESTUDIO / RECESOS")
        lbl_ratio.setObjectName("eyebrow")
        self.stat_ratio_value = QLabel("0%")
        self.stat_ratio_value.setObjectName("stat_hero_value")
        self.stat_ratio_bar = QProgressBar()
        self.stat_ratio_bar.setRange(0, 100)
        self.stat_ratio_bar.setValue(0)
        self.stat_ratio_bar.setFormat("Estudio %p%")
        self.stat_ratio_note = QLabel("0 sesiones registradas en total")
        self.stat_ratio_note.setObjectName("status")
        c6_layout.addWidget(lbl_ratio)
        c6_layout.addWidget(self.stat_ratio_value)
        c6_layout.addWidget(self.stat_ratio_bar)
        c6_layout.addWidget(self.stat_ratio_note)
        bento_grid.addWidget(card_ratio, 1, 2)

        layout.addLayout(bento_grid)

        # -------------------------------------------------------------
        # 2. Gráfico de Evolución Acumulativa (Horas y Curva de Logros)
        # -------------------------------------------------------------
        evol_card = QFrame()
        evol_card.setObjectName("sectionCard")
        evol_layout = QVBoxLayout(evol_card)
        evol_layout.setContentsMargins(20, 16, 20, 18)
        evol_layout.setSpacing(10)

        evol_header = QHBoxLayout()
        evol_title = QLabel("CURVA DE APRENDIZAJE Y EVOLUCIÓN ACUMULADA")
        evol_title.setObjectName("eyebrow")
        evol_header.addWidget(evol_title)
        evol_header.addStretch()
        evol_hint = QLabel("Horas netas y progreso histórico de intentos")
        evol_hint.setObjectName("status")
        evol_header.addWidget(evol_hint)
        evol_layout.addLayout(evol_header)

        self.cumulative_chart = CumulativeEvolutionChartWidget()
        self.cumulative_chart.set_dark_mode(self._is_dark_mode)
        evol_layout.addWidget(self.cumulative_chart)
        layout.addWidget(evol_card)

        # -------------------------------------------------------------
        # 3. Cronograma de Cursada (Course Heatmap)
        # -------------------------------------------------------------
        heatmap_card = QFrame()
        heatmap_card.setObjectName("sectionCard")
        hm_layout = QVBoxLayout(heatmap_card)
        hm_layout.setContentsMargins(20, 16, 20, 18)
        hm_layout.setSpacing(10)

        hm_header = QHBoxLayout()
        hm_title = QLabel("CRONOGRAMA DE CURSADA Y CALENDARIO DE EXÁMENES")
        hm_title.setObjectName("eyebrow")
        hm_header.addWidget(hm_title)
        hm_header.addStretch()
        hm_layout.addLayout(hm_header)

        self.course_heatmap = CourseHeatmapWidget(is_dark_mode=self._is_dark_mode)
        self.course_heatmap.request_configure_schedule.connect(self.request_configure_schedule.emit)
        hm_layout.addWidget(self.course_heatmap)
        layout.addWidget(heatmap_card)

        # -------------------------------------------------------------
        # 4. Fila Doble: Desglose por Guía + Ranking Top 5 Esfuerzo
        # -------------------------------------------------------------
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

        # Desglose por Guía
        sec_card = QFrame()
        sec_card.setObjectName("sectionCard")
        sec_layout = QVBoxLayout(sec_card)
        sec_layout.setContentsMargins(20, 16, 20, 16)
        sec_layout.setSpacing(10)
        sec_title = QLabel("DESGLOSE CURRICULAR POR SECCIÓN")
        sec_title.setObjectName("eyebrow")
        sec_layout.addWidget(sec_title)

        self.section_table = QTableWidget(0, 5)
        self.section_table.setHorizontalHeaderLabels([
            "Sección",
            "T. Ejercicio",
            "T. Receso",
            "Completados",
            "Intentos",
        ])
        self.section_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.section_table.setAlternatingRowColors(True)
        self.section_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.section_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.section_table.verticalHeader().setVisible(False)
        self.section_table.setMinimumHeight(150)
        sec_layout.addWidget(self.section_table)
        mid_row.addWidget(sec_card, 3)

        # Top 5 Ejercicios de Mayor Esfuerzo
        effort_card = QFrame()
        effort_card.setObjectName("sectionCard")
        effort_layout = QVBoxLayout(effort_card)
        effort_layout.setContentsMargins(20, 16, 20, 16)
        effort_layout.setSpacing(8)

        effort_top = QHBoxLayout()
        effort_title = QLabel("TOP 5 EJERCICIOS")
        effort_title.setObjectName("eyebrow")
        effort_top.addWidget(effort_title)
        effort_top.addStretch()

        self.combo_sort = QComboBox()
        self.combo_sort.addItem("Mayor tiempo neto", "time")
        self.combo_sort.addItem("Más reintentos", "retries")
        self.combo_sort.addItem("Mejores marcas / PB", "pb")
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)
        effort_top.addWidget(self.combo_sort)
        effort_layout.addLayout(effort_top)

        self.effort_table = QTableWidget(0, 5)
        self.effort_table.setHorizontalHeaderLabels([
            "#",
            "Ejercicio",
            "Tiempo Neto",
            "Intentos",
            "Acción",
        ])
        self.effort_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.effort_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.effort_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.effort_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.effort_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.effort_table.setAlternatingRowColors(True)
        self.effort_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.effort_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.effort_table.verticalHeader().setVisible(False)
        self.effort_table.setMinimumHeight(150)
        self.effort_table.cellDoubleClicked.connect(self._on_effort_double_clicked)
        effort_layout.addWidget(self.effort_table)

        mid_row.addWidget(effort_card, 3)
        layout.addLayout(mid_row)

        # -------------------------------------------------------------
        # 5. Distribución de Actividad 24 Horas
        # -------------------------------------------------------------
        hourly_card = QFrame()
        hourly_card.setObjectName("sectionCard")
        hourly_layout = QVBoxLayout(hourly_card)
        hourly_layout.setContentsMargins(20, 16, 20, 16)
        hourly_layout.setSpacing(8)

        hourly_top = QHBoxLayout()
        hourly_title = QLabel("DISTRIBUCIÓN DE ACTIVIDAD CIRCADIANA (24 HORAS)")
        hourly_title.setObjectName("eyebrow")
        hourly_top.addWidget(hourly_title)
        hourly_top.addStretch()
        self.lbl_peak_hour = QLabel("Franja horaria (00h a 23h)")
        self.lbl_peak_hour.setObjectName("status")
        hourly_top.addWidget(self.lbl_peak_hour)
        hourly_layout.addLayout(hourly_top)

        self.hourly_chart = Hourly24hChartWidget(is_dark_mode=self._is_dark_mode)
        hourly_layout.addWidget(self.hourly_chart)
        layout.addWidget(hourly_card)

        scroll.setWidget(container)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

    def _on_sort_changed(self) -> None:
        criteria = self.combo_sort.currentData() or "time"
        self.request_change_sort.emit(criteria)

    def _on_effort_double_clicked(self, row: int, col: int) -> None:
        if 0 <= row < len(self._top_effort_data):
            ex = self._top_effort_data[row]
            self.request_load_timer.emit(ex.section_type, ex.section_number, ex.exercise, ex.inciso)

    def render_data(
        self,
        stats: RecordStatistics,
        streak_days: int,
        total_study_days: int,
        evolution_data: CumulativeEvolutionData,
        top_effort: list[TopEffortExercise],
        heatmap_data: dict[str, Any],
        hourly_data: dict[int, int],
    ) -> None:
        self.stat_total_exercise.setText(format_hh_mm(stats.total_exercise_time_ms))
        self.stat_total_break.setText(format_hh_mm(stats.total_break_time_ms))
        self.stat_avg_exercise.setText(format_hh_mm(stats.avg_exercise_time_ms))
        self.stat_avg_break.setText(format_hh_mm(stats.avg_break_time_ms))
        self.stat_longest_time.setText(format_hh_mm(stats.longest_exercise_time_ms))
        self.stat_longest_name.setText(stats.longest_exercise_name)

        # Racha y días
        self.stat_streak_value.setText(f"🔥 {streak_days} días" if streak_days > 0 else "0 días")
        self.stat_study_days_value.setText(f"{total_study_days} días activos")

        # Universo y progreso
        if stats.has_planner and stats.planned_total_units > 0:
            comp_display = stats.planned_completed_display
            self.stat_completed_count.setText(f"{comp_display} / {stats.planned_total_units}")
            pct = int(round(stats.planned_completion_percentage))
            self.stat_progress_bar.setValue(pct)
            self.stat_completed_note.setText(
                f"{pct}% del universo planificado ({comp_display} de {stats.planned_total_units} ej)"
            )
        else:
            self.stat_completed_count.setText(f"{stats.completed_unique_exercises} / {stats.total_unique_exercises}")
            pct = int(round(stats.completion_percentage))
            self.stat_progress_bar.setValue(pct)
            self.stat_completed_note.setText(f"{pct}% de ejercicios únicos completados")

        # Ratio estudio / receso
        ex_ratio = stats.exercise_ratio_percentage
        self.stat_ratio_value.setText(f"{ex_ratio:.1f}%")
        self.stat_ratio_bar.setValue(int(round(ex_ratio)))
        self.stat_ratio_note.setText(f"{stats.total_attempts} intentos registrados en total")

        # Gráfico de evolución acumulativa
        self.cumulative_chart.set_data(evolution_data)

        # Cronograma de cursada
        self.course_heatmap.set_data(heatmap_data)

        # Desglose por sección
        self.section_table.setRowCount(len(stats.section_summaries))
        for row, sec in enumerate(stats.section_summaries):
            item_sec = QTableWidgetItem(sec.section_key)
            item_ex = QTableWidgetItem(format_hh_mm(sec.exercise_time_ms))
            item_ex.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_br = QTableWidgetItem(format_hh_mm(sec.break_time_ms))
            item_br.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if sec.planned_total is not None and sec.planned_total > 0:
                comp_txt = f"{sec.planned_completed_display} / {sec.planned_total}"
            else:
                comp_txt = f"{sec.completed_unique} / {sec.total_unique}"
            item_comp = QTableWidgetItem(comp_txt)
            item_comp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_att = QTableWidgetItem(str(sec.attempts))
            item_att.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.section_table.setItem(row, 0, item_sec)
            self.section_table.setItem(row, 1, item_ex)
            self.section_table.setItem(row, 2, item_br)
            self.section_table.setItem(row, 3, item_comp)
            self.section_table.setItem(row, 4, item_att)

        # Top 5 Esfuerzo
        self._top_effort_data = top_effort
        self.effort_table.setRowCount(len(top_effort))
        for row, ex in enumerate(top_effort):
            inciso_txt = f" ({ex.inciso})" if ex.inciso else ""
            ex_display = f"{ex.section_type} {ex.section_number} · Ej {ex.exercise}{inciso_txt}"

            it_rank = QTableWidgetItem(str(ex.rank))
            it_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_name = QTableWidgetItem(ex_display)
            it_time = QTableWidgetItem(format_hh_mm(ex.exercise_time_ms))
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_att = QTableWidgetItem(str(ex.attempts))
            it_att.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.effort_table.setItem(row, 0, it_rank)
            self.effort_table.setItem(row, 1, it_name)
            self.effort_table.setItem(row, 2, it_time)
            self.effort_table.setItem(row, 3, it_att)

            btn = QPushButton("Cargar")
            btn.setProperty("small", True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, s=ex.section_type, sn=ex.section_number, e=ex.exercise, inc=ex.inciso: (
                    self.request_load_timer.emit(s, sn, e, inc)
                )
            )
            self.effort_table.setCellWidget(row, 4, btn)

        # Histograma 24h
        # Detectar hora pico
        if hourly_data:
            peak_h = max(hourly_data.keys(), key=lambda h: hourly_data[h])
            if hourly_data[peak_h] > 0:
                self.lbl_peak_hour.setText(f"Franja pico: {peak_h:02d}:00 a {(peak_h+1)%24:02d}:00")
            else:
                self.lbl_peak_hour.setText("Franja horaria (00h a 23h)")
