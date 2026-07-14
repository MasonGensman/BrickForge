"""
BrickForge LDraw Colors

Parses the official LDraw color definitions (LDConfig.ldr). Named
ldraw_colors specifically to leave room for other color systems (BrickLink,
LEGO, Studio, rendering materials) to live alongside it later without a
name collision.
"""

import re
from dataclasses import dataclass
from pathlib import Path

_COLOUR_LINE = re.compile(
    r"^0\s+!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+(#[0-9A-Fa-f]{6})\s+EDGE\s+(#[0-9A-Fa-f]{6})"
)


@dataclass(slots=True)
class LDrawColor:
    """One entry from LDConfig.ldr."""

    code: int
    name: str
    hex: str
    edge_hex: str


def load_ldraw_colors(
    config_path: str | Path,
) -> dict[int, LDrawColor]:
    """
    Parse an LDConfig.ldr file into a lookup table of LDrawColor by
    LDraw color code.
    """

    config_path = Path(config_path)

    colors: dict[int, LDrawColor] = {}

    with config_path.open(
        "r",
        encoding="utf-8",
        errors="ignore",
    ) as file:

        for line in file:

            match = _COLOUR_LINE.match(line)

            if match is None:
                continue

            name, code, hex_value, edge_hex = match.groups()

            code = int(code)

            colors[code] = LDrawColor(
                code=code,
                name=name,
                hex=hex_value,
                edge_hex=edge_hex,
            )

    return colors
