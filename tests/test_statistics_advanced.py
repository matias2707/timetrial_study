import unittest
from datetime import date, timedelta
from PySide6.QtWidgets import QApplication

from application.application_service import StudyApplicationService
from application.statistics_service import (
    HourlyDistribution,
    TopEffortExercise,
    compute_statistics,
    get_24h_hourly_distribution,
    get_course_heatmap_data,
    get_top_effort_exercises,
)
from domain.models import Milestone, PlannedSection, PlannerSchedule, Record, TimerItem
from infrastructure.storage_service import StorageService
from presentation.course_heatmap_widget import CourseHeatmapWidget
from presentation.hourly_chart_widget import Hourly24hChartWidget
from presentation.planner_dialogs import ScheduleConfigDialog
from presentation.statistics_view import StatisticsViewWidget

# Asegurar QApplication para pruebas de widgets
app = QApplication.instance() or QApplication([])


class TestAdvancedStatisticsService(unittest.TestCase):
    def setUp(self):
        self.record = Record(record_name="AdvancedStatsTest")

    def test_top_effort_exercises_order_and_limit(self):
        # Crear items con distintos tiempos y ejercicios
        # Ejercicio 1: 10000 ms neto
        # Ejercicio 2: 30000 ms neto
        # Ejercicio 3: 5000 ms neto
        # Ejercicio 4: 50000 ms neto
        # Ejercicio 5: 20000 ms neto
        # Ejercicio 6: 25000 ms neto
        items = [
            TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, exercise_time_ms=10000, break_time_ms=5000, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=2, inciso=None, exercise_time_ms=30000, break_time_ms=2000, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=3, inciso=None, exercise_time_ms=5000, break_time_ms=1000, completed=False),
            TimerItem(section_type="Guía", section_number=1, exercise=4, inciso=None, exercise_time_ms=50000, break_time_ms=8000, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=5, inciso=None, exercise_time_ms=20000, break_time_ms=3000, completed=False),
            TimerItem(section_type="Guía", section_number=1, exercise=6, inciso=None, exercise_time_ms=25000, break_time_ms=4000, completed=True),
        ]
        self.record.items = items

        top5 = get_top_effort_exercises(self.record, limit=5)
        self.assertEqual(len(top5), 5)
        # Orden debe ser: Ej 4 (50000), Ej 2 (30000), Ej 6 (25000), Ej 5 (20000), Ej 1 (10000)
        self.assertEqual(top5[0].exercise, 4)
        self.assertEqual(top5[0].exercise_time_ms, 50000)
        self.assertEqual(top5[1].exercise, 2)
        self.assertEqual(top5[2].exercise, 6)
        self.assertEqual(top5[3].exercise, 5)
        self.assertEqual(top5[4].exercise, 1)

    def test_top_effort_with_incisos_and_multiple_attempts(self):
        # Multiple attempts on same exercise
        items = [
            TimerItem(section_type="Guía", section_number=2, exercise=10, inciso=1, exercise_time_ms=15000, break_time_ms=0, completed=False),
            TimerItem(section_type="Guía", section_number=2, exercise=10, inciso=1, exercise_time_ms=25000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=2, exercise=10, inciso=2, exercise_time_ms=5000, break_time_ms=0, completed=True),
        ]
        self.record.items = items

        top = get_top_effort_exercises(self.record, limit=5)
        self.assertEqual(len(top), 2)
        # Guia 2 Ej 10.1 tiene 40000 ms en 2 intentos
        self.assertEqual(top[0].exercise, 10)
        self.assertEqual(top[0].inciso, 1)
        self.assertEqual(top[0].exercise_time_ms, 40000)
        self.assertEqual(top[0].attempts, 2)
        self.assertEqual(top[0].status, "completed")

    def test_24h_hourly_distribution(self):
        items = [
            TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, created_at="2026-09-15T10:15:00", exercise_time_ms=1000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=2, inciso=None, created_at="2026-09-15T10:45:00", exercise_time_ms=1000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=3, inciso=None, created_at="2026-09-15T14:00:00", exercise_time_ms=1000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=4, inciso=None, created_at="2026-09-15T23:30:00", exercise_time_ms=1000, break_time_ms=0, completed=True),
        ]
        self.record.items = items

        dist = get_24h_hourly_distribution(self.record)
        self.assertEqual(dist.total_sessions, 4)
        self.assertEqual(len(dist.slots), 24)
        self.assertEqual(dist.slots[10].count, 2)
        self.assertEqual(dist.slots[10].percentage, 50.0)
        self.assertEqual(dist.slots[14].count, 1)
        self.assertEqual(dist.slots[23].count, 1)
        self.assertEqual(dist.peak_hour, 10)
        self.assertEqual(dist.peak_count, 2)

    def test_course_heatmap_data_without_schedule(self):
        heatmap = get_course_heatmap_data(self.record)
        self.assertFalse(heatmap.has_schedule)
        self.assertEqual(heatmap.total_study_days, 0)
        self.assertEqual(heatmap.current_streak, 0)

    def test_course_heatmap_data_with_schedule_and_streak(self):
        today_str = date.today().isoformat()
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        two_days_ago_str = (date.today() - timedelta(days=2)).isoformat()

        start_date = (date.today() - timedelta(days=14)).isoformat()
        end_date = (date.today() + timedelta(days=30)).isoformat()
        exam_date = (date.today() + timedelta(days=10)).isoformat()

        m = Milestone(name="1er Parcial", date=exam_date, type="parcial")
        sched = PlannerSchedule(
            start_date=start_date,
            end_date=end_date,
            period_type="cuatrimestre",
            milestones=[m],
        )
        self.record.planner_schedule = sched

        # Agregar intentos hoy, ayer y anteayer -> racha de 3 días
        self.record.items = [
            TimerItem(section_type="Guía", section_number=1, exercise=1, inciso=None, created_at=f"{two_days_ago_str}T09:00:00", exercise_time_ms=5000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=2, inciso=None, created_at=f"{yesterday_str}T10:00:00", exercise_time_ms=6000, break_time_ms=0, completed=True),
            TimerItem(section_type="Guía", section_number=1, exercise=3, inciso=None, created_at=f"{today_str}T11:00:00", exercise_time_ms=7000, break_time_ms=0, completed=True),
        ]

        heatmap = get_course_heatmap_data(self.record)
        self.assertTrue(heatmap.has_schedule)
        self.assertEqual(heatmap.current_streak, 3)
        self.assertEqual(heatmap.total_study_days, 3)
        self.assertEqual(heatmap.days_until_next_exam, 10)
        self.assertEqual(heatmap.next_exam_title, "1er Parcial")
        self.assertGreater(len(heatmap.day_cells), 0)


