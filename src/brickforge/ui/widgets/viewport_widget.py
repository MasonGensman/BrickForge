"""
BrickForge Viewport Widget
Renderer V2
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from brickforge.render.renderer import Renderer, ScenePreview
from brickforge.tools.move_tool import MoveTool


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
    # Emits (brick_id, new_position) once a brick-drag completes with
    # real movement -- MainWindow owns the Transform package and the
    # scene activation helper, and reacts to this the same way it
    # reacts to brick_clicked. Package_029.
    #
    brick_moved = Signal(object, object)

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.StrongFocus)

        self.renderer = Renderer()
        self.move_tool = MoveTool()

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

            if (
                brick_id is not None
                and brick_id == self.renderer.selected_id
            ):

                #
                # Pressing the already-selected brick begins a move
                # drag instead of re-selecting it -- selection is
                # unchanged, so no signal is emitted here.
                #
                brick = self.renderer.scene.get(brick_id)

                grab_point = self.renderer.project_to_ground(
                    event.position().x(),
                    event.position().y(),
                    brick.position.y,
                )

                if grab_point is not None:
                    self.move_tool.begin(brick, grab_point)

                return

            self.brick_clicked.emit(brick_id)

            return

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = event.position()

    def mouseReleaseEvent(self, event):

        if self.move_tool.is_dragging:

            grab_point = self.renderer.project_to_ground(
                event.position().x(),
                event.position().y(),
                self.move_tool.plane_y,
            )

            if grab_point is not None:
                result = self.move_tool.finish(grab_point)
            else:
                self.move_tool.cancel()
                result = None

            self.renderer.set_preview(None)

            if result is not None:
                self.brick_moved.emit(*result)

            self.update()

            return

        if event.button() in (
            Qt.RightButton,
            Qt.MiddleButton,
        ):
            self.last_mouse_position = None

    def mouseMoveEvent(self, event):

        if self.move_tool.is_dragging:

            grab_point = self.renderer.project_to_ground(
                event.position().x(),
                event.position().y(),
                self.move_tool.plane_y,
            )

            if grab_point is not None:

                brick = self.renderer.scene.get(self.move_tool.brick_id)

                self.renderer.set_preview(
                    ScenePreview(
                        brick_id=self.move_tool.brick_id,
                        position=self.move_tool.update(grab_point),
                        rotation=brick.rotation,
                    )
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