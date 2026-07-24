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

import tempfile
import unittest
from pathlib import Path

import glm
from PySide6.QtGui import QAction, QKeySequence
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
from brickforge.ui.widgets.properties_widget import PropertiesWidget

_app = QApplication.instance() or QApplication([])

_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
"""


def _write_ldconfig(directory: Path) -> Path:

    path = directory / "LDConfig.ldr"
    path.write_text(_FIXTURE_LDCONFIG, encoding="utf-8")

    return path


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

    def test_undo_and_redo_have_standard_shortcuts_despite_being_disabled(self):
        """A disabled QAction's shortcut simply never fires -- assigning
        one anyway is normal, unsurprising Qt behavior (Package_047)."""

        actions = self._build_toolbar()

        self.assertEqual(actions["Undo"].shortcut(), QKeySequence("Ctrl+Z"))
        self.assertEqual(actions["Redo"].shortcut(), QKeySequence("Ctrl+Y"))

    def test_toolbar_actions_have_no_shortcuts_of_their_own(self):
        """Package_047: shortcuts live on the menu's QAction instances
        (MenuShortcutTests below), not the toolbar's separate instances
        for the same operations -- two enabled QActions sharing an
        identical shortcut in the same window is ambiguous to Qt and
        neither would fire. Undo/Redo are the one exception: they have
        no menu equivalent at all, so there's nothing to collide with."""

        actions = self._build_toolbar()

        for name in ("New", "Open", "Save", "Export"):
            self.assertTrue(
                actions[name].shortcut().isEmpty(),
                f"{name} toolbar action should not carry its own shortcut",
            )

    def test_toolbar_actions_have_matching_tooltip_and_statustip(self):
        """Package_047: setToolTip() alongside the pre-existing
        setStatusTip() -- a tooltip appears at the cursor immediately,
        while a status tip only shows in the easy-to-miss status bar."""

        actions = self._build_toolbar()

        for name in ("New", "Open", "Save", "Export", "Undo", "Redo"):
            self.assertEqual(
                actions[name].toolTip(), actions[name].statusTip(),
            )
            #
            # QAction.toolTip() silently defaults to .text() when
            # never explicitly set -- comparing against the bare label
            # confirms setToolTip() was actually called, not just
            # coincidentally equal to statusTip() by Qt's own default.
            #
            self.assertNotEqual(actions[name].toolTip(), name)


class MenuShortcutTests(unittest.TestCase):
    """MainWindow.create_menu() against a real (cheap) QMainWindow --
    no OpenGL/catalog dependency, so a live instance is safe here."""

    def _build_menu(self):

        class _Window(QMainWindow):
            create_menu = MainWindow.create_menu

            def on_new_project(self):
                pass

            def on_open_project(self):
                pass

            def on_save_project(self):
                pass

            def on_save_project_as(self):
                pass

            def on_export_model(self):
                pass

            def on_duplicate_selected(self):
                pass

        #
        # Kept alive on self -- same QAction/parent-lifetime reason as
        # ToolbarTests._build_toolbar() above.
        #
        self._window = _Window()
        self._window.create_menu()

        return {
            action.text(): action
            for action in self._window.findChildren(QAction)
        }

    def test_shortcuts_match_the_approved_set(self):

        actions = self._build_menu()

        self.assertEqual(
            actions["New Project"].shortcut(), QKeySequence("Ctrl+N"),
        )
        self.assertEqual(
            actions["Open Project..."].shortcut(), QKeySequence("Ctrl+O"),
        )
        self.assertEqual(
            actions["Save Project"].shortcut(), QKeySequence("Ctrl+S"),
        )
        self.assertEqual(
            actions["Save Project As..."].shortcut(),
            QKeySequence("Ctrl+Shift+S"),
        )
        self.assertEqual(
            actions["Export Model..."].shortcut(), QKeySequence("Ctrl+E"),
        )
        self.assertEqual(
            actions["Duplicate Selected Brick"].shortcut(),
            QKeySequence("Ctrl+D"),
        )


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


class _FakeBrickManager:

    def __init__(self, library_path):

        class _Library:
            pass

        self.library = _Library()
        self.library.library_path = library_path


class _FakeRenderer:

    def __init__(self, scene, brick_manager=None):
        self.scene = scene
        self.selected_id = None
        self.brick_manager = brick_manager

    def set_scene(self, scene):
        self.scene = scene

    def set_selected_id(self, brick_id):
        self.selected_id = brick_id


class _FakeGenerationMode:
    """Stands in for a GenerationMode (Package_017) -- only the
    .generate() shape on_generate_lego() actually calls."""

    def __init__(self, scene_to_return):
        self._scene = scene_to_return
        self.calls = []

    def generate(self, image, palette, catalog, settings):
        self.calls.append((image, palette, catalog, settings))
        return self._scene


