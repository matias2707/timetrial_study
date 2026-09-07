import unittest
from pathlib import Path

from application_service import SessionLocation, StudyApplicationService
from models import Record
from timer_service import TimerMode


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

    def test_navigation_from_an_exercise_without_active_session(self) -> None:
        application = StudyApplicationService(storage=MemoryStorage())

        self.assertTrue(application.navigate("next_exercise"))
        self.assertEqual(application.location.exercise, 2)
        self.assertIsNone(application.location.inciso)

        self.assertTrue(application.navigate("previous_exercise"))
        self.assertEqual(application.location.exercise, 1)
        self.assertFalse(application.navigate("previous_exercise"))

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


if __name__ == "__main__":
    unittest.main()