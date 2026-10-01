from __future__ import annotations

"""Pruebas unitarias e integrales para el control robusto de archivos, autoguardado y recuperación de fallos (TASK-029).

Cubre:
1. Escritura Atómica en disco (save_atomic).
2. Detección preventiva de modificaciones externas (Cloud Sync Guard / FileMetadataWatcher).
3. Bloqueo de concurrencia de una sola instancia activa (FileLockManager / Single-Writer Lock).
4. Diario de recuperación de sesión activa ante caídas (SessionDraftManager / Crash Recovery).
5. Motor de autoguardado periódico y por eventos de ventana.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from application.application_service import SessionLocation, StudyApplicationService
from application.save_policy import SavePolicy
from domain.exceptions import ExternalModificationConflictError, FileLockedError
from domain.models import Record, TimerItem
from domain.timer_service import TimerMode
from infrastructure.storage_service import (
    FileLockManager,
    FileMetadataWatcher,
    LockInfo,
    SessionDraftManager,
    StorageService,
    save_atomic,
)
from presentation.main_window import MainWindow

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestAtomicFileWriting(unittest.TestCase):
    """Pruebas para save_atomic garantizando resistencia ante fallos de I/O."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_atomic_creates_and_replaces_file_cleanly(self) -> None:
        target_path = self.dir_path / "test_record.json"
        payload = json.dumps({"record_name": "Test", "schema_version": 1})

        save_atomic(target_path, payload)

        self.assertTrue(target_path.exists())
        self.assertEqual(target_path.read_text(encoding="utf-8"), payload)
        # Asegurar que no quedan temporales residuales
        temp_files = list(self.dir_path.glob(".*.tmp"))
        self.assertEqual(len(temp_files), 0)

    def test_save_atomic_cleans_up_temp_file_on_error(self) -> None:
        target_path = self.dir_path / "failing_record.json"

        # Simular fallo durante os.replace
        with patch("os.replace", side_effect=OSError("Disk write error")):
            with self.assertRaises(OSError):
                save_atomic(target_path, "{}")

        # El archivo objetivo no debe existir y el temporal debe ser eliminado
        self.assertFalse(target_path.exists())
        temp_files = list(self.dir_path.glob(".*.tmp"))
        self.assertEqual(len(temp_files), 0)


