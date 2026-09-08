import os
import unittest
from PySide6.QtWidgets import QApplication

from application.record_query import COL_EXERCISE, COL_SECTION, ColumnFilterRule
from domain.models import TimerItem
from presentation.excel_filter_popup import ExcelColumnFilterPopup
from presentation.main_window import MainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class MainWindowExcelRecordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()
        # Agregar items de prueba variados
        self.window.application.record.items = [
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=1,
                inciso=None,
                exercise_time_ms=60000,
                break_time_ms=5000,
                completed=True,
                comment="Fácil",
                created_at="2026-09-07T10:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=2,
                exercise_time_ms=120000,
                break_time_ms=15000,
                completed=False,
                comment="",
                created_at="2026-09-07T12:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=30000,
                break_time_ms=2000,
                completed=True,
                comment="",
                created_at="2026-09-06T09:00:00",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=1,
                exercise_time_ms=90000,
                break_time_ms=10000,
                completed=True,
                comment="Duda",
                created_at="2026-09-07T11:00:00",
            ),
        ]
        self.window.refresh_table()

    def test_header_is_movable_and_has_12_columns(self) -> None:
        header = self.window.table.horizontalHeader()
        self.assertTrue(header.sectionsMovable())
        self.assertEqual(self.window.table.columnCount(), 12)

    def test_header_3_click_cycle(self) -> None:
        """Ciclo de 3 clics: 1: Ascendente (▲), 2: Descendente (▼), 3: Quitar orden."""
        # Columna 0 es Sección
        # Clic 1 -> asc
        self.window._on_header_section_clicked(0)
        self.assertEqual(self.window.column_sort_states.get(COL_SECTION), "asc")
        header_text = self.window.table.horizontalHeaderItem(0).text()
        self.assertIn("▲", header_text)

        # Clic 2 -> desc
        self.window._on_header_section_clicked(0)
        self.assertEqual(self.window.column_sort_states.get(COL_SECTION), "desc")
        header_text = self.window.table.horizontalHeaderItem(0).text()
        self.assertIn("▼", header_text)

        # Clic 3 -> sin orden
        self.window._on_header_section_clicked(0)
        self.assertNotIn(COL_SECTION, self.window.column_sort_states)
        header_text = self.window.table.horizontalHeaderItem(0).text()
        self.assertNotIn("▲", header_text)
        self.assertNotIn("▼", header_text)

    def test_multisort_hierarchy_from_left_to_right(self) -> None:
        """Si se activa Sección (col 0) y Ejercicio (col 1), Sección domina porque está a la izquierda."""
        self.window._on_header_section_clicked(0)  # Sección asc
        self.window._on_header_section_clicked(1)  # Ejercicio asc

        active_sorts = self.window.get_active_sorts_by_hierarchy()
        self.assertEqual(active_sorts, [(COL_SECTION, "asc"), (COL_EXERCISE, "asc")])

        # Comprobar resultado en la tabla
        self.assertEqual(self.window.table.rowCount(), 4)
        self.assertEqual(self.window.table.item(0, 0).text(), "Guía 1")
        self.assertEqual(self.window.table.item(0, 1).text(), "1")

        self.assertEqual(self.window.table.item(3, 0).text(), "Guía 2")
        self.assertEqual(self.window.table.item(3, 1).text(), "1")

    def test_column_reorder_changes_hierarchy(self) -> None:
        """Al mover Ejercicio (col 1) antes de Sección (col 0), Ejercicio pasa a ser la jerarquía dominante."""
        self.window._on_header_section_clicked(0)  # Sección asc
        self.window._on_header_section_clicked(1)  # Ejercicio asc

        # Mover visualmente la sección 1 (Ejercicio) a la posición 0
        header = self.window.table.horizontalHeader()
        header.moveSection(1, 0)
        self.window._on_column_moved(1, 1, 0)

        active_sorts = self.window.get_active_sorts_by_hierarchy()
        # Ahora Ejercicio está a la izquierda de Sección
        self.assertEqual(active_sorts[0][0], COL_EXERCISE)
        self.assertEqual(active_sorts[1][0], COL_SECTION)

        # En la tabla, deben aparecer los ejercicios 1 primero (de Guía 1 y Guía 2)
        first_row_ex = self.window.table.item(0, 1).text()
        second_row_ex = self.window.table.item(1, 1).text()
        self.assertEqual(first_row_ex, "1")
        self.assertEqual(second_row_ex, "1")

    def test_excel_filter_popup_application(self) -> None:
        """Prueba aplicar filtro de checkboxes desde ExcelColumnFilterPopup."""
        # Filtrar solo 'Guía 2'
        rule = ColumnFilterRule(selected_values={"Guía 2"})
        self.window._on_popup_filter_applied(COL_SECTION, rule)

        self.assertEqual(self.window.table.rowCount(), 1)
        self.assertEqual(self.window.table.item(0, 0).text(), "Guía 2")

        # Debe mostrar icono de filtro en el cabezal de Sección
        header_text = self.window.table.horizontalHeaderItem(0).text()
        self.assertIn("🔍", header_text)

        # Resetear filtros
        self.window.reset_all_filters()
        self.assertEqual(self.window.table.rowCount(), 4)
        header_text_reset = self.window.table.horizontalHeaderItem(0).text()
        self.assertNotIn("🔍", header_text_reset)


if __name__ == "__main__":
    unittest.main()
