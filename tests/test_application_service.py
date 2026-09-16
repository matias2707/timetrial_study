"""Pruebas unitarias de aplicación e infraestructura sin levantar Qt."""

import os
import tempfile
import unittest
from pathlib import Path

from application.application_service import SessionLocation, StudyApplicationService
from domain.models import Record
from domain.timer_service import TimerMode
from infrastructure.storage_service import RecentFilesManager, StorageService


class MemoryStorage:
    def __init__(self) -> None:
        self.path = Path("memory.json")
        self.saved_records: list[Record] = []

    @property
    def is_open(self) -> bool:
        return self.path is not None

    def create_automatic(self) -> Record:
        return Record(record_name="memory")

    def save(self, record: Record, path: Path | None = None) -> None:
        if path is not None:
            self.path = path
        self.saved_records.append(record)


class ApplicationServiceTests(unittest.TestCase):
    def test_finishing_session_creates_item_and_resets_timer(self) -> None:
        storage = MemoryStorage()
        application = StudyApplicationService(storage=storage)
        application.toggle_session(SessionLocation("Parcial", 2, 7, 1))

        self.assertEqual(application.mode, TimerMode.PLAY)
        self.assertTrue(application.finish_item(completed=True))
        self.assertEqual(application.mode, TimerMode.WAITING)
        self.assertEqual(len(application.record.items), 1)
        self.assertEqual(application.record.items[0].section_type, "Parcial")
        self.assertTrue(application.record.items[0].completed)
        self.assertTrue(storage.saved_records)


    def test_comment_is_saved_with_finished_item(self) -> None:
        application = StudyApplicationService(storage=MemoryStorage())
        application.set_comment("  Revisar signo  ")
        application.toggle_session()

        self.assertTrue(application.finish_item(completed=False))
        self.assertEqual(application.record.items[0].comment, "Revisar signo")
        self.assertEqual(application.pending_comment, "")

    def test_missing_comment_is_compatible_with_legacy_item(self) -> None:
        item = Record.from_dict({
            "schema_version": 1,
            "items": [{
                "section_type": "Guía",
                "section_number": 1,
                "exercise": 1,
                "inciso": None,
                "exercise_time_ms": 0,
                "break_time_ms": 0,
                "completed": False,
            }],
        }).items[0]

        self.assertEqual(item.comment, "")

    def test_new_record_uses_default_name_and_sets_active_path(self) -> None:
        current_dir = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                application = StudyApplicationService(storage=StorageService())

                application.new_record("Mi plan de estudio")

                self.assertEqual(application.record.record_name, "Mi plan de estudio")
                self.assertEqual(application.record_path, Path.cwd() / "Mi plan de estudio.json")
                self.assertTrue(application.is_record_open)
            finally:
                os.chdir(current_dir)

    def test_new_record_avoids_overwriting_existing_file(self) -> None:
        current_dir = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                existing_path = Path(directory) / "Mi plan de estudio.json"
                existing_path.write_text("{}", encoding="utf-8")

                application = StudyApplicationService(storage=StorageService())
                application.new_record("Mi plan de estudio")

                self.assertEqual(application.record.record_name, "Mi plan de estudio_1")
                self.assertEqual(application.record_path, existing_path.with_name("Mi plan de estudio_1.json"))
                self.assertTrue(application.is_record_open)
            finally:
                os.chdir(current_dir)

    def test_recent_files_manager_keeps_most_recent_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_path = Path(directory) / "recent.json"
            manager = RecentFilesManager(storage_path)
            first = Path(directory) / "primer.json"
            second = Path(directory) / "segundo.json"
            for path in (first, second):
                path.write_text("{}", encoding="utf-8")

            manager.add(first)
            manager.add(second)
            manager.add(first)

            self.assertEqual(manager.paths[0], first)
            self.assertEqual(manager.paths[1], second)
            self.assertEqual(len(manager.paths), 2)

    def test_import_items_keeps_current_file_and_imports_only_selected_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            source_path = directory_path / "source.json"
            current_path = directory_path / "current.json"
            source = Record.from_dict({
                "schema_version": 1,
                "items": [
                    {
                        "section_type": "Guía",
                        "section_number": 1,
                        "exercise": 1,
                        "inciso": None,
                        "exercise_time_ms": 1000,
                        "break_time_ms": 0,
                        "completed": True,
                    },
                    {
                        "section_type": "Guía",
                        "section_number": 1,
                        "exercise": 2,
                        "inciso": None,
                        "exercise_time_ms": 2000,
                        "break_time_ms": 0,
                        "completed": False,
                    },
                ],
            })
            storage = StorageService()
            storage.save(source, source_path)
            current = StudyApplicationService(storage=StorageService())
            current.save_as(current_path)

            imported_count = current.import_items(source_path, [1])

            self.assertEqual(imported_count, 1)
            self.assertEqual(current.record.items[0].exercise, 2)
            self.assertEqual(current.record.items[0].exercise_time_ms, 2000)
            self.assertNotEqual(current.record.items[0].id, source.items[1].id)
            self.assertEqual(current.record_path, current_path)

    def test_get_today_study_time_ms_with_and_without_active_session(self) -> None:
        from datetime import date
        from domain.models import TimerItem

        application = StudyApplicationService(storage=MemoryStorage())
        today = date.today().isoformat()
        application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=50_000,
                break_time_ms=5_000,
                completed=True,
                created_at=f"{today}T10:00:00",
            )
        )
        self.assertEqual(application.get_today_study_time_ms(include_current=False), 50_000)
        self.assertEqual(application.get_today_study_time_ms(include_current=True), 50_000)

    def test_ordered_items_returns_most_recent_first(self) -> None:
        from domain.models import TimerItem

        application = StudyApplicationService(storage=MemoryStorage())
        application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=1000,
                break_time_ms=0,
                completed=True,
                created_at="2026-09-01T10:00:00",
            )
        )
        application.record.items.append(
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=None,
                exercise_time_ms=2000,
                break_time_ms=0,
                completed=True,
                created_at="2026-09-05T10:00:00",
            )
        )
        ordered = application.ordered_items()
        self.assertEqual(ordered[0].exercise, 2)
        self.assertEqual(ordered[1].exercise, 1)

    def test_load_item_into_session_and_overwrite(self) -> None:
        from domain.models import TimerItem

        storage = MemoryStorage()
        application = StudyApplicationService(storage=storage)
        original_item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=3,
            inciso=1,
            exercise_time_ms=60000,
            break_time_ms=5000,
            completed=False,
            comment="Original",
        )
        application.record.items.append(original_item)

        # Cargar el item en sesión
        application.load_item_into_session(original_item)
        self.assertTrue(application.is_editing)
        self.assertEqual(application.editing_item_id, original_item.id)
        self.assertEqual(application.location.exercise, 3)
        self.assertEqual(application.location.inciso, 1)
        self.assertEqual(application.pending_comment, "Original")
        self.assertEqual(application.timer.exercise_time_ms, 60000)
        self.assertEqual(application.timer.break_time_ms, 5000)

        # Modificar comentario y simular tiempo acumulado extra
        application.set_comment("Actualizado con éxito")
        application.timer.exercise_time_ms = 75000
        application.timer.break_time_ms = 8000

        # Finalizar con sobrescritura (overwrite=True por defecto)
        result = application.finish_item(completed=True, overwrite=True)
        self.assertTrue(result)
        self.assertFalse(application.is_editing)
        self.assertIsNone(application.editing_item_id)
        self.assertEqual(len(application.record.items), 1)

        saved = application.record.items[0]
        self.assertEqual(saved.id, original_item.id)
        self.assertEqual(saved.exercise_time_ms, 75000)
        self.assertEqual(saved.break_time_ms, 8000)
        self.assertTrue(saved.completed)
        self.assertEqual(saved.comment, "Actualizado con éxito")

    def test_load_item_into_session_and_save_as_new(self) -> None:
        from domain.models import TimerItem

        storage = MemoryStorage()
        application = StudyApplicationService(storage=storage)
        original_item = TimerItem(
            section_type="Guía",
            section_number=2,
            exercise=5,
            inciso=None,
            exercise_time_ms=30000,
            break_time_ms=2000,
            completed=False,
            comment="Intento 1",
        )
        application.record.items.append(original_item)

        application.load_item_into_session(original_item)
        application.set_comment("Intento 2 bifurcado")
        application.timer.exercise_time_ms = 45000

        # Finalizar bifurcando / guardando como nuevo (overwrite=False)
        result = application.finish_item(completed=True, overwrite=False)
        self.assertTrue(result)
        self.assertFalse(application.is_editing)
        self.assertEqual(len(application.record.items), 2)

        # El original no se tocó
        self.assertEqual(application.record.items[0].id, original_item.id)
        self.assertEqual(application.record.items[0].exercise_time_ms, 30000)
        self.assertEqual(application.record.items[0].comment, "Intento 1")

        # El nuevo item tiene id diferente y nuevos valores
        new_item = application.record.items[1]
        self.assertNotEqual(new_item.id, original_item.id)
        self.assertEqual(new_item.exercise_time_ms, 45000)
        self.assertEqual(new_item.comment, "Intento 2 bifurcado")
        self.assertTrue(new_item.completed)

    def test_cancel_editing_session_resets_cleanly(self) -> None:
        from domain.models import TimerItem

        application = StudyApplicationService(storage=MemoryStorage())
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=50000,
            break_time_ms=5000,
            completed=True,
            comment="Nota",
        )
        application.load_item_into_session(item)
        self.assertTrue(application.is_editing)

        application.cancel_editing_session()
        self.assertFalse(application.is_editing)
        self.assertIsNone(application.editing_item_id)
        self.assertEqual(application.timer.exercise_time_ms, 0)
        self.assertEqual(application.timer.break_time_ms, 0)
        self.assertEqual(application.pending_comment, "")

    def test_get_today_study_time_ms_during_continuation_does_not_double_count(self) -> None:
        from datetime import date
        from domain.models import TimerItem

        storage = MemoryStorage()
        application = StudyApplicationService(storage=storage)
        today_iso = f"{date.today().isoformat()}T10:00:00"
        item = TimerItem(
            section_type="Guía",
            section_number=1,
            exercise=1,
            inciso=None,
            exercise_time_ms=60000,
            break_time_ms=5000,
            completed=True,
            created_at=today_iso,
        )
        application.record.items.append(item)

        # Sin correr cronómetro, hoy tiene 60_000
        self.assertEqual(application.get_today_study_time_ms(), 60000)

        # Cargar en cronómetro
        application.load_item_into_session(item)
        self.assertEqual(application.get_today_study_time_ms(), 60000)

        # Iniciar sesión y correr 10 segundos adicionales (70_000 total acumulado)
        application.toggle_session()  # pasa a PLAY
        application.timer.exercise_time_ms = 70000

        # Debe reportar 70_000, NO 130_000 (evitando doble conteo del tiempo original)
        self.assertEqual(application.get_today_study_time_ms(include_current=True), 70000)


if __name__ == "__main__":
    unittest.main()