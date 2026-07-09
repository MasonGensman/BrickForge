"""
BrickForge LDraw Loader
"""

from pathlib import Path

from brickforge.ldraw.parser import LDrawParser
from brickforge.ldraw.part import Part


class LDrawLoader:
    """Loads parts from an LDraw library."""

    def __init__(self, library_path: str | Path):

        self.library_path = Path(library_path)

        self.parser = LDrawParser()

    def load_part(
        self,
        filename: str,
    ) -> Part:
        """
        Load a part by filename.

        Example:
            load_part("3001.dat")
        """

        part_path = (
            self.library_path
            / "parts"
            / filename
        )

        if not part_path.exists():
            raise FileNotFoundError(
                f"Part not found: {part_path}"
            )

        return self.parser.parse(part_path)