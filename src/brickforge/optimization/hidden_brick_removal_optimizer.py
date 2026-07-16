"""
BrickForge Hidden Brick Removal Optimizer

Removes any brick that is fully surrounded, on all six sides, by other
bricks sharing its exact part and rotation. Such a brick is never
visible from any exterior viewing angle, so removing it never changes
the model's appearance -- confirmed safe because every SceneBrick this
codebase's generation modes produce is provably opaque (PaletteEngine
only ever maps ColorCategory.SOLID colors, and both Flat Mosaic and
Height Relief skip transparent pixels entirely rather than emitting a
colorless brick), so color is never part of the occlusion check.

"Hidden" is evaluated entirely against the original, unmodified Scene's
brick positions -- a single deterministic pass, not a fixed-point loop
like the Brick Merge optimizer needs. This makes the result inherently
idempotent: a brick that survives one pass (because at least one of its
six neighbors was missing or didn't match) can never become "more
surrounded" in a second pass, since removal only shrinks the position
set that later passes would check against.

Deliberately conservative: requires the covering neighbor to share the
exact same part_name and rotation as the brick being checked, not just
"any brick present" -- this avoids reasoning about whether a
differently-sized or differently-oriented neighbor's footprint actually
covers the checked face. A Scene containing a mix of part sizes (e.g.
after the Brick Merge optimizer has already run) is handled safely:
uniform regions are still correctly detected, mixed boundaries simply
never trigger a false removal.

Depends on engine/ and services/ only through Scene/SceneBrick/
PartCatalog's existing, unmodified public API, exactly like
brick_merge_optimizer.py. Never touches generation/, ui/, or render/,
and does not import from brick_merge_optimizer.py -- kept fully
independent, duplicating the one small physical constant it needs
rather than coupling the two optimizer modules together.
"""

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.models.part_definition import BrickDefinition
from brickforge.optimization.optimizer import Optimizer
from brickforge.optimization.registry import register_optimizer
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDraw units -- the same physical constant every
# generation mode and the Brick Merge optimizer use, redefined here
# (not imported) to keep this optimizer independent.
#
_STUD_LDU = 20.0


def _rotation_key(rotation) -> tuple[float, float, float, float]:

    return (
        rotation.x,
        rotation.y,
        rotation.z,
        rotation.w,
    )


def _position_key(brick: SceneBrick, x: float, y: float, z: float) -> tuple:

    return (
        brick.part_name,
        _rotation_key(brick.rotation),
        x,
        y,
        z,
    )


def _is_hidden(
    brick: SceneBrick,
    definition: BrickDefinition,
    position_index: dict,
) -> bool:
    """
    True if a brick of the exact same part and rotation as `brick`
    exists at all six neighbor offsets (derived from `definition`'s own
    stud_width/stud_length/height_units) within `position_index`.
    """

    spacing_x = definition.stud_width * _STUD_LDU
    spacing_z = definition.stud_length * _STUD_LDU
    spacing_y = definition.height_units

    offsets = (
        (spacing_x, 0.0, 0.0),
        (-spacing_x, 0.0, 0.0),
        (0.0, spacing_y, 0.0),
        (0.0, -spacing_y, 0.0),
        (0.0, 0.0, spacing_z),
        (0.0, 0.0, -spacing_z),
    )

    for dx, dy, dz in offsets:

        key = _position_key(
            brick,
            brick.position.x + dx,
            brick.position.y + dy,
            brick.position.z + dz,
        )

        if key not in position_index:
            return False

    return True


def optimize_hidden_brick_removal(
    scene: Scene,
    catalog: PartCatalog,
) -> Scene:
    """
    Remove every brick that is fully surrounded on all six sides by
    other bricks of the same part and rotation, since such a brick can
    never be visible. A single pass evaluated against the original
    Scene's positions -- see the module docstring for why this makes
    the result inherently idempotent.

    A brick whose part_name doesn't resolve in `catalog` is kept
    unconditionally (its neighbor spacing can't be determined), the
    same graceful-skip convention brick_merge_optimizer.py uses.

    Never mutates the input scene: builds a new Scene, reusing
    surviving SceneBrick instances by reference (they are never
    modified, only kept or dropped).
    """

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    bricks = list(scene)

    position_index: dict[tuple, bool] = {}

    for brick in bricks:

        key = _position_key(
            brick,
            brick.position.x,
            brick.position.y,
            brick.position.z,
        )

        position_index[key] = True

    optimized = Scene()

    for brick in bricks:

        definition = part_index.get(brick.part_name)

        if definition is None:

            optimized.add_brick(brick)
            continue

        if _is_hidden(brick, definition, position_index):
            continue

        optimized.add_brick(brick)

    return optimized


register_optimizer(
    Optimizer(
        id="hidden_brick_removal",
        display_name="Hidden Brick Removal",
        description=(
            "Removes bricks fully surrounded on all six sides by other "
            "bricks of the same part and rotation, since such bricks "
            "can never be visible. Evaluated entirely against the "
            "original Scene in a single deterministic pass."
        ),
        version=1,
        optimize=optimize_hidden_brick_removal,
    )
)
