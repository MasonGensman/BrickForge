"""
BrickForge Renderer
"""

from pathlib import Path

import glm

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_LINES,
    glClear,
    glClearColor,
    glDrawArrays,
    glEnable,
)

from brickforge.ldraw.library import LDrawLibrary
from brickforge.render.camera import Camera
from brickforge.render.grid import Grid
from brickforge.render.shader import Shader
from brickforge.render.vertex_array import VertexArray
from brickforge.render.vertex_buffer import VertexBuffer


class Renderer:

    def __init__(self):

        self.camera = Camera()

        self.shader = None

        self.grid = None
        self.grid_vao = None
        self.grid_vbo = None

        self.library = None
        self.brick_mesh = None

        self.width = 1
        self.height = 1

    def initialize(self):

        glEnable(GL_DEPTH_TEST)

        glClearColor(
            0.14,
            0.15,
            0.17,
            1.0,
        )

        shader_path = Path(__file__).parent / "shaders"

        self.shader = Shader(
            shader_path / "grid.vert",
            shader_path / "grid.frag",
        )

        self.grid = Grid()

        self.grid_vao = VertexArray()
        self.grid_vao.bind()

        self.grid_vbo = VertexBuffer(
            self.grid.vertices
        )

        self.grid_vbo.enable_attribute(
            0,
            3,
            12,
            0,
        )

        VertexArray.unbind()

        library_path = (
            Path(__file__).resolve().parents[1]
            / "ldraw"
            / "ldraw"
        )

        self.library = LDrawLibrary(
            library_path
        )

        part = self.library.test_load(
            "3001.dat"
        )

        self.brick_mesh = part.build_mesh()

    def resize(
        self,
        width,
        height,
    ):

        self.width = max(
            width,
            1,
        )

        self.height = max(
            height,
            1,
        )

    def render(self):

        glClear(
            GL_COLOR_BUFFER_BIT
            | GL_DEPTH_BUFFER_BIT
        )

        self.shader.use()

        model = glm.mat4(1)

        self.shader.set_matrix4(
            "u_model",
            model,
        )

        self.shader.set_matrix4(
            "u_view",
            self.camera.view_matrix(),
        )

        self.shader.set_matrix4(
            "u_projection",
            self.camera.projection_matrix(
                self.width,
                self.height,
            ),
        )

        self.grid_vao.bind()

        glDrawArrays(
            GL_LINES,
            0,
            self.grid.vertex_count,
        )

        VertexArray.unbind()

        #
        # Draw LEGO mesh
        #

        if self.brick_mesh is not None:

            self.brick_mesh.draw()