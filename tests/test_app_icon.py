"""Pruebas del icono y recursos de identidad visual de la aplicación."""

import os
from pathlib import Path
import unittest

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import QApplication

import main


class AppIconTests(unittest.TestCase):
    """Verifica la existencia, resoluciones y carga del icono de la aplicación."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_icon_assets_exist(self) -> None:
        media_dir = Path("presentation/media")
        ico_file = media_dir / "app_icon.ico"
        png_file = media_dir / "app_icon.png"

        self.assertTrue(ico_file.exists(), "app_icon.ico debe existir en presentation/media")
        self.assertTrue(png_file.exists(), "app_icon.png debe existir en presentation/media")

    def test_ico_contains_multiple_resolutions(self) -> None:
        ico_file = Path("presentation/media/app_icon.ico")
        icon = QIcon(str(ico_file))

        self.assertFalse(icon.isNull(), "app_icon.ico debe ser un QIcon válido")
        sizes = icon.availableSizes()
        self.assertGreaterEqual(len(sizes), 4, "app_icon.ico debe contener múltiples resoluciones")

        # Comprobar tamaños clave para Windows
        expected_sizes = [QSize(16, 16), QSize(32, 32), QSize(48, 48), QSize(256, 256)]
        for expected in expected_sizes:
            self.assertIn(expected, sizes, f"El icono debe incluir la resolución {expected.width()}x{expected.height()}")

    def test_png_has_valid_dimensions_and_alpha(self) -> None:
        png_file = Path("presentation/media/app_icon.png")
        image = QImage(str(png_file))

        self.assertFalse(image.isNull(), "app_icon.png debe ser una imagen válida")
        self.assertGreaterEqual(image.width(), 256)
        self.assertGreaterEqual(image.height(), 256)
        self.assertTrue(image.hasAlphaChannel(), "app_icon.png debe tener canal alfa (transparencia)")

    def test_main_get_app_icon_returns_valid_icon(self) -> None:
        icon = main._get_app_icon()
        self.assertFalse(icon.isNull(), "_get_app_icon() debe devolver un icono cargado")


if __name__ == "__main__":
    unittest.main()
