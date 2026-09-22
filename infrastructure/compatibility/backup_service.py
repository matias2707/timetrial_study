from __future__ import annotations

"""Gestión de copias de seguridad de archivos de registro y recuperación."""

import shutil
from datetime import datetime
from pathlib import Path


def create_backup_file(
    file_path: Path | str,
    backup_dir: Path | str | None = None,
    reason: str = "",
) -> Path | None:
    """Crea una copia de respaldo fechada de un archivo de registro antes de migraciones o sobrescrituras.

    Si no se especifica backup_dir, se crea en una carpeta '.backups' adyacente al archivo original.
    Devuelve la ruta del archivo de backup generado o None si el archivo de origen no existe.
    """
    src = Path(file_path)
    if not src.exists() or not src.is_file():
        return None

    if backup_dir is not None:
        target_folder = Path(backup_dir)
    else:
        target_folder = src.parent / ".backups"

    target_folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reason_part = f"_{reason}" if reason else ""
    backup_filename = f"{src.stem}_backup_{timestamp}{reason_part}{src.suffix}"
    dest = target_folder / backup_filename

    shutil.copy2(src, dest)
    return dest


def restore_backup_file(backup_path: Path | str, target_path: Path | str) -> bool:
    """Restaura un archivo desde una copia de respaldo."""
    src = Path(backup_path)
    dest = Path(target_path)
    if not src.exists() or not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def list_backups_for_file(file_path: Path | str) -> list[Path]:
    """Lista las copias de seguridad ordenadas cronológicamente para un archivo dado."""
    src = Path(file_path)
    backup_folder = src.parent / ".backups"
    if not backup_folder.exists():
        return []
    pattern = f"{src.stem}_backup_*{src.suffix}"
    backups = list(backup_folder.glob(pattern))
    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return backups
