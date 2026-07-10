"""
BrickForge Vertex Buffer
Renderer V2
"""

import ctypes

import numpy as np

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


class VertexBuffer:
    """Modern OpenGL Vertex Buffer."""

    def __init__(self, vertices):

        self.vertices = np.asarray(
            vertices,
            dtype=np.float32,
        )

        self._id = glGenBuffers(1)

        if not self._id:
            raise RuntimeError(
                "Failed to create VBO."
            )

        self.bind()

        glBufferData(
            GL_ARRAY_BUFFER,
            self.vertices.nbytes,
            self.vertices,
            GL_STATIC_DRAW,
        )

    @property
    def id(self):

        return self._id

    def bind(self):

        glBindBuffer(
            GL_ARRAY_BUFFER,
            self._id,
        )

    @staticmethod
    def unbind():

        glBindBuffer(
            GL_ARRAY_BUFFER,
            0,
        )

    def enable_attribute(
        self,
        index,
        size,
        stride,
        offset,
    ):

        self.bind()

        glEnableVertexAttribArray(index)

        glVertexAttribPointer(
            index,
            size,
            GL_FLOAT,
            False,
            stride,
            ctypes.c_void_p(offset),
        )

    def delete(self):

        if self._id:

            glDeleteBuffers(
                1,
                [self._id],
            )

            self._id = 0

    def __del__(self):

        try:
            self.delete()
        except Exception:
            pass