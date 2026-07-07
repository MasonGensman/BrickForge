from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget,
    QListWidget,
    QLineEdit,
    QWidget,
    QVBoxLayout,
)

from brickforge.models.brick import Brick
from brickforge.services.brick_database import BrickDatabase


class BrickLibraryWidget(QDockWidget):
    """Displays available LEGO bricks."""

    brick_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.database = BrickDatabase()

        self._bricks: list[Brick] = []

        container = QWidget()
        layout = QVBoxLayout(container)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search bricks...")

        self.brick_list = QListWidget()

        layout.addWidget(self.search)
        layout.addWidget(self.brick_list)

        self.setWidget(container)

        self.populate()

        self.brick_list.currentRowChanged.connect(self.on_row_changed)

    def populate(self):
        self._bricks = self.database.all()

        self.brick_list.clear()

        for brick in self._bricks:
            self.brick_list.addItem(str(brick))

    def on_row_changed(self, row: int):
        if row < 0:
            return

        brick = self._bricks[row]

        self.brick_selected.emit(brick)