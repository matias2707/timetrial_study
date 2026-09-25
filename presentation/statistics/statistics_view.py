"""Vista Pasiva (MVP) para la pestaña de Estadísticas y Analítica Temporal."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from application.application_service import StudyApplicationService
from application.statistics_service import (
    CumulativeEvolutionData,
    DailyStatsSummary,
    RecordStatistics,
    TopEffortExercise,
    WeeklyStatsSummary,
)
from presentation.empty_state_widget import EmptyStateWidget
from presentation.statistics.daily_tab_widget import DailyTabWidget
from presentation.statistics.general_tab_widget import GeneralTabWidget
from presentation.statistics.interfaces import IStatisticsView
from presentation.statistics.statistics_presenter import StatisticsPresenter
from presentation.statistics.weekly_tab_widget import WeeklyTabWidget


class StatisticsViewWidget(QWidget):
    """Vista modular con tres dimensiones temporales: General, Semanal y Diario."""

    request_load_timer = Signal(str, int, int, object)  # (sec_type, sec_num, ex, inc)
    request_configure_schedule = Signal()
    request_export = Signal()

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
        self.presenter = StatisticsPresenter(view=self, application=self.application)

    @property
    def course_heatmap(self):
        return self.general_tab.course_heatmap

    @property
    def weekly_chart(self):
        return self.weekly_tab.weekly_chart

    @property
    def hourly_chart(self):
        return self.general_tab.hourly_chart

    @property
    def cumulative_chart(self):
        return self.general_tab.cumulative_chart

    @property
    def stats_effort_table(self):
        return self.general_tab.effort_table

    # Compatibilidad con tests legacy
    @property
    def hero_stack(self):
        return self.subtab_stack

    @property
    def btn_view_weekly(self):
        return self.btn_tab_weekly

    @property
    def btn_view_heatmap(self):
        return self.btn_tab_general

    def _show_weekly_view(self) -> None:
        self.presenter.set_subtab(1)

    def _show_heatmap_view(self) -> None:
        self.presenter.set_subtab(0)

    def _get_tab_button_style(self, is_dark: bool) -> str:
        if is_dark:
            return """
                QPushButton {
                    background-color: transparent;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    color: #94a3b8;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #f8fafc;
                }
                QPushButton:checked {
                    background-color: #065f46;
                    border-color: #10b981;
                    color: #ecfdf5;
                    font-weight: 700;
                }
            """
        return """
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                color: #475569;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f1f5f9;
                color: #0f172a;
            }
            QPushButton:checked {
                background-color: #e7f4ec;
                border-color: #059669;
                color: #047857;
                font-weight: 700;
            }
        """

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark
        self.general_tab.set_dark_mode(is_dark)
        self.weekly_tab.set_dark_mode(is_dark)
        self.daily_tab.set_dark_mode(is_dark)

        style = self._get_tab_button_style(is_dark)
        self.btn_tab_general.setStyleSheet(style)
        self.btn_tab_weekly.setStyleSheet(style)
        self.btn_tab_daily.setStyleSheet(style)

    def _build_ui(self) -> None:
        self.main_stack = QStackedWidget(self)

        # 1. Página de Estado Vacío
        self.empty_state_page = EmptyStateWidget(is_dark_mode=self._is_dark_mode, parent=self)
        self.main_stack.addWidget(self.empty_state_page)

        # 2. Página Principal con Estadísticas
        content_page = QWidget()
        page_layout = QVBoxLayout(content_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Encabezado superior unificado
        header_frame = QFrame()
        header_frame.setObjectName("statsHeaderFrame")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(32, 20, 32, 14)
        h_layout.setSpacing(16)

        header_left = QVBoxLayout()
        header_left.setSpacing(2)
        title = QLabel("Estadísticas y Análisis")
        title.setObjectName("brand")
        self.stats_source_label = QLabel("REGISTRO ACTIVO")
        self.stats_source_label.setObjectName("record_meta")
        header_left.addWidget(title)
        header_left.addWidget(self.stats_source_label)
        h_layout.addLayout(header_left)

        h_layout.addStretch()

        # Botón de exportación (Integración TASK-009)
        self.btn_export = QPushButton("📤 Exportar Datos")
        self.btn_export.setObjectName("export_button")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.request_export.emit)
        h_layout.addWidget(self.btn_export)

        page_layout.addWidget(header_frame)

        # Barra Segmentada de Sub-pestañas
        tab_bar_frame = QFrame()
        tab_bar_frame.setObjectName("subtabBarFrame")
        tb_layout = QHBoxLayout(tab_bar_frame)
        tb_layout.setContentsMargins(32, 0, 32, 10)
        tb_layout.setSpacing(10)

        tab_style = self._get_tab_button_style(self._is_dark_mode)

        self.btn_tab_general = QPushButton("🌐 General / Cursada")
        self.btn_tab_general.setCheckable(True)
        self.btn_tab_general.setChecked(True)
        self.btn_tab_general.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_general.setStyleSheet(tab_style)
        self.btn_tab_general.clicked.connect(lambda: self.presenter.set_subtab(0))
        tb_layout.addWidget(self.btn_tab_general)

        self.btn_tab_weekly = QPushButton("📊 Semanal (7 Días)")
        self.btn_tab_weekly.setCheckable(True)
        self.btn_tab_weekly.setChecked(False)
        self.btn_tab_weekly.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_weekly.setStyleSheet(tab_style)
        self.btn_tab_weekly.clicked.connect(lambda: self.presenter.set_subtab(1))
        tb_layout.addWidget(self.btn_tab_weekly)

        self.btn_tab_daily = QPushButton("📅 Diario (Jornada)")
        self.btn_tab_daily.setCheckable(True)
        self.btn_tab_daily.setChecked(False)
        self.btn_tab_daily.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_daily.setStyleSheet(tab_style)
        self.btn_tab_daily.clicked.connect(lambda: self.presenter.set_subtab(2))
        tb_layout.addWidget(self.btn_tab_daily)

        tb_layout.addStretch()
        page_layout.addWidget(tab_bar_frame)

        # Stack de sub-pestañas
        self.subtab_stack = QStackedWidget()

        # Sub-pestaña 0: General
        self.general_tab = GeneralTabWidget(is_dark_mode=self._is_dark_mode)
        self.general_tab.request_load_timer.connect(self.request_load_timer.emit)
        self.general_tab.request_configure_schedule.connect(self.request_configure_schedule.emit)
        self.general_tab.request_change_sort.connect(self._on_change_top_effort_sort)
        self.subtab_stack.addWidget(self.general_tab)

        # Sub-pestaña 1: Semanal
        self.weekly_tab = WeeklyTabWidget(is_dark_mode=self._is_dark_mode)
        self.weekly_tab.request_load_timer.connect(self.request_load_timer.emit)
        self.weekly_tab.request_navigate_week.connect(self._on_navigate_week)
        self.weekly_tab.request_current_week.connect(self._on_current_week)
        self.subtab_stack.addWidget(self.weekly_tab)

        # Sub-pestaña 2: Diario
        self.daily_tab = DailyTabWidget(is_dark_mode=self._is_dark_mode)
        self.daily_tab.request_load_timer.connect(self.request_load_timer.emit)
        self.daily_tab.request_navigate_day.connect(self._on_navigate_day)
        self.daily_tab.request_today.connect(self._on_today)
        self.subtab_stack.addWidget(self.daily_tab)

        page_layout.addWidget(self.subtab_stack)
        self.main_stack.addWidget(content_page)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.main_stack)

    def _on_change_top_effort_sort(self, criteria: str) -> None:
        self.presenter.set_top_effort_criteria(criteria)

    def _on_navigate_week(self, offset: int) -> None:
        self.presenter.navigate_week(offset)

    def _on_current_week(self) -> None:
        self.presenter.go_to_current_week()

    def _on_navigate_day(self, offset: int) -> None:
        self.presenter.navigate_day(offset)

    def _on_today(self) -> None:
        self.presenter.go_to_today()

    # --- Implementación de IStatisticsView ---

    def set_empty_state(self, is_empty: bool) -> None:
        self.main_stack.setCurrentIndex(0 if is_empty else 1)

    def set_active_subtab(self, index: int) -> None:
        self.subtab_stack.setCurrentIndex(index)
        self.btn_tab_general.setChecked(index == 0)
        self.btn_tab_weekly.setChecked(index == 1)
        self.btn_tab_daily.setChecked(index == 2)

    def render_general_tab(
        self,
        stats: RecordStatistics,
        streak_days: int,
        total_study_days: int,
        evolution_data: CumulativeEvolutionData,
        top_effort: list[TopEffortExercise],
        heatmap_data: dict[str, Any],
        hourly_data: dict[int, int],
        file_name: str,
    ) -> None:
        self.stats_source_label.setText(f"FUENTE: {file_name.upper()}  ·  {stats.total_attempts} INTENTOS")
        self.general_tab.render_data(
            stats=stats,
            streak_days=streak_days,
            total_study_days=total_study_days,
            evolution_data=evolution_data,
            top_effort=top_effort,
            heatmap_data=heatmap_data,
            hourly_data=hourly_data,
        )

    def render_weekly_tab(self, summary: WeeklyStatsSummary) -> None:
        self.weekly_tab.render_data(summary)

    def render_daily_tab(self, summary: DailyStatsSummary) -> None:
        self.daily_tab.render_data(summary)

    def refresh_statistics(self) -> None:
        """Punto de entrada público llamado por MainWindow o eventos de aplicación."""
        self.presenter.refresh_all()
