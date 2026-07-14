"""
BrickForge Image Manager

Holds the currently loaded image. Shape mirrors
brickforge.project.ProjectManager (a single current-state holder), not
the static lookup catalogs in services/.
"""

from pathlib import Path

from brickforge.io.image_loader import ImageLoader
from brickforge.io.image_resource import ImageResource


class ImageManager:
    """Holds the currently loaded ImageResource."""

    def __init__(self):

        self.current_image: ImageResource | None = None

        self._loader = ImageLoader()

    def load(
        self,
        path: str | Path,
    ) -> ImageResource:
        """Load a file and make it the current image."""

        self.current_image = self._loader.load(path)

        return self.current_image

    def clear(self) -> None:
        """Discard the current image."""

        self.current_image = None

    @property
    def has_image(self) -> bool:

        return self.current_image is not None
