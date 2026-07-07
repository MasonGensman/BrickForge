from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QDockWidget


class PropertiesWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        label = QLabel(
            "No brick selected.\n\n"
            "Select a brick from the library\n"
            "or click one in the viewport."
        )

        label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        label.setContentsMargins(10, 10, 10, 10)

        self.setWidget(label)