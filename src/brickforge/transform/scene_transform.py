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
input -- replace_brick performs a strict one-for-one swap, never an
insert or removal -- which is what lets MainWindow.set_current_scene()
tell a Transform's output apart from a New/Open/Generate replacement
without being told which case it is (see Package_028.md).
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
