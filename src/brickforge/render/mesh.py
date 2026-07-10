"""
BrickForge Mesh
Renderer V2
"""

from OpenGL.GL import (
    GL_TRIANGLES,
    glDrawArrays,
)

from brickforge.render.vertex_array import VertexArray
from brickforge.render.vertex_buffer import VertexBuffer


class Mesh:
    """GPU mesh consisting of one VAO and one VBO."""

    def __init__(self, vertices):

        self.vertex_count = len(vertices) // 3

        self.vao = VertexArray()
        self.vao.bind()

        self.vbo = VertexBuffer(vertices)

        self.vbo.enable_attribute(
            index=0,
            size=3,
            stride=12,
            offset=0,
        )

        VertexArray.unbind()

    def draw(self):

        if self.vertex_count == 0:
            return

        self.vao.bind()

        glDrawArrays(
            GL_TRIANGLES,
            0,
            self.vertex_count,
        )

        VertexArray.unbind()

    def delete(self):

        self.vbo.delete()
        self.vao.delete()

    def __del__(self):

        try:
            self.delete()
        except Exception:
            pass