"""
BrickForge LDraw Parser
"""

from pathlib import Path

from brickforge.ldraw.part import Part


class LDrawParser:
    """Parses LDraw .dat files."""

    def parse(self, filename: str | Path) -> Part:

        filename = Path(filename)

        part = Part(
            name=filename.stem,
        )

        with filename.open(
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("0 "):

                    text = line[2:].strip()

                    if (
                        part.description == ""
                        and text
                    ):
                        part.description = text

        return part