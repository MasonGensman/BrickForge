"""
StudWorks Application

Creates and starts the Qt application.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from brickforge._version import APP_NAME, display_version
from brickforge.ui.main_window import MainWindow
from brickforge.ui.resources.theme import DARK_THEME

_SPLASH_SIZE = (480, 280)
_SPLASH_BACKGROUND = "#252526"
_SPLASH_NAME_COLOR = "#F3F3F3"
_SPLASH_VERSION_COLOR = "#9CDCFE"


def _build_splash_screen() -> QSplashScreen:
    """
    A lightweight, self-drawn splash screen (no external image asset
    needed) showing the application name and Preview version while
    MainWindow does its real startup work (catalog loading, GL setup).
    """

    width, height = _SPLASH_SIZE

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(_SPLASH_BACKGROUND))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    name_font = QFont()
    name_font.setPointSize(28)
    name_font.setBold(True)

    painter.setFont(name_font)
    painter.setPen(QColor(_SPLASH_NAME_COLOR))
    painter.drawText(
        pixmap.rect().adjusted(0, -20, 0, -20),
        Qt.AlignCenter,
        APP_NAME,
    )

    version_font = QFont()
    version_font.setPointSize(14)

    painter.setFont(version_font)
    painter.setPen(QColor(_SPLASH_VERSION_COLOR))
    painter.drawText(
        pixmap.rect().adjusted(0, 40, 0, 40),
        Qt.AlignCenter,
        display_version(),
    )

    painter.end()

    return QSplashScreen(pixmap)


def run() -> None:
    """Start the StudWorks application."""

    app = QApplication(sys.argv)

    # Apply the global application theme
    app.setStyleSheet(DARK_THEME)

    splash = _build_splash_screen()
    splash.show()
    app.processEvents()

    window = MainWindow()
    window.show()

    splash.finish(window)

    sys.exit(app.exec())
