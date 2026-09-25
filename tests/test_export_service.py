from __future__ import annotations

"""Pruebas unitarias para el servicio de exportación CSV/Excel y el diálogo de exportación (TASK-009)."""

import csv
import os
from pathlib import Path
import tempfile
import unittest

from application.application_service import StudyApplicationService
from domain.models import PlannedSection, Record, TagDefinition, TimerItem
from infrastructure.export_service import (
    ExportResult,
    export_items_to_csv,
    export_summary_to_csv,
    format_ms_to_hhmmss,
)
from infrastructure.storage_service import StorageService

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestExportInfrastructure(unittest.TestCase):
    """Pruebas de la capa de infraestructura para formateo y escritura RFC 4180 con BOM."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_format_ms_to_hhmmss(self) -> None:
        self.assertEqual(format_ms_to_hhmmss(0), "00:00:00")
        self.assertEqual(format_ms_to_hhmmss(999), "00:00:00")
        self.assertEqual(format_ms_to_hhmmss(1000), "00:00:01")
        self.assertEqual(format_ms_to_hhmmss(61000), "00:01:01")
        self.assertEqual(format_ms_to_hhmmss(3665000), "01:01:05")

    def test_export_items_to_csv_detailed_semicolon(self) -> None:
        file_path = self.dir_path / "test_export_detailed.csv"

        tag_catalog = [
            TagDefinition(id="t1", name="Rehacer", color="#ef4444"),
            TagDefinition(id="t2", name="Duda", color="#f59e0b"),
        ]

        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=3,
        )
        sec.set_exercise_tags(1, None, ["t1"])
        sec.set_note(1, None, "Nota con salto de línea\ny comilla \"especial\"")

        items = [
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=125000,
                break_time_ms=15000,
                completed=True,
                comment="Comentario del intento 1",
                created_at="2026-09-25T10:15:30",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=1,
                exercise_time_ms=45000,
                break_time_ms=5000,
                completed=False,
                comment="",
                created_at="2026-09-25T11:00:00",
            ),
        ]

        result = export_items_to_csv(
            file_path=file_path,
            items=items,
            delimiter=";",
            tag_catalog=tag_catalog,
            planner_sections=[sec],
        )

        self.assertTrue(result.success)
        self.assertEqual(result.rows_exported, 2)
        self.assertTrue(file_path.exists())

        # Verificar que comienza con el BOM UTF-8 (\xef\xbb\xbf) para compatibilidad con Excel
        raw_bytes = file_path.read_bytes()
        self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"))

        # Leer con csv.reader asegurando decodificación utf-8-sig
        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as fp:
            reader = list(csv.reader(fp, delimiter=";"))

        # Verificar cabecera
        self.assertEqual(len(reader), 3)  # Cabecera + 2 filas
        headers = reader[0]
        self.assertIn("Fecha", headers)
        self.assertIn("Guia / Seccion", headers)
        self.assertIn("Identificador", headers)
        self.assertIn("Etiquetas", headers)
        self.assertIn("Notas / Apuntes", headers)

        # Fila 1
        row1 = reader[1]
        self.assertEqual(row1[0], "2026-09-25")
        self.assertEqual(row1[1], "10:15:30")
        self.assertEqual(row1[3], "Guía")
        self.assertEqual(row1[4], "1")
        self.assertEqual(row1[5], "1")
        self.assertEqual(row1[6], "")  # Inciso vacío
        self.assertEqual(row1[7], "Guía 1 · Ej. 1")
        self.assertEqual(row1[8], "Completado")
        self.assertEqual(row1[9], "00:02:05")
        self.assertEqual(row1[15], "Rehacer")
        self.assertIn("Nota con salto de línea", row1[16])
        self.assertEqual(row1[17], "Comentario del intento 1")

        # Fila 2
        row2 = reader[2]
        self.assertEqual(row2[6], "1")  # Inciso 1
        self.assertEqual(row2[7], "Guía 1 · Ej. 2.1")
        self.assertEqual(row2[8], "Incompleto")

    def test_export_items_comma_delimiter(self) -> None:
        file_path = self.dir_path / "test_comma.csv"
        items = [
            TimerItem(
                section_type="TP",
                section_number=2,
                exercise=4,
                inciso=None,
                exercise_time_ms=60000,
                break_time_ms=0,
                completed=True,
                comment="Listo",
                created_at="2026-09-25T14:00:00",
            )
        ]
        result = export_items_to_csv(file_path, items, delimiter=",")
        self.assertTrue(result.success)

        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as fp:
            reader = list(csv.reader(fp, delimiter=","))

        self.assertEqual(len(reader), 2)
        self.assertEqual(reader[1][3], "TP")

    def test_export_summary_to_csv(self) -> None:
        file_path = self.dir_path / "test_summary.csv"
        summary_rows = [
            {
                "section_type": "Guía",
                "section_number": 1,
                "exercise": 1,
                "inciso": "",
                "identifier": "Guía 1 · Ejercicio 1",
                "resolution_status": "Resuelto",
                "total_attempts": 3,
                "completed_attempts": 2,
                "failed_attempts": 1,
                "success_rate": "66.7%",
                "total_time_hhmmss": "00:25:30",
                "total_time_s": "1530.00",
                "avg_time_hhmmss": "00:08:30",
                "pb_time_hhmmss": "00:06:10",
                "tags": "Importante | Rehacer",
                "notes": "Recordar teorema de Taylor",
            }
        ]

        result = export_summary_to_csv(file_path, summary_rows, delimiter=";")
        self.assertTrue(result.success)
        self.assertEqual(result.rows_exported, 1)

        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as fp:
            reader = list(csv.reader(fp, delimiter=";"))

        self.assertEqual(len(reader), 2)
        headers = reader[0]
        self.assertIn("Estado Resolucion", headers)
        self.assertIn("Mejor Marca PB (hh:mm:ss)", headers)

        data = reader[1]
        self.assertEqual(data[5], "Resuelto")
        self.assertEqual(data[6], "3")
        self.assertEqual(data[9], "66.7%")
        self.assertEqual(data[13], "00:06:10")
        self.assertEqual(data[14], "Importante | Rehacer")
        self.assertEqual(data[15], "Recordar teorema de Taylor")

    def test_export_empty_list_yields_valid_csv_with_headers(self) -> None:
        file_path = self.dir_path / "empty.csv"
        result = export_items_to_csv(file_path, items=[])
        self.assertTrue(result.success)
        self.assertEqual(result.rows_exported, 0)
        self.assertTrue(file_path.exists())

        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as fp:
            reader = list(csv.reader(fp, delimiter=";"))
        self.assertEqual(len(reader), 1)  # Solo encabezado


class TestExportApplicationService(unittest.TestCase):
    """Pruebas de la orquestación de exportación en StudyApplicationService."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(default_dir=Path(self.temp_dir.name))
        self.app = StudyApplicationService(storage=self.storage)
        self.app.new_record("Algebra")

        # Planificar 1 sección con 2 ejercicios
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=2)
        sec.set_note(1, None, "Nota del ejercicio 1")
        self.app.record.planner_sections = [sec]

        # Agregar intentos
        self.app.record.items = [
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=180000,
                break_time_ms=20000,
                completed=True,
                comment="Excelente",
                created_at="2026-09-24T15:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=90000,
                break_time_ms=10000,
                completed=False,
                comment="Duda en paso 2",
                created_at="2026-09-25T16:00:00",
            ),
        ]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_app_export_items_to_csv(self) -> None:
        target = Path(self.temp_dir.name) / "algebra_items.csv"
        result = self.app.export_items_to_csv(target, delimiter=";")
        self.assertTrue(result.success)
        self.assertEqual(result.rows_exported, 2)
        self.assertTrue(target.exists())

    def test_app_export_items_with_filtered_subset(self) -> None:
        target = Path(self.temp_dir.name) / "algebra_subset.csv"
        subset = [self.app.record.items[0]]
        result = self.app.export_items_to_csv(target, items=subset, delimiter=";")
        self.assertTrue(result.success)
        self.assertEqual(result.rows_exported, 1)

    def test_app_export_summary_to_csv(self) -> None:
        target = Path(self.temp_dir.name) / "algebra_summary.csv"
        result = self.app.export_summary_to_csv(target, delimiter=";")
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.rows_exported, 2)
        self.assertTrue(target.exists())


