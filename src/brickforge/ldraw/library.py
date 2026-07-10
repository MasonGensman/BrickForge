"""
BrickForge LDraw Library
"""

from pathlib import Path

from brickforge.ldraw.loader import LDrawLoader
from brickforge.ldraw.part import Part
from brickforge.render.mesh import Mesh


class LDrawLibrary:
    """Represents an LDraw parts library."""

    def __init__(
        self,
        library_path: str | Path,
    ):

        self.library_path = Path(library_path)

        if not self.library_path.exists():
            raise FileNotFoundError(
                f"LDraw library not found: {self.library_path}"
            )

        self.loader = LDrawLoader(
            self.library_path
        )

        self._cache: dict[str, Part] = {}

    def load(
        self,
        filename: str,
    ) -> Part:

        filename = filename.lower()

        if filename not in self._cache:

            self._cache[filename] = (
                self.loader.load_part(filename)
            )

        return self._cache[filename]

    def load_mesh(
        self,
        filename: str,
    ) -> Mesh | None:

        return self.load(filename).build_mesh()

    def clear_cache(self):

        self._cache.clear()

    @property
    def cache_size(self):

        return len(self._cache)

    def test_load(
        self,
        filename: str,
    ) -> Part:

        part = self.load(filename)

        print()
        print("=" * 40)
        print("LDraw Part Loaded")
        print("=" * 40)
        print(f"Name        : {part.name}")
        print(f"Description : {part.description}")
        print(f"Vertices    : {len(part.vertices) // 3}")
        print(f"Triangles   : {len(part.vertices) // 9}")
        print(f"Has Mesh    : {part.has_geometry()}")
        print("=" * 40)
        print()

        return part