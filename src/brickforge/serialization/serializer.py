"""
StudWorks Scene Serializer

serialize_scene() is the one public entry point for writing a Scene
directly to a file, in StudWorks' native JSON format (schema.py).
scene_to_document() (Package_026) exposes the same conversion as a
plain dict, so a caller that needs to embed a Scene document inside a
larger document (Package_026's Project) doesn't have to round-trip
through a temporary file -- serialize_scene() is now a thin wrapper
around it plus the actual file write.

Never mutates the input Scene. Deterministic: bricks are written in
the Scene's own existing order, already deterministic transitively
from whichever generation/optimization stages produced it -- no
re-sorting here, matching Package_024's exporter's own reasoning.

Full floating-point precision throughout -- unlike Package_024's
LDraw writer, which deliberately truncates to 6 decimal places and
normalizes near-zero noise for clean LDraw output, this format's job
is exact round-trip fidelity. Python's json module encodes floats via
the shortest-round-trip representation, verified during Package_025
planning to reproduce every float64 test value (including -0.0 and
~1e-7 magnitude noise) bit-for-bit -- no custom number formatting is
needed or used here.

One nuance worth understanding, confirmed during verification:
glm.vec3/glm.quat inherently store components as float32, not
float64 -- a value is already truncated to float32 the moment it
enters a SceneBrick (true throughout this codebase, not introduced
here). "Exact round-trip fidelity" means exactly what's actually
stored (the float32-precision value read via .x/.y/.z/.w) survives
serialize -> deserialize unchanged -- not that some hypothetical
higher-precision value that was never really part of the Scene gets
preserved.
"""

import json
from pathlib import Path

from brickforge.engine.scene import Scene
from brickforge.serialization.schema import (
    FORMAT_IDENTIFIER,
    SCHEMA_VERSION,
    quat_to_list,
    vec3_to_list,
)


def scene_to_document(scene: Scene) -> dict:
    """
    Convert scene to its JSON-serializable StudWorks Scene document
    (schema.py) -- the exact shape serialize_scene() writes to disk,
    exposed as a plain dict so callers (e.g. Package_026's Project)
    can embed it inside a larger document.
    """

    bricks = []

    for brick in scene:

        bricks.append({
            "id": brick.id,
            "part_name": brick.part_name,
            "position": vec3_to_list(brick.position),
            "rotation": quat_to_list(brick.rotation),
            "color_code": brick.color_code,
        })

    return {
        "format": FORMAT_IDENTIFIER,
        "schema_version": SCHEMA_VERSION,
        "bricks": bricks,
    }


def serialize_scene(scene: Scene, path: str | Path) -> None:
    """
    Serialize scene to path as StudWorks' native JSON Scene format.

    Raises OSError (unwrapped) if the file can't be written.
    """

    document = scene_to_document(scene)

    path = Path(path)

    with path.open("w", encoding="utf-8") as file:

        json.dump(document, file, indent=2)
        file.write("\n")
