from __future__ import annotations

"""Persistencia local de registros, escritura atómica, control de concurrencia y recuperación ante fallos."""

import atexit
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
from typing import Any

from domain.exceptions import ExternalModificationConflictError, FileLockedError
from domain.models import Record


def save_atomic(target_path: Path | str, payload: str, encoding: str = "utf-8") -> None:
    """Escribe el contenido en un archivo temporal adyacente y aplica reemplazo atómico."""
    resolved_path = Path(target_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = resolved_path.parent / f".{resolved_path.name}.{os.getpid()}.tmp"

    try:
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(payload)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(temp_path, resolved_path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


class FileMetadataWatcher:
    """Supervisa la integridad del archivo en disco respecto a la versión en memoria (Cloud Sync Guard)."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path: Path | None = Path(path).resolve() if path is not None else None
        self.last_known_mtime: float = 0.0
        self.last_known_hash: str = ""
        self.update_snapshot()

    def set_path(self, path: Path | str | None) -> None:
        self.path = Path(path).resolve() if path is not None else None
        self.update_snapshot()

    def has_external_modification(self) -> bool:
        """Determina si un proceso externo (ej. Dropbox/OneDrive/otro editor) modificó el archivo en disco."""
        if self.path is None or not self.path.exists():
            return False
        try:
            current_mtime = self.path.stat().st_mtime
        except OSError:
            return False

        if current_mtime != self.last_known_mtime:
            current_hash = self._compute_hash()
            return current_hash != self.last_known_hash
        return False

    def update_snapshot(self) -> None:
        """Actualiza los metadatos de control tras una carga o guardado local exitoso."""
        if self.path is not None and self.path.exists():
            try:
                self.last_known_mtime = self.path.stat().st_mtime
                self.last_known_hash = self._compute_hash()
            except OSError:
                self.last_known_mtime = 0.0
                self.last_known_hash = ""
        else:
            self.last_known_mtime = 0.0
            self.last_known_hash = ""

    def _compute_hash(self) -> str:
        if self.path is None or not self.path.exists():
            return ""
        try:
            return hashlib.sha256(self.path.read_bytes()).hexdigest()
        except OSError:
            return ""


@dataclass
class LockInfo:
    pid: int
    hostname: str
    acquired_at: str
    record_path: str


class FileLockManager:
    """Gestiona el archivo de bloqueo .lock para prevenir concurrencia entre instancias."""

    def __init__(self, target_path: Path | str | None = None) -> None:
        self.target_path: Path | None = Path(target_path).resolve() if target_path is not None else None
        self.lock_file: Path | None = self._get_lock_path(self.target_path) if self.target_path else None
        self._is_locked_by_me: bool = False
        atexit.register(self.release)

    @staticmethod
    def _get_lock_path(path: Path) -> Path:
        return path.parent / f".{path.name}.lock"

    def set_target(self, target_path: Path | str | None) -> None:
        if self._is_locked_by_me:
            self.release()
        self.target_path = Path(target_path).resolve() if target_path is not None else None
        self.lock_file = self._get_lock_path(self.target_path) if self.target_path else None

    def get_existing_lock(self) -> LockInfo | None:
        if not self.lock_file or not self.lock_file.exists():
            return None
        try:
            data = json.loads(self.lock_file.read_text(encoding="utf-8"))
            return LockInfo(
                pid=int(data.get("pid", 0)),
                hostname=str(data.get("hostname", "")),
                acquired_at=str(data.get("acquired_at", "")),
                record_path=str(data.get("record_path", "")),
            )
        except Exception:
            return None

    def is_lock_active(self) -> tuple[bool, LockInfo | None]:
        info = self.get_existing_lock()
        if not info:
            return False, None

        if info.pid == os.getpid() and info.hostname == socket.gethostname():
            return False, info

        if self._is_process_alive(info.pid, info.hostname):
            return True, info

        return False, info

    def acquire(self, force: bool = False) -> tuple[bool, LockInfo | None]:
        if not self.lock_file or not self.target_path:
            return True, None

        active, existing_info = self.is_lock_active()
        if active and not force:
            return False, existing_info

        payload = {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "acquired_at": datetime.now().isoformat(timespec="seconds"),
            "record_path": str(self.target_path),
        }
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._is_locked_by_me = True
            return True, None
        except OSError:
            return False, existing_info

    def release(self) -> None:
        if self.lock_file and self.lock_file.exists():
            info = self.get_existing_lock()
            if info is None or (info.pid == os.getpid() and info.hostname == socket.gethostname()):
                try:
                    self.lock_file.unlink()
                except OSError:
                    pass
        self._is_locked_by_me = False

    @staticmethod
    def _is_process_alive(pid: int, hostname: str) -> bool:
        if hostname != socket.gethostname():
            return True
        if pid <= 0:
            return False
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                STILL_ACTIVE = 259
                return exit_code.value == STILL_ACTIVE
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False


class SessionDraftManager:
    """Gestiona borradores de recuperación de sesión activa (Crash Recovery Journal)."""

    def __init__(self, drafts_dir: Path | str | None = None) -> None:
        if drafts_dir is not None:
            self.drafts_dir = Path(drafts_dir).resolve()
        else:
            self.drafts_dir = (Path.cwd() / "data" / ".drafts").resolve()

    def get_draft_path(self, record_path: Path | str) -> Path:
        p = Path(record_path)
        return self.drafts_dir / f"{p.stem}_draft.json"

    def has_draft(self, record_path: Path | str) -> bool:
        return self.get_draft_path(record_path).exists()

    def save_draft(
        self,
        record_path: Path | str,
        timer_mode: str,
        is_paused: bool,
        exercise_time_ms: int,
        break_time_ms: int,
        location: dict[str, Any],
        comment: str = "",
        session_started_at: str | None = None,
        editing_item_id: str | None = None,
    ) -> Path:
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_path = self.get_draft_path(record_path)
        payload = {
            "version": 1,
            "record_path": str(Path(record_path).resolve()),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "session_started_at": session_started_at,
            "timer_mode": timer_mode,
            "is_paused": is_paused,
            "exercise_time_ms": exercise_time_ms,
            "break_time_ms": break_time_ms,
            "location": location,
            "comment": comment,
            "editing_item_id": editing_item_id,
        }
        save_atomic(draft_path, json.dumps(payload, ensure_ascii=False, indent=2))
        return draft_path

    def load_draft(self, record_path: Path | str) -> dict[str, Any] | None:
        draft_path = self.get_draft_path(record_path)
        if not draft_path.exists():
            return None
        try:
            data = json.loads(draft_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version") == 1:
                return data
        except Exception:
            return None
        return None

    def discard_draft(self, record_path: Path | str) -> None:
        draft_path = self.get_draft_path(record_path)
        if draft_path.exists():
            try:
                draft_path.unlink()
            except OSError:
                pass


class RecentFilesManager:
    """Mantiene una lista de archivos abiertos recientemente en disco."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        else:
            data_recent = Path.cwd() / "data" / ".study_timetrial_recent.json"
            root_recent = Path.cwd() / ".study_timetrial_recent.json"
            if data_recent.exists():
                self.path = data_recent
            elif root_recent.exists():
                self.path = root_recent
            elif (Path.cwd() / "data").exists():
                self.path = data_recent
            else:
                self.path = root_recent
        self._paths: list[Path] = []
        self.load()

    @property
    def paths(self) -> list[Path]:
        return list(self._paths)

    def load(self) -> None:
        if not self.path.exists():
            self._paths = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._paths = []
            return
        entries = data if isinstance(data, list) else []
        resolved: list[Path] = []
        for value in entries:
            if not isinstance(value, str):
                continue
            candidate = Path(value).expanduser()
            if candidate.exists() and candidate.is_file():
                resolved.append(candidate)
        self._paths = resolved[:10]

    def save(self) -> None:
        payload = [str(path) for path in self._paths[:10]]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        save_atomic(self.path, json.dumps(payload, ensure_ascii=False, indent=2))

    def add(self, path: str | Path) -> None:
        candidate = Path(path).expanduser().resolve()
        existing = [item for item in self._paths if item.resolve() == candidate]
        if existing:
            self._paths = [existing[0], *[item for item in self._paths if item.resolve() != candidate]]
        else:
            self._paths = [candidate, *self._paths]
        self._paths = self._paths[:10]
        self.save()


class StorageService:
    """Gestiona el almacenamiento local del registro en formato JSON con persistencia atómica."""

    def __init__(
        self,
        recent_files_path: Path | str | None = None,
        default_dir: Path | str | None = None,
        drafts_dir: Path | str | None = None,
    ) -> None:
        self.path: Path | None = None
        self._default_dir = Path(default_dir) if default_dir is not None else None
        self.recent_files = RecentFilesManager(recent_files_path)
        self.watcher = FileMetadataWatcher()
        self.lock_manager = FileLockManager()
        self.draft_manager = SessionDraftManager(drafts_dir)

    @property
    def default_directory(self) -> Path:
        """Devuelve el directorio estándar para almacenar registros."""
        if self._default_dir is not None:
            return self._default_dir
        records_dir = Path.cwd() / "data" / "records"
        if records_dir.exists():
            return records_dir
        return Path.cwd()

    @property
    def is_open(self) -> bool:
        """Indica si hay un archivo activo asociado al servicio."""
        return self.path is not None

    def has_external_modification(self) -> bool:
        """Indica si el archivo activo en disco fue alterado externamente."""
        return self.watcher.has_external_modification()

    def create_automatic(self) -> Record:
        """Crea un registro nuevo con un nombre basado en la fecha actual."""
        stamp = datetime.now().strftime("%Y%m%d")
        target_dir = self.default_directory
        target_dir.mkdir(parents=True, exist_ok=True)
        self.path = target_dir / f"StudyTimetrial_{stamp}.json"
        self.lock_manager.set_target(self.path)
        self.lock_manager.acquire(force=True)
        self.watcher.set_path(self.path)
        return Record(record_name=self.path.stem)

    def save(self, record: Record, path: Path | None = None, force: bool = False) -> None:
        """Guarda el registro actual de forma atómica en el fichero activo o en uno explícito."""
        if path is not None:
            resolved = Path(path).resolve()
            if self.path != resolved:
                self.path = resolved
                self.lock_manager.set_target(self.path)
                self.lock_manager.acquire(force=True)
                self.watcher.set_path(self.path)

        if self.path is None:
            raise ValueError("No hay un archivo activo")

        if not force and self.watcher.has_external_modification():
            raise ExternalModificationConflictError(
                f"El archivo '{self.path.name}' ha sido modificado externamente por otro proceso."
            )

        payload = json.dumps(record.to_dict(), ensure_ascii=False, indent=2)
        save_atomic(self.path, payload)
        self.watcher.update_snapshot()
        if self.path.exists():
            self.recent_files.add(self.path)

    def load(self, path: Path, force_lock: bool = False) -> Record:
        """Carga un registro desde disco y lo deja como activo adquiriendo su lock."""
        resolved_path = Path(path).resolve()

        target_lock = FileLockManager(resolved_path)
        is_locked, existing_info = target_lock.is_lock_active()
        if is_locked and not force_lock and existing_info is not None:
            raise FileLockedError(
                f"El archivo '{resolved_path.name}' está abierto en otra instancia de Study Timetrial "
                f"(PID: {existing_info.pid}, Equipo: {existing_info.hostname})."
            )

        self.lock_manager.set_target(resolved_path)
        self.lock_manager.acquire(force=True)

        record = self.read(resolved_path)
        self.path = resolved_path
        self.watcher.set_path(resolved_path)
        self.recent_files.add(resolved_path)
        return record

    def read(self, path: Path) -> Record:
        """Lee un registro sin cambiar el archivo activo y migra notas/comentarios a Markdown si es necesario."""
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema_version") != 1:
            from infrastructure.compatibility import migrate_raw_record_dict
            data, _, _ = migrate_raw_record_dict(data, target_version=1)
        record = Record.from_dict(data)
        from infrastructure.compatibility import migrate_record_notes_to_markdown
        migrate_record_notes_to_markdown(record)
        return record

    def close(self) -> None:
        """Cierra el archivo activo y libera su archivo de bloqueo."""
        self.lock_manager.release()
        self.lock_manager.set_target(None)
        self.watcher.set_path(None)
        self.path = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass