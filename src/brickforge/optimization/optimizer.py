"""
BrickForge Optimizer Contract

The registry contract every Scene optimizer implements (Package_020's
approved architecture, extended in Package_039). An Optimizer is
responsible only for improving a Scene -- it must know nothing about
images, image preparation, generation modes, UI, or the renderer.

Package_039 widened OptimizeCallable with a constraints parameter so
optimizers that select or replace bricks can route candidate discovery
through generation.candidates.candidates_for() (Package_036) rather
than scanning PartCatalog directly -- the same architectural boundary
Package_038's generation engine already established. Every registered
optimizer must accept the parameter even if it never uses it (an
optimizer that only inspects or removes already-placed bricks, never
introducing a new one, has nothing to constrain) -- a uniform shape
across every optimizer, matching how GenerationMode.generate() already
requires every mode to accept a palette parameter even though not every
mode necessarily depends on it in the same way.
"""

from dataclasses import dataclass
from typing import Protocol

from brickforge.engine.scene import Scene
from brickforge.generation.candidates import GenerationConstraints
from brickforge.services.part_catalog import PartCatalog


class OptimizeCallable(Protocol):
    """The shape every optimizer's optimize function must have."""

    def __call__(
        self,
        scene: Scene,
        catalog: PartCatalog,
        constraints: GenerationConstraints | None,
    ) -> Scene:
        ...


@dataclass(frozen=True, slots=True)
class Optimizer:
    """
    One registered Scene optimizer. Pure registration data -- the
    optimizer's actual logic stays a plain function, not a method on
    this class, matching how GenerationMode wraps generate_mosaic().
    """

    id: str
    display_name: str
    description: str
    version: int
    optimize: OptimizeCallable
