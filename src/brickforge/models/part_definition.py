"""
BrickForge Brick Definition

Catalog-level knowledge about a LEGO part: what it is, its dimensions, the
colors it comes in, and its LDraw filename. Distinct from both
brickforge.models.brick.Brick (a UI catalog display row) and
brickforge.engine.scene_brick.SceneBrick (a placed scene instance) -- this
is the part-type "intelligence" record the two of those don't carry.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class BoundingBox:
    """Axis-aligned bounding box, in LDraw units."""

    min: tuple[float, float, float]
    max: tuple[float, float, float]


@dataclass(slots=True)
class BrickDefinition:
    """Catalog knowledge about one LEGO part."""

    part_number: str
    name: str
    category: str
    ldraw_filename: str

    stud_width: int
    stud_length: int
    height_units: float

    available_colors: list[int] = field(
        default_factory=list
    )

    bounding_box: BoundingBox | None = None
    description: str = ""

    #
    # Optional metadata. Not populated beyond the initial seed data yet,
    # but present now so adding real values later isn't a breaking change.
    #
    weight_g: float | None = None
    aliases: list[str] = field(default_factory=list)
    family: str | None = None

    @property
    def part_name(self) -> str:
        """Alias for ldraw_filename, matching SceneBrick.part_name."""
        return self.ldraw_filename
