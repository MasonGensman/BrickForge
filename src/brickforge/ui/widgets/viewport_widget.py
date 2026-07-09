from OpenGL.GL import (
    glBegin,
    glClear,
    glClearColor,
    glColor3f,
    glEnd,
    glFlush,
    glVertex2f,
    GL_COLOR_BUFFER_BIT,
    GL_LINES,
)

from PySide6.QtCore import QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class ViewportWidget(QOpenGLWidget):

    def __init__(self):
        super().__init__()

        self.setMinimumSize(640, 480)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    def initializeGL(self):
        glClearColor(0.14, 0.15, 0.17, 1.0)

    def resizeGL(self, width, height):
        pass

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)

        glBegin(GL_LINES)

        # X Axis (Red)
        glColor3f(1.0, 0.2, 0.2)
        glVertex2f(-0.75, 0.0)
        glVertex2f(0.75, 0.0)

        # Y Axis (Green)
        glColor3f(0.2, 1.0, 0.2)
        glVertex2f(0.0, -0.75)
        glVertex2f(0.0, 0.75)

        glEnd()

        glFlush()