class _FakeViewport:

    def __init__(self, renderer):
        self.renderer = renderer
        self.update_called = 0

    def update(self):
        self.update_called += 1


class _FakeMainWindow:
    """Carries only what on_brick_clicked()/on_brick_transformed()/
    set_current_scene()/_refresh_window_title()/_resolve_ldraw_library()/
    on_generate_lego() actually touch."""

    on_brick_clicked = MainWindow.on_brick_clicked
    on_brick_transformed = MainWindow.on_brick_transformed
    set_current_scene = MainWindow.set_current_scene
    _refresh_window_title = MainWindow._refresh_window_title
    _resolve_ldraw_library = MainWindow._resolve_ldraw_library
    on_generate_lego = MainWindow.on_generate_lego

    def __init__(self, catalog, scene, project, library_path=None):

        self.catalog = catalog
        self.status = _FakeStatusBar()
        self.properties = _FakePropertiesWidget()
        self.selection_manager = SelectionManager()

        brick_manager = (
            _FakeBrickManager(library_path)
            if library_path is not None
            else None
        )
        self.viewport = _FakeViewport(_FakeRenderer(scene, brick_manager))

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


class ResolveLdrawLibraryTests(unittest.TestCase):
    """Package_047: on_generate_lego()/on_generate_model() previously
    duplicated this exact guard verbatim -- now shared."""

    def test_returns_the_library_when_present(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            catalog = PartCatalog.from_seed()
            project = Project()

            window = _FakeMainWindow(
                catalog, Scene(), project, library_path=tmp_path,
            )

            library = window._resolve_ldraw_library()

            self.assertIsNotNone(library)
            self.assertEqual(library.library_path, tmp_path)
            self.assertIsNone(window.status.last_message)

    def test_shows_a_message_and_returns_none_when_absent(self):

        catalog = PartCatalog.from_seed()
        project = Project()

        window = _FakeMainWindow(catalog, Scene(), project, library_path=None)

        library = window._resolve_ldraw_library()

        self.assertIsNone(library)
        self.assertIn(
            "LDraw library not available", window.status.last_message,
        )


class OnGenerateLegoTests(unittest.TestCase):
    """First-ever test coverage for on_generate_lego() (Package_047) --
    confirmed via grep to have had none since its Package_017 origin."""

    def test_successful_generation_updates_scene_and_project(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            _write_ldconfig(tmp_path)

            catalog = PartCatalog.from_seed()
            project = Project()
            scene_to_return = _scene_of(_brick(0))

            window = _FakeMainWindow(
                catalog, Scene(), project, library_path=tmp_path,
            )
            mode = _FakeGenerationMode(scene_to_return)

            window.on_generate_lego(
                image=object(), mode=mode, settings=object(),
            )

            self.assertIs(project.scene, scene_to_return)
            self.assertTrue(project.dirty)
            self.assertEqual(len(mode.calls), 1)
            self.assertIn("Generated 1 bricks", window.status.last_message)
            self.assertEqual(len(window.window_titles), 1)
            self.assertIn("*", window.window_titles[-1])

    def test_missing_library_shows_a_message_and_does_not_generate(self):

        catalog = PartCatalog.from_seed()
        project = Project()

        window = _FakeMainWindow(
            catalog, Scene(), project, library_path=None,
        )
        mode = _FakeGenerationMode(_scene_of(_brick(0)))

        window.on_generate_lego(image=object(), mode=mode, settings=object())

        self.assertIn(
            "LDraw library not available", window.status.last_message,
        )
        self.assertEqual(mode.calls, [])
        self.assertFalse(project.dirty)
        self.assertEqual(window.window_titles, [])


class OnBrickTransformedFailureMessageTests(unittest.TestCase):
    """Package_047: result.verb is always past tense, so gluing it
    directly onto "failed" previously read as broken English
    ("Moved failed: ...")."""

    def test_failure_message_reads_correctly_and_names_the_brick(self):

        catalog = PartCatalog.from_seed()
        scene = _scene_of(_brick(0))
        project = Project()

        window = _FakeMainWindow(catalog, scene, project)

        #
        # brick_id 999 doesn't exist in `scene` -- remove_brick()
        # raises TransformError, exercising the failure branch.
        #
        window.on_brick_transformed(ToolResult(brick_id=999, verb="Deleted"))

        message = window.status.last_message

        self.assertIn("Deleted brick #999", message)
        self.assertIn("failed", message)
        self.assertNotIn("Deleted failed", message)


class PropertiesWidgetEmptyStateTests(unittest.TestCase):
    """Package_047: the empty-state text was stale since Package_046
    wired viewport selection into this same widget."""

    def test_empty_state_mentions_both_selection_sources(self):

        widget = PropertiesWidget()
        text = widget.label.text().lower()

        self.assertIn("library", text)
        self.assertIn("viewport", text)


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
