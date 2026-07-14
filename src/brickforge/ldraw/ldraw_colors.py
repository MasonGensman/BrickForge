"""
BrickForge LDraw Colors

Parses the official LDraw color definitions (LDConfig.ldr). Named
ldraw_colors specifically to leave room for other color systems (BrickLink,
LEGO, Studio, rendering materials) to live alongside it later without a
name collision.
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_COLOUR_LINE = re.compile(
    r"^0\s+!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+(#[0-9A-Fa-f]{6})\s+EDGE\s+(#[0-9A-Fa-f]{6})"
)

_SECTION_LINE = re.compile(
    r"^0\s*//\s*LDraw\s+(.+?)\s+Colours\s*$"
)


class ColorCategory(Enum):
    """
    Which LDConfig.ldr section a color belongs to. Only SOLID colors are
    ordinary opaque plastic -- every other category is a special finish
    (transparent, chrome, metallic, glitter, rubber, ...) and generally
    unsuitable for naive pixel-color matching.
    """

    SOLID = "Solid"
    TRANSPARENT = "Transparent"
    CHROME = "Chrome Plated"
    PEARLESCENT = "Pearlescent Plastic"
    METALLIC = "Metallic Paint"
    FLUORESCENT = "Fluorescent Paint"
    MILKY = "Milky"
    GLITTER = "Glitter"
    OPALESCENT = "Opalescent"
    SPECKLE = "Speckle"
    MODULEX = "Modulex"
    RUBBER = "Rubber"
    TRANSPARENT_RUBBER = "Transparent Rubber"
    FABRIC = "Fabric"
    OBSOLETE = "Obsolete"
    INTERNAL_COMMON_MATERIAL = "Internal Common Material"


@dataclass(slots=True)
class LDrawColor:
    """One entry from LDConfig.ldr."""

    code: int
    name: str
    hex: str
    edge_hex: str
    category: ColorCategory


def load_ldraw_colors(
    config_path: str | Path,
) -> dict[int, LDrawColor]:
    """
    Parse an LDConfig.ldr file into a lookup table of LDrawColor by
    LDraw color code. Each color's ColorCategory is taken from the most
    recent "0 // LDraw <Section> Colours" header line preceding it.
    """

    config_path = Path(config_path)

    colors: dict[int, LDrawColor] = {}

    category: ColorCategory | None = None

    with config_path.open(
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as file:

        for line in file:

            section_match = _SECTION_LINE.match(line)

            if section_match is not None:

                category = ColorCategory(
                    section_match.group(1).strip()
                )

                continue

            match = _COLOUR_LINE.match(line)

            if match is None:
                continue

            if category is None:

                raise ValueError(
                    "Encountered a !COLOUR line before any "
                    f"section header:\n{line.strip()}"
                )

            name, code, hex_value, edge_hex = match.groups()

            code = int(code)

            colors[code] = LDrawColor(
                code=code,
                name=name,
                hex=hex_value,
                edge_hex=edge_hex,
                category=category,
            )

    return colors
