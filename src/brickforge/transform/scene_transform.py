"""
StudWorks Scene Transform

The engine future editing tools (Move, Rotate, Duplicate, ...) will
build on -- not a tool itself. A stateless plain function, matching
every other Scene -> Scene pipeline stage in this codebase
(optimize_scene, export_scene, scene_to_document): there is no
per-call state to hold, so there is no manager/service class here.

Immutable by the same convention already established by
optimization/pipeline.py and brick_merge_optimizer.py: replace_brick
builds a new Scene, reusing every untouched SceneBrick by reference
and substituting only the target. Neither the input Scene nor any
SceneBrick is ever mutated.

A transform's output Scene always has the exact same id set as its
input, or a strict subset -- replace_brick performs a one-for-one
swap (same id set), remove_brick a strict removal (smaller id set),
neither ever an insert. Either way the output's id set is never
*larger* than the input's, which is what lets
MainWindow.set_current_scene() tell any Transform's output apart from
a New/Open/Generate replacement (an unrelated, typically larger or
disjoint id set) without being told which case it is (see
Package_028.md) -- and, for remove_brick specifically, is exactly why
a deleted brick's selection clears for free: its id is provably absent
from the result.

remove_brick(scene, brick_id) intentionally shares its name with the
existing Scene.remove_brick(brick_id) (Package_021, used internally by
the Brick Merge / Hidden Brick Removal optimizers) despite that method
mutating in place -- the two are disambiguated by calling convention
at every call site (scene.remove_brick(id) vs. remove_brick(scene, id))
the same way replace_brick(scene, brick) already reads distinctly from
a hypothetical scene.replace(...) method. Scene.remove_brick() is left
exactly as it was; remove_brick() below never calls it, building a
fresh Scene by filtering during iteration instead, the same pattern
replace_brick already uses (Package_032).

duplicate_brick(scene, brick_id) is the one operation here whose id
set *grows* -- and the one function in this module that returns more
than a Scene. Its (Scene, new_id) return isn't an inconsistency with
replace_brick/remove_brick's plain Scene return; it's a genuine
difference in what each operation's caller needs: a modify or removal
is fully described by the id the caller already gave it, but a
duplicate creates an id the caller has no way to know in advance
without redundantly re-deriving it (e.g. diffing before/after id
sets). Forcing replace_brick/remove_brick into a matching tuple shape
for cosmetic symmetry was considered and declined -- it would give
every existing caller a meaningless second value for no benefit
(Package_033).
"""

import dataclasses

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick

#
# One stud (the same _STUD_LDU constant every generation mode uses),
# along +X. Fixed and deterministic rather than derived from the
# duplicated part's actual footprint: Transform functions deliberately
# take no PartCatalog (Package_025's established precedent), and a
# bare SceneBrick doesn't carry stud_width/stud_length, so there's no
# footprint to derive it from. This satisfies "a translated position
# to avoid occupying exactly the same location" -- it does not
# guarantee no visual overlap for parts larger than 1x1, and doesn't
# check for or avoid collision with any other existing brick's
# position either; nothing else in Scene/SceneBrick/Move has ever
# prevented bricks from overlapping, so Duplicate doesn't introduce
# that check just for itself.
#
_DUPLICATE_OFFSET = glm.vec3(20.0, 0.0, 0.0)


class TransformError(Exception):
    """Raised when a transform can't be applied -- e.g. no brick with
    the given id exists in the Scene. Never raised for a problem with
    the Scene's own structure; that's Scene/serialization's job."""


def replace_brick(
    scene: Scene,
    updated_brick: SceneBrick,
) -> Scene:
    """
    Return a new Scene with updated_brick substituted for the
    existing brick that shares its id, preserving every other brick
    unchanged (by reference). Raises TransformError if updated_brick.id
    doesn't match any brick currently in scene.
    """

    if scene.get(updated_brick.id) is None:

        raise TransformError(
            f"No brick with id {updated_brick.id} in this Scene."
        )

    new_scene = Scene()

    for brick in scene:

        new_scene.add_brick(
            updated_brick if brick.id == updated_brick.id else brick
        )

    return new_scene


def remove_brick(
    scene: Scene,
    brick_id: int,
) -> Scene:
    """
    Return a new Scene with the brick matching brick_id removed,
    preserving every other brick unchanged (by reference) and in
    order. Raises TransformError if brick_id doesn't match any brick
    currently in scene. Removing the last brick in a Scene produces a
    valid, ordinary empty Scene -- not a special case.
    """

    if scene.get(brick_id) is None:

        raise TransformError(
            f"No brick with id {brick_id} in this Scene."
        )

    new_scene = Scene()

    for brick in scene:

        if brick.id != brick_id:
            new_scene.add_brick(brick)

    return new_scene


def duplicate_brick(
    scene: Scene,
    brick_id: int,
) -> tuple[Scene, int]:
    """
    Return a new Scene with a copy of the brick matching brick_id
    appended -- same part_name, rotation, and color_code, a freshly
    generated unique id (scene.next_available_id()), and a position
    offset by _DUPLICATE_OFFSET so it doesn't occupy exactly the same
    location. The original brick is unchanged and still present.
    Raises TransformError if brick_id doesn't match any brick
    currently in scene.

    Returns (new_scene, new_id) -- see the module docstring for why
    this is the one function here that returns more than a Scene.
    """

    original = scene.get(brick_id)

    if original is None:

        raise TransformError(
            f"No brick with id {brick_id} in this Scene."
        )

    new_id = scene.next_available_id()

    duplicate = dataclasses.replace(
        original,
        id=new_id,
        position=original.position + _DUPLICATE_OFFSET,
    )

    new_scene = Scene()

    for brick in scene:
        new_scene.add_brick(brick)

    new_scene.add_brick(duplicate)

    return new_scene, new_id
