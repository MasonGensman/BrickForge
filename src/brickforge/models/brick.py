"""
BrickForge Brick Model

Represents a single LEGO brick.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Brick:
    """Represents one LEGO element."""

    part_number: str
    name: str
    category: str
    color: str
    studs: int