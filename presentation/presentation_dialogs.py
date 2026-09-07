"""Dialogos Qt de la capa de presentacion de Study Timetrial.

Los dialogos validan y traducen entradas visuales a modelos de dominio, pero
no ejecutan casos de uso ni escriben directamente en el almacenamiento.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from domain.models import Record, TimerItem
from presentation.presentation_formatters import format_milliseconds, parse_milliseconds

DEFAULT_SECTION_TYPE = "Guía"
MAX_VALUE = 999_999


class ItemDialog(QDialog):
    """Formulario para crear o editar un item del historial de ejercicios."""

    def __init__(self, parent: QWidget | None = None, item: TimerItem | None = None) -> None:
        super().__init__(parent)
        self.validated_item: TimerItem | None = None
        self.setWindowTitle("Editar item" if item else "Agregar item")

        form = QFormLayout(self)
        self.section_type = QLineEdit(item.section_type if item else DEFAULT_SECTION_TYPE)
        self.section_number = QSpinBox()
        self.section_number.setRange(1, MAX_VALUE)
        self.section_number.setValue(item.section_number if item else 1)
        self.exercise = QSpinBox()
        self.exercise.setRange(1, MAX_VALUE)
        self.exercise.setValue(item.exercise if item else 1)
        self.inciso = QSpinBox()
        self.inciso.setRange(0, MAX_VALUE)
        self.inciso.setSpecialValueText("Sin inciso")
        self.inciso.setValue(item.inciso or 0 if item else 0)
        self.exercise_time = QLineEdit(format_milliseconds(item.exercise_time_ms if item else 0))
        self.break_time = QLineEdit(format_milliseconds(item.break_time_ms if item else 0))
        self.completed = QCheckBox("Completado")
        self.completed.setChecked(item.completed if item else False)

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
            exercise_time_ms=parse_milliseconds(self.exercise_time.text()),
            break_time_ms=parse_milliseconds(self.break_time.text()),
            completed=self.completed.isChecked(),
        )

        if existing:
            result.id = existing.id
            result.created_at = existing.created_at
            result.comment = existing.comment

        return result

    def accept(self) -> None:
        """Valida el formulario antes de cerrar el diálogo."""
        try:
            self.validated_item = self.item()
        except (TypeError, ValueError) as error:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Valor inválido", str(error))
            return
        super().accept()


class ImportRecordsDialog(QDialog):
    """Permite elegir items individuales de otro archivo de registro."""

    def __init__(self, record: Record, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Importar registros")
        self.resize(650, 420)
        self.table = QTableWidget(len(record.items), 6)
        self.table.setHorizontalHeaderLabels([
            "Añadir",
            "Sección",
            "Ejercicio",
            "Inciso",
            "Tiempo",
            "Estado",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        for row, item in enumerate(record.items):
            selected = QTableWidgetItem()
            selected.setCheckState(Qt.CheckState.Checked)
            selected.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            self.table.setItem(row, 0, selected)
            self.table.setItem(row, 1, QTableWidgetItem(f"{item.section_type} {item.section_number}"))
            self.table.setItem(row, 2, QTableWidgetItem(str(item.exercise)))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.inciso or "-")))
            self.table.setItem(row, 4, QTableWidgetItem(format_milliseconds(item.exercise_time_ms)))
            self.table.setItem(row, 5, QTableWidgetItem("Sí" if item.completed else "No"))

        select_all = QPushButton("Seleccionar todos")
        select_all.clicked.connect(lambda: self.set_all_checked(True))
        clear_selection = QPushButton("Limpiar selección")
        clear_selection.clicked.connect(lambda: self.set_all_checked(False))
        selection_buttons = QHBoxLayout()
        selection_buttons.addWidget(select_all)
        selection_buttons.addWidget(clear_selection)
        selection_buttons.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecciona los registros que deseas añadir al archivo actual:"))
        layout.addWidget(self.table)
        layout.addLayout(selection_buttons)
        layout.addWidget(buttons)

    def set_all_checked(self, checked: bool) -> None:
        """Marca o desmarca todos los items de la tabla."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)

    def selected_indexes(self) -> list[int]:
        """Devuelve los índices de los items seleccionados."""
        return [
            row for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() is Qt.CheckState.Checked
        ]
