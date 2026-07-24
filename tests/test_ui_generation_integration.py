"""
StudWorks New-Pipeline UI Integration Tests (Package_044)

The first test coverage for anything in ui/ -- no prior test
instantiates MainWindow, and MainWindow.__init__() does real,
potentially slow setup (a real PartCatalog scan, a real OpenGL
viewport widget), which this file deliberately avoids depending on.

MainWindow.on_generate_model()/set_current_scene() are plain functions
under the hood -- this file calls them directly against a lightweight,
duck-typed stand-in object carrying only the attributes those methods
actually touch, rather than instantiating a real MainWindow. This
matches the project's own established pattern (Packages 027-033) of
testing event-handler logic without a live Qt window.

ImagePreviewWidget itself IS instantiated directly -- it's a plain
QDockWidget with no OpenGL/catalog dependency, so a real instance is
cheap and safe to build under a real QApplication.
"""

import tempfile
import types
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from brickforge.engine.scene import Scene
from brickforge.generation.candidates import GenerationConstraints
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.project.project import Project
from brickforge.project.project_manager import ProjectManager
from brickforge.selection.selection_manager import SelectionManager
from brickforge.services.part_catalog import PartCatalog
from brickforge.ui.main_window import MainWindow
from brickforge.ui.widgets.image_preview_widget import ImagePreviewWidget

_app = QApplication.instance() or QApplication([])

