"""
BrickForge Vertex Buffer
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
    """OpenGL Vertex Buffer Object."""

    def __init__(self, vertices: np.ndarray):

        self.vertices = np.asarray(
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

    @staticmethod
    def unbind():

        glBindBuffer(
            GL_ARRAY_BUFFER,
            0,
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
            ctypes.c_void_p(offset),
        )

    def delete(self):

        glDeleteBuffers(
            1,
            [self.buffer],
        )