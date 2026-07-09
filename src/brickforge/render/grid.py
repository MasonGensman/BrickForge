"""
BrickForge Grid
"""

import numpy as np


class Grid:
    """Generates a simple XZ construction grid."""

    def __init__(
        self,
        size: int = 20,
        spacing: float = 1.0,
    ):
        self.size = size
        self.spacing = spacing

        self.vertices = self._build()

    def _build(self):

        vertices = []

        extent = self.size * self.spacing

        for i in range(-self.size, self.size + 1):

            x = i * self.spacing

            vertices.extend([
                x, 0.0, -extent,
                x, 0.0, extent,
            ])

            z = i * self.spacing

            vertices.extend([
                -extent, 0.0, z,
                extent, 0.0, z,
            ])

        return np.array(
            vertices,
            dtype=np.float32,
        )