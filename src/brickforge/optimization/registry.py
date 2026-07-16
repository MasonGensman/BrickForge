"""
BrickForge Optimizer Registry

Discovers available Scene optimizers. Deliberately knows nothing about
any specific optimizer -- not brick merging, not any future one.
Optimizers register themselves (see brick_merge_optimizer.py for the
pattern); this module only stores and looks them up.
"""

from brickforge.optimization.optimizer import Optimizer

_registry: dict[str, Optimizer] = {}


def register_optimizer(optimizer: Optimizer) -> None:
    """
    Register one Optimizer. Raises ValueError on a duplicate id -- a
    collision here is a real bug (two optimizers claiming the same
    identity), not something to silently paper over.
    """

    if optimizer.id in _registry:

        raise ValueError(
            f"Optimizer id {optimizer.id!r} is already registered."
        )

    _registry[optimizer.id] = optimizer


def list_optimizers() -> list[Optimizer]:
    """All registered optimizers, in registration order."""

    return list(_registry.values())


def get_optimizer(optimizer_id: str) -> Optimizer | None:
    """Look up one registered optimizer by id, or None if not found."""

    return _registry.get(optimizer_id)
