"""
BrickForge Vertex Array
"""

from OpenGL.GL import (
    glBindVertexArray,
    glDeleteVertexArrays,
    glGenVertexArrays,
)


class VertexArray:
    """OpenGL Vertex Array Object."""

    def __init__(self):

        self.vao = glGenVertexArrays(1)

    def bind(self):

        glBindVertexArray(
            self.vao,
        )

    @staticmethod
    def unbind():

        glBindVertexArray(0)

    def delete(self):

        glDeleteVertexArrays(
            1,
            [self.vao],
        )