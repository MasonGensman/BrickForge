"""
BrickForge LDraw Parser
"""

from pathlib import Path

import numpy as np

from brickforge.ldraw.part import Part, PartReference


class LDrawParser:
    """Parses LDraw DAT files."""

    def parse(
        self,
        filename: str | Path,
    ) -> Part:

        filename = Path(filename)

        part = Part(
            name=filename.stem,
        )

        vertices = []

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

                record_type = tokens[0]

                if record_type == "0":

                    if (
                        not part.description
                        and len(tokens) > 1
                    ):
                        part.description = " ".join(tokens[1:])

                elif record_type == "1":
                    #
                    # Type 1 subfile reference
                    #
                    # tokens[1]    colour (unused, same as type 3/4)
                    # tokens[2:5]  translation (x, y, z)
                    # tokens[5:14] 3x3 transform matrix (a-i, row-major)
                    # tokens[14:]  referenced file name (may contain spaces)
                    #

                    translation = np.array(
                        list(
                            map(
                                float,
                                tokens[2:5],
                            )
                        ),
                        dtype=np.float32,
                    )

                    matrix = np.array(
                        list(
                            map(
                                float,
                                tokens[5:14],
                            )
                        ),
                        dtype=np.float32,
                    ).reshape(3, 3)

                    file_name = (
                        " ".join(tokens[14:])
                        .replace("\\", "/")
                    )

                    part.subfile_references.append(
                        PartReference(
                            file_name=file_name,
                            translation=translation,
                            matrix=matrix,
                        )
                    )

                elif record_type == "2":
                    #
                    # Optional line
                    #
                    continue

                elif record_type == "3":

                    coords = list(
                        map(
                            float,
                            tokens[2:11],
                        )
                    )

                    vertices.extend(coords)

                elif record_type == "4":

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

                elif record_type == "5":
                    #
                    # Conditional line
                    #
                    continue

        part.vertices = np.array(
            vertices,
            dtype=np.float32,
        )

        return part