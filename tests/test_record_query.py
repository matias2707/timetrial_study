from datetime import date
import unittest

from application.record_query import (
    COL_DATE,
    COL_EXERCISE,
    COL_INCISO,
    COL_SECTION,
    COL_TIME,
    ColumnFilterRule,
    apply_column_filters_and_sort,
    get_column_unique_values,
)
from domain.models import TimerItem


class RecordQueryExcelTests(unittest.TestCase):
    def setUp(self):
        self.items = [
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
                comment="Duda en paso 2",
                created_at="2026-09-07T11:00:00",
            ),
        ]

    def test_multisort_hierarchy_left_to_right(self):
        """Si la jerarquía es [Sección asc, Ejercicio asc, Inciso asc], ordena Guía 1 Ej 1, Guía 1 Ej 2 Inc 1, etc."""
        active_sorts = [(COL_SECTION, "asc"), (COL_EXERCISE, "asc"), (COL_INCISO, "asc")]
        result = apply_column_filters_and_sort(self.items, {}, active_sorts)

        self.assertEqual(result[0].section_number, 1)
        self.assertEqual(result[0].exercise, 1)
        self.assertIsNone(result[0].inciso)

        self.assertEqual(result[1].section_number, 1)
        self.assertEqual(result[1].exercise, 2)
        self.assertEqual(result[1].inciso, 1)

        self.assertEqual(result[2].section_number, 1)
        self.assertEqual(result[2].exercise, 2)
        self.assertEqual(result[2].inciso, 2)

        self.assertEqual(result[3].section_number, 2)

    def test_multisort_reordered_hierarchy(self):
        """Si se arrastra Ejercicio a la izquierda de Sección: [Ejercicio asc, Sección asc]."""
        active_sorts = [(COL_EXERCISE, "asc"), (COL_SECTION, "asc")]
        result = apply_column_filters_and_sort(self.items, {}, active_sorts)

        # Ejercicios 1 primero: Guía 1 Ej 1, Guía 2 Ej 1
        self.assertEqual(result[0].exercise, 1)
        self.assertEqual(result[0].section_number, 1)

        self.assertEqual(result[1].exercise, 1)
        self.assertEqual(result[1].section_number, 2)

        # Luego ejercicios 2:
        self.assertEqual(result[2].exercise, 2)
        self.assertEqual(result[3].exercise, 2)

    def test_filter_checkboxes(self):
        """Filtro por valores seleccionados (tipo Excel checkboxes)."""
        filters = {
            COL_SECTION: ColumnFilterRule(selected_values={"Guía 1"}),
        }
        result = apply_column_filters_and_sort(self.items, filters, [])
        self.assertEqual(len(result), 3)
        for it in result:
            self.assertEqual(it.section_number, 1)

    def test_filter_condition(self):
        filters = {
            COL_TIME: ColumnFilterRule(condition_type="GT", condition_value=50000),
        }
        result = apply_column_filters_and_sort(self.items, filters, [])
        self.assertEqual(len(result), 3)
        for it in result:
            self.assertGreater(it.exercise_time_ms, 50000)

    def test_unique_values_extraction(self):
        unique_secs = get_column_unique_values(self.items, COL_SECTION)
        # Debe haber 'Guía 1' con 3 ocurrencias y 'Guía 2' con 1 ocurrencia
        self.assertEqual(unique_secs, [("Guía 1", 3), ("Guía 2", 1)])

    def test_default_sort_orders_most_recent_first(self):
        """Por defecto (sin ordenamientos activos), los registros más recientes aparecen arriba."""
        result = apply_column_filters_and_sort(self.items, {}, [])
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].created_at, "2026-09-07T12:00:00")
        self.assertEqual(result[1].created_at, "2026-09-07T11:00:00")
        self.assertEqual(result[2].created_at, "2026-09-07T10:00:00")
        self.assertEqual(result[3].created_at, "2026-09-06T09:00:00")

    def test_explicit_date_sort_ascending(self):
        """Orden explícito de fecha ascendente muestra los registros más antiguos arriba."""
        result = apply_column_filters_and_sort(self.items, {}, [(COL_DATE, "asc")])
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].created_at, "2026-09-06T09:00:00")
        self.assertEqual(result[3].created_at, "2026-09-07T12:00:00")


if __name__ == "__main__":
    unittest.main()
