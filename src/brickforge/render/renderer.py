"""
BrickForge Renderer
Renderer V2
Milestone 3.1
"""

from dataclasses import dataclass

import glm

from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FILL,
    GL_FRONT_AND_BACK,
    GL_LINE,
    GL_LINES,
    glClear,
    glClearColor,
    glDrawArrays,
    glEnable,
    glPolygonMode,
)

from brickforge.engine.brick_manager import BrickManager
from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.render.camera import Camera
from brickforge.render.color_resolver import ColorResolver
from brickforge.render.grid import Grid
from brickforge.render.picking import (
    ray_intersects_aabb,
    ray_intersects_horizontal_plane,
    screen_to_ray,
)
from brickforge.render.render_context import RenderContext
from brickforge.render.shader import Shader
from brickforge.render.vertex_array import VertexArray
from brickforge.render.vertex_buffer import VertexBuffer
from brickforge.resources import resource_path
from brickforge.services.ldraw_library_locator import find_ldraw_library
from brickforge.services.part_catalog import PartCatalog

#
# Distinct from every default LDConfig color this app currently uses
# (black/blue/green/red/yellow/white, see color_resolver.py) so the
# selection highlight is never confused with a brick's real color.
#
_SELECTION_HIGHLIGHT_RGB = (0.1, 0.95, 1.0)


@dataclass(frozen=True, slots=True)
class ScenePreview:
    """
    A transient, renderer-only override of one brick's rendered
    transform -- render() draws brick_id at position/rotation instead
    of whatever its SceneBrick in Scene currently holds. Never
    touches Scene or SceneBrick, and carries nothing else (not
    part_name, not color): only what render()'s model-matrix
    construction actually needs, so it stays deliberately generic
    rather than shaped around any one tool. Renderer only ever
    consumes this value -- it has no knowledge of which interaction
    subsystem (MoveTool today, a future RotateTool, ...) produced it
    (Package_029).
    """

    brick_id: int
    position: glm.vec3
    rotation: glm.quat


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

        #
        # The only selection state Renderer holds -- an id to draw a
        # highlight for, nothing more. Renderer has no reference to
        # SelectionManager and no way to reach for one; MainWindow
        # pushes the current selection in via set_selected_id(),
        # mirroring how set_scene() already works (Package_027).
        #
        self.selected_id: int | None = None

        #
        # The only preview state Renderer holds -- an optional
        # override of one brick's rendered transform. Renderer has no
        # reference to MoveTool (or any future interaction tool) and
        # no way to reach for one; the owning widget pushes the
        # current preview in via set_preview(), mirroring
        # set_scene()/set_selected_id() (Package_029).
        #
        self.preview: ScenePreview | None = None

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

    def set_selected_id(
        self,
        brick_id: int | None,
    ) -> None:
        """Replace the id Renderer highlights. No validation -- the caller
        (MainWindow) is the one that owns and validates selection state."""

        self.selected_id = brick_id

    def set_preview(
        self,
        preview: ScenePreview | None,
    ) -> None:
        """Replace the transform preview override. Pass None to clear
        it -- there is no separate clear_preview(), matching
        set_selected_id(None)'s existing idiom."""

        self.preview = preview

    def project_to_ground(
        self,
        screen_x: float,
        screen_y: float,
        plane_y: float,
    ) -> glm.vec3 | None:
        """
        Cast a ray from a screen-space point and intersect it with
        the horizontal plane at plane_y, returning the world-space
        hit point, or None if the ray is parallel to that plane (a
        rare degenerate case at the current camera orientation).
        """

        ray_origin, ray_direction = screen_to_ray(
            screen_x,
            screen_y,
            self.width,
            self.height,
            self.camera.view_matrix(),
            self.camera.projection_matrix(
                self.width,
                self.height,
            ),
        )

        return ray_intersects_horizontal_plane(
            ray_origin,
            ray_direction,
            plane_y,
        )

    def pick(
        self,
        screen_x: float,
        screen_y: float,
    ) -> int | None:
        """
        Cast a ray from a screen-space click and return the id of the
        nearest SceneBrick it hits, or None. Pure CPU ray/AABB test
        against each brick's cached local-space bounding box
        (BrickManager.aabb_for) -- no ID buffers, no offscreen render
        passes, no acceleration structure. The model matrix is rigid
        (rotation + translation only, no scale anywhere in this
        codebase), so transforming the ray into a brick's local space
        preserves distances exactly -- the local-space hit distance
        is numerically identical to the world-space one, safe to
        compare directly across bricks to find the nearest hit.
        """

        if self.brick_manager is None:
            return None

        ray_origin, ray_direction = screen_to_ray(
            screen_x,
            screen_y,
            self.width,
            self.height,
            self.camera.view_matrix(),
            self.camera.projection_matrix(
                self.width,
                self.height,
            ),
        )

        nearest_id = None
        nearest_t = None

        for brick in self.scene:

            aabb = self.brick_manager.aabb_for(brick.part_name)

            if aabb is None:
                continue

            box_min, box_max = aabb

            inverse_model = glm.inverse(
                glm.translate(
                    glm.mat4(1.0),
                    brick.position,
                )
                * glm.mat4_cast(brick.rotation)
            )

            local_origin = glm.vec3(
                inverse_model * glm.vec4(ray_origin, 1.0)
            )

            local_direction = glm.vec3(
                inverse_model * glm.vec4(ray_direction, 0.0)
            )

            hit_t = ray_intersects_aabb(
                local_origin,
                local_direction,
                box_min,
                box_max,
            )

            if hit_t is not None and (
                nearest_t is None or hit_t < nearest_t
            ):

                nearest_t = hit_t
                nearest_id = brick.id

        return nearest_id

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

            position = brick.position
            rotation = brick.rotation

            if (
                self.preview is not None
                and self.preview.brick_id == brick.id
            ):

                position = self.preview.position
                rotation = self.preview.rotation

            self.shader.set_matrix4(
                "u_model",
                glm.translate(
                    glm.mat4(1.0),
                    position,
                )
                * glm.mat4_cast(rotation),
            )

            resolved_color = self.color_resolver.resolve(
                brick.color_code
            )

            self.shader.set_color(
                *resolved_color.rgb
            )

            mesh.draw()

            #
            # Selection highlight: redraw the same mesh as a
            # wireframe overlay in a distinct color. Renderer only
            # ever compares against self.selected_id -- it has no
            # knowledge of SelectionManager (Package_027).
            #
            if brick.id == self.selected_id:

                glPolygonMode(
                    GL_FRONT_AND_BACK,
                    GL_LINE,
                )

                self.shader.set_color(
                    *_SELECTION_HIGHLIGHT_RGB
                )

                mesh.draw()

                glPolygonMode(
                    GL_FRONT_AND_BACK,
                    GL_FILL,
                )
