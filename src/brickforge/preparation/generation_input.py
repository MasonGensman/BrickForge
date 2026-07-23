"""
StudWorks Generation Input

The stable boundary between raw user assets and the future generation
pipeline (Package_034): a GenerationInput bundles a reference to a
source image on disk, the deterministic settings used to prepare it,
the resulting prepared ImageResource, and (Package_035) the analysis
computed from it. Future generation packages should consume only
prepared_image/analysis, never touch a raw file directly -- this is the
one place that boundary is crossed.

from_source() is the single canonical way to build a GenerationInput,
used identically at fresh-import time and at project-reload time:
calling it twice with the same path and settings reproduces
byte-identical prepared_image and analysis data, by prepare_image()'s
and analyze_image()'s own determinism guarantees. This is what lets
Project (Package_034) store only source_path + content_hash + settings
and regenerate prepared_image (and, transitively, analysis) on load,
rather than embedding pixel/array data in the project file -- see
Package_034.md and Package_035.md for the full reasoning.
"""

from dataclasses import dataclass
from pathlib import Path

from brickforge.analysis.image_analysis import ImageAnalysisResult, analyze_image
from brickforge.io.image_loader import ImageLoader
from brickforge.io.image_resource import ImageResource
from brickforge.preparation.image_preparation import (
    ImagePreparationSettings,
    prepare_image,
)


@dataclass(slots=True)
class GenerationInput:
    """
    A Project's generation-input asset. prepared_image and analysis are
    held in memory only -- neither is ever serialized, since both are
    fully and deterministically re-derivable from source_path + settings
    via from_source().
    """

    source_path: Path
    content_hash: str
    settings: ImagePreparationSettings
    prepared_image: ImageResource
    analysis: ImageAnalysisResult

    @classmethod
    def from_source(
        cls,
        path: str | Path,
        settings: ImagePreparationSettings | None = None,
    ) -> "GenerationInput":
        """
        Load path, prepare it per settings, analyze the prepared result,
        and bundle everything together. Raises FileNotFoundError/
        ValueError exactly as ImageLoader.load() does -- no new exception
        type, no different failure surface.
        """

        settings = settings or ImagePreparationSettings()

        resource = ImageLoader().load(path)
        prepared = prepare_image(resource, settings)

        return cls(
            source_path=Path(path),
            content_hash=resource.content_hash,
            settings=settings,
            prepared_image=prepared,
            analysis=analyze_image(prepared),
        )
