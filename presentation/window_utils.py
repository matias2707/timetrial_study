"""Utilidades de gestión de ventanas, foco y presencia en la barra de tareas.

Proporciona funciones seguras y desacopladas para garantizar que las ventanas
y diálogos principales aparezcan en primer plano, no pierdan prioridad
y mantengan visibilidad en la barra de tareas de Windows.
"""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QWidget


def get_app_icon() -> QIcon:
    """Obtiene el icono oficial de la aplicación (cronómetro)."""
    media_dir = Path(__file__).resolve().parent / "media"
    ico_path = media_dir / "app_icon.ico"
    png_path = media_dir / "app_icon.png"

    if ico_path.exists():
        return QIcon(str(ico_path))
    if png_path.exists():
        return QIcon(str(png_path))
    return QIcon()


def force_activate_window(widget: QWidget) -> None:
    """Fuerza la activación de la ventana en primer plano y le otorga el foco de entrada.

    En Windows, utiliza las APIs nativas de usuario (BringWindowToTop y SetForegroundWindow)
    para sortear restricciones de z-order y de 'Focus Stealing Prevention'.
    """
    if widget.isMinimized():
        widget.showNormal()

    widget.setWindowState(
        (widget.windowState() & ~Qt.WindowState.WindowMinimized)
        | Qt.WindowState.WindowActive
    )
    widget.raise_()
    widget.activateWindow()

    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = int(widget.winId())
            if hwnd:
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
        except Exception:
            pass


def ensure_dialog_taskbar_presence(dialog: QDialog, icon: QIcon | None = None) -> None:
    """Configura banderas de ventana para garantizar presencia en la barra de tareas.

    Útil cuando un diálogo modal o ventana secundaria se abre como ventana
    independiente de primer nivel.
    """
    dialog.setWindowFlags(
        Qt.WindowType.Window
        | Qt.WindowType.WindowTitleHint
        | Qt.WindowType.WindowSystemMenuHint
        | Qt.WindowType.WindowMinimizeButtonHint
        | Qt.WindowType.WindowCloseButtonHint
    )
    effective_icon = icon if (icon is not None and not icon.isNull()) else get_app_icon()
    if not effective_icon.isNull():
        dialog.setWindowIcon(effective_icon)
