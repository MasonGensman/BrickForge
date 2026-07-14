"""
BrickForge Renderer
Renderer V2
Milestone 3.1
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

from brickforge.engine.brick_manager import BrickManager
from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.render.camera import Camera
from brickforge.render.grid import Grid
from brickforge.render.render_context import RenderContext
from brickforge.render.shader import Shader
from brickforge.render.vertex_array import VertexArray
from brickforge.render.vertex_buffer import VertexBuffer


class Renderer:
    """BrickForge Renderer V2."""

    def __init__(self):

        self.context = RenderContext()

        self.camera = Camera()

        self.shader = None

        self.grid = None
        self.grid_vao = None
        self.grid_vbo = None

        self.scene = Scene()
        self.brick_manager = None

        self.width = 1
        self.height = 1

    def initialize(self):

        self.context.initialize()

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
            index=0,
            size=3,
            stride=12,
            offset=0,
        )

        VertexArray.unbind()

        library_path = (
            Path(__file__).resolve().parents[1]
            / "ldraw"
            / "ldraw"
        )

        self.brick_manager = BrickManager(library_path)

        self.scene.add(
            SceneBrick(
                id=1,
                part_name="3001.dat",
            )
        )

    def resize(
        self,
        width,
        height,
    ):

        self.width = max(width, 1)
        self.height = max(height, 1)

    def render(self):

        self.context.validate()

        glClear(
            GL_COLOR_BUFFER_BIT
            | GL_DEPTH_BUFFER_BIT
        )

        self.shader.use()

        self.shader.set_matrix4(
            "u_model",
            glm.mat4(1.0),
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

        #
        # Draw grid
        #

        self.shader.set_color(
            0.35,
            0.35,
            0.35,
        )

        self.grid_vao.bind()

        glDrawArrays(
            GL_LINES,
            0,
            self.grid.vertex_count,
        )

        VertexArray.unbind()

        #
        # Draw scene bricks
        #

        for brick, mesh in self.brick_manager.renderables(
            self.scene
        ):

            self.shader.set_color(
                0.80,
                0.05,
                0.05,
            )

            mesh.draw()
