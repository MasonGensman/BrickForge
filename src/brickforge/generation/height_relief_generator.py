"""
BrickForge Height Relief Generator

Deterministically converts an ImageResource into a three-dimensional
Scene: each non-transparent pixel becomes a vertical stack of one fixed
part, one LDraw color per stack, with stack height quantized directly
from that pixel's own luminance -- no smoothing, no interpolation, no
adaptive scaling.

Height Relief is the second registered GenerationMode (Package_019),
existing specifically to validate that the registry/UI/preparation
architecture built in Packages 016-018 needs no changes to support a
genuinely different Scene shape: a variable number of bricks per pixel
at variable Y, rather than Flat Mosaic's fixed one-brick-at-Y=0.

This is intentionally a simple, deterministic height generator meant to
validate the architecture -- not a relief-quality algorithm. Smoothing,
surface interpolation, adaptive layer heights, structural analysis, and
optimization are all out of scope here and reserved for future packages.

Depends on engine/ only through Scene/SceneBrick's existing, unmodified
public API, exactly like mosaic_generator.py. Never touches render/,
OpenGL, UI, or AI. Deliberately independent of mosaic_generator.py -- no
shared import beyond the same physical LDU constant, redefined here
rather than imported, to keep the two modes fully decoupled.
"""

from dataclasses import dataclass

import glm

from brickforge.analysis.image_analysis import to_grayscale
from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.io.image_resource import ImageResource
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDraw units -- the same physical constant
# mosaic_generator.py uses, redefined here (not imported) to keep the
# two modes independent.
#
_STUD_LDU = 20.0


@dataclass(slots=True)
class HeightReliefSettings:
    """
    Configuration for one Height Relief generation pass. Independent of
    GenerationSettings (Flat Mosaic's own settings type) -- no shared
    fields, no inheritance.
    """

    default_part_number: str = "3023"

    #
    # Number of stacked layers a pixel can produce, not a physical
    # height -- the actual world-space height of a stack is
    # max_layers * definition.height_units.
    #
    max_layers: int = 4

    skip_transparent_pixels: bool = True


def generate_height_relief(
    image: ImageResource,
    palette: PaletteEngine,
    catalog: PartCatalog,
    settings: HeightReliefSettings | None = None,
) -> Scene:
    """
    Convert one image into a Scene: each non-transparent pixel becomes a
    vertical stack of 1..max_layers copies of one fixed part, all
    sharing one LDraw color mapped from that pixel.

    Coordinate convention (explicit and deterministic, matching
    mosaic_generator.py's own documented convention):
    - Image pixel (row=0, col=0) is the top-left pixel.
    - Image column maps to world X; image row maps to world Z. The grid
      is centered on the world origin:
          x = (col - (width - 1) / 2) * spacing_x
          z = (row - (height - 1) / 2) * spacing_z
    - World Y stacks upward from the grid plane: layer L (0-indexed,
      bottom to top) sits at y = L * definition.height_units. The
      renderer's camera uses +Y as "up" (glm.lookAt(..., up=(0,1,0)),
      confirmed by inspection during Package_019 planning), so
      increasing Y is the correct direction for a taller stack.
    - spacing_x / spacing_z are derived from the resolved part's own
      stud_width / stud_length footprint (stud_width * 20 LDU), exactly
      like mosaic_generator.py, so stacks tile edge-to-edge with no
      gaps.

    Stack height quantization (deterministic, no smoothing, no
    interpolation, no adaptive scaling): luminance is computed once via
    the existing to_grayscale(), then per pixel,

        height = 1 + round((luminance / 255.0) * (max_layers - 1))

    Luminance 0 -> 1 layer (minimum); luminance 255 -> max_layers
    (maximum) -- purely a function of that single pixel's own luminance,
    with no neighbor influence and no image-wide adaptive scaling.

    Every SceneBrick in one pixel's stack shares identical X/Z and one
    LDraw color; only Y differs between layers.

    Brick ids are assigned via a running counter over row-major
    iteration, then bottom-to-top per pixel -- deterministic given fixed
    iteration order, guaranteed unique.

    A pixel PaletteEngine treats as transparent produces no bricks (the
    entire stack is skipped) when settings.skip_transparent_pixels is
    True (the default).
    """

    settings = settings or HeightReliefSettings()

    definition = catalog.get(settings.default_part_number)

    if definition is None:

        raise ValueError(
            "PartCatalog has no part "
            f"{settings.default_part_number!r}"
        )

    spacing_x = definition.stud_width * _STUD_LDU
    spacing_z = definition.stud_length * _STUD_LDU
    layer_height = definition.height_units

    width = image.width
    height = image.height

    x_offset = (width - 1) / 2.0
    z_offset = (height - 1) / 2.0

    luminance = to_grayscale(image.pixels)

    scene = Scene()

    next_id = 0

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

            stack_height = 1 + round(
                (luminance[row, col] / 255.0)
                * (settings.max_layers - 1)
            )

            x = (col - x_offset) * spacing_x
            z = (row - z_offset) * spacing_z

            color_code = (
                mapped.color.code
                if mapped.color is not None
                else None
            )

            for layer in range(stack_height):

                scene.add_brick(
                    SceneBrick.from_definition(
                        definition,
                        id=next_id,
                        position=glm.vec3(
                            x,
                            layer * layer_height,
                            z,
                        ),
                        color_code=color_code,
                    )
                )

                next_id += 1

    return scene
