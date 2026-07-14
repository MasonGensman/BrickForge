"""
BrickForge LDraw Part

Represents a parsed LDraw part.
"""

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class PartReference:
    """
    One LDraw Type-1 line: a reference to another part.

    Stores the placement exactly as the LDraw file format expresses it -- a
    translation vector and the native 3x3 transform matrix -- rather than an
    internal 4x4 representation.
    """

    file_name: str
    translation: np.ndarray
    matrix: np.ndarray


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

    subfile_references: list[PartReference] = field(
        default_factory=list
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