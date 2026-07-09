"""
BrickForge Grid
"""

import numpy as np


class Grid:
    """Simple construction grid."""

    def __init__(
        self,
        size: int = 20,
        spacing: float = 1.0,
    ):
        self.size = size
        self.spacing = spacing

        self.vertices = self._generate_vertices()

    def _generate_vertices(self) -> np.ndarray:

        vertices = []

        extent = self.size * self.spacing

        for i in range(-self.size, self.size + 1):

            value = i * self.spacing

            # Vertical line
            vertices.extend([
                value, 0.0, -extent,
                value, 0.0, extent,
            ])

            # Horizontal line
            vertices.extend([
                -extent, 0.0, value,
                extent, 0.0, value,
            ])

        return np.array(
            vertices,
            dtype=np.float32,
        )

    @property
    def vertex_count(self) -> int:
        return len(self.vertices) // 3