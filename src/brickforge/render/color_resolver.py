"""
BrickForge Color Resolver

Resolves a SceneBrick.color_code (a raw LDraw color code) to a
ResolvedColor for the renderer -- the one place a color code becomes an
RGB float triple a shader can use. Lookup-only: never touches geometry
(BrickManager's job) or color matching (PaletteEngine's job).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from brickforge.ldraw.ldraw_colors import LDrawColor, load_ldraw_colors

logger = logging.getLogger(__name__)

#
# The renderer's own original hardcoded brick color, preserved as the
# explicit fallback -- a brick with no color_code (every pre-Package_013
# SceneBrick) renders exactly as it always has.
#
DEFAULT_NAME = "Default"
DEFAULT_RGB = (0.80, 0.05, 0.05)


@dataclass(frozen=True, slots=True)
class ResolvedColor:
    """
    Immutable result of resolving one color_code. Carries more than
    Renderer currently needs (rgb only, this package) specifically so
    future rendering, export, debugging, and selection work can reuse
    this same result without another lookup layer.
    """

    code: int | None
    name: str
    rgb: tuple[float, float, float]
    edge_rgb: tuple[float, float, float]


def _hex_to_rgb(
    hex_value: str,
) -> tuple[float, float, float]:

    hex_value = hex_value.lstrip("#")

    return (
        int(hex_value[0:2], 16) / 255.0,
        int(hex_value[2:4], 16) / 255.0,
        int(hex_value[4:6], 16) / 255.0,
    )


class ColorResolver:
    """Resolves SceneBrick.color_code values to ResolvedColor. Lookup-only."""

    def __init__(
        self,
        config_path: str | Path,
    ):

        self._colors: dict[int, LDrawColor] = {}

        try:
            self._colors = load_ldraw_colors(config_path)

        except OSError as error:

            logger.warning(
                "LDraw color config could not be opened, every "
                "brick will use the default color: %s",
                error,
            )

        self._cache: dict[int | None, ResolvedColor] = {}

    def resolve(
        self,
        color_code: int | None,
    ) -> ResolvedColor:
        """
        Resolve one color_code. None, or a code not present in the
        loaded color table, resolves to the default color -- never
        raises.
        """

        if color_code not in self._cache:

            color = (
                self._colors.get(color_code)
                if color_code is not None
                else None
            )

            if color is not None:

                resolved = ResolvedColor(
                    code=color.code,
                    name=color.name,
                    rgb=_hex_to_rgb(color.hex),
                    edge_rgb=_hex_to_rgb(color.edge_hex),
                )

            else:

                resolved = ResolvedColor(
                    code=color_code,
                    name=DEFAULT_NAME,
                    rgb=DEFAULT_RGB,
                    edge_rgb=DEFAULT_RGB,
                )

            self._cache[color_code] = resolved

        return self._cache[color_code]
