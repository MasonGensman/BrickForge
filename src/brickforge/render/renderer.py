"""
BrickForge Renderer
Renderer V2
Milestone 3.1
"""

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
from brickforge.render.color_resolver import ColorResolver
from brickforge.render.grid import Grid
from brickforge.render.render_context import RenderContext
from brickforge.render.shader import Shader
from brickforge.render.vertex_array import VertexArray
from brickforge.render.vertex_buffer import VertexBuffer
from brickforge.resources import resource_path
from brickforge.services.ldraw_library_locator import find_ldraw_library
from brickforge.services.part_catalog import PartCatalog


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
        self.color_resolver = None

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

        shader_path = resource_path("render", "shaders")

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

        #
        # Same discovery order PartCatalog.load_best_available() uses
        # (find_ldraw_library()'s four tiers) -- the renderer and the
        # catalog always agree on which library is "best available",
        # rather than each resolving a different path independently.
        # find_ldraw_library() only returns None if even the bundled
        # fallback is missing; resource_path() is the same last-resort
        # fallback it would have found anyway.
        #
        library_path = (
            find_ldraw_library()
            or resource_path("ldraw", "ldraw")
        )

        self.brick_manager = BrickManager(library_path)

        self.color_resolver = ColorResolver(
            library_path / "LDConfig.ldr"
        )

        catalog = PartCatalog.load_best_available()

        demo_bricks = (
            (
                "3001",
                1,
                glm.vec3(0.0, 0.0, 0.0),
                glm.quat(),
            ),
            (
                "3003",
                2,
                glm.vec3(100.0, 0.0, 0.0),
                glm.angleAxis(
                    glm.radians(45.0),
                    glm.vec3(0.0, 1.0, 0.0),
                ),
            ),
            (
                "3004",
                3,
                glm.vec3(200.0, 0.0, 0.0),
                glm.quat(),
            ),
        )

        for (
            part_number,
            brick_id,
            position,
            rotation,
        ) in demo_bricks:

            definition = catalog.get(part_number)

            if definition is None:
                continue

            self.scene.add_brick(
                SceneBrick.from_definition(
                    definition,
                    id=brick_id,
                    position=position,
                    rotation=rotation,
                )
            )

    def resize(
        self,
        width,
        height,
    ):

        self.width = max(width, 1)
        self.height = max(height, 1)

    def set_scene(
        self,
        scene: Scene,
    ) -> None:
        """
        Replace the active Scene. render() already re-reads self.scene
        fresh every frame, so no other renderer state needs to change.
        """

        self.scene = scene

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

            self.shader.set_matrix4(
                "u_model",
                glm.translate(
                    glm.mat4(1.0),
                    brick.position,
                )
                * glm.mat4_cast(brick.rotation),
            )

            resolved_color = self.color_resolver.resolve(
                brick.color_code
            )

            self.shader.set_color(
                *resolved_color.rgb
            )

            mesh.draw()
