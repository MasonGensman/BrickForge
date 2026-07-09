"""
BrickForge LDraw Parser
"""

from pathlib import Path

import numpy as np

from brickforge.ldraw.part import Part


class LDrawParser:
    """Parses LDraw DAT files."""

    def parse(
        self,
        filename: str | Path,
    ) -> Part:

        filename = Path(filename)

        vertices = []

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

                tokens = line.split()

                if tokens[0] == "0":

                    if (
                        part.description == ""
                        and len(tokens) > 1
                    ):
                        part.description = " ".join(tokens[1:])

                elif tokens[0] == "3":

                    coords = list(
                        map(
                            float,
                            tokens[2:11],
                        )
                    )

                    vertices.extend(coords)

                elif tokens[0] == "4":

                    coords = list(
                        map(
                            float,
                            tokens[2:14],
                        )
                    )

                    p1 = coords[0:3]
                    p2 = coords[3:6]
                    p3 = coords[6:9]
                    p4 = coords[9:12]

                    vertices.extend(
                        p1 + p2 + p3
                    )

                    vertices.extend(
                        p1 + p3 + p4
                    )

        part.vertices = np.array(
            vertices,
            dtype=np.float32,
        )

        return part