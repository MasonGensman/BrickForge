"""
BrickForge LDraw Library
"""

from pathlib import Path

from brickforge.ldraw.loader import LDrawLoader
from brickforge.ldraw.part import Part


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
        """
        Load a part from the library.

        Uses an in-memory cache so each part is
        only parsed once.
        """

        filename = filename.lower()

        if filename not in self._cache:

            self._cache[filename] = (
                self.loader.load_part(filename)
            )

        return self._cache[filename]

    def clear_cache(self):

        self._cache.clear()

    @property
    def cache_size(self) -> int:

        return len(self._cache)