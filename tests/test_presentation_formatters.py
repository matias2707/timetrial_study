"""Pruebas de los adaptadores de formato usados por la interfaz."""

import unittest

from presentation.presentation_formatters import format_milliseconds, parse_milliseconds, timer_markup


class PresentationFormatterTests(unittest.TestCase):
    """Verifica conversiones de tiempo sin iniciar Qt."""

    def test_format_and_parse_are_compatible(self) -> None:
        value = 3_726_005

        self.assertEqual(format_milliseconds(value), "01:02:06:005")
        self.assertEqual(parse_milliseconds(format_milliseconds(value)), value)

    def test_parse_accepts_compact_time(self) -> None:
        self.assertEqual(parse_milliseconds("02:345"), 2_345)
        self.assertIn("<span", timer_markup(2_345))

    def test_parse_rejects_invalid_ranges(self) -> None:
        with self.assertRaises(ValueError):
            parse_milliseconds("01:60:000")


if __name__ == "__main__":
    unittest.main()
