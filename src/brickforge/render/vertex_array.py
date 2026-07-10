"""
BrickForge Vertex Array
Renderer V2
"""

from OpenGL.GL import (
    glBindVertexArray,
    glDeleteVertexArrays,
    glGenVertexArrays,
)


class VertexArray:
    """Modern OpenGL Vertex Array Object."""

    def __init__(self):

        self._id = glGenVertexArrays(1)

        if not self._id:
            raise RuntimeError(
                "Failed to create VAO."
            )

    @property
    def id(self):

        return self._id

    def bind(self):

        glBindVertexArray(self._id)

    @staticmethod
    def unbind():

        glBindVertexArray(0)

    def delete(self):

        if self._id:

            glDeleteVertexArrays(
                1,
                [self._id],
            )

            self._id = 0

    def __del__(self):

        #
        # OpenGL context may already be gone.
        # Ignore cleanup failures.
        #
        try:
            self.delete()
        except Exception:
            pass