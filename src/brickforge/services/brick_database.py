"""
Temporary brick database.

Later this will load from BrickLink, Rebrickable,
LDraw, local project files, etc.
"""

from brickforge.models.brick import Brick


class BrickDatabase:
    def __init__(self):

        self._bricks = [

            Brick("3005", "Brick 1x1", "Brick", "Red", 1),
            Brick("3004", "Brick 1x2", "Brick", "Red", 2),
            Brick("3622", "Brick 1x3", "Brick", "Red", 3),
            Brick("3010", "Brick 1x4", "Brick", "Red", 4),
            Brick("3003", "Brick 2x2", "Brick", "Red", 4),
            Brick("3002", "Brick 2x3", "Brick", "Red", 6),
            Brick("3001", "Brick 2x4", "Brick", "Red", 8),
            Brick("3023", "Plate 1x2", "Plate", "Red", 2),
            Brick("3022", "Plate 2x2", "Plate", "Red", 4),
            Brick("3068", "Tile 2x2", "Tile", "Red", 4),

        ]

    def all(self) -> list[Brick]:
        return self._bricks