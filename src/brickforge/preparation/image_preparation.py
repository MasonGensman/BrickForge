"""
BrickForge Image Preparation

The shared stage between Image Import and every Generation Mode. Image
Preparation is deterministic, stateless, and generation-mode agnostic --
it performs pure image transformations only, never anything a specific
mode would care about (part selection, color mapping, brick placement).

Every Generation Mode receives an already-prepared ImageResource through
the existing, unmodified GenerateCallable contract -- prepare_image()
returns a plain ImageResource, so no mode needs to know this stage
exists.

Package_018 migrates MainWindow's prior inline resize-to-fit logic here
unchanged in behavior: prepare_image()'s default (and, for this package,
only) transform reproduces that exact math. Additional transforms
(stretch, crop, rotate, flip, padding) are deliberately deferred to
future packages -- this one's purpose is relocating existing behavior
into shared, reusable infrastructure, not expanding it.
"""

from dataclasses import dataclass

from brickforge.analysis.image_analysis import resize
from brickforge.io.image_resource import ImageResource


@dataclass(slots=True)
class ImagePreparationSettings:
    """
    Configuration for the Image Preparation stage. Deliberately
    independent from GenerationSettings or any other mode's settings
    type -- modes never see this object, only its result.

    max_dimension is an internal default for Package_018, not a
    user-facing control.
    """

    max_dimension: int = 48


def prepare_image(
    image: ImageResource,
    settings: ImagePreparationSettings | None = None,
) -> ImageResource:
    """
    Deterministically fit an image within settings.max_dimension on its
    longer side, preserving aspect ratio. Returns the image unchanged
    (same object) if it's already within bounds on both axes.
    """

    settings = settings or ImagePreparationSettings()

    if (
        image.width <= settings.max_dimension
        and image.height <= settings.max_dimension
    ):
        return image

    scale = settings.max_dimension / max(
        image.width,
        image.height,
    )

    new_width = max(1, round(image.width * scale))
    new_height = max(1, round(image.height * scale))

    return ImageResource(
        path=image.path,
        width=new_width,
        height=new_height,
        format=image.format,
        pixels=resize(image.pixels, new_width, new_height),
        content_hash=image.content_hash,
    )
