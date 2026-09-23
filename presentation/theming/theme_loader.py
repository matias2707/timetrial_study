"""Carga y validación dinámica de plantillas y temas visuales desde archivos JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from presentation.theme_tokens import (
    DARK_TOKENS,
    LIGHT_TOKENS,
    THEME_DARK,
    THEME_LIGHT,
    THEME_TOKENS_MAP,
    ThemeTokens,
)

THEMES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "themes"


def _dict_to_tokens(data: dict[str, Any], fallback: ThemeTokens) -> ThemeTokens:
    """Convierte un diccionario JSON a una instancia ThemeTokens usando fallback para campos faltantes."""
    fields = {}
    fallback_dict = fallback.__dict__
    for key, default_val in fallback_dict.items():
        fields[key] = data.get(key, default_val)
    return ThemeTokens(**fields)


def load_theme_from_file(file_path: Path) -> ThemeTokens | None:
    """Carga un tema visual desde un archivo .json."""
    if not file_path.is_file():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        is_dark = data.get("is_dark", True)
        fallback = DARK_TOKENS if is_dark else LIGHT_TOKENS
        return _dict_to_tokens(data, fallback)
    except Exception:
        return None


def validate_theme_dict(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Valida la estructura de un tema JSON según el contrato requerido.
    Retorna (es_valido, lista_errores).
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return False, ["El tema debe ser un objeto JSON (dict)."]

    if "name" not in data or not isinstance(data["name"], str) or not data["name"].strip():
        errors.append("Falta el campo obligatorio 'name' (string no vacío).")
    if "is_dark" not in data or not isinstance(data["is_dark"], bool):
        errors.append("Falta el campo obligatorio 'is_dark' (booleano).")

    core_keys = [
        "bg_app", "bg_dialog", "bg_surface", "bg_card",
        "text_primary", "text_secondary", "text_muted",
        "border_subtle", "border_strong", "toolbar_primary_bg",
        "hero_start_bg",
    ]
    for k in core_keys:
        val = data.get(k)
        if val is None or not isinstance(val, str) or not val.startswith("#"):
            errors.append(f"El token cromático '{k}' es requerido y debe ser un valor hexadecimal válido.")

    return (len(errors) == 0, errors)


def get_available_themes(themes_dir: Path | None = None) -> list[str]:
    """Descubre y retorna la lista de nombres de temas disponibles."""
    target_dir = themes_dir or THEMES_DIR
    themes = [THEME_LIGHT, THEME_DARK]
    if target_dir.is_dir():
        for file in sorted(target_dir.glob("*.json")):
            if file.name.endswith(".schema.json") or file.name.startswith("."):
                continue
            stem = file.stem.lower()
            if stem not in themes:
                themes.append(stem)
    return themes


def get_theme_tokens(theme: str, themes_dir: Path | None = None) -> ThemeTokens:
    """Obtiene los ThemeTokens para un tema dado, consultando data/themes/ con fallback seguro."""
    theme_key = (theme or "").strip().lower()

    target_dir = themes_dir or THEMES_DIR
    json_path = target_dir / f"{theme_key}.json"

    if json_path.is_file():
        loaded = load_theme_from_file(json_path)
        if loaded is not None:
            return loaded

    # Fallback al mapa canónico en memoria
    return THEME_TOKENS_MAP.get(theme_key, LIGHT_TOKENS)
