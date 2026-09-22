"""Tests para el subsistema de retrocompatibilidad, migraciones y backups."""

import os
import shutil
import tempfile
import unittest

from domain.models import PlannedSection, Record, TimerItem
from infrastructure.compatibility.backup_service import (
    create_backup_file,
    list_backups_for_file,
    restore_backup_file,
)
from infrastructure.compatibility.markdown_migrator import (
    convert_plain_text_to_markdown,
    migrate_record_notes_to_markdown,
)


class TestCompatibilityAndMigration(unittest.TestCase):
    """Pruebas unitarias para migración inyectiva a Markdown y backups de compatibilidad."""

    def test_injective_markdown_conversion(self) -> None:
        # Texto vacío
        self.assertEqual(convert_plain_text_to_markdown(""), "")
        self.assertEqual(convert_plain_text_to_markdown("   "), "")

        # Texto que ya tiene markdown
        md_text = "### Título\n**Importante**\n- Item 1\n- Item 2"
        self.assertEqual(convert_plain_text_to_markdown(md_text), md_text)

        # Viñetas informales (•) convertidas a viñeta Markdown (-)
        bullets_raw = "• Primer punto\n• Segundo punto\n- Tercer punto"
        converted = convert_plain_text_to_markdown(bullets_raw)
        self.assertIn("- Primer punto", converted)
        self.assertIn("- Segundo punto", converted)
        self.assertIn("- Tercer punto", converted)

        # Párrafos en texto plano
        plain_paragraphs = "Primer párrafo con notas.\n\nSegundo párrafo con fórmula."
        converted_para = convert_plain_text_to_markdown(plain_paragraphs)
        self.assertEqual(converted_para, plain_paragraphs)

        # Función inyectiva: convertir dos veces da exactamente el mismo resultado (idempotente)
        first_pass = convert_plain_text_to_markdown("Nota simple de estudio")
        second_pass = convert_plain_text_to_markdown(first_pass)
        self.assertEqual(first_pass, second_pass)

    def test_migrate_record_notes_to_markdown(self) -> None:
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            exercise_notes={
                "1": "• Nota en formato viñeta vieja",
                "2": "Nota plana simple",
            },
        )
        record = Record(
            record_name="Test Record",
            items=[
                TimerItem(
                    section_type="Guía",
                    section_number=1,
                    exercise=1,
                    inciso=None,
                    exercise_time_ms=1000,
                    break_time_ms=0,
                    completed=True,
                    comment="• Comentario de timer con viñeta",
                )
            ],
            planner_sections=[sec],
        )

        migrated = migrate_record_notes_to_markdown(record)
        self.assertTrue(migrated)

        # Verificar notas de ejercicios migradas a formato Markdown
        self.assertIn("- Nota en formato viñeta vieja", record.planner_sections[0].exercise_notes["1"])
        self.assertEqual(record.planner_sections[0].exercise_notes["2"], "Nota plana simple")

        # Verificar comentario de timer migrado
        self.assertIn("- Comentario de timer con viñeta", record.items[0].comment)

        # Migrar de nuevo no debe realizar cambios innecesarios
        second_migration = migrate_record_notes_to_markdown(record)
        self.assertFalse(second_migration)

    def test_backup_service_lifecycle(self) -> None:
        temp_dir = tempfile.mkdtemp()
        try:
            original_path = os.path.join(temp_dir, "mi_estudio.json")
            with open(original_path, "w", encoding="utf-8") as f:
                f.write('{"name": "Original Data"}')

            # Crear backup
            backup_path = create_backup_file(original_path, reason="test_migration")
            self.assertIsNotNone(backup_path)
            self.assertTrue(os.path.exists(backup_path))
            self.assertIn("_backup_", str(backup_path))

            # Listar backups
            backups = list_backups_for_file(original_path)
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0], backup_path)

            # Modificar archivo original
            with open(original_path, "w", encoding="utf-8") as f:
                f.write('{"name": "Corrupted Data"}')

            # Restaurar desde backup
            restored = restore_backup_file(backup_path, target_path=original_path)
            self.assertTrue(restored)

            with open(original_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('"Original Data"', content)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
