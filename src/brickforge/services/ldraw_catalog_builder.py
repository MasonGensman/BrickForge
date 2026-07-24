"""
BrickForge LDraw Catalog Builder

Scans an LDraw library's parts/ directory and builds BrickDefinition
objects from confidently-available data: part number, filename,
description, bounding box (when geometry resolves), and -- since
Package_037 -- stud_width/stud_length/height_units/category, each
independently derived from that same bounding box (or, for category,
from the part file's own header) and used only when the derivation can
be validated against the geometry it came from. available_colors,
weight_g, aliases, and family have no reliable source in the LDraw part
format itself (verified during Package_037's inspection: color tokens
in geometry lines are structural "inherit" sentinels, not availability
data; there is no !FAMILY header convention) and are left at their
placeholder defaults -- an explicit, honest "unknown" beats a guess.

Real LEGO parts are geometrically diverse -- slopes, curves, technic,
minifigs, decorated variants -- and most do not reduce to a clean
rectangular-footprint/plate-quantized-height/named-category model.
Package_037's own empirical validation (a 400-part random sample of the
real library) found stud_width/stud_length reliably derivable for ~36%
of parts, height_units for ~54%, and category (from an explicit
!CATEGORY header line) for ~23% -- each field independently, not
all-or-nothing. Where a derivation cannot be validated, the existing
placeholder is left untouched rather than replaced with an unverified
guess -- see _derive_stud_footprint/_derive_height_units/
_extract_category below for the exact validation each applies.
"""

import logging
from pathlib import Path

import numpy as np

from brickforge.ldraw.library import LDrawLibrary
from brickforge.ldraw.library_layout import resolve_parts_directory
from brickforge.models.part_definition import BoundingBox, BrickDefinition

logger = logging.getLogger(__name__)

#
# Conservative placeholders -- not measured, not derived from geometry.
# BrickDefinition.stud_width/stud_length/height_units/category have no
# default, and generate_mosaic() reads stud_width/stud_length
# unconditionally, so every built BrickDefinition needs *some* safe
# value. 1x1 matches the smallest seed-catalog part (safest possible
# footprint if ever selected for generation); 24.0 matches the seed
# catalog's own "Brick" height convention. Used whenever a derivation
# helper below returns None -- i.e. whenever the geometry/header does
# not confidently support a real value.
#
DEFAULT_STUD_WIDTH = 1
DEFAULT_STUD_LENGTH = 1
DEFAULT_HEIGHT_UNITS = 24.0
DEFAULT_CATEGORY = "Part"

#
# 1 LDraw stud = 20 LDU horizontally. A real LEGO stud protrudes 4 LDU
# above a part's body; LEGO System part heights are always a whole
# number of 8-LDU "plate" units. Both empirically confirmed against the
# 10 seed-catalog parts during Package_037's planning (see
# _derive_height_units) before being encoded here as constants.
#
_STUD_LDU = 20.0
_PLATE_HEIGHT_LDU = 8.0
_STUD_HEIGHT_LDU = 4.0

#
# How close a raw derived value must be to a whole unit to be trusted.
# Not zero: real geometry carries float rounding noise from the LDraw
# source data itself, even for parts that are genuinely rectangular.
#
_FOOTPRINT_TOLERANCE_STUDS = 0.05
_HEIGHT_TOLERANCE_LDU = 0.5

_CATEGORY_LINE_PREFIX = "0 !CATEGORY"
_CATEGORY_SCAN_LINE_LIMIT = 40


def _bounding_box(
    vertices: np.ndarray,
) -> BoundingBox | None:

    if vertices.size == 0:
        return None

    points = vertices.reshape(-1, 3)

    return BoundingBox(
        min=tuple(points.min(axis=0).tolist()),
        max=tuple(points.max(axis=0).tolist()),
    )


def _derive_stud_footprint(
    bounding_box: BoundingBox | None,
) -> tuple[int, int] | None:
    """
    (stud_width, stud_length) derived from bounding_box's X/Z extent,
    if and only if both axes land within _FOOTPRINT_TOLERANCE_STUDS of
    a whole number of studs (at least 1 each). None otherwise -- most
    real parts are not rectangular in footprint and correctly produce
    None here (empirically: ~36% of a 400-part real-library sample
    passed this check).

    Independent helper: consumes only bounding_box, produces only this
    one result, never calls or depends on any other derivation helper.
    """

    if bounding_box is None:
        return None

    extent_x = bounding_box.max[0] - bounding_box.min[0]
    extent_z = bounding_box.max[2] - bounding_box.min[2]

    if extent_x <= 0 or extent_z <= 0:
        return None

    width_raw = extent_x / _STUD_LDU
    length_raw = extent_z / _STUD_LDU

    width = round(width_raw)
    length = round(length_raw)

    if width < 1 or length < 1:
        return None

    if (
        abs(width_raw - width) > _FOOTPRINT_TOLERANCE_STUDS
        or abs(length_raw - length) > _FOOTPRINT_TOLERANCE_STUDS
    ):
        return None

    return width, length


