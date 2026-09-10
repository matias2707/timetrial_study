"""Pruebas para la detección y corrección de desfasajes de incisos."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["STUDY_TIMETRIAL_TEST"] = "1"

from PySide6.QtWidgets import QApplication, QLabel

from application.application_service import StudyApplicationService
from domain.models import Record, TimerItem
from domain.timer_service import TimerMode
from infrastructure.storage_service import StorageService
from presentation.inciso_dialog import (
    ACTION_CANCEL,
    ACTION_CORRECT_ALL,
    ACTION_CUSTOM_VALUES,
    ACTION_KEEP_MANUAL,
    IncisoCorrectionDialog,
)
from presentation.main_window import MainWindow

app = QApplication.instance() or QApplication([])


class TestIncisoCorrectionService(unittest.TestCase):
    """Pruebas unitarias de detección y promoción de incisos en StudyApplicationService."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "test_record.json"
        self.storage = StorageService()
        self.service = StudyApplicationService(self.storage)
        self.storage.path = self.file_path
        self.record = self.service.record
        self.service.save()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_find_inciso_gap_candidates_returns_empty_when_no_inciso_on_both(self) -> None:
        """No debe detectar desfasaje si el nuevo inciso también es None."""
        self.record.items.append(
            TimerItem("Guía", 1, 3, None, 60_000, 0, True)
        )
        self.service.save()

        self.assertEqual(
            self.service.find_inciso_gap_candidates("Guía", 1, 3, None),
            [],
        )

    def test_find_inciso_gap_candidates_detects_gap_when_saving_inciso_1_with_existing_unincisoed(self) -> None:
        """Detecta items sin inciso cuando se registra inciso 1 (caso E1 I0 luego E1 I1)."""
        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        self.record.items.append(item0)
        self.service.save()

        candidates = self.service.find_inciso_gap_candidates("Guía", 1, 1, 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], item0)

    def test_find_inciso_gap_candidates_detects_gap_when_saving_inciso_2_with_existing_unincisoed(self) -> None:
        """Detecta items sin inciso cuando se registra inciso 2."""
        item0 = TimerItem("Guía", 1, 5, None, 120_000, 0, True)
        self.record.items.append(item0)
        self.service.save()

        candidates = self.service.find_inciso_gap_candidates("Guía", 1, 5, 2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], item0)

    def test_find_inciso_gap_candidates_detects_gap_with_e1_i0_and_e1_i1_when_saving_e1_i2(self) -> None:
        """Caso del usuario: E1 I0 + E1 I1 existentes y se carga E1 I2."""
        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        item1 = TimerItem("Guía", 1, 1, 1, 60_000, 0, True)
        self.record.items.extend([item0, item1])
        self.service.save()

        candidates = self.service.find_inciso_gap_candidates("Guía", 1, 1, 2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], item0)

    def test_find_inciso_gap_candidates_ignores_items_with_incisos_when_no_unincisoed(self) -> None:
        """No debe considerar items que ya tienen inciso como candidatos a desfasaje."""
        item2 = TimerItem("Guía", 1, 1, 2, 60_000, 0, True)
        self.record.items.append(item2)
        self.service.save()

        candidates = self.service.find_inciso_gap_candidates("Guía", 1, 1, 3)
        self.assertEqual(candidates, [])

    def test_promote_gap_items_updates_only_unincisoed_to_1(self) -> None:
        """promote_gap_items solo actualiza los items con '-' (sin inciso) a 1 y persiste."""
        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        item1 = TimerItem("Guía", 1, 1, 1, 60_000, 0, True)
        self.record.items.extend([item0, item1])
        self.service.save()

        # Solo le pasamos item0 (el que estaba sin inciso)
        self.service.promote_gap_items([item0], target_inciso=1)

        self.assertEqual(item0.inciso, 1)
        self.assertEqual(item1.inciso, 1)

        reloaded = self.storage.load(self.file_path)
        self.assertEqual(reloaded.items[0].inciso, 1)
        self.assertEqual(reloaded.items[1].inciso, 1)


