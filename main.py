"""Punto de entrada estable de Study Timetrial."""

import sys

from PySide6.QtWidgets import QApplication

from presentation.main_window import MainWindow


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())
