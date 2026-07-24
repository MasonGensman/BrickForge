"""
StudWorks Generation Workflow Polish Tests (Package_046)

Covers the UI-only fixes made against real, observed first-time-user
friction (see Package_046.md's inspection findings): a properly
disabled (not silently no-op) Undo/Redo, an Export toolbar button,
window-title reflecting the current project's name/dirty state, and
PropertiesWidget finally reflecting a viewport (not just Brick
Library) selection.

Matches the project's established pattern (Packages 027-033, 044-045):
duck-typed stand-ins carrying only the attributes the real, unbound
MainWindow methods actually touch, bound on via
`SomeMethod.__get__(fake_self)`/direct class-attribute assignment --
never a live MainWindow, whose __init__ does real, slow setup (a real
PartCatalog scan, a real OpenGL viewport) this file deliberately avoids
depending on.
"""

import unittest

import glm
from PySide6.QtWidgets import QApplication, QMainWindow

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.models.part_definition import BrickDefinition
from brickforge.project.project import Project
from brickforge.project.project_manager import ProjectManager
from brickforge.selection.selection_manager import SelectionManager
from brickforge.services.part_catalog import PartCatalog
from brickforge.tools.active_tool_manager import ToolResult
from brickforge.ui.main_window import MainWindow
from brickforge.ui.toolbar import create_toolbar
from brickforge.ui.widgets.image_preview_widget import ImagePreviewWidget

_app = QApplication.instance() or QApplication([])


def _brick(id_, part_name="3005.dat") -> SceneBrick:

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(0.0, 0.0, 0.0),
        rotation=glm.quat(),
        color_code=4,
    )


def _scene_of(*bricks) -> Scene:

    scene = Scene()

    for brick in bricks:
        scene.add_brick(brick)

    return scene


class ToolbarTests(unittest.TestCase):
    """create_toolbar() against a real (cheap) QMainWindow -- no
    OpenGL/catalog dependency, so a live instance is safe here."""

    def _build_toolbar(self):

        class _Window(QMainWindow):
            def on_new_project(self):
                pass

            def on_open_project(self):
                pass

            def on_save_project(self):
                pass

            def on_export_model(self):
                pass

        #
        # Kept alive on self -- QAction's C++ objects are owned by
        # their QMainWindow parent, so if `window` isn't kept
        # referenced somewhere, Python garbage-collecting it destroys
        # the whole parent-child tree (including every QAction),
        # leaving the returned actions dangling.
        #
        self._window = _Window()
        self._toolbar = create_toolbar(self._window)

        return {
            action.text(): action
            for action in self._toolbar.actions()
            if not action.isSeparator()
        }

    def test_undo_and_redo_are_disabled_not_silently_nonfunctional(self):

        actions = self._build_toolbar()

        self.assertFalse(actions["Undo"].isEnabled())
        self.assertFalse(actions["Redo"].isEnabled())

    def test_export_action_exists_alongside_new_open_save(self):

        actions = self._build_toolbar()

        self.assertIn("New", actions)
        self.assertIn("Open", actions)
        self.assertIn("Save", actions)
        self.assertIn("Export", actions)


class _FakeStatusBar:

    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None


class _FakePropertiesWidget:

    def __init__(self):
        self.displayed = []
        self.clear_calls = 0

    def display_brick(self, definition):
        self.displayed.append(definition)

    def clear(self):
        self.clear_calls += 1


class _FakeRenderer:

    def __init__(self, scene):
        self.scene = scene
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


class _FakeMainWindow:
    """Carries only what on_brick_clicked()/on_brick_transformed()/
    set_current_scene()/_refresh_window_title() actually touch."""

    on_brick_clicked = MainWindow.on_brick_clicked
    on_brick_transformed = MainWindow.on_brick_transformed
    set_current_scene = MainWindow.set_current_scene
    _refresh_window_title = MainWindow._refresh_window_title

    def __init__(self, catalog, scene, project):

        self.catalog = catalog
        self.status = _FakeStatusBar()
        self.properties = _FakePropertiesWidget()
        self.selection_manager = SelectionManager()
        self.viewport = _FakeViewport(_FakeRenderer(scene))

        self.project_manager = ProjectManager()
        self.project_manager.current_project = project

        self.window_titles = []

    def setWindowTitle(self, title):
        self.window_titles.append(title)


