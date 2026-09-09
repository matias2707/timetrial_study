"""Composicion de la interfaz Qt y adaptacion de eventos de usuario.

La ventana presenta el estado de `StudyApplicationService`; no contiene reglas
de persistencia ni construye directamente el formato de los datos guardados.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QRectF, QSettings, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QActionGroup, QBrush, QCloseEvent, QColor, QFont, QPainter, QPen
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QBoxLayout,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import SessionLocation, StudyApplicationService
from application.record_query import (
    COL_BREAK,
    COL_COMMENT,
    COL_DATE,
    COL_EXERCISE,
    COL_INCISO,
    COL_SECTION,
    COL_STATUS,
    COL_TIME,
    COLUMN_TITLES,
    ColumnFilterRule,
    apply_column_filters_and_sort,
    format_item_datetime,
    get_column_display_value,
    get_column_unique_values,
)
from application.statistics_service import DailyStatistic
from domain.models import TimerItem
from domain.timer_service import TimerMode
from presentation.excel_filter_popup import ExcelColumnFilterPopup
from presentation.planner_widget import PlannerWidget
from presentation.presentation_dialogs import ImportRecordsDialog, ItemDialog
from presentation.presentation_formatters import (
    format_hh_mm,
    format_hh_mm_ss,
    format_milliseconds,
    timer_markup,
)
from presentation.theme import THEME_DARK, THEME_LIGHT, get_dialog_stylesheet, get_theme_stylesheet

DEFAULT_SECTION_TYPE = "Guía"
APP_TITLE = "Study Timetrial"
APP_VERSION = "v1.0"
MAX_VALUE = 999_999


class WeeklyChartWidget(QWidget):
    """Componente visual que renderiza las barras de horas de estudio para 7 días."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.daily_stats: list[DailyStatistic] = []
        self.dark_mode: bool = False
        self.setMinimumHeight(175)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_stats(self, daily_stats: list[DailyStatistic]) -> None:
        self.daily_stats = daily_stats
        self.update()

    def set_dark_mode(self, dark_mode: bool) -> None:
        self.dark_mode = dark_mode
        self.update()

    def paintEvent(self, event) -> None:
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


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación Study Timetrial."""

    STYLESHEET = get_theme_stylesheet(THEME_LIGHT)

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("StudyTimetrial", "Preferences")
        self.current_theme = str(self.settings.value("theme", THEME_LIGHT))
        if self.current_theme not in (THEME_LIGHT, THEME_DARK):
            self.current_theme = THEME_LIGHT

        self.application = StudyApplicationService()

        media_dir = Path(__file__).resolve().parent / "media"
        self._sound_muted = self.settings.value("sound_muted", False, type=bool)

        self.start_sound = QSoundEffect(self)
        self.start_sound.setSource(QUrl.fromLocalFile(str(media_dir / "universfield-new-notification-040-493469.wav")))
        self.start_sound.setVolume(1.0)
        self.start_sound.setMuted(self._sound_muted)

        self.complete_sound = QSoundEffect(self)
        self.complete_sound.setSource(QUrl.fromLocalFile(str(media_dir / "universfield-new-notification-051-494246.wav")))
        self.complete_sound.setVolume(1.0)
        self.complete_sound.setMuted(self._sound_muted)

        self.setMinimumSize(940, 700)
        stylesheet = get_theme_stylesheet(self.current_theme)
        self.setStyleSheet(stylesheet)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.column_sort_states: dict[str, str] = {}
        self.column_filter_rules: dict[str, ColumnFilterRule] = {}
        self._current_displayed_items: list[TimerItem] = []
        self.LOGICAL_COL_KEYS = {
            0: COL_SECTION,
            1: COL_EXERCISE,
            2: COL_INCISO,
            3: COL_DATE,
            4: COL_BREAK,
            5: COL_TIME,
            6: COL_STATUS,
            7: COL_COMMENT,
        }

        self.home = self.build_home()
        self.records = self.build_records()
        self.statistics = self.build_statistics()
        self.planner = PlannerWidget(self.application, is_dark_mode=self.is_dark_mode, parent=self)
        self.planner.request_load_timer.connect(self._on_planner_load_timer)

        self.tabs.addTab(self.home, qta.icon("fa5s.stopwatch", color="#bef264"), "  Cronómetro")
        self.tabs.addTab(self.records, qta.icon("fa5s.history", color="#94a3b8"), "  Registros")
        self.tabs.addTab(self.statistics, qta.icon("fa5s.chart-bar", color="#94a3b8"), "  Estadísticas")
        self.tabs.addTab(self.planner, qta.icon("fa5s.tasks", color="#94a3b8"), "  Planificador")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.build_main_toolbar()

        if hasattr(self, "weekly_chart"):
            self.weekly_chart.set_dark_mode(self.is_dark_mode)

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.refresh_clock)
        self.tick.start(50)

        self.prompt_initial_record_choice()
        self.update_title()
        self.refresh_statistics()
        self.autosave()

    @property
    def is_dark_mode(self) -> bool:
        return self.current_theme == THEME_DARK

    @property
    def is_sound_muted(self) -> bool:
        return bool(self._sound_muted)

    @is_sound_muted.setter
    def is_sound_muted(self, value: bool) -> None:
        self._sound_muted = bool(value)

    @property
    def is_muted(self) -> bool:
        return self.is_sound_muted

    def toggle_sound_muted(self) -> None:
        """Alterna entre silenciar y activar los sonidos de la aplicación."""
        self.set_sound_muted(not self.is_sound_muted)

    def set_sound_muted(self, muted: bool) -> None:
        """Establece si los sonidos están silenciados y guarda la preferencia."""
        self.is_sound_muted = muted
        self.settings.setValue("sound_muted", muted)
        if hasattr(self, "start_sound"):
            self.start_sound.setMuted(muted)
        if hasattr(self, "complete_sound"):
            self.complete_sound.setMuted(muted)
        self.update_sound_action()

    def update_sound_action(self) -> None:
        """Actualiza el texto, icono y tooltip de la acción de sonido según el estado actual."""
        if not hasattr(self, "sound_action"):
            return
        is_dark = self.is_dark_mode
        if self.is_sound_muted:
            self.sound_action.setText("Activar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-up", color="#34d399" if is_dark else "#10b981"))
            self.sound_action.setToolTip("Activar las notificaciones de sonido del cronómetro")
        else:
            self.sound_action.setText("Silenciar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-mute", color="#f87171" if is_dark else "#e11d48"))
            self.sound_action.setToolTip("Silenciar las notificaciones de sonido del cronómetro")

    def play_start_sound(self) -> None:
        """Reproduce el sonido de inicio si no está silenciado."""
        if not self.is_sound_muted and hasattr(self, "start_sound"):
            self.start_sound.play()

    def play_complete_sound(self) -> None:
        """Reproduce el sonido de completado si no está silenciado."""
        if not self.is_sound_muted and hasattr(self, "complete_sound"):
            self.complete_sound.play()

    def set_theme(self, theme: str) -> None:
        """Aplica el tema visual ('light' o 'dark') en toda la aplicación."""
        self.current_theme = theme
        self.settings.setValue("theme", theme)

        if hasattr(self, "theme_dark_action"):
            self.theme_dark_action.setChecked(theme == THEME_DARK)
        if hasattr(self, "theme_light_action"):
            self.theme_light_action.setChecked(theme == THEME_LIGHT)

        stylesheet = get_theme_stylesheet(theme)
        self.setStyleSheet(stylesheet)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)

        if hasattr(self, "weekly_chart"):
            self.weekly_chart.set_dark_mode(theme == THEME_DARK)
        if hasattr(self, "planner"):
            self.planner.set_dark_mode(theme == THEME_DARK)

        self.update_timer_visual_state()
        self.update_theme_icons()

        if hasattr(self, "table") and self.table.rowCount() > 0:
            self.refresh_table()

    def update_theme_icons(self) -> None:
        """Actualiza los iconos de la barra y botones según el contraste del tema actual."""
        is_dark = self.is_dark_mode
        toolbar_icon_color = "#cbd5e1" if is_dark else "#334155"

        if hasattr(self, "file_button"):
            self.file_button.setIcon(qta.icon("fa5s.folder", color=toolbar_icon_color))
        if hasattr(self, "config_button"):
            self.config_button.setIcon(qta.icon("fa5s.cog", color=toolbar_icon_color))
        if hasattr(self, "view_button"):
            self.view_button.setIcon(qta.icon("fa5s.cog", color=toolbar_icon_color))
        if hasattr(self, "themes_menu"):
            self.themes_menu.setIcon(qta.icon("fa5s.palette", color=toolbar_icon_color))
        if hasattr(self, "sound_action"):
            self.update_sound_action()
        if hasattr(self, "new_file_action"):
            self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=toolbar_icon_color))
        if hasattr(self, "open_file_action"):
            self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=toolbar_icon_color))
        if hasattr(self, "recent_file_action"):
            self.recent_file_action.setIcon(qta.icon("fa5s.history", color=toolbar_icon_color))
        if hasattr(self, "save_file_action"):
            self.save_file_action.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))

        # Iconos de steppers numéricos (Sección Nº, Ejercicio, Inciso)
        stepper_icon_color = "#94a3b8" if is_dark else "#475569"
        if hasattr(self, "stepper_buttons"):
            for i, btn in enumerate(self.stepper_buttons):
                icon_name = "fa5s.minus" if (i % 2 == 0) else "fa5s.plus"
                btn.setIcon(qta.icon(icon_name, color=stepper_icon_color))

        # Iconos de botones de navegación rápida
        nav_icon_color = "#94a3b8" if is_dark else "#475569"
        if hasattr(self, "navigation_buttons"):
            for i, btn in enumerate(self.navigation_buttons):
                icon_name = "fa5s.chevron-left" if (i % 2 == 0) else "fa5s.chevron-right"
                btn.setIcon(qta.icon(icon_name, color=nav_icon_color))

        self.update_session_button()

    def _on_tab_changed(self, index: int) -> None:
        """Actualiza la vista correspondiente e iconos cuando el usuario cambia de pestaña."""
        icons = [
            ("fa5s.stopwatch", "  Cronómetro"),
            ("fa5s.history", "  Registros"),
            ("fa5s.chart-bar", "  Estadísticas"),
            ("fa5s.tasks", "  Planificador"),
        ]
        for i, (icon_name, title) in enumerate(icons):
            color = "#bef264" if i == index else "#94a3b8"
            self.tabs.setTabIcon(i, qta.icon(icon_name, color=color))

        if index == 1:
            self.refresh_table()
        elif index == 2:
            self.refresh_statistics()
        elif index == 3:
            self.planner.refresh_view()

    def build_main_toolbar(self) -> None:
        """Construye el toolbar principal con las acciones de archivo y vista."""
        toolbar = QToolBar("Barra principal", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        is_dark = self.is_dark_mode
        icon_color = "#cbd5e1" if is_dark else "#334155"

        # --- Menú Archivo ---
        self.file_menu = QMenu("Archivo", self)

        self.new_file_action = QAction("Nuevo archivo", self)
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=icon_color))
        self.new_file_action.triggered.connect(self.new_record)
        self.file_menu.addAction(self.new_file_action)

        self.open_file_action = QAction("Abrir archivo", self)
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.open_file_action.triggered.connect(self.open_record)
        self.file_menu.addAction(self.open_file_action)

        self.recent_file_action = QAction("Reciente", self)
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=icon_color))
        self.recent_files_menu = QMenu(self)
        self.recent_file_action.setMenu(self.recent_files_menu)
        self.file_menu.addAction(self.recent_file_action)

        self.save_file_action = QAction("Guardar como", self)
        self.save_file_action.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.save_file_action.triggered.connect(self.save_as)
        self.file_menu.addAction(self.save_file_action)

        self.file_menu.addSeparator()
        close_file_action = QAction("Cerrar archivo", self)
        close_file_action.setIcon(qta.icon("fa5s.times-circle", color="#e11d48"))
        close_file_action.triggered.connect(self.close_record)
        self.file_menu.addAction(close_file_action)

        close_program_action = QAction("Cerrar programa", self)
        close_program_action.setIcon(qta.icon("fa5s.power-off", color="#e11d48"))
        close_program_action.triggered.connect(self.close)
        self.file_menu.addAction(close_program_action)

        self.file_button = QToolButton(toolbar)
        self.file_button.setObjectName("file_toolbar_button")
        self.file_button.setText(" Archivo")
        self.file_button.setIcon(qta.icon("fa5s.folder", color=icon_color))
        self.file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.file_button.setMenu(self.file_menu)
        self.file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.file_button.setStyleSheet("QToolButton#file_toolbar_button::menu-indicator { image: none; }")
        toolbar.addWidget(self.file_button)

        # --- Menú Configuración (Temas y Sonidos) ---
        self.config_menu = QMenu("Configuración", self)
        self.view_menu = self.config_menu  # alias para retrocompatibilidad

        self.themes_menu = QMenu("Temas", self.config_menu)
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=icon_color))

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        self.theme_dark_action = QAction("Modo oscuro", self)
        self.theme_dark_action.setIcon(qta.icon("fa5s.moon", color="#60a5fa"))
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.setChecked(self.current_theme == THEME_DARK)
        self.theme_dark_action.triggered.connect(lambda: self.set_theme(THEME_DARK))
        theme_group.addAction(self.theme_dark_action)
        self.themes_menu.addAction(self.theme_dark_action)

        self.theme_light_action = QAction("Modo claro", self)
        self.theme_light_action.setIcon(qta.icon("fa5s.sun", color="#eab308"))
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.setChecked(self.current_theme == THEME_LIGHT)
        self.theme_light_action.triggered.connect(lambda: self.set_theme(THEME_LIGHT))
        theme_group.addAction(self.theme_light_action)
        self.themes_menu.addAction(self.theme_light_action)

        self.config_menu.addMenu(self.themes_menu)
        self.config_menu.addSeparator()

        # Acción silenciar/activar sonidos
        self.sound_action = QAction(self)
        self.mute_action = self.sound_action  # alias
        self.sound_action.triggered.connect(self.toggle_sound_muted)
        self.config_menu.addAction(self.sound_action)
        self.update_sound_action()

        self.config_button = QToolButton(toolbar)
        self.view_button = self.config_button  # alias para retrocompatibilidad
        self.config_button.setObjectName("config_toolbar_button")
        self.config_button.setText(" Configuración")
        self.config_button.setIcon(qta.icon("fa5s.cog", color=icon_color))
        self.config_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.config_button.setMenu(self.config_menu)
        self.config_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.config_button.setStyleSheet(
            "QToolButton#config_toolbar_button::menu-indicator, "
            "QToolButton#view_toolbar_button::menu-indicator { image: none; }"
        )
        toolbar.addWidget(self.config_button)

    def build_home(self) -> QWidget:
        """Construye la vista del cronómetro completamente responsiva."""
        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        container = QWidget()
        container.setObjectName("homeContainer")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(40, 24, 40, 32)
        outer.setSpacing(16)

        # Top Bar: App/Record title + Today card
        top = QHBoxLayout()
        top.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.home_title = QLabel(APP_TITLE)
        self.home_title.setObjectName("brand")
        record_meta = QLabel("REGISTRO LOCAL  ·  SIN SERVIDOR")
        record_meta.setObjectName("record_meta")
        title_box.addWidget(self.home_title)
        title_box.addWidget(record_meta)
        top.addLayout(title_box)
        top.addStretch()

        today_card = QFrame()
        today_card.setObjectName("todayCard")
        today_layout = QHBoxLayout(today_card)
        today_layout.setContentsMargins(14, 8, 16, 8)
        today_layout.setSpacing(12)

        today_icon = QLabel()
        today_icon.setPixmap(qta.icon("fa5s.stopwatch", color="#10b981").pixmap(20, 20))
        today_icon.setObjectName("today_icon")
        today_layout.addWidget(today_icon)

        today_text_layout = QVBoxLayout()
        today_text_layout.setContentsMargins(0, 0, 0, 0)
        today_text_layout.setSpacing(1)

        today_title = QLabel("ESTUDIADO HOY")
        today_title.setObjectName("today_label")
        self.today_study_label = QLabel("00:00:00")
        self.today_study_label.setObjectName("today_value")
        today_text_layout.addWidget(today_title)
        today_text_layout.addWidget(self.today_study_label)
        today_layout.addLayout(today_text_layout)

        top.addWidget(today_card)
        outer.addLayout(top)

        # Hero Card: Location
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(14)

        hero_header = QHBoxLayout()
        hero_icon = QLabel()
        hero_icon.setPixmap(qta.icon("fa5s.map-marker-alt", color="#84cc16").pixmap(14, 14))
        hero_header.addWidget(hero_icon)
        eyebrow = QLabel("UBICACIÓN ACTUAL")
        eyebrow.setObjectName("eyebrow")
        hero_header.addWidget(eyebrow)
        hero_header.addStretch()
        hero_layout.addLayout(hero_header)

        self.location_label = QLabel()
        self.location_label.setObjectName("location_badge")
        self.location_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.location_label.setWordWrap(True)
        hero_layout.addWidget(self.location_label)

        selectors = QGridLayout()
        selectors.setHorizontalSpacing(12)
        selectors.setVerticalSpacing(6)
        self.section_input = QLineEdit(DEFAULT_SECTION_TYPE)
        self.section_input.setPlaceholderText("Tipo de sección")
        self.section_number_input = QSpinBox()
        self.section_number_input.setRange(1, MAX_VALUE)
        self.section_number_input.setValue(1)
        self.exercise_input = QSpinBox()
        self.exercise_input.setRange(1, MAX_VALUE)
        self.exercise_input.setValue(1)
        self.inciso_input = QSpinBox()
        self.inciso_input.setRange(0, MAX_VALUE)
        self.inciso_input.setSpecialValueText("Sin inciso")

        self.section_input.textChanged.connect(self.sync_location)
        self.section_number_input.valueChanged.connect(self.sync_location)
        self.exercise_input.valueChanged.connect(self.sync_location)
        self.inciso_input.valueChanged.connect(self.sync_location)

        self.stepper_buttons: list[QPushButton] = []
        section_number_stepper = self._create_stepper(self.section_number_input, "número de sección")
        exercise_stepper = self._create_stepper(self.exercise_input, "ejercicio")
        inciso_stepper = self._create_stepper(self.inciso_input, "inciso")

        for column, (label, widget) in enumerate((
            ("Sección", self.section_input),
            ("Nº", section_number_stepper),
            ("Ejercicio", exercise_stepper),
            ("Inciso", inciso_stepper),
        )):
            field_label = QLabel(label.upper())
            field_label.setObjectName("eyebrow")
            selectors.addWidget(field_label, 0, column)
            selectors.addWidget(widget, 1, column)
        selectors.setColumnStretch(0, 2)
        selectors.setColumnStretch(1, 1)
        selectors.setColumnStretch(2, 1)
        selectors.setColumnStretch(3, 1)
        hero_layout.addLayout(selectors)
        outer.addWidget(hero)

        # Metrics Layout: Clocks
        metrics = QHBoxLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(14)
        self.metrics_layout = metrics

        self.exercise_clock = QLabel(timer_markup(0))
        self.break_clock = QLabel(timer_markup(0))
        for clock in (self.exercise_clock, self.break_clock):
            clock.setTextFormat(Qt.TextFormat.RichText)
            clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            clock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.exercise_card = QFrame()
        self.exercise_card.setObjectName("exerciseCard")
        exercise_layout = QVBoxLayout(self.exercise_card)
        exercise_layout.setContentsMargins(22, 16, 22, 18)
        exercise_layout.setSpacing(4)

        ex_top = QHBoxLayout()
        ex_icon = QLabel()
        ex_icon.setPixmap(qta.icon("fa5s.stopwatch", color="#34d399").pixmap(14, 14))
        ex_top.addWidget(ex_icon)
        exercise_label = QLabel("TIEMPO EJERCICIO")
        exercise_label.setObjectName("eyebrow")
        ex_top.addWidget(exercise_label)
        ex_top.addStretch()
        exercise_layout.addLayout(ex_top)

        self.exercise_clock.setObjectName("digital_clock_exercise")
        exercise_layout.addWidget(self.exercise_clock)
        metrics.addWidget(self.exercise_card, 3)

        self.break_card = QFrame()
        self.break_card.setObjectName("breakCard")
        break_layout = QVBoxLayout(self.break_card)
        break_layout.setContentsMargins(20, 16, 20, 18)
        break_layout.setSpacing(4)

        br_top = QHBoxLayout()
        br_icon = QLabel()
        br_icon.setPixmap(qta.icon("fa5s.coffee", color="#fbbf24").pixmap(14, 14))
        br_top.addWidget(br_icon)
        break_label = QLabel("RECESO ACUMULADO")
        break_label.setObjectName("eyebrow")
        br_top.addWidget(break_label)
        br_top.addStretch()
        break_layout.addLayout(br_top)

        self.break_clock.setObjectName("digital_clock_break")
        break_layout.addWidget(self.break_clock)
        metrics.addWidget(self.break_card, 2)
        outer.addLayout(metrics)

        # Controls Card
        controls_card = QFrame()
        controls_card.setObjectName("sectionCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(22, 18, 22, 20)
        controls_layout.setSpacing(14)

        controls_header = QHBoxLayout()
        controls_icon = QLabel()
        controls_icon.setPixmap(qta.icon("fa5s.play-circle", color="#84cc16").pixmap(14, 14))
        controls_header.addWidget(controls_icon)
        controls_title = QLabel("CONTROLES DE SESIÓN")
        controls_title.setObjectName("eyebrow")
        controls_header.addWidget(controls_title)
        controls_header.addStretch()
        self.status_pill = QLabel(" ●  LISTO PARA COMENZAR")
        self.status_pill.setObjectName("status_badge")
        controls_header.addWidget(self.status_pill)
        controls_layout.addLayout(controls_header)

        # Primary Controls Grid (Cuadrícula simétrica y ergonómica)
        self.primary_controls = QGridLayout()
        self.primary_controls.setHorizontalSpacing(10)
        self.primary_controls.setVerticalSpacing(10)

        self.session_button = QPushButton("  INICIAR")
        self.session_button.setObjectName("hero_start")
        self.session_button.setIcon(qta.icon("fa5s.play", color="#bef264"))
        self.session_button.clicked.connect(self.toggle_session)

        self.stop_button = QPushButton("  DETENER")
        self.stop_button.setObjectName("stop")
        self.stop_button.setIcon(qta.icon("fa5s.stop", color="#dc2626"))
        self.stop_button.clicked.connect(self.stop_timer)

        self.complete_button = QPushButton("  COMPLETO")
        self.complete_button.setObjectName("complete")
        self.complete_button.setIcon(qta.icon("fa5s.check-circle", color="#ffffff"))
        self.complete_button.clicked.connect(lambda: self.finish_item(True, keep_location=True))

        self.incomplete_button = QPushButton("  INCOMPLETO")
        self.incomplete_button.setObjectName("danger")
        self.incomplete_button.setIcon(qta.icon("fa5s.times-circle", color="#ffffff"))
        self.incomplete_button.clicked.connect(lambda: self.finish_item(False, keep_location=True))

        self.comment_button = QPushButton("  COMENTARIO")
        self.comment_button.setObjectName("comment_action")
        self.comment_button.setIcon(qta.icon("fa5s.comment-dots", color="#475569"))
        self.comment_button.clicked.connect(self.add_home_comment)

        self.primary_buttons = (
            self.session_button,
            self.stop_button,
            self.complete_button,
            self.incomplete_button,
            self.comment_button,
        )
        for button in self.primary_buttons:
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        controls_layout.addLayout(self.primary_controls)
        self._arrange_session_controls(compact=False, very_compact=False)

        # Navigation Header & Pods
        nav_header = QLabel("NAVEGACIÓN RÁPIDA")
        nav_header.setObjectName("eyebrow")
        nav_header.setStyleSheet("margin-top: 6px;")
        controls_layout.addWidget(nav_header)

        # Botones de navegación con iconos y tooltips claros
        self.btn_prev_section = QPushButton("  Anterior")
        self.btn_prev_section.setObjectName("nav_button")
        self.btn_prev_section.setToolTip("Guardar intento y volver a la sección anterior")
        self.btn_prev_section.setIcon(qta.icon("fa5s.chevron-left", color="#94a3b8"))
        self.btn_prev_section.clicked.connect(self.previous_section)

        self.btn_next_section = QPushButton("Siguiente  ")
        self.btn_next_section.setObjectName("nav_button")
        self.btn_next_section.setToolTip("Guardar intento y avanzar a la siguiente sección")
        self.btn_next_section.setIcon(qta.icon("fa5s.chevron-right", color="#94a3b8"))
        self.btn_next_section.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_next_section.clicked.connect(self.next_section)

        self.btn_prev_exercise = QPushButton("  Anterior")
        self.btn_prev_exercise.setObjectName("nav_button")
        self.btn_prev_exercise.setToolTip("Guardar intento y volver al ejercicio anterior")
        self.btn_prev_exercise.setIcon(qta.icon("fa5s.chevron-left", color="#94a3b8"))
        self.btn_prev_exercise.clicked.connect(self.previous_exercise)

        self.btn_next_exercise = QPushButton("Siguiente  ")
        self.btn_next_exercise.setObjectName("nav_button")
        self.btn_next_exercise.setToolTip("Guardar intento y pasar al siguiente ejercicio")
        self.btn_next_exercise.setIcon(qta.icon("fa5s.chevron-right", color="#94a3b8"))
        self.btn_next_exercise.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_next_exercise.clicked.connect(self.next_exercise)

        self.btn_prev_inciso = QPushButton("  Anterior")
        self.btn_prev_inciso.setObjectName("nav_button")
        self.btn_prev_inciso.setToolTip("Guardar intento y volver al inciso anterior")
        self.btn_prev_inciso.setIcon(qta.icon("fa5s.chevron-left", color="#94a3b8"))
        self.btn_prev_inciso.clicked.connect(self.previous_inciso)

        self.btn_next_inciso = QPushButton("Siguiente  ")
        self.btn_next_inciso.setObjectName("nav_button")
        self.btn_next_inciso.setToolTip("Guardar intento y avanzar al siguiente inciso")
        self.btn_next_inciso.setIcon(qta.icon("fa5s.chevron-right", color="#94a3b8"))
        self.btn_next_inciso.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.btn_next_inciso.clicked.connect(self.next_inciso)

        self.navigation_buttons = [
            self.btn_prev_section,
            self.btn_next_section,
            self.btn_prev_exercise,
            self.btn_next_exercise,
            self.btn_prev_inciso,
            self.btn_next_inciso,
        ]

        # 3 Pods jerárquicos alineados: Sección, Ejercicio, Inciso
        self.nav_pod_section = self._create_nav_pod("Sección", "fa5s.bookmark", self.btn_prev_section, self.btn_next_section)
        self.nav_pod_exercise = self._create_nav_pod("Ejercicio", "fa5s.tasks", self.btn_prev_exercise, self.btn_next_exercise)
        self.nav_pod_inciso = self._create_nav_pod("Inciso", "fa5s.list-ol", self.btn_prev_inciso, self.btn_next_inciso)

        self.navigation = QGridLayout()
        self.navigation.setHorizontalSpacing(10)
        self.navigation.setVerticalSpacing(10)
        self._arrange_navigation_pods(compact=False)
        controls_layout.addLayout(self.navigation)

        self.status_label = QLabel("Listo para comenzar")
        self.status_label.setObjectName("status")
        self.status_label.setVisible(False)
        controls_layout.addWidget(self.status_label)

        outer.addWidget(controls_card)
        outer.addStretch()

        scroll.setWidget(container)
        self.sync_location()
        return scroll

    def _create_stepper(self, spinbox: QSpinBox, tooltip_prefix: str) -> QWidget:
        """Envuelve un QSpinBox con botones [-] y [+] táctiles y modernos."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        icon_color = "#94a3b8" if self.is_dark_mode else "#475569"

        btn_minus = QPushButton()
        btn_minus.setObjectName("stepper_button")
        btn_minus.setToolTip(f"Decrementar {tooltip_prefix}")
        btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_minus.setIcon(qta.icon("fa5s.minus", color=icon_color))
        btn_minus.clicked.connect(spinbox.stepDown)

        btn_plus = QPushButton()
        btn_plus.setObjectName("stepper_button")
        btn_plus.setToolTip(f"Incrementar {tooltip_prefix}")
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.setIcon(qta.icon("fa5s.plus", color=icon_color))
        btn_plus.clicked.connect(spinbox.stepUp)

        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(btn_minus)
        layout.addWidget(spinbox, 1)
        layout.addWidget(btn_plus)

        if not hasattr(self, "stepper_buttons"):
            self.stepper_buttons = []
        self.stepper_buttons.extend([btn_minus, btn_plus])

        return container

    def _create_nav_pod(
        self,
        title: str,
        icon_name: str,
        prev_btn: QPushButton,
        next_btn: QPushButton,
    ) -> QFrame:
        """Crea un módulo visual agrupado para navegar por Sección, Ejercicio o Inciso."""
        pod = QFrame()
        pod.setObjectName("nav_pod")
        pod_layout = QVBoxLayout(pod)
        pod_layout.setContentsMargins(12, 10, 12, 12)
        pod_layout.setSpacing(8)

        # Encabezado del pod
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 0)
        header.setSpacing(6)
        icon_label = QLabel()
        icon_color = "#bef264" if self.is_dark_mode else "#65a30d"
        icon_label.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(12, 12))
        header.addWidget(icon_label)

        lbl = QLabel(title.upper())
        lbl.setObjectName("eyebrow")
        lbl.setStyleSheet("font-size: 10px; font-weight: 800; letter-spacing: 1.2px;")
        header.addWidget(lbl)
        header.addStretch()
        pod_layout.addLayout(header)

        # Botones Anterior / Siguiente en fila
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        prev_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        next_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(prev_btn)
        btn_layout.addWidget(next_btn)
        pod_layout.addLayout(btn_layout)

        return pod

    def _arrange_session_controls(self, compact: bool = False, very_compact: bool = False) -> None:
        """Distribuye simétricamente los controles de sesión en cuadrícula según el ancho."""
        while self.primary_controls.count():
            self.primary_controls.takeAt(0)

        for col in range(4):
            self.primary_controls.setColumnStretch(col, 1)

        if very_compact:
            # 1 columna vertical para ventanas muy estrechas
            for idx, btn in enumerate(self.primary_buttons):
                self.primary_controls.addWidget(btn, idx, 0)
        elif compact:
            # 2 columnas equilibradas
            # Fila 0: INICIAR (span 2)
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 2)
            # Fila 1: DETENER, COMENTARIO
            self.primary_controls.addWidget(self.stop_button, 1, 0)
            self.primary_controls.addWidget(self.comment_button, 1, 1)
            # Fila 2: COMPLETO, INCOMPLETO
            self.primary_controls.addWidget(self.complete_button, 2, 0)
            self.primary_controls.addWidget(self.incomplete_button, 2, 1)
        else:
            # 4 columnas, 2 filas simétricas
            # Fila 0: INICIAR (span 2), DETENER (col 2), COMENTARIO (col 3)
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 2)
            self.primary_controls.addWidget(self.stop_button, 0, 2)
            self.primary_controls.addWidget(self.comment_button, 0, 3)
            # Fila 1: COMPLETO (span 2), INCOMPLETO (span 2)
            self.primary_controls.addWidget(self.complete_button, 1, 0, 1, 2)
            self.primary_controls.addWidget(self.incomplete_button, 1, 2, 1, 2)

    def _arrange_navigation_pods(self, compact: bool = False) -> None:
        """Distribuye los 3 pods de navegación en 3 columnas o 3 filas según el ancho."""
        while self.navigation.count():
            self.navigation.takeAt(0)

        pods = (self.nav_pod_section, self.nav_pod_exercise, self.nav_pod_inciso)
        if compact:
            # 3 filas de 1 pod cada una
            for row, pod in enumerate(pods):
                self.navigation.addWidget(pod, row, 0)
            self.navigation.setColumnStretch(0, 1)
            self.navigation.setColumnStretch(1, 0)
            self.navigation.setColumnStretch(2, 0)
        else:
            # 3 columnas lado a lado (1 fila)
            for col, pod in enumerate(pods):
                self.navigation.addWidget(pod, 0, col)
                self.navigation.setColumnStretch(col, 1)

    def resizeEvent(self, event) -> None:
        """Refluye controles y adapta los relojes y cuadrículas responsivamente."""
        super().resizeEvent(event)
        w = self.width()
        compact = w < 960
        very_compact = w < 720

        if hasattr(self, "primary_controls"):
            self._arrange_session_controls(compact, very_compact)

        if hasattr(self, "navigation"):
            self._arrange_navigation_pods(compact)

        if hasattr(self, "metrics_layout"):
            self.metrics_layout.setDirection(
                QBoxLayout.Direction.TopToBottom if very_compact else QBoxLayout.Direction.LeftToRight
            )

        self.update_timer_visual_state()

    def build_records(self) -> QWidget:
        """Construye la vista donde se muestran y gestionan los registros guardados."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(14)

        # Heading
        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Registros")
        title.setObjectName("brand")
        self.records_summary = QLabel("0 intentos guardados")
        self.records_summary.setObjectName("record_meta")
        title_box.addWidget(title)
        title_box.addWidget(self.records_summary)
        heading.addLayout(title_box)
        heading.addStretch()
        layout.addLayout(heading)

        # Quick KPI Metrics Cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        def make_kpi(icon_name: str, icon_color: str, title: str) -> tuple[QFrame, QLabel]:
            card = QFrame()
            card.setObjectName("kpiCard")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 10, 14, 10)
            c_layout.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(18, 18))
            c_layout.addWidget(icon_lbl)

            t_layout = QVBoxLayout()
            t_layout.setContentsMargins(0, 0, 0, 0)
            t_layout.setSpacing(1)
            t_lbl = QLabel(title)
            t_lbl.setObjectName("kpi_title")
            v_lbl = QLabel("-")
            v_lbl.setObjectName("kpi_value")
            t_layout.addWidget(t_lbl)
            t_layout.addWidget(v_lbl)
            c_layout.addLayout(t_layout)
            return card, v_lbl

        card_att, self.rec_stat_attempts = make_kpi("fa5s.history", "#3b82f6", "TOTAL INTENTOS")
        card_ex, self.rec_stat_exercise_time = make_kpi("fa5s.clock", "#10b981", "TIEMPO ESTUDIO")
        card_br, self.rec_stat_break_time = make_kpi("fa5s.coffee", "#f59e0b", "TIEMPO RECESO")
        card_eff, self.rec_stat_effectiveness = make_kpi("fa5s.check-circle", "#84cc16", "EFECTIVIDAD")

        for c in (card_att, card_ex, card_br, card_eff):
            c.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
            kpi_row.addWidget(c)
        layout.addLayout(kpi_row)

        # Toolbar and Search
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        open_button = QPushButton(" Abrir")
        open_button.setIcon(qta.icon("fa5s.folder-open", color="#334155"))
        open_button.setObjectName("secondary_action")
        self.recent_files_menu = QMenu(self)
        self.refresh_recent_files_menu()
        open_button.setMenu(self.recent_files_menu)
        open_button.clicked.connect(self.open_record)
        toolbar.addWidget(open_button)

        for text, callback, icon_name, icon_color in (
            ("Importar", self.import_records, "fa5s.file-import", "#334155"),
            ("Guardar como", self.save_as, "fa5s.save", "#334155"),
            ("Renombrar", self.rename_record, "fa5s.pen", "#334155"),
            ("Cerrar", self.close_record, "fa5s.times", "#ef4444"),
        ):
            button = QPushButton(f" {text}")
            button.setObjectName("secondary_action")
            button.setIcon(qta.icon(icon_name, color=icon_color))
            button.clicked.connect(callback)
            toolbar.addWidget(button)

        toolbar.addStretch()

        # Search Bar
        self.record_search_input = QLineEdit()
        self.record_search_input.setPlaceholderText("Buscar sección, ejercicio o comentario...")
        self.record_search_input.setClearButtonEnabled(True)
        self.record_search_input.setMinimumWidth(260)
        self.record_search_input.addAction(qta.icon("fa5s.search", color="#94a3b8"), QLineEdit.ActionPosition.LeadingPosition)
        self.record_search_input.textChanged.connect(self.filter_records_table)
        toolbar.addWidget(self.record_search_input)

        add_btn = QPushButton(" Agregar intento")
        add_btn.setObjectName("toolbar_primary")
        add_btn.setIcon(qta.icon("fa5s.plus", color="#bef264"))
        add_btn.clicked.connect(self.add_item)
        toolbar.addWidget(add_btn)

        # Botón para limpiar todos los filtros activos
        self.clear_all_filters_btn = QPushButton(" Limpiar filtros")
        self.clear_all_filters_btn.setObjectName("filter_reset_btn")
        self.clear_all_filters_btn.setIcon(qta.icon("fa5s.filter", color="#94a3b8"))
        self.clear_all_filters_btn.setToolTip("Restablecer todos los filtros y órdenes de columna")
        self.clear_all_filters_btn.clicked.connect(self.reset_all_filters)
        self.clear_all_filters_btn.setVisible(False)
        toolbar.addWidget(self.clear_all_filters_btn)

        layout.addLayout(toolbar)

        # Table (12 columnas incluyendo Fecha visible y cabeceras interactivas estilo Excel)
        self.table = QTableWidget(0, 12)
        header = self.table.horizontalHeader()

        # Permitir arrastrar columnas para definir la jerarquía (la más a la izquierda tiene mayor jerarquía)
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDropIndicatorShown(True)
        header.setSortIndicatorShown(False)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Conectar eventos de cabecera
        header.sectionClicked.connect(self._on_header_section_clicked)
        header.customContextMenuRequested.connect(self._on_header_context_menu)
        header.sectionMoved.connect(self._on_column_moved)

        self.update_header_labels()

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        for col in (8, 9, 10, 11):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, 48)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self.show_comment_alert)
        layout.addWidget(self.table)
        return page

    def update_header_labels(self) -> None:
        """Actualiza los títulos de las cabeceras mostrando flecha de orden y filtro activo."""
        labels = []
        for col_idx in range(8):
            col_key = self.LOGICAL_COL_KEYS[col_idx]
            title = COLUMN_TITLES.get(col_key, col_key.capitalize())

            # Indicador de orden (▲ o ▼, sin números ya que la posición física define la jerarquía)
            sort_dir = self.column_sort_states.get(col_key)
            arrow = ""
            if sort_dir == "asc":
                arrow = " ▲"
            elif sort_dir == "desc":
                arrow = " ▼"

            # Indicador de filtro activo
            filter_rule = self.column_filter_rules.get(col_key)
            filter_icon = " 🔍" if (filter_rule and filter_rule.is_active()) else ""
            labels.append(f"{title}{arrow}{filter_icon}")

        # Columnas de acción fijas
        labels.extend(["💬", "✏️", "🔄", "🗑️"])
        self.table.setHorizontalHeaderLabels(labels)

    def get_active_sorts_by_hierarchy(self) -> list[tuple[str, str]]:
        """Devuelve las tuplas (col_key, direction) ordenadas por su posición visual (de izquierda a derecha)."""
        active: list[tuple[int, str, str]] = []
        header = self.table.horizontalHeader()

        for logical_index, col_key in self.LOGICAL_COL_KEYS.items():
            direction = self.column_sort_states.get(col_key)
            if direction in ("asc", "desc"):
                visual_index = header.visualIndex(logical_index)
                active.append((visual_index, col_key, direction))

        # La columna con menor visual_index (más a la izquierda) tiene la jerarquía dominante
        active.sort(key=lambda item: item[0])
        return [(col_key, direction) for _, col_key, direction in active]

    def _on_header_section_clicked(self, logical_index: int) -> None:
        """Ciclo de 3 clics en cabecera: Ascendente -> Descendente -> Sin orden."""
        if logical_index not in self.LOGICAL_COL_KEYS:
            return

        col_key = self.LOGICAL_COL_KEYS[logical_index]
        current_direction = self.column_sort_states.get(col_key)

        if current_direction is None:
            # 1° Clic: Ascendente
            self.column_sort_states[col_key] = "asc"
        elif current_direction == "asc":
            # 2° Clic: Descendente
            self.column_sort_states[col_key] = "desc"
        else:
            # 3° Clic: Quitar orden
            self.column_sort_states.pop(col_key, None)

        self.update_header_labels()
        self.refresh_table()

    def _on_column_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int) -> None:
        """Al arrastrar y soltar columnas, se recalcula la jerarquía de izquierda a derecha."""
        self.refresh_table()

    def _on_header_context_menu(self, pos) -> None:
        """Abre el diálogo de filtro estilo Excel al hacer clic derecho en la cabecera."""
        header = self.table.horizontalHeader()
        logical_index = header.logicalIndexAt(pos)
        if logical_index not in self.LOGICAL_COL_KEYS:
            return

        col_key = self.LOGICAL_COL_KEYS[logical_index]
        self.open_excel_filter_popup(logical_index, col_key)

    def open_excel_filter_popup(self, logical_index: int, col_key: str) -> None:
        """Construye y posiciona el popup de filtro de Excel para la columna dada."""
        all_items = self.application.record.items
        current_rule = self.column_filter_rules.get(col_key)
        current_sort = self.column_sort_states.get(col_key)

        popup = ExcelColumnFilterPopup(
            column_key=col_key,
            items=all_items,
            current_rule=current_rule,
            current_sort_direction=current_sort,
            parent=self,
        )
        popup.filter_applied.connect(self._on_popup_filter_applied)
        popup.sort_requested.connect(self._on_popup_sort_requested)

        # Posicionar el popup justo debajo del cabezal de la columna
        header = self.table.horizontalHeader()
        section_viewport_x = header.sectionViewportPosition(logical_index)
        global_pos = self.table.mapToGlobal(self.table.rect().topLeft())
        popup_x = max(20, global_pos.x() + section_viewport_x)
        popup_y = header.mapToGlobal(header.rect().bottomLeft()).y() + 2

        popup.move(popup_x, popup_y)
        popup.exec()

    def _on_popup_filter_applied(self, col_key: str, rule: ColumnFilterRule) -> None:
        """Recibe la regla de filtro desde el popup de Excel."""
        if rule.is_active():
            self.column_filter_rules[col_key] = rule
        else:
            self.column_filter_rules.pop(col_key, None)

        self.update_header_labels()
        self.refresh_table()

    def _on_popup_sort_requested(self, col_key: str, direction: str) -> None:
        """Aplica la dirección de orden solicitada desde el popup de Excel."""
        if direction in ("asc", "desc"):
            self.column_sort_states[col_key] = direction
        else:
            self.column_sort_states.pop(col_key, None)

        self.update_header_labels()
        self.refresh_table()

    def reset_all_filters(self) -> None:
        """Restablece todos los filtros de columna y búsqueda textual."""
        self.column_filter_rules.clear()
        self.column_sort_states.clear()
        if hasattr(self, "record_search_input"):
            self.record_search_input.clear()
        self.update_header_labels()
        self.refresh_table()

    def filter_records_table(self, _query: str = "") -> None:
        """Filtra en tiempo real la tabla según la búsqueda y filtros activos."""
        self.refresh_table()

    def build_statistics(self) -> QWidget:
        """Construye la vista de análisis y estadísticas del registro activo."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
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
        return page

    def refresh_statistics(self) -> None:
        """Calcula y actualiza los indicadores de la pestaña de estadísticas."""
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

    def sync_location(self) -> None:
        """Actualiza el estado actual del ejercicio, sección e inciso en la UI."""
        location = SessionLocation(
            section_type=self.section_input.text().strip() or DEFAULT_SECTION_TYPE,
            section_number=self.section_number_input.value(),
            exercise=self.exercise_input.value(),
            inciso=self.inciso_input.value() or None,
        )
        self.application.set_location(location)

        suffix = f" · Inciso {location.inciso}" if location.inciso else ""
        text = f"{location.section_type} {location.section_number} · Ejercicio {location.exercise}{suffix}"
        self.location_label.setText(text)

    def set_locked(self, locked: bool) -> None:
        """Bloquea o desbloquea los controles de ubicación del ejercicio."""
        for widget in (self.section_input, self.section_number_input, self.exercise_input, self.inciso_input):
            widget.setEnabled(not locked)
        for btn in getattr(self, "stepper_buttons", []):
            btn.setEnabled(not locked)

    def toggle_session(self) -> None:
        """Inicia, pausa en receso o reanuda la sesión según su estado."""
        if self.application.mode is TimerMode.WAITING:
            self.sync_location()
            self.play_start_sound()
        self.application.toggle_session()

        self.set_locked(True)
        self.update_session_button()
        self.update_timer_visual_state()

    def update_session_button(self) -> None:
        """Actualiza el texto, icono y apariencia del control de sesión según el modo actual."""
        if self.application.mode is TimerMode.WAITING:
            self.session_button.setText("  INICIAR")
            self.session_button.setIcon(qta.icon("fa5s.play", color="#bef264"))
            self.session_button.setObjectName("hero_start")
        elif self.application.mode is TimerMode.PLAY:
            self.session_button.setText("  RECESO")
            self.session_button.setIcon(qta.icon("fa5s.pause", color="#b45309"))
            self.session_button.setObjectName("hero_pause")
        elif self.application.mode is TimerMode.BREAK:
            self.session_button.setText("  CONTINUAR")
            self.session_button.setIcon(qta.icon("fa5s.forward", color="#047857"))
            self.session_button.setObjectName("hero_resume")

        self.session_button.style().unpolish(self.session_button)
        self.session_button.style().polish(self.session_button)

    def stop_timer(self) -> None:
        """Detiene y descarta el conteo actual sin guardar un intento."""
        self.application.stop_session()
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        if hasattr(self, "comment_button"):
            self.comment_button.setText("  COMENTARIO")
            self.comment_button.setIcon(qta.icon("fa5s.comment-dots", color="#475569"))
        self.status_label.setText("Listo para comenzar")

    def finish_item(self, completed: bool, keep_location: bool = False, stop: bool = False) -> None:
        """Guarda el intento actual como item y limpia el estado del temporizador."""
        if self.application.mode is TimerMode.WAITING:
            return

        if completed:
            self.play_complete_sound()

        self.application.finish_item(completed)
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        result = "completo" if completed else "incompleto"
        self.status_label.setText(f"Intento {result}. Listo para comenzar")
        if hasattr(self, "comment_button"):
            self.comment_button.setText("  COMENTARIO")
            self.comment_button.setIcon(qta.icon("fa5s.comment-dots", color="#475569"))

        if not keep_location and not stop:
            self.sync_location()

        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()

        self.refresh_clock()
        self.refresh_table()

    def _check_boundary_permission(self, target_location: SessionLocation) -> bool:
        """Verifica si la ubicación excede la planificación y muestra aviso interactivo si es necesario."""
        is_ok, msg = self.application.check_location_boundary(target_location)
        if is_ok:
            return True

        from presentation.planner_dialogs import (
            ACTION_CANCEL,
            ACTION_CONTINUE,
            ACTION_GO_PLANNER,
            BoundaryWarningDialog,
        )

        dlg = BoundaryWarningDialog(self, msg, is_dark=self.is_dark_mode)
        dlg.exec()
        if dlg.result_action == ACTION_GO_PLANNER:
            self.tabs.setCurrentIndex(3)
            return False
        elif dlg.result_action == ACTION_CONTINUE:
            return True
        else:
            return False

    def _on_planner_load_timer(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None
    ) -> None:
        """Carga en el cronómetro la ubicación seleccionada desde el planificador."""
        if self.application.mode is not TimerMode.WAITING:
            confirm = QMessageBox.question(
                self,
                "Sesión activa en curso",
                "Hay una sesión activa en el cronómetro. ¿Deseas detenerla para cargar este ejercicio?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.stop_timer()

        self.section_input.setText(section_type)
        self.section_number_input.setValue(section_number)
        self.exercise_input.setValue(exercise)
        self.inciso_input.setValue(inciso or 0)
        self.sync_location()
        self.tabs.setCurrentIndex(0)

    def next_inciso(self) -> None:
        """Guarda el ejercicio actual y avanza al siguiente inciso."""
        target_loc = SessionLocation(
            section_type=self.section_input.text().strip() or DEFAULT_SECTION_TYPE,
            section_number=self.section_number_input.value(),
            exercise=self.exercise_input.value(),
            inciso=(self.inciso_input.value() or 0) + 1,
        )
        if not self._check_boundary_permission(target_loc):
            return

        was_active = self.application.mode is not TimerMode.WAITING
        if was_active:
            self.play_complete_sound()
        self.application.navigate("next_inciso")
        self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def previous_inciso(self) -> None:
        """Guarda el intento y vuelve al inciso anterior, si existe."""
        was_active = self.application.mode is not TimerMode.WAITING
        if self.application.navigate("previous_inciso"):
            if was_active:
                self.play_complete_sound()
            self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def next_exercise(self) -> None:
        """Guarda el ejercicio y pasa al siguiente ejercicio de la sección."""
        target_loc = SessionLocation(
            section_type=self.section_input.text().strip() or DEFAULT_SECTION_TYPE,
            section_number=self.section_number_input.value(),
            exercise=self.exercise_input.value() + 1,
            inciso=None,
        )
        if not self._check_boundary_permission(target_loc):
            return

        was_active = self.application.mode is not TimerMode.WAITING
        if was_active:
            self.play_complete_sound()
        self.application.navigate("next_exercise")
        self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def previous_exercise(self) -> None:
        """Guarda el intento y vuelve al ejercicio anterior, si existe."""
        was_active = self.application.mode is not TimerMode.WAITING
        if self.application.navigate("previous_exercise"):
            if was_active:
                self.play_complete_sound()
            self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def next_section(self) -> None:
        """Guarda el ejercicio actual y avanza a la siguiente sección."""
        target_loc = SessionLocation(
            section_type=self.section_input.text().strip() or DEFAULT_SECTION_TYPE,
            section_number=self.section_number_input.value() + 1,
            exercise=1,
            inciso=None,
        )
        if not self._check_boundary_permission(target_loc):
            return

        was_active = self.application.mode is not TimerMode.WAITING
        if was_active:
            self.play_complete_sound()
        self.application.navigate("next_section")
        self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def previous_section(self) -> None:
        """Guarda el intento y vuelve a la sección anterior, si existe."""
        was_active = self.application.mode is not TimerMode.WAITING
        if self.application.navigate("previous_section"):
            if was_active:
                self.play_complete_sound()
            self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()
        self.application.sync_planner_with_records()
        if hasattr(self, "planner"):
            self.planner.refresh_view()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def refresh_clock(self) -> None:
        """Actualiza los labels con los tiempos actuales del cronómetro."""
        exercise_ms, break_ms = self.application.timer.snapshot()
        self.exercise_clock.setText(timer_markup(exercise_ms))
        self.break_clock.setText(timer_markup(break_ms))
        self.update_timer_visual_state()

        today_ms = self.application.get_today_study_time_ms(include_current=True)
        self.today_study_label.setText(format_hh_mm_ss(today_ms))

    def update_timer_visual_state(self) -> None:
        """Aplica el estilo digital de alta precisión a la lectura según su modo."""
        compact = self.width() < 1000
        clock_size = 38 if compact else 48
        break_size = 20 if compact else 25
        is_dark = self.is_dark_mode

        if self.application.mode is TimerMode.PLAY:
            if hasattr(self, "exercise_card"):
                self.exercise_card.setStyleSheet("QFrame#exerciseCard { background: #071510; border: 2px solid #10b981; border-radius: 14px; }")
                self.break_card.setStyleSheet("QFrame#breakCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }")
            self.exercise_clock.setStyleSheet(f"color: #34d399; font-size: {clock_size}px; font-weight: 800;")
            self.break_clock.setStyleSheet(f"color: #64748b; font-size: {break_size}px; font-weight: 700;")
            if hasattr(self, "status_pill"):
                self.status_pill.setText(" ●  SESIÓN EN CURSO")
                if is_dark:
                    self.status_pill.setStyleSheet("background: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
                else:
                    self.status_pill.setStyleSheet("background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
            self.status_label.setText("Sesión en curso")
        elif self.application.mode is TimerMode.BREAK:
            if hasattr(self, "exercise_card"):
                self.exercise_card.setStyleSheet("QFrame#exerciseCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }")
                self.break_card.setStyleSheet("QFrame#breakCard { background: #191408; border: 2px solid #f59e0b; border-radius: 14px; }")
            self.exercise_clock.setStyleSheet(f"color: #64748b; font-size: {clock_size}px; font-weight: 800;")
            self.break_clock.setStyleSheet(f"color: #fbbf24; font-size: {break_size}px; font-weight: 700;")
            if hasattr(self, "status_pill"):
                self.status_pill.setText(" ●  RECESO EN CURSO")
                if is_dark:
                    self.status_pill.setStyleSheet("background: #451a03; color: #fde68a; border: 1px solid #78350f; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
                else:
                    self.status_pill.setStyleSheet("background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
            self.status_label.setText("Receso en curso")
        else:
            if hasattr(self, "exercise_card"):
                self.exercise_card.setStyleSheet("QFrame#exerciseCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }")
                self.break_card.setStyleSheet("QFrame#breakCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }")
            self.exercise_clock.setStyleSheet(f"color: #e2e8f0; font-size: {clock_size}px; font-weight: 800;")
            self.break_clock.setStyleSheet(f"color: #64748b; font-size: {break_size}px; font-weight: 700;")
            if hasattr(self, "status_pill"):
                self.status_pill.setText(" ●  LISTO PARA COMENZAR")
                if is_dark:
                    self.status_pill.setStyleSheet("background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
                else:
                    self.status_pill.setStyleSheet("background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;")
            self.status_label.setText("Listo para comenzar")

    def autosave(self) -> None:
        """Guarda el registro activo en el archivo asociado."""
        self.application.save()

    def prompt_initial_record_choice(self) -> None:
        """Pregunta al usuario si debe crear un registro nuevo o abrir uno existente."""
        import os
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or os.environ.get("STUDY_TIMETRIAL_TEST"):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Study Timetrial")
        dialog.setModal(True)
        dialog.setMinimumWidth(560)
        dialog.setStyleSheet(get_dialog_stylesheet(self.current_theme))

        layout = QVBoxLayout(dialog)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 22, 24, 20)

        header = QHBoxLayout()
        title = QLabel("Study Timetrial")
        title.setObjectName("title")
        version = QLabel(APP_VERSION)
        version.setObjectName("version")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(version)
        layout.addLayout(header)

        subtitle = QLabel("Puede crear un archivo nuevo o abrir un registro reciente.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        recent_paths = self.application.storage.recent_files.paths
        recent_list = QListWidget()
        recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        if recent_paths:
            for path in recent_paths[:5]:
                if path.exists():
                    recent_list.addItem(f"{path.name} — {path.parent}")
                    item = recent_list.item(recent_list.count() - 1)
                    item.setData(Qt.ItemDataRole.UserRole, str(path))
        else:
            recent_list.addItem("No hay archivos recientes todavía")
            recent_list.setEnabled(False)
        recent_list.itemDoubleClicked.connect(
            lambda item: self._handle_initial_choice(
                dialog, "recent", item.data(Qt.ItemDataRole.UserRole)
            )
        )
        layout.addWidget(recent_list)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        new_button = QPushButton("  Nuevo archivo")
        new_button.setIcon(qta.icon("fa5s.plus", color="#090d16" if self.is_dark_mode else "#bef264"))
        new_button.setObjectName("primary")
        new_button.clicked.connect(lambda: self._handle_initial_choice(dialog, "new"))

        open_button = QPushButton("  Abrir archivo")
        open_button.setIcon(qta.icon("fa5s.folder-open", color="#cbd5e1" if self.is_dark_mode else "#334155"))
        open_button.setObjectName("secondary")
        open_button.clicked.connect(
            lambda: self._handle_initial_choice(
                dialog,
                "open",
                recent_list.currentItem().data(Qt.ItemDataRole.UserRole)
                if recent_list.currentItem() is not None
                else None,
            )
        )

        cancel_button = QPushButton("Cancelar")
        cancel_button.setObjectName("ghost")
        cancel_button.clicked.connect(lambda: self._handle_initial_choice(dialog, "cancel"))

        buttons.addWidget(new_button)
        buttons.addWidget(open_button)
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        dialog.exec()

    def _handle_initial_choice(self, dialog: QDialog, choice: str, recent_path: str | None = None) -> None:
        """Procesa la opción seleccionada en el diálogo de inicio."""
        default_name = self.application.record.record_name or "StudyTimetrial"

        if choice == "recent":
            if recent_path is not None:
                candidate = Path(recent_path)
                if candidate.exists():
                    self.application.load(candidate)
                    self.update_title()
                    self.refresh_table()
                    self.refresh_recent_files_menu()
                    dialog.accept()
                    return
            dialog.reject()
            return

        if choice == "new":
            name, accepted = QInputDialog.getText(
                self,
                "Nuevo archivo",
                "Nombre del archivo:",
                QLineEdit.EchoMode.Normal,
                default_name,
            )
            if accepted:
                self.application.new_record(name.strip() or default_name)
            else:
                self.application.new_record(default_name)
            self.refresh_table()
            dialog.accept()
            return

        if choice == "open":
            dialog.reject()
            if recent_path is not None:
                self.open_recent_record(recent_path)
            else:
                self.open_record()
            return

        self.application.new_record(default_name)
        self.refresh_table()
        dialog.accept()

    def new_record(self) -> None:
        """Solicita un nombre y crea un archivo de registro nuevo."""
        default_name = self.application.record.record_name or "StudyTimetrial"
        name, accepted = QInputDialog.getText(
            self,
            "Nuevo archivo",
            "Nombre del archivo:",
            QLineEdit.EchoMode.Normal,
            default_name,
        )
        if not accepted:
            return

        self.application.new_record(name.strip() or default_name)
        self.update_title()
        self.refresh_table()

    def update_title(self) -> None:
        """Actualiza el título de la ventana según el archivo de registro abierto."""
        if self.application.is_record_open and self.application.record_path:
            file_name = self.application.record_path.stem
            self.home_title.setText(file_name)
            self.setWindowTitle(f"{APP_TITLE} - {file_name}")
        else:
            name = self.application.record.record_name or APP_TITLE
            self.home_title.setText(name)
            self.setWindowTitle(f"{APP_TITLE} - {name}")

    def refresh_table(self) -> None:
        """Vuelca a pintar la tabla con los registros filtrados y ordenados estilo Excel."""
        all_items = self.application.record.items
        active_sorts = self.get_active_sorts_by_hierarchy()
        search_text = self.record_search_input.text() if hasattr(self, "record_search_input") else ""

        # Construir mapa de valores posibles para cada columna
        all_col_values = {}
        for col_key in self.LOGICAL_COL_KEYS.values():
            all_col_values[col_key] = {val for val, _ in get_column_unique_values(all_items, col_key)}

        self._current_displayed_items = apply_column_filters_and_sort(
            all_items,
            column_filters=self.column_filter_rules,
            active_sorts_ordered=active_sorts,
            global_query=search_text,
            all_column_values_map=all_col_values,
        )

        self.table.setRowCount(0)
        total_items = len(all_items)
        displayed_count = len(self._current_displayed_items)

        has_active_filters = (
            any(rule.is_active(all_col_values.get(k)) for k, rule in self.column_filter_rules.items())
            or bool(self.column_sort_states)
            or bool(search_text.strip())
        )
        if hasattr(self, "clear_all_filters_btn"):
            self.clear_all_filters_btn.setVisible(has_active_filters)

        if displayed_count != total_items:
            self.records_summary.setText(f"Mostrando {displayed_count} de {total_items} intento{'s' if total_items != 1 else ''} (filtrado)")
        else:
            self.records_summary.setText(f"{total_items} intento{'s' if total_items != 1 else ''} guardado{'s' if total_items != 1 else ''}")

        if hasattr(self, "planner"):
            self.planner.refresh_view()

        # Update KPI cards
        stats = self.application.get_statistics()
        if hasattr(self, "rec_stat_attempts"):
            self.rec_stat_attempts.setText(str(stats.total_attempts))
            self.rec_stat_exercise_time.setText(format_hh_mm(stats.total_exercise_time_ms))
            self.rec_stat_break_time.setText(format_hh_mm(stats.total_break_time_ms))
            eff_pct = int(round((stats.completed_attempts / stats.total_attempts * 100.0))) if stats.total_attempts else 0
            self.rec_stat_effectiveness.setText(f"{eff_pct}%")

        for index, item in enumerate(self._current_displayed_items):
            self.table.insertRow(index)
            self.table.setRowHeight(index, 38)

            location_text = f"{item.section_type} {item.section_number}"
            loc_item = QTableWidgetItem(location_text)
            loc_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(index, 0, loc_item)

            ex_item = QTableWidgetItem(str(item.exercise))
            ex_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 1, ex_item)

            inc_item = QTableWidgetItem(str(item.inciso or "-"))
            inc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 2, inc_item)

            # Columna 3: Fecha
            try:
                dt_obj = datetime.fromisoformat(item.created_at)
                date_str = dt_obj.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = item.created_at[:16] if len(item.created_at) >= 16 else item.created_at
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 3, date_item)

            br_item = QTableWidgetItem(format_milliseconds(item.break_time_ms))
            br_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 4, br_item)

            t_item = QTableWidgetItem(format_milliseconds(item.exercise_time_ms))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(index, 5, t_item)

            # Columna 6: Estado badge
            status_badge = QLabel("✓ Completado" if item.completed else "✕ Incompleto")
            status_badge.setObjectName("table_badge_completed" if item.completed else "table_badge_incomplete")
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(index, 6, status_badge)

            # Columna 7: Comentario
            comm_item = QTableWidgetItem(item.comment)
            comm_item.setToolTip(item.comment or "Sin comentario")
            self.table.setItem(index, 7, comm_item)

            # Botones de acción compactos con iconos y tooltips
            comm_btn = QPushButton()
            comm_btn.setIcon(qta.icon("fa5s.comment-dots", color="#3b82f6"))
            comm_btn.setObjectName("table_action_icon")
            comm_btn.setToolTip("Comentar registro")
            comm_btn.clicked.connect(lambda _, it=item: self.comment_item(it))
            self.table.setCellWidget(index, 8, comm_btn)

            edit_btn = QPushButton()
            edit_btn.setIcon(qta.icon("fa5s.edit", color="#6366f1"))
            edit_btn.setObjectName("table_action_icon")
            edit_btn.setToolTip("Editar registro")
            edit_btn.clicked.connect(lambda _, it=item: self.edit_item(it))
            self.table.setCellWidget(index, 9, edit_btn)

            reset_btn = QPushButton()
            reset_btn.setIcon(qta.icon("fa5s.redo-alt", color="#f59e0b"))
            reset_btn.setObjectName("table_action_icon")
            reset_btn.setToolTip("Reiniciar tiempo")
            reset_btn.clicked.connect(lambda _, it=item: self.reset_item(it))
            self.table.setCellWidget(index, 10, reset_btn)

            del_btn = QPushButton()
            del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#ef4444"))
            del_btn.setObjectName("table_delete_icon")
            del_btn.setToolTip("Eliminar registro")
            del_btn.clicked.connect(lambda _, it=item: self.delete_item(it))
            self.table.setCellWidget(index, 11, del_btn)

        self.refresh_statistics()

    def show_comment_alert(self, row: int, column: int) -> None:
        """Muestra el comentario completo al hacer click en su celda."""
        if column != 7:
            return

        if row < len(self._current_displayed_items):
            item = self._current_displayed_items[row]
            QMessageBox.information(
                self,
                "Comentario del registro",
                item.comment or "Este registro no tiene comentario.",
            )

    def add_home_comment(self) -> None:
        """Captura el comentario que se guardará al finalizar el intento actual."""
        comment, accepted = QInputDialog.getMultiLineText(
            self,
            "Comentario del intento",
            "Comentario:",
            self.application.pending_comment,
        )
        if accepted:
            self.application.set_comment(comment)
            clean = comment.strip()
            if clean:
                short = (clean[:25] + "…") if len(clean) > 25 else clean
                self.comment_button.setText(f"  COMENTARIO: \"{short}\"")
                self.comment_button.setIcon(qta.icon("fa5s.comment-dots", color="#10b981"))
            else:
                self.comment_button.setText("  COMENTARIO")
                self.comment_button.setIcon(qta.icon("fa5s.comment-dots", color="#475569"))
            self.status_label.setText("Comentario preparado para el próximo registro")

    def comment_item(self, target: int | TimerItem) -> None:
        """Agrega o edita el comentario de un registro existente."""
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        comment, accepted = QInputDialog.getMultiLineText(
            self,
            "Comentario del registro",
            "Comentario:",
            item.comment,
        )
        if accepted:
            self.application.update_comment(item, comment)
            self.refresh_table()

    def add_item(self) -> None:
        """Añade un item manualmente desde el diálogo de edición."""
        dialog = ItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.validated_item is not None:
                self.application.add_item(dialog.validated_item)
            self.refresh_table()

    def edit_item(self, target: int | TimerItem) -> None:
        """Edita un item existente."""
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        dialog = ItemDialog(self, item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.validated_item is not None:
                self.application.replace_item(item, dialog.validated_item)
            self.refresh_table()

    def reset_item(self, target: int | TimerItem) -> None:
        """Reinicia el tiempo de un item concreto."""
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        if QMessageBox.question(
            self,
            "Confirmar reset",
            "¿Está seguro de reiniciar este registro?",
        ) == QMessageBox.StandardButton.Yes:
            self.application.reset_item(item)
            self.refresh_table()

    def delete_item(self, target: int | TimerItem) -> None:
        """Elimina un item concreto tras confirmar la acción."""
        item = target if isinstance(target, TimerItem) else (
            self._current_displayed_items[target] if target < len(self._current_displayed_items)
            else self.application.ordered_items()[target]
        )
        if QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro de eliminar este registro?\nEsta acción no se puede deshacer.",
        ) == QMessageBox.StandardButton.Yes:
            self.application.delete_item(item)
            self.refresh_table()

    def refresh_recent_files_menu(self) -> None:
        """Actualiza el menú de archivos recientes con los últimos registros accesibles."""
        self.recent_files_menu.clear()
        recent_paths = self.application.storage.recent_files.paths

        open_action = QAction("Abrir archivo…", self)
        open_action.setIcon(qta.icon("fa5s.folder-open", color="#334155"))
        open_action.triggered.connect(self.open_record)
        self.recent_files_menu.addAction(open_action)

        if not recent_paths:
            empty_action = QAction("No hay archivos recientes", self)
            empty_action.setEnabled(False)
            self.recent_files_menu.addAction(empty_action)
            return

        self.recent_files_menu.addSeparator()
        for path in recent_paths:
            if not path.exists():
                continue
            action = QAction(f"{path.name} — {path.parent}", self)
            action.setIcon(qta.icon("fa5s.file", color="#64748b"))
            action.triggered.connect(lambda _checked, selected=path: self.open_recent_record(selected))
            self.recent_files_menu.addAction(action)

    def open_recent_record(self, path: str | Path) -> None:
        """Abre un archivo reciente desde la lista guardada."""
        target = Path(path)
        if not target.exists():
            QMessageBox.warning(self, "Archivo no encontrado", f"No se pudo abrir: {target}")
            return
        try:
            self.application.load(target)
            self.update_title()
            self.refresh_table()
            self.refresh_recent_files_menu()
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Archivo inválido", str(error))

    def open_record(self) -> None:
        """Abre un fichero JSON para cargar un registro existente."""
        if self.application.is_record_open and (self.application.record.items or self.application.mode is not TimerMode.WAITING):
            QMessageBox.warning(
                self,
                "Registro abierto",
                "Ya existe un registro abierto. Cierre el registro actual antes de abrir otro.",
            )
            return

        path, _ = QFileDialog.getOpenFileName(self, "Abrir registro", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return

        try:
            self.application.load(Path(path))
            self.update_title()
            self.refresh_table()
            self.refresh_recent_files_menu()
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Archivo inválido", str(error))

    def import_records(self) -> None:
        """Selecciona y añade items individuales desde otro registro JSON."""
        path, _ = QFileDialog.getOpenFileName(self, "Importar registros", str(Path.cwd()), "JSON (*.json)")
        if not path:
            return

        try:
            source_record = self.application.storage.read(Path(path))
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Archivo inválido", str(error))
            return

        if not source_record.items:
            QMessageBox.information(self, "Sin registros", "El archivo seleccionado no contiene registros.")
            return

        dialog = ImportRecordsDialog(source_record, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected_indexes = dialog.selected_indexes()
        if not selected_indexes:
            QMessageBox.information(self, "Sin selección", "Selecciona al menos un registro para importar.")
            return

        try:
            imported_count = self.application.import_items(Path(path), selected_indexes)
        except (OSError, TypeError, ValueError, IndexError) as error:
            QMessageBox.critical(self, "No se pudieron importar los registros", str(error))
            return

        self.refresh_table()
        self.update_title()
        QMessageBox.information(self, "Importación completada", f"Se importaron {imported_count} registros.")

    def save_as(self) -> None:
        """Guarda el registro actual en una ruta distinta indicada por el usuario."""
        default = str(self.application.record_path or Path.cwd() / "StudyTimetrial.json")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar registro", default, "JSON (*.json)")
        if path:
            self.application.save_as(Path(path))
            self.update_title()

    def rename_record(self) -> None:
        """Renombra el fichero activo del registro."""
        if self.application.record_path is None:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Renombrar registro", str(self.application.record_path), "JSON (*.json)")
        if not path:
            return

        new_path = Path(path)
        try:
            self.application.rename(new_path)
        except OSError as error:
            QMessageBox.critical(self, "No se pudo renombrar", str(error))
            return

        self.update_title()

    def close_record(self) -> None:
        """Cierra el registro activo y crea uno nuevo en memoria."""
        if QMessageBox.question(self, "Cerrar registro", "¿Desea cerrar el registro actual?") != QMessageBox.StandardButton.Yes:
            return

        self.application.close_record()
        self.update_title()
        self.refresh_table()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Confirma antes de cerrar si hay un intento activo en curso."""
        if self.application.mode is TimerMode.WAITING:
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "Intento en curso",
            "Hay un intento en curso.\n¿Desea guardar la información antes de salir?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        )

        if answer is QMessageBox.StandardButton.Save:
            self.finish_item(False, stop=True)
            event.accept()
        elif answer is QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()
