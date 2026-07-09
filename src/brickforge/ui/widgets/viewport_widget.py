"""
BrickForge Viewport Widget
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brickforge.render.renderer import Renderer


class ViewportWidget(QOpenGLWidget):
    """Main 3D viewport."""

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self.renderer = Renderer()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

        self.last_mouse_position = None

    def initializeGL(self):
        self.renderer.initialize()

    def resizeGL(self, width, height):
        self.renderer.resize(width, height)

    def paintGL(self):
        self.renderer.render()

    def mousePressEvent(self, event):

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = event.position()

    def mouseReleaseEvent(self, event):

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = None

    def mouseMoveEvent(self, event):

        if self.last_mouse_position is None:
            return

        delta = event.position() - self.last_mouse_position

        if event.buttons() & Qt.RightButton:

            self.renderer.camera.orbit(
                delta.x(),
                delta.y(),
            )

        elif event.buttons() & Qt.MiddleButton:

            self.renderer.camera.pan(
                delta.x(),
                delta.y(),
            )

        self.last_mouse_position = event.position()

        self.update()

    def wheelEvent(self, event):

        self.renderer.camera.zoom(
            -event.angleDelta().y() / 240.0
        )

        self.update()

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ):

        if event.key() == Qt.Key_F:

            self.renderer.camera.reset()

            self.update()

        super().keyPressEvent(event)