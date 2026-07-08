from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QListWidget,
    QWidget,
    QVBoxLayout,
)

from brickforge.services.brick_database import BrickDatabase
from brickforge.ui.widgets.search_bar import SearchBar


class BrickLibraryWidget(QDockWidget):
    brick_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.database = BrickDatabase()
        self.bricks = self.database.all()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        self.search = SearchBar()
        self.brick_list = QListWidget()

        layout.addWidget(self.search)
        layout.addWidget(self.brick_list)

        self.setWidget(container)

        self.populate_list()

        self.search.search_changed.connect(self.filter_bricks)
        self.brick_list.currentRowChanged.connect(self.on_selection_changed)

    def populate_list(self):
        self.brick_list.clear()

        for brick in self.bricks:
            self.brick_list.addItem(f"{brick.part_number} - {brick.name}")

    def filter_bricks(self, text):
        text = text.lower()

        self.brick_list.clear()

        self.filtered_bricks = []

        for brick in self.bricks:
            if (
                text in brick.name.lower()
                or text in brick.part_number.lower()
            ):
                self.filtered_bricks.append(brick)
                self.brick_list.addItem(
                    f"{brick.part_number} - {brick.name}"
                )

    def on_selection_changed(self, index):
        if hasattr(self, "filtered_bricks"):
            bricks = self.filtered_bricks
        else:
            bricks = self.bricks

        if 0 <= index < len(bricks):
            self.brick_selected.emit(bricks[index])