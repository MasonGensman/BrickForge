"""
BrickForge Image Analysis

Deterministic image-processing primitives that future generation packages
will consume. analyze_image(image) is the primary entry point -- it
produces ImageAnalysisResult, a plain structured-data result, so a future
consumer never needs to decode an image or touch pixels directly. crop(),
resize(), rotate90(), histogram(), average_color(), to_grayscale(),
sobel_edges(), dominant_colors(), and occupied_bounds() are pure helper
functions: stateless, no hidden state, safe to call independently.

Region segmentation, connected components, contours, and generic
"feature extraction" are deliberately not built here -- no concrete
consumer needs them yet, and they lean toward algorithm-specific/AI
interpretation rather than the deterministic primitives this module is
scoped to (Package_035).

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

_DOMINANT_COLOR_COUNT = 5
_DOMINANT_COLOR_BUCKET_SIZE = 16
_EDGE_DENSITY_THRESHOLD = 128


@dataclass(slots=True)
class ImageAnalysisResult:
    """Structured, deterministic facts about one image."""

    width: int
    height: int
    pixel_count: int
    aspect_ratio: float

    average_color: np.ndarray
    histogram: np.ndarray
    dominant_colors: list[tuple[int, int, int]]

    mean_luminance: float
    min_luminance: float
    max_luminance: float
    std_luminance: float

    edges: np.ndarray
    edge_density: float

    occupied_bounds: tuple[int, int, int, int] | None


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


def sobel_edges(pixels: np.ndarray) -> np.ndarray:
    """
    Per-pixel Sobel edge magnitude, shape (H, W), uint8. Operates on
    to_grayscale()'s luminance output. Border pixels use edge-replicated
    padding, so the result is always the same shape as the input --
    verified empirically against a known vertical boundary before
    building this: response is 0 away from an edge, 255 (clipped) at it.
    """

    gray = to_grayscale(pixels).astype(np.float32)
    padded = np.pad(gray, 1, mode="edge")

    top_left = padded[0:-2, 0:-2]
    top_center = padded[0:-2, 1:-1]
    top_right = padded[0:-2, 2:]
    mid_left = padded[1:-1, 0:-2]
    mid_right = padded[1:-1, 2:]
    bottom_left = padded[2:, 0:-2]
    bottom_center = padded[2:, 1:-1]
    bottom_right = padded[2:, 2:]

    gradient_x = (top_right + 2 * mid_right + bottom_right) - (
        top_left + 2 * mid_left + bottom_left
    )
    gradient_y = (bottom_left + 2 * bottom_center + bottom_right) - (
        top_left + 2 * top_center + top_right
    )

    magnitude = np.sqrt(gradient_x ** 2 + gradient_y ** 2)

    return np.clip(magnitude, 0, 255).astype(np.uint8)


def dominant_colors(
    pixels: np.ndarray,
    count: int = _DOMINANT_COLOR_COUNT,
) -> list[tuple[int, int, int]]:
    """
    The `count` most common colors, most frequent first. Deterministic
    bucket-quantization (not k-means, which needs an iterative or
    random-init algorithm to be reproducible): each RGB channel is
    rounded down to a multiple of _DOMINANT_COLOR_BUCKET_SIZE, then
    bucket frequency is counted. Fully-transparent pixels (alpha == 0)
    are excluded -- they aren't visible content. Ties are broken by the
    bucket's own RGB tuple so ordering never depends on Python's
    iteration/hashing order.
    """

    flat = pixels.reshape(-1, 4)
    opaque_rgb = flat[flat[:, 3] > 0][:, :3]

    if opaque_rgb.size == 0:
        return []

    quantized = (
        opaque_rgb.astype(np.int64) // _DOMINANT_COLOR_BUCKET_SIZE
    ) * _DOMINANT_COLOR_BUCKET_SIZE

    buckets, counts = np.unique(quantized, axis=0, return_counts=True)

    order = sorted(
        range(len(buckets)),
        key=lambda i: (-int(counts[i]), tuple(int(c) for c in buckets[i])),
    )

    return [tuple(int(c) for c in buckets[i]) for i in order[:count]]


def occupied_bounds(pixels: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    Bounding box (min_x, min_y, max_x, max_y) of every pixel with
    alpha > 0. None if the image is fully transparent -- there is no
    content to bound.
    """

    rows, cols = np.where(pixels[:, :, 3] > 0)

    if rows.size == 0:
        return None

    return (
        int(cols.min()), int(rows.min()),
        int(cols.max()), int(rows.max()),
    )


def analyze_image(image: ImageResource) -> ImageAnalysisResult:
    """
    Compute deterministic analysis facts for a loaded image. The primary
    public entry point -- future packages should consume this rather than
    calling the helper functions individually.
    """

    pixels = image.pixels

    luminance = to_grayscale(pixels).astype(np.float64)
    edge_map = sobel_edges(pixels)

    return ImageAnalysisResult(
        width=image.width,
        height=image.height,
        pixel_count=image.width * image.height,
        aspect_ratio=image.width / image.height,
        average_color=average_color(pixels),
        histogram=histogram(pixels),
        dominant_colors=dominant_colors(pixels),
        mean_luminance=float(luminance.mean()),
        min_luminance=float(luminance.min()),
        max_luminance=float(luminance.max()),
        std_luminance=float(luminance.std()),
        edges=edge_map,
        edge_density=float(
            (edge_map > _EDGE_DENSITY_THRESHOLD).mean()
        ),
        occupied_bounds=occupied_bounds(pixels),
    )
