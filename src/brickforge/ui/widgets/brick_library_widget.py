from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QListWidget,
    QLineEdit,
    QWidget,
    QVBoxLayout,
)

from brickforge.services.brick_database import BrickDatabase


class BrickLibraryWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.database = BrickDatabase()

        container = QWidget()
        layout = QVBoxLayout(container)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search bricks...")

        self.brick_list = QListWidget()

        layout.addWidget(self.search)
        layout.addWidget(self.brick_list)

        self.setWidget(container)

        self.populate()

    def populate(self):
        self.brick_list.clear()

        for brick in self.database.all():
            self.brick_list.addItem(
                f"{brick.part_number} - {brick.name}"
            )