from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class ViewportWidget(QLabel):
    def __init__(self):
        super().__init__("3D Viewport\n\n(Coming Soon)")

        self.setAlignment(Qt.AlignCenter)

        self.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #555555;
            }
        """)