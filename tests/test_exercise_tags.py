"""Pruebas unitarias para el sistema de marcadores y etiquetas (TASK-002)."""

from __future__ import annotations

import unittest
from domain.models import PlannedSection, Record, TagDefinition, TimerItem, default_tags
from application.planner_service import PlannerService, STATUS_COMPLETED
from application.application_service import StudyApplicationService, SessionLocation
from infrastructure.storage_service import StorageService


class TestExerciseTags(unittest.TestCase):
    """Pruebas unitarias de etiquetas a nivel de dominio, aplicación y persistencia."""

    def test_tag_definition_serialization(self) -> None:
        tag = TagDefinition(id="tag-custom", name="Consulta", color="#10b981")
        data = tag.to_dict()
        self.assertEqual(data["id"], "tag-custom")
        self.assertEqual(data["name"], "Consulta")
        self.assertEqual(data["color"], "#10b981")

        restored = TagDefinition.from_dict(data)
        self.assertEqual(restored.id, tag.id)
        self.assertEqual(restored.name, tag.name)
        self.assertEqual(restored.color, tag.color)

    def test_default_tags(self) -> None:
        defaults = default_tags()
        self.assertEqual(len(defaults), 4)
        tag_ids = [t.id for t in defaults]
        self.assertIn("tag-redo", tag_ids)
        self.assertIn("tag-doubt", tag_ids)
        self.assertIn("tag-consulted", tag_ids)
        self.assertIn("tag-key", tag_ids)

    def test_planned_section_exercise_tags(self) -> None:
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=5,
            exercise_configs={2: 3},
        )
        self.assertEqual(sec.get_exercise_tags(1), [])
        self.assertEqual(sec.get_exercise_tags(2, 1), [])

        # Asignar tags a ejercicio simple
        sec.set_exercise_tags(1, None, ["tag-redo", "tag-key", "tag-redo"])
        # Debe preservar unicidad manteniendo orden
        self.assertEqual(sec.get_exercise_tags(1), ["tag-redo", "tag-key"])

        # Asignar tags a inciso
        sec.set_exercise_tags(2, 1, ["tag-doubt"])
        self.assertEqual(sec.get_exercise_tags(2, 1), ["tag-doubt"])

        # Serialización y reconstrucción
        d = sec.to_dict()
        self.assertIn("exercise_tags", d)
        self.assertEqual(d["exercise_tags"]["1"], ["tag-redo", "tag-key"])
        self.assertEqual(d["exercise_tags"]["2.1"], ["tag-doubt"])

        sec2 = PlannedSection.from_dict(d)
        self.assertEqual(sec2.get_exercise_tags(1), ["tag-redo", "tag-key"])
        self.assertEqual(sec2.get_exercise_tags(2, 1), ["tag-doubt"])

        # Limpiar tags
        sec.set_exercise_tags(1, None, [])
        self.assertEqual(sec.get_exercise_tags(1), [])
        self.assertNotIn("1", sec.exercise_tags)

    def test_record_tags_backwards_compatibility(self) -> None:
        # JSON legado sin campo tags ni exercise_tags
        legacy_data = {
            "schema_version": 1,
            "application": "Study Timetrial",
            "record_name": "Legacy",
            "created_at": "2026-09-01T12:00:00",
            "updated_at": "2026-09-01T12:00:00",
            "items": [],
            "planner_sections": [
                {
                    "section_type": "Guía",
                    "section_number": 1,
                    "total_exercises": 10,
                }
            ],
        }
        record = Record.from_dict(legacy_data)
        self.assertEqual(len(record.tags), 4)
        self.assertEqual(record.tags[0].name, "Rehacer")
        self.assertEqual(record.planner_sections[0].exercise_tags, {})

        # Serialización incluye tags y exercise_tags
        out_data = record.to_dict()
        self.assertIn("tags", out_data)
        self.assertEqual(len(out_data["tags"]), 4)
        self.assertIn("exercise_tags", out_data["planner_sections"][0])

    def test_planner_service_compute_overview_tags(self) -> None:
        record = Record(record_name="TestTags")
        sec = PlannedSection(
            section_type="Guía",
            section_number=1,
            total_exercises=3,
            exercise_configs={2: 2},
        )
        sec.set_exercise_tags(1, None, ["tag-redo"])
        sec.set_exercise_tags(2, 2, ["tag-key", "tag-doubt"])
        record.planner_sections.append(sec)

        overview = PlannerService.compute_overview(record)
        sec_status = overview.sections[0]
        nodes = sec_status.exercise_nodes

        # Nodo 1: simple con tag-redo
        node1 = nodes[0]
        self.assertEqual(len(node1.tags), 1)
        self.assertEqual(node1.tags[0].id, "tag-redo")
        self.assertEqual(node1.tags[0].name, "Rehacer")

        # Nodo 2: compuesto
        node2 = nodes[1]
        self.assertTrue(node2.has_incisos)
        # Inciso 2.1 no tiene tags
        self.assertEqual(len(node2.incisos[0].tags), 0)
        # Inciso 2.2 tiene 2 tags
        self.assertEqual(len(node2.incisos[1].tags), 2)
        tag_ids_2_2 = [t.id for t in node2.incisos[1].tags]
        self.assertIn("tag-key", tag_ids_2_2)
        self.assertIn("tag-doubt", tag_ids_2_2)

        # Nodo 3: simple sin tags
        node3 = nodes[2]
        self.assertEqual(len(node3.tags), 0)

    def test_tag_catalog_crud(self) -> None:
        record = Record()
        self.assertEqual(len(record.tags), 4)

        # 1. Add tag
        new_tag = PlannerService.add_tag_definition(record, "Urgente", "#ef4444")
        self.assertTrue(new_tag.id.startswith("tag-"))
        self.assertEqual(new_tag.name, "Urgente")
        self.assertEqual(len(record.tags), 5)

        # 2. Update tag
        success = PlannerService.update_tag_definition(record, new_tag.id, "Muy Urgente", "#dc2626")
        self.assertTrue(success)
        self.assertEqual(new_tag.name, "Muy Urgente")
        self.assertEqual(new_tag.color, "#dc2626")

        # Asignar tag a una sección
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=2)
        sec.set_exercise_tags(1, None, [new_tag.id, "tag-redo"])
        record.planner_sections.append(sec)
        self.assertIn(new_tag.id, sec.get_exercise_tags(1))

        # 3. Delete tag y verificar limpieza en cascada
        del_success = PlannerService.delete_tag_definition(record, new_tag.id)
        self.assertTrue(del_success)
        self.assertEqual(len(record.tags), 4)
        self.assertNotIn(new_tag.id, [t.id for t in record.tags])
        # Verificamos que se eliminó de los ejercicios asignados
        self.assertNotIn(new_tag.id, sec.get_exercise_tags(1))
        self.assertEqual(sec.get_exercise_tags(1), ["tag-redo"])

    def test_set_exercise_tags_auto_sync(self) -> None:
        record = Record()
        self.assertEqual(len(record.planner_sections), 0)

        # Asignar tags a una sección y ejercicio que aún no estaban en la planificación
        PlannerService.set_exercise_tags(
            record, "Práctica", 2, 7, 3, ["tag-doubt"]
        )
        self.assertEqual(len(record.planner_sections), 1)
        sec = record.planner_sections[0]
        self.assertEqual(sec.section_type, "Práctica")
        self.assertEqual(sec.section_number, 2)
        self.assertEqual(sec.total_exercises, 7)
        self.assertEqual(sec.get_incisos_count(7), 3)
        self.assertEqual(sec.get_exercise_tags(7, 3), ["tag-doubt"])

    def test_application_service_tags_facade(self) -> None:
        app = StudyApplicationService()
        catalog = app.get_tag_catalog()
        self.assertEqual(len(catalog), 4)

        # Añadir etiqueta
        added = app.add_tag_definition("Prueba Facade", "#8b5cf6")
        self.assertIsNotNone(added)
        self.assertEqual(len(app.get_tag_catalog()), 5)

        # Asignar y leer etiqueta
        app.set_exercise_tags("Guía", 1, 3, None, [added.id])
        tags = app.get_exercise_tags("Guía", 1, 3, None)
        self.assertEqual(tags, [added.id])

        # Actualizar
        ok = app.update_tag_definition(added.id, "Prueba Editada", "#7c3aed")
        self.assertTrue(ok)
        self.assertEqual(app.get_tag_catalog()[-1].name, "Prueba Editada")

        # Eliminar
        deleted = app.delete_tag_definition(added.id)
        self.assertTrue(deleted)
        self.assertEqual(len(app.get_tag_catalog()), 4)
        self.assertEqual(app.get_exercise_tags("Guía", 1, 3, None), [])


