"""Vista Home / Cronómetro de Study Timetrial."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPaintEvent
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QBoxLayout,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import SessionLocation, StudyApplicationService
from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
)
from domain.models import TagDefinition, TimerItem
from domain.timer_service import TimerMode
from presentation.audio_service import AudioService
from presentation.empty_state_widget import EmptyStateWidget
from presentation.presentation_formatters import format_hh_mm_ss, timer_markup
from presentation.theme import get_status_pill_style, get_timer_cards_style
from presentation.home.home_presenter import HomePresenter
from presentation.home.interfaces import IHomeView
from presentation.today_activity_strip_widget import TodayActivityStripWidget

if TYPE_CHECKING:
    from presentation.main_window import MainWindow

DEFAULT_SECTION_TYPE = "Guía"
APP_TITLE = "Study Timetrial"
APP_VERSION = "v1.0"
MAX_VALUE = 999_999


class LocationBadgeLabel(QLabel):
    """Etiqueta y recuadro de ubicación en el cronómetro que soporta dibujar marcadores (bookmarks)."""

    BASE_WIDTH = 340
    EXPANDED_WIDTH = 440
    LARGE_WIDTH = 520
    FIXED_HEIGHT = 50

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._tags: list[TagDefinition] = []
        font = self.font()
        font.setPointSize(18)
        font.setBold(True)
        self.setFont(font)
        self.setFixedHeight(self.FIXED_HEIGHT)
        self.setFixedWidth(self.BASE_WIDTH)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_tags(self, tags: list[TagDefinition]) -> None:
        """Actualiza la lista de marcadores asignados y recalcula el tamaño fijo requerido."""
        self._tags = list(tags)
        self._adjust_fixed_size()
        self.update()

    @property
    def tags(self) -> list[TagDefinition]:
        return self._tags

    def setText(self, text: str) -> None:
        super().setText(text)
        self._adjust_fixed_size()

    def _adjust_fixed_size(self) -> None:
        """Ajusta el ancho fijo: usa el tamaño base, pero si los bookmarks no entran, se agranda a un tamaño fijo superior."""
        fm = self.fontMetrics()
        text_w = fm.horizontalAdvance(self.text())
        k = len(self._tags)
        gap = 3
        bw = 13
        tags_w = (k * bw + max(0, k - 1) * gap) if k > 0 else 0

        # Al estar el texto centrado, el espacio para que el texto no solape con los marcadores a la derecha:
        needed_w = text_w + (tags_w * 2 + 50 if tags_w > 0 else 40)

        if needed_w <= self.BASE_WIDTH:
            target_w = self.BASE_WIDTH
        elif needed_w <= self.EXPANDED_WIDTH:
            target_w = self.EXPANDED_WIDTH
        else:
            target_w = self.LARGE_WIDTH

        if self.width() != target_w:
            self.setFixedWidth(target_w)

    def sizeHint(self) -> QSize:
        return QSize(self.width(), self.FIXED_HEIGHT)

    def minimumSizeHint(self) -> QSize:
        return QSize(self.BASE_WIDTH, self.FIXED_HEIGHT)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self._tags:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        clip_path = QPainterPath()
        clip_path.addRoundedRect(0, 0, w, h, 10, 10)
        painter.setClipPath(clip_path)

        outline_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        tags = self._tags
        k = len(tags)
        gap = 3
        bw = 13
        bh = 20
        total_w = k * bw + (k - 1) * gap
        margin_right = 10
        start_x = w - margin_right - total_w
        y_pos = 2  # Cuelgan en la parte superior derecha, al igual como en el planificador

        outline_bm = qta.icon("fa5s.bookmark", color="rgba(0, 0, 0, 180)")

        for i, tag in enumerate(tags):
            x_pos = start_x + i * (bw + gap)
            color = tag.color or "#a855f7"

            for ox, oy in outline_offsets:
                outline_bm.paint(
                    painter, QRect(int(x_pos + ox), int(y_pos + oy), int(bw), int(bh))
                )

            qta.icon("fa5s.bookmark", color=color).paint(
                painter, QRect(int(x_pos), int(y_pos), int(bw), int(bh))
            )


class HomeViewWidget(QWidget):
    """Vista principal con el cronómetro de estudio y controles de intento.

    Satisface estructuralmente el protocolo IHomeView.
    """

    item_finished = Signal(bool)  # completed

    def __init__(
        self,
        application: StudyApplicationService,
        audio_service: AudioService,
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.application = application
        self.audio_service = audio_service
        self._is_dark_mode = is_dark_mode
        self.stepper_buttons: list[QPushButton] = []
        self.presenter = HomePresenter(view=self, application=self.application, audio_service=self.audio_service)

        self._build_ui()

    def update_clock_display(self, exercise_formatted: str, break_formatted: str) -> None:
        """Actualiza los dígitos visuales del cronómetro."""
        if hasattr(self, "exercise_clock"):
            self.exercise_clock.setText(timer_markup(exercise_formatted))
        if hasattr(self, "break_clock"):
            self.break_clock.setText(timer_markup(break_formatted))

    def update_session_state(self, mode: str, is_paused: bool, is_editing: bool) -> None:
        """Actualiza el estado visual de los controles."""
        self.update_session_button()
        self.update_timer_visual_state()

    def update_personal_best(self, pb_text: str) -> None:
        """Actualiza el badge de récord personal."""
        if hasattr(self, "personal_best_badge"):
            self.personal_best_badge.setText(pb_text)

    def update_daily_kpis(self, study_time: str, completed_count: int, attempts_count: int) -> None:
        """Actualiza las micro-tarjetas de métricas del día."""
        if hasattr(self, "today_study_label"):
            self.today_study_label.setText(study_time)
        if hasattr(self, "today_completed_label"):
            self.today_completed_label.setText(str(completed_count))
        if hasattr(self, "today_attempts_label"):
            self.today_attempts_label.setText(str(attempts_count))

    def set_location_inputs(self, section_type: str, section_number: int, exercise: int, inciso: int | None) -> None:
        """Sincroniza los campos de entrada de ubicación."""
        if hasattr(self, "section_input"):
            self.section_input.setText(section_type)
        if hasattr(self, "section_number_input"):
            self.section_number_input.setValue(section_number)
        if hasattr(self, "exercise_input"):
            self.exercise_input.setValue(exercise)
        if hasattr(self, "inciso_input"):
            self.inciso_input.setValue(inciso or 0)

    def set_controls_locked(self, locked: bool) -> None:
        """Bloquea o desbloquea controles."""
        self.set_locked(locked)

    def set_status_message(self, message: str) -> None:
        """Actualiza el texto de estado."""
        if hasattr(self, "status_label"):
            self.status_label.setText(message)

    @property
    def is_dark_mode(self) -> bool:
        return self._is_dark_mode

    @is_dark_mode.setter
    def is_dark_mode(self, value: bool) -> None:
        self._is_dark_mode = bool(value)
        if hasattr(self, "empty_state_widget"):
            self.empty_state_widget.set_dark_mode(self._is_dark_mode)
        if hasattr(self, "activity_strip"):
            self.activity_strip.is_dark_mode = self._is_dark_mode
        if hasattr(self, "session_button"):
            self.update_session_button()
        if hasattr(self, "stop_button"):
            self.stop_button.setIcon(qta.icon("fa5s.stop", color="#fca5a5" if self._is_dark_mode else "#b91c1c"))
        if hasattr(self, "incomplete_button"):
            self.incomplete_button.setIcon(qta.icon("fa5s.times-circle", color="#fca5a5" if self._is_dark_mode else "#b91c1c"))
        if hasattr(self, "update_tags_visual_state"):
            self.update_tags_visual_state()
        if hasattr(self, "update_personal_best_badge"):
            self.update_personal_best_badge()
        self.update_timer_visual_state()
        if hasattr(self, "_refresh_exercise_chips"):
            self._refresh_exercise_chips()
        if hasattr(self, "location_label") and hasattr(self, "sync_location"):
            self.sync_location()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
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

        # Top Bar: Nombre de la materia activa + Tríada de KPIs Diarios
        top = QHBoxLayout()
        top.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.home_title = QLabel(APP_TITLE)
        self.home_title.setObjectName("brand")
        title_box.addWidget(self.home_title)
        top.addLayout(title_box)
        top.addStretch()

        # KPI Triad (3 micro-tarjetas: Intentos, Resueltos, Enfoque hoy)
        kpis_layout = QHBoxLayout()
        kpis_layout.setSpacing(10)

        # KPI: Intentos (a la izquierda)
        self.kpi_today_attempts = QFrame()
        self.kpi_today_attempts.setObjectName("kpiCardToday")
        kpi_att_layout = QHBoxLayout(self.kpi_today_attempts)
        kpi_att_layout.setContentsMargins(12, 6, 14, 6)
        kpi_att_layout.setSpacing(8)

        kpi_att_icon = QLabel()
        kpi_att_icon.setPixmap(qta.icon("fa5s.bolt", color="#fbbf24").pixmap(18, 18))
        kpi_att_layout.addWidget(kpi_att_icon)

        kpi_att_text = QVBoxLayout()
        kpi_att_text.setContentsMargins(0, 0, 0, 0)
        kpi_att_text.setSpacing(1)
        kpi_att_label = QLabel("INTENTOS")
        kpi_att_label.setObjectName("kpiTodayLabel")
        self.today_attempts_label = QLabel("0")
        self.today_attempts_label.setObjectName("kpiTodayValue")
        kpi_att_text.addWidget(kpi_att_label)
        kpi_att_text.addWidget(self.today_attempts_label)
        kpi_att_layout.addLayout(kpi_att_text)
        kpis_layout.addWidget(self.kpi_today_attempts)

        # KPI: Resueltos (en el centro, sin 'ej.')
        self.kpi_today_completed = QFrame()
        self.kpi_today_completed.setObjectName("kpiCardToday")
        kpi_comp_layout = QHBoxLayout(self.kpi_today_completed)
        kpi_comp_layout.setContentsMargins(12, 6, 14, 6)
        kpi_comp_layout.setSpacing(8)

        kpi_comp_icon = QLabel()
        kpi_comp_icon.setPixmap(qta.icon("fa5s.check-circle", color="#34d399").pixmap(18, 18))
        kpi_comp_layout.addWidget(kpi_comp_icon)

        kpi_comp_text = QVBoxLayout()
        kpi_comp_text.setContentsMargins(0, 0, 0, 0)
        kpi_comp_text.setSpacing(1)
        kpi_comp_label = QLabel("RESUELTOS")
        kpi_comp_label.setObjectName("kpiTodayLabel")
        self.today_completed_label = QLabel("0")
        self.today_completed_label.setObjectName("kpiTodayValue")
        kpi_comp_text.addWidget(kpi_comp_label)
        kpi_comp_text.addWidget(self.today_completed_label)
        kpi_comp_layout.addLayout(kpi_comp_text)
        kpis_layout.addWidget(self.kpi_today_completed)

        # KPI: Tiempo de estudio (a la derecha)
        self.kpi_today_study = QFrame()
        self.kpi_today_study.setObjectName("kpiCardToday")
        kpi_study_layout = QHBoxLayout(self.kpi_today_study)
        kpi_study_layout.setContentsMargins(12, 6, 14, 6)
        kpi_study_layout.setSpacing(8)

        kpi_study_icon = QLabel()
        kpi_study_icon.setPixmap(qta.icon("fa5s.stopwatch", color="#10b981").pixmap(18, 18))
        kpi_study_layout.addWidget(kpi_study_icon)

        kpi_study_text = QVBoxLayout()
        kpi_study_text.setContentsMargins(0, 0, 0, 0)
        kpi_study_text.setSpacing(1)
        kpi_study_label = QLabel("ENFOQUE HOY")
        kpi_study_label.setObjectName("kpiTodayLabel")
        self.today_study_label = QLabel("00:00:00")
        self.today_study_label.setObjectName("kpiTodayValue")
        kpi_study_text.addWidget(kpi_study_label)
        kpi_study_text.addWidget(self.today_study_label)
        kpi_study_layout.addLayout(kpi_study_text)
        kpis_layout.addWidget(self.kpi_today_study)

        top.addLayout(kpis_layout)
        outer.addLayout(top)

        # Activity Strip de 24 Horas
        self.activity_strip = TodayActivityStripWidget(is_dark_mode=self.is_dark_mode, parent=self)
        outer.addWidget(self.activity_strip)

        # Banner contextual de modo continuación
        self.continuation_banner = QFrame()
        self.continuation_banner.setObjectName("continuationBanner")
        self.continuation_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.continuation_banner)
        banner_layout.setContentsMargins(18, 10, 18, 10)
        banner_layout.setSpacing(12)

        self.continuation_icon = QLabel()
        self.continuation_icon.setPixmap(qta.icon("fa5s.history", color="#f59e0b").pixmap(18, 18))
        banner_layout.addWidget(self.continuation_icon)

        self.continuation_label = QLabel("Modo continuación activo")
        self.continuation_label.setObjectName("continuation_label")
        banner_layout.addWidget(self.continuation_label, 1)

        self.continuation_cancel_btn = QPushButton(" Cancelar edición")
        self.continuation_cancel_btn.setObjectName("continuation_cancel_btn")
        self.continuation_cancel_btn.setIcon(qta.icon("fa5s.times", color="#ef4444"))
        self.continuation_cancel_btn.setToolTip("Descarta los cambios y vuelve a un intento nuevo")
        self.continuation_cancel_btn.clicked.connect(self.cancel_continuation)
        banner_layout.addWidget(self.continuation_cancel_btn)

        outer.addWidget(self.continuation_banner)

        # Hero Card: Ubicación y Récord Personal
        self.hero_card = QFrame()
        hero = self.hero_card
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 18, 24, 18)
        hero_layout.setSpacing(12)

        hero_top = QHBoxLayout()
        hero_top.setSpacing(10)

        self.location_label = LocationBadgeLabel()
        self.location_label.setObjectName("location_badge")
        self.location_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.location_label.mousePressEvent = self._on_location_label_clicked
        hero_top.addWidget(self.location_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Tira de 5 Chips de Ejercicios (el 3ro es el actual) inmediatamente a la derecha del título
        chips_box = QHBoxLayout()
        chips_box.setSpacing(6)
        chips_box.setContentsMargins(6, 0, 0, 0)

        self.exercise_chips: list[QPushButton] = []
        for i in range(5):
            btn = QPushButton()
            btn.setObjectName(f"exercise_chip_{i}")
            btn.setFixedSize(58, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._on_chip_clicked(idx))
            self.exercise_chips.append(btn)
            chips_box.addWidget(btn)

        hero_top.addLayout(chips_box)
        hero_top.addStretch()

        self.auto_advance_checkbox = QCheckBox("Auto-avanzar al completar")
        self.auto_advance_checkbox.setObjectName("auto_advance_toggle")
        self.auto_advance_checkbox.setToolTip("Avanza automáticamente al siguiente ejercicio al completar con éxito")
        self.auto_advance_checkbox.setChecked(True)
        hero_top.addWidget(self.auto_advance_checkbox, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.personal_best_badge = QLabel("🏆 Récord: --:--")
        self.personal_best_badge.setObjectName("personal_best_badge")
        hero_top.addWidget(self.personal_best_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        hero_layout.addLayout(hero_top)

        selectors = QGridLayout()
        selectors.setHorizontalSpacing(12)
        selectors.setVerticalSpacing(6)
        self.section_input = QLineEdit(DEFAULT_SECTION_TYPE)
        self.section_input.setObjectName("location_selector_input")
        self.section_input.setPlaceholderText("Tipo de sección")
        self.section_number_input = QSpinBox()
        self.section_number_input.setObjectName("location_selector_input")
        self.section_number_input.setRange(1, MAX_VALUE)
        self.section_number_input.setValue(1)
        self.exercise_input = QSpinBox()
        self.exercise_input.setObjectName("location_selector_input")
        self.exercise_input.setRange(1, MAX_VALUE)
        self.exercise_input.setValue(1)
        self.inciso_input = QSpinBox()
        self.inciso_input.setObjectName("location_selector_input")
        self.inciso_input.setRange(0, MAX_VALUE)
        self.inciso_input.setSpecialValueText("Sin inciso")

        self.section_input.textChanged.connect(self.sync_location)
        self.section_number_input.valueChanged.connect(self.sync_location)
        self.exercise_input.valueChanged.connect(self.sync_location)
        self.inciso_input.valueChanged.connect(self.sync_location)

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
            field_label.setObjectName("location_selector_label")
            selectors.addWidget(field_label, 0, column)
            selectors.addWidget(widget, 1, column)
        selectors.setColumnStretch(0, 2)
        selectors.setColumnStretch(1, 1)
        selectors.setColumnStretch(2, 1)
        selectors.setColumnStretch(3, 1)
        hero_layout.addLayout(selectors)
        outer.addWidget(hero)

        # Independent section for Notes and Tags (between selectors and clocks)
        self.notes_card = QFrame()
        self.notes_card.setObjectName("notesCard")
        notes_card_layout = QVBoxLayout(self.notes_card)
        notes_card_layout.setContentsMargins(20, 12, 20, 12)
        notes_card_layout.setSpacing(8)

        notes_header = QHBoxLayout()
        notes_header.setSpacing(8)
        notes_icon = QLabel()
        notes_icon.setPixmap(qta.icon("fa5s.sticky-note", color="#38bdf8").pixmap(14, 14))
        notes_header.addWidget(notes_icon)

        notes_title = QLabel("APUNTES Y MARCADORES")
        notes_title.setObjectName("eyebrow")
        notes_header.addWidget(notes_title)
        notes_header.addStretch()

        self.comment_button = QPushButton("  APUNTES")
        self.comment_button.setObjectName("comment_action")
        self.comment_button.setFixedHeight(32)
        self.comment_button.setMinimumWidth(100)
        self.comment_button.setMaximumWidth(140)
        self.comment_button.setIcon(qta.icon("fa5s.sticky-note", color="#475569"))
        self.comment_button.setToolTip("Ver o redactar apuntes con formato Markdown")
        self.comment_button.clicked.connect(self.add_home_comment)
        self.notes_button = self.comment_button

        self.tags_button = QPushButton("  MARCADORES")
        self.tags_button.setObjectName("tags_action")
        self.tags_button.setFixedHeight(32)
        self.tags_button.setMinimumWidth(110)
        self.tags_button.setMaximumWidth(150)
        self.tags_button.setIcon(qta.icon("fa5s.tags", color="#475569"))
        self.tags_button.setToolTip("Asignar o editar marcadores para este ejercicio")
        self.tags_button.clicked.connect(self.manage_home_tags)

        notes_header.addWidget(self.comment_button)
        notes_header.addWidget(self.tags_button)
        notes_card_layout.addLayout(notes_header)

        self.notes_browser = QTextBrowser()
        self.notes_browser.setObjectName("notes_browser")
        self.notes_browser.setOpenExternalLinks(True)
        self.notes_browser.setMinimumHeight(44)
        self.notes_browser.setMaximumHeight(115)
        self.notes_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.notes_browser.setToolTip("Doble clic o pulsa «APUNTES» para redactar o editar")
        self.notes_browser.mouseDoubleClickEvent = lambda _event: self.add_home_comment()
        placeholder_color = "#64748b" if self.is_dark_mode else "#94a3b8"
        self.notes_browser.setHtml(
            f"<p style='color: {placeholder_color}; font-style: italic; font-size: 11px; margin: 0;'>"
            "Sin apuntes para este ejercicio. Presiona «Apuntes» para redactar notas en Markdown."
            "</p>"
        )
        notes_card_layout.addWidget(self.notes_browser)

        outer.addWidget(self.notes_card)

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
        exercise_label = QLabel("ENFOQUE")
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
        break_label = QLabel("DESCANSO")
        break_label.setObjectName("eyebrow")
        br_top.addWidget(break_label)
        br_top.addStretch()
        break_layout.addLayout(br_top)

        self.break_clock.setObjectName("digital_clock_break")
        break_layout.addWidget(self.break_clock)
        metrics.addWidget(self.break_card, 2)
        outer.addLayout(metrics)

        # Controls Card
        self.controls_card = QFrame()
        controls_card = self.controls_card
        controls_card.setObjectName("sectionCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(22, 16, 22, 18)
        controls_layout.setSpacing(12)

        controls_header = QHBoxLayout()
        controls_header.addStretch()
        self.status_pill = QLabel(" ●  LISTO PARA COMENZAR")
        self.status_pill.setObjectName("status_badge")
        controls_header.addWidget(self.status_pill)
        controls_layout.addLayout(controls_header)

        # Primary Controls Grid (con ancho ergonómico no expandido)
        self.primary_controls = QGridLayout()
        self.primary_controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.primary_controls.setHorizontalSpacing(10)
        self.primary_controls.setVerticalSpacing(10)

        # Botón Enfoque y Descanso (unificado, como estaba antes)
        self.session_button = QPushButton("  INICIAR ENFOQUE")
        self.session_button.setObjectName("hero_start")
        self.session_button.setFixedHeight(44)
        self.session_button.setMinimumWidth(180)
        self.session_button.setMaximumWidth(240)
        self.session_button.setIcon(qta.icon("fa5s.play", color="#6ee7b7" if self.is_dark_mode else "#ffffff"))
        self.session_button.clicked.connect(self.toggle_session)

        # Alias para mantener compatibilidad
        self.break_button = self.session_button

        # Acciones Secundarias (38px, ancho ergonómico no expandido)
        self.complete_button = QPushButton("  COMPLETO")
        self.complete_button.setObjectName("complete")
        self.complete_button.setFixedHeight(38)
        self.complete_button.setMinimumWidth(110)
        self.complete_button.setMaximumWidth(150)
        self.complete_button.setIcon(qta.icon("fa5s.check-circle", color="#ffffff"))
        self.complete_button.clicked.connect(lambda: self.finish_item(True, keep_location=False))

        self.incomplete_button = QPushButton("  INCOMPLETO")
        self.incomplete_button.setObjectName("danger")
        self.incomplete_button.setFixedHeight(38)
        self.incomplete_button.setMinimumWidth(110)
        self.incomplete_button.setMaximumWidth(150)
        self.incomplete_button.setIcon(qta.icon("fa5s.times-circle", color="#fca5a5" if self.is_dark_mode else "#b91c1c"))
        self.incomplete_button.clicked.connect(lambda: self.finish_item(False, keep_location=True))

        self.stop_button = QPushButton("  DETENER")
        self.stop_button.setObjectName("stop")
        self.stop_button.setFixedHeight(38)
        self.stop_button.setMinimumWidth(100)
        self.stop_button.setMaximumWidth(130)
        self.stop_button.setIcon(qta.icon("fa5s.stop", color="#fca5a5" if self.is_dark_mode else "#b91c1c"))
        self.stop_button.clicked.connect(self.stop_timer)

        self.primary_buttons = (
            self.session_button,
            self.complete_button,
            self.incomplete_button,
            self.stop_button,
            self.comment_button,
            self.tags_button,
        )

        controls_layout.addLayout(self.primary_controls)
        self._arrange_session_controls(compact=False, very_compact=False)
        self.status_label = QLabel("Listo para comenzar")
        self.status_label.setObjectName("status")
        self.status_label.setVisible(False)
        controls_layout.addWidget(self.status_label)

        outer.addWidget(controls_card)

        # Panel de estado vacío
        self.empty_state_widget = EmptyStateWidget(is_dark_mode=self.is_dark_mode, parent=self)
        self.empty_state_widget.setVisible(False)
        outer.addWidget(self.empty_state_widget)

        outer.addStretch()

        scroll.setWidget(container)
        self.sync_location()

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    def set_empty_state(self, is_empty: bool) -> None:
        """Alterna la visualización del estado vacío protegiendo los controles de sesión."""
        self.empty_state_widget.setVisible(is_empty)
        if hasattr(self, "activity_strip"):
            self.activity_strip.setVisible(not is_empty)
        if hasattr(self, "hero_card"):
            self.hero_card.setVisible(not is_empty)
        if hasattr(self, "notes_card"):
            self.notes_card.setVisible(not is_empty)
        if hasattr(self, "controls_card"):
            self.controls_card.setVisible(not is_empty)
        if hasattr(self, "exercise_card"):
            self.exercise_card.setVisible(not is_empty)
        if hasattr(self, "break_card"):
            self.break_card.setVisible(not is_empty)

        self.set_locked(is_empty)
        self.session_button.setEnabled(not is_empty)
        if hasattr(self, "break_button") and self.break_button is not self.session_button:
            self.break_button.setEnabled(not is_empty and self.application.mode is not TimerMode.WAITING)
        self.comment_button.setEnabled(not is_empty)
        if hasattr(self, "tags_button"):
            self.tags_button.setEnabled(not is_empty)
        self.stop_button.setEnabled(not is_empty)
        self.complete_button.setEnabled(not is_empty)
        self.incomplete_button.setEnabled(not is_empty)

        if is_empty:
            self.status_pill.setText(" ●  SIN PROYECTO ACTIVO")
            self.status_label.setText("Ningún proyecto abierto")
            if hasattr(self, "personal_best_badge"):
                self.personal_best_badge.setText("🏆 Récord: --:--")
            if hasattr(self, "_refresh_exercise_chips"):
                self._refresh_exercise_chips()
        else:
            self.update_timer_visual_state()
            self.update_tags_visual_state()
            self.update_notes_visual_state()
            self.update_personal_best_badge()
            self.update_activity_strip()
            if hasattr(self, "_refresh_exercise_chips"):
                self._refresh_exercise_chips()
            self.status_label.setText("Listo para comenzar")

    def _create_stepper(self, spinbox: QSpinBox, tooltip_prefix: str) -> QWidget:
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
        btn_minus.setIconSize(QSize(15, 15))
        btn_minus.clicked.connect(spinbox.stepDown)

        btn_plus = QPushButton()
        btn_plus.setObjectName("stepper_button")
        btn_plus.setToolTip(f"Incrementar {tooltip_prefix}")
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.setIcon(qta.icon("fa5s.plus", color=icon_color))
        btn_plus.setIconSize(QSize(15, 15))
        btn_plus.clicked.connect(spinbox.stepUp)

        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(btn_minus)
        layout.addWidget(spinbox, 1)
        layout.addWidget(btn_plus)

        btn_minus.setProperty("spinbox", spinbox)
        btn_plus.setProperty("spinbox", spinbox)
        self.stepper_buttons.extend([btn_minus, btn_plus])
        return container

    def _arrange_session_controls(self, compact: bool = False, very_compact: bool = False) -> None:
        while self.primary_controls.count():
            self.primary_controls.takeAt(0)

        self.primary_controls.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.primary_controls.setHorizontalSpacing(10)
        self.primary_controls.setVerticalSpacing(10)

        if very_compact:
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
            self.primary_controls.addWidget(self.complete_button, 1, 0)
            self.primary_controls.addWidget(self.incomplete_button, 1, 1)
            self.primary_controls.addWidget(self.stop_button, 2, 0, 1, 2)
        elif compact:
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            self.primary_controls.addWidget(self.complete_button, 1, 0)
            self.primary_controls.addWidget(self.incomplete_button, 1, 1)
            self.primary_controls.addWidget(self.stop_button, 1, 2)
        else:
            # Fila Hero: Enfoque y Descanso unificado, centrado
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
            # Fila Secundaria: Acciones compactas
            self.primary_controls.addWidget(self.complete_button, 1, 0)
            self.primary_controls.addWidget(self.incomplete_button, 1, 1)
            self.primary_controls.addWidget(self.stop_button, 1, 2)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()
        compact = w < 960
        very_compact = w < 720

        if hasattr(self, "primary_controls"):
            self._arrange_session_controls(compact, very_compact)

        if hasattr(self, "metrics_layout"):
            self.metrics_layout.setDirection(
                QBoxLayout.Direction.TopToBottom if very_compact else QBoxLayout.Direction.LeftToRight
            )

    def sync_location(self, force: bool = False) -> None:
        location = SessionLocation(
            section_type=self.section_input.text().strip() or DEFAULT_SECTION_TYPE,
            section_number=self.section_number_input.value(),
            exercise=self.exercise_input.value(),
            inciso=self.inciso_input.value() or None,
        )
        is_active = self.application.mode is not TimerMode.WAITING
        self.application.set_location(location, force=force or is_active)

        suffix = f" · Inciso {location.inciso}" if location.inciso else ""
        text = f"{location.section_type} {location.section_number} · Ejercicio {location.exercise}{suffix}"

        st = self.application.get_exercise_status(
            location.section_type, location.section_number, location.exercise, location.inciso
        )
        is_dark = self.is_dark_mode
        if st == STATUS_COMPLETED:
            bg_col = "#064e3b" if is_dark else "#ecfdf5"
            border_col = "#059669" if is_dark else "#a7f3d0"
            text_col = "#6ee7b7" if is_dark else "#047857"
            hover_bg = "#065f46" if is_dark else "#d1fae5"
            status_desc = "Completado"
        elif st == STATUS_FAILED:
            bg_col = "#450a0a" if is_dark else "#fef2f2"
            border_col = "#7f1d1d" if is_dark else "#fecaca"
            text_col = "#fca5a5" if is_dark else "#b91c1c"
            hover_bg = "#5c1010" if is_dark else "#fee2e2"
            status_desc = "En dificultad"
        else:
            bg_col = "#1e293b" if is_dark else "#f1f5f9"
            border_col = "#334155" if is_dark else "#cbd5e1"
            text_col = "#94a3b8" if is_dark else "#64748b"
            hover_bg = "#334155" if is_dark else "#e2e8f0"
            status_desc = "Sin realizar"

        if self.application.is_record_open:
            tag_ids = self.application.get_exercise_tags(
                location.section_type, location.section_number, location.exercise, location.inciso
            )
            tag_catalog = {t.id: t for t in self.application.get_tag_catalog()}
            tags = [tag_catalog[tid] for tid in tag_ids if tid in tag_catalog]
        else:
            tags = []

        self.location_label.set_tags(tags)
        self.location_label.setText(text)

        tooltip_text = f"{text} ({status_desc})"
        if tags:
            tag_names = ", ".join(t.name for t in tags)
            tooltip_text += f"\nMarcadores: {tag_names}"
        tooltip_text += "\nHaz clic para ver detalles, notas o marcadores"

        self.location_label.setToolTip(tooltip_text)
        self.location_label.setCursor(Qt.CursorShape.PointingHandCursor)

        self.location_label.setStyleSheet(
            f"""
            QLabel#location_badge {{
                background-color: {bg_col};
                color: {text_col};
                border: 2px solid {border_col};
                border-radius: 10px;
                font-size: 24px;
                font-weight: 800;
                padding: 8px 16px;
                qproperty-alignment: AlignCenter;
            }}
            QLabel#location_badge:hover {{
                background-color: {hover_bg};
            }}
            """
        )

        self.update_tags_visual_state()
        self.update_notes_visual_state()
        self.update_personal_best_badge()
        if hasattr(self, "_refresh_exercise_chips"):
            self._refresh_exercise_chips()

    def update_personal_best_badge(self) -> None:
        if not hasattr(self, "personal_best_badge"):
            return
        if not self.application.is_record_open:
            self.personal_best_badge.setText("🏆 Récord: --:--")
            self.personal_best_badge.setToolTip("Sin proyecto activo")
            return

        loc = self.application.location
        pb_ms = self.application.get_exercise_personal_best_ms(
            loc.section_type, loc.section_number, loc.exercise, loc.inciso
        )
        if pb_ms is not None:
            pb_str = format_hh_mm_ss(pb_ms)
            self.personal_best_badge.setText(f"🏆 Récord: {pb_str}")
            self.personal_best_badge.setToolTip(f"Menor tiempo neto completado históricamente: {pb_str}")
        else:
            self.personal_best_badge.setText("🏆 Primer intento")
            self.personal_best_badge.setToolTip("Aún no se registran intentos completados para este ejercicio")

    def update_activity_strip(self) -> None:
        if not hasattr(self, "activity_strip"):
            return
        buckets = self.application.get_today_timeline_buckets()
        self.activity_strip.update_buckets(buckets)

    def set_locked(self, locked: bool) -> None:
        if not self.application.is_record_open:
            for widget in (self.section_input, self.section_number_input, self.exercise_input, self.inciso_input):
                widget.setEnabled(False)
            for btn in self.stepper_buttons:
                btn.setEnabled(False)
            if hasattr(self, "exercise_chips"):
                for chip in self.exercise_chips:
                    chip.setEnabled(False)
            if hasattr(self, "auto_advance_checkbox"):
                self.auto_advance_checkbox.setEnabled(False)
            return

        is_continuation = self.application.is_editing
        self.section_input.setEnabled(not locked and not is_continuation)
        self.section_number_input.setEnabled(not locked and not is_continuation)

        # En sesión normal, el ejercicio y el inciso permanecen editables para reasignación en caliente sin esperas
        self.exercise_input.setEnabled(not is_continuation)
        self.inciso_input.setEnabled(not is_continuation)
        if hasattr(self, "auto_advance_checkbox"):
            self.auto_advance_checkbox.setEnabled(not is_continuation)

        for btn in self.stepper_buttons:
            target = btn.property("spinbox")
            if target is self.section_number_input:
                btn.setEnabled(not locked and not is_continuation)
            else:
                btn.setEnabled(not is_continuation)

        if hasattr(self, "_refresh_exercise_chips"):
            self._refresh_exercise_chips()

    def toggle_session(self) -> None:
        if not self.application.is_record_open:
            QMessageBox.information(
                self.window(),
                "Sin proyecto activo",
                "No hay un proyecto activo.\nCrea o abre un registro para iniciar una sesión de estudio.",
            )
            return

        if self.application.mode is TimerMode.WAITING:
            self.sync_location()
            self.audio_service.play_start()
        self.application.toggle_session()

        self.set_locked(True)
        self.update_session_button()
        self.update_timer_visual_state()
        self.refresh_clock()

    def toggle_break(self) -> None:
        self.toggle_session()

    def update_session_button(self) -> None:
        is_dark = self.is_dark_mode
        mode = self.application.mode

        if mode is TimerMode.WAITING:
            self.session_button.setText("  INICIAR ENFOQUE")
            self.session_button.setIcon(qta.icon("fa5s.play", color="#6ee7b7" if is_dark else "#ffffff"))
            self.session_button.setObjectName("hero_start")
        elif mode is TimerMode.PLAY:
            self.session_button.setText("  TOMAR DESCANSO")
            self.session_button.setIcon(qta.icon("fa5s.coffee", color="#fbbf24" if is_dark else "#b45309"))
            self.session_button.setObjectName("hero_pause")
        elif mode is TimerMode.BREAK:
            self.session_button.setText("  CONTINUAR ENFOQUE")
            self.session_button.setIcon(qta.icon("fa5s.forward", color="#a7f3d0" if is_dark else "#047857"))
            self.session_button.setObjectName("hero_resume")

        self.session_button.style().unpolish(self.session_button)
        self.session_button.style().polish(self.session_button)

    def load_continuation_item(self, item: TimerItem) -> None:
        """Carga en pantalla el item a continuar, prellenando ubicación, tiempos y notas."""
        self.section_input.setText(item.section_type)
        self.section_number_input.setValue(item.section_number)
        self.exercise_input.setValue(item.exercise)
        self.inciso_input.setValue(item.inciso or 0)
        self.sync_location(force=True)
        self.set_locked(True)

        self.comment_button.setText("  APUNTES")
        if item.comment and item.comment.strip():
            clean = item.comment.strip()
            self.comment_button.setIcon(qta.icon("fa5s.sticky-note", color="#38bdf8"))
            self.comment_button.setToolTip(f"Apuntes para {item.section_type} {item.section_number} · Ej. {item.exercise}:\n{clean}")
            if hasattr(self, "notes_browser"):
                self.notes_browser.setMarkdown(clean)
        else:
            self.comment_button.setIcon(
                qta.icon("fa5s.sticky-note", color="#475569" if self.is_dark_mode else "#64748b")
            )
            self.comment_button.setToolTip("Ver o editar apuntes / notas para este ejercicio")
            if hasattr(self, "notes_browser"):
                placeholder_color = "#64748b" if self.is_dark_mode else "#94a3b8"
                self.notes_browser.setHtml(
                    f"<p style='color: {placeholder_color}; font-style: italic; font-size: 11px; margin: 0;'>"
                    "Sin apuntes registrados para este ejercicio. Presiona «Apuntes» para redactar en Markdown."
                    "</p>"
                )

        inciso_str = f" · Inciso {item.inciso}" if item.inciso else ""
        time_str = format_hh_mm_ss(item.exercise_time_ms)
        created_str = item.created_at[:16].replace("T", " ")
        self.continuation_label.setText(
            f"✏️ Modo continuación: editando {item.section_type} {item.section_number} · Ejercicio {item.exercise}{inciso_str} "
            f"(Tiempo previo: {time_str} · Guardado: {created_str})"
        )
        self.continuation_banner.setVisible(True)

        self.status_label.setText("Modo continuación listo para reanudar o registrar")
        self.update_session_button()
        self.update_timer_visual_state()
        self.refresh_clock()

    def cancel_continuation(self) -> None:
        """Solicita confirmación y cancela el modo continuación."""
        if QMessageBox.question(
            self.window(),
            "Cancelar continuación",
            "¿Desea descartar los cambios y volver a un intento limpio nuevo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        self.application.cancel_editing_session()
        self.clear_continuation_mode()

    def clear_continuation_mode(self) -> None:
        """Limpia los indicadores visuales del modo continuación."""
        self.continuation_banner.setVisible(False)
        self.set_locked(False)
        self.update_notes_visual_state()
        self.status_label.setText("Listo para comenzar")
        self.update_session_button()
        self.update_timer_visual_state()
        self.refresh_clock()

    def stop_timer(self) -> None:
        if self.application.is_editing:
            self.cancel_continuation()
            return

        self.application.stop_session()
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        self.update_notes_visual_state()
        self.update_personal_best_badge()
        self.status_label.setText("Listo para comenzar")

    def _prompt_inciso_gap_dialog(
        self,
        section_type: str,
        section_number: int,
        exercise: int,
        inciso: int | None,
        gap_items: list[TimerItem],
        always_resume: bool = False,
    ) -> tuple[str, str, int, int, int | None]:
        was_active = self.application.mode is not TimerMode.WAITING
        if was_active:
            self.application.pause_timer()
            self.update_timer_visual_state()
            self.refresh_clock()

        from presentation.inciso_dialog import (
            ACTION_CANCEL,
            ACTION_CORRECT_ALL,
            IncisoCorrectionDialog,
        )

        dlg = IncisoCorrectionDialog(
            parent=self.window(),
            section_type=section_type,
            section_number=section_number,
            exercise=exercise,
            current_inciso=inciso or 1,
            affected_count=len(gap_items),
            is_dark=self.is_dark_mode,
            gap_items=gap_items,
        )
        try:
            dlg.exec()
        finally:
            if was_active and (always_resume or dlg.result_action == ACTION_CANCEL):
                self.application.resume_timer()
                self.update_session_button()
                self.update_timer_visual_state()
                self.refresh_clock()

        if dlg.result_action == ACTION_CORRECT_ALL:
            self.application.promote_gap_items(gap_items, target_inciso=1)

        return (
            dlg.result_action,
            dlg.selected_section_type,
            dlg.selected_section_number,
            dlg.selected_exercise,
            dlg.selected_inciso,
        )

    def _resolve_inciso_gap(self) -> bool:
        loc = self.application.location
        gap_items = self.application.find_inciso_gap_candidates(
            loc.section_type,
            loc.section_number,
            loc.exercise,
            loc.inciso,
        )
        if not gap_items:
            return True

        from presentation.inciso_dialog import ACTION_CANCEL, ACTION_CUSTOM_VALUES

        action, sec_type, sec_num, ex, inc = self._prompt_inciso_gap_dialog(
            loc.section_type,
            loc.section_number,
            loc.exercise,
            loc.inciso,
            gap_items,
            always_resume=False,
        )

        if action == ACTION_CANCEL:
            return False
        elif action == ACTION_CUSTOM_VALUES:
            self.section_input.setText(sec_type)
            self.section_number_input.setValue(sec_num)
            self.exercise_input.setValue(ex)
            self.inciso_input.setValue(inc or 0)
            self.sync_location(force=True)
            return True
        return True

    def finish_item(self, completed: bool, keep_location: bool = False, stop: bool = False) -> None:
        if not self.application.is_record_open:
            return

        if self.application.mode is TimerMode.WAITING and not self.application.is_editing:
            return

        if not self._resolve_inciso_gap():
            return

        if completed:
            self.audio_service.play_complete()
        else:
            self.audio_service.play_fail()

        self.application.finish_item(completed, overwrite=True)
        self.clear_continuation_mode()
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        result = "completo" if completed else "incompleto"
        self.status_label.setText(f"Intento {result}. Listo para comenzar")
        self.update_notes_visual_state()

        if (
            completed
            and getattr(self, "auto_advance_checkbox", None)
            and self.auto_advance_checkbox.isChecked()
            and not keep_location
            and not stop
        ):
            self._auto_advance_next_exercise()
        else:
            self.sync_location()

        self.update_personal_best_badge()
        self.update_activity_strip()
        self.refresh_clock()
        if hasattr(self, "_refresh_exercise_chips"):
            self._refresh_exercise_chips()
        self.item_finished.emit(completed)

    def _auto_advance_next_exercise(self) -> None:
        """Avanza automáticamente al siguiente ejercicio o inciso planificado al completar con éxito."""
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        curr_ex = self.exercise_input.value()
        curr_inc = self.inciso_input.value()

        max_incisos = self.application.get_max_incisos_for_exercise(sec_type, sec_num, curr_ex)

        if max_incisos > 0:
            if curr_inc < max_incisos:
                self.inciso_input.setValue(curr_inc + 1)
            else:
                next_ex = curr_ex + 1
                self.exercise_input.setValue(next_ex)
                next_max = self.application.get_max_incisos_for_exercise(sec_type, sec_num, next_ex)
                self.inciso_input.setValue(1 if next_max > 0 else 0)
        else:
            if curr_inc > 0:
                self.inciso_input.setValue(curr_inc + 1)
            else:
                self.exercise_input.setValue(curr_ex + 1)

        self.sync_location()

    def _refresh_exercise_chips(self) -> None:
        """Actualiza la tira de 5 chips (el 3° es el actual), sin iconos y con los colores oficiales."""
        if not hasattr(self, "exercise_chips") or len(self.exercise_chips) < 5:
            return

        if not self.application.is_record_open:
            for btn in self.exercise_chips:
                btn.setText("—")
                btn.setEnabled(False)
                btn.setFixedSize(58, 32)
                btn.setToolTip("Sin proyecto activo")
                btn.setStyleSheet(
                    "QPushButton { background-color: transparent; color: #64748b; border: 1px dashed #475569; border-radius: 6px; font-size: 13px; padding: 0px 2px; text-align: center; }"
                )
            return

        current_ex = self.exercise_input.value()
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        is_dark = self.is_dark_mode

        # Índices relativos: [-2, -1, 0, 1, 2] -> el 3° chip (idx=2) es el ejercicio actual
        for idx, offset in enumerate([-2, -1, 0, 1, 2]):
            btn = self.exercise_chips[idx]
            btn.setFixedSize(58, 32)
            target_ex = current_ex + offset

            if target_ex < 1:
                btn.setText("—")
                btn.setEnabled(False)
                btn.setToolTip("")
                bg = "#1e293b" if is_dark else "#f1f5f9"
                border = "#334155" if is_dark else "#cbd5e1"
                text_col = "#64748b" if is_dark else "#94a3b8"
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {bg}; color: {text_col}; border: 1.5px dashed {border}; border-radius: 6px; font-weight: 600; font-size: 13px; padding: 0px 2px; text-align: center; }}"
                )
            else:
                btn.setText(str(target_ex))
                btn.setEnabled(True)
                st = self.application.get_exercise_status(sec_type, sec_num, target_ex)

                if st == STATUS_COMPLETED:
                    bg = "#064e3b" if is_dark else "#ecfdf5"
                    border = "#059669" if is_dark else "#a7f3d0"
                    text_col = "#6ee7b7" if is_dark else "#047857"
                    hover_bg = "#065f46" if is_dark else "#d1fae5"
                    st_name = "Completado"
                elif st == STATUS_FAILED:
                    bg = "#450a0a" if is_dark else "#fef2f2"
                    border = "#7f1d1d" if is_dark else "#fecaca"
                    text_col = "#fca5a5" if is_dark else "#b91c1c"
                    hover_bg = "#5c1010" if is_dark else "#fee2e2"
                    st_name = "En dificultad"
                else:  # STATUS_PENDING
                    bg = "#1e293b" if is_dark else "#f1f5f9"
                    border = "#334155" if is_dark else "#cbd5e1"
                    text_col = "#94a3b8" if is_dark else "#64748b"
                    hover_bg = "#334155" if is_dark else "#e2e8f0"
                    st_name = "Pendiente"

                if offset == 0:
                    # El 3° chip: Ejercicio Actual destacado
                    active_border = "#38bdf8" if is_dark else "#0284c7"
                    border_style = f"2.5px solid {active_border}"
                    font_weight = "800"
                    btn.setToolTip(
                        f"Ejercicio {target_ex} (Actual · {st_name})\nHaz clic para ver detalles, notas o marcadores"
                    )
                else:
                    border_style = f"1.5px solid {border}"
                    font_weight = "700" if st != STATUS_PENDING else "600"
                    btn.setToolTip(
                        f"Ejercicio {target_ex} ({st_name})\nHaz clic para ver detalles o cargar en cronómetro"
                    )

                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {bg};
                        color: {text_col};
                        border: {border_style};
                        border-radius: 6px;
                        font-weight: {font_weight};
                        font-size: 13px;
                        padding: 0px 2px;
                        text-align: center;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_bg};
                    }}
                    """
                )

    def _on_location_label_clicked(self, event=None) -> None:
        """Abre la ventana modal de detalle para el ejercicio actual (equivalente al 3° chip)."""
        if event is not None and hasattr(event, "button"):
            if event.button() != Qt.MouseButton.LeftButton:
                return
        self._on_chip_clicked(2)

    def _on_chip_clicked(self, chip_idx: int) -> None:
        """Abre la ventana modal de detalle (ExerciseDetailPopup) para el ejercicio clickeado."""
        if not self.application.is_record_open:
            return
        current_ex = self.exercise_input.value()
        target_ex = current_ex + (chip_idx - 2)
        if target_ex < 1:
            return

        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        inc = self.inciso_input.value() if (target_ex == current_ex and self.inciso_input.value() > 0) else None

        from presentation.planner_dialogs import ExerciseDetailPopup

        node = self.application.get_or_create_exercise_node(
            sec_type, sec_num, target_ex, inc
        )

        was_active = self.application.mode is TimerMode.PLAY
        if was_active:
            self.application.pause_timer()
            self.update_timer_visual_state()
            self.refresh_clock()

        try:
            dlg = ExerciseDetailPopup(
                parent=self.window(),
                node=node,
                app_service=self.application,
                is_dark=self.is_dark_mode,
            )
            if dlg.exec() == ExerciseDetailPopup.DialogCode.Accepted:
                if getattr(dlg, "chosen_action", None) == "load_timer":
                    self.exercise_input.setValue(node.exercise)
                    self.inciso_input.setValue(node.inciso or 0)
                    self.sync_location(force=True)
        finally:
            if was_active:
                self.application.resume_timer()
                self.update_session_button()
                self.update_timer_visual_state()
                self.refresh_clock()

        self.update_tags_visual_state()
        self.update_notes_visual_state()
        self._refresh_exercise_chips()

    def add_home_comment(self) -> None:
        if not self.application.is_record_open:
            return

        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        ex = self.exercise_input.value()
        inc = self.inciso_input.value() or None

        from presentation.planner_dialogs import ExerciseNoteDialog

        dlg = ExerciseNoteDialog(
            parent=self.window(),
            app_service=self.application,
            section_type=sec_type,
            section_number=sec_num,
            exercise=ex,
            inciso=inc,
            is_dark=self.is_dark_mode,
        )
        if dlg.exec() == ExerciseNoteDialog.DialogCode.Accepted:
            self.update_notes_visual_state()
            self.status_label.setText("Apuntes actualizados para el ejercicio actual")

    def manage_home_tags(self) -> None:
        if not self.application.is_record_open:
            return
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        ex = self.exercise_input.value()
        inc = self.inciso_input.value() or None

        from presentation.planner_dialogs import TagSelectionDialog
        dlg = TagSelectionDialog(
            parent=self.window(),
            app_service=self.application,
            section_type=sec_type,
            section_number=sec_num,
            exercise=ex,
            inciso=inc,
            is_dark=self.is_dark_mode,
        )
        if dlg.exec() == TagSelectionDialog.DialogCode.Accepted:
            self.update_tags_visual_state()

    def update_tags_visual_state(self) -> None:
        """Actualiza el aspecto del botón de marcadores y del recuadro de ubicación según si el ejercicio actual tiene etiquetas."""
        if not hasattr(self, "tags_button") or not self.application.is_record_open:
            if hasattr(self, "location_label") and hasattr(self.location_label, "set_tags"):
                self.location_label.set_tags([])
            return
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        ex = self.exercise_input.value()
        inc = self.inciso_input.value() or None

        tag_ids = self.application.get_exercise_tags(sec_type, sec_num, ex, inc)
        tag_catalog = {t.id: t for t in self.application.get_tag_catalog()}
        tags = [tag_catalog[tid] for tid in tag_ids if tid in tag_catalog]

        if hasattr(self, "location_label") and hasattr(self.location_label, "set_tags"):
            self.location_label.set_tags(tags)
            st = self.application.get_exercise_status(sec_type, sec_num, ex, inc)
            status_desc = "Completado" if st == STATUS_COMPLETED else ("En dificultad" if st == STATUS_FAILED else "Sin realizar")
            suffix = f" · Inciso {inc}" if inc else ""
            text = f"{sec_type} {sec_num} · Ejercicio {ex}{suffix}"
            tt = f"{text} ({status_desc})"
            if tags:
                tag_names = ", ".join(t.name for t in tags)
                tt += f"\nMarcadores: {tag_names}"
            tt += "\nHaz clic para ver detalles, notas o marcadores"
            self.location_label.setToolTip(tt)

        if tag_ids:
            self.tags_button.setText(f"  MARCADORES ({len(tag_ids)})")
            self.tags_button.setIcon(qta.icon("fa5s.tags", color="#a855f7"))
        else:
            self.tags_button.setText("  MARCADORES")
            self.tags_button.setIcon(qta.icon("fa5s.tags", color="#475569" if self.is_dark_mode else "#64748b"))

    def update_notes_visual_state(self) -> None:
        """Actualiza el aspecto del botón de notas y el panel de apuntes según si el ejercicio actual tiene apuntes."""
        if not hasattr(self, "comment_button") or not self.application.is_record_open:
            return
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        ex = self.exercise_input.value()
        inc = self.inciso_input.value() or None

        note = self.application.get_exercise_note(sec_type, sec_num, ex, inc)
        loc = self.application.location
        if (
            not note
            and self.application.pending_comment
            and loc.section_type.strip().lower() == sec_type.strip().lower()
            and loc.section_number == sec_num
            and loc.exercise == ex
            and loc.inciso == inc
        ):
            note = self.application.pending_comment

        self.comment_button.setText("  APUNTES")
        if note and note.strip():
            clean = note.strip()
            self.comment_button.setIcon(qta.icon("fa5s.sticky-note", color="#38bdf8"))
            self.comment_button.setToolTip(f"Apuntes para {sec_type} {sec_num} · Ej. {ex}:\n{clean}")
            if hasattr(self, "notes_browser"):
                self.notes_browser.setMarkdown(clean)
                self.notes_browser.setToolTip(f"Apuntes de {sec_type} {sec_num} · Ej. {ex}")
        else:
            self.comment_button.setIcon(
                qta.icon("fa5s.sticky-note", color="#475569" if self.is_dark_mode else "#64748b")
            )
            self.comment_button.setToolTip("Ver o editar apuntes / notas para este ejercicio")
            if hasattr(self, "notes_browser"):
                placeholder_color = "#64748b" if self.is_dark_mode else "#94a3b8"
                self.notes_browser.setHtml(
                    f"<p style='color: {placeholder_color}; font-style: italic; font-size: 11px; margin: 0;'>"
                    "Sin apuntes registrados para este ejercicio. Presiona «Apuntes» para redactar en Markdown."
                    "</p>"
                )
                self.notes_browser.setToolTip("Sin notas para este ejercicio")

    def refresh_clock(self) -> None:
        exercise_ms, break_ms = self.application.timer.snapshot()
        self.exercise_clock.setText(timer_markup(exercise_ms))
        self.break_clock.setText(timer_markup(break_ms))
        self.update_timer_visual_state()

        today_ms = self.application.get_today_study_time_ms(include_current=True)
        self.today_study_label.setText(format_hh_mm_ss(today_ms))

        metrics = self.application.get_today_summary_metrics()
        if hasattr(self, "today_completed_label"):
            self.today_completed_label.setText(str(metrics["completed_unique_count"]))
        if hasattr(self, "today_attempts_label"):
            self.today_attempts_label.setText(str(metrics["total_attempts"]))

        if hasattr(self, "activity_strip"):
            self.activity_strip.refresh_needle()

        self._strip_counter = getattr(self, "_strip_counter", 0) + 1
        if self._strip_counter % 20 == 0:
            self.update_activity_strip()

    def update_timer_visual_state(self) -> None:
        compact = self.width() < 1000
        clock_size = 38 if compact else 48
        break_size = 20 if compact else 25
        is_dark = self.is_dark_mode

        if self.application.is_timer_paused:
            state = "paused"
            pill_text = " ⏸  PAUSADO"
            ex_color = "#94a3b8" if is_dark else "#78716c"
            br_color = "#64748b" if is_dark else "#a8a29e"
        elif self.application.mode is TimerMode.PLAY:
            state = "play"
            pill_text = " ●  ENFOQUE EN CURSO"
            ex_color = "#34d399" if is_dark else "#047857"
            br_color = "#64748b" if is_dark else "#a8a29e"
        elif self.application.mode is TimerMode.BREAK:
            state = "break"
            pill_text = " ●  DESCANSO EN CURSO"
            ex_color = "#64748b" if is_dark else "#a8a29e"
            br_color = "#fbbf24" if is_dark else "#b45309"
        else:
            state = "waiting"
            pill_text = " ●  LISTO PARA COMENZAR"
            ex_color = "#f1f5f9" if is_dark else "#1c1917"
            br_color = "#64748b" if is_dark else "#78716c"

        ex_card_style, br_card_style = get_timer_cards_style(state, is_dark)
        if hasattr(self, "exercise_card"):
            self.exercise_card.setStyleSheet(ex_card_style)
            self.break_card.setStyleSheet(br_card_style)

        self.exercise_clock.setStyleSheet(f"color: {ex_color}; font-size: {clock_size}px; font-weight: 800;")
        self.break_clock.setStyleSheet(f"color: {br_color}; font-size: {break_size}px; font-weight: 700;")

        if hasattr(self, "status_pill"):
            self.status_pill.setText(pill_text)
            self.status_pill.setStyleSheet(get_status_pill_style(state, is_dark))
