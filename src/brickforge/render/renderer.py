"""
BrickForge Renderer
"""

from pathlib import Path

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    glClear,
    glClearColor,
    glEnable,
    GL_DEPTH_TEST,
)

from brickforge.render.camera import Camera
from brickforge.render.shader import Shader


class Renderer:
    """Main renderer."""

    def __init__(self):

        self.camera = Camera()

        self.shader = None

        self.background = (
            0.14,
            0.15,
            0.17,
            1.0,
        )

    def initialize(self):

        glEnable(GL_DEPTH_TEST)

        glClearColor(*self.background)

        shader_path = Path(__file__).parent / "shaders"

        self.shader = Shader(
            shader_path / "grid.vert",
            shader_path / "grid.frag",
        )

    def resize(
        self,
        width: int,
        height: int,
    ):
        self.width = width
        self.height = height

    def render(self):

        glClear(
            GL_COLOR_BUFFER_BIT |
            GL_DEPTH_BUFFER_BIT
        )

        self.shader.use()