class TestCloudSyncGuard(unittest.TestCase):
    """Pruebas para FileMetadataWatcher y detección de cambios externos."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.storage = StorageService(default_dir=self.dir_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_watcher_detects_external_file_change(self) -> None:
        record_path = self.dir_path / "sync_test.json"
        record = Record(record_name="sync_test")
        self.storage.save(record, record_path)

        self.assertFalse(self.storage.has_external_modification())

        # Simular modificación externa por software de nube (Dropbox/OneDrive)
        time.sleep(0.05)  # Asegurar avance de mtime
        record_path.write_text(json.dumps({"record_name": "sync_test", "modified": True}), encoding="utf-8")

        self.assertTrue(self.storage.has_external_modification())

    def test_watcher_ignores_mtime_touch_if_content_identical(self) -> None:
        record_path = self.dir_path / "touch_test.json"
        record = Record(record_name="touch_test")
        self.storage.save(record, record_path)

        # Modificar solo el mtime del archivo sin alterar el hash SHA-256
        old_mtime = record_path.stat().st_mtime
        new_mtime = old_mtime + 5.0
        os.utime(record_path, (new_mtime, new_mtime))

        self.assertFalse(self.storage.has_external_modification())

    def test_save_raises_conflict_error_on_external_change_unless_forced(self) -> None:
        record_path = self.dir_path / "conflict.json"
        record = Record(record_name="conflict")
        self.storage.save(record, record_path)

        # Modificación externa
        time.sleep(0.05)
        record_path.write_text(json.dumps({"external": 123}), encoding="utf-8")

        # Guardado normal sin force debe lanzar ExternalModificationConflictError
        with self.assertRaises(ExternalModificationConflictError):
            self.storage.save(record, record_path, force=False)

        # Guardado forzado (sobrescribir) debe proceder
        self.storage.save(record, record_path, force=True)
        self.assertFalse(self.storage.has_external_modification())

    def test_application_reload_from_disk_restores_external_content(self) -> None:
        record_path = self.dir_path / "reload.json"
        storage = StorageService(default_dir=self.dir_path)
        app = StudyApplicationService(storage=storage)
        app.save_as(record_path)

        # Mutación local en memoria
        item = TimerItem("Guía", 1, 1, None, 1000, 0, True)
        app.add_item(item)
        self.assertTrue(app.is_dirty)
        self.assertEqual(len(app.record.items), 1)

        # Modificación en disco externa
        external_record = Record(record_name="reload")
        external_item = TimerItem("Parcial", 2, 5, 1, 2000, 0, True)
        external_record.items.append(external_item)
        time.sleep(0.05)
        record_path.write_text(json.dumps(external_record.to_dict()), encoding="utf-8")

        self.assertTrue(app.has_external_modification())

        # Recargar de disco
        app.reload_from_disk()

        self.assertFalse(app.is_dirty)
        self.assertFalse(app.has_external_modification())
        self.assertEqual(len(app.record.items), 1)
        self.assertEqual(app.record.items[0].section_type, "Parcial")
        self.assertEqual(app.record.items[0].exercise, 5)


class TestSingleWriterFileLock(unittest.TestCase):
    """Pruebas para FileLockManager y prevención de colisión de instancias concurrentes."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_acquire_and_release_lock_lifecycle(self) -> None:
        target_path = self.dir_path / "locked_file.json"
        lock_mgr = FileLockManager(target_path)

        acquired, info = lock_mgr.acquire()
        self.assertTrue(acquired)
        self.assertIsNone(info)
        self.assertTrue(lock_mgr.lock_file.exists())

        # Re-adquisición por el mismo proceso es permitida
        active, existing = lock_mgr.is_lock_active()
        self.assertFalse(active)

        lock_mgr.release()
        self.assertFalse(lock_mgr.lock_file.exists())

    def test_lock_active_when_held_by_another_live_process(self) -> None:
        target_path = self.dir_path / "concurrent.json"
        lock_mgr = FileLockManager(target_path)

        # Simular archivo lock creado por otro PID activo en este mismo host
        foreign_pid = 999999
        payload = {
            "pid": foreign_pid,
            "hostname": socket.gethostname(),
            "acquired_at": datetime.now().isoformat(),
            "record_path": str(target_path),
        }
        lock_mgr.lock_file.write_text(json.dumps(payload), encoding="utf-8")

        # Con el proceso simulado como vivo
        with patch.object(FileLockManager, "_is_process_alive", return_value=True):
            active, info = lock_mgr.is_lock_active()
            self.assertTrue(active)
            self.assertIsNotNone(info)
            self.assertEqual(info.pid, foreign_pid)

            # Adquisición normal falla
            acquired, info2 = lock_mgr.acquire(force=False)
            self.assertFalse(acquired)

            # Adquisición forzada tiene éxito
            acquired_force, _ = lock_mgr.acquire(force=True)
            self.assertTrue(acquired_force)

    def test_stale_lock_from_dead_process_is_broken_automatically(self) -> None:
        target_path = self.dir_path / "stale.json"
        lock_mgr = FileLockManager(target_path)

        # Simular archivo lock de un proceso ya extinto
        dead_pid = 88888
        payload = {
            "pid": dead_pid,
            "hostname": socket.gethostname(),
            "acquired_at": datetime.now().isoformat(),
            "record_path": str(target_path),
        }
        lock_mgr.lock_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(FileLockManager, "_is_process_alive", return_value=False):
            active, _ = lock_mgr.is_lock_active()
            self.assertFalse(active)

            # Se adquiere sin problemas
            acquired, _ = lock_mgr.acquire(force=False)
            self.assertTrue(acquired)


