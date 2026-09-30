"""Pruebas unitarias para el modelo de dominio del Organizador."""

from __future__ import annotations

import unittest
from domain.models import Milestone, OrganizedSection, OrganizerSchedule, Record, TimerItem


class TestOrganizerModels(unittest.TestCase):
    def test_organized_section_defaults(self):
        sec = OrganizedSection(section_type="Guía", section_number=4, total_exercises=36)
        self.assertEqual(sec.section_type, "Guía")
        self.assertEqual(sec.section_number, 4)
        self.assertEqual(sec.total_exercises, 36)
        self.assertEqual(sec.get_incisos_count(1), 0)

    def test_organized_section_incisos(self):
        sec = OrganizedSection(section_type="Guía", section_number=1, total_exercises=10)
        sec.set_incisos_count(4, 3)
        self.assertEqual(sec.get_incisos_count(4), 3)
        self.assertEqual(sec.get_incisos_count(5), 0)

        data = sec.to_dict()
        restored = OrganizedSection.from_dict(data)
        self.assertEqual(restored.section_type, "Guía")
        self.assertEqual(restored.get_incisos_count(4), 3)

    def test_record_backward_compatibility_old_json(self):
        old_data = {
            "schema_version": 1,
            "application": "Study Timetrial",
            "record_name": "TestOld",
            "items": [],
            "created_at": "2026-09-08T00:00:00",
            "updated_at": "2026-09-08T00:00:00",
        }
        rec = Record.from_dict(old_data)
        self.assertEqual(len(rec.organizer_sections), 0)
        self.assertEqual(len(rec.planner_sections), 0)

    def test_record_serialization_with_organizer_dual_keys(self):
        rec = Record(record_name="TestOrganizer")
        rec.organizer_sections.append(
            OrganizedSection(
                section_type="Guía",
                section_number=2,
                title="Álgebra",
                total_exercises=20,
                exercise_configs={2: 4},
            )
        )
        serialized = rec.to_dict()
        # Dual persistence: both keys must exist
        self.assertIn("organizer_sections", serialized)
        self.assertIn("planner_sections", serialized)
        self.assertEqual(len(serialized["organizer_sections"]), 1)
        self.assertEqual(len(serialized["planner_sections"]), 1)
        self.assertEqual(serialized["organizer_sections"][0]["title"], "Álgebra")
        self.assertEqual(serialized["organizer_sections"][0]["exercise_configs"], {"2": 4})

        # Deserializing loads correctly into organizer_sections
        restored = Record.from_dict(serialized)
        self.assertEqual(len(restored.organizer_sections), 1)
        self.assertEqual(restored.organizer_sections[0].title, "Álgebra")
        self.assertEqual(restored.organizer_sections[0].get_incisos_count(2), 4)
        # Property planner_sections mirrors organizer_sections
        self.assertEqual(len(restored.planner_sections), 1)

    def test_record_load_from_legacy_planner_only(self):
        legacy_data = {
            "schema_version": 1,
            "application": "Study Timetrial",
            "record_name": "Legacy",
            "items": [],
            "planner_sections": [
                {
                    "section_type": "TP",
                    "section_number": 3,
                    "title": "Física",
                    "total_exercises": 15,
                    "exercise_configs": {"1": 2},
                }
            ],
            "created_at": "2026-09-08T00:00:00",
            "updated_at": "2026-09-08T00:00:00",
        }
        rec = Record.from_dict(legacy_data)
        self.assertEqual(len(rec.organizer_sections), 1)
        self.assertEqual(rec.organizer_sections[0].title, "Física")
        self.assertEqual(rec.organizer_sections[0].get_incisos_count(1), 2)

    def test_milestone_and_organizer_schedule_serialization(self):
        m1 = Milestone(name="Primer Parcial", date="2026-10-15", type="parcial")
        m2 = Milestone(name="Entrega TP", date="2026-11-01", type="entrega")
        sched = OrganizerSchedule(
            start_date="2026-08-10",
            end_date="2026-12-15",
            period_type="cuatrimestre",
            milestones=[m1, m2],
        )

        d = sched.to_dict()
        self.assertEqual(d["start_date"], "2026-08-10")
        self.assertEqual(len(d["milestones"]), 2)

        restored = OrganizerSchedule.from_dict(d)
        self.assertEqual(restored.end_date, "2026-12-15")
        self.assertEqual(len(restored.milestones), 2)
        self.assertEqual(restored.milestones[0].name, "Primer Parcial")

        rec = Record(record_name="WithSchedule")
        rec.organizer_schedule = sched
        serialized = rec.to_dict()
        self.assertIn("organizer_schedule", serialized)
        self.assertIn("planner_schedule", serialized)
        self.assertEqual(serialized["organizer_schedule"]["start_date"], "2026-08-10")

        restored_rec = Record.from_dict(serialized)
        self.assertIsNotNone(restored_rec.organizer_schedule)
        self.assertEqual(restored_rec.organizer_schedule.start_date, "2026-08-10")
        self.assertIsNotNone(restored_rec.planner_schedule)


if __name__ == "__main__":
    unittest.main()
