"""
BrickForge LDraw Part
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from brickforge.render.mesh import Mesh


@dataclass
class Part:
    """Represents one LDraw part."""

    name: str = ""

    description: str = ""

    vertices: np.ndarray = field(
        default_factory=lambda: np.array(
            [],
            dtype=np.float32,
        )
    )

    indices: np.ndarray = field(
        default_factory=lambda: np.array(
            [],
            dtype=np.uint32,
        )
    )

    def has_geometry(self) -> bool:
        return self.vertices.size > 0

    def build_mesh(self) -> Mesh | None:

        if not self.has_geometry():
            return None

        # Local import avoids a circular dependency.
        from brickforge.render.mesh import Mesh

        return Mesh(self.vertices)

    def append_vertices(
        self,
        vertices: np.ndarray,
    ) -> None:

        if vertices.size == 0:
            return

        if self.vertices.size == 0:
            self.vertices = vertices.copy()
        else:
            self.vertices = np.concatenate(
                (
                    self.vertices,
                    vertices,
                )
            )