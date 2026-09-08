import unittest
from domain.models import PlannedSection, Record, TimerItem
from application.statistics_service import compute_statistics


class TestStatisticsWithPlanner(unittest.TestCase):
    def test_statistics_with_planner_empty_items(self):
        rec = Record(record_name="StatsPlanner")
        rec.planner_sections.append(
            PlannedSection(section_type="Guía", section_number=1, total_exercises=10)
        )
        stats = compute_statistics(rec)
        self.assertTrue(stats.has_planner)
        self.assertEqual(stats.planned_total_units, 10)
        self.assertEqual(stats.planned_completed_units, 0)
        self.assertEqual(stats.planned_completion_percentage, 0.0)
        self.assertEqual(len(stats.section_summaries), 1)
        self.assertEqual(stats.section_summaries[0].section_key, "Guía 1")
        self.assertEqual(stats.section_summaries[0].planned_total, 10)
        self.assertEqual(stats.section_summaries[0].planned_completed, 0)

    def test_statistics_with_planner_and_items(self):
        rec = Record(record_name="StatsPlanner2")
        rec.planner_sections.append(
            PlannedSection(
                section_type="Guía",
                section_number=2,
                total_exercises=4,
                exercise_configs={2: 2},  # Ej 2 tiene 2 incisos: 1, 2. Total units = 1 + 2 + 1 + 1 = 5
            )
        )
        # Completar ej 1
        rec.items.append(
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=1,
                inciso=None,
                exercise_time_ms=1000,
                break_time_ms=0,
                completed=True,
            )
        )
        # Completar ej 2.1
        rec.items.append(
            TimerItem(
                section_type="Guía",
                section_number=2,
                exercise=2,
                inciso=1,
                exercise_time_ms=1200,
                break_time_ms=0,
                completed=True,
            )
        )

        stats = compute_statistics(rec)
        self.assertTrue(stats.has_planner)
        self.assertEqual(stats.planned_total_units, 5)
        self.assertEqual(stats.planned_completed_units, 2)
        self.assertAlmostEqual(stats.planned_completion_percentage, 40.0)

        sec_sum = stats.section_summaries[0]
        self.assertEqual(sec_sum.section_key, "Guía 2")
        self.assertEqual(sec_sum.planned_total, 5)
        self.assertEqual(sec_sum.planned_completed, 2)
        self.assertAlmostEqual(sec_sum.planned_completion_pct, 40.0)


if __name__ == "__main__":
    unittest.main()
