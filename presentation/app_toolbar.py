"""Barra de herramientas principal de la aplicación Study Timetrial."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from presentation.theme import get_available_themes, get_theme_tokens
from presentation.theme_tokens import THEME_DARK, THEME_LIGHT



class AppToolbar(QToolBar):
    """Barra superior que aloja los accesos a Archivo y Configuración."""

    request_new_record = Signal()
    request_open_record = Signal()
    request_open_recent = Signal(Path)
    request_save = Signal()
    request_save_as = Signal()
    request_export = Signal()
    request_close_record = Signal()
    request_close_app = Signal()
    request_theme_change = Signal(str)
    request_toggle_sound = Signal()
    request_toggle_auto_open = Signal(bool)
    request_undo = Signal()
    request_redo = Signal()

    def __init__(
        self,
        is_dark_mode: bool = False,
        auto_open_recent: bool = True,
        parent: QWidget | None = None,
        current_theme: str = THEME_LIGHT,
        is_sound_muted: bool = False,
    ) -> None:
        super().__init__("Barra principal", parent)
        self.setObjectName("main_toolbar")
        self.setMovable(False)
        self._current_theme = current_theme if current_theme else (THEME_DARK if is_dark_mode else THEME_LIGHT)

        tokens = get_theme_tokens(self._current_theme)
        icon_color = tokens.toolbar_btn_fg if hasattr(tokens, "toolbar_btn_fg") else ("#cbd5e1" if is_dark_mode else "#334155")

        # --- Menú Archivo ---
        self.file_menu = QMenu("Archivo", self)

        self.new_file_action = QAction("Nuevo archivo", self)
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=icon_color))
        self.new_file_action.setShortcut("Ctrl+N")
        self.new_file_action.setToolTip("Nuevo archivo (Ctrl+N)")
        self.new_file_action.triggered.connect(self.request_new_record.emit)
        self.file_menu.addAction(self.new_file_action)

        self.open_file_action = QAction("Abrir archivo", self)
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.open_file_action.setShortcut("Ctrl+O")
        self.open_file_action.setToolTip("Abrir archivo (Ctrl+O)")
        self.open_file_action.triggered.connect(self.request_open_record.emit)
        self.file_menu.addAction(self.open_file_action)

        self.recent_file_action = QAction("Reciente", self)
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=icon_color))
        self.recent_files_menu = QMenu(self)
        self.recent_file_action.setMenu(self.recent_files_menu)
        self.file_menu.addAction(self.recent_file_action)

        self.file_menu.addSeparator()

        self.save_action = QAction("Guardar", self)
        self.save_action.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.setToolTip("Guardar (Ctrl+S)")
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(self.request_save.emit)
        self.file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Guardar como...", self)
        self.save_as_action.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.save_as_action.setShortcut("Ctrl+Shift+S")
        self.save_as_action.setToolTip("Guardar como... (Ctrl+Shift+S)")
        self.save_as_action.triggered.connect(self.request_save_as.emit)
        self.file_menu.addAction(self.save_as_action)
        self.save_file_action = self.save_as_action

        self.export_file_action = QAction("Exportar datos (CSV)...", self)
        self.export_file_action.setIcon(qta.icon("fa5s.file-export", color=icon_color))
        self.export_file_action.triggered.connect(self.request_export.emit)
        self.file_menu.addAction(self.export_file_action)

        self.file_menu.addSeparator()
        self.close_file_action = QAction("Cerrar archivo", self)
        self.close_file_action.setIcon(qta.icon("fa5s.times-circle", color="#e11d48"))
        self.close_file_action.setShortcut("Ctrl+W")
        self.close_file_action.setToolTip("Cerrar archivo (Ctrl+W)")
        self.close_file_action.triggered.connect(self.request_close_record.emit)
        self.file_menu.addAction(self.close_file_action)

        self.close_program_action = QAction("Cerrar programa", self)
        self.close_program_action.setIcon(qta.icon("fa5s.power-off", color="#e11d48"))
        self.close_program_action.setShortcut("Ctrl+Q")
        self.close_program_action.setToolTip("Cerrar programa (Ctrl+Q)")
        self.close_program_action.triggered.connect(self.request_close_app.emit)
        self.file_menu.addAction(self.close_program_action)

        # --- Menú Edición (Deshacer / Rehacer) ---
        self.edit_menu = QMenu("Edición", self)

        self.undo_action = QAction("Deshacer", self)
        self.undo_action.setIcon(qta.icon("fa5s.undo", color=icon_color))
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.request_undo.emit)
        self.edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Rehacer", self)
        self.redo_action.setIcon(qta.icon("fa5s.redo", color=icon_color))
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.request_redo.emit)
        self.edit_menu.addAction(self.redo_action)

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
            ("high_night", "High Night [Dinámico]", "fa5s.star-and-crescent", "#9d4edd"),
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

        # Dimensiones de iconos compactos para estilo de editor
        compact_icon_size = QSize(13, 13)

        # =========================================================================
        # Ensamble de la estructura de 2 niveles
        # =========================================================================
        self.toolbar_container = QWidget(self)
        self.toolbar_container.setObjectName("toolbar_container")
        self.toolbar_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        vbox = QVBoxLayout(self.toolbar_container)
        vbox.setContentsMargins(0, 1, 0, 2)
        vbox.setSpacing(2)

        # Nivel 1: Fila de Menús a la izquierda
        self.menu_row = QWidget(self.toolbar_container)
        self.menu_row.setObjectName("toolbar_menu_row")
        row1 = QHBoxLayout(self.menu_row)
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(2)

        # =========================================================================
        # NIVEL 1: Menús Principales (Izquierda)
        # =========================================================================
        self.file_button = QToolButton(self.menu_row)
        self.file_button.setObjectName("file_toolbar_button")
        self.file_button.setText("Archivo")
        self.file_button.setIcon(qta.icon("fa5s.folder", color=icon_color))
        self.file_button.setIconSize(compact_icon_size)
        self.file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.file_button.setMenu(self.file_menu)
        self.file_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row1.addWidget(self.file_button)

        self.edit_button = QToolButton(self.menu_row)
        self.edit_button.setObjectName("edit_toolbar_button")
        self.edit_button.setText("Edición")
        self.edit_button.setIcon(qta.icon("fa5s.edit", color=icon_color))
        self.edit_button.setIconSize(compact_icon_size)
        self.edit_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.edit_button.setMenu(self.edit_menu)
        self.edit_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row1.addWidget(self.edit_button)

        self.config_button = QToolButton(self.menu_row)
        self.view_button = self.config_button  # alias para retrocompatibilidad
        self.config_button.setObjectName("config_toolbar_button")
        self.config_button.setText("Configuración")
        self.config_button.setIcon(qta.icon("fa5s.cog", color=icon_color))
        self.config_button.setIconSize(compact_icon_size)
        self.config_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.config_button.setMenu(self.config_menu)
        self.config_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row1.addWidget(self.config_button)

        row1.addStretch()
        vbox.addWidget(self.menu_row)

        # Nivel 2: Fila de Acciones Rápidas
        self.actions_row = QWidget(self.toolbar_container)
        self.actions_row.setObjectName("toolbar_actions_row")
        row2 = QHBoxLayout(self.actions_row)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(3)

        # =========================================================================
        # NIVEL 2: Acciones Rápidas (Distribución estándar de software de edición)
        # Orden: [Nuevo] [Abrir] [Guardar] [Guardar como]  |  [Deshacer] [Rehacer]
        # =========================================================================
        self.quick_new_button = QToolButton(self.actions_row)
        self.quick_new_button.setObjectName("quick_new_button")
        self.quick_new_button.setText("Nuevo")
        self.quick_new_button.setIcon(qta.icon("fa5s.file-medical", color=icon_color))
        self.quick_new_button.setIconSize(compact_icon_size)
        self.quick_new_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_new_button.setToolTip("Nuevo archivo (Ctrl+N)")
        self.quick_new_button.clicked.connect(self.request_new_record.emit)
        row2.addWidget(self.quick_new_button)

        self.quick_open_button = QToolButton(self.actions_row)
        self.quick_open_button.setObjectName("quick_open_button")
        self.quick_open_button.setText("Abrir")
        self.quick_open_button.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.quick_open_button.setIconSize(compact_icon_size)
        self.quick_open_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_open_button.setToolTip("Abrir archivo (Ctrl+O)")
        self.quick_open_button.clicked.connect(self.request_open_record.emit)
        row2.addWidget(self.quick_open_button)

        self.quick_save_button = QToolButton(self.actions_row)
        self.quick_save_button.setObjectName("quick_save_button")
        self.quick_save_button.setText("Guardar")
        self.quick_save_button.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.quick_save_button.setIconSize(compact_icon_size)
        self.quick_save_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_save_button.setToolTip("Guardar (Ctrl+S)")
        self.quick_save_button.setEnabled(False)
        self.quick_save_button.clicked.connect(self.request_save.emit)
        row2.addWidget(self.quick_save_button)

        self.quick_save_as_button = QToolButton(self.actions_row)
        self.quick_save_as_button.setObjectName("quick_save_as_button")
        self.quick_save_as_button.setText("Guardar como")
        self.quick_save_as_button.setIcon(qta.icon("fa5s.save", color=icon_color))
        self.quick_save_as_button.setIconSize(compact_icon_size)
        self.quick_save_as_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_save_as_button.setToolTip("Guardar como... (Ctrl+Shift+S)")
        self.quick_save_as_button.setEnabled(False)
        self.quick_save_as_button.clicked.connect(self.request_save_as.emit)
        row2.addWidget(self.quick_save_as_button)

        # Separador vertical
        sep = QFrame(self.actions_row)
        sep.setObjectName("toolbar_row_separator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        row2.addWidget(sep)

        # Historial de cambios
        self.quick_undo_button = QToolButton(self.actions_row)
        self.quick_undo_button.setObjectName("quick_undo_button")
        self.quick_undo_button.setText("Deshacer")
        self.quick_undo_button.setIcon(qta.icon("fa5s.undo", color=icon_color))
        self.quick_undo_button.setIconSize(compact_icon_size)
        self.quick_undo_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_undo_button.setToolTip("Deshacer (Ctrl+Z)")
        self.quick_undo_button.setEnabled(False)
        self.quick_undo_button.clicked.connect(self.request_undo.emit)
        row2.addWidget(self.quick_undo_button)

        self.quick_redo_button = QToolButton(self.actions_row)
        self.quick_redo_button.setObjectName("quick_redo_button")
        self.quick_redo_button.setText("Rehacer")
        self.quick_redo_button.setIcon(qta.icon("fa5s.redo", color=icon_color))
        self.quick_redo_button.setIconSize(compact_icon_size)
        self.quick_redo_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.quick_redo_button.setToolTip("Rehacer (Ctrl+Y)")
        self.quick_redo_button.setEnabled(False)
        self.quick_redo_button.clicked.connect(self.request_redo.emit)
        row2.addWidget(self.quick_redo_button)

        row2.addStretch()
        vbox.addWidget(self.actions_row)

        # Referencias de retrocompatibilidad (sin parent para no renderizarse ni superponerse en la barra)
        self.quick_sound_button = QToolButton()
        self.quick_sound_button.setObjectName("quick_sound_button")
        self.quick_sound_button.setVisible(False)
        self.quick_sound_button.hide()
        self.quick_sound_button.clicked.connect(self.request_toggle_sound.emit)

        self.quick_theme_button = QToolButton()
        self.quick_theme_button.setObjectName("quick_theme_button")
        self.quick_theme_button.setVisible(False)
        self.quick_theme_button.hide()
        self.quick_theme_button.clicked.connect(self._on_quick_theme_clicked)

        self.spacer = QWidget()
        self.spacer.setObjectName("toolbar_spacer")
        self.spacer.setVisible(False)
        self.spacer.hide()

        # Agregar el contenedor único a la barra de herramientas
        self.addWidget(self.toolbar_container)

        # Registrar acciones en toolbar_container (QWidget) para atajos de teclado sin crear botones visuales en QToolBar
        for act in (
            self.new_file_action,
            self.open_file_action,
            self.save_action,
            self.save_as_action,
            self.close_file_action,
            self.close_program_action,
            self.undo_action,
            self.redo_action,
        ):
            act.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.toolbar_container.addAction(act)

        self.update_sound_action(is_sound_muted)
        self._update_quick_theme_button(tokens.is_dark)

    def _on_quick_theme_clicked(self) -> None:
        """Alterna rápidamente entre tema claro y tema oscuro."""
        tokens = get_theme_tokens(self._current_theme)
        target_theme = THEME_LIGHT if tokens.is_dark else THEME_DARK
        self.request_theme_change.emit(target_theme)

    def _update_quick_theme_button(self, is_dark: bool) -> None:
        """Actualiza el aspecto del botón rápido de tema (sol / luna)."""
        if not hasattr(self, "quick_theme_button"):
            return
        if is_dark:
            self.quick_theme_button.setIcon(qta.icon("fa5s.sun", color="#f59e0b"))
            self.quick_theme_button.setToolTip("Cambiar a modo claro")
        else:
            self.quick_theme_button.setIcon(qta.icon("fa5s.moon", color="#3b82f6"))
            self.quick_theme_button.setToolTip("Cambiar a modo oscuro")

    def update_sound_action(self, is_muted: bool) -> None:
        """Actualiza el texto e icono de la acción y botón rápido de sonido."""
        self._is_sound_muted = is_muted
        if is_muted:
            self.sound_action.setText("Activar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-mute", color="#ef4444"))
            if hasattr(self, "quick_sound_button"):
                self.quick_sound_button.setIcon(qta.icon("fa5s.volume-mute", color="#ef4444"))
                self.quick_sound_button.setToolTip("Sonidos silenciados — Clic para activar")
        else:
            self.sound_action.setText("Silenciar sonidos")
            self.sound_action.setIcon(qta.icon("fa5s.volume-up", color="#10b981"))
            if hasattr(self, "quick_sound_button"):
                self.quick_sound_button.setIcon(qta.icon("fa5s.volume-up", color="#10b981"))
                self.quick_sound_button.setToolTip("Sonidos activos — Clic para silenciar")

    def set_record_actions_enabled(self, enabled: bool) -> None:
        """Habilita o deshabilita acciones que requieren un archivo abierto."""
        self.save_as_action.setEnabled(enabled)
        self.save_file_action.setEnabled(enabled)
        self.save_action.setEnabled(enabled)
        if hasattr(self, "quick_save_button"):
            self.quick_save_button.setEnabled(enabled)
        if hasattr(self, "quick_save_as_button"):
            self.quick_save_as_button.setEnabled(enabled)
        self.export_file_action.setEnabled(enabled)
        self.close_file_action.setEnabled(enabled)
        if hasattr(self, "edit_button"):
            self.edit_button.setEnabled(enabled)
        if not enabled:
            if hasattr(self, "quick_undo_button"):
                self.quick_undo_button.setEnabled(False)
            if hasattr(self, "quick_redo_button"):
                self.quick_redo_button.setEnabled(False)

    def update_save_action(self, is_record_open: bool, is_dirty: bool) -> None:
        """Actualiza la disponibilidad reactiva de las acciones de guardado."""
        can_save = is_record_open and is_dirty
        self.save_action.setEnabled(can_save)
        self.save_as_action.setEnabled(is_record_open)
        if hasattr(self, "quick_save_button"):
            self.quick_save_button.setEnabled(can_save)
            if not is_record_open:
                self.quick_save_button.setToolTip("Guardar (No hay archivo abierto)")
            elif is_dirty:
                self.quick_save_button.setToolTip("Guardar cambios pendientes (Ctrl+S)")
            else:
                self.quick_save_button.setToolTip("Sin cambios pendientes (Ctrl+S)")
        if hasattr(self, "quick_save_as_button"):
            self.quick_save_as_button.setEnabled(is_record_open)

    def update_auto_open_action(self, enabled: bool) -> None:
        """Actualiza el estado de la acción de auto-apertura."""
        self.auto_open_action.setChecked(enabled)

    def set_current_theme(self, theme: str) -> None:
        """Actualiza el estado marcado del tema activo."""
        self._current_theme = theme
        for key, action in self.theme_actions.items():
            action.setChecked(key == theme)
        tokens = get_theme_tokens(theme)
        self._update_quick_theme_button(tokens.is_dark)

    def update_theme_icons(self, is_dark: bool) -> None:
        """Actualiza los iconos de la barra de herramientas al alternar tema."""
        tokens = get_theme_tokens(self._current_theme)
        toolbar_icon_color = tokens.toolbar_btn_fg if hasattr(tokens, "toolbar_btn_fg") else ("#cbd5e1" if is_dark else "#334155")

        self.file_button.setIcon(qta.icon("fa5s.folder", color=toolbar_icon_color))
        self.new_file_action.setIcon(qta.icon("fa5s.file-medical", color=toolbar_icon_color))
        self.open_file_action.setIcon(qta.icon("fa5s.folder-open", color=toolbar_icon_color))
        self.recent_file_action.setIcon(qta.icon("fa5s.history", color=toolbar_icon_color))
        self.save_action.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))
        self.save_as_action.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))
        self.export_file_action.setIcon(qta.icon("fa5s.file-export", color=toolbar_icon_color))

        if hasattr(self, "quick_new_button"):
            self.quick_new_button.setIcon(qta.icon("fa5s.file-medical", color=toolbar_icon_color))
        if hasattr(self, "quick_open_button"):
            self.quick_open_button.setIcon(qta.icon("fa5s.folder-open", color=toolbar_icon_color))
        if hasattr(self, "quick_save_button"):
            self.quick_save_button.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))
        if hasattr(self, "quick_save_as_button"):
            self.quick_save_as_button.setIcon(qta.icon("fa5s.save", color=toolbar_icon_color))

        if hasattr(self, "edit_button"):
            self.edit_button.setIcon(qta.icon("fa5s.edit", color=toolbar_icon_color))
            self.undo_action.setIcon(qta.icon("fa5s.undo", color=toolbar_icon_color))
            self.redo_action.setIcon(qta.icon("fa5s.redo", color=toolbar_icon_color))

        if hasattr(self, "quick_undo_button"):
            self.quick_undo_button.setIcon(qta.icon("fa5s.undo", color=toolbar_icon_color))
        if hasattr(self, "quick_redo_button"):
            self.quick_redo_button.setIcon(qta.icon("fa5s.redo", color=toolbar_icon_color))

        self.config_button.setIcon(qta.icon("fa5s.cog", color=toolbar_icon_color))
        self.themes_menu.setIcon(qta.icon("fa5s.palette", color=toolbar_icon_color))

        self._update_quick_theme_button(is_dark)

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

    def update_undo_redo_actions(
        self, can_undo: bool, can_redo: bool, undo_text: str = "", redo_text: str = ""
    ) -> None:
        """Actualiza el estado habilitado y los tooltips de Deshacer y Rehacer."""
        self.undo_action.setEnabled(can_undo)
        self.redo_action.setEnabled(can_redo)
        self.quick_undo_button.setEnabled(can_undo)
        self.quick_redo_button.setEnabled(can_redo)

        undo_label = f"Deshacer {undo_text}" if undo_text else "Deshacer"
        redo_label = f"Rehacer {redo_text}" if redo_text else "Rehacer"
        self.undo_action.setText(undo_label)
        self.redo_action.setText(redo_label)
        self.quick_undo_button.setToolTip(f"{undo_label} (Ctrl+Z)")
        self.quick_redo_button.setToolTip(f"{redo_label} (Ctrl+Y)")
