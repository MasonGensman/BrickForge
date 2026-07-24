"""
BrickForge Generation Engine

The first package that produces an actual LEGO model (Package_038):
generate_scene() converts a GenerationInput's analyzed image data into a
Scene, using only the existing Generation Candidate System for part
selection -- never touching PartCatalog internals directly.

Deliberately simple: one part for the whole Scene, one brick per
occupied pixel, colors reduced to the image's own (at most five)
dominant colors rather than per-pixel unconstrained matching.
Correctness, determinism, and clean integration are this package's
goals -- not generation quality. Optimization, structural validation,
and search-based placement are explicitly future packages' work.

Produces a plain Scene via the same Scene()/add_brick()/
SceneBrick.from_definition()/Scene.next_available_id() path every other
Scene producer in this codebase already uses -- no generation-specific
Scene type, no alternate id scheme, so every downstream subsystem
(renderer, selection, transform, serialization, export) needs no
special-case code for a generated Scene.

Independent of engine/render/ui -- depends only on the existing
GenerationInput, ImageAnalysisResult, PartCatalog, PaletteEngine,
GenerationConstraints/candidates_for, and Scene/SceneBrick.
"""

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.generation.candidates import GenerationConstraints, candidates_for
from brickforge.models.part_definition import BrickDefinition
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDU -- the same physical constant every other
# generator in this package independently defines (see
# mosaic_generator.py/height_relief_generator.py's own docstrings on
# why each redefines it rather than sharing one).
#
_STUD_LDU = 20.0


def select_generation_brick(
    candidates: list[BrickDefinition],
) -> BrickDefinition:
    """
    Pick one BrickDefinition to use for generation, from a list of
    already-filtered candidates (generation/candidates.py). A pure,
    isolated policy -- generate_scene() only knows that it asked for a
    brick and received one, never why. Future optimization packages can
    replace this function's logic entirely without restructuring the
    generation pipeline.

    Today's policy: the smallest stud footprint (stud_width *
    stud_length), tie-broken by part_number for determinism. A small
    part guarantees gap-free tiling for any image shape, matching the
    existing generators' own choice of a small default part.

    Raises ValueError if candidates is empty -- there is no reasonable
    brick to select, whether because GenerationConstraints eliminated
    every part or the catalog itself has none.
    """

    if not candidates:

        raise ValueError(
            "select_generation_brick() received no candidates -- "
            "GenerationConstraints eliminated every part, or the "
            "catalog has none to offer."
        )

    return min(
        candidates,
        key=lambda definition: (
            definition.stud_width * definition.stud_length,
            definition.part_number,
        ),
    )


def _nearest_dominant_color(
    pixel_rgb: tuple[int, int, int],
    dominant_colors: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """
    The entry of dominant_colors closest to pixel_rgb by squared
    Euclidean distance. Deterministic: Python's min() returns the first
    minimal element on a tie, and dominant_colors is itself already
    deterministically ordered (ImageAnalysisResult, Package_035).

    Independent, pure helper -- consumes only its two arguments, never
    calls select_generation_brick() or anything else in this module.
    """

    return min(
        dominant_colors,
        key=lambda color: sum(
            (a - b) ** 2
            for a, b in zip(pixel_rgb, color)
        ),
    )


def generate_scene(
    generation_input: GenerationInput,
    catalog: PartCatalog,
    palette: PaletteEngine,
    constraints: GenerationConstraints | None = None,
) -> Scene:
    """
    Convert one GenerationInput into a Scene: one brick of a single,
    candidate-selected part per occupied pixel, colored by the image's
    own dominant colors.

    Pipeline: candidates_for() (never a direct catalog lookup) ->
    select_generation_brick() -> one brick per occupied pixel, using
    Scene.next_available_id() for every id exactly as any other Scene
    producer would.

    Coordinate convention (matches mosaic_generator.py's own documented
    convention): image column maps to world X, image row maps to world
    Z, world Y is always 0.0. Placement is centered on
    analysis.occupied_bounds -- the image's actual content region --
    rather than the full canvas, so transparent padding around a small
    subject doesn't push the generated model off-center.

    Deterministic given identical (generation_input, catalog, palette,
    constraints): candidates_for()/select_generation_brick()/
    ImageAnalysisResult are all already deterministic, iteration is
    row-major over a fixed pixel array, and colors are drawn from
    analysis.dominant_colors, itself already deterministically ordered.

    Failure handling:
    - No candidates (empty catalog, or constraints eliminating every
      part): select_generation_brick() raises ValueError.
    - A fully transparent image (analysis.occupied_bounds is None):
      returns an empty Scene() -- a valid, ordinary Scene, not an
      error, matching every existing generator's own "skip transparent
      pixels" convention taken to its limit.
    """

    candidates = candidates_for(catalog, constraints)
    definition = select_generation_brick(candidates)

    scene = Scene()

    analysis = generation_input.analysis

    if analysis.occupied_bounds is None:
        return scene

    min_col, min_row, max_col, max_row = analysis.occupied_bounds

    center_col = (min_col + max_col) / 2.0
    center_row = (min_row + max_row) / 2.0

    spacing_x = definition.stud_width * _STUD_LDU
    spacing_z = definition.stud_length * _STUD_LDU

    #
    # Mapped once per dominant color (at most five), never per pixel --
    # analysis.dominant_colors already excludes fully-transparent
    # pixels and is RGB-only, so alpha=255 is always passed and
    # map_color() never returns its is_transparent sentinel here.
    #
    dominant_ldraw_colors = {
        rgb: palette.map_color((*rgb, 255)).color.code
        for rgb in analysis.dominant_colors
    }

    pixels = generation_input.prepared_image.pixels

    for row in range(min_row, max_row + 1):

        for col in range(min_col, max_col + 1):

            r, g, b, alpha = pixels[row, col]

            if alpha <= 0:
                continue

            nearest = _nearest_dominant_color(
                (int(r), int(g), int(b)),
                analysis.dominant_colors,
            )

            x = (col - center_col) * spacing_x
            z = (row - center_row) * spacing_z

            scene.add_brick(
                SceneBrick.from_definition(
                    definition,
                    id=scene.next_available_id(),
                    position=glm.vec3(x, 0.0, z),
                    color_code=dominant_ldraw_colors[nearest],
                )
            )

    return scene
