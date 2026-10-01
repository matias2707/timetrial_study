from __future__ import annotations

"""Políticas y estrategias de guardado de la aplicación."""

from enum import Enum


class SavePolicy(str, Enum):
    """Política de guardado configurada en la aplicación."""

    AUTO_IMMEDIATE = "auto_immediate"  # Guarda en disco tras cada mutación (comportamiento ágil)
    AUTO_PERIODIC = "auto_periodic"    # Guarda periódicamente cada N segundos solo si is_dirty=True
    MANUAL = "manual"                  # Guarda exclusivamente a petición explícita (Ctrl+S o salir)
