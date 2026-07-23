"""
BrickForge Image Analysis

Deterministic image-processing primitives that future AI packages will
consume. analyze(image) is the primary entry point -- it produces
ImageStatistics, a plain structured-data result, so a future AI consumer
never needs to decode an image or touch pixels directly. crop(), resize(),
rotate90(), histogram(), average_color(), and to_grayscale() are pure
helper functions: stateless, no hidden state, safe to call independently.

No AI, no palette mapping, no LEGO generation. Independent of engine/,
render/, OpenGL, and ui/ -- depends only on numpy, dataclasses, and
ImageResource.
"""

from dataclasses import dataclass

import numpy as np

from brickforge.io.image_resource import ImageResource

_LUMA_WEIGHTS = np.array(
    [0.2126, 0.7152, 0.0722],
    dtype=np.float32,
)


@dataclass(slots=True)
class ImageStatistics:
    """Structured, deterministic facts about one image."""

    width: int
    height: int
    pixel_count: int
    aspect_ratio: float

    average_color: np.ndarray
    histogram: np.ndarray

    mean_luminance: float
    min_luminance: float
    max_luminance: float
    std_luminance: float


def crop(
    pixels: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Extract a sub-region. Raises ValueError if out of bounds."""

    image_height, image_width = pixels.shape[:2]

    if (
        x < 0
        or y < 0
        or width <= 0
        or height <= 0
        or x + width > image_width
        or y + height > image_height
    ):

        raise ValueError(
            f"Crop region ({x}, {y}, {width}, {height}) is out of "
            f"bounds for a {image_width}x{image_height} image."
        )

    return pixels[y:y + height, x:x + width].copy()


def resize(
    pixels: np.ndarray,
    width: int,
    height: int,
) -> np.ndarray:
    """
    Deterministic nearest-neighbor resize to the given dimensions. No
    interpolation -- every output pixel is copied from exactly one source
    pixel, so the same input always produces the same output.
    """

    source_height, source_width = pixels.shape[:2]

    row_indices = np.clip(
        (
            np.arange(height) * source_height // height
        ),
        0,
        source_height - 1,
    )

    col_indices = np.clip(
        (
            np.arange(width) * source_width // width
        ),
        0,
        source_width - 1,
    )

    return pixels[row_indices][:, col_indices].copy()


def rotate90(
    pixels: np.ndarray,
    degrees: int,
) -> np.ndarray:
    """
    Rotate by a multiple of 90 degrees, clockwise. degrees must be one
    of 0, 90, 180, 270 -- arbitrary angles need an interpolation
    algorithm choice, which is exactly the kind of algorithm-specific
    behavior this module's deterministic primitives avoid; deferred,
    not built here. Verified empirically against numpy's own rotation
    convention: np.rot90's k is counterclockwise, so k = -(degrees // 90)
    gives the clockwise rotation this function promises.
    """

    if degrees not in (0, 90, 180, 270):

        raise ValueError(
            f"rotate90 only supports 0/90/180/270 degrees, got {degrees}."
        )

    if degrees == 0:
        return pixels.copy()

    return np.rot90(
        pixels,
        k=-(degrees // 90),
        axes=(0, 1),
    ).copy()


def to_grayscale(pixels: np.ndarray) -> np.ndarray:
    """Per-pixel luminance (Rec. 709 weights), shape (H, W), uint8."""

    rgb = pixels[:, :, :3].astype(np.float32)

    luminance = rgb @ _LUMA_WEIGHTS

    return np.clip(luminance, 0, 255).astype(np.uint8)


def average_color(pixels: np.ndarray) -> np.ndarray:
    """Mean RGBA color across all pixels, as a (4,) uint8 array."""

    return pixels.reshape(-1, 4).mean(axis=0).astype(np.uint8)


def histogram(
    pixels: np.ndarray,
    bins: int = 256,
) -> np.ndarray:
    """
    Per-channel pixel-value histogram, shape (4, bins) -- R, G, B, A kept
    separate, never combined.
    """

    result = np.empty(
        (4, bins),
        dtype=np.int64,
    )

    for channel in range(4):

        result[channel], _ = np.histogram(
            pixels[:, :, channel],
            bins=bins,
            range=(0, 256),
        )

    return result


def analyze(image: ImageResource) -> ImageStatistics:
    """
    Compute deterministic statistics for a loaded image. The primary
    public entry point -- future packages should consume this rather than
    calling the helper functions individually.
    """

    pixels = image.pixels

    luminance = to_grayscale(pixels).astype(np.float64)

    return ImageStatistics(
        width=image.width,
        height=image.height,
        pixel_count=image.width * image.height,
        aspect_ratio=image.width / image.height,
        average_color=average_color(pixels),
        histogram=histogram(pixels),
        mean_luminance=float(luminance.mean()),
        min_luminance=float(luminance.min()),
        max_luminance=float(luminance.max()),
        std_luminance=float(luminance.std()),
    )
