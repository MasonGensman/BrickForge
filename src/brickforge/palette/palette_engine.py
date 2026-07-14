"""
BrickForge Palette Engine

Deterministic mapping from arbitrary RGBA pixel colors to the nearest
solid LEGO/LDraw color. map_color(rgba) is the one public entry point --
future packages (Brick Generator, AI Optimization) should never need to
implement color matching themselves.

No AI, no brick generation, no scene generation. Independent of engine/,
render/, OpenGL, and ui/ -- depends only on numpy, dataclasses, and
brickforge.ldraw.ldraw_colors.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from brickforge.ldraw.ldraw_colors import (
    ColorCategory,
    LDrawColor,
    load_ldraw_colors,
)

DEFAULT_ALPHA_THRESHOLD = 16


@dataclass(slots=True)
class MappedColor:
    """Result of matching one RGBA pixel to the nearest LDraw color."""

    color: LDrawColor | None
    distance: float | None
    is_transparent: bool


def _hex_to_rgb(
    hex_value: str,
) -> tuple[int, int, int]:

    hex_value = hex_value.lstrip("#")

    return (
        int(hex_value[0:2], 16),
        int(hex_value[2:4], 16),
        int(hex_value[4:6], 16),
    )


def _redmean_distance(
    rgb: np.ndarray,
    palette_rgb: np.ndarray,
) -> np.ndarray:
    """
    Weighted RGB distance ("redmean") from one color to every row of a
    palette array. A low-cost, deterministic correction for plain
    Euclidean RGB distance's known green-channel under-weighting.
    """

    r1, g1, b1 = rgb[0], rgb[1], rgb[2]

    r2 = palette_rgb[:, 0]
    g2 = palette_rgb[:, 1]
    b2 = palette_rgb[:, 2]

    r_mean = (r1 + r2) / 2.0

    delta_r = r1 - r2
    delta_g = g1 - g2
    delta_b = b1 - b2

    return np.sqrt(
        (2 + r_mean / 256) * delta_r ** 2
        + 4 * delta_g ** 2
        + (2 + (255 - r_mean) / 256) * delta_b ** 2
    )


class PaletteEngine:
    """
    Matches arbitrary RGBA colors to the nearest solid LDraw color.

    Loads and filters the palette once at construction; map_color() is
    then cheap to call repeatedly without re-parsing or re-filtering.
    """

    def __init__(
        self,
        config_path: str | Path,
        alpha_threshold: int = DEFAULT_ALPHA_THRESHOLD,
    ):

        self.alpha_threshold = alpha_threshold

        all_colors = load_ldraw_colors(config_path)

        self._colors: list[LDrawColor] = [
            color
            for color in all_colors.values()
            if color.category is ColorCategory.SOLID
        ]

        self._palette_rgb = np.array(
            [
                _hex_to_rgb(color.hex)
                for color in self._colors
            ],
            dtype=np.float64,
        )

    def map_color(
        self,
        rgba,
    ) -> MappedColor:
        """
        Match one RGBA color to the nearest solid LDraw color.

        Returns a transparent sentinel (color=None, distance=None,
        is_transparent=True) if alpha is below alpha_threshold, rather
        than forcing a match onto an effectively-transparent pixel.
        """

        r, g, b, a = rgba

        if a < self.alpha_threshold:

            return MappedColor(
                color=None,
                distance=None,
                is_transparent=True,
            )

        rgb = np.array(
            [r, g, b],
            dtype=np.float64,
        )

        distances = _redmean_distance(
            rgb,
            self._palette_rgb,
        )

        index = int(np.argmin(distances))

        return MappedColor(
            color=self._colors[index],
            distance=float(distances[index]),
            is_transparent=False,
        )
