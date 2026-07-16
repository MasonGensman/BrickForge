"""
BrickForge Optimizer Contract

The registry contract every Scene optimizer implements (Package_020's
approved architecture). An Optimizer is responsible only for improving
a Scene -- it must know nothing about images, image preparation,
generation modes, UI, or the renderer.
"""

from dataclasses import dataclass
from typing import Protocol

from brickforge.engine.scene import Scene
from brickforge.services.part_catalog import PartCatalog


class OptimizeCallable(Protocol):
    """The shape every optimizer's optimize function must have."""

    def __call__(
        self,
        scene: Scene,
        catalog: PartCatalog,
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
