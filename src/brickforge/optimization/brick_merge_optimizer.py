"""
BrickForge Brick Merge Optimizer

Conservatively replaces groups of identical, adjacent bricks with a
larger equivalent part whenever the catalog declares an exact
dimensional match. No hardcoded part-number table: valid merge targets
are discovered by inspecting the active PartCatalog's own declared
stud_width/stud_length/height_units/category at runtime, so this scales
to any catalog -- larger, smaller, seed, or a future accurately-populated
real-library catalog -- without code changes.

Only merges two bricks placed end-to-end along their shared
stud_length axis (Z-adjacent, same column) with identical part, color,
rotation, and Y layer. Never rotates a replacement part and never
approximates position: the merged brick's position follows the exact
same centered-grid convention the generation pipeline itself already
uses (the midpoint of the two source positions), so a merged brick sits
exactly where the two originals collectively occupied.

Runs its pairwise merge pass to a fixed point (repeating until a full
pass finds nothing left to merge) within one optimize() call. This
guarantees running the optimizer again on an already-optimized Scene
produces an identical Scene -- a merge is never partially applied and
never left for a hypothetical second external call to finish.

Depends on engine/ and services/ only through Scene/SceneBrick/
PartCatalog's existing, unmodified public API. Never touches
generation/, ui/, or render/.
"""

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.models.part_definition import BrickDefinition
from brickforge.optimization.optimizer import Optimizer
from brickforge.optimization.registry import register_optimizer
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDraw units -- the same physical constant every
# generation mode uses, redefined here (not imported) to keep this
# optimizer independent of generation/.
#
_STUD_LDU = 20.0


def _rotation_key(
    rotation: glm.quat,
) -> tuple[float, float, float, float]:

    return (
        rotation.x,
        rotation.y,
        rotation.z,
        rotation.w,
    )


def _find_merge_target(
    source: BrickDefinition,
    catalog: PartCatalog,
) -> BrickDefinition | None:
    """
    Find a catalog part that exactly matches two of `source` placed
    end-to-end along their shared stud_length axis: same category,
    same stud_width, double the stud_length, same height_units.
    Derived entirely from the catalog's own declared dimensions -- no
    hardcoded part-number table -- so a larger or different catalog
    naturally yields different (or no) merge targets without any code
    change here.

    Returns None if no exact match exists. If more than one candidate
    matches, the lowest part_number is chosen, deterministically.
    """

    candidates = [
        definition
        for definition in catalog.all()
        if definition.part_number != source.part_number
        and definition.category == source.category
        and definition.stud_width == source.stud_width
        and definition.stud_length == source.stud_length * 2
        and definition.height_units == source.height_units
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda definition: definition.part_number,
    )


def _merge_pass(
    bricks: list[SceneBrick],
    part_index: dict[str, BrickDefinition],
    target_cache: dict[str, BrickDefinition | None],
    catalog: PartCatalog,
) -> tuple[list[SceneBrick], bool]:
    """
    One deterministic pairwise merge pass over `bricks`.

    Bricks are grouped by (part_name, color_code, rotation, Y, X) --
    everything that must be identical to merge, except the Z position
    used for adjacency. Within each group, bricks are processed in
    ascending Z order; a brick is greedily paired with its immediate
    next-row neighbor when the gap between them exactly equals the
    source part's own stud_length footprint. Each brick is consumed by
    at most one merge. This resolves ties deterministically: for three
    consecutive identical bricks, rows 0-1 merge and row 2 is left
    unmerged, never the other way around.

    Returns (new_bricks, changed).
    """

    groups: dict[tuple, list[SceneBrick]] = {}

    for brick in bricks:

        key = (
            brick.part_name,
            brick.color_code,
            _rotation_key(brick.rotation),
            brick.position.y,
            brick.position.x,
        )

        groups.setdefault(key, []).append(brick)

    result: list[SceneBrick] = []
    changed = False

    for key, group in groups.items():

        part_name = key[0]

        source = part_index.get(part_name)

        if source is None:

            result.extend(group)
            continue

        if part_name not in target_cache:
            target_cache[part_name] = _find_merge_target(
                source,
                catalog,
            )

        target = target_cache[part_name]

        if target is None:

            result.extend(group)
            continue

        ordered = sorted(
            group,
            key=lambda brick: brick.position.z,
        )

        expected_gap = source.stud_length * _STUD_LDU

        index = 0

        while index < len(ordered):

            if index + 1 < len(ordered):

                brick_a = ordered[index]
                brick_b = ordered[index + 1]

                gap = brick_b.position.z - brick_a.position.z

                if gap == expected_gap:

                    merged_position = glm.vec3(
                        (brick_a.position.x + brick_b.position.x) / 2.0,
                        (brick_a.position.y + brick_b.position.y) / 2.0,
                        (brick_a.position.z + brick_b.position.z) / 2.0,
                    )

                    result.append(
                        SceneBrick(
                            id=min(brick_a.id, brick_b.id),
                            part_name=target.part_name,
                            position=merged_position,
                            rotation=brick_a.rotation,
                            color_code=brick_a.color_code,
                        )
                    )

                    changed = True
                    index += 2
                    continue

            result.append(ordered[index])
            index += 1

    return result, changed


def optimize_brick_merge(
    scene: Scene,
    catalog: PartCatalog,
) -> Scene:
    """
    Conservatively merge groups of identical, adjacent bricks into
    larger equivalent parts wherever the active catalog declares an
    exact dimensional match. Repeats to a fixed point within this one
    call, so calling this again on the result finds nothing further to
    merge -- the second call's first internal pass immediately reports
    no change.

    Never mutates the input scene: builds new SceneBrick and Scene
    objects throughout. Bricks that are never touched by any merge are
    reused by reference (they are read-only in practice), matching the
    same convention prepare_image() uses for unmodified images.
    """

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    target_cache: dict[str, BrickDefinition | None] = {}

    bricks = list(scene)

    while True:

        bricks, changed = _merge_pass(
            bricks,
            part_index,
            target_cache,
            catalog,
        )

        if not changed:
            break

    optimized = Scene()

    for brick in bricks:
        optimized.add_brick(brick)

    return optimized


register_optimizer(
    Optimizer(
        id="brick_merge",
        display_name="Brick Merge",
        description=(
            "Conservatively replaces groups of identical, adjacent "
            "bricks with a larger equivalent part whenever the active "
            "catalog declares an exact dimensional match. Never "
            "approximates; runs to a fixed point so re-running it "
            "finds nothing further to merge."
        ),
        version=1,
        optimize=optimize_brick_merge,
    )
)
