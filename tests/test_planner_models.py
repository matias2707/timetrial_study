import unittest
from domain.models import PlannedSection, Record, TimerItem


class TestPlannerModels(unittest.TestCase):
    def test_planned_section_defaults(self):
        sec = PlannedSection(section_type="Guía", section_number=4, total_exercises=36)
        self.assertEqual(sec.section_type, "Guía")
        self.assertEqual(sec.section_number, 4)
        self.assertEqual(sec.total_exercises, 36)
        self.assertEqual(sec.get_incisos_count(1), 0)

    def test_planned_section_incisos(self):
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=10)
        sec.set_incisos_count(4, 3)
        self.assertEqual(sec.get_incisos_count(4), 3)
        self.assertEqual(sec.get_incisos_count(5), 0)

        data = sec.to_dict()
        restored = PlannedSection.from_dict(data)
        self.assertEqual(restored.section_type, "Guía")
        self.assertEqual(restored.get_incisos_count(4), 3)

    def test_record_backward_compatibility(self):
        old_data = {
            "schema_version": 1,
            "application": "Study Timetrial",
            "record_name": "TestOld",
            "items": [],
            "created_at": "2026-09-08T00:00:00",
            "updated_at": "2026-09-08T00:00:00",
        }
        rec = Record.from_dict(old_data)
        self.assertEqual(len(rec.planner_sections), 0)

    def test_record_serialization_with_planner(self):
        rec = Record(record_name="TestPlanner")
        rec.planner_sections.append(
            PlannedSection(section_type="Guía", section_number=2, title="Álgebra", total_exercises=20, exercise_configs={2: 4})
        )
        serialized = rec.to_dict()
        self.assertIn("planner_sections", serialized)
        self.assertEqual(len(serialized["planner_sections"]), 1)
        self.assertEqual(serialized["planner_sections"][0]["title"], "Álgebra")
        self.assertEqual(serialized["planner_sections"][0]["exercise_configs"], {"2": 4})

        restored = Record.from_dict(serialized)
        self.assertEqual(len(restored.planner_sections), 1)
        self.assertEqual(restored.planner_sections[0].title, "Álgebra")
        self.assertEqual(restored.planner_sections[0].get_incisos_count(2), 4)


if __name__ == "__main__":
    unittest.main()