_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
"""


def _write_ldconfig(directory: Path) -> Path:

    path = directory / "LDConfig.ldr"
    path.write_text(_FIXTURE_LDCONFIG, encoding="utf-8")

    return path


def _write_test_image(directory: Path, width=6, height=6) -> Path:

    from PySide6.QtGui import QColor, QImage

    image = QImage(width, height, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            image.setPixelColor(x, y, QColor(200, 10, 10, 255))

    path = directory / "source.png"
    image.save(str(path))

    return path


class ImagePreviewWidgetNewPipelineButtonTests(unittest.TestCase):

    def test_emits_generate_model_requested_with_the_current_generation_input(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))

            widget = ImagePreviewWidget()

            received = []
            widget.generate_model_requested.connect(received.append)

            generation_input = GenerationInput.from_source(image_path)
            widget._generation_input = generation_input

            widget.generate_via_new_pipeline()

            self.assertEqual(len(received), 1)
            self.assertIs(received[0], generation_input)

    def test_shows_a_message_and_emits_nothing_without_an_imported_image(self):

        widget = ImagePreviewWidget()

        received = []
        widget.generate_model_requested.connect(received.append)

        widget.generate_via_new_pipeline()

        self.assertEqual(received, [])
        self.assertIn("import an image", widget.info.text().lower())

    def test_legacy_generate_button_is_unaffected(self):
        """The existing button/signal still exist and still work,
        confirming the new button is additive, not a replacement."""

        widget = ImagePreviewWidget()

        self.assertTrue(hasattr(widget, "generate_button"))
        self.assertTrue(hasattr(widget, "generate_model_button"))
        self.assertIsNot(widget.generate_button, widget.generate_model_button)


class _FakeBrickManager:

    def __init__(self, library_path):

        class _Library:
            pass

        self.library = _Library()
        self.library.library_path = library_path


class _FakeRenderer:

    def __init__(self, brick_manager):

        self.brick_manager = brick_manager
        self.scene = None
        self.selected_id = None

    def set_scene(self, scene):
        self.scene = scene

    def set_selected_id(self, brick_id):
        self.selected_id = brick_id


class _FakeViewport:

    def __init__(self, renderer):

        self.renderer = renderer
        self.update_called = 0

    def update(self):
        self.update_called += 1


class _FakeStatusBar:

    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None


class _FakeMainWindow:
    """Duck-typed stand-in carrying only what on_generate_model()/
    set_current_scene() actually touch -- not a real MainWindow."""

    set_current_scene = MainWindow.set_current_scene
    on_generate_model = MainWindow.on_generate_model
    _refresh_window_title = MainWindow._refresh_window_title
    _resolve_ldraw_library = MainWindow._resolve_ldraw_library

    def __init__(self, catalog, library_path, project):

        brick_manager = (
            _FakeBrickManager(library_path)
            if library_path is not None
            else None
        )

        self.viewport = _FakeViewport(_FakeRenderer(brick_manager))
        self.status = _FakeStatusBar()
        self.selection_manager = SelectionManager()
        self.catalog = catalog

        self.project_manager = ProjectManager()
        self.project_manager.current_project = project

        #
        # Package_046: on_generate_model() now also refreshes the
        # window title on success -- recorded (not just a no-op) so
        # OnGenerateModelTests can assert on it directly.
        #
        self.window_titles = []

    def setWindowTitle(self, title):
        self.window_titles.append(title)


class OnGenerateModelTests(unittest.TestCase):

    def test_successful_generation_updates_scene_and_project(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            image_path = _write_test_image(tmp_path)
            _write_ldconfig(tmp_path)

            catalog = PartCatalog.from_seed()
            project = Project()

            window = _FakeMainWindow(catalog, tmp_path, project)
            generation_input = GenerationInput.from_source(image_path)

            window.on_generate_model(generation_input)

            self.assertIsInstance(window.viewport.renderer.scene, Scene)
            self.assertGreater(
                len(list(window.viewport.renderer.scene)), 0,
            )
            self.assertIs(project.scene, window.viewport.renderer.scene)
            self.assertIs(project.generation_input, generation_input)
            self.assertTrue(project.dirty)

            self.assertIn("Generated", window.status.last_message)
            self.assertIn("Valid", window.status.last_message)

            self.assertEqual(len(window.window_titles), 1)
            self.assertIn(project.name, window.window_titles[-1])
            self.assertIn("*", window.window_titles[-1])

    def test_missing_library_shows_a_message_and_does_not_generate(self):

        catalog = PartCatalog.from_seed()
        project = Project()

        window = _FakeMainWindow(catalog, None, project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))
            generation_input = GenerationInput.from_source(image_path)

        window.on_generate_model(generation_input)

        self.assertIn(
            "LDraw library not available", window.status.last_message,
        )
        self.assertIsNone(window.viewport.renderer.scene)
        self.assertFalse(project.dirty)
        self.assertEqual(window.window_titles, [])

    def test_no_candidates_error_is_reported_not_raised(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            image_path = _write_test_image(tmp_path)
            _write_ldconfig(tmp_path)

            catalog = PartCatalog.from_seed()
            project = Project()
            project.generation_constraints = GenerationConstraints(
                excluded_part_numbers=[
                    d.part_number for d in catalog.all()
                ],
            )

            window = _FakeMainWindow(catalog, tmp_path, project)
            generation_input = GenerationInput.from_source(image_path)

            window.on_generate_model(generation_input)

            self.assertIn("Generation failed", window.status.last_message)
            self.assertFalse(project.dirty)

    def test_respects_project_generation_constraints(self):
        """Confirms constraints already stored on Project (even though
        no UI sets them yet) are read and passed through correctly."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            image_path = _write_test_image(tmp_path)
            _write_ldconfig(tmp_path)

            catalog = PartCatalog.from_seed()
            project = Project()

            unconstrained_window = _FakeMainWindow(
                catalog, tmp_path, project,
            )
            generation_input = GenerationInput.from_source(image_path)
            unconstrained_window.on_generate_model(generation_input)
            unconstrained_part = next(
                iter(unconstrained_window.viewport.renderer.scene)
            ).part_name

            constrained_project = Project()
            constrained_project.generation_constraints = (
                GenerationConstraints(
                    excluded_part_numbers=[
                        unconstrained_part.replace(".dat", ""),
                    ],
                )
            )
            constrained_window = _FakeMainWindow(
                catalog, tmp_path, constrained_project,
            )
            constrained_window.on_generate_model(generation_input)
            constrained_part = next(
                iter(constrained_window.viewport.renderer.scene)
            ).part_name

            self.assertNotEqual(unconstrained_part, constrained_part)


if __name__ == "__main__":
    unittest.main()