class TestExportDialog(unittest.TestCase):
    """Pruebas de la vista pasiva ExportDialog en PySide6 offscreen."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication
        cls.qapp = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageService(default_dir=Path(self.temp_dir.name))
        self.app = StudyApplicationService(storage=self.storage)
        self.app.new_record("Fisica")
        self.app.record.items = [
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=10000,
                break_time_ms=1000,
                completed=True,
                created_at="2026-09-25T10:00:00",
            )
        ]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_dialog_init_and_controls(self) -> None:
        from presentation.export_dialog import ExportDialog

        dialog = ExportDialog(self.app, current_theme="light", is_dark_mode=False)
        self.assertEqual(dialog.windowTitle(), "Exportar Datos y Reportes (CSV)")
        self.assertTrue(dialog.radio_detailed.isChecked())
        self.assertTrue(dialog.radio_scope_all.isChecked())
        self.assertTrue(dialog.radio_delim_semicolon.isChecked())
        self.assertTrue(dialog.path_input.text().endswith(".csv"))

        # Cambiar a resumen
        dialog.radio_summary.setChecked(True)
        self.assertFalse(dialog.scope_box.isEnabled())
        self.assertTrue("resumen" in dialog.path_input.text())

        # Volver a detallado
        dialog.radio_detailed.setChecked(True)
        self.assertTrue(dialog.scope_box.isEnabled())
        self.assertTrue("intentos" in dialog.path_input.text())

        dialog.close()


if __name__ == "__main__":
    unittest.main()
