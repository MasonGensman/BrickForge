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
"""

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick


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
