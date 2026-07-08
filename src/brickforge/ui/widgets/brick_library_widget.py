from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QListWidget

from brickforge.services.brick_database import BrickDatabase


class BrickLibraryWidget(QDockWidget):
    """Displays the available bricks."""

    brick_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.database = BrickDatabase()
        self.bricks = self.database.all()

        self.brick_list = QListWidget()
        self.setWidget(self.brick_list)

        self.populate_list()

        self.brick_list.currentRowChanged.connect(
            self.on_selection_changed
        )

    def populate_list(self):
        """Fill the list with available bricks."""

        self.brick_list.clear()

        for brick in self.bricks:
            self.brick_list.addItem(
                f"{brick.part_number} - {brick.name}"
            )

    def on_selection_changed(self, index):
        """Emit the currently selected brick."""

        if 0 <= index < len(self.bricks):
            self.brick_selected.emit(self.bricks[index])