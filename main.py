from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QBoxLayout,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFrame,
    QGridLayout,
)

from application_service import SessionLocation, StudyApplicationService
from models import TimerItem
from timer_service import TimerMode

DEFAULT_SECTION_TYPE = "Guía"
APP_TITLE = "Study Timetrial"
MAX_VALUE = 999_999


def format_ms(milliseconds: int) -> str:
    """Convierte milisegundos al formato completo usado en registros."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{millis:03d}"


def format_timer_ms(milliseconds: int) -> tuple[str, str]:
    """Devuelve la parte principal y los milisegundos del reloj de sesión."""
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}", f".{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}", f".{millis:03d}"


def timer_markup(milliseconds: int) -> str:
    """Crea el reloj con milisegundos visualmente secundarios."""
    main, millis = format_timer_ms(milliseconds)
    return f'{main}<span style="font-size: 52%;">{millis}</span>'


def parse_ms(value: str) -> int:
    """Parsea un tiempo compacto o completo y lo convierte a milisegundos."""
    parts = value.strip().split(":")
    if len(parts) not in (2, 3, 4):
        raise ValueError("Use SS:SSS, MM:SS:SSS o HH:MM:SS:SSS")

    try:
        values = [int(part) for part in parts]
    except ValueError as error:
        raise ValueError("El tiempo solo puede contener números") from error

    if len(values) == 2:
        hours, minutes, seconds, millis = 0, 0, *values
    elif len(values) == 3:
        hours, minutes, seconds, millis = 0, *values
    else:
        hours, minutes, seconds, millis = values

    if min(hours, minutes, seconds, millis) < 0 or minutes > 59 or seconds > 59 or millis > 999:
        raise ValueError("Tiempo inválido")

    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


class ItemDialog(QDialog):
    """Formulario para crear o editar un item del historial de ejercicios."""

    def __init__(self, parent: QWidget | None = None, item: TimerItem | None = None) -> None:
        super().__init__(parent)
        self._validated: TimerItem | None = None
        self.setWindowTitle("Editar item" if item else "Agregar item")

        form = QFormLayout(self)
        self.section_type = QLineEdit(item.section_type if item else DEFAULT_SECTION_TYPE)
        self.section_number = QSpinBox(); self.section_number.setRange(1, MAX_VALUE); self.section_number.setValue(item.section_number if item else 1)
        self.exercise = QSpinBox(); self.exercise.setRange(1, MAX_VALUE); self.exercise.setValue(item.exercise if item else 1)
        self.inciso = QSpinBox(); self.inciso.setRange(0, MAX_VALUE); self.inciso.setSpecialValueText("Sin inciso"); self.inciso.setValue(item.inciso or 0 if item else 0)
        self.exercise_time = QLineEdit(format_ms(item.exercise_time_ms if item else 0))
        self.break_time = QLineEdit(format_ms(item.break_time_ms if item else 0))
        self.completed = QCheckBox("Completado"); self.completed.setChecked(item.completed if item else False)

        for label, widget in (
            ("Tipo de sección", self.section_type),
            ("Número de sección", self.section_number),
            ("Ejercicio", self.exercise),
            ("Inciso", self.inciso),
            ("Tiempo", self.exercise_time),
            ("Receso", self.break_time),
            ("Estado", self.completed),
        ):
            form.addRow(label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def item(self, existing: TimerItem | None = None) -> TimerItem:
        """Valida y devuelve el item a partir de los datos del formulario."""
        section_type = self.section_type.text().strip()
        if not section_type:
            raise ValueError("El tipo de sección es obligatorio")

        result = TimerItem(
            section_type=section_type,
            section_number=self.section_number.value(),
            exercise=self.exercise.value(),
            inciso=self.inciso.value() or None,
            exercise_time_ms=parse_ms(self.exercise_time.text()),
            break_time_ms=parse_ms(self.break_time.text()),
            completed=self.completed.isChecked(),
        )

        if existing:
            result.id = existing.id
            result.created_at = existing.created_at

        return result

    def accept(self) -> None:
        """Valida el formulario antes de cerrar el diálogo."""
        try:
            self._validated = self.item()
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Valor inválido", str(error))
            return
        super().accept()


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación Study Timetrial."""

    STYLESHEET = """
        QWidget { background: #f4f6f2; color: #263238; font-size: 14px; }
        QMainWindow { background: #f4f6f2; }
        QTabWidget::pane { border: none; background: #f4f6f2; }
        QTabBar { background: #18252b; }
        QTabBar::tab { background: #18252b; color: #aeb9b6; padding: 14px 26px; border: none; font-weight: 600; }
        QTabBar::tab:selected { color: #d7f56b; border-bottom: 3px solid #d7f56b; }
        QLabel#brand { color: #18252b; font-size: 27px; font-weight: 800; letter-spacing: 1px; }
        QLabel#eyebrow { color: #75827f; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
        QLabel#record_meta { color: #75827f; font-size: 13px; }
        QLabel#location { color: #18252b; font-size: 27px; font-weight: 800; qproperty-alignment: AlignCenter; }
        QLabel#status { color: #60706d; font-size: 13px; }
        QFrame#heroCard, QFrame#metricCard, QFrame#sectionCard { background: #ffffff; border: 1px solid #dfe6df; border-radius: 12px; }
        QFrame#heroCard { border-top: 4px solid #d7f56b; }
        QFrame#metricCard { padding: 4px; }
        QLabel#metric_label { color: #75827f; font-size: 11px; font-weight: 700; letter-spacing: 1px; qproperty-alignment: AlignCenter; }
        QLabel#metric_value { color: #18252b; font-size: 43px; font-weight: 800; qproperty-alignment: AlignCenter; }
        QLabel#break_label { color: #75827f; font-size: 10px; font-weight: 700; letter-spacing: 1px; qproperty-alignment: AlignCenter; }
        QLabel#break_value { color: #60706d; font-size: 22px; font-weight: 700; qproperty-alignment: AlignCenter; }
        QLineEdit, QSpinBox { background: #fbfcfa; border: 1px solid #cbd6d0; border-radius: 7px; padding: 9px 10px; min-height: 18px; }
        QLineEdit:focus, QSpinBox:focus { border: 2px solid #8da844; padding: 8px 9px; }
        QLineEdit:disabled, QSpinBox:disabled { background: #edf1ed; color: #77827f; }
        QPushButton { background: #ffffff; color: #263238; border: 1px solid #cbd6d0; border-radius: 7px; padding: 8px 12px; font-size: 12px; font-weight: 600; }
        QPushButton:hover { border-color: #8da844; background: #f4f8e8; }
        QPushButton:pressed { background: #e8f0d2; }
        QPushButton#primary { background: #18252b; color: #d7f56b; border: 1px solid #18252b; font-weight: 800; padding: 10px 18px; }
        QPushButton#primary:hover { background: #2a3b40; }
        QPushButton#break { color: #a36a21; border-color: #e5c896; }
        QPushButton#danger { color: #a33c32; border-color: #e2b4af; }
        QPushButton#stop { color: #a33c32; border-color: #e2b4af; }
        QPushButton#toolbar_primary { background: #d7f56b; color: #18252b; border: none; }
        QLabel#section_title { color: #18252b; font-size: 15px; font-weight: 700; }
        QTableWidget { background: #ffffff; border: 1px solid #dfe6df; border-radius: 8px; gridline-color: #edf1ed; alternate-background-color: #f7f9f6; selection-background-color: #eaf2d2; selection-color: #18252b; }
        QHeaderView::section { background: #eef2ed; color: #60706d; border: none; border-bottom: 1px solid #dfe6df; padding: 11px 8px; font-size: 11px; font-weight: 700; }
        QTableWidget QPushButton { padding: 6px 8px; font-size: 11px; }
        QCheckBox { spacing: 8px; }
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
        self.tabs.addTab(self.home, "Cronómetro")
        self.tabs.addTab(self.records, "Registros")
        self.tabs.currentChanged.connect(lambda index: self.refresh_table() if index == 1 else None)

        self.tick = QTimer(self)
        self.tick.timeout.connect(self.refresh_clock)
        self.tick.start(50)

        self.update_title()
        self.autosave()

    def build_home(self) -> QWidget:
        """Construye la vista del cronómetro."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(48, 32, 48, 38)
        outer.setSpacing(18)

        top = QHBoxLayout()
        brand = QLabel("STUDY TIMETRIAL")
        brand.setObjectName("brand")
        top.addWidget(brand)
        top.addStretch()
        record_meta = QLabel("REGISTRO LOCAL  ·  SIN SERVIDOR")
        record_meta.setObjectName("record_meta")
        top.addWidget(record_meta)
        outer.addLayout(top)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 22, 28, 24)
        hero_layout.setSpacing(18)

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
        self.section_input = QLineEdit(DEFAULT_SECTION_TYPE)
        self.section_input.setPlaceholderText("Tipo de sección")
        self.section_number_input = QSpinBox(); self.section_number_input.setRange(1, MAX_VALUE); self.section_number_input.setValue(1)
        self.exercise_input = QSpinBox(); self.exercise_input.setRange(1, MAX_VALUE); self.exercise_input.setValue(1)
        self.inciso_input = QSpinBox(); self.inciso_input.setRange(0, MAX_VALUE); self.inciso_input.setSpecialValueText("Sin inciso")
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
        metrics.setContentsMargins(0, 2, 0, 2)
        metrics.setSpacing(8)
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
        exercise_label = QLabel("TIEMPO DE EJERCICIO"); exercise_label.setObjectName("metric_label")
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
        controls_layout = QVBoxLayout(controls_card); controls_layout.setContentsMargins(18, 16, 18, 16); controls_layout.setSpacing(12)
        controls_title = QLabel("CONTROLES DE SESIÓN"); controls_title.setObjectName("eyebrow")
        controls_layout.addWidget(controls_title)
        primary_controls = QGridLayout(); primary_controls.setHorizontalSpacing(10); primary_controls.setVerticalSpacing(8)
        self.primary_controls = primary_controls
        self.session_button = QPushButton("INICIAR"); self.session_button.setObjectName("primary"); self.session_button.clicked.connect(self.toggle_session)
        stop = QPushButton("DETENER"); stop.setObjectName("stop"); stop.clicked.connect(self.stop_timer)
        incomplete = QPushButton("INCOMPLETO"); incomplete.setObjectName("danger"); incomplete.clicked.connect(lambda: self.finish_item(False, keep_location=True))
        complete = QPushButton("COMPLETO"); complete.clicked.connect(lambda: self.finish_item(True, keep_location=True))
        self.primary_buttons = (self.session_button, stop, complete, incomplete)
        for column, button in enumerate(self.primary_buttons):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            primary_controls.addWidget(button, 0 if column < 2 else 1, column % 2)
        controls_layout.addLayout(primary_controls)
        navigation = QGridLayout(); navigation.setHorizontalSpacing(10); navigation.setVerticalSpacing(8)
        self.navigation = navigation
        self.navigation_buttons = []
        for text, callback in (
            ("ANTERIOR INCISO", self.previous_inciso),
            ("SIGUIENTE INCISO", self.next_inciso),
            ("ANTERIOR EJERCICIO", self.previous_exercise),
            ("SIGUIENTE EJERCICIO", self.next_exercise),
            ("ANTERIOR SECCIÓN", self.previous_section),
            ("SIGUIENTE SECCIÓN", self.next_section),
        ):
            button = QPushButton(text); button.clicked.connect(callback)
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

        for text, callback, object_name in (
            ("Abrir registro", self.open_record, ""),
            ("Guardar registro", self.save_as, ""),
            ("Renombrar", self.rename_record, ""),
            ("Cerrar registro", self.close_record, ""),
            ("Agregar intento", self.add_item, "toolbar_primary"),
        ):
            button = QPushButton(text)
            if object_name:
                button.setObjectName(object_name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Sección",
            "Ejercicio",
            "Inciso",
            "Receso",
            "Tiempo",
            "Completado",
            "Editar",
            "Reset",
            "Eliminar",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        return page

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
        self.application.navigate("next_inciso")
        self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()

    def previous_inciso(self) -> None:
        """Guarda el intento y vuelve al inciso anterior, si existe."""
        if self.application.navigate("previous_inciso"):
            self.inciso_input.setValue(self.application.location.inciso or 0)
        self.sync_location()

    def next_exercise(self) -> None:
        """Guarda el ejercicio y pasa al siguiente ejercicio de la sección."""
        self.application.navigate("next_exercise")
        self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()

    def previous_exercise(self) -> None:
        """Guarda el intento y vuelve al ejercicio anterior, si existe."""
        if self.application.navigate("previous_exercise"):
            self.exercise_input.setValue(self.application.location.exercise)
        self.inciso_input.setValue(0)
        self.sync_location()

    def next_section(self) -> None:
        """Guarda el ejercicio actual y avanza a la siguiente sección."""
        self.application.navigate("next_section")
        self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()

    def previous_section(self) -> None:
        """Guarda el intento y vuelve a la sección anterior, si existe."""
        if self.application.navigate("previous_section"):
            self.section_number_input.setValue(self.application.location.section_number)
        self.exercise_input.setValue(1)
        self.inciso_input.setValue(0)
        self.sync_location()

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

    def update_title(self) -> None:
        """Actualiza el título de la ventana según el archivo de registro abierto."""
        if self.application.is_record_open:
            self.setWindowTitle(f"{APP_TITLE} - {self.application.record.record_name}")
        else:
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
            self.table.setItem(index, 3, QTableWidgetItem(format_ms(item.break_time_ms)))
            self.table.setItem(index, 4, QTableWidgetItem(format_ms(item.exercise_time_ms)))
            self.table.setItem(index, 5, QTableWidgetItem("Sí" if item.completed else "No"))

            for column, label, callback in (
                (6, "EDITAR", lambda _, row=index: self.edit_item(row)),
                (7, "RESET", lambda _, row=index: self.reset_item(row)),
                (8, "ELIMINAR", lambda _, row=index: self.delete_item(row)),
            ):
                button = QPushButton(label)
                button.clicked.connect(callback)
                self.table.setCellWidget(index, column, button)

    def add_item(self) -> None:
        """Añade un item manualmente desde el diálogo de edición."""
        dialog = ItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.application.add_item(dialog._validated)
            self.refresh_table()

    def edit_item(self, row: int) -> None:
        """Edita un item existente en la fila indicada."""
        item = self.application.ordered_items()[row]
        dialog = ItemDialog(self, item)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.application.replace_item(item, dialog._validated)
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
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Archivo inválido", str(error))

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())