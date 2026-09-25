"""Sub-pestaña Diaria: Bitácora detallada de la jornada e historial cronológico de intentos."""

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

from application.statistics_service import DailyStatsSummary
from presentation.presentation_formatters import format_hh_mm


class DailyTabWidget(QWidget):
    """Componente que proyecta las métricas de la jornada y el log cronológico de ejercicios."""

    request_navigate_day = Signal(int)  # -1 (prev), +1 (next)
    request_today = Signal()
    request_load_timer = Signal(str, int, int, object)  # (sec_type, sec_num, ex, inc)

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._is_dark_mode = is_dark_mode
        self._summary: DailyStatsSummary | None = None
        self._build_ui()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark_mode = is_dark

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 20, 32, 32)
        layout.setSpacing(18)

        # -------------------------------------------------------------
        # 1. Barra de Navegación de Días
        # -------------------------------------------------------------
        nav_card = QFrame()
        nav_card.setObjectName("sectionCard")
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(16, 12, 16, 12)
        nav_layout.setSpacing(12)

        self.btn_prev_day = QPushButton("◀ Día Anterior")
        self.btn_prev_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_day.clicked.connect(lambda: self.request_navigate_day.emit(-1))
        nav_layout.addWidget(self.btn_prev_day)

        nav_layout.addStretch()

        self.lbl_day_title = QLabel("Día")
        self.lbl_day_title.setObjectName("stat_hero_value")
        self.lbl_day_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.lbl_day_title)

        self.badge_today = QLabel("HOY")
        self.badge_today.setObjectName("badge_tag")
        self.badge_today.setStyleSheet(
            "background-color: #065f46; color: #ecfdf5; font-weight: bold; border-radius: 4px; padding: 2px 8px;"
        )
        nav_layout.addWidget(self.badge_today)

        nav_layout.addStretch()

        self.btn_today = QPushButton("📅 Ir a Hoy")
        self.btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_today.clicked.connect(self.request_today.emit)
        nav_layout.addWidget(self.btn_today)

        self.btn_next_day = QPushButton("Día Siguiente ▶")
        self.btn_next_day.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next_day.clicked.connect(lambda: self.request_navigate_day.emit(1))
        nav_layout.addWidget(self.btn_next_day)

        layout.addWidget(nav_card)

        # -------------------------------------------------------------
        # 2. KPIs de la Jornada
        # -------------------------------------------------------------
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(14)

        # Tiempo neto hoy
        card_study = QFrame()
        card_study.setObjectName("metricCard")
        c1 = QVBoxLayout(card_study)
        c1.setContentsMargins(18, 14, 18, 14)
        c1.setSpacing(4)
        l1 = QLabel("TIEMPO NETO DE ESTUDIO HOY")
        l1.setObjectName("eyebrow")
        self.lbl_day_study = QLabel("00:00")
        self.lbl_day_study.setObjectName("stat_hero_value")
        l1_sub = QLabel("TIEMPO TOTAL DE DESCANSOS")
        l1_sub.setObjectName("eyebrow")
        self.lbl_day_break = QLabel("00:00")
        self.lbl_day_break.setObjectName("stat_sub_value")
        c1.addWidget(l1)
        c1.addWidget(self.lbl_day_study)
        c1.addWidget(l1_sub)
        c1.addWidget(self.lbl_day_break)
        kpi_grid.addWidget(card_study, 0, 0)

        # Intentos y Efectividad
        card_eff = QFrame()
        card_eff.setObjectName("metricCard")
        c2 = QVBoxLayout(card_eff)
        c2.setContentsMargins(18, 14, 18, 14)
        c2.setSpacing(4)
        l2 = QLabel("EJERCICIOS COMPLETADOS HOY")
        l2.setObjectName("eyebrow")
        self.lbl_day_completed = QLabel("0")
        self.lbl_day_completed.setObjectName("stat_hero_value")
        l2_sub = QLabel("TASA DE ÉXITO DE LA JORNADA")
        l2_sub.setObjectName("eyebrow")
        self.lbl_success_rate = QLabel("0% completitud")
        self.lbl_success_rate.setObjectName("status")
        c2.addWidget(l2)
        c2.addWidget(self.lbl_day_completed)
        c2.addWidget(l2_sub)
        c2.addWidget(self.lbl_success_rate)
        kpi_grid.addWidget(card_eff, 0, 1)

        # Índice de Enfoque
        card_focus = QFrame()
        card_focus.setObjectName("metricCard")
        c3 = QVBoxLayout(card_focus)
        c3.setContentsMargins(18, 14, 18, 14)
        c3.setSpacing(4)
        l3 = QLabel("ÍNDICE DE ENFOQUE DEL DÍA")
        l3.setObjectName("eyebrow")
        self.lbl_focus_ratio = QLabel("0%")
        self.lbl_focus_ratio.setObjectName("stat_hero_value")
        l3_sub = QLabel("TOTAL DE SESIONES")
        l3_sub.setObjectName("eyebrow")
        self.lbl_sessions_count = QLabel("0 intentos registrados")
        self.lbl_sessions_count.setObjectName("stat_sub_value")
        c3.addWidget(l3)
        c3.addWidget(self.lbl_focus_ratio)
        c3.addWidget(l3_sub)
        c3.addWidget(self.lbl_sessions_count)
        kpi_grid.addWidget(card_focus, 0, 2)

        layout.addLayout(kpi_grid)

        # -------------------------------------------------------------
        # 3. Bitácora / Tabla Cronológica de Intentos del Día
        # -------------------------------------------------------------
        table_card = QFrame()
        table_card.setObjectName("sectionCard")
        tbl_layout = QVBoxLayout(table_card)
        tbl_layout.setContentsMargins(20, 16, 20, 16)
        tbl_layout.setSpacing(10)

        tbl_head = QHBoxLayout()
        tbl_title = QLabel("BITÁCORA CRONOLÓGICA DE INTENTOS")
        tbl_title.setObjectName("eyebrow")
        tbl_head.addWidget(tbl_title)
        tbl_head.addStretch()
        self.lbl_attempts_sub = QLabel("0 sesiones registradas")
        self.lbl_attempts_sub.setObjectName("status")
        tbl_head.addWidget(self.lbl_attempts_sub)
        tbl_layout.addLayout(tbl_head)

        self.day_table = QTableWidget(0, 7)
        self.day_table.setHorizontalHeaderLabels([
            "Hora",
            "Ubicación / Ejercicio",
            "Tiempo Neto",
            "Receso",
            "Resultado",
            "Notas",
            "Acción",
        ])
        self.day_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.day_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.day_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.day_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.day_table.setAlternatingRowColors(True)
        self.day_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.day_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.day_table.verticalHeader().setVisible(False)
        self.day_table.setMinimumHeight(200)
        self.day_table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        tbl_layout.addWidget(self.day_table)

        layout.addWidget(table_card)

        scroll.setWidget(container)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if self._summary and 0 <= row < len(self._summary.attempts):
            it = self._summary.attempts[row]
            self.request_load_timer.emit(it.section_type, it.section_number, it.exercise, it.inciso)

    def render_data(self, summary: DailyStatsSummary) -> None:
        self._summary = summary

        self.lbl_day_title.setText(summary.display_date)
        self.badge_today.setVisible(summary.is_today)

        self.lbl_day_study.setText(format_hh_mm(summary.total_exercise_time_ms))
        self.lbl_day_break.setText(format_hh_mm(summary.total_break_time_ms))

        total_attempts = summary.completed_count + summary.failed_count
        self.lbl_day_completed.setText(str(summary.completed_count))

        if total_attempts > 0:
            rate = int(round((summary.completed_count / total_attempts) * 100.0))
            self.lbl_success_rate.setText(f"{rate}% de efectividad ({summary.failed_count} incompletos)")
        else:
            self.lbl_success_rate.setText("Sin intentos en esta fecha")

        self.lbl_focus_ratio.setText(f"{summary.focus_ratio:.1f}%")
        self.lbl_sessions_count.setText(f"{total_attempts} sesiones registradas")

        attempts = summary.attempts
        self.lbl_attempts_sub.setText(f"{len(attempts)} sesiones realizadas")
        self.day_table.setRowCount(len(attempts))

        for row, att in enumerate(attempts):
            it_time = QTableWidgetItem(att.start_time_str)
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            inc_txt = f" (Inciso {att.inciso})" if att.inciso else ""
            ex_display = f"{att.section_display} · Ejercicio {att.exercise}{inc_txt}"
            it_ex = QTableWidgetItem(ex_display)

            it_net = QTableWidgetItem(format_hh_mm(att.exercise_time_ms))
            it_net.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            it_brk = QTableWidgetItem(format_hh_mm(att.break_time_ms))
            it_brk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            res_txt = "✓ Completado" if att.completed else "✗ Incompleto"
            it_res = QTableWidgetItem(res_txt)
            it_res.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if att.completed:
                it_res.setForeground(Qt.GlobalColor.darkGreen if not self._is_dark_mode else Qt.GlobalColor.green)
            else:
                it_res.setForeground(Qt.GlobalColor.red)

            it_notes = QTableWidgetItem(att.notes or "—")

            self.day_table.setItem(row, 0, it_time)
            self.day_table.setItem(row, 1, it_ex)
            self.day_table.setItem(row, 2, it_net)
            self.day_table.setItem(row, 3, it_brk)
            self.day_table.setItem(row, 4, it_res)
            self.day_table.setItem(row, 5, it_notes)

            load_btn = QPushButton("Cargar")
            load_btn.setProperty("small", True)
            load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            load_btn.clicked.connect(
                lambda checked=False, s=att.section_type, sn=att.section_number, e=att.exercise, inc=att.inciso: (
                    self.request_load_timer.emit(s, sn, e, inc)
                )
            )
            self.day_table.setCellWidget(row, 6, load_btn)
