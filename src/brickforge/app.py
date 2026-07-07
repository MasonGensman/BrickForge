"""
BrickForge Application

Creates and starts the Qt application.
"""

import sys

from PySide6.QtWidgets import QApplication

from brickforge.ui.main_window import MainWindow
from brickforge.ui.resources.theme import DARK_THEME


def run() -> None:
    """Start the BrickForge application."""

    app = QApplication(sys.argv)

    # Apply the global application theme
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())