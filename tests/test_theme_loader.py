"""Pruebas unitarias para el cargador dinámico de temas JSON."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from presentation.theme_tokens import DARK_TOKENS, LIGHT_TOKENS
from presentation.theming.theme_loader import (
    THEMES_DIR,
    get_available_themes,
    get_theme_tokens,
    load_theme_from_file,
    validate_theme_dict,
)


class TestThemeLoader(unittest.TestCase):
    """Verifica el descubrimiento y parseo dinámico de temas JSON."""

    def test_available_themes_contains_light_and_dark_and_excludes_schema(self) -> None:
        themes = get_available_themes()
        self.assertIn("light", themes)
        self.assertIn("dark", themes)
        self.assertNotIn("theme.schema", themes)

    def test_theme_schema_file_exists_and_is_valid_json(self) -> None:
        schema_path = THEMES_DIR / "theme.schema.json"
        self.assertTrue(schema_path.is_file())
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("$schema", data)
        self.assertIn("required", data)
        self.assertIn("properties", data)

    def test_validate_theme_dict(self) -> None:
        valid_theme = {
            "name": "test_theme",
            "is_dark": True,
            "bg_app": "#112233",
            "bg_dialog": "#112233",
            "bg_surface": "#112233",
            "bg_card": "#112233",
            "text_primary": "#ffffff",
            "text_secondary": "#cccccc",
            "text_muted": "#888888",
            "border_subtle": "#223344",
            "border_strong": "#334455",
            "toolbar_primary_bg": "#059669",
            "hero_start_bg": "#059669",
        }
        is_valid, errors = validate_theme_dict(valid_theme)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        invalid_theme = {"name": "", "is_dark": "not_a_bool"}
        is_valid, errors = validate_theme_dict(invalid_theme)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    def test_load_nord_theme(self) -> None:
        tokens = get_theme_tokens("nord")
        self.assertEqual(tokens.name, "nord")
        self.assertTrue(tokens.is_dark)
        self.assertEqual(tokens.bg_app, "#2e3440")

    def test_fallback_for_non_existent_theme(self) -> None:
        tokens = get_theme_tokens("tema_inexistente_123")
        self.assertEqual(tokens.name, LIGHT_TOKENS.name)

    def test_load_theme_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "custom.json"
            data = {
                "name": "custom",
                "is_dark": True,
                "mode_comment": "/* custom */",
                "bg_app": "#123456",
            }
            file_path.write_text(json.dumps(data), encoding="utf-8")
            tokens = load_theme_from_file(file_path)
            self.assertIsNotNone(tokens)
            assert tokens is not None
            self.assertEqual(tokens.name, "custom")
            self.assertEqual(tokens.bg_app, "#123456")
            # Los campos no especificados deben heredar de DARK_TOKENS
            self.assertEqual(tokens.bg_dialog, DARK_TOKENS.bg_dialog)


if __name__ == "__main__":
    unittest.main()
