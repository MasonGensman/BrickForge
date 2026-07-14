"""
BrickForge Mosaic Generator

Deterministically converts an ImageResource into a Scene: one
non-transparent pixel becomes one SceneBrick, using a single fixed part
and its PaletteEngine-mapped LDraw color. No AI, no optimization, no
variable brick sizing, no merging.

Named mosaic_generator specifically because it is one generation strategy
among future others (a height-map mode, a voxel mode, ...) that would
live alongside it in generation/ as separate modules -- see the module
docstring below on generate_mosaic for how a future mode coexists without
changing this module's public API.

Depends on engine/ only through Scene/SceneBrick's existing, unmodified
public API (Scene.add_brick, SceneBrick.from_definition). Never touches
render/, OpenGL, UI, or AI.
"""

from dataclasses import dataclass
from enum import Enum

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.io.image_resource import ImageResource
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDraw units. Used to derive brick spacing from a
# part's real stud footprint so bricks tile edge-to-edge with no gaps.
#
_STUD_LDU = 20.0


class OriginMode(Enum):
    """Where image pixel (row=0, col=0) maps to in world space."""

    CENTERED = "centered"
    CORNER = "corner"


@dataclass(slots=True)
class GenerationSettings:
    """
    Configuration for one generation pass.

    New settings belong here, not as new parameters on generate_mosaic()
    or any future generation function -- keeps every generation
    function's signature stable as capabilities grow. A future,
    differently-shaped generation mode (e.g. a height-map mode needing a
    depth-scale setting) can introduce its own settings type reusing this
    one's fields/spirit, rather than this type growing indefinitely to
    cover strategies it doesn't apply to.
    """

    default_part_number: str = "3005"
    skip_transparent_pixels: bool = True
    origin_mode: OriginMode = OriginMode.CENTERED

    #
    # None means: derive automatically from the resolved part's own
    # stud_width/stud_length (see generate_mosaic). Set explicitly to
    # override with one uniform spacing for both axes.
    #
    spacing: float | None = None


def generate_mosaic(
    image: ImageResource,
    palette: PaletteEngine,
    catalog: PartCatalog,
    settings: GenerationSettings | None = None,
) -> Scene:
    """
    Convert one image into a Scene, one brick per non-transparent pixel.

    Coordinate convention (explicit and deterministic):
    - Image pixel (row=0, col=0) is the top-left pixel -- standard raster
      convention, matching ImageResource.pixels' own (height, width, 4)
      layout.
    - Image column maps to world X; image row maps to world Z. Both axes
      increase together: column increasing -> +X, row increasing -> +Z.
    - World Y is always 0.0 -- a flat mosaic; no height-map data exists
      in this package.
    - OriginMode.CENTERED (default): the whole grid is centered on the
      world origin:
          x = (col - (width - 1) / 2) * spacing_x
          z = (row - (height - 1) / 2) * spacing_z
      OriginMode.CORNER: pixel (0, 0) sits exactly at world (0, 0, 0):
          x = col * spacing_x
          z = row * spacing_z
    - spacing_x / spacing_z default to the resolved part's own footprint
      (stud_width / stud_length * 20 LDU). settings.spacing, if set,
      overrides both axes uniformly.

    Brick ids are assigned as `row * width + col` -- deterministic, tied
    directly to iteration order, guaranteed unique for any image size.

    A pixel PaletteEngine treats as transparent produces no SceneBrick
    when settings.skip_transparent_pixels is True (the default).
    """

    settings = settings or GenerationSettings()

    definition = catalog.get(settings.default_part_number)

    if definition is None:

        raise ValueError(
            "PartCatalog has no part "
            f"{settings.default_part_number!r}"
        )

    spacing_x = (
        settings.spacing
        if settings.spacing is not None
        else definition.stud_width * _STUD_LDU
    )

    spacing_z = (
        settings.spacing
        if settings.spacing is not None
        else definition.stud_length * _STUD_LDU
    )

    width = image.width
    height = image.height

    if settings.origin_mode is OriginMode.CENTERED:

        x_offset = (width - 1) / 2.0
        z_offset = (height - 1) / 2.0

    else:

        x_offset = 0.0
        z_offset = 0.0

    scene = Scene()

    for row in range(height):

        for col in range(width):

            mapped = palette.map_color(
                image.pixels[row, col]
            )

            if (
                mapped.is_transparent
                and settings.skip_transparent_pixels
            ):
                continue

            x = (col - x_offset) * spacing_x
            z = (row - z_offset) * spacing_z

            scene.add_brick(
                SceneBrick.from_definition(
                    definition,
                    id=row * width + col,
                    position=glm.vec3(x, 0.0, z),
                    color_code=(
                        mapped.color.code
                        if mapped.color is not None
                        else None
                    ),
                )
            )

    return scene