class TestSessionDraftManager(unittest.TestCase):
    """Pruebas para SessionDraftManager y recuperación de fallos en cronómetro (Crash Recovery)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.drafts_dir = Path(self.temp_dir.name) / ".drafts"
        self.draft_manager = SessionDraftManager(self.drafts_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_and_load_session_draft(self) -> None:
        record_path = Path("d:/Proyectos/Algebra.json")
        location = {"section_type": "Guía", "section_number": 2, "exercise": 7, "inciso": 3}

        draft_path = self.draft_manager.save_draft(
            record_path=record_path,
            timer_mode="PLAY",
            is_paused=False,
            exercise_time_ms=180000,
            break_time_ms=30000,
            location=location,
            comment="Resolviendo paso 3",
        )

        self.assertTrue(draft_path.exists())
        self.assertTrue(self.draft_manager.has_draft(record_path))

        loaded = self.draft_manager.load_draft(record_path)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["version"], 1)
        self.assertEqual(loaded["timer_mode"], "PLAY")
        self.assertEqual(loaded["exercise_time_ms"], 180000)
        self.assertEqual(loaded["break_time_ms"], 30000)
        self.assertEqual(loaded["comment"], "Resolviendo paso 3")
        self.assertEqual(loaded["location"]["exercise"], 7)
        self.assertEqual(loaded["location"]["inciso"], 3)

        # Descarte
        self.draft_manager.discard_draft(record_path)
        self.assertFalse(self.draft_manager.has_draft(record_path))

    def test_application_service_session_draft_lifecycle(self) -> None:
        storage = StorageService(default_dir=Path(self.temp_dir.name), drafts_dir=self.drafts_dir)
        app = StudyApplicationService(storage=storage)
        record_file = Path(self.temp_dir.name) / "draft_test.json"
        app.save_as(record_file)

        # Iniciar cronómetro
        loc = SessionLocation("Guía", 3, 10, 2)
        app.toggle_session(loc)
        app.set_comment("Comentario en curso")

        # Guardar borrador periódico
        saved = app.save_session_draft()
        self.assertTrue(saved)
        self.assertTrue(app.storage.draft_manager.has_draft(record_file))

        # Al completar el item, el borrador debe eliminarse automáticamente
        app.finish_item(completed=True)
        self.assertFalse(app.storage.draft_manager.has_draft(record_file))

    def test_application_service_restore_draft_state(self) -> None:
        storage = StorageService(default_dir=Path(self.temp_dir.name), drafts_dir=self.drafts_dir)
        app = StudyApplicationService(storage=storage)
        record_file = Path(self.temp_dir.name) / "restore_test.json"
        app.save_as(record_file)

        draft = {
            "version": 1,
            "record_path": str(record_file),
            "updated_at": "2026-09-30T20:00:00",
            "session_started_at": "2026-09-30T19:40:00",
            "timer_mode": "PLAY",
            "is_paused": True,
            "exercise_time_ms": 1200000,
            "break_time_ms": 60000,
            "location": {"section_type": "Parcial", "section_number": 1, "exercise": 4, "inciso": 2},
            "comment": "Recuperando demostración",
            "editing_item_id": None,
        }

        app.restore_session_draft(draft)

        self.assertEqual(app.location.section_type, "Parcial")
        self.assertEqual(app.location.section_number, 1)
        self.assertEqual(app.location.exercise, 4)
        self.assertEqual(app.location.inciso, 2)
        self.assertEqual(app.pending_comment, "Recuperando demostración")
        self.assertEqual(app.mode, TimerMode.PLAY)
        self.assertTrue(app.is_timer_paused)
        self.assertEqual(app.timer.exercise_time_ms, 1200000)
        self.assertEqual(app.timer.break_time_ms, 60000)


class TestAutosaveAndWindowEvents(unittest.TestCase):
    """Pruebas del motor de autoguardado periódico y eventos de ventana en MainWindow."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.storage = StorageService(default_dir=self.dir_path)
        self.app_service = StudyApplicationService(
            storage=self.storage,
            save_policy=SavePolicy.AUTO_PERIODIC,
        )
        self.window = MainWindow()
        self.window.application = self.app_service
        self.window.home_view.application = self.app_service
        self.window.records_view.application = self.app_service
        self.window.organizer.application = self.app_service
        self.window.statistics_view.application = self.app_service

        self.test_file = self.dir_path / "autosave_window.json"
        self.app_service.save_as(self.test_file)

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def test_periodic_autosave_persists_dirty_state(self) -> None:
        # Añadir item -> is_dirty = True
        item = TimerItem("Guía", 1, 2, None, 1000, 0, True)
        self.app_service.add_item(item)
        self.assertTrue(self.app_service.is_dirty)

        # Disparar autoguardado periódico
        self.window._on_periodic_autosave()

        # Debe haberse persistido en disco y reseteado dirty
        self.assertFalse(self.app_service.is_dirty)
        reloaded = self.storage.read(self.test_file)
        self.assertEqual(len(reloaded.items), 1)

    def test_periodic_autosave_respects_manual_policy(self) -> None:
        self.app_service.save_policy = SavePolicy.MANUAL
        item = TimerItem("Guía", 1, 3, None, 1000, 0, True)
        self.app_service.add_item(item)
        self.assertTrue(self.app_service.is_dirty)

        # El autoguardado no debe ejecutarse en modo manual
        self.window._on_periodic_autosave()
        self.assertTrue(self.app_service.is_dirty)

    def test_window_deactivation_triggers_autosave(self) -> None:
        item = TimerItem("Guía", 1, 4, None, 1000, 0, True)
        self.app_service.add_item(item)
        self.assertTrue(self.app_service.is_dirty)

        # Simular evento de cambio de activación de ventana
        event = QEvent(QEvent.Type.ActivationChange)
        with patch.object(self.window, "isActiveWindow", return_value=False):
            self.window.changeEvent(event)

        self.assertFalse(self.app_service.is_dirty)

    def test_autosave_suspends_and_prompts_on_external_cloud_conflict(self) -> None:
        item = TimerItem("Guía", 1, 5, None, 1000, 0, True)
        self.app_service.add_item(item)
        self.assertTrue(self.app_service.is_dirty)

        # Modificación externa en disco
        time.sleep(0.05)
        self.test_file.write_text(json.dumps({"external": True}), encoding="utf-8")
        self.assertTrue(self.app_service.has_external_modification())

        # El autoguardado periódico debe detectar el conflicto y pausarse
        with patch.object(self.window, "_handle_external_modification_conflict") as mock_conflict:
            self.window._on_periodic_autosave()
            mock_conflict.assert_called_once()


if __name__ == "__main__":
    unittest.main()
