"""
BrickForge Brick Manager
"""

import logging
from pathlib import Path

from brickforge.engine.scene import Scene
from brickforge.ldraw.library import LDrawLibrary
from brickforge.render.mesh import Mesh

logger = logging.getLogger(__name__)


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

                return None

            self._mesh_cache[part_name] = (
                Mesh(part.vertices)
                if part.has_geometry()
                else None
            )

        return self._mesh_cache[part_name]

    def renderables(self, scene: Scene):
        """Yield (SceneBrick, Mesh) pairs for every brick with resolvable geometry."""

        for brick in scene:

            mesh = self._mesh_for(brick.part_name)

            if mesh is not None:
                yield brick, mesh
