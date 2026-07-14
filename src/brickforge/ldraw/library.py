"""
BrickForge LDraw Library

Caches loaded LDraw parts.
"""

from pathlib import Path

from brickforge.ldraw.loader import LDrawLoader
from brickforge.ldraw.part import Part


class LDrawLibrary:
    """Caches loaded LDraw parts."""

    def __init__(
        self,
        library_path: str | Path,
    ):

        self.library_path = Path(library_path)

        if not self.library_path.exists():

            raise FileNotFoundError(
                f"LDraw library not found:\n{self.library_path}"
            )

        self.loader = LDrawLoader(
            self.library_path,
        )

        self._cache: dict[str, Part] = {}

    def load(
        self,
        filename: str,
    ) -> Part:
        """
        Load a part from the cache or disk.
        """

        filename = filename.lower()

        if filename not in self._cache:

            self._cache[filename] = (
                self.loader.load_part(
                    filename,
                    resolve=self.load,
                )
            )

        return self._cache[filename]

    def clear_cache(self) -> None:
        """Clear all cached parts."""

        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached parts."""

        return len(self._cache)