"""
BrickForge LDraw Loader

Loads individual LDraw part files from the library, recursively resolving
and flattening Type-1 subfile references into one fully composed vertex
array per requested part.
"""

import logging
from pathlib import Path

import numpy as np

from brickforge.ldraw.library_layout import resolve_parts_directory
from brickforge.ldraw.parser import LDrawParser
from brickforge.ldraw.part import Part

logger = logging.getLogger(__name__)


class LDrawLoader:
    """Loads LDraw parts from the official library."""

    def __init__(
        self,
        library_path: str | Path,
    ):

        self.library_path = Path(library_path)
        self.parts_path = resolve_parts_directory(self.library_path)
        self.primitives_path = self.library_path / "p"

        self.parser = LDrawParser()

        self._visiting: set[str] = set()

    def _resolve_path(
        self,
        filename: str,
    ) -> Path | None:

        for base in (
            self.parts_path,
            self.primitives_path,
        ):

            candidate = base / filename

            if candidate.exists():
                return candidate

        return None

    def load_part(
        self,
        filename: str,
        resolve=None,
    ) -> Part:
        """
        Load one LDraw part from disk.

        Any Type-1 subfile references found in the file are resolved
        recursively (via `resolve`, defaulting to this method itself) and
        flattened into the returned Part's vertices, already transformed
        into this part's local coordinate frame. A missing or circular
        subfile reference is logged and skipped -- only a missing top-level
        `filename` raises.
        """

        resolve = resolve or self.load_part

        filename = filename.lower().replace("\\", "/")

        if filename in self._visiting:

            logger.warning(
                "Circular LDraw subfile reference detected, skipping: %s",
                filename,
            )

            return Part(name=filename)

        part_file = self._resolve_path(filename)

        if part_file is None:

            raise FileNotFoundError(
                f"LDraw part not found:\n"
                f"{self.parts_path / filename}\n"
                f"{self.primitives_path / filename}"
            )

        self._visiting.add(filename)

        try:

            part = self.parser.parse(part_file)

            vertex_chunks = [part.vertices]

            for reference in part.subfile_references:

                try:
                    child = resolve(reference.file_name)

                except OSError as error:

                    logger.warning(
                        "LDraw subfile reference could not be "
                        "resolved, skipping: %s",
                        error,
                    )

                    continue

                if not child.has_geometry():
                    continue

                points = child.vertices.reshape(-1, 3)

                transformed = (
                    points @ reference.matrix.T
                    + reference.translation
                )

                vertex_chunks.append(
                    transformed.reshape(-1).astype(
                        np.float32
                    )
                )

            part.vertices = np.concatenate(vertex_chunks)

            return part

        finally:
            self._visiting.discard(filename)

    def part_exists(
        self,
        filename: str,
    ) -> bool:
        """
        Check whether a part exists.
        """

        return (
            self._resolve_path(
                filename.lower().replace("\\", "/")
            )
            is not None
        )