class RefreshWindowTitleTests(unittest.TestCase):

    def test_shows_project_name_without_a_dirty_marker_when_clean(self):

        project = Project(name="My Model")
        window = _FakeMainWindow(PartCatalog.from_seed(), Scene(), project)

        window._refresh_window_title()

        self.assertIn("My Model", window.window_titles[-1])
        self.assertNotIn("My Model*", window.window_titles[-1])

    def test_shows_a_dirty_marker_once_the_project_is_modified(self):

        project = Project(name="My Model")
        project.mark_dirty()

        window = _FakeMainWindow(PartCatalog.from_seed(), Scene(), project)
        window._refresh_window_title()

        self.assertIn("My Model*", window.window_titles[-1])


class OnBrickClickedPropertiesTests(unittest.TestCase):
    """Package_046: viewport selection should feed PropertiesWidget the
    same way Brick Library selection already does (Package_027 only
    ever fed the status bar)."""

    def test_selecting_a_placed_brick_displays_its_catalog_definition(self):

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0, part_name="3005.dat"))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        window.on_brick_clicked(0)

        self.assertEqual(len(window.properties.displayed), 1)

        displayed = window.properties.displayed[0]
        self.assertIsInstance(displayed, BrickDefinition)
        self.assertEqual(displayed.part_number, "3005")

    def test_clicking_empty_space_clears_properties(self):

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        window.on_brick_clicked(0)
        window.on_brick_clicked(None)

        self.assertEqual(window.properties.clear_calls, 1)

    def test_unresolvable_part_clears_properties_instead_of_guessing(self):
        """Matches the Candidate System's own precedent (§2.3 of
        HANDOFF.md): an unresolvable reference is left honestly
        unresolved rather than approximated."""

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0, part_name="not_in_catalog.dat"))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        window.on_brick_clicked(0)

        self.assertEqual(window.properties.displayed, [])
        self.assertEqual(window.properties.clear_calls, 1)


class OnBrickTransformedPropertiesTests(unittest.TestCase):

    def test_deleting_the_selected_brick_clears_properties(self):

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0), _brick(1))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        window.on_brick_clicked(0)
        self.assertEqual(len(window.properties.displayed), 1)

        window.on_brick_transformed(ToolResult(brick_id=0, verb="Deleted"))

        self.assertEqual(window.properties.clear_calls, 1)

    def test_moving_the_selected_brick_leaves_properties_untouched(self):

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        window.on_brick_clicked(0)
        self.assertEqual(len(window.properties.displayed), 1)

        window.on_brick_transformed(
            ToolResult(
                brick_id=0,
                verb="Moved",
                field="position",
                value=glm.vec3(1.0, 0.0, 0.0),
            )
        )

        self.assertEqual(window.properties.clear_calls, 0)


class ImagePreviewWidgetLabelingTests(unittest.TestCase):
    """Package_046: the two Generate buttons must be distinguishable --
    previously two visually-identical buttons with no explanation."""

    def test_both_paths_have_distinct_captions_and_tooltips(self):

        widget = ImagePreviewWidget()

        self.assertNotEqual(
            widget.generate_button.toolTip(),
            widget.generate_model_button.toolTip(),
        )
        self.assertTrue(widget.generate_button.toolTip())
        self.assertTrue(widget.generate_model_button.toolTip())

        self.assertIn(
            "Recommended", widget.new_pipeline_section_label.text()
        )
        self.assertIn("Legacy", widget.legacy_section_label.text())


if __name__ == "__main__":
    unittest.main()
