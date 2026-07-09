"""
BrickForge LDraw Part
"""

from dataclasses import dataclass, field

import numpy as np


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