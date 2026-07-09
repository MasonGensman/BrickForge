"""
BrickForge Vertex Buffer
"""

from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_FLOAT,
    GL_STATIC_DRAW,
    glBindBuffer,
    glBufferData,
    glDeleteBuffers,
    glEnableVertexAttribArray,
    glGenBuffers,
    glVertexAttribPointer,
)

import numpy as np


class VertexBuffer:
    """Simple OpenGL vertex buffer."""

    def __init__(self, vertices):

        self.vertices = np.array(
            vertices,
            dtype=np.float32,
        )

        self.buffer = glGenBuffers(1)

        glBindBuffer(
            GL_ARRAY_BUFFER,
            self.buffer,
        )

        glBufferData(
            GL_ARRAY_BUFFER,
            self.vertices.nbytes,
            self.vertices,
            GL_STATIC_DRAW,
        )

    def bind(self):

        glBindBuffer(
            GL_ARRAY_BUFFER,
            self.buffer,
        )

    def enable_attribute(
        self,
        index: int,
        size: int,
        stride: int,
        offset: int,
    ):

        glEnableVertexAttribArray(index)

        glVertexAttribPointer(
            index,
            size,
            GL_FLOAT,
            False,
            stride,
            offset,
        )

    def delete(self):

        glDeleteBuffers(
            1,
            [self.buffer],
        )