"""
StudWorks Export UI Integration Tests (Package_045)

Mirrors test_ui_generation_integration.py's own established pattern
(Package_044): MainWindow.on_export_model()/_export_model_to() are
exercised via a lightweight, duck-typed stand-in carrying only the
attributes those methods actually touch, not a real MainWindow (whose
__init__ does real, slow setup this file deliberately avoids depending
on). export_scene() (Package_024) needed no changes at all for this
integration -- these tests exercise the real, unmodified backend
function through the new UI entry points.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import glm
from PySide6.QtWidgets import QApplication

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.project.project import Project
from brickforge.project.project_manager import ProjectManager
from brickforge.services.part_catalog import PartCatalog
from brickforge.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


def _brick(id_, part_name="3005.dat", x=0.0) -> SceneBrick:

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(x, 0.0, 0.0),
        rotation=glm.quat(),
        color_code=4,
    )


def _scene_of(*bricks) -> Scene:

    scene = Scene()

    for brick in bricks:
        scene.add_brick(brick)

    return scene


class _FakeStatusBar:

    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None


class _FakeMainWindow:
    """Duck-typed stand-in carrying only what on_export_model()/
    _export_model_to() actually touch -- not a real MainWindow."""

    on_export_model = MainWindow.on_export_model
    _export_model_to = MainWindow._export_model_to
    _refresh_window_title = MainWindow._refresh_window_title

    def __init__(self, catalog, project):

        self.catalog = catalog
        self.status = _FakeStatusBar()

        self.project_manager = ProjectManager()
        self.project_manager.current_project = project

        #
        # Package_046: GenerateThenExportEndToEndTests below also
        # binds on_generate_model() onto this stand-in, which now
        # refreshes the window title on success.
        #
        self.window_titles = []

    def setWindowTitle(self, title):
        self.window_titles.append(title)


class ExportModelToTests(unittest.TestCase):
    """Direct tests of _export_model_to() -- bypasses the file dialog
    entirely, matching Package_044's own established split between
    dialog-handling and testable write logic."""

    def test_successful_export_writes_a_valid_file_and_reports_it(self):

        catalog = PartCatalog.from_seed()
        project = Project()
        project.scene = _scene_of(_brick(0), _brick(1, x=20.0))

        window = _FakeMainWindow(catalog, project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            out_path = Path(tmp_dir) / "model.ldr"

            window._export_model_to(str(out_path))

            self.assertTrue(out_path.is_file())

            content = out_path.read_text(encoding="utf-8")
            self.assertIn("3005.dat", content)

        self.assertIn("Exported 2 bricks", window.status.last_message)
        self.assertIn("model.ldr", window.status.last_message)

    def test_empty_scene_exports_successfully(self):

        catalog = PartCatalog.from_seed()
        project = Project()

        window = _FakeMainWindow(catalog, project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            out_path = Path(tmp_dir) / "empty.ldr"

            window._export_model_to(str(out_path))

            self.assertTrue(out_path.is_file())

        self.assertIn("Exported 0 bricks", window.status.last_message)

    def test_write_failure_is_reported_not_raised(self):

        catalog = PartCatalog.from_seed()
        project = Project()
        project.scene = _scene_of(_brick(0))

        window = _FakeMainWindow(catalog, project)

        bad_path = str(
            Path(tempfile.gettempdir())
            / "studworks_export_test_missing_dir"
            / "model.ldr"
        )

        window._export_model_to(bad_path)

        self.assertIn("Failed to export model", window.status.last_message)

    def test_unrecognized_part_is_still_exported(self):
        """Matches export_scene()'s own documented behavior: an
        unrecognized part is written, never silently dropped."""

        catalog = PartCatalog.from_seed()
        project = Project()
        project.scene = _scene_of(
            _brick(0, part_name="not_in_catalog.dat"),
        )

        window = _FakeMainWindow(catalog, project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            out_path = Path(tmp_dir) / "model.ldr"

            window._export_model_to(str(out_path))

            content = out_path.read_text(encoding="utf-8")
            self.assertIn("not_in_catalog.dat", content)

        self.assertIn("Exported 1 bricks", window.status.last_message)


class OnExportModelDialogTests(unittest.TestCase):
    """Tests the dialog-handling half (cancellation, extension
    normalization) by mocking QFileDialog.getSaveFileName only --
    everything downstream is the real _export_model_to()."""

    def test_cancellation_exports_nothing(self):

        catalog = PartCatalog.from_seed()
        project = Project()
        project.scene = _scene_of(_brick(0))

        window = _FakeMainWindow(catalog, project)

        with patch(
            "brickforge.ui.main_window.QFileDialog.getSaveFileName",
            return_value=("", ""),
        ):
            window.on_export_model()

        self.assertIsNone(window.status.last_message)

    def test_missing_extension_is_normalized(self):

        catalog = PartCatalog.from_seed()
        project = Project()
        project.scene = _scene_of(_brick(0))

        window = _FakeMainWindow(catalog, project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            path_without_extension = str(Path(tmp_dir) / "model")

            with patch(
                "brickforge.ui.main_window.QFileDialog.getSaveFileName",
                return_value=(path_without_extension, ""),
            ):
                window.on_export_model()

            self.assertTrue(
                (Path(tmp_dir) / "model.ldr").is_file()
            )


_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
"""


class GenerateThenExportEndToEndTests(unittest.TestCase):
    """Chains MainWindow.on_generate_model() (Package_044) directly into
    on_export_model()/_export_model_to() (this package), proving the
    full Import -> Generate -> Export journey works end to end through
    the actual, unmodified handlers -- not inferred from each half being
    separately tested."""

    def test_generated_scene_can_be_exported(self):

        from PySide6.QtGui import QColor, QImage

        from brickforge.preparation.generation_input import GenerationInput

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)

            image = QImage(6, 6, QImage.Format_RGBA8888)
            image.fill(QColor(0, 0, 0, 0))

            for y in range(1, 5):
                for x in range(1, 5):
                    image.setPixelColor(x, y, QColor(200, 10, 10, 255))

            image_path = tmp_path / "source.png"
            image.save(str(image_path))

            (tmp_path / "LDConfig.ldr").write_text(
                _FIXTURE_LDCONFIG, encoding="utf-8",
            )

            catalog = PartCatalog.from_seed()
            project = Project()

            class _Library:
                pass

            library = _Library()
            library.library_path = tmp_path

            class _BrickManager:
                pass

            brick_manager = _BrickManager()
            brick_manager.library = library

            class _Renderer:
                def __init__(self):
                    self.brick_manager = brick_manager
                    self.scene = None
                def set_scene(self, scene):
                    self.scene = scene
                def set_selected_id(self, brick_id):
                    pass

            class _Viewport:
                def __init__(self):
                    self.renderer = _Renderer()
                def update(self):
                    pass

            window = _FakeMainWindow(catalog, project)
            window.viewport = _Viewport()

            from brickforge.selection.selection_manager import SelectionManager
            window.selection_manager = SelectionManager()
            window.set_current_scene = MainWindow.set_current_scene.__get__(window)
            window.on_generate_model = MainWindow.on_generate_model.__get__(window)

            generation_input = GenerationInput.from_source(image_path)
            window.on_generate_model(generation_input)

            self.assertGreater(len(list(project.scene)), 0)

            out_path = tmp_path / "generated.ldr"
            window._export_model_to(str(out_path))

            self.assertTrue(out_path.is_file())

            exported_brick_count = len(list(project.scene))
            self.assertIn(
                f"Exported {exported_brick_count} bricks",
                window.status.last_message,
            )


if __name__ == "__main__":
    unittest.main()
