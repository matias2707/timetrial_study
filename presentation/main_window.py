"""Ventana principal de la aplicación Study Timetrial.

Ensambla y orquesta la interfaz gráfica delegando en vistas y servicios desacoplados.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

from application.application_service import StudyApplicationService
from domain.models import TimerItem
from domain.timer_service import TimerMode
from presentation.app_toolbar import AppToolbar
from presentation.audio_service import AudioService
from presentation.home_view import APP_TITLE, APP_VERSION, DEFAULT_SECTION_TYPE, MAX_VALUE, HomeViewWidget
from presentation.planner_widget import PlannerWidget
from presentation.presentation_dialogs import ImportRecordsDialog
from presentation.records_view import RecordsViewWidget
from presentation.statistics_view import StatisticsViewWidget
from presentation.theme import (
    THEME_DARK,
    THEME_LIGHT,
    get_dialog_stylesheet,
    get_theme_stylesheet,
)
from presentation.weekly_chart_widget import WeeklyChartWidget

__all__ = ["MainWindow", "WeeklyChartWidget", "APP_TITLE", "APP_VERSION", "DEFAULT_SECTION_TYPE", "MAX_VALUE"]


class MainWindow(QMainWindow):
    """Ventana principal que orquesta la barra de herramientas, pestañas y diálogos."""

    STYLESHEET = get_theme_stylesheet(THEME_LIGHT)

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("StudyTimetrial", "Preferences")
        self.current_theme = str(self.settings.value("theme", THEME_LIGHT))
        if self.current_theme not in (THEME_LIGHT, THEME_DARK):
            self.current_theme = THEME_LIGHT

        self.application = StudyApplicationService()
        self.audio_service = AudioService(self)

        # Configurar icono oficial
        media_dir = Path(__file__).resolve().parent / "media"
        app_icon_path = media_dir / "app_icon.ico"
        if not app_icon_path.exists():
            app_icon_path = media_dir / "app_icon.png"
        if app_icon_path.exists():
            self.setWindowIcon(QIcon(str(app_icon_path)))

        self.setMinimumSize(940, 700)
        self._apply_current_stylesheet()

        # Barra de herramientas desacoplada
        self.toolbar = AppToolbar(is_dark_mode=self.is_dark_mode, parent=self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        self.toolbar.update_sound_action(self.audio_service.is_muted)

        # Construcción de vistas modulares
        self.home_view = HomeViewWidget(
            application=self.application,
            audio_service=self.audio_service,
            is_dark_mode=self.is_dark_mode,
            parent=self,
        )
        self.records_view = RecordsViewWidget(
            application=self.application,
            parent=self,
        )
        self.statistics_view = StatisticsViewWidget(
            application=self.application,
            is_dark_mode=self.is_dark_mode,
            parent=self,
        )
        self.planner = PlannerWidget(
            self.application,
            is_dark_mode=self.is_dark_mode,
            parent=self,
        )

        # Contenedor de pestañas
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.home = self.home_view
        self.records = self.records_view
        self.statistics = self.statistics_view

        self.tabs.addTab(self.home_view, qta.icon("fa5s.stopwatch", color="#bef264"), "  Cronómetro")
        self.tabs.addTab(self.records_view, qta.icon("fa5s.history", color="#94a3b8"), "  Registros")
        self.tabs.addTab(self.statistics_view, qta.icon("fa5s.chart-bar", color="#94a3b8"), "  Estadísticas")
        self.tabs.addTab(self.planner, qta.icon("fa5s.tasks", color="#94a3b8"), "  Planificador")

        self._connect_signals()

        # Timer para el refresco del reloj (50 ms)
        self.tick = QTimer(self)
        self.tick.timeout.connect(self.refresh_clock)
        self.tick.start(50)

        self.refresh_recent_files_menu()
        self.prompt_initial_record_choice()
        self.update_title()
        self.refresh_table()
        self.refresh_statistics()
        self.autosave()

    def _apply_current_stylesheet(self) -> None:
        stylesheet = get_theme_stylesheet(self.current_theme)
        self.setStyleSheet(stylesheet)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)

    def _connect_signals(self) -> None:
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Conexiones de la barra de herramientas
        self.toolbar.request_new_record.connect(self.new_record)
        self.toolbar.request_open_record.connect(self.open_record)
        self.toolbar.request_open_recent.connect(self.open_recent_record)
        self.toolbar.request_save_as.connect(self.save_as)
        self.toolbar.request_close_record.connect(self.close_record)
        self.toolbar.request_close_app.connect(self.close)
        self.toolbar.request_theme_change.connect(self.set_theme)
        self.toolbar.request_toggle_sound.connect(self.toggle_sound_muted)

        # Conexiones de vistas
        self.home_view.item_finished.connect(self._on_home_item_finished)
        self.records_view.data_modified.connect(self._on_records_data_modified)
        self.records_view.request_open_record.connect(self.open_record)
        self.records_view.request_import_records.connect(self.import_records)
        self.records_view.request_save_as.connect(self.save_as)
        self.records_view.request_rename_record.connect(self.rename_record)
        self.records_view.request_close_record.connect(self.close_record)

        self.planner.request_load_timer.connect(self._on_planner_load_timer)

    def _on_tab_changed(self, index: int) -> None:
        icons = [
            ("fa5s.stopwatch", "Cronómetro"),
            ("fa5s.history", "Registros"),
            ("fa5s.chart-bar", "Estadísticas"),
            ("fa5s.tasks", "Planificador"),
        ]
        for i, (icon_name, _title) in enumerate(icons):
            color = "#bef264" if i == index else "#94a3b8"
            self.tabs.setTabIcon(i, qta.icon(icon_name, color=color))

        if index == 1:
            self.refresh_table()
        elif index == 2:
            self.refresh_statistics()
        elif index == 3:
            self.planner.refresh_view()

    def _on_home_item_finished(self, _completed: bool) -> None:
        self.application.sync_planner_with_records()
        self.planner.refresh_view()
        self.refresh_table()
        self.refresh_statistics()

    def _on_records_data_modified(self) -> None:
        self.application.sync_planner_with_records()
        self.planner.refresh_view()
        self.refresh_statistics()

    # --- Gestión de temas y sonidos ---

    @property
    def is_dark_mode(self) -> bool:
        return self.current_theme == THEME_DARK

    @property
    def is_sound_muted(self) -> bool:
        return self.audio_service.is_muted

    @is_sound_muted.setter
    def is_sound_muted(self, value: bool) -> None:
        self.audio_service.is_muted = value
        self.toolbar.update_sound_action(self.audio_service.is_muted)

    @property
    def is_muted(self) -> bool:
        return self.is_sound_muted

    def toggle_sound_muted(self) -> None:
        self.set_sound_muted(not self.is_sound_muted)

    def set_sound_muted(self, muted: bool) -> None:
        self.is_sound_muted = muted

    def update_sound_action(self) -> None:
        self.toolbar.update_sound_action(self.audio_service.is_muted)

    def play_start_sound(self) -> None:
        self.audio_service.play_start()

    def play_complete_sound(self) -> None:
        self.audio_service.play_complete()

    def set_theme(self, theme: str) -> None:
        """Cambia el tema de la aplicación ('light' o 'dark') y propaga a vistas."""
        self.current_theme = theme
        self.settings.setValue("theme", theme)

        self._apply_current_stylesheet()
        self.toolbar.update_theme_icons(self.is_dark_mode)

        self.home_view.is_dark_mode = self.is_dark_mode
        self.statistics_view.set_dark_mode(self.is_dark_mode)
        self.planner.set_dark_mode(self.is_dark_mode)

        self.update_theme_icons()
        self.update_timer_visual_state()

    def update_theme_icons(self) -> None:
        self.toolbar.update_theme_icons(self.is_dark_mode)

    # --- Delegaciones a vistas para compatibilidad 100% con tests y callers ---

    @property
    def table(self):
        return self.records_view.table

    @property
    def column_sort_states(self) -> dict[str, str]:
        return self.records_view.column_sort_states

    @property
    def column_filter_rules(self):
        return self.records_view.column_filter_rules

    @property
    def _current_displayed_items(self) -> list[TimerItem]:
        return self.records_view._current_displayed_items

    @property
    def LOGICAL_COL_KEYS(self):
        return self.records_view.LOGICAL_COL_KEYS

    @property
    def exercise_input(self):
        return self.home_view.exercise_input

    @property
    def inciso_input(self):
        return self.home_view.inciso_input

    @property
    def section_input(self):
        return self.home_view.section_input

    @property
    def section_number_input(self):
        return self.home_view.section_number_input

    @property
    def stepper_buttons(self) -> list:
        return self.home_view.stepper_buttons

    @property
    def primary_controls(self):
        return self.home_view.primary_controls

    @property
    def stop_button(self):
        return self.home_view.stop_button

    @property
    def complete_button(self):
        return self.home_view.complete_button

    @property
    def incomplete_button(self):
        return self.home_view.incomplete_button

    @property
    def comment_button(self):
        return self.home_view.comment_button

    @property
    def session_button(self):
        return self.home_view.session_button

    @property
    def status_pill(self):
        return self.home_view.status_pill

    @property
    def status_label(self):
        return self.home_view.status_label

    @property
    def weekly_chart(self):
        return self.statistics_view.weekly_chart

    @property
    def start_sound(self):
        return self.audio_service.start_sound

    @property
    def complete_sound(self):
        return self.audio_service.complete_sound

    @property
    def config_button(self):
        return self.toolbar.config_button

    @property
    def view_button(self):
        return self.toolbar.view_button

    @property
    def config_menu(self):
        return self.toolbar.config_menu

    @property
    def view_menu(self):
        return self.toolbar.view_menu

    @property
    def themes_menu(self):
        return self.toolbar.themes_menu

    @property
    def theme_dark_action(self):
        return self.toolbar.theme_dark_action

    @property
    def theme_light_action(self):
        return self.toolbar.theme_light_action

    @property
    def sound_action(self):
        return self.toolbar.sound_action

    @property
    def mute_action(self):
        return self.toolbar.mute_action

    @property
    def file_button(self):
        return self.toolbar.file_button

    @property
    def recent_files_menu(self):
        return self.toolbar.recent_files_menu

    def refresh_clock(self) -> None:
        self.home_view.refresh_clock()

    def update_timer_visual_state(self) -> None:
        self.home_view.update_timer_visual_state()

    def sync_location(self, force: bool = False) -> None:
        self.home_view.sync_location(force=force)

    def set_locked(self, locked: bool) -> None:
        self.home_view.set_locked(locked)

    def toggle_session(self) -> None:
        self.home_view.toggle_session()

    def update_session_button(self) -> None:
        self.home_view.update_session_button()

    def stop_timer(self) -> None:
        self.home_view.stop_timer()

    def finish_item(self, completed: bool, keep_location: bool = False, stop: bool = False) -> None:
        self.home_view.finish_item(completed, keep_location=keep_location, stop=stop)

    def _arrange_session_controls(self, compact: bool = False, very_compact: bool = False) -> None:
        self.home_view._arrange_session_controls(compact, very_compact)

    def _create_stepper(self, spinbox, tooltip_prefix: str) -> QWidget:
        return self.home_view._create_stepper(spinbox, tooltip_prefix)

    def _prompt_inciso_gap_dialog(self, *args, **kwargs):
        return self.home_view._prompt_inciso_gap_dialog(*args, **kwargs)

    def _resolve_inciso_gap(self) -> bool:
        return self.home_view._resolve_inciso_gap()

    def add_home_comment(self) -> None:
        self.home_view.add_home_comment()

    def refresh_table(self) -> None:
        self.records_view.refresh_table()

    def refresh_statistics(self) -> None:
        self.statistics_view.refresh_statistics()

    def open_excel_filter_popup(self, logical_index: int, col_key: str) -> None:
        self.records_view.open_excel_filter_popup(logical_index, col_key)

    def filter_records_table(self, query: str = "") -> None:
        self.records_view.filter_records_table(query)

    def reset_all_filters(self) -> None:
        self.records_view.reset_all_filters()

    def delete_item(self, target: int | TimerItem) -> None:
        self.records_view.delete_item(target)

    def edit_item(self, target: int | TimerItem) -> None:
        self.records_view.edit_item(target)

    def reset_item(self, target: int | TimerItem) -> None:
        self.records_view.reset_item(target)

    def comment_item(self, target: int | TimerItem) -> None:
        self.records_view.comment_item(target)

    def add_item(self) -> None:
        self.records_view.add_item()

    def show_comment_alert(self, row: int, column: int) -> None:
        self.records_view.show_comment_alert(row, column)

    def update_header_labels(self) -> None:
        self.records_view.update_header_labels()

    def get_active_sorts_by_hierarchy(self) -> list[tuple[str, str]]:
        return self.records_view.get_active_sorts_by_hierarchy()

    def _on_header_section_clicked(self, logical_index: int) -> None:
        self.records_view._on_header_section_clicked(logical_index)

    def _on_column_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int) -> None:
        self.records_view._on_column_moved(logical_index, old_visual_index, new_visual_index)

    def _on_popup_filter_applied(self, col_key: str, rule) -> None:
        self.records_view._on_popup_filter_applied(col_key, rule)

    def _on_popup_sort_requested(self, col_key: str, direction: str) -> None:
        self.records_view._on_popup_sort_requested(col_key, direction)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "home_view"):
            self.home_view.resizeEvent(event)

    def _on_planner_load_timer(
        self, section_type: str, section_number: int, exercise: int, inciso: int | None
    ) -> None:
        if self.application.mode is not TimerMode.WAITING:
            confirm = QMessageBox.question(
                self,
                "Sesión activa en curso",
                "Hay una sesión activa en el cronómetro. ¿Deseas detenerla para cargar este ejercicio?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            self.stop_timer()

        self.section_input.setText(section_type)
        self.section_number_input.setValue(section_number)
        self.exercise_input.setValue(exercise)
        self.inciso_input.setValue(inciso or 0)
        self.sync_location()
        self.tabs.setCurrentIndex(0)

    # --- Gestión de Archivos y Diálogos ---

    def prompt_initial_record_choice(self) -> None:
        import os
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or os.environ.get("STUDY_TIMETRIAL_TEST"):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Study Timetrial")
        dialog.setModal(True)
        dialog.setMinimumWidth(560)
        dialog.setStyleSheet(get_dialog_stylesheet(self.current_theme))

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

        new_button = QPushButton("  Nuevo archivo")
        new_button.setIcon(qta.icon("fa5s.plus", color="#090d16" if self.is_dark_mode else "#bef264"))
        new_button.setObjectName("primary")
        new_button.clicked.connect(lambda: self._handle_initial_choice(dialog, "new"))

        open_button = QPushButton("  Abrir archivo")
        open_button.setIcon(qta.icon("fa5s.folder-open", color="#cbd5e1" if self.is_dark_mode else "#334155"))
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
        if self.application.is_record_open and (self.application.record.items or self.application.mode is not TimerMode.WAITING):
            answer = QMessageBox.question(
                self,
                "Registro abierto",
                "Hay un registro en memoria. ¿Deseas cerrarlo y crear uno nuevo?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        name, accepted = QInputDialog.getText(
            self,
            "Nuevo registro",
            "Nombre del archivo/registro:",
            QLineEdit.EchoMode.Normal,
            "StudyTimetrial",
        )
        if not accepted:
            return

        self.application.new_record(name.strip() or "StudyTimetrial")
        self.update_title()
        self.refresh_table()

    def update_title(self) -> None:
        record_name = self.application.record_path.name if self.application.record_path else (self.application.record.record_name or "Sin guardar")
        self.setWindowTitle(f"{APP_TITLE} — {record_name}")
        if hasattr(self, "home_view") and hasattr(self.home_view, "home_title"):
            self.home_view.home_title.setText(self.application.record_path.stem if self.application.record_path else record_name)

    def refresh_recent_files_menu(self) -> None:
        recent_paths = self.application.storage.recent_files.paths
        self.toolbar.populate_recent_files(
            recent_paths=recent_paths,
            on_open_file=self.open_record,
            on_select_recent=self.open_recent_record,
        )

    def open_recent_record(self, path: str | Path) -> None:
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
        if self.application.is_record_open and (self.application.record.items or self.application.mode is not TimerMode.WAITING):
            QMessageBox.warning(
                self,
                "Registro abierto",
                "Ya existe un registro abierto. Cierre el registro actual antes de abrir otro.",
            )
            return

        initial_dir = str(getattr(self.application.storage, "default_directory", Path.cwd()))
        path, _ = QFileDialog.getOpenFileName(self, "Abrir registro", initial_dir, "JSON (*.json)")
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
        initial_dir = str(getattr(self.application.storage, "default_directory", Path.cwd()))
        path, _ = QFileDialog.getOpenFileName(self, "Importar registros", initial_dir, "JSON (*.json)")
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
        default_dir = getattr(self.application.storage, "default_directory", Path.cwd())
        default = str(self.application.record_path or (default_dir / "StudyTimetrial.json"))
        path, _ = QFileDialog.getSaveFileName(self, "Guardar registro", default, "JSON (*.json)")
        if path:
            self.application.save_as(Path(path))
            self.update_title()

    def rename_record(self) -> None:
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
        if QMessageBox.question(self, "Cerrar registro", "¿Desea cerrar el registro actual?") != QMessageBox.StandardButton.Yes:
            return

        self.application.close_record()
        self.update_title()
        self.refresh_table()

    def autosave(self) -> None:
        """Autoguarda cambios si existe un fichero vinculado."""
        if self.application.record_path and self.application.is_record_open:
            try:
                self.application.save()
            except OSError:
                pass

    def closeEvent(self, event: QCloseEvent) -> None:
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
            if self.application.mode is not TimerMode.WAITING:
                event.ignore()
                return
            event.accept()
        elif answer is QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()