class TestPresentationAdvancedStatistics(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.storage = StorageService(recent_files_path=temp_path / "recent.json", default_dir=temp_path)
        self.app_service = StudyApplicationService(self.storage)
        self.app_service.new_record(record_name="TestAdvancedUI")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_statistics_view_widget_creation_and_refresh(self):
        widget = StatisticsViewWidget(self.app_service)
        widget.refresh_statistics()

        # Comprobar elementos creados
        self.assertIsNotNone(widget.course_heatmap)
        self.assertIsNotNone(widget.weekly_chart)
        self.assertIsNotNone(widget.stats_effort_table)
        self.assertIsNotNone(widget.hourly_chart)

        # Alternar vistas en Hero
        widget._show_weekly_view()
        self.assertEqual(widget.hero_stack.currentIndex(), 1)
        self.assertTrue(widget.btn_view_weekly.isChecked())
        self.assertFalse(widget.btn_view_heatmap.isChecked())

        widget._show_heatmap_view()
        self.assertEqual(widget.hero_stack.currentIndex(), 0)
        self.assertTrue(widget.btn_view_heatmap.isChecked())

    def test_statistics_view_signals(self):
        widget = StatisticsViewWidget(self.app_service)
        received_schedule = []
        widget.request_configure_schedule.connect(lambda: received_schedule.append(True))
        widget.request_configure_schedule.emit()
        self.assertEqual(received_schedule, [True])

        received_timer = []
        widget.request_load_timer.connect(lambda st, sn, ex, inc: received_timer.append((st, sn, ex, inc)))
        widget.request_load_timer.emit("Guía", 2, 5, None)
        self.assertEqual(received_timer, [("Guía", 2, 5, None)])

    def test_schedule_config_dialog(self):
        sched = PlannerSchedule(
            start_date="2026-08-10",
            end_date="2026-12-15",
            period_type="Cuatrimestral",
            milestones=[
                Milestone(name="Parcial 1", date="2026-09-30", type="parcial", color="#ef4444", icon="🎯")
            ],
        )
        dlg = ScheduleConfigDialog(schedule=sched)
        self.assertEqual(dlg.combo_period.currentText(), "Cuatrimestral")
        self.assertEqual(dlg.table_milestones.rowCount(), 1)
        self.assertEqual(dlg.table_milestones.columnCount(), 5)
        self.assertEqual(dlg.table_milestones.item(0, 0).text(), "Parcial 1")

        # Verificar widgets de ícono, color y tipo
        combo_icon = dlg.table_milestones.cellWidget(0, 2)
        self.assertIsNotNone(combo_icon)
        self.assertEqual(combo_icon.currentData(), "🎯")

        btn_color = dlg.table_milestones.cellWidget(0, 3)
        self.assertIsNotNone(btn_color)
        self.assertEqual(btn_color.property("color_hex"), "#ef4444")

        combo_type = dlg.table_milestones.cellWidget(0, 4)
        self.assertIsNotNone(combo_type)
        self.assertEqual(combo_type.currentText(), "Parcial")

        # Probar agregar nuevo hito
        dlg._on_add_milestone()
        self.assertEqual(dlg.table_milestones.rowCount(), 2)

        # Personalizar el nuevo hito
        dlg.table_milestones.item(1, 0).setText("Entrega Proyecto Final")
        btn_color_2 = dlg.table_milestones.cellWidget(1, 3)
        btn_color_2.setProperty("color_hex", "#8b5cf6")
        combo_icon_2 = dlg.table_milestones.cellWidget(1, 2)
        combo_icon_2.setCurrentIndex(combo_icon_2.findData("💻"))
        combo_type_2 = dlg.table_milestones.cellWidget(1, 4)
        combo_type_2.setEditText("Proyecto Especial")

        # Probar recolección de datos
        dlg._on_save()
        result_sched = dlg.schedule
        self.assertIsNotNone(result_sched)
        self.assertEqual(result_sched.period_type, "Cuatrimestral")
        self.assertEqual(len(result_sched.milestones), 2)
        m2 = result_sched.milestones[1]
        self.assertEqual(m2.name, "Entrega Proyecto Final")
        self.assertEqual(m2.color, "#8b5cf6")
        self.assertEqual(m2.icon, "💻")
        self.assertEqual(m2.type, "Proyecto Especial")

    def test_course_heatmap_canvas_geometry_and_weekdays(self):
        from presentation.course_heatmap_widget import CourseHeatmapCanvas, DAY_LETTERS, DAY_NAMES

        self.assertEqual(len(DAY_LETTERS), 7)
        self.assertEqual(DAY_LETTERS[5], "S")
        self.assertEqual(DAY_LETTERS[6], "D")
        self.assertEqual(len(DAY_NAMES), 7)
        self.assertEqual(DAY_NAMES[5], "Sábado")
        self.assertEqual(DAY_NAMES[6], "Domingo")

        canvas = CourseHeatmapCanvas()
        req_h = canvas.get_required_height()
        # Verificar que la altura requerida sea suficiente para los 7 días (~220-236px)
        self.assertGreaterEqual(req_h, 200)

        # Verificar cálculo de geometría para 16 semanas típicas
        left_m, top_m, bottom_m, cell_sz, sp = canvas._calc_geometry()
        # La coordenada inferior del día domingo (índice 6) debe caber dentro de req_h
        domingo_bottom_y = top_m + 6 * (cell_sz + sp) + cell_sz
        self.assertLessEqual(domingo_bottom_y + bottom_m, req_h)
        sabado_bottom_y = top_m + 5 * (cell_sz + sp) + cell_sz
        self.assertLess(sabado_bottom_y, domingo_bottom_y)


if __name__ == "__main__":
    unittest.main()
