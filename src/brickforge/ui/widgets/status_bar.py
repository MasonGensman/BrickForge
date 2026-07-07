from PySide6.QtWidgets import QStatusBar


class BrickForgeStatusBar(QStatusBar):
    def __init__(self):
        super().__init__()

        self.showMessage("Ready")