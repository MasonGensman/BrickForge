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
    """Displays and searches available LEGO bricks."""

    brick_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.database = BrickDatabase()

        # Complete brick list
        self._all_bricks: list[Brick] = self.database.all()

        # Currently displayed bricks
        self._visible_bricks: list[Brick] = []

        container = QWidget()
        layout = QVBoxLayout(container)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search bricks...")

        self.brick_list = QListWidget()

        layout.addWidget(self.search)
        layout.addWidget(self.brick_list)

        self.setWidget(container)

        self.populate(self._all_bricks)

        self.search.textChanged.connect(self.filter_bricks)
        self.brick_list.currentRowChanged.connect(self.on_row_changed)

    def populate(self, bricks: list[Brick]):

        self._visible_bricks = bricks

        self.brick_list.clear()

        for brick in bricks:
            self.brick_list.addItem(str(brick))

    def filter_bricks(self, text: str):

        text = text.lower().strip()

        if not text:
            self.populate(self._all_bricks)
            return

        filtered = [
            brick
            for brick in self._all_bricks
            if text in brick.name.lower()
            or text in brick.part_number.lower()
            or text in brick.category.lower()
            or text in brick.color.lower()
        ]

        self.populate(filtered)

    def on_row_changed(self, row: int):

        if row < 0:
            return

        if row >= len(self._visible_bricks):
            return

        self.brick_selected.emit(self._visible_bricks[row])