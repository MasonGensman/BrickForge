"""
BrickForge Scene Exporter

export_scene() is the one public entry point: write a Scene to a .ldr
file that opens correctly in BrickLink Studio. Consumes only Scene and
PartCatalog -- generation, optimization, and rendering all remain
completely unaware this package exists.

PartCatalog is kept as an explicit parameter, not resolved internally
(Package_024 decision): this matches the same dependency-injection
shape GenerationMode.generate() and Optimizer.optimize() already use
throughout this codebase -- callers own and share one PartCatalog
instance, and every pipeline stage that needs one receives it
explicitly rather than each independently resolving its own. Here it
is used for validation only (SceneBrick already carries everything a
Type-1 line structurally needs -- part name, position, rotation,
color): an unrecognized part is written anyway, never silently
dropped, with a logged warning -- export never produces an incomplete
model just because the local catalog happens to be missing metadata
for a part that may well be perfectly valid in BrickLink's own
library.

Never mutates the input Scene -- only reads it. A terminal pipeline
stage: produces a file, not a Scene.
"""

import logging
from pathlib import Path

from brickforge.engine.scene import Scene
from brickforge.export.ldraw_writer import format_type1_line, write_ldraw_file
from brickforge.services.part_catalog import PartCatalog

logger = logging.getLogger(__name__)

#
# LDraw's own "inherit/current color" convention -- used when a
# SceneBrick has no color_code assigned (rare in practice: every
# generation mode skips transparent pixels rather than emitting a
# colorless brick).
#
_DEFAULT_COLOR_CODE = 16


def export_scene(
    scene: Scene,
    catalog: PartCatalog,
    path: str | Path,
) -> None:
    """
    Export scene as a .ldr file at path.

    Deterministic: bricks are written in the Scene's own existing
    order, which is already deterministic -- every generation mode and
    optimizer that could have produced this Scene already guarantees
    that, so no additional sorting is needed here.

    Raises OSError (unwrapped) if the file can't be written. Never
    raises over an individual brick's data -- an unrecognized part is
    validated and warned about, not skipped (see module docstring).
    """

    path = Path(path)
    model_name = path.stem

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    lines = []

    for brick in scene:

        if brick.part_name not in part_index:

            logger.warning(
                "Exporting brick id=%s with unrecognized part %r "
                "(not found in the active catalog) -- writing it "
                "anyway.",
                brick.id,
                brick.part_name,
            )

        color_code = (
            brick.color_code
            if brick.color_code is not None
            else _DEFAULT_COLOR_CODE
        )

        lines.append(
            format_type1_line(
                color_code,
                brick.position,
                brick.rotation,
                brick.part_name,
            )
        )

    write_ldraw_file(path, model_name, lines)
