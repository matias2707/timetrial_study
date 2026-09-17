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

    def test_milestone_and_planner_schedule_serialization(self):
        from domain.models import Milestone, PlannerSchedule

        m1 = Milestone(name="Primer Parcial", date="2026-10-15", type="parcial")
        m2 = Milestone(name="Entrega TP", date="2026-11-01", type="entrega")
        sched = PlannerSchedule(
            start_date="2026-08-10",
            end_date="2026-12-15",
            period_type="cuatrimestre",
            milestones=[m1, m2],
        )
        rec = Record(record_name="TestSchedule", planner_schedule=sched)
        serialized = rec.to_dict()

        self.assertIn("planner_schedule", serialized)
        sched_dict = serialized["planner_schedule"]
        self.assertEqual(sched_dict["start_date"], "2026-08-10")
        self.assertEqual(len(sched_dict["milestones"]), 2)
        self.assertEqual(sched_dict["milestones"][0]["name"], "Primer Parcial")
        self.assertEqual(sched_dict["milestones"][0]["type"], "parcial")

        restored = Record.from_dict(serialized)
        self.assertIsNotNone(restored.planner_schedule)
        self.assertEqual(restored.planner_schedule.start_date, "2026-08-10")
        self.assertEqual(restored.planner_schedule.end_date, "2026-12-15")
        self.assertEqual(restored.planner_schedule.period_type, "cuatrimestre")
        self.assertEqual(len(restored.planner_schedule.milestones), 2)
        self.assertEqual(restored.planner_schedule.milestones[1].name, "Entrega TP")

    def test_milestone_custom_color_and_icon(self):
        from domain.models import Milestone

        # Milestone con color e ícono por defecto según tipo
        m_def = Milestone(name="Parcial 1", date="2026-10-15", type="Parcial")
        self.assertEqual(m_def.color, "#ef4444")
        self.assertEqual(m_def.icon, "🎯")

        # Milestone con personalizaciones explícitas del usuario
        m_custom = Milestone(
            name="Defensa Final",
            date="2026-12-20",
            type="Coloquio Especial",
            color="#8b5cf6",
            icon="⭐"
        )
        self.assertEqual(m_custom.color, "#8b5cf6")
        self.assertEqual(m_custom.icon, "⭐")
        self.assertEqual(m_custom.type, "Coloquio Especial")

        # Serialización y deserialización
        serialized = m_custom.to_dict()
        self.assertEqual(serialized["color"], "#8b5cf6")
        self.assertEqual(serialized["icon"], "⭐")
        self.assertEqual(serialized["type"], "Coloquio Especial")

        deserialized = Milestone.from_dict(serialized)
        self.assertEqual(deserialized.name, "Defensa Final")
        self.assertEqual(deserialized.color, "#8b5cf6")
        self.assertEqual(deserialized.icon, "⭐")
        self.assertEqual(deserialized.type, "Coloquio Especial")

        # Compatibilidad retroactiva: JSON antiguo sin color ni icon
        legacy_data = {"name": "TP 1", "date": "2026-09-20", "type": "entrega"}
        from_legacy = Milestone.from_dict(legacy_data)
        self.assertEqual(from_legacy.color, "#3b82f6")
        self.assertEqual(from_legacy.icon, "💻")

    def test_record_without_planner_schedule_backward_compatible(self):
        old_data = {
            "schema_version": 1,
            "application": "Study Timetrial",
            "record_name": "NoSched",
            "items": [],
            "created_at": "2026-09-08T00:00:00",
            "updated_at": "2026-09-08T00:00:00",
        }
        rec = Record.from_dict(old_data)
        self.assertIsNone(rec.planner_schedule)


if __name__ == "__main__":
    unittest.main()