def _derive_height_units(
    bounding_box: BoundingBox | None,
) -> float | None:
    """
    height_units derived from bounding_box's Y extent, rounded down to
    the nearest 8-LDU plate unit -- but only if the remainder left over
    is close to 0 (no stud) or close to _STUD_HEIGHT_LDU (one stud
    layer). None otherwise.

    A part's full geometry (including any stud) measures 4 LDU taller
    than its stacking-relevant body height -- confirmed against all 10
    seed-catalog parts during planning: every stud-bearing brick/plate
    measured exactly 4 LDU over its known-correct height_units before
    this adjustment; the one stud-less seed part (a tile) matched
    exactly with no adjustment needed.

    Independent helper: consumes only bounding_box, produces only this
    one result, never calls or depends on any other derivation helper.
    """

    if bounding_box is None:
        return None

    extent_y = bounding_box.max[1] - bounding_box.min[1]

    if extent_y <= 0:
        return None

    rounded_down = (
        int(extent_y) // int(_PLATE_HEIGHT_LDU)
    ) * _PLATE_HEIGHT_LDU

    if rounded_down <= 0:
        return None

    remainder = extent_y - rounded_down

    if (
        remainder <= _HEIGHT_TOLERANCE_LDU
        or abs(remainder - _STUD_HEIGHT_LDU) <= _HEIGHT_TOLERANCE_LDU
    ):
        return float(rounded_down)

    return None


def _extract_category(
    part_file: Path,
) -> str | None:
    """
    The value of a '0 !CATEGORY <name>' header line, if present within
    the first _CATEGORY_SCAN_LINE_LIMIT lines of the file -- the
    official, authoritative LDraw category where present. None
    otherwise -- deliberately no description-based guessing: checked
    during planning against the ~23% of the real library that does
    carry an explicit !CATEGORY line, and a naive "first word of the
    description" heuristic matched only 3 of 488 cases, so it is not
    used here at all.

    Independent helper: reads part_file directly, produces only this
    one result, never calls or depends on any other derivation helper
    (in particular, does not share a pass with, or depend on output
    from, the geometry parser/loader).
    """

    try:

        with part_file.open(
            "r", encoding="utf-8", errors="ignore",
        ) as file:

            for line_number, line in enumerate(file):

                if line_number >= _CATEGORY_SCAN_LINE_LIMIT:
                    break

                if line.startswith(_CATEGORY_LINE_PREFIX):

                    category = line[len(_CATEGORY_LINE_PREFIX):].strip()

                    return category or None

    except OSError:
        return None

    return None


def build_catalog_parts(
    library_path: str | Path,
) -> list[BrickDefinition]:
    """
    Parse every top-level part in the library's parts directory ("parts",
    the official LDraw name, or "part" as a fallback -- see
    ldraw.library_layout; not recursing into parts/s/ subparts, which
    aren't standalone catalog items) and build a BrickDefinition for
    each. Never raises -- returns an empty list if the library or its
    parts directory can't be opened, so a caller can fall back to the
    seed catalog.
    """

    library_path = Path(library_path)
    parts_path = resolve_parts_directory(library_path)

    if not parts_path.is_dir():

        logger.warning(
            "LDraw parts directory not found: %s",
            parts_path,
        )

        return []

    try:
        library = LDrawLibrary(library_path)

    except OSError as error:

        logger.warning(
            "LDraw library could not be opened: %s",
            error,
        )

        return []

    definitions = []

    for entry in sorted(parts_path.iterdir()):

        if (
            not entry.is_file()
            or entry.suffix.lower() != ".dat"
        ):
            continue

        filename = entry.name

        try:
            part = library.load(filename)

        except (OSError, ValueError) as error:

            logger.warning(
                "Skipping unreadable LDraw part %s: %s",
                filename,
                error,
            )

            continue

        #
        # bounding_box is the single source of geometric truth for
        # this part -- computed once here, passed to both geometric
        # derivation helpers below. Each helper is called and its
        # result applied independently: a part can get a real
        # footprint with a placeholder height, or vice versa, per
        # Package_037's "unknown is a valid result" design. The
        # orchestration (calling helpers, choosing derived-vs-default)
        # belongs here alone -- the helpers never call each other.
        #
        bounding_box = _bounding_box(part.vertices)

        footprint = _derive_stud_footprint(bounding_box)
        height_units = _derive_height_units(bounding_box)
        category = _extract_category(entry)

        stud_width, stud_length = (
            footprint
            if footprint is not None
            else (DEFAULT_STUD_WIDTH, DEFAULT_STUD_LENGTH)
        )

        definitions.append(
            BrickDefinition(
                part_number=entry.stem,
                name=part.description or entry.stem,
                category=(
                    category
                    if category is not None
                    else DEFAULT_CATEGORY
                ),
                ldraw_filename=filename,
                stud_width=stud_width,
                stud_length=stud_length,
                height_units=(
                    height_units
                    if height_units is not None
                    else DEFAULT_HEIGHT_UNITS
                ),
                bounding_box=bounding_box,
                description=part.description,
            )
        )

    return definitions
