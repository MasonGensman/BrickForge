from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from brickforge.ui.widgets import (
    BrickLibraryWidget,
    BrickForgeStatusBar,
    PropertiesWidget,
    ViewportWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setup_window()
        self.create_menu()
        self.create_widgets()

    def setup_window(self):
        self.setWindowTitle("BrickForge v0.1.0")
        self.resize(1400, 800)

    def create_menu(self):
        menu = self.menuBar()

        menu.addMenu("File")
        menu.addMenu("Edit")
        menu.addMenu("View")
        menu.addMenu("Project")
        menu.addMenu("Help")

    def create_widgets(self):
        # Left Dock
        self.library = BrickLibraryWidget(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library)

        # Right Dock
        self.properties = PropertiesWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)

        # Center Viewport
        self.viewport = ViewportWidget()
        self.setCentralWidget(self.viewport)

        # Status Bar
        self.status = BrickForgeStatusBar()
        self.setStatusBar(self.status)