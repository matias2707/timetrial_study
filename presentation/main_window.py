"""Composicion de la interfaz Qt y adaptacion de eventos de usuario.

La ventana presenta el estado de `StudyApplicationService`; no contiene reglas
de persistencia ni construye directamente el formato de los datos guardados.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QBrush, QCloseEvent, QColor, QFont, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
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

from application.application_service import SessionLocation, StudyApplicationService
from application.statistics_service import DailyStatistic
from domain.timer_service import TimerMode
from presentation.presentation_dialogs import ImportRecordsDialog, ItemDialog
from presentation.presentation_formatters import (
    format_hh_mm,
    format_hh_mm_ss,
    format_milliseconds,
    timer_markup,
)

DEFAULT_SECTION_TYPE = "Guía"
APP_TITLE = "Study Timetrial"
APP_VERSION = "v1.0"
MAX_VALUE = 999_999


class WeeklyChartWidget(QWidget):
    """Componente visual que renderiza las barras de horas de estudio para 7 días."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.daily_stats: list[DailyStatistic] = []
        self.setMinimumHeight(175)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_stats(self, daily_stats: list[DailyStatistic]) -> None:
        self.daily_stats = daily_stats
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

        for i, stat in enumerate(self.daily_stats):
            center_x = i * col_width + (col_width / 2.0)
            bar_x = center_x - (bar_width / 2.0)

            bg_rect = QRectF(bar_x, top_margin, bar_width, available_bar_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#edf3ed")))
            painter.drawRoundedRect(bg_rect, 6.0, 6.0)

            if stat.exercise_time_ms > 0:
                ratio = min(1.0, stat.exercise_time_ms / max_ms)
                bar_h = max(8.0, ratio * available_bar_height)
                bar_y = height - bottom_margin - bar_h
                bar_rect = QRectF(bar_x, bar_y, bar_width, bar_h)
                painter.setBrush(QBrush(QColor("#9abb3c")))
                painter.drawRoundedRect(bar_rect, 6.0, 6.0)

            time_text = format_hh_mm(stat.exercise_time_ms)
            font_time = QFont()
            font_time.setPointSize(9)
            font_time.setBold(True)
            painter.setFont(font_time)
            painter.setPen(QColor("#17242a" if stat.exercise_time_ms > 0 else "#8b9b97"))
            time_rect = QRectF(center_x - (col_width / 2.0), top_margin - 24.0, col_width, 18.0)
            painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_text)

            font_day = QFont()
            font_day.setPointSize(9)
            font_day.setBold(True)
            painter.setFont(font_day)
            painter.setPen(QColor("#17242a"))
            day_rect = QRectF(center_x - (col_width / 2.0), height - bottom_margin + 5.0, col_width, 16.0)
            painter.drawText(day_rect, Qt.AlignmentFlag.AlignCenter, stat.day_name)

            font_date = QFont()
            font_date.setPointSize(8)
            painter.setFont(font_date)
            painter.setPen(QColor("#75827f"))
            date_rect = QRectF(center_x - (col_width / 2.0), height - bottom_margin + 22.0, col_width, 14.0)
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, stat.date_str)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación Study Timetrial."""

    STYLESHEET = """
        QWidget { background: #f3f6f1; color: #1f2a2d; font-size: 14px; }
        QMainWindow { background: #edf3ee; }
        QTabWidget::pane { border: none; background: #edf3ee; }
        QTabBar { background: #16252d; border: none; }
        QTabBar::tab { background: #16252d; color: #a8b8b4; padding: 14px 26px; border: none; font-weight: 700; min-width: 140px; }
        QTabBar::tab:selected { color: #d9f76d; border-bottom: 3px solid #d9f76d; }
        QTabBar::tab:hover { color: #edf5c0; }
        QLabel#brand { color: #17242a; font-size: 28px; font-weight: 800; letter-spacing: 0.6px; }
        QLabel#eyebrow { color: #788886; font-size: 11px; font-weight: 800; letter-spacing: 1.4px; }
        QLabel#record_meta { color: #667b7a; font-size: 12px; font-weight: 700; }
        QLabel#location { color: #1b2c32; font-size: 28px; font-weight: 800; qproperty-alignment: AlignCenter; }
        QLabel#status { color: #546a68; font-size: 13px; font-weight: 600; }
        QFrame#heroCard, QFrame#metricCard, QFrame#sectionCard, QFrame#panelCard { background: #ffffff; border: 1px solid #dfe7e1; border-radius: 16px; }
        QFrame#heroCard { border-top: 4px solid #d9f76d; }
        QFrame#metricCard { padding: 4px; }
        QLabel#metric_label { color: #75827f; font-size: 11px; font-weight: 800; letter-spacing: 1.2px; qproperty-alignment: AlignCenter; }
        QLabel#metric_value { color: #17242a; font-size: 43px; font-weight: 800; qproperty-alignment: AlignCenter; }
        QLabel#break_label { color: #75827f; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; qproperty-alignment: AlignCenter; }
        QLabel#break_value { color: #60706d; font-size: 22px; font-weight: 700; qproperty-alignment: AlignCenter; }
        QLineEdit, QSpinBox { background: #fbfcfa; border: 1px solid #cad4cf; border-radius: 10px; padding: 10px 11px; min-height: 22px; }
        QLineEdit:focus, QSpinBox:focus { border: 2px solid #9abb3c; padding: 9px 10px; }
        QLineEdit:disabled, QSpinBox:disabled { background: #edf1ed; color: #77827f; }
        QPushButton { background: #ffffff; color: #22333a; border: 1px solid #cbd7d2; border-radius: 10px; padding: 9px 14px; font-size: 12px; font-weight: 700; }
        QPushButton:hover { border-color: #9abb3c; background: #f4f8e9; }
        QPushButton:pressed { background: #ebf3d0; }
        QPushButton#primary { background: #17242a; color: #d9f76d; border: 1px solid #17242a; font-weight: 800; padding: 10px 18px; }
        QPushButton#primary:hover { background: #273e45; }
        QPushButton#complete { background: #eaf6ea; color: #236c39; border: 1px solid #abd4b7; font-weight: 800; }
        QPushButton#complete:hover { background: #daf0da; border-color: #7bbe8f; color: #174e27; }
        QPushButton#complete:pressed { background: #cce9cc; }
        QPushButton#break { color: #b27722; border-color: #efc98a; }
        QPushButton#danger { color: #b04642; border-color: #eab8b1; }
        QPushButton#stop { color: #b04642; border-color: #eab8b1; }
        QPushButton#nav_button { background: #fbfdfa; color: #22333a; border: 1px solid #cad7d2; border-radius: 9px; padding: 8px 12px; font-size: 12px; font-weight: 700; }
        QPushButton#nav_button:hover { border-color: #9abb3c; background: #f4f8e9; color: #17242a; }
        QPushButton#nav_button:pressed { background: #ebf3d0; }
        QPushButton#nav_button:disabled { background: #edf1ed; color: #8c9c98; border-color: #dbe3df; }
        QPushButton#comment_action { background: #f9fbf9; color: #2d3e42; border: 1px solid #ccd8d2; border-radius: 9px; padding: 9px 14px; font-size: 12px; font-weight: 700; }
        QPushButton#comment_action:hover { background: #edf4ed; border-color: #9abb3c; }
        QPushButton#toolbar_primary { background: #d9f76d; color: #17242a; border: none; }
        QPushButton#secondary_action { background: #f5f8f5; }
        QPushButton#table_action { background: #f0f5ed; border-color: #dfe7df; padding: 6px 9px; }
        QPushButton#table_delete { background: #fff3f1; color: #b04642; border-color: #efc4be; padding: 6px 9px; }
        QFrame#todayCard { background: #ffffff; border: 1px solid #cad7cf; border-radius: 12px; }
        QLabel#today_icon { font-size: 16px; }
        QLabel#today_label { color: #75827f; font-size: 10px; font-weight: 800; letter-spacing: 1px; }
        QLabel#today_value { color: #17242a; font-size: 17px; font-weight: 800; }
        QLabel#section_title { color: #17242a; font-size: 15px; font-weight: 700; }
        QTableWidget { background: #ffffff; border: 1px solid #dfe7e1; border-radius: 12px; gridline-color: #edf1ed; alternate-background-color: #f9fbf8; selection-background-color: #e9f2d5; selection-color: #17242a; }
        QHeaderView::section { background: #eef4ee; color: #617877; border: none; border-bottom: 1px solid #dfe7e1; padding: 11px 8px; font-size: 11px; font-weight: 800; }
        QTableWidget QPushButton { padding: 6px 8px; font-size: 11px; }
        QCheckBox { spacing: 8px; }
        QProgressBar { background: #edf1ed; border: 1px solid #dfe7e1; border-radius: 8px; text-align: center; color: #17242a; font-weight: 700; font-size: 11px; min-height: 20px; }
        QProgressBar::chunk { background: #d9f76d; border-radius: 7px; }
        QScrollArea#statsScroll { background: transparent; border: none; }
        QWidget#statsContainer { background: transparent; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.application = StudyApplicationService()
        self.start_sound_player = QMediaPlayer(self)
        self.start_sound_output = QAudioOutput(self)
        self.start_sound_player.setAudioOutput(self.start_sound_output)
        sound_path = Path(__file__).resolve().parent / "media" / "start_sound.mp3"
        self.start_sound_player.setSource(QUrl.fromLocalFile(str(sound_path)))

        self.setMinimumSize(900, 700)
        self.setStyleSheet(self.STYLESHEET)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.home = self.build_home()
        self.records = self.build_records()
        self.statistics = self.build_statistics()
        self.tabs.addTab(self.home, "Cronómetro")
        self.tabs.addTab(self.records, "Registros")
        self.tabs.addTab(self.statistics, "Estadisticas")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.build_main_toolbar()

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.refresh_clock)
        self.tick.start(50)

        self.prompt_initial_record_choice()
        self.update_title()
        self.refresh_statistics()
        self.autosave()

    def _on_tab_changed(self, index: int) -> None:
        """Actualiza la vista correspondiente cuando el usuario cambia de pestaña."""
        if index == 1:
            self.refresh_table()
        elif index == 2:
            self.refresh_statistics()

    def build_main_toolbar(self) -> None:
        """Construye el toolbar principal con las acciones de archivo."""
        toolbar = QToolBar("Barra principal", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        file_menu = QMenu("Archivo", self)
        new_action = QAction("Nuevo archivo", self)
        new_action.triggered.connect(self.new_record)
        file_menu.addAction(new_action)

        open_action = QAction("Abrir archivo", self)
        open_action.triggered.connect(self.open_record)
        file_menu.addAction(open_action)

        recent_action = QAction("Reciente", self)
        recent_action.setMenu(self.recent_files_menu)
        file_menu.addAction(recent_action)

        save_action = QAction("Guardar como", self)
        save_action.triggered.connect(self.save_as)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        close_file_action = QAction("Cerrar archivo", self)
        close_file_action.triggered.connect(self.close_record)
        file_menu.addAction(close_file_action)

        close_program_action = QAction("Cerrar programa", self)
        close_program_action.triggered.connect(self.close)
        file_menu.addAction(close_program_action)

        file_button = QToolButton(toolbar)
        file_button.setObjectName("file_toolbar_button")
        file_button.setText("Archivo")
        file_button.setMenu(file_menu)
        file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        file_button.setStyleSheet("QToolButton#file_toolbar_button::menu-indicator { image: none; }")
        toolbar.addWidget(file_button)

    def build_home(self) -> QWidget:
        """Construye la vista del cronómetro."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(48, 28, 48, 38)
        outer.setSpacing(18)

        top = QHBoxLayout()
        self.home_title = QLabel(APP_TITLE)
        self.home_title.setObjectName("brand")
        top.addWidget(self.home_title)
        top.addStretch()

        today_card = QFrame()
        today_card.setObjectName("todayCard")
        today_layout = QHBoxLayout(today_card)
        today_layout.setContentsMargins(14, 6, 16, 6)
        today_layout.setSpacing(10)

        today_icon = QLabel("⏱")
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
        top.addSpacing(14)

        record_meta = QLabel("REGISTRO LOCAL  ·  SIN SERVIDOR")
        record_meta.setObjectName("record_meta")
        top.addWidget(record_meta)
        outer.addLayout(top)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 24)
        hero_layout.setSpacing(16)

        eyebrow = QLabel("UBICACIÓN ACTUAL")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)

        self.location_label = QLabel()
        self.location_label.setObjectName("location")
        self.location_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.location_label.setWordWrap(True)
        hero_layout.addWidget(self.location_label)

        selectors = QGridLayout()
        selectors.setHorizontalSpacing(12)
        selectors.setVerticalSpacing(8)
        self.section_input = QLineEdit(DEFAULT_SECTION_TYPE)
        self.section_input.setPlaceholderText("Tipo de sección")
        self.section_number_input = QSpinBox(); self.section_number_input.setRange(1, MAX_VALUE); self.section_number_input.setValue(1)
        self.exercise_input = QSpinBox(); self.exercise_input.setRange(1, MAX_VALUE); self.exercise_input.setValue(1)
        self.inciso_input = QSpinBox(); self.inciso_input.setRange(0, MAX_VALUE); self.inciso_input.setSpecialValueText("Sin inciso")

        self.section_input.textChanged.connect(self.sync_location)
        self.section_number_input.valueChanged.connect(self.sync_location)
        self.exercise_input.valueChanged.connect(self.sync_location)
        self.inciso_input.valueChanged.connect(self.sync_location)

        for column, (label, widget) in enumerate((
            ("Sección", self.section_input), ("Nº", self.section_number_input),
            ("Ejercicio", self.exercise_input), ("Inciso", self.inciso_input),
        )):
            field_label = QLabel(label.upper())
            field_label.setObjectName("eyebrow")
            selectors.addWidget(field_label, 0, column)
            selectors.addWidget(widget, 1, column)
        selectors.setColumnStretch(0, 2)
        for column in range(1, 4):
            selectors.setColumnStretch(column, 1)
        hero_layout.addLayout(selectors)
        outer.addWidget(hero)

        metrics = QHBoxLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setSpacing(12)
        metrics.setStretch(0, 3)
        metrics.setStretch(1, 2)
        self.metrics_layout = metrics
        self.exercise_clock = QLabel(timer_markup(0))
        self.break_clock = QLabel(timer_markup(0))
        for clock in (self.exercise_clock, self.break_clock):
            clock.setTextFormat(Qt.TextFormat.RichText)
            clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            clock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        exercise_card = QFrame(); exercise_card.setObjectName("metricCard")
        exercise_layout = QVBoxLayout(exercise_card); exercise_layout.setContentsMargins(20, 14, 20, 15); exercise_layout.setSpacing(3)
        exercise_label = QLabel("TIEMPO EJERCICIO"); exercise_label.setObjectName("metric_label")
        self.exercise_clock.setObjectName("metric_value")
        exercise_layout.addWidget(exercise_label); exercise_layout.addWidget(self.exercise_clock)
        metrics.addWidget(exercise_card)

        break_card = QFrame(); break_card.setObjectName("metricCard")
        break_layout = QVBoxLayout(break_card); break_layout.setContentsMargins(20, 8, 20, 10); break_layout.setSpacing(2)
        break_label = QLabel("RECESO ACUMULADO"); break_label.setObjectName("break_label")
        self.break_clock.setObjectName("break_value")
        break_layout.addWidget(break_label); break_layout.addWidget(self.break_clock)
        metrics.addWidget(break_card)
        outer.addLayout(metrics)

        controls_card = QFrame(); controls_card.setObjectName("sectionCard")
        controls_layout = QVBoxLayout(controls_card); controls_layout.setContentsMargins(18, 16, 18, 18); controls_layout.setSpacing(16)
        controls_title = QLabel("CONTROLES DE SESIÓN"); controls_title.setObjectName("eyebrow")
        controls_layout.addWidget(controls_title)

        primary_controls = QGridLayout(); primary_controls.setHorizontalSpacing(10); primary_controls.setVerticalSpacing(8)
        self.primary_controls = primary_controls
        self.session_button = QPushButton("INICIAR"); self.session_button.setObjectName("primary"); self.session_button.clicked.connect(self.toggle_session)
        stop = QPushButton("DETENER"); stop.setObjectName("stop"); stop.clicked.connect(self.stop_timer)
        incomplete = QPushButton("INCOMPLETO"); incomplete.setObjectName("danger"); incomplete.clicked.connect(lambda: self.finish_item(False, keep_location=True))
        complete = QPushButton("COMPLETO"); complete.setObjectName("complete"); complete.clicked.connect(lambda: self.finish_item(True, keep_location=True))
        self.primary_buttons = (self.session_button, stop, complete, incomplete)
        for column, button in enumerate(self.primary_buttons):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            primary_controls.addWidget(button, 0 if column < 2 else 1, column % 2)
        controls_layout.addLayout(primary_controls)

        comment_button = QPushButton("COMENTARIO")
        comment_button.setObjectName("comment_action")
        comment_button.clicked.connect(self.add_home_comment)
        controls_layout.addWidget(comment_button)

        navigation = QGridLayout(); navigation.setHorizontalSpacing(10); navigation.setVerticalSpacing(8)
        self.navigation = navigation
        self.navigation_buttons = []
        for text, callback in (
            ("◀ Anterior Inciso", self.previous_inciso),
            ("Siguiente Inciso ▶", self.next_inciso),
            ("◀ Anterior Ejercicio", self.previous_exercise),
            ("Siguiente Ejercicio ▶", self.next_exercise),
            ("◀ Anterior Sección", self.previous_section),
            ("Siguiente Sección ▶", self.next_section),
        ):
            button = QPushButton(text)
            button.setObjectName("nav_button")
            button.clicked.connect(callback)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.navigation_buttons.append(button)
        self._populate_grid(self.primary_controls, self.primary_buttons, 2)
        self._populate_grid(self.navigation, self.navigation_buttons, 2)
        controls_layout.addLayout(navigation)
        self.status_label = QLabel("Listo para comenzar")
        self.status_label.setObjectName("status")
        controls_layout.addWidget(self.status_label)
        outer.addWidget(controls_card)
        outer.addStretch()
        self.sync_location()
        return page

    @staticmethod
    def _populate_grid(layout: QGridLayout, widgets: tuple[QPushButton, ...] | list[QPushButton], columns: int) -> None:
        """Coloca los botones en columnas que puedan cambiar con el ancho disponible."""
        while layout.count():
            layout.takeAt(0)
        for index, widget in enumerate(widgets):
            layout.addWidget(widget, index // columns, index % columns)
        for column in range(columns):
            layout.setColumnStretch(column, 1)

    def resizeEvent(self, event) -> None:
        """Refluye controles y reduce los relojes antes de que su contenido se recorte."""
        super().resizeEvent(event)
        compact = self.width() < 1_020
        self._populate_grid(self.primary_controls, self.primary_buttons, 1 if compact else 2)
        self._populate_grid(self.navigation, self.navigation_buttons, 1 if compact else 2)
        self.metrics_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        clock_size = 34 if compact else 43
        self.update_timer_visual_state()

    def build_records(self) -> QWidget:
        """Construye la vista donde se muestran y gestionan los registros guardados."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 28, 42, 36)
        layout.setSpacing(16)

        heading = QHBoxLayout()
        title = QLabel("Registros")
        title.setObjectName("brand")
        heading.addWidget(title)
        heading.addStretch()
        self.records_summary = QLabel("0 intentos guardados")
        self.records_summary.setObjectName("record_meta")
        heading.addWidget(self.records_summary)
        layout.addLayout(heading)

        toolbar = QHBoxLayout()
        open_button = QPushButton("Abrir registro")
        open_button.setObjectName("secondary_action")
        self.recent_files_menu = QMenu(self)
        self.refresh_recent_files_menu()
        open_button.setMenu(self.recent_files_menu)
        open_button.clicked.connect(self.open_record)

        for text, callback, object_name in (
            ("Importar registros", self.import_records, "secondary_action"),
            ("Guardar registro", self.save_as, "secondary_action"),
            ("Renombrar", self.rename_record, "secondary_action"),
            ("Cerrar registro", self.close_record, "secondary_action"),
            ("Agregar intento", self.add_item, "toolbar_primary"),
        ):
            button = QPushButton(text)
            if object_name:
                button.setObjectName(object_name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)

        toolbar.insertWidget(0, open_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Sección",
            "Ejercicio",
            "Inciso",
            "Receso",
            "Tiempo",
            "Completado",
            "Comentario",
            "Comentar",
            "Editar",
            "Reset",
            "Eliminar",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self.show_comment_alert)
        layout.addWidget(self.table)
        return page

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
        lbl_tot.setObjectName("metric_label")
        self.stat_total_exercise = QLabel("00:00")
        self.stat_total_exercise.setObjectName("metric_value")
        lbl_break_tot = QLabel("TIEMPO TOTAL DE RECESO")
        lbl_break_tot.setObjectName("break_label")
        self.stat_total_break = QLabel("00:00")
        self.stat_total_break.setObjectName("break_value")
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
        lbl_avg.setObjectName("metric_label")
        self.stat_avg_exercise = QLabel("00:00")
        self.stat_avg_exercise.setObjectName("metric_value")
        lbl_break_avg = QLabel("TIEMPO PROMEDIO DE RECESO")
        lbl_break_avg.setObjectName("break_label")
        self.stat_avg_break = QLabel("00:00")
        self.stat_avg_break.setObjectName("break_value")
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
        lbl_longest.setObjectName("metric_label")
        self.stat_longest_time = QLabel("00:00")
        self.stat_longest_time.setObjectName("metric_value")
        lbl_longest_sub = QLabel("EJERCICIO")
        lbl_longest_sub.setObjectName("break_label")
        self.stat_longest_name = QLabel("Ninguno")
        self.stat_longest_name.setObjectName("break_value")
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
        lbl_comp.setObjectName("metric_label")
        self.stat_completed_count = QLabel("0 / 0")
        self.stat_completed_count.setObjectName("metric_value")
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
            self.stats_section_table.setItem(row, 3, QTableWidgetItem(f"{sec.completed_unique} / {sec.total_unique}"))
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

    def toggle_session(self) -> None:
        """Inicia, pausa en receso o reanuda la sesión según su estado."""
        if self.application.mode is TimerMode.WAITING:
            self.sync_location()
            self.start_sound_player.setPosition(0)
            self.start_sound_player.play()
        self.application.toggle_session()

        self.set_locked(True)
        self.update_session_button()
        self.update_timer_visual_state()
        self.status_label.setText("Receso en curso" if self.application.mode is TimerMode.BREAK else "Sesión en curso")

    def update_session_button(self) -> None:
        """Actualiza el texto del control de sesión según el modo actual."""
        labels = {
            TimerMode.WAITING: "INICIAR",
            TimerMode.PLAY: "RECESO",
            TimerMode.BREAK: "CONTINUAR",
        }
        self.session_button.setText(labels[self.application.mode])

    def stop_timer(self) -> None:
        """Detiene y descarta el conteo actual sin guardar un intento."""
        self.application.stop_session()
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        self.status_label.setText("Listo para comenzar")

    def finish_item(self, completed: bool, keep_location: bool = False, stop: bool = False) -> None:
        """Guarda el intento actual como item y limpia el estado del temporizador."""
        if self.application.mode is TimerMode.WAITING:
            return

        self.application.finish_item(completed)
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        result = "completo" if completed else "incompleto"
        self.status_label.setText(f"Intento {result}. Listo para comenzar")

        if not keep_location and not stop:
            self.sync_location()

        self.refresh_clock()
        self.refresh_table()

    def next_inciso(self) -> None:
        """Guarda el ejercicio actual y avanza al siguiente inciso."""
        was_active = self.application.mode is not TimerMode.WAITING
        self.application.navigate("next_inciso")
        self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()
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
            self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def next_exercise(self) -> None:
        """Guarda el ejercicio y pasa al siguiente ejercicio de la sección."""
        was_active = self.application.mode is not TimerMode.WAITING
        self.application.navigate("next_exercise")
        self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()
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
            self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()
        if was_active:
            self.set_locked(False)
            self.update_session_button()
            self.update_timer_visual_state()
            self.refresh_table()
            self.refresh_clock()

    def next_section(self) -> None:
        """Guarda el ejercicio actual y avanza a la siguiente sección."""
        was_active = self.application.mode is not TimerMode.WAITING
        self.application.navigate("next_section")
        self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()
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
            self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()
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
        if self.application.mode is TimerMode.PLAY:
            self.status_label.setText("Sesión en curso")
        elif self.application.mode is TimerMode.BREAK:
            self.status_label.setText("Receso en curso")

        today_ms = self.application.get_today_study_time_ms(include_current=True)
        self.today_study_label.setText(format_hh_mm_ss(today_ms))

    def update_timer_visual_state(self) -> None:
        """Aplica el color de énfasis a la lectura que está avanzando."""
        exercise_color = "#2f8f57" if self.application.mode is TimerMode.PLAY else "#18252b"
        break_color = "#c64d4d" if self.application.mode is TimerMode.BREAK else "#60706d"
        compact = self.width() < 1_020
        clock_size = 34 if compact else 43
        self.exercise_clock.setStyleSheet(f"color: {exercise_color}; font-size: {clock_size}px;")
        self.break_clock.setStyleSheet(
            f"color: {break_color}; font-size: {max(19, clock_size // 2)}px;"
        )

    def autosave(self) -> None:
        """Guarda el registro activo en el archivo asociado."""
        self.application.save()

    def prompt_initial_record_choice(self) -> None:
        """Pregunta al usuario si debe crear un registro nuevo o abrir uno existente."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Study Timetrial")
        dialog.setModal(True)
        dialog.setMinimumWidth(560)
        dialog.setStyleSheet(
            """
            QDialog { background: #f4f6f2; }
            QLabel#title { color: #18252b; font-size: 22px; font-weight: 800; }
            QLabel#subtitle { color: #60706d; font-size: 13px; }
            QLabel#version { color: #75827f; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            QListWidget { background: #ffffff; border: 1px solid #dfe6df; border-radius: 8px; min-height: 96px; }
            QPushButton { min-height: 42px; min-width: 160px; border-radius: 9px; }
            QPushButton#primary { background: #18252b; color: #d7f56b; border: 1px solid #18252b; font-weight: 800; }
            QPushButton#secondary { background: #ffffff; color: #263238; border: 1px solid #cbd6d0; }
            QPushButton#ghost { background: transparent; color: #60706d; border: 1px solid #dfe6df; }
            """
        )

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

        new_button = QPushButton("Nuevo archivo")
        new_button.setObjectName("primary")
        new_button.clicked.connect(lambda: self._handle_initial_choice(dialog, "new"))

        open_button = QPushButton("Abrir archivo")
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
        if self.application.is_record_open:
            file_name = self.application.record_path.stem
            self.home_title.setText(file_name)
            self.setWindowTitle(f"{APP_TITLE} - {file_name}")
        else:
            self.home_title.setText(APP_TITLE)
            self.setWindowTitle(APP_TITLE)

    def refresh_table(self) -> None:
        """Vuelca a pintar la tabla con los registros ordenados por fecha."""
        self.table.setRowCount(0)
        ordered_items = self.application.ordered_items()
        total_items = len(ordered_items)
        self.records_summary.setText(f"{total_items} intento{'s' if total_items != 1 else ''} guardado{'s' if total_items != 1 else ''}")

        for index, item in enumerate(ordered_items):
            self.table.insertRow(index)
            location = f"{item.section_type} {item.section_number}"
            self.table.setItem(index, 0, QTableWidgetItem(location))
            self.table.setItem(index, 1, QTableWidgetItem(str(item.exercise)))
            self.table.setItem(index, 2, QTableWidgetItem(str(item.inciso or "-")))
            self.table.setItem(index, 3, QTableWidgetItem(format_milliseconds(item.break_time_ms)))
            self.table.setItem(index, 4, QTableWidgetItem(format_milliseconds(item.exercise_time_ms)))
            self.table.setItem(index, 5, QTableWidgetItem("Sí" if item.completed else "No"))
            self.table.setItem(index, 6, QTableWidgetItem(item.comment))

            for column, label, callback in (
                (7, "COMENTAR", lambda _, row=index: self.comment_item(row)),
                (8, "EDITAR", lambda _, row=index: self.edit_item(row)),
                (9, "RESET", lambda _, row=index: self.reset_item(row)),
            ):
                button = QPushButton(label)
                button.setObjectName("table_action")
                button.clicked.connect(callback)
                self.table.setCellWidget(index, column, button)

            delete_button = QPushButton("ELIMINAR")
            delete_button.setObjectName("table_delete")
            delete_button.clicked.connect(lambda _, row=index: self.delete_item(row))
            self.table.setCellWidget(index, 10, delete_button)

        self.refresh_statistics()

    def show_comment_alert(self, row: int, column: int) -> None:
        """Muestra el comentario completo al hacer click en su celda."""
        if column != 6:
            return

        item = self.application.ordered_items()[row]
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
            self.status_label.setText("Comentario preparado para el próximo registro")

    def comment_item(self, row: int) -> None:
        """Agrega o edita el comentario de un registro existente."""
        item = self.application.ordered_items()[row]
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

    def edit_item(self, row: int) -> None:
        """Edita un item existente en la fila indicada."""
        item = self.application.ordered_items()[row]
        dialog = ItemDialog(self, item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.validated_item is not None:
                self.application.replace_item(item, dialog.validated_item)
            self.refresh_table()

    def reset_item(self, row: int) -> None:
        """Reinicia el tiempo de un item concreto."""
        item = self.application.ordered_items()[row]
        if QMessageBox.question(
            self,
            "Confirmar reset",
            "¿Está seguro de reiniciar este registro?",
        ) == QMessageBox.StandardButton.Yes:
            self.application.reset_item(item)
            self.refresh_table()

    def delete_item(self, row: int) -> None:
        """Elimina un item concreto tras confirmar la acción."""
        item = self.application.ordered_items()[row]
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