class TestIncisoCorrectionDialog(unittest.TestCase):
    """Pruebas del widget de diálogo interactivo de 3 opciones y sus textos."""

    def test_dialog_has_exact_3_options_and_manual_checked_by_default(self) -> None:
        dlg = IncisoCorrectionDialog(
            section_type="Guía",
            section_number=2,
            exercise=4,
            current_inciso=2,
            affected_count=1,
            is_dark=True,
        )
        # 3 opciones exactas y la primera es la manual (por defecto)
        self.assertEqual(len(dlg.btn_group.buttons()), 3)
        self.assertEqual(dlg.btn_group.buttons()[0], dlg.radio_manual)
        self.assertEqual(dlg.btn_group.buttons()[1], dlg.radio_correct)
        self.assertEqual(dlg.btn_group.buttons()[2], dlg.radio_custom)
        self.assertTrue(dlg.radio_manual.isChecked())
        self.assertFalse(dlg.radio_correct.isChecked())
        self.assertFalse(dlg.radio_custom.isChecked())

        # Controles personalizados deshabilitados inicialmente
        self.assertFalse(dlg.combo_section_type.isEnabled())
        self.assertFalse(dlg.spin_section_number.isEnabled())
        self.assertFalse(dlg.spin_custom_exercise.isEnabled())
        self.assertFalse(dlg.spin_custom_inciso.isEnabled())

    def test_dialog_texts_match_user_specification(self) -> None:
        dlg = IncisoCorrectionDialog(
            section_type="Guía",
            section_number=1,
            exercise=3,
            current_inciso=2,
            affected_count=2,
            is_dark=True,
        )
        # Verificar subtexto de opción 1
        labels = [lbl.text() for lbl in dlg.findChildren(QLabel)]
        found_opt1_hint = any("Se actualizarán 2 registros de" in t and "Inciso 1" in t for t in labels)
        self.assertTrue(found_opt1_hint)

        # Verificar subtexto de opción 2 (manual) con salto de línea en la última oración
        found_opt2_hint = any(
            "Guardar como" in t
            and "Ejercicio 3" in t
            and "Inciso 2" in t
            and "<br>" in t
            and "No se modificarán anteriores" in t
            for t in labels
        )
        self.assertTrue(found_opt2_hint)

        # Verificar etiquetas de opción 3
        found_nombre_sec = any("Nombre de sección:" in t for t in labels)
        found_num_sec = any("N° de sección:" in t for t in labels)
        self.assertTrue(found_nombre_sec)
        self.assertTrue(found_num_sec)

    def test_dialog_select_custom_values(self) -> None:
        dlg = IncisoCorrectionDialog(section_type="Guía", section_number=1, exercise=4, current_inciso=2)
        dlg.radio_custom.setChecked(True)
        self.assertTrue(dlg.combo_section_type.isEnabled())
        self.assertTrue(dlg.spin_section_number.isEnabled())
        self.assertTrue(dlg.spin_custom_exercise.isEnabled())
        self.assertTrue(dlg.spin_custom_inciso.isEnabled())

        dlg.combo_section_type.setCurrentText("Práctica")
        dlg.spin_section_number.setValue(3)
        dlg.spin_custom_exercise.setValue(7)
        dlg.spin_custom_inciso.setValue(4)
        dlg._on_accept()

        self.assertEqual(dlg.result_action, ACTION_CUSTOM_VALUES)
        self.assertEqual(dlg.selected_section_type, "Práctica")
        self.assertEqual(dlg.selected_section_number, 3)
        self.assertEqual(dlg.selected_exercise, 7)
        self.assertEqual(dlg.selected_inciso, 4)

    def test_badge_grammar_agreement_singular_and_plural(self) -> None:
        dlg1 = IncisoCorrectionDialog(affected_count=1)
        labels1 = [lbl.text() for lbl in dlg1.findChildren(QLabel)]
        self.assertTrue(any("Se detectó <b>1</b> registro previo" in t for t in labels1))

        dlg2 = IncisoCorrectionDialog(affected_count=3)
        labels2 = [lbl.text() for lbl in dlg2.findChildren(QLabel)]
        self.assertTrue(any("Se detectaron <b>3</b> registros previos" in t for t in labels2))

    def test_dialog_select_custom_values_with_zero_inciso_yields_none(self) -> None:
        dlg = IncisoCorrectionDialog(section_type="Guía", section_number=1, exercise=4, current_inciso=2)
        dlg.radio_custom.setChecked(True)
        dlg.spin_custom_inciso.setValue(0)
        dlg._on_accept()

        self.assertEqual(dlg.result_action, ACTION_CUSTOM_VALUES)
        self.assertIsNone(dlg.selected_inciso)

    def test_dialog_is_application_modal(self) -> None:
        dlg = IncisoCorrectionDialog(
            section_type="Guía",
            section_number=1,
            exercise=1,
            current_inciso=2,
            affected_count=1,
            is_dark=True,
        )
        from PySide6.QtCore import Qt
        self.assertTrue(dlg.isModal())
        self.assertEqual(dlg.windowModality(), Qt.WindowModality.ApplicationModal)