class TestExerciseTagsGUI(unittest.TestCase):
    """Pruebas gráficas de celdas, diálogos y filtrado de etiquetas."""

    @classmethod
    def setUpClass(cls) -> None:
        from PySide6.QtWidgets import QApplication
        cls.qapp = QApplication.instance() or QApplication([])

    def test_exercise_cell_button_with_tags_and_dimming(self) -> None:
        from application.planner_service import ExerciseNodeStatus
        from presentation.planner_widget import ExerciseCellButton

        tag1 = TagDefinition(id="t1", name="Rehacer", color="#ef4444")
        tag2 = TagDefinition(id="t2", name="Clave", color="#a855f7")

        node = ExerciseNodeStatus(
            section_type="Guía",
            section_number=1,
            exercise=1,
            tags=[tag1, tag2],
        )

        btn = ExerciseCellButton(node, is_dark=True)
        self.assertEqual(btn.sizeHint().width(), 52)
        self.assertEqual(btn.sizeHint().height(), 48)
        self.assertIn("Rehacer", btn.toolTip())
        self.assertIn("Clave", btn.toolTip())

        # Probar atenuación (dimming)
        self.assertIsNone(btn.graphicsEffect())
        btn.set_dimmed(True)
        self.assertIsNotNone(btn.graphicsEffect())
        btn.set_dimmed(False)
        self.assertIsNone(btn.graphicsEffect())

    def test_planner_widget_tag_filtering(self) -> None:
        from presentation.planner_widget import PlannerWidget, ExerciseCellButton

        app = StudyApplicationService()
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=3)
        app.add_or_update_planned_section(sec)

        # Asignar tag-redo solo al ejercicio 1
        app.set_exercise_tags("Guía", 1, 1, None, ["tag-redo"])

        widget = PlannerWidget(app, is_dark_mode=True)
        self.assertTrue(hasattr(widget, "combo_tag_filter"))
        self.assertGreaterEqual(widget.combo_tag_filter.count(), 3)

        # Obtener botones de celdas
        buttons = widget.findChildren(ExerciseCellButton)
        self.assertEqual(len(buttons), 3)

        # Inicialmente en "all": ninguno atenuado
        for b in buttons:
            self.assertIsNone(b.graphicsEffect())

        # Cambiar filtro a "Solo con marcadores" (índice 1)
        widget.combo_tag_filter.setCurrentIndex(1)
        # Ejercicio 1 no debe estar atenuado, 2 y 3 sí
        self.assertIsNone(buttons[0].graphicsEffect())
        self.assertIsNotNone(buttons[1].graphicsEffect())
        self.assertIsNotNone(buttons[2].graphicsEffect())

        # Volver a "Todos los ejercicios" (índice 0)
        widget.combo_tag_filter.setCurrentIndex(0)
        for b in buttons:
            self.assertIsNone(b.graphicsEffect())

    def test_home_view_tags_button_reflects_active_exercise(self) -> None:
        from presentation.home_view import HomeViewWidget
        from presentation.audio_service import AudioService

        app = StudyApplicationService()
        audio = AudioService()
        home = HomeViewWidget(app, audio, is_dark_mode=True)

        self.assertTrue(hasattr(home, "tags_button"))
        self.assertEqual(home.tags_button.text().strip(), "MARCADORES")

        # Asignar tag a Guía 1 Ejercicio 1
        app.set_exercise_tags("Guía", 1, 1, None, ["tag-redo", "tag-doubt"])
        home.sync_location(force=True)

        self.assertIn("MARCADORES (2)", home.tags_button.text())

        # Cambiar a Ejercicio 2
        home.exercise_input.setValue(2)
        home.sync_location()
        self.assertEqual(home.tags_button.text().strip(), "MARCADORES")


if __name__ == "__main__":
    unittest.main()

