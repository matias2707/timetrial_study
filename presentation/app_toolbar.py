"""Barra de herramientas principal de la aplicación Study Timetrial."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QToolBar, QToolButton, QWidget
import qtawesome as qta

from presentation.theme import get_available_themes, get_theme_tokens
from presentation.theme_tokens import THEME_DARK, THEME_LIGHT



class AppToolbar(QToolBar):
    """Barra superior que aloja los accesos a Archivo y Configuración."""

    request_new_record = Signal()
    request_open_record = Signal()
    request_open_recent = Signal(Path)
    request_save_as = Signal()
    request_export = Signal()
    request_close_record = Signal()
    request_close_app = Signal()
    request_theme_change = Signal(str)
    request_toggle_sound = Signal()
    request_toggle_auto_open = Signal(bool)

    def __init__(
        self,
        is_dark_mode: bool = False,
        auto_open_recent: bool = True,
        parent: QWidget | None = None,
        current_theme: str = THEME_LIGHT,
    ) -> None:
        super().__init__("Barra principal", parent)
        self.setObjectName("main_toolbar")
        self.setMovable(False)
        self._current_theme = current_theme if current_theme else (THEME_DARK if is_dark_mode else THEME_LIGHT)

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

        self.export_file_action = QAction("Exportar datos (CSV)...", self)
        self.export_file_action.setIcon(qta.icon("fa5s.file-export", color=icon_color))
        self.export_file_action.triggered.connect(self.request_export.emit)
        self.file_menu.addAction(self.export_file_action)

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

        # --- Menú Configuración (Temas, Sonidos y Opciones de Inicio) ---
        self.config_menu = QMenu("Configuración", self)
        self.view_menu = self.config_menu  # alias para retrocompatibilidad

        self.themes_menu = QMenu("Temas", self.config_menu)
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=icon_color))

        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}

        # Modos estándar
        self.theme_light_action = QAction("Modo claro", self)
        self.theme_light_action.setIcon(qta.icon("fa5s.sun", color="#eab308"))
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.setChecked(self._current_theme == THEME_LIGHT)
        self.theme_light_action.triggered.connect(lambda: self.request_theme_change.emit(THEME_LIGHT))
        self.theme_group.addAction(self.theme_light_action)
        self.themes_menu.addAction(self.theme_light_action)
        self.theme_actions[THEME_LIGHT] = self.theme_light_action

        self.theme_dark_action = QAction("Modo oscuro", self)
        self.theme_dark_action.setIcon(qta.icon("fa5s.moon", color="#60a5fa"))
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.setChecked(self._current_theme == THEME_DARK)
        self.theme_dark_action.triggered.connect(lambda: self.request_theme_change.emit(THEME_DARK))
        self.theme_group.addAction(self.theme_dark_action)
        self.themes_menu.addAction(self.theme_dark_action)
        self.theme_actions[THEME_DARK] = self.theme_dark_action

        # Sección: Skins temáticos & dinámicos
        self.themes_menu.addSeparator()
        seasonal_section = QAction("Skins temáticos & dinámicos", self)
        seasonal_section.setEnabled(False)
        self.themes_menu.addAction(seasonal_section)

        thematic_skins = [
            ("sakura", "Sakura [Dinámico]", "fa5s.spa", "#ec4899"),
            ("black_sakura", "Black Sakura [Dinámico]", "fa5s.moon", "#f43f5e"),
            ("winter", "Winter [Dinámico]", "fa5s.snowflake", "#38bdf8"),
            ("spring", "Spring [Dinámico]", "fa5s.leaf", "#22c55e"),
            ("bamboo", "Bamboo [Dinámico]", "fa5s.tree", "#65a30d"),
            ("midnight", "Midnight [Dinámico]", "fa5s.star", "#8b5cf6"),
            ("vampyr", "Vampyr [Dinámico]", "fa5s.tint", "#dc2626"),
            ("halloween", "Halloween [Dinámico]", "fa5s.ghost", "#f97316"),
        ]
        for key, label, icon_name, color in thematic_skins:
            act = QAction(label, self)
            act.setIcon(qta.icon(icon_name, color=color))
            act.setCheckable(True)
            act.setChecked(self._current_theme == key)
            act.triggered.connect(lambda checked=False, k=key: self.request_theme_change.emit(k))
            self.theme_group.addAction(act)
            self.themes_menu.addAction(act)
            self.theme_actions[key] = act

        # Sección: Paletas Pantone & Diseñador
        self.themes_menu.addSeparator()
        pantone_section = QAction("Paletas Pantone & Diseñador", self)
        pantone_section.setEnabled(False)
        self.themes_menu.addAction(pantone_section)

        pantone_skins = [
            ("classic_blue", "Pantone: Classic Blue", "fa5s.tint", "#0f4c81"),
            ("peach_fuzz", "Pantone: Peach Fuzz", "fa5s.heart", "#ea580c"),
            ("marsala", "Pantone: Marsala", "fa5s.wine-glass-alt", "#955251"),
            ("emerald", "Pantone: Emerald", "fa5s.gem", "#009473"),
            ("illuminating", "Pantone: Illuminating", "fa5s.bolt", "#f5df4d"),
            ("nord", "Nord Polar", "fa5s.compass", "#88c0d0"),
        ]
        for key, label, icon_name, color in pantone_skins:
            act = QAction(label, self)
            act.setIcon(qta.icon(icon_name, color=color))
            act.setCheckable(True)
            act.setChecked(self._current_theme == key)
            act.triggered.connect(lambda checked=False, k=key: self.request_theme_change.emit(k))
            self.theme_group.addAction(act)
            self.themes_menu.addAction(act)
            self.theme_actions[key] = act

        # Sección: Skins personalizados del usuario (descubrimiento automático en data/themes/)
        known_keys = {THEME_LIGHT, THEME_DARK} | {k for k, _, _, _ in thematic_skins} | {k for k, _, _, _ in pantone_skins}
        available_all = get_available_themes()
        custom_keys = [k for k in available_all if k not in known_keys]
        if custom_keys:
            self.themes_menu.addSeparator()
            custom_section = QAction("Temas personalizados", self)
            custom_section.setEnabled(False)
            self.themes_menu.addAction(custom_section)

            for key in custom_keys:
                tok = get_theme_tokens(key)
                is_dyn = tok.effect not in ("none", "")
                display_title = key.replace("_", " ").title()
                if is_dyn:
                    display_title += " [Dinámico]"
                icon_name = "fa5s.magic" if is_dyn else "fa5s.paint-brush"
                color = tok.hero_start_bg if tok.hero_start_bg.startswith("#") else "#64748b"

                act = QAction(display_title, self)
                act.setIcon(qta.icon(icon_name, color=color))
                act.setCheckable(True)
                act.setChecked(self._current_theme == key)
                act.triggered.connect(lambda checked=False, k=key: self.request_theme_change.emit(k))
                self.theme_group.addAction(act)
                self.themes_menu.addAction(act)
                self.theme_actions[key] = act

        self.config_menu.addMenu(self.themes_menu)
        self.config_menu.addSeparator()

        # Acción silenciar/activar sonidos
        self.sound_action = QAction(self)
        self.mute_action = self.sound_action  # alias
        self.sound_action.triggered.connect(self.request_toggle_sound.emit)
        self.config_menu.addAction(self.sound_action)

        self.config_menu.addSeparator()

        # Acción auto-apertura del último archivo al iniciar
        self.auto_open_action = QAction("Cargar último archivo al iniciar", self)
        self.auto_open_action.setCheckable(True)
        self.auto_open_action.setChecked(auto_open_recent)
        self.auto_open_action.triggered.connect(self.request_toggle_auto_open.emit)
        self.config_menu.addAction(self.auto_open_action)

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

    def set_record_actions_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita acciones que requieren un archivo abierto."""
        self.save_file_action.setEnabled(enabled)
        self.export_file_action.setEnabled(enabled)
        self.close_file_action.setEnabled(enabled)

    def update_auto_open_action(self, enabled: bool) -> None:
        """Actualiza el estado de la acción de auto-apertura."""
        self.auto_open_action.setChecked(enabled)

    def set_current_theme(self, theme: str) -> None:
        """Actualiza el estado marcado del tema activo."""
        self._current_theme = theme
        for key, action in self.theme_actions.items():
            action.setChecked(key == theme)

    def update_theme_icons(self, is_dark: bool) -> None:
        """Actualiza los iconos de la barra de herramientas al alternar tema."""
        toolbar_icon_color = "#cbd5e1" if is_dark else "#334155"

        self.file_button.setIcon(qta.icon("fa5s.folder", color=toolbar_icon_color))
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=toolbar_icon_color))
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=toolbar_icon_color))
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=toolbar_icon_color))
        self.save_file_action.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))
        self.export_file_action.setIcon(qta.icon("fa5s.file-export", color=toolbar_icon_color))

        self.config_button.setIcon(qta.icon("fa5s.cog", color=toolbar_icon_color))
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=toolbar_icon_color))

        current = getattr(self, "_current_theme", None)
        if current and current in self.theme_actions:
            for key, action in self.theme_actions.items():
                action.setChecked(key == current)
        else:
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
