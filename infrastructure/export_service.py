from __future__ import annotations

"""Servicio de infraestructura para exportación estandarizada en formato CSV (RFC 4180 / utf-8-sig)."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from domain.models import PlannedSection, TagDefinition, TimerItem


@dataclass(frozen=True)
class ExportResult:
    """Resultado de la operación de exportación tabular."""

    success: bool
    rows_exported: int
    file_path: Path
    error_message: str | None = None


def format_ms_to_hhmmss(ms: int) -> str:
    """Convierte milisegundos enteros a formato legible HH:MM:SS."""
    total_seconds = max(0, int(ms // 1000))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _parse_created_at(raw_iso: str) -> tuple[str, str, str]:
    """Parsea la marca temporal devolviendo (fecha, hora, iso_normalizado)."""
    clean = raw_iso.strip()
    try:
        dt = datetime.fromisoformat(clean)
        return (
            dt.strftime("%Y-%m-%d"),
            dt.strftime("%H:%M:%S"),
            dt.isoformat(timespec="seconds"),
        )
    except (ValueError, TypeError):
        # En caso de fecha personalizada o no estándar
        parts = clean.split("T") if "T" in clean else clean.split(" ")
        date_part = parts[0] if parts else clean
        time_part = parts[1][:8] if len(parts) > 1 else "00:00:00"
        return (date_part, time_part, clean)


def export_items_to_csv(
    file_path: Path | str,
    items: Sequence[TimerItem],
    delimiter: str = ";",
    tag_catalog: Sequence[TagDefinition] | None = None,
    planner_sections: Sequence[PlannedSection] | None = None,
) -> ExportResult:
    """Exporta el historial detallado de intentos a un archivo CSV codificado en UTF-8 con BOM.

    Satisface el estándar RFC 4180 y asegura apertura nativa en Microsoft Excel y Google Sheets.
    """
    target = Path(file_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=f"No se pudo crear la carpeta destino: {err}",
        )

    # Mapeo de tag_id -> nombre legible
    tag_names: dict[str, str] = {}
    if tag_catalog:
        for tag in tag_catalog:
            tag_names[tag.id] = tag.name

    # Indexar secciones por (section_type, section_number)
    sec_map: dict[tuple[str, int], PlannedSection] = {}
    if planner_sections:
        for sec in planner_sections:
            sec_map[(sec.section_type.strip().lower(), sec.section_number)] = sec

    headers = [
        "Fecha",
        "Hora",
        "Fecha y Hora ISO",
        "Guia / Seccion",
        "Numero Seccion",
        "Ejercicio",
        "Inciso",
        "Identificador",
        "Estado",
        "Tiempo Neto (hh:mm:ss)",
        "Tiempo Neto (s)",
        "Tiempo Neto (ms)",
        "Tiempo Descanso (hh:mm:ss)",
        "Tiempo Descanso (s)",
        "Tiempo Total (hh:mm:ss)",
        "Etiquetas",
        "Notas / Apuntes",
        "Comentario Intento",
    ]

    try:
        with open(target, mode="w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(
                fp,
                delimiter=delimiter,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\r\n",
            )
            writer.writerow(headers)

            for item in items:
                date_str, time_str, iso_str = _parse_created_at(item.created_at)

                sec_key = (item.section_type.strip().lower(), item.section_number)
                sec = sec_map.get(sec_key)

                # Inciso string e identificador
                inciso_val = item.inciso
                inciso_str = str(inciso_val) if (inciso_val is not None and inciso_val > 0) else ""
                if inciso_str:
                    ident = f"{item.section_type} {item.section_number} · Ej. {item.exercise}.{inciso_str}"
                else:
                    ident = f"{item.section_type} {item.section_number} · Ej. {item.exercise}"

                status_str = "Completado" if item.completed else "Incompleto"

                # Tiempos
                net_hhmmss = format_ms_to_hhmmss(item.exercise_time_ms)
                net_s = f"{item.exercise_time_ms / 1000.0:.2f}"
                break_hhmmss = format_ms_to_hhmmss(item.break_time_ms)
                break_s = f"{item.break_time_ms / 1000.0:.2f}"
                total_hhmmss = format_ms_to_hhmmss(item.exercise_time_ms + item.break_time_ms)

                # Etiquetas
                tags_str = ""
                notes_str = ""
                if sec is not None:
                    raw_tags = sec.get_exercise_tags(item.exercise, inciso_val)
                    tag_labels = [tag_names.get(tid, tid) for tid in raw_tags]
                    tags_str = " | ".join(tag_labels)
                    notes_str = sec.get_note(item.exercise, inciso_val)

                writer.writerow(
                    [
                        date_str,
                        time_str,
                        iso_str,
                        item.section_type,
                        str(item.section_number),
                        str(item.exercise),
                        inciso_str,
                        ident,
                        status_str,
                        net_hhmmss,
                        net_s,
                        str(item.exercise_time_ms),
                        break_hhmmss,
                        break_s,
                        total_hhmmss,
                        tags_str,
                        notes_str,
                        item.comment or "",
                    ]
                )

        return ExportResult(
            success=True,
            rows_exported=len(items),
            file_path=target,
        )

    except PermissionError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=(
                f"El archivo está bloqueado o abierto por otra aplicación (ej: Excel): {err}. "
                "Cierre el archivo y vuelva a intentarlo."
            ),
        )
    except OSError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=f"Error de entrada/salida al escribir el archivo: {err}",
        )


def export_summary_to_csv(
    file_path: Path | str,
    summary_rows: Sequence[dict[str, Any]],
    delimiter: str = ";",
) -> ExportResult:
    """Exporta el reporte consolidado por guía y ejercicios a un archivo CSV (RFC 4180 / utf-8-sig)."""
    target = Path(file_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=f"No se pudo crear la carpeta destino: {err}",
        )

    headers = [
        "Guia / Seccion",
        "Numero Seccion",
        "Ejercicio",
        "Inciso",
        "Identificador",
        "Estado Resolucion",
        "Total Intentos",
        "Intentos Completados",
        "Intentos Incompletos",
        "Tasa Exito (%)",
        "Tiempo Total Neto (hh:mm:ss)",
        "Tiempo Total Neto (s)",
        "Tiempo Promedio (hh:mm:ss)",
        "Mejor Marca PB (hh:mm:ss)",
        "Etiquetas",
        "Notas / Apuntes",
    ]

    try:
        with open(target, mode="w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.writer(
                fp,
                delimiter=delimiter,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\r\n",
            )
            writer.writerow(headers)

            for row in summary_rows:
                writer.writerow(
                    [
                        str(row.get("section_type", "")),
                        str(row.get("section_number", "")),
                        str(row.get("exercise", "")),
                        str(row.get("inciso", "") or ""),
                        str(row.get("identifier", "")),
                        str(row.get("resolution_status", "")),
                        str(row.get("total_attempts", 0)),
                        str(row.get("completed_attempts", 0)),
                        str(row.get("failed_attempts", 0)),
                        str(row.get("success_rate", "0.0%")),
                        str(row.get("total_time_hhmmss", "00:00:00")),
                        str(row.get("total_time_s", "0.00")),
                        str(row.get("avg_time_hhmmss", "00:00:00")),
                        str(row.get("pb_time_hhmmss", "-")),
                        str(row.get("tags", "")),
                        str(row.get("notes", "")),
                    ]
                )

        return ExportResult(
            success=True,
            rows_exported=len(summary_rows),
            file_path=target,
        )

    except PermissionError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=(
                f"El archivo está bloqueado o abierto por otra aplicación (ej: Excel): {err}. "
                "Cierre el archivo y vuelva a intentarlo."
            ),
        )
    except OSError as err:
        return ExportResult(
            success=False,
            rows_exported=0,
            file_path=target,
            error_message=f"Error al escribir el archivo de resumen: {err}",
        )
