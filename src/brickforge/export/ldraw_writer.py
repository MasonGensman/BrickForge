"""
BrickForge LDraw Writer

Low-level LDraw text formatting: converting one SceneBrick's data into
a Type-1 line, and assembling a complete .ldr file's text. Pure
string/number formatting -- no Scene/PartCatalog knowledge, no file
I/O beyond the one write in write_ldraw_file().

Rotation conversion (glm.quat -> LDraw's row-major 3x3 matrix) is
centralized here as the one place that does it. PyGLM's mat3_cast
stores column-major (matrix[col][row]), so extracting LDraw's
row-major a..i values requires matrix[col][row] with column and row
swapped from what "row-major" might suggest at a glance -- verified
during Package_024 planning against a known 90-degree-around-Y case
(m * (1,0,0) = (0,0,-1), matching the derived matrix exactly) so this
isn't re-derived incorrectly later.

Positions and rotations are used exactly as given: StudWorks'
generation pipeline already produces native LDraw coordinates (no
transform is applied anywhere from part parsing through to SceneBrick
placement, confirmed during Package_024 planning), so no coordinate
conversion happens anywhere in this module.
"""

from pathlib import Path

import glm

from brickforge._version import APP_NAME

#
# Half a unit in the last displayed decimal place (.6f => 1e-6):
# anything smaller than this rounds to "0.000000" at that precision
# regardless, so normalizing it to exactly +0.0 first avoids a
# "-0.000000" artifact for small negative noise. Verified empirically
# during Package_024 planning/testing that glm's own quaternion math
# produces noise around 6e-8 for "clean" angles (e.g. 90 degrees) --
# comfortably caught by this threshold.
#
_NEAR_ZERO = 5e-7


def _format_number(value: float) -> str:
    """
    Deterministic, fixed-point formatting -- never scientific
    notation, and floating-point noise near zero (e.g. glm's own
    ~1e-7 artifacts from quaternion math) is normalized to a clean
    "0.000000" rather than "-0.000000".
    """

    if abs(value) < _NEAR_ZERO:
        value = 0.0

    return f"{value:.6f}"


def rotation_to_ldraw_matrix(
    rotation: glm.quat,
) -> tuple[
    float, float, float,
    float, float, float,
    float, float, float,
]:
    """
    Convert a rotation quaternion to LDraw's row-major 3x3 transform
    matrix (a b c / d e f / g h i, per the Type-1 line format
    LDrawParser already reads). The one place this conversion happens.
    """

    matrix = glm.mat3_cast(rotation)

    return (
        matrix[0][0], matrix[1][0], matrix[2][0],
        matrix[0][1], matrix[1][1], matrix[2][1],
        matrix[0][2], matrix[1][2], matrix[2][2],
    )


def format_type1_line(
    color_code: int,
    position: glm.vec3,
    rotation: glm.quat,
    part_name: str,
) -> str:
    """Format one brick as an LDraw Type-1 line."""

    a, b, c, d, e, f, g, h, i = rotation_to_ldraw_matrix(rotation)

    numbers = (
        position.x, position.y, position.z,
        a, b, c,
        d, e, f,
        g, h, i,
    )

    formatted = " ".join(
        _format_number(value)
        for value in numbers
    )

    return f"1 {color_code} {formatted} {part_name}"


def write_ldraw_file(
    path: str | Path,
    model_name: str,
    lines: list[str],
) -> None:
    """
    Write a complete, minimal but valid .ldr file: a short descriptive
    header followed by one line per brick, in the order given.

    Raises OSError (unwrapped) on any write failure -- callers must
    know export failed, not have it silently swallowed.
    """

    header = [
        f"0 {model_name}",
        f"0 Name: {model_name}",
        f"0 Author: {APP_NAME}",
        "",
    ]

    path = Path(path)

    with path.open("w", encoding="utf-8") as file:

        for line in header:
            file.write(line + "\n")

        for line in lines:
            file.write(line + "\n")
