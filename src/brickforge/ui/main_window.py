import dataclasses

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow

from brickforge._version import window_title
from brickforge.engine.scene import Scene
from brickforge.generation.generation_mode import GenerationMode
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.project.project import ProjectFileError
from brickforge.resources import resource_path
from brickforge.selection.selection_manager import SelectionManager
from brickforge.serialization.schema import SceneSerializationError
from brickforge.services.part_catalog import PartCatalog
from brickforge.transform.scene_transform import (
    TransformError,
    duplicate_brick,
    remove_brick,
    replace_brick,
)
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
        edit_menu = menu.addMenu("Edit")
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

        #
        # No dedicated tool/button for Duplicate -- there's no fourth
        # mouse button left to bind (Move/Rotate/Delete already claim
        # Left/Right/Middle), and it has no continuous parameter to
        # drive through a viewport drag anyway. A single menu action
        # operating directly on the current selection, mirroring how
        # New/Open/Save are already self-contained QAction -> MainWindow
        # handlers with no ActiveToolManager involvement (Package_033).
        #
        duplicate_action = QAction("Duplicate Selected Brick", self)
        duplicate_action.triggered.connect(self.on_duplicate_selected)

        edit_menu.addAction(duplicate_action)

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
        # Owns the single currently-selected SceneBrick.id (Package_027).
        # Renderer only ever consumes whatever id is pushed into it via
        # set_selected_id() -- it has no reference to this manager.
        #
        self.selection_manager = SelectionManager()

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

        self.viewport.brick_clicked.connect(self.on_brick_clicked)
        self.viewport.brick_transformed.connect(self.on_brick_transformed)

    def on_brick_selected(self, brick):
        self.status.showMessage(
            f"Selected: {brick.name} ({brick.part_number})"
        )

    def on_brick_clicked(self, brick_id):

        if brick_id is None:

            self.selection_manager.clear()
            self.status.showMessage("Selection cleared.")

        else:

            self.selection_manager.select(brick_id)

            #
            # pick() just found this id by intersecting the current
            # scene, so it's guaranteed to still be there.
            #
            brick = self.viewport.renderer.scene.get(brick_id)

            self.status.showMessage(
                f"Selected brick #{brick_id} ({brick.part_name})."
            )

        self.viewport.renderer.set_selected_id(
            self.selection_manager.selected_id()
        )

        self.viewport.update()

    def on_brick_transformed(self, result):
        """
        Handles the outcome of any completed editing-tool interaction
        (Move, Rotate, Delete, and whatever future tool produces a
        ToolResult) -- one generic handler in place of separate
        per-tool handlers (Package_031, extended for removal in
        Package_032).
        """

        scene = self.viewport.renderer.scene

        try:

            if result.is_removal:

                new_scene = remove_brick(scene, result.brick_id)

            else:

                updated_brick = dataclasses.replace(
                    scene.get(result.brick_id),
                    **{result.field: result.value},
                )

                new_scene = replace_brick(scene, updated_brick)

        except TransformError as error:

            self.status.showMessage(
                f"{result.verb} failed: {error}"
            )
            return

        #
        # Package_028: set_current_scene() clears selection only if
        # the selected id is no longer present. replace_brick()
        # preserves every id, so a moved/rotated brick stays selected;
        # remove_brick() drops exactly the deleted id, so selection
        # clears automatically -- no Delete-specific selection logic
        # needed here (Package_032).
        #
        self.set_current_scene(new_scene)
        self.project_manager.current_project.mark_dirty()

        self.status.showMessage(
            f"{result.verb} brick #{result.brick_id}."
        )

    def on_duplicate_selected(self):
        """
        Duplicate the currently selected brick, triggered directly by
        the Edit menu action -- no viewport interaction, no
        ActiveToolManager/ToolResult involvement, since there's no
        mouse gesture to interpret (Package_033).
        """

        selected_id = self.selection_manager.selected_id()

        if selected_id is None:

            self.status.showMessage(
                "No brick selected to duplicate."
            )
            return

        scene = self.viewport.renderer.scene

        try:
            new_scene, new_id = duplicate_brick(scene, selected_id)

        except TransformError as error:

            self.status.showMessage(
                f"Duplicate failed: {error}"
            )
            return

        #
        # set_current_scene() preserves selection on the ORIGINAL by
        # default (its id is still present) -- explicitly move
        # selection onto the new duplicate afterward, so the user can
        # immediately move/adjust the fresh copy without an extra
        # click. The first operation in this session that needs to
        # reassign selection to a different id rather than just
        # preserve or clear the existing one.
        #
        self.set_current_scene(new_scene)

        self.selection_manager.select(new_id)
        self.viewport.renderer.set_selected_id(new_id)

        self.project_manager.current_project.mark_dirty()

        self.status.showMessage(
            f"Duplicated brick #{selected_id} -> #{new_id}."
        )

    def set_current_scene(
        self,
        scene: Scene,
    ) -> None:
        """
        Replace the active Scene everywhere it's tracked: the current
        Project and the Renderer. The one consistent path New Project,
        Open Project, Generate LEGO Model, and future Transform
        operations all follow (Package_028).

        Selection is preserved if it still references an id present
        in the new Scene, and cleared otherwise -- one rule that
        handles both "Scene was completely replaced" (New/Open/
        Generate -- the old id will not exist in the new Scene, so
        selection clears, matching Package_027's behavior) and "Scene
        was produced by a Transform" (replace_brick() guarantees the
        exact same id set as its input, so selection survives)
        without the caller needing to say which case it is. This is
        SelectionManager's own documented invariant --
        selected_id is either None or references an existing
        SceneBrick.id in the active Scene -- enforced here as code
        rather than left to each caller to remember.

        Does not mark the project dirty -- New/Open must not (fresh/
        just-loaded-from-disk state), while Generate and future
        Transform operations should; that stays the caller's call.
        """

        self.project_manager.current_project.scene = scene
        self.viewport.renderer.set_scene(scene)

        selected_id = self.selection_manager.selected_id()

        if selected_id is not None and scene.get(selected_id) is None:
            self.selection_manager.clear()

        self.viewport.renderer.set_selected_id(
            self.selection_manager.selected_id()
        )

        self.viewport.update()

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

            self.set_current_scene(scene)
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

        self.set_current_scene(
            self.project_manager.current_project.scene
        )

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

        self.set_current_scene(project.scene)

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
