"""
BrickForge Optimization Pipeline

optimize_scene() is the one public entry point future callers use. It
may run a chain of registered optimizers internally, but a caller
never needs to know that -- matching how mode.generate(...) and
prepare_image(...) already read as single transformations
(Package_020's naming decision).

Optimizers run strictly sequentially, each consuming the Scene the
previous optimizer produced, not the original input Scene. This is
deterministic (registration order is fixed) and is intentional
pipeline design, not an incidental side effect of the loop below: a
later optimizer is expected to see, and may benefit from, geometry an
earlier optimizer has already transformed. Registration order
therefore matters -- see optimization/__init__.py for the order known
optimizer modules are imported in.
"""

from brickforge.engine.scene import Scene
from brickforge.optimization.registry import get_optimizer, list_optimizers
from brickforge.services.part_catalog import PartCatalog


def optimize_scene(
    scene: Scene,
    catalog: PartCatalog,
    optimizer_ids: list[str] | None = None,
) -> Scene:
    """
    Run scene through the given optimizers (or every registered
    optimizer, in registration order, if optimizer_ids is None),
    returning a new, optimized Scene.

    Optimizers are chained sequentially: each one receives the Scene
    the previous optimizer produced, not the original `scene` argument.
    This is deterministic and by design -- see the module docstring.

    Performs no mutation of its own; each optimizer is independently
    responsible for never mutating the Scene it receives.
    """

    ids = (
        optimizer_ids
        if optimizer_ids is not None
        else [optimizer.id for optimizer in list_optimizers()]
    )

    for optimizer_id in ids:

        optimizer = get_optimizer(optimizer_id)

        if optimizer is None:

            raise ValueError(
                f"No optimizer registered with id {optimizer_id!r}"
            )

        scene = optimizer.optimize(scene, catalog)

    return scene
