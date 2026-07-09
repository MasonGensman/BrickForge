"""
BrickForge Viewport Widget
"""

from PySide6.QtCore import QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brickforge.render.renderer import Renderer


class ViewportWidget(QOpenGLWidget):
    """Main 3D viewport."""

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)

        self.renderer = Renderer()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS

    def initializeGL(self):
        self.renderer.initialize()

    def resizeGL(self, width, height):
        self.renderer.resize(width, height)

    def paintGL(self):
        self.renderer.render()