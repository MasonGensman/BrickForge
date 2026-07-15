"""
BrickForge LDraw Catalog Builder

Scans an LDraw library's parts/ directory and builds BrickDefinition
objects from confidently-available data only: part number, filename,
description, and bounding box (when geometry resolves). Everything else
-- stud_width, stud_length, height_units, category, available_colors,
weight_g, aliases, family -- is left at conservative, documented
placeholder defaults, not derived and not guessed. Replacing these
placeholders with real values (measured or curated) is future
metadata-enrichment work, not this package's job.
"""

import logging
from pathlib import Path

import numpy as np

from brickforge.ldraw.library import LDrawLibrary
from brickforge.models.part_definition import BoundingBox, BrickDefinition

logger = logging.getLogger(__name__)

#
# Conservative placeholders -- not measured, not derived from geometry.
# BrickDefinition.stud_width/stud_length/height_units/category have no
# default, and generate_mosaic() reads stud_width/stud_length
# unconditionally, so every built BrickDefinition needs *some* safe
# value. 1x1 matches the smallest seed-catalog part (safest possible
# footprint if ever selected for generation); 24.0 matches the seed
# catalog's own "Brick" height convention.
#
DEFAULT_STUD_WIDTH = 1
DEFAULT_STUD_LENGTH = 1
DEFAULT_HEIGHT_UNITS = 24.0
DEFAULT_CATEGORY = "Part"


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


def build_catalog_parts(
    library_path: str | Path,
) -> list[BrickDefinition]:
    """
    Parse every top-level part in library_path/"parts" (not recursing
    into parts/s/ subparts, which aren't standalone catalog items) and
    build a BrickDefinition for each. Never raises -- returns an empty
    list if the library or its parts directory can't be opened, so a
    caller can fall back to the seed catalog.
    """

    library_path = Path(library_path)
    parts_path = library_path / "parts"

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

        definitions.append(
            BrickDefinition(
                part_number=entry.stem,
                name=part.description or entry.stem,
                category=DEFAULT_CATEGORY,
                ldraw_filename=filename,
                stud_width=DEFAULT_STUD_WIDTH,
                stud_length=DEFAULT_STUD_LENGTH,
                height_units=DEFAULT_HEIGHT_UNITS,
                bounding_box=_bounding_box(part.vertices),
                description=part.description,
            )
        )

    return definitions
