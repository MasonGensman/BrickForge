"""
BrickForge Part Catalog

Indexes BrickDefinition entries for lookup by part number. The catalog
itself is agnostic to where its entries came from: today's small
hand-curated seed list and a future loader deriving BrickDefinitions from
the full LDraw parts library both produce a list[BrickDefinition] and are
loaded through the same PartCatalog constructor.
"""

from collections.abc import Iterable

from brickforge.models.part_definition import BrickDefinition

#
# Common LDraw color codes (verified against LDConfig.ldr):
# 0 Black, 1 Blue, 2 Green, 4 Red, 14 Yellow, 15 White.
#
_COMMON_COLORS = [0, 1, 2, 4, 14, 15]


def load_seed_bricks() -> list[BrickDefinition]:
    """
    Today's small, hand-curated seed catalog.

    A future loader (e.g. one deriving BrickDefinitions from the full LDraw
    parts library) returns the same list[BrickDefinition] shape and can be
    passed to PartCatalog exactly like this one -- PartCatalog does not
    assume this is the only source of entries.
    """

    return [
        BrickDefinition(
            part_number="3005",
            name="Brick 1x1",
            category="Brick",
            ldraw_filename="3005.dat",
            stud_width=1,
            stud_length=1,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3004",
            name="Brick 1x2",
            category="Brick",
            ldraw_filename="3004.dat",
            stud_width=1,
            stud_length=2,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3622",
            name="Brick 1x3",
            category="Brick",
            ldraw_filename="3622.dat",
            stud_width=1,
            stud_length=3,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3010",
            name="Brick 1x4",
            category="Brick",
            ldraw_filename="3010.dat",
            stud_width=1,
            stud_length=4,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3003",
            name="Brick 2x2",
            category="Brick",
            ldraw_filename="3003.dat",
            stud_width=2,
            stud_length=2,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3002",
            name="Brick 2x3",
            category="Brick",
            ldraw_filename="3002.dat",
            stud_width=2,
            stud_length=3,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3001",
            name="Brick 2x4",
            category="Brick",
            ldraw_filename="3001.dat",
            stud_width=2,
            stud_length=4,
            height_units=24.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3023",
            name="Plate 1x2",
            category="Plate",
            ldraw_filename="3023.dat",
            stud_width=1,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3022",
            name="Plate 2x2",
            category="Plate",
            ldraw_filename="3022.dat",
            stud_width=2,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
        BrickDefinition(
            part_number="3068",
            name="Tile 2x2",
            category="Tile",
            ldraw_filename="3068.dat",
            stud_width=2,
            stud_length=2,
            height_units=8.0,
            available_colors=list(_COMMON_COLORS),
        ),
    ]


class PartCatalog:
    """Looks up BrickDefinition entries by part number."""

    def __init__(
        self,
        parts: Iterable[BrickDefinition] = (),
    ):

        self._parts: dict[str, BrickDefinition] = {
            part.part_number: part
            for part in parts
        }

    @classmethod
    def from_seed(cls) -> "PartCatalog":
        """Build a PartCatalog from today's hand-curated seed list."""

        return cls(load_seed_bricks())

    def all(self) -> list[BrickDefinition]:
        return list(self._parts.values())

    def get(
        self,
        part_number: str,
    ) -> BrickDefinition | None:

        return self._parts.get(part_number)
