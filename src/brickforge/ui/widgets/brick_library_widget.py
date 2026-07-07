from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QListWidget


class BrickLibraryWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Brick Library", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

        self.brick_list = QListWidget()

        self.setWidget(self.brick_list)