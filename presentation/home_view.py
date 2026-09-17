"""Vista Home / Cronómetro de Study Timetrial."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QBoxLayout,
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
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import SessionLocation, StudyApplicationService
from domain.models import TimerItem
from domain.timer_service import TimerMode
from presentation.audio_service import AudioService
from presentation.empty_state_widget import EmptyStateWidget
from presentation.presentation_formatters import format_hh_mm_ss, timer_markup
from presentation.theme import get_status_pill_style, get_timer_cards_style

if TYPE_CHECKING:
    from presentation.main_window import MainWindow

DEFAULT_SECTION_TYPE = "Guía"
APP_TITLE = "Study Timetrial"
APP_VERSION = "v1.0"
MAX_VALUE = 999_999


class HomeViewWidget(QWidget):
    """Vista principal con el cronómetro de estudio y controles de intento."""

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

        self._build_ui()

    @property
    def is_dark_mode(self) -> bool:
        return self._is_dark_mode

    @is_dark_mode.setter
    def is_dark_mode(self, value: bool) -> None:
        self._is_dark_mode = bool(value)
        if hasattr(self, "empty_state_widget"):
            self.empty_state_widget.set_dark_mode(self._is_dark_mode)
        self.update_timer_visual_state()

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

        # Hero Card: Ubicación
        self.hero_card = QFrame()
        hero = self.hero_card
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
        self.controls_card = QFrame()
        controls_card = self.controls_card
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

        # Primary Controls Grid
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

        self.comment_button = QPushButton("  APUNTES")
        self.comment_button.setObjectName("comment_action")
        self.comment_button.setIcon(qta.icon("fa5s.sticky-note", color="#475569"))
        self.comment_button.setToolTip("Ver o editar apuntes / notas para este ejercicio")
        self.comment_button.clicked.connect(self.add_home_comment)
        self.notes_button = self.comment_button

        self.tags_button = QPushButton("  MARCADORES")
        self.tags_button.setObjectName("tags_action")
        self.tags_button.setIcon(qta.icon("fa5s.tags", color="#475569"))
        self.tags_button.setToolTip("Asignar o editar marcadores para este ejercicio")
        self.tags_button.clicked.connect(self.manage_home_tags)

        self.primary_buttons = (
            self.session_button,
            self.stop_button,
            self.comment_button,
            self.tags_button,
            self.complete_button,
            self.incomplete_button,
        )
        for button in self.primary_buttons:
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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
        if hasattr(self, "hero_card"):
            self.hero_card.setVisible(not is_empty)
        if hasattr(self, "controls_card"):
            self.controls_card.setVisible(not is_empty)
        if hasattr(self, "exercise_card"):
            self.exercise_card.setVisible(not is_empty)
        if hasattr(self, "break_card"):
            self.break_card.setVisible(not is_empty)

        self.set_locked(is_empty)
        self.session_button.setEnabled(not is_empty)
        self.comment_button.setEnabled(not is_empty)
        if hasattr(self, "tags_button"):
            self.tags_button.setEnabled(not is_empty)
        self.stop_button.setEnabled(not is_empty)
        self.complete_button.setEnabled(not is_empty)
        self.incomplete_button.setEnabled(not is_empty)

        if is_empty:
            self.status_pill.setText(" ●  SIN PROYECTO ACTIVO")
            self.status_label.setText("Ningún proyecto abierto")
        else:
            self.update_timer_visual_state()
            self.update_tags_visual_state()
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

        self.stepper_buttons.extend([btn_minus, btn_plus])
        return container

    def _arrange_session_controls(self, compact: bool = False, very_compact: bool = False) -> None:
        while self.primary_controls.count():
            self.primary_controls.takeAt(0)

        for col in range(4):
            self.primary_controls.setColumnStretch(col, 1)

        if very_compact:
            for idx, btn in enumerate(self.primary_buttons):
                self.primary_controls.addWidget(btn, idx, 0)
        elif compact:
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 2)
            self.primary_controls.addWidget(self.stop_button, 1, 0)
            self.primary_controls.addWidget(self.comment_button, 1, 1)
            self.primary_controls.addWidget(self.tags_button, 2, 0, 1, 2)
            self.primary_controls.addWidget(self.complete_button, 3, 0)
            self.primary_controls.addWidget(self.incomplete_button, 3, 1)
        else:
            self.primary_controls.addWidget(self.session_button, 0, 0, 1, 2)
            self.primary_controls.addWidget(self.comment_button, 0, 2)
            self.primary_controls.addWidget(self.tags_button, 0, 3)
            self.primary_controls.addWidget(self.complete_button, 1, 0, 1, 2)
            self.primary_controls.addWidget(self.incomplete_button, 1, 2)
            self.primary_controls.addWidget(self.stop_button, 1, 3)

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
        self.application.set_location(location, force=force)

        suffix = f" · Inciso {location.inciso}" if location.inciso else ""
        text = f"{location.section_type} {location.section_number} · Ejercicio {location.exercise}{suffix}"
        self.location_label.setText(text)
        self.update_tags_visual_state()
        self.update_notes_visual_state()

    def set_locked(self, locked: bool) -> None:
        for widget in (self.section_input, self.section_number_input, self.exercise_input, self.inciso_input):
            widget.setEnabled(not locked)
        for btn in self.stepper_buttons:
            btn.setEnabled(not locked)

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

    def update_session_button(self) -> None:
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

    def load_continuation_item(self, item: TimerItem) -> None:
        """Carga en pantalla el item a continuar, prellenando ubicación, tiempos y notas."""
        self.section_input.setText(item.section_type)
        self.section_number_input.setValue(item.section_number)
        self.exercise_input.setValue(item.exercise)
        self.inciso_input.setValue(item.inciso or 0)
        self.sync_location(force=True)
        self.set_locked(True)

        if item.comment:
            clean = item.comment.strip()
            short = (clean[:25] + "…") if len(clean) > 25 else clean
            self.comment_button.setText(f'  COMENTARIO: "{short}"')
        else:
            self.comment_button.setText("  COMENTARIO")

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

        self.application.finish_item(completed, overwrite=True)
        self.clear_continuation_mode()
        self.set_locked(False)
        self.update_session_button()
        self.update_timer_visual_state()
        result = "completo" if completed else "incompleto"
        self.status_label.setText(f"Intento {result}. Listo para comenzar")
        self.update_notes_visual_state()

        if not keep_location and not stop:
            self.sync_location()

        self.refresh_clock()
        self.item_finished.emit(completed)

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
        """Actualiza el aspecto del botón de marcadores según si el ejercicio actual tiene etiquetas."""
        if not hasattr(self, "tags_button") or not self.application.is_record_open:
            return
        sec_type = self.section_input.text().strip() or DEFAULT_SECTION_TYPE
        sec_num = self.section_number_input.value()
        ex = self.exercise_input.value()
        inc = self.inciso_input.value() or None

        tag_ids = self.application.get_exercise_tags(sec_type, sec_num, ex, inc)
        if tag_ids:
            self.tags_button.setText(f"  MARCADORES ({len(tag_ids)})")
            self.tags_button.setIcon(qta.icon("fa5s.tags", color="#a855f7"))
        else:
            self.tags_button.setText("  MARCADORES")
            self.tags_button.setIcon(qta.icon("fa5s.tags", color="#475569" if self.is_dark_mode else "#64748b"))

    def update_notes_visual_state(self) -> None:
        """Actualiza el aspecto del botón de notas según si el ejercicio actual tiene apuntes."""
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

        if note and note.strip():
            clean = note.strip()
            short = (clean[:18] + "…") if len(clean) > 18 else clean
            self.comment_button.setText(f'  APUNTES: "{short}"')
            self.comment_button.setIcon(qta.icon("fa5s.sticky-note", color="#38bdf8"))
            self.comment_button.setToolTip(f"Apuntes para {sec_type} {sec_num} · Ej. {ex}:\n{clean}")
        else:
            self.comment_button.setText("  APUNTES")
            self.comment_button.setIcon(
                qta.icon("fa5s.sticky-note", color="#475569" if self.is_dark_mode else "#64748b")
            )
            self.comment_button.setToolTip("Ver o editar apuntes / notas para este ejercicio")

    def refresh_clock(self) -> None:
        exercise_ms, break_ms = self.application.timer.snapshot()
        self.exercise_clock.setText(timer_markup(exercise_ms))
        self.break_clock.setText(timer_markup(break_ms))
        self.update_timer_visual_state()

        today_ms = self.application.get_today_study_time_ms(include_current=True)
        self.today_study_label.setText(format_hh_mm_ss(today_ms))

    def update_timer_visual_state(self) -> None:
        compact = self.width() < 1000
        clock_size = 38 if compact else 48
        break_size = 20 if compact else 25
        is_dark = self.is_dark_mode

        if self.application.is_timer_paused:
            state = "paused"
            pill_text = " ⏸  PAUSADO"
            ex_color = "#94a3b8"
            br_color = "#64748b"
        elif self.application.mode is TimerMode.PLAY:
            state = "play"
            pill_text = " ●  SESIÓN EN CURSO"
            ex_color = "#34d399"
            br_color = "#64748b"
        elif self.application.mode is TimerMode.BREAK:
            state = "break"
            pill_text = " ●  RECESO EN CURSO"
            ex_color = "#64748b"
            br_color = "#fbbf24"
        else:
            state = "waiting"
            pill_text = " ●  LISTO PARA COMENZAR"
            ex_color = "#e2e8f0" if is_dark else "#0f172a"
            br_color = "#64748b"

        ex_card_style, br_card_style = get_timer_cards_style(state, is_dark)
        if hasattr(self, "exercise_card"):
            self.exercise_card.setStyleSheet(ex_card_style)
            self.break_card.setStyleSheet(br_card_style)

        self.exercise_clock.setStyleSheet(f"color: {ex_color}; font-size: {clock_size}px; font-weight: 800;")
        self.break_clock.setStyleSheet(f"color: {br_color}; font-size: {break_size}px; font-weight: 700;")

        if hasattr(self, "status_pill"):
            self.status_pill.setText(pill_text)
            self.status_pill.setStyleSheet(get_status_pill_style(state, is_dark))
