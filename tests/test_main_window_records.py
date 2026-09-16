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

    def test_default_order_displays_most_recent_at_top(self) -> None:
        """Comprueba que por defecto la tabla muestra los registros más recientes arriba."""
        self.assertEqual(self.window.table.rowCount(), 4)
        # Fila 0 debe ser el más reciente: 2026-09-07T12:00:00 (Guía 1, Ej 2, Inc 2)
        self.assertEqual(self.window.table.item(0, 0).text(), "Guía 1")
        self.assertEqual(self.window.table.item(0, 1).text(), "2")
        self.assertEqual(self.window.table.item(0, 2).text(), "2")
        self.assertEqual(self.window.table.item(0, 3).text(), "2026-09-07 12:00")

        # Fila 3 debe ser el más antiguo: 2026-09-06T09:00:00 (Guía 1, Ej 1, Inc -)
        self.assertEqual(self.window.table.item(3, 0).text(), "Guía 1")
        self.assertEqual(self.window.table.item(3, 1).text(), "1")
        self.assertEqual(self.window.table.item(3, 3).text(), "2026-09-06 09:00")

        # Al resetear filtros, también debe volver al orden por defecto (más recientes arriba)
        self.window.reset_all_filters()
        self.assertEqual(self.window.table.item(0, 3).text(), "2026-09-07 12:00")
        self.assertEqual(self.window.table.item(3, 3).text(), "2026-09-06 09:00")

    def test_resume_item_requested_loads_into_timer_and_switches_tab(self) -> None:
        """Comprueba que al solicitar continuar un item, este se carga en el cronómetro."""
        item = self.window._current_displayed_items[0]
        self.window.resume_item(item)

        # Debe cambiar a la pestaña 0 (Cronómetro)
        self.assertEqual(self.window.tabs.currentIndex(), 0)

        # Debe haber precargado ubicación
        self.assertEqual(self.window.section_input.text(), item.section_type)
        self.assertEqual(self.window.section_number_input.value(), item.section_number)
        self.assertEqual(self.window.exercise_input.value(), item.exercise)
        self.assertEqual(self.window.inciso_input.value(), item.inciso)

        # Debe estar en modo edición
        self.assertTrue(self.window.application.is_editing)
        self.assertEqual(self.window.application.editing_item_id, item.id)

        # Tiempos acumulados cargados
        self.assertEqual(self.window.application.timer.exercise_time_ms, 120000)
        self.assertEqual(self.window.application.timer.break_time_ms, 15000)

        # Banner visible
        self.assertFalse(self.window.continuation_banner.isHidden())
        self.assertIn("Modo continuación", self.window.home_view.continuation_label.text())

    def test_cancel_continuation_clears_banner_and_resets_timer(self) -> None:
        item = self.window._current_displayed_items[0]
        self.window.resume_item(item)
        self.assertFalse(self.window.continuation_banner.isHidden())

        # Limpiar modo continuación
        self.window.home_view.clear_continuation_mode()
        self.assertTrue(self.window.continuation_banner.isHidden())

    def test_row_column_10_has_resume_in_timer_button(self) -> None:
        """Verifica que la columna 10 contiene el botón de continuar en cronómetro (reemplazando reset)."""
        widget = self.window.table.cellWidget(0, 10)
        self.assertIsNotNone(widget)
        self.assertEqual(widget.toolTip(), "Continuar en cronómetro")

    def test_item_dialog_has_load_in_timer_button_when_editing(self) -> None:
        """Verifica que al abrir ItemDialog para editar, existe el botón 'Cargar en cronómetro'."""
        from presentation.presentation_dialogs import ItemDialog

        item = self.window._current_displayed_items[0]
        dlg = ItemDialog(self.window, item)
        self.assertTrue(hasattr(dlg, "load_timer_btn"))
        self.assertEqual(dlg.load_timer_btn.text(), " Cargar en cronómetro")

        # Al llamar _on_load_in_timer debe solicitar carga
        dlg._on_load_in_timer()
        self.assertTrue(dlg.load_in_timer_requested)

    def test_home_view_finish_item_directly_overwrites_in_continuation(self) -> None:
        """Verifica que finish_item sobrescribe directamente sin mostrar diálogo de Guardar como nuevo."""
        item = self.window._current_displayed_items[0]
        initial_count = len(self.window.application.record.items)
        self.window.resume_item(item)

        self.assertTrue(self.window.application.is_editing)
        self.window.application.timer.exercise_time_ms += 10000

        # Terminar intento
        self.window.home_view.finish_item(completed=True)

        self.assertFalse(self.window.application.is_editing)
        self.assertEqual(len(self.window.application.record.items), initial_count)


if __name__ == "__main__":
    unittest.main()

