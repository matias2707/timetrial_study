"""Punto de entrada estable de Study Timetrial."""

import ctypes
from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from presentation.main_window import MainWindow


def _configure_windows_app_id() -> None:
    """Configura el identificador de modelo de usuario explícito en Windows para la barra de tareas."""
    if sys.platform == "win32":
        try:
            app_id = "study_timetrial.stopwatch.app.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def _get_app_icon() -> QIcon:
    """Obtiene el icono oficial de la aplicación (cronómetro)."""
    media_dir = Path(__file__).resolve().parent / "presentation" / "media"
    ico_path = media_dir / "app_icon.ico"
    png_path = media_dir / "app_icon.png"

    if ico_path.exists():
        return QIcon(str(ico_path))
    if png_path.exists():
        return QIcon(str(png_path))
    return QIcon()


if __name__ == "__main__":
    _configure_windows_app_id()
    application = QApplication(sys.argv)

    app_icon = _get_app_icon()
    if not app_icon.isNull():
        application.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()
    sys.exit(application.exec())

