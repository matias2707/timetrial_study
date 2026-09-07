from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models import Record, TimerItem
from storage_service import StorageService
from timer_service import TimerMode, TimerService


@dataclass
class SessionLocation:
    """Ubicación editable del intento actual."""

    section_type: str = "Guía"
    section_number: int = 1
    exercise: int = 1
    inciso: int | None = None


class StudyApplicationService:
    """Coordina los casos de uso de la aplicación sin depender de Qt.

    La interfaz gráfica adapta eventos y valores de widgets a esta fachada.
    Las reglas de sesión, navegación, registro y persistencia permanecen aquí
    para que puedan probarse sin levantar una ventana.
    """

    def __init__(self, storage: StorageService | None = None, timer: TimerService | None = None) -> None:
        self.storage = storage or StorageService()
        self.timer = timer or TimerService()
        self.record = self.storage.create_automatic()
        self.location = SessionLocation()
        self.pending_comment = ""

    @property
    def is_record_open(self) -> bool:
        return self.storage.is_open

    @property
    def record_path(self) -> Path | None:
        return self.storage.path

    @property
    def mode(self) -> TimerMode:
        return self.timer.mode

    def set_location(self, location: SessionLocation) -> None:
        """Actualiza la ubicación solo cuando no hay una sesión activa."""
        if self.mode is not TimerMode.WAITING:
            return
        self.location = location

    def toggle_session(self, location: SessionLocation | None = None) -> TimerMode:
        """Inicia, pausa o reanuda la sesión y devuelve el modo resultante."""
        if self.mode is TimerMode.WAITING:
            if location is not None:
                self.set_location(location)
            self.timer.start()
        else:
            self.timer.toggle_break()
        return self.mode

    def stop_session(self) -> None:
        """Descarta el intento en curso sin crear un registro."""
        self.timer.reset()

    def set_comment(self, comment: str) -> None:
        """Define el comentario que se guardará con el intento actual."""
        self.pending_comment = comment.strip()

    def finish_item(self, completed: bool) -> bool:
        """Guarda el intento activo y reinicia el cronómetro."""
        if self.mode is TimerMode.WAITING:
            return False

        exercise_ms, break_ms = self.timer.snapshot()
        self.record.items.append(
            TimerItem(
                section_type=self.location.section_type,
                section_number=self.location.section_number,
                exercise=self.location.exercise,
                inciso=self.location.inciso,
                exercise_time_ms=exercise_ms,
                break_time_ms=break_ms,
                completed=completed,
                comment=self.pending_comment,
            )
        )
        self.save()
        self.timer.reset()
        self.pending_comment = ""
        return True

    def navigate(self, target: str) -> bool:
        """Finaliza el intento y mueve la ubicación en una dirección válida."""
        if target == "previous_inciso" and self.location.inciso is None:
            return False
        if target == "previous_exercise" and self.location.exercise <= 1:
            return False
        if target == "previous_section" and self.location.section_number <= 1:
            return False

        self.finish_item(True)
        if target == "next_inciso":
            self.location.inciso = (self.location.inciso or 0) + 1
        elif target == "previous_inciso":
            self.location.inciso = self.location.inciso - 1 or None
        elif target == "next_exercise":
            self.location.exercise += 1
            self.location.inciso = None
        elif target == "previous_exercise":
            self.location.exercise -= 1
            self.location.inciso = None
        elif target == "next_section":
            self.location.section_number += 1
            self.location.exercise = 1
            self.location.inciso = None
        elif target == "previous_section":
            self.location.section_number -= 1
            self.location.exercise = 1
            self.location.inciso = None
        else:
            raise ValueError(f"Dirección de navegación desconocida: {target}")
        return True

    def save(self) -> None:
        self.storage.save(self.record)

    def save_as(self, path: Path) -> None:
        self.storage.save(self.record, path)
        self.record.record_name = path.stem
        self.save()

    def load(self, path: Path) -> None:
        self.record = self.storage.load(path)

    def import_items(self, path: Path, item_indexes: list[int]) -> int:
        """Añade copias de los items seleccionados sin cambiar el archivo activo."""
        imported_record = self.storage.read(path)
        selected_items = [imported_record.items[index] for index in item_indexes]
        for item in selected_items:
            item_data = item.to_dict()
            item_data["id"] = None
            self.record.items.append(TimerItem.from_dict(item_data))

        if selected_items:
            self.save()
        return len(selected_items)

    def rename(self, path: Path) -> None:
        if self.storage.path is None:
            raise ValueError("No hay un archivo activo")
        self.storage.path.rename(path)
        self.storage.path = path
        self.record.record_name = path.stem
        self.save()

    def close_record(self) -> None:
        self.storage.path = None
        self.record = Record()

    def ordered_items(self) -> list[TimerItem]:
        return sorted(self.record.items, key=lambda item: item.created_at)

    def add_item(self, item: TimerItem) -> None:
        self.record.items.append(item)
        self.save()

    def replace_item(self, current: TimerItem, replacement: TimerItem) -> None:
        self.record.items[self.record.items.index(current)] = replacement
        self.save()

    def reset_item(self, item: TimerItem) -> None:
        item.exercise_time_ms = 0
        item.break_time_ms = 0
        self.save()

    def update_comment(self, item: TimerItem, comment: str) -> None:
        """Actualiza el comentario de un item ya guardado."""
        item.comment = comment.strip()
        self.save()

    def delete_item(self, item: TimerItem) -> None:
        self.record.items.remove(item)
        self.save()