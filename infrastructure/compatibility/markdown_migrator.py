from __future__ import annotations

"""Conversión inyectiva y migración de apuntes/comentarios en texto plano hacia Markdown."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.models import Record


def convert_plain_text_to_markdown(raw_text: str) -> str:
    """Convierte texto plano a Markdown estándar de forma inyectiva (unidireccional).

    - Preserva Markdown válido existente.
    - Normaliza saltos de línea para que párrafos en texto plano no se unan accidentalmente.
    - Convierte viñetas informales al estándar `- `.
    - Garantiza estabilidad: convert(convert(x)) == convert(x).
    """
    if not raw_text:
        return ""

    cleaned = raw_text.strip()
    if not cleaned:
        return ""

    normalized = cleaned.replace("\r\n", "\n")
    lines = normalized.split("\n")
    processed_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Convertir viñetas informales (ej: "•", "o ") a viñeta Markdown "- "
        if stripped.startswith("•"):
            processed_lines.append(f"- {stripped.lstrip('•').strip()}")
        elif re.match(r"^[oO]\s+", stripped):
            processed_lines.append(f"- {stripped[2:].strip()}")
        else:
            processed_lines.append(line)

    intermediate = "\n".join(processed_lines)

    # Detección heurística de si contiene sintaxis Markdown explícita
    has_markdown_elements = bool(
        re.search(r"(^#{1,6}\s+|^\s*[-*+]\s+|^\s*\d+\.\s+|^\s*>\s+|\*\*|__|`{1,3}|~~|---|___)", intermediate, re.MULTILINE)
    )

    if has_markdown_elements:
        return intermediate

    # Si hay saltos de línea sin línea en blanco, agrupar párrafos
    result = "\n\n".join(
        "\n".join(chunk) for chunk in _group_paragraphs(processed_lines)
    )
    return result.strip()


def _group_paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(current)
    return paragraphs or [[]]


def migrate_record_notes_to_markdown(record: Record) -> bool:
    """Migra todas las notas y comentarios de un Record a Markdown en memoria.

    Devuelve True si al menos una nota o comentario fue modificado/actualizado.
    """
    modified = False

    # 1. Migrar diccionario de notas por ejercicio (en record o en planned_sections)
    if hasattr(record, "exercise_notes") and isinstance(record.exercise_notes, dict):
        for key, raw_val in list(record.exercise_notes.items()):
            if isinstance(raw_val, str):
                converted = convert_plain_text_to_markdown(raw_val)
                if converted != raw_val:
                    record.exercise_notes[key] = converted
                    modified = True

    if hasattr(record, "planner_sections") and isinstance(record.planner_sections, list):
        for sec in record.planner_sections:
            if hasattr(sec, "exercise_notes") and isinstance(sec.exercise_notes, dict):
                for key, raw_val in list(sec.exercise_notes.items()):
                    if isinstance(raw_val, str):
                        converted = convert_plain_text_to_markdown(raw_val)
                        if converted != raw_val:
                            sec.exercise_notes[key] = converted
                            modified = True

    # 2. Migrar comentarios de ítems de sesión existentes
    if hasattr(record, "items") and isinstance(record.items, list):
        for item in record.items:
            if item.comment:
                converted = convert_plain_text_to_markdown(item.comment)
                if converted != item.comment:
                    item.comment = converted
                    modified = True

    return modified
