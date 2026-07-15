from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from brickforge.analysis.image_analysis import resize
from brickforge.generation.generation_mode import GenerationMode
from brickforge.io.image_resource import ImageResource
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.services.part_catalog import PartCatalog
from brickforge.ui.toolbar import create_toolbar
from brickforge.ui.widgets import (
    BrickLibraryWidget,
    BrickForgeStatusBar,
    ImagePreviewWidget,
    PropertiesWidget,
    ViewportWidget,
)

#
# Generation may run at native image resolution -- a real imported photo
# could be millions of pixels. A fixed, deterministic cap keeps "click
# Generate" usable without any user-facing resize control, regardless of
# which registered generation mode is selected.
#
MAX_GENERATION_DIMENSION = 48


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setup_window()
        self.create_menu()
        create_toolbar(self)
        self.create_widgets()
        self.connect_signals()

    def setup_window(self):
        self.setWindowTitle("BrickForge v0.1.0")
        self.resize(1400, 800)

    def create_menu(self):
        menu = self.menuBar()

        menu.addMenu("File")
        menu.addMenu("Edit")
        menu.addMenu("View")
        menu.addMenu("Project")
        menu.addMenu("Help")

    def create_widgets(self):
        #
        # One PartCatalog, built once and shared by the Brick Library
        # and generation -- avoids re-detecting/re-parsing the LDraw
        # library on every generation click.
        #
        self.catalog = PartCatalog.load_best_available()

        self.library = BrickLibraryWidget(self.catalog, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library)

        self.properties = PropertiesWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)

        self.image_preview = ImagePreviewWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.image_preview)

        self.viewport = ViewportWidget()
        self.setCentralWidget(self.viewport)

        self.status = BrickForgeStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("BrickForge Ready")

    def connect_signals(self):
        self.library.brick_selected.connect(self.properties.display_brick)
        self.library.brick_selected.connect(self.on_brick_selected)

        self.image_preview.generate_requested.connect(
            self.on_generate_lego
        )

    def on_brick_selected(self, brick):
        self.status.showMessage(
            f"Selected: {brick.name} ({brick.part_number})"
        )

    def on_generate_lego(
        self,
        image,
        mode: GenerationMode,
        settings,
    ):

        renderer = self.viewport.renderer

        library = (
            renderer.brick_manager.library
            if renderer.brick_manager is not None
            else None
        )

        if library is None:
            self.status.showMessage(
                "LDraw library not available; cannot generate."
            )
            return

        try:
            image = self._capped_image(image)

            palette = PaletteEngine(
                library.library_path / "LDConfig.ldr"
            )

            scene = mode.generate(
                image,
                palette,
                self.catalog,
                settings,
            )

            renderer.set_scene(scene)

            self.viewport.update()

            self.status.showMessage(
                f"Generated {len(list(scene))} bricks."
            )

        except (OSError, ValueError) as error:

            self.status.showMessage(
                f"Generation failed: {error}"
            )

    @staticmethod
    def _capped_image(image: ImageResource) -> ImageResource:
        """
        Deterministically downscale an image to MAX_GENERATION_DIMENSION
        on its longer side, preserving aspect ratio, before generation.
        Returns the image unchanged if it's already within the cap.
        """

        if (
            image.width <= MAX_GENERATION_DIMENSION
            and image.height <= MAX_GENERATION_DIMENSION
        ):
            return image

        scale = MAX_GENERATION_DIMENSION / max(
            image.width,
            image.height,
        )

        new_width = max(1, round(image.width * scale))
        new_height = max(1, round(image.height * scale))

        return ImageResource(
            path=image.path,
            width=new_width,
            height=new_height,
            format=image.format,
            pixels=resize(image.pixels, new_width, new_height),
            content_hash=image.content_hash,
        )
