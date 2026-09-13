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


if __name__ == "__main__":
    unittest.main()