"""
BrickForge Viewport Widget
Renderer V2
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brickforge.render.renderer import Renderer


class ViewportWidget(QOpenGLWidget):
    """Main OpenGL viewport."""

    #
    # Emits the picked SceneBrick.id, or None for a click on empty
    # space -- MainWindow owns SelectionManager and reacts to this,
    # matching BrickLibraryWidget.brick_selected's existing shape
    # (widgets emit, MainWindow connects and reacts; a widget never
    # manipulates MainWindow state directly). Package_027.
    #
    brick_clicked = Signal(object)

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self.renderer = Renderer()

        #
        # Create timer but don't start it until
        # the OpenGL context is initialized.
        #
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)

        self.last_mouse_position = None

    def initializeGL(self):

        self.renderer.initialize()

        #
        # Safe to begin rendering.
        #
        self.timer.start()

    def resizeGL(
        self,
        width,
        height,
    ):

        self.renderer.resize(
            width,
            height,
        )

    def paintGL(self):

        if not self.isValid():
            return

        self.renderer.render()

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:

            brick_id = self.renderer.pick(
                event.position().x(),
                event.position().y(),
            )

            self.brick_clicked.emit(brick_id)

            return

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

        delta = (
            event.position()
            - self.last_mouse_position
        )

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

        #
        # Redraw after camera movement.
        #
        self.update()

    def wheelEvent(self, event):

        self.renderer.camera.zoom(
            -event.angleDelta().y() / 240.0
        )

        #
        # Redraw after zoom.
        #
        self.update()

    def keyPressEvent(
        self,
        event: QKeyEvent,
    ):

        if event.key() == Qt.Key_F:

            self.renderer.camera.reset()

            #
            # Redraw after reset.
            #
            self.update()

        super().keyPressEvent(event)

    def closeEvent(self, event):

        #
        # Stop rendering before the widget
        # is destroyed.
        #
        self.timer.stop()

        super().closeEvent(event)