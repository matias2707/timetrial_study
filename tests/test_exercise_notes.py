"""Pruebas automatizadas para TASK-003: Sistema de notas y apuntes por ejercicio en la planificación."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from application.application_service import SessionLocation, StudyApplicationService
from application.planner_service import (
    STATUS_COMPLETED,
    STATUS_PENDING,
    ExerciseNodeStatus,
    PlannerService,
)
from domain.models import PlannedSection, Record, TimerItem
from infrastructure.storage_service import StorageService

# Asegurar instancia de QApplication para pruebas de widgets
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app_instance = QApplication.instance() or QApplication([])


class TestExerciseNotesDomain(unittest.TestCase):
    """Pruebas de dominio y persistencia para exercise_notes en PlannedSection y Record."""

    def test_planned_section_get_and_set_note(self) -> None:
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=5)
        self.assertEqual(sec.get_note(1), "")
        self.assertEqual(sec.get_note(2, 1), "")

        # Asignar nota a ejercicio simple
        sec.set_note(1, None, "Cuidado con signo en derivada")
        self.assertEqual(sec.get_note(1), "Cuidado con signo en derivada")
        self.assertIn("1", sec.exercise_notes)

        # Asignar nota a inciso
        sec.set_note(2, 3, "Fórmula de integración por partes")
        self.assertEqual(sec.get_note(2, 3), "Fórmula de integración por partes")
        self.assertIn("2.3", sec.exercise_notes)

        # Limpiar nota pasando texto vacío o espacios
        sec.set_note(1, None, "   ")
        self.assertEqual(sec.get_note(1), "")
        self.assertNotIn("1", sec.exercise_notes)

    def test_planned_section_serialization_backwards_compatibility(self) -> None:
        sec = PlannedSection(section_type="Práctica", section_number=2, total_exercises=3)
        sec.set_note(1, None, "Nota ejercicio 1")
        sec.set_note(2, 1, "Nota inciso 2.1")

        data = sec.to_dict()
        self.assertIn("exercise_notes", data)
        self.assertEqual(data["exercise_notes"]["1"], "Nota ejercicio 1")
        self.assertEqual(data["exercise_notes"]["2.1"], "Nota inciso 2.1")

        # Reconstruir
        restored = PlannedSection.from_dict(data)
        self.assertEqual(restored.get_note(1), "Nota ejercicio 1")
        self.assertEqual(restored.get_note(2, 1), "Nota inciso 2.1")

        # Reconstruir desde datos legados sin 'exercise_notes'
        legacy_data = {
            "section_type": "Guía",
            "section_number": 3,
            "total_exercises": 2,
            "exercise_configs": {"1": 2},
        }
        legacy_sec = PlannedSection.from_dict(legacy_data)
        self.assertEqual(legacy_sec.exercise_notes, {})
        self.assertEqual(legacy_sec.get_note(1), "")

    def test_record_serialization_with_exercise_notes(self) -> None:
        rec = Record(record_name="TestNotes")
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=2)
        sec.set_note(1, None, "Apunte de prueba")
        rec.planner_sections.append(sec)

        data = rec.to_dict()
        self.assertIn("planner_sections", data)
        self.assertIn("exercise_notes", data["planner_sections"][0])

        restored_rec = Record.from_dict(data)
        self.assertEqual(restored_rec.planner_sections[0].get_note(1), "Apunte de prueba")


class TestExerciseNotesService(unittest.TestCase):
    """Pruebas de lógica de negocio, sincronización y migración en PlannerService y ApplicationService."""

    def test_migrate_legacy_comments_to_notes(self) -> None:
        rec = Record(record_name="LegacyRecord")
        # Items con comentarios de intentos
        rec.items = [
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=10000,
                break_time_ms=0,
                completed=False,
                comment="Primer intento fallido",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=1,
                inciso=None,
                exercise_time_ms=12000,
                break_time_ms=0,
                completed=True,
                comment="Segundo intento: revisar regla de L'Hopital",
            ),
            TimerItem(
                section_type="Guía",
                section_number=1,
                exercise=2,
                inciso=1,
                exercise_time_ms=8000,
                break_time_ms=0,
                completed=True,
                comment="Inciso 1 resuelto con sustitución",
            ),
        ]

        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=3)
        # Dejamos una nota preexistente en Ejercicio 3
        sec.set_note(3, None, "Nota ya establecida previamente")
        rec.planner_sections = [sec]

        # Ejecutar migración
        migrated_count = PlannerService.migrate_legacy_comments_to_notes(rec)
        self.assertEqual(migrated_count, 2)  # Ej 1 y Ej 2.1

        # Verificar que Ej 1 tomó el último comentario
        self.assertEqual(sec.get_note(1), "Segundo intento: revisar regla de L'Hopital")
        # Verificar que Ej 2.1 tomó su comentario
        self.assertEqual(sec.get_note(2, 1), "Inciso 1 resuelto con sustitución")
        # Verificar que Ej 3 conservó su nota intacta
        self.assertEqual(sec.get_note(3), "Nota ya establecida previamente")

        # Verificar preservación histórica total de items
        self.assertEqual(len(rec.items), 3)
        self.assertEqual(rec.items[0].comment, "Primer intento fallido")
        self.assertEqual(rec.items[1].comment, "Segundo intento: revisar regla de L'Hopital")

        # Si volvemos a correr la migración, no debe duplicar ni sobrescribir
        second_run = PlannerService.migrate_legacy_comments_to_notes(rec)
        self.assertEqual(second_run, 0)

    def test_application_service_note_facade(self) -> None:
        service = StudyApplicationService()
        self.assertTrue(service.is_record_open)

        # Ubicación actual: Guía 1 Ejercicio 1
        service.set_location(SessionLocation("Guía", 1, 1, None), force=True)

        # Asignar nota desde servicio
        service.set_exercise_note("Guía", 1, 1, None, "Nota importante para Ejercicio 1")

        # Verificar get_exercise_note
        self.assertEqual(
            service.get_exercise_note("Guía", 1, 1, None), "Nota importante para Ejercicio 1"
        )
        # Verificar que pending_comment se sincronizó porque la ubicación coincide
        self.assertEqual(service.pending_comment, "Nota importante para Ejercicio 1")

        # Asignar nota a otra ubicación que no coincide
        service.set_exercise_note("Guía", 1, 2, None, "Nota Ejercicio 2")
        self.assertEqual(service.get_exercise_note("Guía", 1, 2, None), "Nota Ejercicio 2")
        # pending_comment debe seguir siendo el del Ejercicio 1
        self.assertEqual(service.pending_comment, "Nota importante para Ejercicio 1")

    def test_compute_overview_populates_note_and_has_note(self) -> None:
        rec = Record(record_name="TestOverviewNotes")
        sec = PlannedSection(section_type="Guía", section_number=1, total_exercises=2)
        sec.set_incisos_count(2, 2)  # Ej 2 con 2 incisos
        sec.set_note(1, None, "Nota simple en Ej 1")
        sec.set_note(2, 2, "Nota en inciso 2.2")
        rec.planner_sections.append(sec)

        overview = PlannerService.compute_overview(rec)
        sec_status = overview.sections[0]

        # Ejercicio 1 (simple)
        node_ex1 = sec_status.exercise_nodes[0]
        self.assertTrue(node_ex1.has_note)
        self.assertEqual(node_ex1.note, "Nota simple en Ej 1")

        # Ejercicio 2 (compuesto)
        node_ex2 = sec_status.exercise_nodes[1]
        self.assertTrue(node_ex2.has_note)  # Porque su inciso 2.2 tiene nota
        sub_2_1 = node_ex2.incisos[0]
        sub_2_2 = node_ex2.incisos[1]
        self.assertFalse(sub_2_1.has_note)
        self.assertEqual(sub_2_1.note, "")
        self.assertTrue(sub_2_2.has_note)
        self.assertEqual(sub_2_2.note, "Nota en inciso 2.2")


class TestExerciseNotesGUI(unittest.TestCase):
    """Pruebas de interfaz para ExerciseCellButton, ExerciseDetailPopup y HomeViewWidget."""

    def test_exercise_cell_button_with_notes_and_tooltip(self) -> None:
        from presentation.planner_widget import ExerciseCellButton

        node = ExerciseNodeStatus(
            section_type="Guía",
            section_number=1,
            exercise=3,
            inciso=None,
            status=STATUS_COMPLETED,
            attempts=1,
            exercise_time_ms=5000,
            note="Recordar fórmula de Pitágoras",
            has_note=True,
        )

        btn = ExerciseCellButton(node, is_dark=True)
        self.assertTrue(node.has_note)
        self.assertIn("📝 Apuntes / Nota:", btn.toolTip())
        self.assertIn("Recordar fórmula de Pitágoras", btn.toolTip())

    def test_exercise_detail_popup_notes_panel(self) -> None:
        from presentation.planner_dialogs import ExerciseDetailPopup

        service = StudyApplicationService()
        node = ExerciseNodeStatus(
            section_type="Guía",
            section_number=1,
            exercise=4,
            inciso=None,
            status=STATUS_PENDING,
            comments=["Comentario histórico 1", "Comentario histórico 2"],
        )

        popup = ExerciseDetailPopup(None, node, app_service=service, is_dark=True)
        self.assertTrue(hasattr(popup, "notes_edit"))
        self.assertTrue(hasattr(popup, "notes_feedback_label"))

        # Escribir nota y guardar
        popup.notes_edit.setPlainText("Nueva nota escrita desde el popup")
        popup._on_save_note()

        self.assertEqual(
            service.get_exercise_note("Guía", 1, 4, None), "Nueva nota escrita desde el popup"
        )
        self.assertEqual(node.note, "Nueva nota escrita desde el popup")
        self.assertTrue(node.has_note)
        self.assertEqual(popup.notes_feedback_label.text(), "✓ Apunte guardado")
        popup.close()

    def test_home_view_notes_button_sync(self) -> None:
        from presentation.audio_service import AudioService
        from presentation.home_view import HomeViewWidget

        app = StudyApplicationService()
        audio = AudioService()
        home = HomeViewWidget(app, audio, is_dark_mode=True)

        self.assertTrue(hasattr(home, "comment_button"))
        self.assertTrue(hasattr(home, "notes_button"))
        self.assertTrue(hasattr(home, "notes_browser"))
        self.assertTrue(hasattr(home, "notes_card"))
        self.assertEqual(home.comment_button.text().strip(), "APUNTES")

        # Guardar nota para Guía 1 Ejercicio 1
        app.set_exercise_note("Guía", 1, 1, None, "Nota cargada en ejercicio 1")
        home.sync_location(force=True)

        # El botón de apuntes permanece estático (no muestra el texto de la nota)
        self.assertEqual(home.comment_button.text().strip(), "APUNTES")
        # El contenido formateado aparece en el visor notes_browser
        self.assertIn("Nota cargada en ejercicio 1", home.notes_browser.toPlainText())

        # Cambiar a Ejercicio 2 sin nota
        home.exercise_input.setValue(2)
        home.sync_location(force=True)
        self.assertEqual(home.comment_button.text().strip(), "APUNTES")
        self.assertIn("Sin apuntes", home.notes_browser.toPlainText())
        home.close()


if __name__ == "__main__":
    unittest.main()
