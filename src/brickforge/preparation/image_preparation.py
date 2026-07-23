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

Package_018 migrated MainWindow's prior inline resize-to-fit logic here
unchanged in behavior. Package_034 adds crop and rotate (90-degree
multiples only -- arbitrary angles need an interpolation algorithm
choice, deliberately out of scope, see image_analysis.rotate90()),
applied in that order, before the existing fit-to-max_dimension resize:
crop -> rotate -> resize. Stretch, flip, and padding remain deferred --
no current generation mode requires a specific aspect ratio, so padding
would have no real consumer yet.
"""

from dataclasses import dataclass

from brickforge.analysis.image_analysis import crop, resize, rotate90
from brickforge.io.image_resource import ImageResource


@dataclass(slots=True)
class ImagePreparationSettings:
    """
    Configuration for the Image Preparation stage. Deliberately
    independent from GenerationSettings or any other mode's settings
    type -- modes never see this object, only its result.

    max_dimension is an internal default for Package_018, not a
    user-facing control. crop_rect is (x, y, width, height) in the
    source image's own pixel space, or None for no crop.
    rotation_degrees must be 0, 90, 180, or 270.
    """

    max_dimension: int = 48
    crop_rect: tuple[int, int, int, int] | None = None
    rotation_degrees: int = 0


def prepare_image(
    image: ImageResource,
    settings: ImagePreparationSettings | None = None,
) -> ImageResource:
    """
    Deterministically prepare an image for generation: crop (if
    settings.crop_rect is set), then rotate by a 90-degree multiple
    (if settings.rotation_degrees is nonzero), then fit within
    settings.max_dimension on its longer side, preserving aspect
    ratio. Returns the image unchanged (same object) only if every
    step is a no-op. content_hash is always carried over from the
    source image unchanged -- it identifies the source *file*, not
    the prepared pixels (see ImageResource's own docstring).
    """

    settings = settings or ImagePreparationSettings()

    pixels = image.pixels
    width = image.width
    height = image.height
    changed = False

    if settings.crop_rect is not None:

        crop_x, crop_y, crop_width, crop_height = settings.crop_rect

        pixels = crop(pixels, crop_x, crop_y, crop_width, crop_height)
        width, height = crop_width, crop_height
        changed = True

    if settings.rotation_degrees:

        pixels = rotate90(pixels, settings.rotation_degrees)

        if settings.rotation_degrees in (90, 270):
            width, height = height, width

        changed = True

    if (
        width <= settings.max_dimension
        and height <= settings.max_dimension
    ):

        if not changed:
            return image

        return ImageResource(
            path=image.path,
            width=width,
            height=height,
            format=image.format,
            pixels=pixels,
            content_hash=image.content_hash,
        )

    scale = settings.max_dimension / max(width, height)

    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))

    return ImageResource(
        path=image.path,
        width=new_width,
        height=new_height,
        format=image.format,
        pixels=resize(pixels, new_width, new_height),
        content_hash=image.content_hash,
    )
