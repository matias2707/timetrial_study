"""Pruebas unitarias para el módulo transitorio de migraciones en fase alfa."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from infrastructure.compatibility.migrations import (
    CURRENT_SCHEMA_VERSION,
    migrate_file_if_needed,
    migrate_raw_record_dict,
    upgrade_v0_to_v1,
    upgrade_v1_to_v2,
)
from infrastructure.storage_service import StorageService


class TestCompatibilityMigrations(unittest.TestCase):
    """Verifica la migración de esquemas de datos JSON locales."""

    def test_upgrade_v0_to_v1(self) -> None:
        legacy_data = {
            "record_name": "Registro Antiguo",
            "study_sessions": [
                {
                    "section_type": "Teoría",
                    "section_number": 2,
                    "exercise": 3,
                    "exercise_time_ms": 120000,
                    "break_time_ms": 30000,
                    "completed": True,
                }
            ],
        }
        migrated = upgrade_v0_to_v1(legacy_data)
        self.assertEqual(migrated["schema_version"], 1)
        self.assertEqual(migrated["record_name"], "Registro Antiguo")
        self.assertEqual(len(migrated["items"]), 1)
        self.assertEqual(migrated["items"][0]["exercise_time_ms"], 120000)

    def test_upgrade_v1_to_v2(self) -> None:
        v1_data = {
            "schema_version": 1,
            "record_name": "Registro V1",
            "items": [],
        }
        migrated = upgrade_v1_to_v2(v1_data)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertIn("metadata", migrated)
        self.assertEqual(migrated["metadata"]["version_tag"], "alpha-2")

    def test_migrate_raw_record_dict_stepping(self) -> None:
        legacy_v0 = {"record_name": "StepTest"}
        # Migrar a v1
        migrated_v1, ver1, steps1 = migrate_raw_record_dict(legacy_v0, target_version=1)
        self.assertEqual(ver1, 1)
        self.assertEqual(steps1, ["v0->v1"])

        # Migrar a v2
        migrated_v2, ver2, steps2 = migrate_raw_record_dict(legacy_v0, target_version=2)
        self.assertEqual(ver2, 2)
        self.assertEqual(steps2, ["v0->v1", "v1->v2"])

    def test_migrate_file_if_needed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_legacy.json"
            legacy_data = {"record_name": "AlphaLegacyFile"}
            file_path.write_text(json.dumps(legacy_data), encoding="utf-8")

            # Ejecutar migración de archivo a v1
            changed = migrate_file_if_needed(file_path, target_version=1)
            self.assertTrue(changed)

            # Verificar que el archivo ahora tiene schema_version 1
            updated = json.loads(file_path.read_text(encoding="utf-8"))
            self.assertEqual(updated.get("schema_version"), 1)

            # Si se vuelve a ejecutar, no debe modificar nada
            changed_again = migrate_file_if_needed(file_path, target_version=1)
            self.assertFalse(changed_again)

    def test_storage_service_transparent_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "v0_file.json"
            legacy_data = {
                "record_name": "Transparente",
                "sessions": [
                    {
                        "section_type": "Práctica",
                        "section_number": 1,
                        "exercise": 1,
                        "exercise_time_ms": 60000,
                        "break_time_ms": 10000,
                        "completed": True,
                    }
                ],
            }
            file_path.write_text(json.dumps(legacy_data), encoding="utf-8")

            storage = StorageService()
            record = storage.read(file_path)
            self.assertEqual(record.record_name, "Transparente")
            self.assertEqual(len(record.items), 1)
            self.assertEqual(record.items[0].exercise_time_ms, 60000)


if __name__ == "__main__":
    unittest.main()
