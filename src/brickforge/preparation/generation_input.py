"""
StudWorks Generation Input

The stable boundary between raw user assets and the future generation
pipeline (Package_034): a GenerationInput bundles a reference to a
source image on disk, the deterministic settings used to prepare it,
and the resulting prepared ImageResource. Future generation/analysis
packages should consume only prepared_image, never touch a raw file
directly -- this is the one place that boundary is crossed.

from_source() is the single canonical way to build a GenerationInput,
used identically at fresh-import time and at project-reload time:
calling it twice with the same path and settings reproduces
byte-identical prepared_image data, by prepare_image()'s own
determinism guarantee. This is what lets Project (Package_034) store
only source_path + content_hash + settings and regenerate
prepared_image on load, rather than embedding pixel data in the
project file -- see Package_034.md for the full reasoning.
"""

from dataclasses import dataclass
from pathlib import Path

from brickforge.io.image_loader import ImageLoader
from brickforge.io.image_resource import ImageResource
from brickforge.preparation.image_preparation import (
    ImagePreparationSettings,
    prepare_image,
)


@dataclass(slots=True)
class GenerationInput:
    """
    A Project's generation-input asset. prepared_image is held in
    memory only -- it is never serialized, since it's fully and
    deterministically re-derivable from source_path + settings via
    from_source().
    """

    source_path: Path
    content_hash: str
    settings: ImagePreparationSettings
    prepared_image: ImageResource

    @classmethod
    def from_source(
        cls,
        path: str | Path,
        settings: ImagePreparationSettings | None = None,
    ) -> "GenerationInput":
        """
        Load path, prepare it per settings, and bundle the result.
        Raises FileNotFoundError/ValueError exactly as ImageLoader.load()
        does -- no new exception type, no different failure surface.
        """

        settings = settings or ImagePreparationSettings()

        resource = ImageLoader().load(path)

        return cls(
            source_path=Path(path),
            content_hash=resource.content_hash,
            settings=settings,
            prepared_image=prepare_image(resource, settings),
        )
