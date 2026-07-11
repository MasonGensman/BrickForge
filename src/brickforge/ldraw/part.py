"""
BrickForge LDraw Part

Represents a parsed LDraw part.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class Part:
    """Represents one parsed LDraw part."""

    name: str = ""
    description: str = ""

    vertices: np.ndarray = field(
        default_factory=lambda: np.empty(
            0,
            dtype=np.float32,
        )
    )

    def has_geometry(self) -> bool:
        """Return True if this part contains geometry."""
        return self.vertices.size > 0

    @property
    def vertex_count(self) -> int:
        return self.vertices.size // 3

    @property
    def triangle_count(self) -> int:
        return self.vertex_count // 3

    def clear(self) -> None:
        """Release all geometry."""
        self.vertices = np.empty(
            0,
            dtype=np.float32,
        )