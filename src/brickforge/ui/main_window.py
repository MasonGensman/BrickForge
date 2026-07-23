from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow

from brickforge._version import window_title
from brickforge.engine.scene import Scene
from brickforge.generation.generation_mode import GenerationMode
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.project.project import ProjectFileError
from brickforge.resources import resource_path
from brickforge.serialization.schema import SceneSerializationError
from brickforge.services.part_catalog import PartCatalog
from brickforge.ui.toolbar import create_toolbar, project_manager
from brickforge.ui.widgets import (
    BrickLibraryWidget,
    BrickForgeStatusBar,
    ImagePreviewWidget,
    PropertiesWidget,
    ViewportWidget,
)

_PROJECT_FILE_FILTER = "StudWorks Project (*.sws)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setup_window()
        self.create_menu()
        create_toolbar(self)
        self.create_widgets()
        self.connect_signals()

    def setup_window(self):
        self.setWindowTitle(window_title())
        self.setWindowIcon(
            QIcon(str(resource_path("ui", "resources", "icon.ico")))
        )
        self.resize(1400, 800)

    def create_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        menu.addMenu("Edit")
        menu.addMenu("View")
        menu.addMenu("Project")
        menu.addMenu("Help")

        new_project_action = QAction("New Project", self)
        open_project_action = QAction("Open Project...", self)
        save_project_action = QAction("Save Project", self)
        save_project_as_action = QAction("Save Project As...", self)

        new_project_action.triggered.connect(self.on_new_project)
        open_project_action.triggered.connect(self.on_open_project)
        save_project_action.triggered.connect(self.on_save_project)
        save_project_as_action.triggered.connect(self.on_save_project_as)

        file_menu.addAction(new_project_action)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(save_project_action)
        file_menu.addAction(save_project_as_action)

    def create_widgets(self):
        #
        # The shared ProjectManager (currently a module-level singleton
        # owned by ui.toolbar, not restructured here -- see Package_026's
        # inspection notes). Starting with an implicit "Untitled Project"
        # means current_project is never None during normal operation,
        # so Save/Save As don't need a separate "no project open" case.
        #
        self.project_manager = project_manager
        self.project_manager.new_project()

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

            #
            # Package_026: the current project owns its own Scene, so
            # Save operates on current_project directly rather than
            # taking a separate Scene parameter -- this is the one
            # place that Scene changes, so it's the one place that
            # needs to keep current_project.scene in sync.
            #
            self.project_manager.current_project.scene = scene
            self.project_manager.current_project.mark_dirty()

            self.status.showMessage(
                f"Generated {len(list(scene))} bricks."
            )

        except (OSError, ValueError) as error:

            self.status.showMessage(
                f"Generation failed: {error}"
            )

    def on_new_project(self):

        self.project_manager.new_project()

        self.viewport.renderer.set_scene(Scene())
        self.viewport.update()

        self.status.showMessage("New project created.")

    def on_open_project(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            _PROJECT_FILE_FILTER,
        )

        if not path:
            return

        try:
            project = self.project_manager.load(path)

        except (OSError, ProjectFileError, SceneSerializationError) as error:

            self.status.showMessage(
                f"Failed to open project: {error}"
            )
            return

        self.viewport.renderer.set_scene(project.scene)
        self.viewport.update()

        self.status.showMessage(
            f"Opened {project.name} ({len(list(project.scene))} bricks)."
        )

    def on_save_project(self):

        current_path = self.project_manager.current_project.file_path

        if current_path is None:
            self.on_save_project_as()
            return

        self._save_project_to(current_path)

    def on_save_project_as(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            f"{self.project_manager.current_project.name}.sws",
            _PROJECT_FILE_FILTER,
        )

        if not path:
            return

        if not path.lower().endswith(".sws"):
            path += ".sws"

        self._save_project_to(path)

    def _save_project_to(self, path):

        try:
            self.project_manager.save(path)

        except OSError as error:

            self.status.showMessage(
                f"Failed to save project: {error}"
            )
            return

        self.status.showMessage(
            f"Saved {self.project_manager.current_project.name}."
        )
