"""
BrickForge Brick Manager
"""

import logging
from pathlib import Path

import glm

from brickforge.engine.scene import Scene
from brickforge.ldraw.library import LDrawLibrary
from brickforge.render.mesh import Mesh

logger = logging.getLogger(__name__)


def _local_aabb(vertices) -> tuple[glm.vec3, glm.vec3] | None:
    """
    Compute a part's local-space axis-aligned bounding box from its
    raw triangle vertex data. None if the part has no geometry.
    """

    if vertices.size == 0:
        return None

    points = vertices.reshape(-1, 3)

    return (
        glm.vec3(*points.min(axis=0).tolist()),
        glm.vec3(*points.max(axis=0).tolist()),
    )


class BrickManager:
    """Owns the LDraw library and the GPU mesh cache for scene bricks."""

    def __init__(
        self,
        library_path: str | Path,
    ):

        self.library: LDrawLibrary | None = None

        try:
            self.library = LDrawLibrary(library_path)

        except OSError as error:

            logger.warning(
                "LDraw library could not be opened, "
                "no bricks will be rendered: %s",
                error,
            )

        self._mesh_cache: dict[str, Mesh | None] = {}

        #
        # Populated in the same lazy-load pass as _mesh_cache (see
        # _mesh_for) so picking always tests against the exact same
        # geometry that gets rendered -- never an independent source
        # (Package_027).
        #
        self._aabb_cache: dict[str, tuple[glm.vec3, glm.vec3] | None] = {}

    def _mesh_for(
        self,
        part_name: str,
    ) -> Mesh | None:

        if self.library is None:
            return None

        if part_name not in self._mesh_cache:

            try:
                part = self.library.load(part_name)

            except OSError as error:

                logger.warning(
                    "LDraw part could not be loaded, skipping: %s",
                    error,
                )

                self._mesh_cache[part_name] = None
                self._aabb_cache[part_name] = None

                return None

            self._mesh_cache[part_name] = (
                Mesh(part.vertices)
                if part.has_geometry()
                else None
            )

            self._aabb_cache[part_name] = _local_aabb(part.vertices)

        return self._mesh_cache[part_name]

    def aabb_for(
        self,
        part_name: str,
    ) -> tuple[glm.vec3, glm.vec3] | None:
        """
        Return the cached local-space (min, max) AABB for a part,
        loading it via the same path _mesh_for() uses if not yet
        cached. None if the part has no geometry or can't be loaded.
        """

        if part_name not in self._aabb_cache:
            self._mesh_for(part_name)

        return self._aabb_cache.get(part_name)

    def renderables(self, scene: Scene):
        """Yield (SceneBrick, Mesh) pairs for every brick with resolvable geometry."""

        for brick in scene:

            mesh = self._mesh_for(brick.part_name)

            if mesh is not None:
                yield brick, mesh
