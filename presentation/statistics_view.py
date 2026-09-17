"""Vista de Estadísticas y Gráficos de Study Timetrial."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.application_service import StudyApplicationService
from application.planner_service import ExerciseNodeStatus
from application.statistics_service import TopEffortExercise
from presentation.course_heatmap_widget import CourseHeatmapWidget
from presentation.hourly_chart_widget import Hourly24hChartWidget
from presentation.planner_dialogs import ExerciseDetailPopup
from presentation.presentation_formatters import format_hh_mm
from presentation.weekly_chart_widget import WeeklyChartWidget


class StatisticsViewWidget(QWidget):
    """Vista con indicadores cuantitativos, proporciones, mapa de cursada y gráficos avanzados."""

    request_load_timer = Signal(str, int, int, object)  # (section_type, section_number, exercise, inciso)
    request_configure_schedule = Signal()

    def __init__(
        self,
        application: StudyApplicationService,
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.application = application
        self._is_dark_mode = is_dark_mode
        self._top_effort_data: list[TopEffortExercise] = []

        self._build_ui()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark
        self.weekly_chart.set_dark_mode(is_dark)
        self.course_heatmap.set_dark_mode(is_dark)
        self.hourly_chart.set_dark_mode(is_dark)

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

        # Encabezado general
        heading = QHBoxLayout()
        title = QLabel("Estadísticas")
        title.setObjectName("brand")
        heading.addWidget(title)
        heading.addStretch()
        self.stats_source_label = QLabel("REGISTRO ACTIVO")
        self.stats_source_label.setObjectName("record_meta")
        heading.addWidget(self.stats_source_label)
        layout.addLayout(heading)

        # -------------------------------------------------------------
        # Hero Card: Alternador entre Cronograma de Cursada y 7 Días
        # -------------------------------------------------------------
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(14)

        hero_top = QHBoxLayout()
        hero_title = QLabel("CALENDARIO Y HÁBITOS DE ESTUDIO")
        hero_title.setObjectName("eyebrow")
        hero_top.addWidget(hero_title)
        hero_top.addStretch()

        # Botones de alternancia de vista
        toggle_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #f8fafc;
            }
            QPushButton:checked {
                background-color: #065f46;
                border-color: #059669;
                color: #ecfdf5;
                font-weight: 700;
            }
        """

        self.btn_view_heatmap = QPushButton("📅 Cronograma de Cursada")
        self.btn_view_heatmap.setCheckable(True)
        self.btn_view_heatmap.setChecked(True)
        self.btn_view_heatmap.setStyleSheet(toggle_style)
        self.btn_view_heatmap.clicked.connect(self._show_heatmap_view)
        hero_top.addWidget(self.btn_view_heatmap)

        self.btn_view_weekly = QPushButton("📊 Últimos 7 Días")
        self.btn_view_weekly.setCheckable(True)
        self.btn_view_weekly.setChecked(False)
        self.btn_view_weekly.setStyleSheet(toggle_style)
        self.btn_view_weekly.clicked.connect(self._show_weekly_view)
        hero_top.addWidget(self.btn_view_weekly)

        hero_layout.addLayout(hero_top)

        self.hero_stack = QStackedWidget()

        # Página 0: Mapa de calor del cronograma de cursada
        self.course_heatmap = CourseHeatmapWidget(is_dark_mode=self._is_dark_mode)
        self.course_heatmap.request_configure_schedule.connect(self.request_configure_schedule.emit)
        self.hero_stack.addWidget(self.course_heatmap)

        # Página 1: Gráfico semanal clásico de 7 días
        self.weekly_chart = WeeklyChartWidget()
        self.weekly_chart.set_dark_mode(self._is_dark_mode)
        self.hero_stack.addWidget(self.weekly_chart)

        hero_layout.addWidget(self.hero_stack)
        layout.addWidget(hero)

        # -------------------------------------------------------------
        # Cuadrícula Bento de Métricas Principales
        # -------------------------------------------------------------
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

        # -------------------------------------------------------------
        # Fila Intermedia: Desglose por Sección y Proporción / Actividad
        # -------------------------------------------------------------
        mid_row = QHBoxLayout()
        mid_row.setSpacing(14)

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
        mid_row.addWidget(sec_card, 3)

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

        mid_row.addWidget(dist_card, 2)
        layout.addLayout(mid_row)

        # -------------------------------------------------------------
        # Fila Avanzada: Ranking Top 5 Esfuerzo + Histograma 24 Horas
        # -------------------------------------------------------------
        adv_row = QHBoxLayout()
        adv_row.setSpacing(14)

        # Card de Ranking Top 5
        effort_card = QFrame()
        effort_card.setObjectName("sectionCard")
        effort_layout = QVBoxLayout(effort_card)
        effort_layout.setContentsMargins(20, 16, 20, 16)
        effort_layout.setSpacing(8)

        effort_top = QHBoxLayout()
        effort_title = QLabel("TOP 5 EJERCICIOS DE MAYOR ESFUERZO")
        effort_title.setObjectName("eyebrow")
        effort_top.addWidget(effort_title)
        effort_top.addStretch()
        effort_hint = QLabel("Por tiempo neto acumulado")
        effort_hint.setObjectName("status")
        effort_top.addWidget(effort_hint)
        effort_layout.addLayout(effort_top)

        self.stats_effort_table = QTableWidget(0, 5)
        self.stats_effort_table.setHorizontalHeaderLabels([
            "#",
            "Ejercicio",
            "Tiempo Neto",
            "Intentos",
            "Acción",
        ])
        self.stats_effort_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.stats_effort_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.stats_effort_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.stats_effort_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.stats_effort_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.stats_effort_table.setAlternatingRowColors(True)
        self.stats_effort_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.stats_effort_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_effort_table.verticalHeader().setVisible(False)
        self.stats_effort_table.setMinimumHeight(150)
        self.stats_effort_table.cellDoubleClicked.connect(self._on_effort_cell_double_clicked)
        effort_layout.addWidget(self.stats_effort_table)

        adv_row.addWidget(effort_card, 3)

        # Card de Distribución 24 Horas
        hourly_card = QFrame()
        hourly_card.setObjectName("sectionCard")
        hourly_layout = QVBoxLayout(hourly_card)
        hourly_layout.setContentsMargins(20, 16, 20, 16)
        hourly_layout.setSpacing(8)

        hourly_top = QHBoxLayout()
        hourly_title = QLabel("DISTRIBUCIÓN DE ACTIVIDAD 24 HORAS")
        hourly_title.setObjectName("eyebrow")
        hourly_top.addWidget(hourly_title)
        hourly_top.addStretch()
        hourly_hint = QLabel("Franja horaria (00h a 23h)")
        hourly_hint.setObjectName("status")
        hourly_top.addWidget(hourly_hint)
        hourly_layout.addLayout(hourly_top)

        self.hourly_chart = Hourly24hChartWidget(is_dark_mode=self._is_dark_mode)
        hourly_layout.addWidget(self.hourly_chart)

        adv_row.addWidget(hourly_card, 2)
        layout.addLayout(adv_row)

        scroll.setWidget(container)
        page_layout.addWidget(scroll)

    def _show_heatmap_view(self) -> None:
        self.hero_stack.setCurrentIndex(0)
        self.btn_view_heatmap.setChecked(True)
        self.btn_view_weekly.setChecked(False)

    def _show_weekly_view(self) -> None:
        self.hero_stack.setCurrentIndex(1)
        self.btn_view_heatmap.setChecked(False)
        self.btn_view_weekly.setChecked(True)

    def refresh_statistics(self) -> None:
        stats = self.application.get_statistics()

        file_name = self.application.record_path.stem if self.application.is_record_open and self.application.record_path else self.application.record.record_name
        self.stats_source_label.setText(f"FUENTE: {file_name.upper()}  ·  {stats.total_attempts} INTENTOS")

        self.weekly_chart.set_stats(stats.daily_stats)

        # Mapa de cursada
        heatmap_data = self.application.get_course_heatmap_data()
        self.course_heatmap.set_data(heatmap_data)

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

        # Tabla de secciones
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

        # Tabla Top 5 Esfuerzo
        top_effort = self.application.get_top_effort_exercises(5)
        self._top_effort_data = top_effort
        self._render_top_effort_table(top_effort)

        # Histograma 24 horas
        hourly_dist = self.application.get_24h_hourly_distribution()
        self.hourly_chart.set_data(hourly_dist)

    def _render_top_effort_table(self, top_effort: list[TopEffortExercise]) -> None:
        self.stats_effort_table.setRowCount(0)
        if not top_effort:
            self.stats_effort_table.setRowCount(1)
            empty_item = QTableWidgetItem("Aún no hay ejercicios con tiempo registrado")
            empty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.stats_effort_table.setItem(0, 1, empty_item)
            return

        medals = ["🥇 1", "🥈 2", "🥉 3", "4", "5"]

        for row, item in enumerate(top_effort):
            self.stats_effort_table.insertRow(row)

            # Col 0: Ranking
            rank_str = medals[row] if row < len(medals) else str(row + 1)
            rank_item = QTableWidgetItem(rank_str)
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_effort_table.setItem(row, 0, rank_item)

            # Col 1: Ejercicio con estado
            state_icon = "✓ " if item.status == "completed" else ("⚠️ " if item.status == "failed" else "⏳ ")
            name_item = QTableWidgetItem(f"{state_icon}{item.display_label}")
            self.stats_effort_table.setItem(row, 1, name_item)

            # Col 2: Tiempo neto
            time_item = QTableWidgetItem(format_hh_mm(item.exercise_time_ms))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_effort_table.setItem(row, 2, time_item)

            # Col 3: Intentos
            att_str = f"{item.attempts} int."
            att_item = QTableWidgetItem(att_str)
            att_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.stats_effort_table.setItem(row, 3, att_item)

            # Col 4: Botón Detalle
            btn = QPushButton("Detalle")
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #1e293b;
                    color: #93c5fd;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #273549;
                    border-color: #60a5fa;
                    color: #ffffff;
                }
                """
            )
            btn.clicked.connect(lambda _, it=item: self._on_effort_detail_clicked(it))
            self.stats_effort_table.setCellWidget(row, 4, btn)

    def _on_effort_cell_double_clicked(self, row: int, _col: int) -> None:
        if 0 <= row < len(self._top_effort_data):
            self._on_effort_detail_clicked(self._top_effort_data[row])

    def _on_effort_detail_clicked(self, item: TopEffortExercise) -> None:
        node = self._find_or_create_node(item)
        popup = ExerciseDetailPopup(self, node, app_service=self.application, is_dark=self._is_dark_mode)
        if popup.exec() == ExerciseDetailPopup.DialogCode.Accepted:
            if popup.chosen_action == "load_timer":
                self.request_load_timer.emit(
                    node.section_type,
                    node.section_number,
                    node.exercise,
                    node.inciso,
                )
        self.refresh_statistics()

    def _find_or_create_node(self, item: TopEffortExercise) -> ExerciseNodeStatus:
        """Busca el ExerciseNodeStatus en el árbol planificado si existe, o construye uno consistente."""
        if self.application.record.planned_sections:
            overview = self.application.planner_service.build_overview(self.application.record)
            for sec_status in overview.sections:
                if (
                    sec_status.section.section_type.strip().lower() == item.section_type.strip().lower()
                    and sec_status.section.section_number == item.section_number
                ):
                    for n in sec_status.exercise_nodes:
                        if n.exercise == item.exercise:
                            if item.inciso is not None:
                                for sub in n.incisos:
                                    if sub.inciso == item.inciso:
                                        return sub
                            else:
                                return n

        # Si no está planificado formalmente o es un ejercicio libre
        return ExerciseNodeStatus(
            section_type=item.section_type,
            section_number=item.section_number,
            exercise=item.exercise,
            inciso=item.inciso,
            status=item.status,
            attempts=item.attempts,
            exercise_time_ms=item.exercise_time_ms,
            break_time_ms=item.break_time_ms,
        )
