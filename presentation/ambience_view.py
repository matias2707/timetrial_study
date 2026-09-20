"""Vista interactiva de Ambientación Sonora con mezclador multicanal adaptativo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from presentation.audio_mixer_engine import AudioMixerEngine, MAX_ACTIVE_TRACKS


class TrackCardWidget(QFrame):
    """Tarjeta individual de control para una pista de audio."""

    volume_changed = Signal(str, float)  # filename, volume (0.0 a 1.0)
    mute_toggled = Signal(str, bool)

    def __init__(
        self,
        filename: str,
        display_name: str,
        initial_volume: float = 0.0,
        is_dark: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.filename = filename
        self.display_name = display_name
        self.is_dark = is_dark
        self.is_muted = False

        self.setObjectName("kpiCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui(initial_volume)

    def _build_ui(self, initial_volume: float) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header fila 1: Icono, Título y Badge de estado
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_name = "fa5s.music"
        low = self.display_name.lower()
        if "acondicionado" in low or "air" in low or "fan" in low:
            icon_name = "fa5s.wind"
        elif "lluvia" in low or "rain" in low or "agua" in low:
            icon_name = "fa5s.water"
        elif "marron" in low or "brown" in low:
            icon_name = "fa5s.adjust"
        elif "azul" in low or "blue" in low:
            icon_name = "fa5s.tint"

        self._icon_name = icon_name
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon(self._icon_name, color="#38bdf8" if self.is_dark else "#0284c7").pixmap(20, 20))
        top_row.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(self.display_name)
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold;")
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.status_badge = QLabel("Pausado")
        self._last_status = "paused"
        self._apply_status_badge_style("paused")
        top_row.addWidget(self.status_badge)

        self.mute_btn = QPushButton()
        self.mute_btn.setObjectName("trackMuteBtn")
        self.mute_btn.setFixedSize(28, 28)
        self.mute_btn.setToolTip("Silenciar esta pista")
        self._update_mute_icon()
        self.mute_btn.clicked.connect(self._on_mute_clicked)
        top_row.addWidget(self.mute_btn)

        layout.addLayout(top_row)

        # Fila 2: Slider de volumen y porcentaje
        vol_row = QHBoxLayout()
        vol_row.setSpacing(12)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        int_vol = int(round(initial_volume * 100))
        self.slider.setValue(int_vol)
        self.slider.valueChanged.connect(self._on_slider_changed)
        vol_row.addWidget(self.slider)

        self.vol_label = QLabel(f"{int_vol}%")
        self.vol_label.setFixedWidth(38)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.vol_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        vol_row.addWidget(self.vol_label)

        layout.addLayout(vol_row)

    def set_volume_display(self, volume: float) -> None:
        """Actualiza el slider sin disparar señales recursivas."""
        int_val = int(round(max(0.0, min(1.0, volume)) * 100))
        self.slider.blockSignals(True)
        self.slider.setValue(int_val)
        self.slider.blockSignals(False)
        self.vol_label.setText(f"{int_val}%")

    def _apply_status_badge_style(self, status: str | None = None) -> None:
        if status is None:
            status = getattr(self, "_last_status", "paused")
        if status == "playing":
            self.status_badge.setText("● En reproducción")
            if self.is_dark:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.2); color: #34d399; font-weight: bold;"
                )
            else:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #e7f4ec; border: 1px solid #b6e1c6; color: #047857; font-weight: bold;"
                )
        elif status == "error":
            self.status_badge.setText("⚠️ Error de archivo")
            if self.is_dark:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(239, 68, 68, 0.2); color: #f87171;"
                )
            else:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #fae9e9; border: 1px solid #f4bcbc; color: #dc2626;"
                )
        else:
            self.status_badge.setText("Pausado")
            if self.is_dark:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(100, 116, 139, 0.2); color: #94a3b8;"
                )
            else:
                self.status_badge.setStyleSheet(
                    "font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #ede8dd; border: 1px solid #d5cdbf; color: #57534e;"
                )

    def set_playback_status(self, status: str) -> None:
        """Actualiza el indicador visual de estado ('playing', 'paused', 'error')."""
        if getattr(self, "_last_status", None) == status:
            return
        self._last_status = status
        self._apply_status_badge_style(status)

    def _on_slider_changed(self, value: int) -> None:
        vol = value / 100.0
        self.vol_label.setText(f"{value}%")
        self.volume_changed.emit(self.filename, vol)

    def _update_mute_icon(self) -> None:
        if self.is_muted:
            self.mute_btn.setIcon(qta.icon("fa5s.volume-mute", color="#ef4444"))
        else:
            color = "#94a3b8" if self.is_dark else "#78716c"
            self.mute_btn.setIcon(qta.icon("fa5s.volume-up", color=color))

    def _on_mute_clicked(self) -> None:
        self.is_muted = not self.is_muted
        self._update_mute_icon()
        self.mute_toggled.emit(self.filename, self.is_muted)

    def update_theme(self, is_dark: bool) -> None:
        """Actualiza el aspecto de la tarjeta al cambiar el tema de la aplicación."""
        self.is_dark = is_dark
        icon_color = "#38bdf8" if self.is_dark else "#0284c7"
        self.icon_lbl.setPixmap(qta.icon(self._icon_name, color=icon_color).pixmap(20, 20))
        self._apply_status_badge_style()
        self._update_mute_icon()


class AmbienceViewWidget(QWidget):
    """Pestaña de ambientación sonora con mezclador multicanal adaptativo al cronómetro."""

    def __init__(
        self,
        engine: AudioMixerEngine | None = None,
        is_dark_mode: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine or AudioMixerEngine(parent=self)
        self.is_dark = is_dark_mode
        self.selected_scene: str = "study"  # Escena que el usuario está viendo/editando en la UI

        self.cards: dict[str, TrackCardWidget] = {}

        self._build_ui()
        self._connect_signals()
        self._refresh_track_cards()
        self._sync_preset_dropdown()

    def set_dark_mode(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self._update_theme_styles()

    def _update_theme_styles(self) -> None:
        for card in self.cards.values():
            card.update_theme(self.is_dark)
        self._update_scene_buttons()
        if not self.engine.is_master_muted:
            color = "#10b981" if self.is_dark else "#059669"
            self.master_mute_btn.setIcon(qta.icon("fa5s.volume-up", color=color))

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 24, 36, 28)
        main_layout.setSpacing(16)

        # 1. Cabecera
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Ambientación Sonora")
        title.setObjectName("brand")
        subtitle = QLabel("Mezclador multicanal adaptativo · Música de enfoque y ruidos ambientales")
        subtitle.setObjectName("record_meta")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Botones rápidos de carpeta y actualización
        self.btn_open_folder = QPushButton(" Abrir carpeta de audios")
        self.btn_open_folder.setObjectName("secondary_action")
        self.btn_open_folder.setIcon(qta.icon("fa5s.folder-open", color="#3b82f6"))
        self.btn_open_folder.clicked.connect(self._open_audio_folder)
        header_layout.addWidget(self.btn_open_folder)

        self.btn_refresh_tracks = QPushButton(" Actualizar pistas")
        self.btn_refresh_tracks.setObjectName("secondary_action")
        self.btn_refresh_tracks.setIcon(qta.icon("fa5s.sync", color="#10b981"))
        self.btn_refresh_tracks.clicked.connect(self._refresh_audio_tracks)
        header_layout.addWidget(self.btn_refresh_tracks)

        main_layout.addLayout(header_layout)

        # 2. Tarjeta Master: Volumen Maestro, Duración de Fade y Presets
        master_card = QFrame()
        master_card.setObjectName("kpiCard")
        master_layout = QHBoxLayout(master_card)
        master_layout.setContentsMargins(18, 12, 18, 12)
        master_layout.setSpacing(20)

        # Master Volume
        vol_box = QVBoxLayout()
        vol_box.setSpacing(4)
        vol_header = QHBoxLayout()
        self.master_mute_btn = QPushButton()
        self.master_mute_btn.setFixedSize(26, 26)
        self.master_mute_btn.setIcon(qta.icon("fa5s.volume-up", color="#10b981"))
        self.master_mute_btn.setToolTip("Silenciar todo el audio ambiental")
        self.master_mute_btn.clicked.connect(self._toggle_master_mute)
        vol_header.addWidget(self.master_mute_btn)

        vol_lbl = QLabel("VOLUMEN GENERAL")
        vol_lbl.setObjectName("kpi_title")
        vol_header.addWidget(vol_lbl)
        self.master_vol_val = QLabel(f"{int(self.engine.master_volume * 100)}%")
        self.master_vol_val.setObjectName("kpi_title")
        self.master_vol_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        vol_header.addWidget(self.master_vol_val)
        vol_box.addLayout(vol_header)

        self.master_slider = QSlider(Qt.Orientation.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(int(self.engine.master_volume * 100))
        self.master_slider.valueChanged.connect(self._on_master_slider_changed)
        vol_box.addWidget(self.master_slider)
        master_layout.addLayout(vol_box, stretch=2)

        # Fade In (Entrada)
        fade_in_box = QVBoxLayout()
        fade_in_box.setSpacing(4)
        fade_in_header = QHBoxLayout()
        fade_in_lbl = QLabel("FADE IN (ENTRADA)")
        fade_in_lbl.setObjectName("kpi_title")
        fade_in_header.addWidget(fade_in_lbl)
        self.fade_in_val_lbl = QLabel(f"{self.engine.fade_in_sec:.1f}s")
        self.fade_in_val_lbl.setObjectName("kpi_title")
        self.fade_in_val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        fade_in_header.addWidget(self.fade_in_val_lbl)
        fade_in_box.addLayout(fade_in_header)

        self.fade_in_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_in_slider.setRange(5, 50)  # 0.5s a 5.0s
        self.fade_in_slider.setValue(int(round(self.engine.fade_in_sec * 10)))
        self.fade_in_slider.valueChanged.connect(self._on_fade_in_slider_changed)
        fade_in_box.addWidget(self.fade_in_slider)
        master_layout.addLayout(fade_in_box, stretch=2)

        # Fade Out (Salida)
        fade_out_box = QVBoxLayout()
        fade_out_box.setSpacing(4)
        fade_out_header = QHBoxLayout()
        fade_out_lbl = QLabel("FADE OUT (SALIDA)")
        fade_out_lbl.setObjectName("kpi_title")
        fade_out_header.addWidget(fade_out_lbl)
        self.fade_out_val_lbl = QLabel(f"{self.engine.fade_out_sec:.1f}s")
        self.fade_out_val_lbl.setObjectName("kpi_title")
        self.fade_out_val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        fade_out_header.addWidget(self.fade_out_val_lbl)
        fade_out_box.addLayout(fade_out_header)

        self.fade_out_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_out_slider.setRange(5, 50)  # 0.5s a 5.0s
        self.fade_out_slider.setValue(int(round(self.engine.fade_out_sec * 10)))
        self.fade_out_slider.valueChanged.connect(self._on_fade_out_slider_changed)
        fade_out_box.addWidget(self.fade_out_slider)
        master_layout.addLayout(fade_out_box, stretch=2)

        # Aliases para compatibilidad hacia atrás
        self.fade_slider = self.fade_in_slider
        self.fade_val_lbl = self.fade_in_val_lbl

        # Presets
        preset_box = QVBoxLayout()
        preset_box.setSpacing(4)
        preset_lbl = QLabel("PRESET DE AMBIENTE")
        preset_lbl.setObjectName("kpi_title")
        preset_box.addWidget(preset_lbl)

        preset_controls = QHBoxLayout()
        preset_controls.setSpacing(6)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(180)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_combo_changed)
        preset_controls.addWidget(self.preset_combo)

        self.btn_save_preset = QPushButton()
        self.btn_save_preset.setFixedSize(28, 28)
        self.btn_save_preset.setIcon(qta.icon("fa5s.save", color="#3b82f6"))
        self.btn_save_preset.setToolTip("Guardar cambios en el preset activo")
        self.btn_save_preset.clicked.connect(self._on_save_preset)
        preset_controls.addWidget(self.btn_save_preset)

        self.btn_new_preset = QPushButton()
        self.btn_new_preset.setFixedSize(28, 28)
        self.btn_new_preset.setIcon(qta.icon("fa5s.plus", color="#10b981"))
        self.btn_new_preset.setToolTip("Guardar mezcla como nuevo preset...")
        self.btn_new_preset.clicked.connect(self._on_new_preset)
        preset_controls.addWidget(self.btn_new_preset)

        self.btn_delete_preset = QPushButton()
        self.btn_delete_preset.setFixedSize(28, 28)
        self.btn_delete_preset.setIcon(qta.icon("fa5s.trash-alt", color="#ef4444"))
        self.btn_delete_preset.setToolTip("Eliminar preset actual")
        self.btn_delete_preset.clicked.connect(self._on_delete_preset)
        preset_controls.addWidget(self.btn_delete_preset)

        preset_box.addLayout(preset_controls)
        master_layout.addLayout(preset_box, stretch=3)

        main_layout.addWidget(master_card)

        # 3. Barra de Selección de Escena / Estado
        scene_bar = QHBoxLayout()
        scene_bar.setSpacing(10)

        scene_title = QLabel("Configurar volúmenes para:")
        scene_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        scene_bar.addWidget(scene_title)

        self.btn_scene_study = QPushButton(" 🟢 Tiempo Neto (Estudio)")
        self.btn_scene_study.setCheckable(True)
        self.btn_scene_study.clicked.connect(lambda: self._select_scene("study"))
        scene_bar.addWidget(self.btn_scene_study)

        self.btn_scene_break = QPushButton(" 🟡 Receso (Descanso)")
        self.btn_scene_break.setCheckable(True)
        self.btn_scene_break.clicked.connect(lambda: self._select_scene("break_state"))
        scene_bar.addWidget(self.btn_scene_break)

        self.btn_scene_main = QPushButton(" ⚪ Espera / Pausa (Main)")
        self.btn_scene_main.setCheckable(True)
        self.btn_scene_main.clicked.connect(lambda: self._select_scene("main_state"))
        scene_bar.addWidget(self.btn_scene_main)

        scene_bar.addStretch()

        # Botón de Audición en vivo
        self.btn_audition = QPushButton(" ▶️ Audicionar esta escena")
        self.btn_audition.setCheckable(True)
        self.btn_audition.setStyleSheet(
            "padding: 6px 14px; font-weight: bold; border-radius: 6px;"
        )
        self.btn_audition.clicked.connect(self._toggle_audition)
        scene_bar.addWidget(self.btn_audition)

        main_layout.addLayout(scene_bar)

        # 4. Scroll Area con lista de tarjetas de pistas
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ambienceScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")

        self.tracks_container = QWidget()
        self.tracks_container.setObjectName("ambienceContainer")
        self.tracks_layout = QVBoxLayout(self.tracks_container)
        self.tracks_layout.setContentsMargins(0, 0, 0, 0)
        self.tracks_layout.setSpacing(10)

        self.scroll_area.setWidget(self.tracks_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self._update_scene_buttons()

    def _connect_signals(self) -> None:
        self.engine.tracks_refreshed.connect(self._refresh_track_cards)
        self.engine.track_status_changed.connect(self._on_track_status_changed)
        self.engine.scene_changed.connect(self._on_engine_scene_changed)
        self.engine.fade_in_changed.connect(self._on_engine_fade_in_changed)
        self.engine.fade_out_changed.connect(self._on_engine_fade_out_changed)
        self.engine.master_volume_changed.connect(self._on_engine_master_volume_changed)
        self.engine.master_muted_changed.connect(self._on_engine_master_muted_changed)

    def _open_audio_folder(self) -> None:
        audio_dir = self.engine.storage.audio_dir
        audio_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(audio_dir.resolve())))

    def _refresh_audio_tracks(self) -> None:
        self.engine.refresh_tracks()

    def _refresh_track_cards(self) -> None:
        """Reconstruye las tarjetas de pistas según los audios escaneados."""
        # Limpiar contenedor
        while self.tracks_layout.count():
            item = self.tracks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        tracks = self.engine.storage.scan_audio_tracks()
        if not tracks:
            empty_box = QFrame()
            empty_box.setObjectName("kpiCard")
            eb_layout = QVBoxLayout(empty_box)
            eb_layout.setContentsMargins(30, 40, 30, 40)
            eb_layout.setSpacing(12)
            eb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_lbl = QLabel()
            icon_lbl.setPixmap(qta.icon("fa5s.music", color="#64748b").pixmap(48, 48))
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            eb_layout.addWidget(icon_lbl)

            msg_title = QLabel("No se encontraron pistas de audio")
            msg_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #94a3b8;")
            msg_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            eb_layout.addWidget(msg_title)

            msg_sub = QLabel("Coloca archivos .mp3, .m4a, .wav o .flac en la carpeta de audios para comenzar.")
            msg_sub.setStyleSheet("font-size: 13px; color: #64748b;")
            msg_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            eb_layout.addWidget(msg_sub)

            btn_open = QPushButton(" Abrir carpeta data/ambient")
            btn_open.setObjectName("toolbar_primary")
            btn_open.setFixedWidth(220)
            btn_open.setIcon(qta.icon("fa5s.folder-open", color="#ffffff"))
            btn_open.clicked.connect(self._open_audio_folder)
            eb_layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignCenter)

            self.tracks_layout.addWidget(empty_box)
            return

        for track in tracks:
            fn = track["filename"]
            initial_vol = self.engine.get_track_scene_volume(fn, self.selected_scene)
            card = TrackCardWidget(
                filename=fn,
                display_name=track["name"],
                initial_volume=initial_vol,
                is_dark=self.is_dark,
            )
            card.volume_changed.connect(self._on_track_volume_changed)
            card.mute_toggled.connect(self._on_track_mute_toggled)
            self.cards[fn] = card
            self.tracks_layout.addWidget(card)

        self.tracks_layout.addStretch()

    def sync_ui_state(self) -> None:
        """Sincroniza los controles de la interfaz sin destruir ni recrear los widgets de tarjetas."""
        self.master_slider.blockSignals(True)
        self.master_slider.setValue(int(round(self.engine.master_volume * 100)))
        self.master_slider.blockSignals(False)
        self.master_vol_val.setText(f"{int(round(self.engine.master_volume * 100))}%")

        self.fade_in_slider.blockSignals(True)
        self.fade_in_slider.setValue(int(round(self.engine.fade_in_sec * 10)))
        self.fade_in_slider.blockSignals(False)
        self.fade_in_val_lbl.setText(f"{self.engine.fade_in_sec:.1f}s")

        self.fade_out_slider.blockSignals(True)
        self.fade_out_slider.setValue(int(round(self.engine.fade_out_sec * 10)))
        self.fade_out_slider.blockSignals(False)
        self.fade_out_val_lbl.setText(f"{self.engine.fade_out_sec:.1f}s")

        self._sync_preset_dropdown()
        self._update_scene_buttons()
        self.sync_audition_button()
        self._on_engine_master_muted_changed(self.engine.is_master_muted)

        for fn, card in self.cards.items():
            vol = self.engine.get_track_scene_volume(fn, self.selected_scene)
            card.set_volume_display(vol)
            if fn in self.engine.players:
                tp = self.engine.players[fn]
                status = "playing" if (tp._is_playing or tp.audio_output.volume() > 0.001) else "paused"
                card.set_playback_status(status)

    def _select_scene(self, scene: str) -> None:
        self.selected_scene = scene
        self._update_scene_buttons()

        # Actualizar sliders con los volúmenes de la escena seleccionada
        for fn, card in self.cards.items():
            vol = self.engine.get_track_scene_volume(fn, self.selected_scene)
            card.set_volume_display(vol)

        # Si estamos en modo audición, aplicar esta escena de inmediato
        if self.engine.is_auditioning:
            self.engine.start_audition(self.selected_scene)

    def _update_scene_buttons(self) -> None:
        self.btn_scene_study.setChecked(self.selected_scene == "study")
        self.btn_scene_break.setChecked(self.selected_scene == "break_state")
        self.btn_scene_main.setChecked(self.selected_scene == "main_state")

        active_color = "#065f46" if self.is_dark else "#059669"
        border_color = "#059669" if self.is_dark else "#047857"

        for btn, is_selected in (
            (self.btn_scene_study, self.selected_scene == "study"),
            (self.btn_scene_break, self.selected_scene == "break_state"),
            (self.btn_scene_main, self.selected_scene == "main_state"),
        ):
            if is_selected:
                btn.setStyleSheet(f"background: {active_color}; border: 1px solid {border_color}; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 6px;")
            else:
                btn.setStyleSheet("padding: 6px 14px; border-radius: 6px;")

    def _toggle_audition(self) -> None:
        if self.btn_audition.isChecked():
            self.btn_audition.setText(" ⏹️ Detener audición")
            self.btn_audition.setStyleSheet("background: #b91c1c; color: #ffffff; padding: 6px 14px; font-weight: bold; border-radius: 6px;")
            self.engine.start_audition(self.selected_scene)
        else:
            self.btn_audition.setText(" ▶️ Audicionar esta escena")
            self.btn_audition.setStyleSheet("padding: 6px 14px; font-weight: bold; border-radius: 6px;")
            self.engine.stop_audition()

    def sync_audition_button(self) -> None:
        self.btn_audition.blockSignals(True)
        if self.engine.is_auditioning:
            self.btn_audition.setChecked(True)
            self.btn_audition.setText(" ⏹️ Detener audición")
            self.btn_audition.setStyleSheet("background: #b91c1c; color: #ffffff; padding: 6px 14px; font-weight: bold; border-radius: 6px;")
        else:
            self.btn_audition.setChecked(False)
            self.btn_audition.setText(" ▶️ Audicionar esta escena")
            self.btn_audition.setStyleSheet("padding: 6px 14px; font-weight: bold; border-radius: 6px;")
        self.btn_audition.blockSignals(False)

    def _on_track_volume_changed(self, filename: str, volume: float) -> None:
        is_active = (self.selected_scene == self.engine.active_scene_name)
        accepted = self.engine.set_track_scene_volume(filename, self.selected_scene, volume, immediate=is_active)
        if not accepted and volume > 0.001:
            if filename in self.cards:
                prev_vol = self.engine.get_track_scene_volume(filename, self.selected_scene)
                self.cards[filename].set_volume_display(prev_vol)
            QMessageBox.warning(
                self,
                "Límite de pistas alcanzado",
                f"No puedes activar más de {MAX_ACTIVE_TRACKS} pistas simultáneas por escena para garantizar la estabilidad del audio.",
            )

    def _on_track_mute_toggled(self, filename: str, is_muted: bool) -> None:
        self.engine.set_track_muted(filename, is_muted)

    def _on_track_status_changed(self, filename: str, status: str) -> None:
        if filename in self.cards:
            self.cards[filename].set_playback_status(status)

    def _on_engine_scene_changed(self, scene: str) -> None:
        # Si no estamos audicionando manualmente, reflejar la escena activa
        if not self.engine.is_auditioning:
            self._select_scene(scene)

    def _on_master_slider_changed(self, value: int) -> None:
        vol = value / 100.0
        self.master_vol_val.setText(f"{value}%")
        self.engine.set_master_volume(vol)

    def _on_engine_master_volume_changed(self, vol: float) -> None:
        val = int(round(vol * 100))
        self.master_slider.blockSignals(True)
        self.master_slider.setValue(val)
        self.master_slider.blockSignals(False)
        self.master_vol_val.setText(f"{val}%")

    def _toggle_master_mute(self) -> None:
        self.engine.set_master_muted(not self.engine.is_master_muted)

    def _on_engine_master_muted_changed(self, is_muted: bool) -> None:
        if is_muted:
            self.master_mute_btn.setIcon(qta.icon("fa5s.volume-mute", color="#ef4444"))
        else:
            color = "#10b981" if self.is_dark else "#059669"
            self.master_mute_btn.setIcon(qta.icon("fa5s.volume-up", color=color))

    def _on_fade_in_slider_changed(self, value: int) -> None:
        sec = value / 10.0
        self.fade_in_val_lbl.setText(f"{sec:.1f}s")
        self.engine.set_fade_in(sec)

    def _on_fade_out_slider_changed(self, value: int) -> None:
        sec = value / 10.0
        self.fade_out_val_lbl.setText(f"{sec:.1f}s")
        self.engine.set_fade_out(sec)

    def _on_fade_slider_changed(self, value: int) -> None:
        sec = value / 10.0
        self.fade_in_val_lbl.setText(f"{sec:.1f}s")
        self.fade_out_val_lbl.setText(f"{sec:.1f}s")
        self.engine.set_fade_duration(sec)

    def _on_engine_fade_in_changed(self, sec: float) -> None:
        self.fade_in_slider.blockSignals(True)
        self.fade_in_slider.setValue(int(round(sec * 10)))
        self.fade_in_slider.blockSignals(False)
        self.fade_in_val_lbl.setText(f"{sec:.1f}s")

    def _on_engine_fade_out_changed(self, sec: float) -> None:
        self.fade_out_slider.blockSignals(True)
        self.fade_out_slider.setValue(int(round(sec * 10)))
        self.fade_out_slider.blockSignals(False)
        self.fade_out_val_lbl.setText(f"{sec:.1f}s")

    def _sync_preset_dropdown(self) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        selected_idx = 0
        for i, p in enumerate(self.engine.presets):
            self.preset_combo.addItem(p.name, p.id)
            if p.id == self.engine.active_preset_id:
                selected_idx = i
        self.preset_combo.setCurrentIndex(selected_idx)
        self.preset_combo.blockSignals(False)

    def _on_preset_combo_changed(self, index: int) -> None:
        if index >= 0:
            preset_id = self.preset_combo.itemData(index)
            if preset_id:
                self.engine.select_preset(str(preset_id))
                self.master_slider.setValue(int(round(self.engine.master_volume * 100)))
                self.fade_in_slider.setValue(int(round(self.engine.fade_in_sec * 10)))
                self.fade_out_slider.setValue(int(round(self.engine.fade_out_sec * 10)))
                self._select_scene(self.selected_scene)

    def _on_save_preset(self) -> None:
        self.engine.save_current_preset()
        preset_name = self.engine.current_preset.name if self.engine.current_preset else "Preset"
        QMessageBox.information(self, "Preset guardado", f"Se guardó la configuración en '{preset_name}'.")

    def _on_new_preset(self) -> None:
        try:
            name, ok = QInputDialog.getText(self, "Nuevo Preset", "Nombre del preset:")
            if ok and name and name.strip():
                self.engine.create_preset(name.strip())
                self._sync_preset_dropdown()
                self._select_scene(self.selected_scene)
        except Exception:
            pass

    def _on_delete_preset(self) -> None:
        if len(self.engine.presets) <= 1:
            QMessageBox.warning(self, "Acción no permitida", "No puedes eliminar el único preset existente.")
            return

        name = self.engine.current_preset.name if self.engine.current_preset else "este preset"
        if QMessageBox.question(self, "Confirmar eliminación", f"¿Eliminar '{name}'?") == QMessageBox.StandardButton.Yes:
            self.engine.delete_preset(self.engine.active_preset_id)
            self._sync_preset_dropdown()
            self._select_scene(self.selected_scene)
