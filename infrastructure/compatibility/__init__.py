"""Módulo de retrocompatibilidad, migraciones de esquema y copias de seguridad."""

from infrastructure.compatibility.markdown_migrator import (
    convert_plain_text_to_markdown,
    migrate_record_notes_to_markdown,
)
from infrastructure.compatibility.backup_service import (
    create_backup_file,
    restore_backup_file,
)
from infrastructure.compatibility.migrations import (
    CURRENT_SCHEMA_VERSION,
    migrate_file_if_needed,
    migrate_raw_record_dict,
)

__all__ = [
    "convert_plain_text_to_markdown",
    "migrate_record_notes_to_markdown",
    "create_backup_file",
    "restore_backup_file",
    "CURRENT_SCHEMA_VERSION",
    "migrate_raw_record_dict",
    "migrate_file_if_needed",
]
