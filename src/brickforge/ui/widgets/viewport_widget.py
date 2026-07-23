"""
BrickForge Viewport Widget
Renderer V2
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brickforge.render.renderer import Renderer
from brickforge.tools.active_tool_manager import ActiveToolManager


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

    #
    # Emits a ToolResult once an editing tool's drag completes with a
    # real change -- MainWindow owns the Transform package and the
    # scene activation helper, and reacts to this the same way it
    # reacts to brick_clicked. Replaces the separate brick_moved/
    # brick_rotated signals from Packages 029-030, which had grown
    # near-identical MainWindow handlers (Package_031).
    #
    brick_transformed = Signal(object)

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self.renderer = Renderer()
        self.active_tool_manager = ActiveToolManager()

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

        brick_id = self.renderer.pick(
            event.position().x(),
            event.position().y(),
        )

        if self.active_tool_manager.try_begin(
            event.button(),
            self.renderer,
            brick_id,
            event.position().x(),
            event.position().y(),
        ):
            return

        if event.button() == Qt.LeftButton:

            self.brick_clicked.emit(brick_id)

            return

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = event.position()

    def mouseReleaseEvent(self, event):

        if self.active_tool_manager.is_dragging:

            result = self.active_tool_manager.finish(
                self.renderer,
                event.position().x(),
                event.position().y(),
            )

            if result is not None:
                self.brick_transformed.emit(result)

            self.update()

            return

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = None

    def mouseMoveEvent(self, event):

        if self.active_tool_manager.is_dragging:

            self.active_tool_manager.update(
                self.renderer,
                event.position().x(),
                event.position().y(),
            )

            self.update()

            return

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
