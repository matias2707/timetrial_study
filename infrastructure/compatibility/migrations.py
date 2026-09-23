"""
================================================================================
MÓDULO TRANSITORIO DE MIGRACIONES DE ESQUEMA (FASE ALFA)
================================================================================
ADVERTENCIA DE CICLO DE VIDA:
Este módulo es estrictamente TEMPORAL y EFÍMERO. Proporciona soporte de retro-
compatibilidad y migración incremental de esquemas JSON durante el desarrollo alfa
de Study Timetrial.
Dado que se trata de una fase alfa privada y las estructuras de datos evolucionan con
frecuencia, este código no tiene vocación de permanencia: será deprecado y eliminado
en la versión 1.0 sin dejar residuos ni acoplamientos en las capas de Dominio o
Aplicación.
================================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from infrastructure.compatibility.backup_service import create_backup_file

CURRENT_SCHEMA_VERSION = 1


def upgrade_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Migra datos en formato v0 (prototipos iniciales sin schema_version) hacia el contrato v1 canónico.

    Garantiza compatibilidad con Record.from_dict().
    """
    migrated = dict(data)
    migrated["schema_version"] = 1
    migrated.setdefault("application", "Study Timetrial")
    migrated.setdefault("record_name", "StudyTimetrial_Alpha")

    # Mapeo de items: si venía de un formato previo con 'sessions' o 'study_sessions'
    raw_items = migrated.get("items")
    if not isinstance(raw_items, list):
        raw_items = migrated.get("study_sessions", migrated.get("sessions", []))
        if not isinstance(raw_items, list):
            raw_items = []

    normalized_items: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized_item = dict(item)
            # Asegurar campos requeridos por TimerItem
            normalized_item.setdefault("section_type", "Guía")
            normalized_item.setdefault("section_number", 1)
            normalized_item.setdefault("exercise", 1)
            normalized_item.setdefault("exercise_time_ms", 0)
            normalized_item.setdefault("break_time_ms", 0)
            normalized_item.setdefault("completed", True)
            normalized_items.append(normalized_item)

    migrated["items"] = normalized_items

    if not isinstance(migrated.get("planner_sections"), list):
        migrated["planner_sections"] = []

    if not isinstance(migrated.get("tags"), list):
        migrated["tags"] = []

    if "planner_schedule" not in migrated:
        migrated["planner_schedule"] = None

    return migrated


def upgrade_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Migra formato v1 a v2 (escalón prototipo para futuras expansiones en alfa).

    Agrega soporte para metadatos de sincronización e indicadores extendidos.
    """
    migrated = dict(data)
    migrated["schema_version"] = 2
    if not isinstance(migrated.get("metadata"), dict):
        migrated["metadata"] = {
            "version_tag": "alpha-2",
            "engine": "StudyTimetrial",
        }
    return migrated


# Registro ordenado de migraciones secuenciales
_MIGRATION_PIPELINE: list[tuple[int, int, Callable[[dict[str, Any]], dict[str, Any]]]] = [
    (0, 1, upgrade_v0_to_v1),
    (1, 2, upgrade_v1_to_v2),
]


def migrate_raw_record_dict(
    raw_data: dict[str, Any],
    target_version: int = CURRENT_SCHEMA_VERSION,
) -> tuple[dict[str, Any], int, list[str]]:
    """Ejecuta el pipeline de migración sobre un diccionario de registro JSON.

    Retorna:
        (datos_migrados, version_final, lista_de_migraciones_aplicadas)
    """
    data = dict(raw_data)
    initial_version = int(data.get("schema_version", 0))
    current_ver = initial_version
    applied: list[str] = []

    if current_ver >= target_version:
        return data, current_ver, applied

    for from_ver, to_ver, step_fn in _MIGRATION_PIPELINE:
        if current_ver == from_ver and to_ver <= target_version:
            data = step_fn(data)
            current_ver = to_ver
            applied.append(f"v{from_ver}->v{to_ver}")

    return data, current_ver, applied


def migrate_file_if_needed(file_path: Path, target_version: int = CURRENT_SCHEMA_VERSION) -> bool:
    """Verifica si un archivo JSON de registro requiere migración y lo actualiza con respaldo previo.

    Retorna True si fue modificado/migrado, False si ya estaba actualizado o falló.
    """
    if not file_path.is_file():
        return False

    try:
        raw_text = file_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
        if not isinstance(data, dict):
            return False

        current_ver = int(data.get("schema_version", 0))
        if current_ver >= target_version:
            return False

        # Crear respaldo preventivo
        create_backup_file(file_path)

        migrated_data, final_ver, applied = migrate_raw_record_dict(data, target_version)
        if applied:
            file_path.write_text(json.dumps(migrated_data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        return False
    except Exception:
        return False
