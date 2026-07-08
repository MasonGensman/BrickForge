from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLineEdit


class SearchBar(QLineEdit):
    search_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setPlaceholderText("Search bricks...")

        self.textChanged.connect(self.search_changed.emit)