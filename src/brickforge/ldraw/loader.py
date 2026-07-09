"""
BrickForge LDraw Loader
"""

from pathlib import Path

from brickforge.ldraw.parser import LDrawParser
from brickforge.ldraw.part import Part


class LDrawLoader:
    """Loads LDraw parts from the official library."""

    def __init__(self, library_path: str | Path):

        self.library_path = Path(library_path)

        self.parts_path = self.library_path / "parts"

        self.parser = LDrawParser()

    def load_part(
        self,
        filename: str,
    ) -> Part:

        filename = filename.lower()

        part_file = self.parts_path / filename

        if not part_file.exists():

            raise FileNotFoundError(
                f"Part not found:\n{part_file}"
            )

        return self.parser.parse(part_file)

    def part_exists(
        self,
        filename: str,
    ) -> bool:

        return (
            self.parts_path
            / filename.lower()
        ).exists()