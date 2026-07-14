"""
BrickForge Scene Brick
"""

from dataclasses import dataclass, field

import glm


@dataclass(slots=True)
class SceneBrick:
    """Represents one placed LDraw part in a Scene."""

    id: int
    part_name: str

    position: glm.vec3 = field(
        default_factory=lambda: glm.vec3(
            0.0,
            0.0,
            0.0,
        )
    )

    rotation: glm.quat = field(
        default_factory=glm.quat
    )
