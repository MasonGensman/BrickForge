from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QListWidget,
    QMainWindow,
    QStatusBar,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setup_window()
        self.create_menu()
        self.create_docks()
        self.create_viewport()
        self.create_statusbar()

    def setup_window(self):
        self.setWindowTitle("BrickForge v0.1.0-alpha.1")
        self.resize(1400, 800)

    def create_menu(self):
        menu = self.menuBar()

        menu.addMenu("File")
        menu.addMenu("Edit")
        menu.addMenu("View")
        menu.addMenu("Project")
        menu.addMenu("Help")

    def create_docks(self):
        # -----------------------------
        # Brick Library (Left Dock)
        # -----------------------------
        left = QDockWidget("Brick Library", self)
        left.setMinimumWidth(250)
        left.setAllowedAreas(Qt.LeftDockWidgetArea)

        brick_list = QListWidget()
        left.setWidget(brick_list)

        self.addDockWidget(Qt.LeftDockWidgetArea, left)

        # -----------------------------
        # Properties (Right Dock)
        # -----------------------------
        right = QDockWidget("Properties", self)
        right.setMinimumWidth(250)
        right.setAllowedAreas(Qt.RightDockWidgetArea)

        properties = QLabel(
            "No brick selected.\n\n"
            "Select a brick from the library\n"
            "or click one in the viewport."
        )

        properties.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        properties.setContentsMargins(10, 10, 10, 10)

        right.setWidget(properties)

        self.addDockWidget(Qt.RightDockWidgetArea, right)

    def create_viewport(self):
        viewport = QLabel("3D Viewport\n\n(Coming Soon)")
        viewport.setAlignment(Qt.AlignCenter)

        viewport.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #555555;
            }
        """)

        self.setCentralWidget(viewport)

    def create_statusbar(self):
        status = QStatusBar()

        status.showMessage("Ready")

        self.setStatusBar(status)