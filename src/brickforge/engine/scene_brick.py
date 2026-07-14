"""
BrickForge Scene Brick
"""

from dataclasses import dataclass, field

import glm

from brickforge.models.part_definition import BrickDefinition


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

    @classmethod
    def from_definition(
        cls,
        definition: BrickDefinition,
        *,
        id: int,
        position: glm.vec3 | None = None,
        rotation: glm.quat | None = None,
    ) -> "SceneBrick":
        """
        Construct a SceneBrick from catalog BrickDefinition data. The one
        authoritative place a part's LDraw filename becomes a SceneBrick's
        part_name -- callers should never need to type a .dat literal.
        """

        kwargs = {}

        if position is not None:
            kwargs["position"] = position

        if rotation is not None:
            kwargs["rotation"] = rotation

        return cls(
            id=id,
            part_name=definition.part_name,
            **kwargs,
        )
