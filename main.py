"""Punto de entrada estable de Study Timetrial."""

import ctypes
from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from presentation.main_window import MainWindow
from presentation.window_utils import force_activate_window, get_app_icon

# Alias para compatibilidad
_get_app_icon = get_app_icon


def _configure_windows_app_id() -> None:
    """Configura el identificador de modelo de usuario explícito en Windows para la barra de tareas."""
    if sys.platform == "win32":
        try:
            app_id = "study_timetrial.stopwatch.app.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


if __name__ == "__main__":
    _configure_windows_app_id()
    application = QApplication(sys.argv)

    app_icon = get_app_icon()
    if not app_icon.isNull():
        application.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()
    force_activate_window(window)
    sys.exit(application.exec())

