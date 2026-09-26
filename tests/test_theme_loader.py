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

    def test_all_catalog_skins_exist_in_available_themes(self) -> None:
        themes = get_available_themes()
        expected_skins = [
            "sakura", "winter", "spring", "bamboo", "midnight",
            "classic_blue", "peach_fuzz", "marsala", "emerald", "illuminating",
            "black_sakura", "vampyr", "halloween",
        ]
        for skin in expected_skins:
            self.assertIn(skin, themes, f"El skin '{skin}' no se encontró en temas disponibles.")

    def test_all_json_themes_in_directory_are_valid(self) -> None:
        for file in THEMES_DIR.glob("*.json"):
            if file.name.endswith(".schema.json") or file.name.startswith("."):
                continue
            with self.subTest(theme_file=file.name):
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                is_valid, errors = validate_theme_dict(data)
                self.assertTrue(is_valid, f"Tema {file.name} inválido: {errors}")
                self.assertEqual(len(errors), 0)

    def test_requested_skins_luminance_and_properties(self) -> None:
        # Skins temáticos y sus efectos
        sakura = get_theme_tokens("sakura")
        self.assertFalse(sakura.is_dark)
        self.assertEqual(sakura.bg_app, "#f8f1f3")
        self.assertEqual(sakura.effect, "sakura")

        winter = get_theme_tokens("winter")
        self.assertTrue(winter.is_dark)
        self.assertEqual(winter.bg_app, "#090e17")
        self.assertEqual(winter.effect, "snow")

        spring = get_theme_tokens("spring")
        self.assertFalse(spring.is_dark)
        self.assertEqual(spring.bg_app, "#eff5ec")
        self.assertEqual(spring.effect, "leaves")

        bamboo = get_theme_tokens("bamboo")
        self.assertFalse(bamboo.is_dark)
        self.assertEqual(bamboo.bg_app, "#f3ede1")
        self.assertEqual(bamboo.effect, "bamboo")

        midnight = get_theme_tokens("midnight")
        self.assertTrue(midnight.is_dark)
        self.assertEqual(midnight.bg_app, "#05070e")
        self.assertEqual(midnight.effect, "stars")

        black_sakura = get_theme_tokens("black_sakura")
        self.assertTrue(black_sakura.is_dark)
        self.assertEqual(black_sakura.bg_app, "#0c0a0e")
        self.assertEqual(black_sakura.effect, "sakura")

        vampyr = get_theme_tokens("vampyr")
        self.assertTrue(vampyr.is_dark)
        self.assertEqual(vampyr.bg_app, "#080405")
        self.assertEqual(vampyr.effect, "vampyr")

        halloween = get_theme_tokens("halloween")
        self.assertTrue(halloween.is_dark)
        self.assertEqual(halloween.bg_app, "#0c0907")
        self.assertEqual(halloween.effect, "halloween")

    def test_pantone_skins_luminance_and_properties(self) -> None:
        # 5 skins inspirados en Pantone
        classic_blue = get_theme_tokens("classic_blue")
        self.assertTrue(classic_blue.is_dark)
        self.assertEqual(classic_blue.bg_app, "#09111e")

        peach_fuzz = get_theme_tokens("peach_fuzz")
        self.assertFalse(peach_fuzz.is_dark)
        self.assertEqual(peach_fuzz.bg_app, "#f8efe6")

        marsala = get_theme_tokens("marsala")
        self.assertTrue(marsala.is_dark)
        self.assertEqual(marsala.bg_app, "#140a0e")

        emerald = get_theme_tokens("emerald")
        self.assertTrue(emerald.is_dark)
        self.assertEqual(emerald.bg_app, "#040e0a")

        illuminating = get_theme_tokens("illuminating")
        self.assertTrue(illuminating.is_dark)
        self.assertEqual(illuminating.bg_app, "#131518")

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
