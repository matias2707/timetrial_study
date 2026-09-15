"""Diálogo de bienvenida y selección inicial de archivos para Study Timetrial."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from presentation.home_view import APP_VERSION
from presentation.theme import get_dialog_stylesheet
from presentation.theme_tokens import THEME_LIGHT
from presentation.window_utils import ensure_dialog_taskbar_presence, force_activate_window, get_app_icon


class WelcomeDialog(QDialog):
    """Ventana inicial para elegir entre abrir un registro reciente, crear uno nuevo o explorar."""

    def __init__(
        self,
        recent_paths: Sequence[Path] | None = None,
        auto_open_recent: bool = True,
        current_theme: str = THEME_LIGHT,
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Study Timetrial — Inicio")
        self.setMinimumWidth(580)
        self.setMinimumHeight(420)
        self.resize(600, 440)

        self.current_theme = current_theme
        self.is_dark_mode = is_dark_mode
        self.recent_paths = [p for p in (recent_paths or []) if p.exists()]
        self.auto_open_recent_initial = auto_open_recent

        self.selected_action: str = "cancel"
        self.selected_path: Path | None = None

        # Si no hay ventana padre visible, asegurar presencia directa en la barra de tareas
        if parent is None or not parent.isVisible():
            ensure_dialog_taskbar_presence(self)
        else:
            self.setWindowIcon(get_app_icon())

        self.setStyleSheet(get_dialog_stylesheet(self.current_theme))

        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(26, 24, 26, 22)

        # Encabezado (Icono + Título + Versión)
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel(self)
        app_icon = get_app_icon()
        if not app_icon.isNull():
            icon_label.setPixmap(app_icon.pixmap(36, 36))
            header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Study Timetrial", self)
        title.setObjectName("title")
        subtitle = QLabel("Continúa donde lo dejaste o inicia un nuevo registro de estudio.", self)
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)

        header.addStretch()

        version = QLabel(APP_VERSION, self)
        version.setObjectName("version")
        version.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        header.addWidget(version)

        layout.addLayout(header)

        # Sección de archivos recientes
        recent_header = QLabel("Archivos recientes", self)
        recent_header.setObjectName("recent_header")
        layout.addWidget(recent_header)

        self.recent_list = QListWidget(self)
        self.recent_list.setObjectName("recent_files_list")

        if self.recent_paths:
            for path in self.recent_paths[:6]:
                item = QListWidgetItem(self.recent_list)
                item.setText(f"{path.name}\n  📂 {path.parent}")
                item.setToolTip(str(path))
                item.setData(Qt.ItemDataRole.UserRole, str(path))
                self.recent_list.addItem(item)
            self.recent_list.setCurrentRow(0)
        else:
            empty_item = QListWidgetItem("No hay archivos recientes registrados aún.", self.recent_list)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent_list.addItem(empty_item)

        self.recent_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.recent_list)

        # Checkbox de apertura automática
        self.auto_open_checkbox = QCheckBox("Abrir automáticamente el último registro al iniciar", self)
        self.auto_open_checkbox.setChecked(self.auto_open_recent_initial)
        self.auto_open_checkbox.setToolTip("Si está activado, la aplicación cargará el último archivo usado sin mostrar esta pantalla.")
        layout.addWidget(self.auto_open_checkbox)

        # Barra de botones de acción inferior
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.open_recent_button = QPushButton("  Abrir reciente", self)
        self.open_recent_button.setIcon(qta.icon("fa5s.play", color="#090d16" if self.is_dark_mode else "#bef264"))
        self.open_recent_button.setObjectName("primary")
        self.open_recent_button.setEnabled(bool(self.recent_paths))
        self.open_recent_button.clicked.connect(self._on_open_recent_clicked)

        self.new_button = QPushButton("  Nuevo archivo", self)
        self.new_button.setIcon(qta.icon("fa5s.plus", color="#cbd5e1" if self.is_dark_mode else "#334155"))
        self.new_button.setObjectName("secondary")
        self.new_button.clicked.connect(self._on_new_clicked)

        self.open_button = QPushButton("  Explorar...", self)
        self.open_button.setIcon(qta.icon("fa5s.folder-open", color="#cbd5e1" if self.is_dark_mode else "#334155"))
        self.open_button.setObjectName("secondary")
        self.open_button.clicked.connect(self._on_open_clicked)

        self.cancel_button = QPushButton("Cancelar", self)
        self.cancel_button.setObjectName("ghost")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        buttons_layout.addWidget(self.open_recent_button)
        buttons_layout.addWidget(self.new_button)
        buttons_layout.addWidget(self.open_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._on_new_clicked)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._on_open_clicked)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        force_activate_window(self)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if path_str:
            self.selected_action = "recent"
            self.selected_path = Path(path_str)
            self.accept()

    def _on_open_recent_clicked(self) -> None:
        current_item = self.recent_list.currentItem()
        if current_item is not None:
            path_str = current_item.data(Qt.ItemDataRole.UserRole)
            if path_str:
                self.selected_action = "recent"
                self.selected_path = Path(path_str)
                self.accept()
                return

        if self.recent_paths:
            self.selected_action = "recent"
            self.selected_path = self.recent_paths[0]
            self.accept()

    def _on_new_clicked(self) -> None:
        self.selected_action = "new"
        self.selected_path = None
        self.accept()

    def _on_open_clicked(self) -> None:
        self.selected_action = "open"
        self.selected_path = None
        self.accept()

    def _on_cancel_clicked(self) -> None:
        self.selected_action = "cancel"
        self.selected_path = None
        self.reject()

    def exec_welcome(self) -> tuple[str, Path | None, bool]:
        """Ejecuta el diálogo de bienvenida de manera modal y devuelve el resultado."""
        force_activate_window(self)
        result = self.exec()
        auto_open = self.auto_open_checkbox.isChecked()
        if result == QDialog.DialogCode.Accepted:
            return self.selected_action, self.selected_path, auto_open
        return "cancel", None, auto_open
