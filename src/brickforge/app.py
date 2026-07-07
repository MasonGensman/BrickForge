import sys

from PySide6.QtWidgets import QApplication

from brickforge.ui.main_window import MainWindow


def run():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())