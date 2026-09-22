"""Módulo de retrocompatibilidad, migraciones de esquema y copias de seguridad."""

from infrastructure.compatibility.markdown_migrator import (
    convert_plain_text_to_markdown,
    migrate_record_notes_to_markdown,
)
from infrastructure.compatibility.backup_service import (
    create_backup_file,
    restore_backup_file,
)

__all__ = [
    "convert_plain_text_to_markdown",
    "migrate_record_notes_to_markdown",
    "create_backup_file",
    "restore_backup_file",
]
