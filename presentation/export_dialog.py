from __future__ import annotations

"""Diálogo modal para la exportación de registros y reportes analíticos (CSV / Excel)."""

from datetime import datetime
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QDate, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import StudyApplicationService
from domain.models import TimerItem
from presentation.theme import get_dialog_stylesheet, get_theme_tokens
from presentation.theme_tokens import THEME_LIGHT
from presentation.window_utils import ensure_dialog_taskbar_presence, force_activate_window, get_app_icon


class ExportDialog(QDialog):
    """Diálogo modal interactivo para exportar datos a CSV compatible con Excel."""

    def __init__(
        self,
        application: StudyApplicationService,
        filtered_items: Sequence[TimerItem] | None = None,
        current_theme: str = THEME_LIGHT,
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Exportar Datos y Reportes (CSV)")
        self.setMinimumWidth(540)
        self.resize(580, 560)

        self.application = application
        self.filtered_items = list(filtered_items) if filtered_items is not None else None
        self.current_theme = current_theme
        self.is_dark_mode = is_dark_mode

        if parent is None or not parent.isVisible():
            ensure_dialog_taskbar_presence(self)
        else:
            self.setWindowIcon(get_app_icon())

        self.setStyleSheet(get_dialog_stylesheet(self.current_theme))
        self._tokens = get_theme_tokens(self.current_theme)

        self._init_ui()
        self._update_default_file_path()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # 1. Cabecera (Icono + Título + Descripción)
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel(self)
        icon_color = "#84cc16" if self.is_dark_mode else "#65a30d"
        icon_label.setPixmap(qta.icon("fa5s.file-export", color=icon_color).pixmap(32, 32))
        header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Exportar Datos y Reportes", self)
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self._tokens.text_primary};")
        subtitle = QLabel("Genera archivos CSV compatibles con Microsoft Excel, Google Sheets y Pandas.", self)
        subtitle.setStyleSheet(f"font-size: 12px; color: {self._tokens.text_secondary};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        layout.addLayout(header)

        # 2. Grupo: Tipo de Reporte
        type_box = self._create_card("1. Tipo de Reporte")
        type_layout = QVBoxLayout(type_box)
        type_layout.setSpacing(8)
        type_layout.setContentsMargins(14, 12, 14, 12)

        self.type_button_group = QButtonGroup(self)
        self.radio_detailed = QRadioButton("Historial detallado de intentos (Nivel Registro)", self)
        self.radio_detailed.setChecked(True)
        self.type_button_group.addButton(self.radio_detailed)

        detailed_hint = QLabel("   Cada fila es un intento con fecha, hora, tiempos netos y descansos, notas y etiquetas.", self)
        detailed_hint.setStyleSheet(f"font-size: 11px; color: {self._tokens.text_muted};")

        self.radio_summary = QRadioButton("Resumen consolidado por guía y ejercicios (Nivel Guía)", self)
        self.type_button_group.addButton(self.radio_summary)

        summary_hint = QLabel("   Una fila por ejercicio con estado, tasa de éxito, mejor marca (PB) y acumulados.", self)
        summary_hint.setStyleSheet(f"font-size: 11px; color: {self._tokens.text_muted};")

        type_layout.addWidget(self.radio_detailed)
        type_layout.addWidget(detailed_hint)
        type_layout.addWidget(self.radio_summary)
        type_layout.addWidget(summary_hint)

        self.radio_detailed.toggled.connect(self._on_type_changed)
        layout.addWidget(type_box)

        # 3. Grupo: Alcance de los Datos
        self.scope_box = self._create_card("2. Alcance de los Datos")
        scope_layout = QVBoxLayout(self.scope_box)
        scope_layout.setSpacing(8)
        scope_layout.setContentsMargins(14, 12, 14, 12)

        self.scope_button_group = QButtonGroup(self)
        self.radio_scope_all = QRadioButton("Todos los registros del proyecto activo", self)
        self.radio_scope_all.setChecked(True)
        self.scope_button_group.addButton(self.radio_scope_all)
        scope_layout.addWidget(self.radio_scope_all)

        filtered_count = len(self.filtered_items) if self.filtered_items is not None else 0
        self.radio_scope_filtered = QRadioButton(
            f"Solo registros visibles / filtrados en pantalla ({filtered_count} intentos)",
            self,
        )
        self.radio_scope_filtered.setEnabled(self.filtered_items is not None and len(self.filtered_items) > 0)
        self.scope_button_group.addButton(self.radio_scope_filtered)
        scope_layout.addWidget(self.radio_scope_filtered)

        self.radio_scope_dates = QRadioButton("Rango de fechas específico", self)
        self.scope_button_group.addButton(self.radio_scope_dates)
        scope_layout.addWidget(self.radio_scope_dates)

        # Sub-contenedor de fechas
        self.dates_container = QWidget(self)
        dates_layout = QHBoxLayout(self.dates_container)
        dates_layout.setContentsMargins(20, 2, 0, 2)
        dates_layout.setSpacing(10)

        lbl_from = QLabel("Desde:", self.dates_container)
        lbl_from.setStyleSheet(f"color: {self._tokens.text_secondary}; font-size: 12px;")
        self.date_from = QDateEdit(self.dates_container)
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")

        lbl_to = QLabel("Hasta:", self.dates_container)
        lbl_to.setStyleSheet(f"color: {self._tokens.text_secondary}; font-size: 12px;")
        self.date_to = QDateEdit(self.dates_container)
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")

        self._init_dates()

        dates_layout.addWidget(lbl_from)
        dates_layout.addWidget(self.date_from)
        dates_layout.addWidget(lbl_to)
        dates_layout.addWidget(self.date_to)
        dates_layout.addStretch()

        self.dates_container.setEnabled(False)
        self.radio_scope_dates.toggled.connect(self.dates_container.setEnabled)
        scope_layout.addWidget(self.dates_container)

        layout.addWidget(self.scope_box)

        # 4. Grupo: Formato y Delimitador
        delim_box = self._create_card("3. Formato y Delimitador")
        delim_layout = QVBoxLayout(delim_box)
        delim_layout.setSpacing(6)
        delim_layout.setContentsMargins(14, 12, 14, 12)

        self.delim_button_group = QButtonGroup(self)
        self.radio_delim_semicolon = QRadioButton(
            "Punto y coma ( ; ) — Recomendado para Microsoft Excel en Español / Latinoamericano",
            self,
        )
        self.radio_delim_semicolon.setChecked(True)
        self.delim_button_group.addButton(self.radio_delim_semicolon)

        self.radio_delim_comma = QRadioButton(
            "Coma ( , ) — Estándar internacional / RFC 4180 / Python / R",
            self,
        )
        self.delim_button_group.addButton(self.radio_delim_comma)

        delim_layout.addWidget(self.radio_delim_semicolon)
        delim_layout.addWidget(self.radio_delim_comma)
        layout.addWidget(delim_box)

        # 5. Grupo: Destino
        dest_box = self._create_card("4. Archivo de Destino")
        dest_layout = QHBoxLayout(dest_box)
        dest_layout.setSpacing(8)
        dest_layout.setContentsMargins(14, 12, 14, 12)

        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText("Ruta del archivo CSV destino...")
        self.browse_button = QPushButton("Examinar...", self)
        self.browse_button.setIcon(qta.icon("fa5s.folder-open", color=self._tokens.text_primary))
        self.browse_button.clicked.connect(self._on_browse)

        dest_layout.addWidget(self.path_input, 1)
        dest_layout.addWidget(self.browse_button)
        layout.addWidget(dest_box)

        # 6. Botones de acción inferiores
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.cancel_button = QPushButton("Cancelar", self)
        self.cancel_button.setMinimumWidth(95)
        self.cancel_button.clicked.connect(self.reject)

        self.export_button = QPushButton("  Exportar Datos", self)
        self.export_button.setIcon(qta.icon("fa5s.file-export", color="#000000" if self.is_dark_mode else "#ffffff"))
        self.export_button.setMinimumWidth(140)
        self.export_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self._tokens.toolbar_primary_bg};
                color: {self._tokens.toolbar_primary_fg};
                font-weight: 700;
                font-size: 13px;
                border: 1px solid {self._tokens.toolbar_primary_border};
                border-radius: 6px;
                padding: 7px 16px;
            }}
            QPushButton:hover {{
                background-color: {self._tokens.toolbar_primary_hover_bg};
            }}
            """
        )
        self.export_button.clicked.connect(self._on_export)

        btn_layout.addWidget(self.cancel_button)
        btn_layout.addWidget(self.export_button)
        layout.addLayout(btn_layout)

    def _create_card(self, title_text: str) -> QFrame:
        """Crea una tarjeta contenedora estilizada."""
        card = QFrame(self)
        card.setObjectName("export_card")
        card.setStyleSheet(
            f"""
            QFrame#export_card {{
                background-color: {self._tokens.bg_card};
                border: 1px solid {self._tokens.card_border};
                border-radius: 8px;
            }}
            """
        )
        return card

    def _init_dates(self) -> None:
        """Inicializa los selectores de fechas con el historial existente o fecha actual."""
        items = self.application.record.items if self.application.is_record_open else []
        today = QDate.currentDate()
        if items:
            earliest_str = min(it.created_at[:10] for it in items)
            latest_str = max(it.created_at[:10] for it in items)
            try:
                d_earliest = QDate.fromString(earliest_str, "yyyy-MM-dd")
                d_latest = QDate.fromString(latest_str, "yyyy-MM-dd")
                self.date_from.setDate(d_earliest if d_earliest.isValid() else today)
                self.date_to.setDate(d_latest if d_latest.isValid() else today)
                return
            except Exception:
                pass
        self.date_from.setDate(today)
        self.date_to.setDate(today)

    def _on_type_changed(self) -> None:
        """Actualiza la disponibilidad de opciones y la ruta por defecto."""
        is_detailed = self.radio_detailed.isChecked()
        self.scope_box.setEnabled(is_detailed)
        self._update_default_file_path()

    def _update_default_file_path(self) -> None:
        """Genera un nombre de archivo por defecto sugerido."""
        default_dir = getattr(self.application.storage, "default_directory", Path.cwd())
        record_name = "StudyTimetrial"
        if self.application.record_path:
            record_name = self.application.record_path.stem
        elif self.application.is_record_open and self.application.record.record_name:
            record_name = self.application.record.record_name

        stamp = datetime.now().strftime("%Y%m%d")
        mode_suffix = "intentos" if self.radio_detailed.isChecked() else "resumen"
        suggested = default_dir / f"{record_name}_{mode_suffix}_{stamp}.csv"
        self.path_input.setText(str(suggested))

    def _on_browse(self) -> None:
        current_path = self.path_input.text().strip()
        start_dir = str(Path(current_path).parent if current_path else Path.cwd())
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar destino de exportación",
            current_path or start_dir,
            "Archivos CSV (*.csv);;Todos los archivos (*.*)",
        )
        if selected:
            self.path_input.setText(selected)
        force_activate_window(self)

    def _on_export(self) -> None:
        dest_str = self.path_input.text().strip()
        if not dest_str:
            QMessageBox.warning(self, "Ruta requerida", "Por favor seleccione un archivo destino para la exportación.")
            return

        target_path = Path(dest_str)
        delimiter = ";" if self.radio_delim_semicolon.isChecked() else ","

        if self.radio_detailed.isChecked():
            # Determinar items según alcance
            items: Sequence[TimerItem] | None = None
            if self.radio_scope_filtered.isChecked() and self.filtered_items is not None:
                items = self.filtered_items
            elif self.radio_scope_dates.isChecked():
                start_iso = self.date_from.date().toString("yyyy-MM-dd")
                end_iso = self.date_to.date().toString("yyyy-MM-dd")
                all_items = self.application.record.items if self.application.is_record_open else []
                items = [
                    it for it in all_items
                    if start_iso <= it.created_at[:10] <= end_iso
                ]

            result = self.application.export_items_to_csv(
                file_path=target_path,
                items=items,
                delimiter=delimiter,
            )
        else:
            result = self.application.export_summary_to_csv(
                file_path=target_path,
                delimiter=delimiter,
            )

        if not result.success:
            QMessageBox.critical(self, "Error en la exportación", result.error_message or "Error desconocido.")
            return

        # Notificación amigable con opción de abrir la carpeta
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Exportación exitosa")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(
            f"Se exportaron exitosamente {result.rows_exported} filas.\n\n"
            f"Archivo guardado en:\n{result.file_path}"
        )
        btn_open = msg_box.addButton("Abrir carpeta contenedora", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Ok)

        msg_box.exec()

        if msg_box.clickedButton() == btn_open:
            folder_uri = QUrl.fromLocalFile(str(result.file_path.parent))
            QDesktopServices.openUrl(folder_uri)

        self.accept()
