"""
BrickForge Brick Model
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Brick:
    """Represents a LEGO element."""

    part_number: str
    name: str
    category: str
    color: str
    studs: int

    def __str__(self) -> str:
        return f"{self.part_number} - {self.name}"