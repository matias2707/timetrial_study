"""Lógica de ordenamiento y filtrado de registros de estudio estilo Excel.

Este módulo provee funciones puras y estructuras de datos para ordenar por jerarquía
de columnas arrastrables y filtrar por valores únicos (checkboxes) y condiciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Sequence

from domain.models import TimerItem
from presentation.presentation_formatters import format_milliseconds

# Claves de columnas de datos
COL_SECTION = "section"
COL_EXERCISE = "exercise"
COL_INCISO = "inciso"
COL_DATE = "created_at"
COL_BREAK = "break_time_ms"
COL_TIME = "exercise_time_ms"
COL_STATUS = "completed"
COL_COMMENT = "comment"

DATA_COLUMNS = [
    COL_SECTION,
    COL_EXERCISE,
    COL_INCISO,
    COL_DATE,
    COL_BREAK,
    COL_TIME,
    COL_STATUS,
    COL_COMMENT,
]

COLUMN_TITLES = {
    COL_SECTION: "Sección",
    COL_EXERCISE: "Ejercicio",
    COL_INCISO: "Inciso",
    COL_DATE: "Fecha",
    COL_BREAK: "Receso",
    COL_TIME: "Tiempo",
    COL_STATUS: "Estado",
    COL_COMMENT: "Comentario",
}


def parse_item_datetime(item: TimerItem) -> datetime:
    """Parsea la fecha de creación del item de manera segura."""
    try:
        return datetime.fromisoformat(item.created_at)
    except (ValueError, TypeError):
        return datetime.min


def format_item_datetime(created_at: str) -> str:
    """Formatea la fecha para visualización en tabla y filtro."""
    try:
        dt = datetime.fromisoformat(created_at)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return created_at[:16] if len(created_at) >= 16 else created_at


def get_column_display_value(item: TimerItem, column_key: str) -> str:
    """Devuelve el texto formateado que representa el valor de la celda."""
    if column_key == COL_SECTION:
        return f"{item.section_type} {item.section_number}".strip()
    elif column_key == COL_EXERCISE:
        return str(item.exercise)
    elif column_key == COL_INCISO:
        return str(item.inciso) if item.inciso is not None else "(Sin inciso)"
    elif column_key == COL_DATE:
        return format_item_datetime(item.created_at)
    elif column_key == COL_BREAK:
        return format_milliseconds(item.break_time_ms)
    elif column_key == COL_TIME:
        return format_milliseconds(item.exercise_time_ms)
    elif column_key == COL_STATUS:
        return "✓ Completado" if item.completed else "✕ Incompleto"
    elif column_key == COL_COMMENT:
        return item.comment.strip() if item.comment.strip() else "(Vacío)"
    return ""


def get_column_sort_key_value(item: TimerItem, column_key: str) -> Any:
    """Devuelve el valor crudo comparable para ordenar."""
    if column_key == COL_SECTION:
        return (item.section_type.strip().lower(), item.section_number)
    elif column_key == COL_EXERCISE:
        return item.exercise
    elif column_key == COL_INCISO:
        return -1 if item.inciso is None else item.inciso
    elif column_key == COL_DATE:
        return parse_item_datetime(item)
    elif column_key == COL_BREAK:
        return item.break_time_ms
    elif column_key == COL_TIME:
        return item.exercise_time_ms
    elif column_key == COL_STATUS:
        return 1 if item.completed else 0
    elif column_key == COL_COMMENT:
        return item.comment.strip().lower()
    return 0


@dataclass
class ColumnFilterRule:
    """Reglas de filtrado para una columna."""

    selected_values: set[str] | None = None  # None = todos seleccionados
    condition_type: str | None = None  # ej. 'CONTAINS', 'EQUALS', 'GT', 'LT', 'TODAY', etc.
    condition_value: Any | None = None

    def is_active(self, all_possible_values: set[str] | None = None) -> bool:
        """Determina si hay un filtro restrictivo activo en esta columna."""
        if self.condition_type:
            return True
        if self.selected_values is not None:
            if all_possible_values is not None:
                return self.selected_values != all_possible_values
            return True
        return False


def get_column_unique_values(items: Sequence[TimerItem], column_key: str) -> list[tuple[str, int]]:
    """Devuelve lista ordenada de tuplas (valor_formateado, conteo_ocurrencias)."""
    counts: dict[str, int] = {}
    for item in items:
        val = get_column_display_value(item, column_key)
        counts[val] = counts.get(val, 0) + 1

    # Ordenamiento natural
    def sort_key(entry: tuple[str, int]):
        val = entry[0]
        if column_key == COL_EXERCISE:
            try:
                return (0, int(val))
            except ValueError:
                return (1, val)
        if column_key == COL_INCISO:
            if val == "(Sin inciso)":
                return (-1, 0)
            try:
                return (0, int(val))
            except ValueError:
                return (1, val)
        if column_key == COL_SECTION:
            parts = val.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                return (" ".join(parts[:-1]).lower(), int(parts[-1]))
        return (val.lower(), 0)

    sorted_list = sorted(counts.items(), key=sort_key)
    return sorted_list


def matches_column_filter(
    item: TimerItem,
    column_key: str,
    rule: ColumnFilterRule,
    all_possible_values: set[str] | None = None,
    reference_date: date | None = None,
) -> bool:
    """Evalúa si un ítem cumple la regla de filtrado de una columna."""
    disp_val = get_column_display_value(item, column_key)

    # 1. Filtro por valores seleccionados (Checkboxes de Excel)
    if rule.selected_values is not None:
        if disp_val not in rule.selected_values:
            return False

    # 2. Filtro por condición
    cond = rule.condition_type
    cond_val = rule.condition_value

    if cond == "CONTAINS" and cond_val:
        if str(cond_val).lower() not in disp_val.lower():
            return False
    elif cond == "NOT_CONTAINS" and cond_val:
        if str(cond_val).lower() in disp_val.lower():
            return False
    elif cond == "EQUALS" and cond_val:
        if disp_val.lower() != str(cond_val).lower():
            return False
    elif cond == "GT" and cond_val is not None:
        raw_val = get_column_sort_key_value(item, column_key)
        if not (isinstance(raw_val, (int, float)) and raw_val > cond_val):
            return False
    elif cond == "LT" and cond_val is not None:
        raw_val = get_column_sort_key_value(item, column_key)
        if not (isinstance(raw_val, (int, float)) and raw_val < cond_val):
            return False
    elif cond == "DATE_TODAY":
        ref = reference_date or date.today()
        if parse_item_datetime(item).date() != ref:
            return False
    elif cond == "DATE_LAST_7_DAYS":
        ref = reference_date or date.today()
        start = ref - timedelta(days=6)
        if not (start <= parse_item_datetime(item).date() <= ref):
            return False
    elif cond == "DATE_THIS_MONTH":
        ref = reference_date or date.today()
        item_date = parse_item_datetime(item).date()
        if item_date.year != ref.year or item_date.month != ref.month:
            return False

    return True


def apply_column_filters_and_sort(
    items: Sequence[TimerItem],
    column_filters: dict[str, ColumnFilterRule],
    active_sorts_ordered: list[tuple[str, str]],  # [(column_key, "asc"|"desc")] ordenados por jerarquía (izq a der)
    global_query: str = "",
    all_column_values_map: dict[str, set[str]] | None = None,
    reference_date: date | None = None,
) -> list[TimerItem]:
    """Filtra y ordena la lista de items.

    active_sorts_ordered contiene las tuplas (columna, direccion) ordenadas
    por prioridad jerárquica: la primera columna en la lista tiene la mayor
    prioridad (la más a la izquierda).
    """
    filtered: list[TimerItem] = []

    clean_query = global_query.strip().lower()

    for item in items:
        # Búsqueda global
        if clean_query:
            match_global = (
                clean_query in f"{item.section_type} {item.section_number}".lower()
                or clean_query in str(item.exercise)
                or (item.inciso is not None and clean_query in str(item.inciso))
                or clean_query in item.comment.lower()
            )
            if not match_global:
                continue

        # Filtros por columna
        passed = True
        for col_key, rule in column_filters.items():
            all_vals = all_column_values_map.get(col_key) if all_column_values_map else None
            if not matches_column_filter(item, col_key, rule, all_possible_values=all_vals, reference_date=reference_date):
                passed = False
                break

        if passed:
            filtered.append(item)

    # Ordenamiento por defecto: registros más recientes arriba (fecha descendente)
    sorted_items = list(reversed(filtered))
    sorted_items.sort(key=parse_item_datetime, reverse=True)

    # Ordenamiento jerárquico acumulativo:
    # Usamos ordenamiento estable de Python en sentido inverso (de la regla menos prioritaria a la más prioritaria)
    # garantizando que la primera tupla en active_sorts_ordered (más a la izquierda) sea la prioridad dominante.
    for col_key, direction in reversed(active_sorts_ordered):
        is_desc = (direction.lower() == "desc")
        sorted_items.sort(key=lambda it: get_column_sort_key_value(it, col_key), reverse=is_desc)

    return sorted_items
