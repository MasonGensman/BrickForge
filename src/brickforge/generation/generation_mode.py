"""
BrickForge Generation Mode Contract

The registry contract every LEGO model generation mode implements.
Flat Mosaic (generation/mosaic_generator.py) is the first mode to satisfy
it -- this file describes the contract itself, not any specific mode.

Generation Modes are responsible only for producing a valid Scene. They
are never responsible for optimization, pricing, inventory management,
export, or rendering.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtWidgets import QWidget

from brickforge.engine.scene import Scene
from brickforge.io.image_resource import ImageResource
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.services.part_catalog import PartCatalog


class SettingsPanel(Protocol):
    """
    A mode-provided settings UI. The shared UI only ever sees this shape
    -- a widget to embed, and a way to read back the mode's own settings
    object when generation is requested. It never inspects individual
    fields; each mode is free to build whatever controls make sense for
    it (sliders, previews, diagrams, ...) without the shared UI changing.
    """

    @property
    def widget(self) -> QWidget:
        """The Qt widget the shared UI embeds as-is."""
        ...

    def get_settings(self) -> object:
        """The mode's own settings object, built from current control state."""
        ...


class GenerateCallable(Protocol):
    """The shape every mode's generation function must have."""

    def __call__(
        self,
        image: ImageResource,
        palette: PaletteEngine,
        catalog: PartCatalog,
        settings: object,
    ) -> Scene:
        ...


@dataclass(frozen=True, slots=True)
class GenerationMode:
    """
    One registered LEGO model generation mode. Pure registration data --
    the mode's actual generation logic stays a plain function
    (e.g. generate_mosaic), not a method on this class.
    """

    id: str
    display_name: str
    description: str
    version: int
    create_settings_panel: Callable[[], SettingsPanel]
    generate: GenerateCallable
