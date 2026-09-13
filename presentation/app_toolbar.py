"""Barra de herramientas principal de la aplicación Study Timetrial."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QToolBar, QToolButton, QWidget
import qtawesome as qta

from presentation.theme_tokens import THEME_DARK, THEME_LIGHT


class AppToolbar(QToolBar):
    """Barra superior que aloja los accesos a Archivo y Configuración."""

    request_new_record = Signal()
    request_open_record = Signal()
    request_open_recent = Signal(Path)
    request_save_as = Signal()
    request_close_record = Signal()
    request_close_app = Signal()
    request_theme_change = Signal(str)
    request_toggle_sound = Signal()

    def __init__(self, is_dark_mode: bool = False, parent: QWidget | None = None) -> None:
        super().__init__("Barra principal", parent)
        self.setObjectName("main_toolbar")
        self.setMovable(False)

        icon_color = "#cbd5e1" if is_dark_mode else "#334155"

        # --- Menú Archivo ---
        self.file_menu = QMenu("Archivo", self)

        self.new_file_action = QAction("Nuevo archivo", self)
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=icon_color))
        self.new_file_action.triggered.connect(self.request_new_record.emit)
        self.file_menu.addAction(self.new_file_action)

        self.open_file_action = QAction("Abrir archivo", self)
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.open_file_action.triggered.connect(self.request_open_record.emit)
        self.file_menu.addAction(self.open_file_action)

        self.recent_file_action = QAction("Reciente", self)
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=icon_color))
        self.recent_files_menu = QMenu(self)
        self.recent_file_action.setMenu(self.recent_files_menu)
        self.file_menu.addAction(self.recent_file_action)

        self.save_file_action = QAction("Guardar como", self)
        self.save_file_action.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.save_file_action.triggered.connect(self.request_save_as.emit)
        self.file_menu.addAction(self.save_file_action)

        self.file_menu.addSeparator()
        self.close_file_action = QAction("Cerrar archivo", self)
        self.close_file_action.setIcon(qta.icon("fa5s.times-circle", color="#e11d48"))
        self.close_file_action.triggered.connect(self.request_close_record.emit)
        self.file_menu.addAction(self.close_file_action)

        self.close_program_action = QAction("Cerrar programa", self)
        self.close_program_action.setIcon(qta.icon("fa5s.power-off", color="#e11d48"))
        self.close_program_action.triggered.connect(self.request_close_app.emit)
        self.file_menu.addAction(self.close_program_action)

        self.file_button = QToolButton(self)
        self.file_button.setObjectName("file_toolbar_button")
        self.file_button.setText(" Archivo")
        self.file_button.setIcon(qta.icon("fa5s.folder", color=icon_color))
        self.file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.file_button.setMenu(self.file_menu)
        self.file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.file_button.setStyleSheet("QToolButton#file_toolbar_button::menu-indicator { image: none; }")
        self.addWidget(self.file_button)

        # --- Menú Configuración (Temas y Sonidos) ---
        self.config_menu = QMenu("Configuración", self)
        self.view_menu = self.config_menu  # alias para retrocompatibilidad

        self.themes_menu = QMenu("Temas", self.config_menu)
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=icon_color))

        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        self.theme_dark_action = QAction("Modo oscuro", self)
        self.theme_dark_action.setIcon(qta.icon("fa5s.moon", color="#60a5fa"))
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.setChecked(is_dark_mode)
        self.theme_dark_action.triggered.connect(lambda: self.request_theme_change.emit(THEME_DARK))
        self.theme_group.addAction(self.theme_dark_action)
        self.themes_menu.addAction(self.theme_dark_action)

        self.theme_light_action = QAction("Modo claro", self)
        self.theme_light_action.setIcon(qta.icon("fa5s.sun", color="#eab308"))
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.setChecked(not is_dark_mode)
        self.theme_light_action.triggered.connect(lambda: self.request_theme_change.emit(THEME_LIGHT))
        self.theme_group.addAction(self.theme_light_action)
        self.themes_menu.addAction(self.theme_light_action)

        self.config_menu.addMenu(self.themes_menu)
        self.config_menu.addSeparator()

        # Acción silenciar/activar sonidos
        self.sound_action = QAction(self)
        self.mute_action = self.sound_action  # alias
        self.sound_action.triggered.connect(self.request_toggle_sound.emit)
        self.config_menu.addAction(self.sound_action)

        self.config_button = QToolButton(self)
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
        self.addWidget(self.config_button)

    def update_sound_action(self, is_muted: bool) -> None:
        """Actualiza el texto e icono de la acción de sonido."""
        if is_muted:
            self.sound_action.setText("Activar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-mute", color="#ef4444"))
        else:
            self.sound_action.setText("Silenciar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-up", color="#10b981"))

    def update_theme_icons(self, is_dark: bool) -> None:
        """Actualiza los iconos de la barra de herramientas al alternar tema."""
        toolbar_icon_color = "#cbd5e1" if is_dark else "#334155"

        self.file_button.setIcon(qta.icon("fa5s.folder", color=toolbar_icon_color))
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=toolbar_icon_color))
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=toolbar_icon_color))
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=toolbar_icon_color))
        self.save_file_action.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))

        self.config_button.setIcon(qta.icon("fa5s.cog", color=toolbar_icon_color))
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=toolbar_icon_color))

        self.theme_dark_action.setChecked(is_dark)
        self.theme_light_action.setChecked(not is_dark)

    def populate_recent_files(
        self,
        recent_paths: list[Path],
        on_open_file: Callable[[], None],
        on_select_recent: Callable[[Path], None],
    ) -> None:
        """Regenera los elementos del submenú de archivos recientes."""
        self.recent_files_menu.clear()

        open_action = QAction("Abrir archivo…", self)
        open_action.setIcon(qta.icon("fa5s.folder-open", color="#334155"))
        open_action.triggered.connect(on_open_file)
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
            action.triggered.connect(lambda _checked, selected=path: on_select_recent(selected))
            self.recent_files_menu.addAction(action)
