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

    #
    # Raw LDraw color code (e.g. from PaletteEngine.MappedColor.color.code),
    # not a live LDrawColor reference -- matches how part_name is already a
    # raw identifier rather than a Part object reference. None means no
    # color has been assigned; the renderer still draws its own fixed
    # color regardless (wiring this into rendering is a future package).
    #
    color_code: int | None = None

    @classmethod
    def from_definition(
        cls,
        definition: BrickDefinition,
        *,
        id: int,
        position: glm.vec3 | None = None,
        rotation: glm.quat | None = None,
        color_code: int | None = None,
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

        if color_code is not None:
            kwargs["color_code"] = color_code

        return cls(
            id=id,
            part_name=definition.part_name,
            **kwargs,
        )
