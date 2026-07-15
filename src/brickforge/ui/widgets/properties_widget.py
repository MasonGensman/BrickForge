from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QDockWidget

from brickforge.models.part_definition import BrickDefinition


class PropertiesWidget(QDockWidget):

    def __init__(self, parent=None):

        super().__init__("Properties", parent)

        self.setMinimumWidth(250)
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self.label = QLabel()

        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label.setContentsMargins(10, 10, 10, 10)

        self.setWidget(self.label)

        self.clear()

    def clear(self):

        self.label.setText(
            "No brick selected.\n\n"
            "Select a brick from the library."
        )

    def display_brick(self, brick: BrickDefinition):

        colors = (
            ", ".join(
                str(code) for code in brick.available_colors
            )
            if brick.available_colors
            else "Unknown"
        )

        self.label.setText(
            f"""
Name:
{brick.name}

Part Number:
{brick.part_number}

Category:
{brick.category}

Dimensions:
{brick.stud_width} x {brick.stud_length} studs

Available Colors:
{colors}
"""
        )