class TestMainWindowIncisoFlow(unittest.TestCase):
    """Pruebas de integración de la interacción de MainWindow ante desfasajes de incisos."""

    def setUp(self) -> None:
        self.window = MainWindow()
        self.service = self.window.application

    def tearDown(self) -> None:
        self.window.stop_timer()
        self.window.close()

    def test_timer_pauses_when_dialog_opens_and_resumes_on_cancel(self) -> None:
        """Verifica que el cronómetro se congela/pausa mientras el diálogo está abierto y se reanuda en PLAY al cancelar."""
        # 1. Crear item sin inciso previo
        self.service.record.items.append(
            TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        )
        self.service.save()

        # 2. Iniciar sesión en Inciso 1
        self.window.section_input.setText("Guía")
        self.window.section_number_input.setValue(1)
        self.window.exercise_input.setValue(1)
        self.window.inciso_input.setValue(1)
        self.window.sync_location()
        self.window.toggle_session()
        self.assertEqual(self.service.mode, TimerMode.PLAY)

        # 3. Durante el diálogo, verificar que está pausado y congelado
        dialog_checks = []

        def fake_exec(dlg):
            dialog_checks.append(self.service.is_timer_paused)
            t1 = self.service.timer.snapshot()
            import time
            time.sleep(0.02)
            t2 = self.service.timer.snapshot()
            # El tiempo de ejercicio y descanso no debe haber aumentado
            dialog_checks.append(t1 == t2)
            dlg.result_action = ACTION_CANCEL
            return False

        with patch.object(IncisoCorrectionDialog, "exec", fake_exec):
            self.window.finish_item(True)

        self.assertEqual(dialog_checks, [True, True])
        # Al cancelar, el cronómetro ya no debe estar pausado y debe haber vuelto a PLAY (no a BREAK)
        self.assertFalse(self.service.is_timer_paused)
        self.assertEqual(self.service.mode, TimerMode.PLAY)

    def test_finish_item_promotes_unincisoed_and_saves(self) -> None:
        """Al completar con ACTION_CORRECT_ALL, los items sin inciso pasan a 1 y el actual se guarda."""
        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        self.service.record.items.append(item0)
        self.service.save()

        self.window.section_input.setText("Guía")
        self.window.section_number_input.setValue(1)
        self.window.exercise_input.setValue(1)
        self.window.inciso_input.setValue(2)
        self.window.sync_location()
        self.window.toggle_session()

        # Simular diálogo que acepta ACTION_CORRECT_ALL
        def fake_exec(dlg):
            dlg.result_action = ACTION_CORRECT_ALL
            return True

        with patch.object(IncisoCorrectionDialog, "exec", fake_exec):
            self.window.finish_item(True)

        self.assertEqual(len(self.service.record.items), 2)
        self.assertEqual(self.service.record.items[0].inciso, 1)
        self.assertEqual(self.service.record.items[1].inciso, 2)
        self.assertEqual(self.service.mode, TimerMode.WAITING)
        self.assertFalse(self.service.is_timer_paused)

    def test_close_event_ignored_when_inciso_dialog_cancelled(self) -> None:
        """Si en closeEvent se pulsa Guardar pero se cancela el diálogo de incisos, la ventana no se cierra."""
        from PySide6.QtGui import QCloseEvent
        from PySide6.QtWidgets import QMessageBox

        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        self.service.record.items.append(item0)
        self.service.save()

        self.window.section_input.setText("Guía")
        self.window.section_number_input.setValue(1)
        self.window.exercise_input.setValue(1)
        self.window.inciso_input.setValue(2)
        self.window.sync_location()
        self.window.toggle_session()

        event = QCloseEvent()

        def fake_exec(dlg):
            dlg.result_action = ACTION_CANCEL
            return False

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Save):
            with patch.object(IncisoCorrectionDialog, "exec", fake_exec):
                self.window.closeEvent(event)

        self.assertFalse(event.isAccepted())
        self.assertEqual(self.service.mode, TimerMode.PLAY)

    def test_add_item_uses_inciso_correction_dialog(self) -> None:
        """Al agregar un item manual mediante add_item, si hay desfasaje se abre el diálogo y se corrige."""
        from presentation.presentation_dialogs import ItemDialog

        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        self.service.record.items.append(item0)
        self.service.save()

        manual_item = TimerItem("Guía", 1, 1, 2, 90_000, 0, True)

        def fake_item_exec(dlg):
            dlg.validated_item = manual_item
            return 1

        def fake_inciso_exec(dlg):
            dlg.result_action = ACTION_CORRECT_ALL
            return True

        with patch.object(ItemDialog, "exec", fake_item_exec):
            with patch.object(IncisoCorrectionDialog, "exec", fake_inciso_exec):
                self.window.add_item()

        self.assertEqual(len(self.service.record.items), 2)
        self.assertEqual(self.service.record.items[0].inciso, 1)
        self.assertEqual(self.service.record.items[1].inciso, 2)

    def test_finish_item_custom_values_with_sin_inciso_saves_as_none(self) -> None:
        """Al personalizar valor actual y dejar 'Sin inciso' (0), el item se debe guardar con inciso=None."""
        item0 = TimerItem("Guía", 1, 1, None, 60_000, 0, True)
        self.service.record.items.append(item0)
        self.service.save()

        self.window.section_input.setText("Guía")
        self.window.section_number_input.setValue(1)
        self.window.exercise_input.setValue(1)
        self.window.inciso_input.setValue(1)
        self.window.sync_location()
        self.window.toggle_session()

        def fake_exec(dlg):
            dlg.radio_custom.setChecked(True)
            dlg.spin_custom_inciso.setValue(0)
            dlg._on_accept()
            return True

        with patch.object(IncisoCorrectionDialog, "exec", fake_exec):
            self.window.finish_item(True)

        self.assertEqual(len(self.service.record.items), 2)
        self.assertIsNone(self.service.record.items[0].inciso)
        self.assertIsNone(self.service.record.items[1].inciso)
        self.assertEqual(self.window.inciso_input.value(), 0)


if __name__ == "__main__":
    unittest.main()
