"""
StudWorks Data Integrity & Application Lifecycle Tests (Package_048)

Covers real, previously-unguarded data-loss risks found by inspection:
New/Open/window-close discarding unsaved work with zero warning, a
ProjectManager.save() ordering bug that left file_path pointing at a
location that was never successfully written, and Project.name never
reflecting the actual saved filename.

Matches the project's established pattern: duck-typed stand-ins
carrying only the attributes the real, unbound MainWindow methods
actually touch, bound on via direct class-attribute assignment -- never
a live MainWindow, whose __init__ does real, slow setup this file
deliberately avoids depending on. QFileDialog/QMessageBox are mocked at
their brickforge.ui.main_window import site, matching
test_ui_export_integration.py's existing pattern.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QMessageBox

from brickforge.engine.scene import Scene
from brickforge.project.project import Project
from brickforge.project.project_manager import ProjectManager
from brickforge.selection.selection_manager import SelectionManager
from brickforge.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


class _FakeStatusBar:

    def __init__(self):
        self.messages = []

    def showMessage(self, message):
        self.messages.append(message)

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None


class _FakeRenderer:

    def __init__(self):
        self.scene = None
        self.selected_id = None

    def set_scene(self, scene):
        self.scene = scene

    def set_selected_id(self, brick_id):
        self.selected_id = brick_id


class _FakeViewport:

    def __init__(self):
        self.renderer = _FakeRenderer()

    def update(self):
        pass


class _FakeCloseEvent:

    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class _FakeMainWindow:
    """Carries only what the project-lifecycle handlers actually
    touch -- no OpenGL viewport, no real PartCatalog scan."""

    _confirm_discard_unsaved_changes = (
        MainWindow._confirm_discard_unsaved_changes
    )
    closeEvent = MainWindow.closeEvent
    on_new_project = MainWindow.on_new_project
    on_open_project = MainWindow.on_open_project
    on_save_project = MainWindow.on_save_project
    on_save_project_as = MainWindow.on_save_project_as
    _save_project_to = MainWindow._save_project_to
    set_current_scene = MainWindow.set_current_scene
    _refresh_window_title = MainWindow._refresh_window_title

    def __init__(self, project):

        self.status = _FakeStatusBar()
        self.viewport = _FakeViewport()
        self.selection_manager = SelectionManager()

        self.project_manager = ProjectManager()
        self.project_manager.current_project = project

        self.window_titles = []

    def setWindowTitle(self, title):
        self.window_titles.append(title)


def _dirty_project(name="My Model") -> Project:

    project = Project(name=name)
    project.mark_dirty()

    return project


class ConfirmDiscardUnsavedChangesTests(unittest.TestCase):

    def test_returns_true_immediately_when_not_dirty_no_dialog_shown(self):

        window = _FakeMainWindow(Project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
        ) as mock_question:

            result = window._confirm_discard_unsaved_changes()

        self.assertTrue(result)
        mock_question.assert_not_called()

    def test_cancel_returns_false_and_leaves_project_dirty(self):

        window = _FakeMainWindow(_dirty_project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Cancel,
        ):
            result = window._confirm_discard_unsaved_changes()

        self.assertFalse(result)
        self.assertTrue(window.project_manager.current_project.dirty)

    def test_discard_returns_true_without_saving(self):

        window = _FakeMainWindow(_dirty_project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Discard,
        ):
            result = window._confirm_discard_unsaved_changes()

        self.assertTrue(result)
        #
        # Discard means "throw it away," not "save it" -- dirty stays
        # True (nothing was written), the caller just proceeds anyway.
        #
        self.assertTrue(window.project_manager.current_project.dirty)

    def test_save_with_existing_path_saves_and_returns_true(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = Path(tmp_dir) / "existing.sws"
            project = _dirty_project()
            project.file_path = path

            window = _FakeMainWindow(project)

            with patch(
                "brickforge.ui.main_window.QMessageBox.question",
                return_value=QMessageBox.Save,
            ):
                result = window._confirm_discard_unsaved_changes()

            self.assertTrue(result)
            self.assertFalse(window.project_manager.current_project.dirty)
            self.assertTrue(path.is_file())

    def test_save_with_no_path_cancels_nested_save_as_and_returns_false(self):
        """Save chosen, but the project has never been saved before --
        on_save_project() redirects to on_save_project_as(), whose own
        file dialog is canceled here. The project stays dirty, so this
        method correctly reports "not safe to proceed" without any
        special-cased nested-cancel logic of its own."""

        window = _FakeMainWindow(_dirty_project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Save,
        ), patch(
            "brickforge.ui.main_window.QFileDialog.getSaveFileName",
            return_value=("", ""),
        ):
            result = window._confirm_discard_unsaved_changes()

        self.assertFalse(result)
        self.assertTrue(window.project_manager.current_project.dirty)


class OnNewProjectGuardTests(unittest.TestCase):

    def test_cancel_leaves_the_dirty_project_untouched(self):

        original_project = _dirty_project()
        window = _FakeMainWindow(original_project)

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Cancel,
        ):
            window.on_new_project()

        self.assertIs(
            window.project_manager.current_project, original_project,
        )
        self.assertEqual(window.status.messages, [])

    def test_discard_replaces_the_project_as_before(self):

        window = _FakeMainWindow(_dirty_project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Discard,
        ):
            window.on_new_project()

        self.assertEqual(
            window.project_manager.current_project.name, "Untitled Project",
        )
        self.assertIn("New project created.", window.status.messages)

    def test_not_dirty_proceeds_without_any_dialog(self):

        window = _FakeMainWindow(Project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
        ) as mock_question:
            window.on_new_project()

        mock_question.assert_not_called()
        self.assertIn("New project created.", window.status.messages)


class OnOpenProjectGuardTests(unittest.TestCase):

    def test_cancel_never_shows_the_file_dialog(self):

        window = _FakeMainWindow(_dirty_project())

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Cancel,
        ), patch(
            "brickforge.ui.main_window.QFileDialog.getOpenFileName",
        ) as mock_open_dialog:
            window.on_open_project()

        mock_open_dialog.assert_not_called()


class CloseEventTests(unittest.TestCase):

    def test_not_dirty_accepts_the_close(self):

        window = _FakeMainWindow(Project())
        event = _FakeCloseEvent()

        window.closeEvent(event)

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

    def test_dirty_and_cancel_ignores_the_close(self):

        window = _FakeMainWindow(_dirty_project())
        event = _FakeCloseEvent()

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Cancel,
        ):
            window.closeEvent(event)

        self.assertTrue(event.ignored)
        self.assertFalse(event.accepted)

    def test_dirty_and_discard_accepts_the_close(self):

        window = _FakeMainWindow(_dirty_project())
        event = _FakeCloseEvent()

        with patch(
            "brickforge.ui.main_window.QMessageBox.question",
            return_value=QMessageBox.Discard,
        ):
            window.closeEvent(event)

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)


class OnSaveProjectAsOwnershipTests(unittest.TestCase):
    """Package_048: Project.name previously never updated on Save As --
    a project saved as "MyModel.sws" kept showing "Untitled Project"
    everywhere (window title, status messages, the next Save-As
    dialog's own default filename)."""

    def test_project_name_is_derived_from_the_chosen_filename(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = str(Path(tmp_dir) / "MyLegoModel.sws")

            window = _FakeMainWindow(Project())

            with patch(
                "brickforge.ui.main_window.QFileDialog.getSaveFileName",
                return_value=(path, ""),
            ):
                window.on_save_project_as()

            self.assertEqual(
                window.project_manager.current_project.name, "MyLegoModel",
            )
            self.assertIn("MyLegoModel", window.window_titles[-1])
            self.assertIn("Saved MyLegoModel.", window.status.messages)

    def test_missing_extension_is_still_reflected_in_the_derived_name(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path_without_extension = str(Path(tmp_dir) / "MyLegoModel")

            window = _FakeMainWindow(Project())

            with patch(
                "brickforge.ui.main_window.QFileDialog.getSaveFileName",
                return_value=(path_without_extension, ""),
            ):
                window.on_save_project_as()

            self.assertEqual(
                window.project_manager.current_project.name, "MyLegoModel",
            )


class ProjectManagerSaveOrderingTests(unittest.TestCase):
    """Package_048: file_path/mark_saved() previously committed BEFORE
    the write was attempted, so a failed write left file_path pointing
    at a location that was never actually written."""

    def test_failed_write_leaves_file_path_at_its_prior_value(self):

        manager = ProjectManager()
        manager.current_project = Project()
        manager.current_project.mark_dirty()

        bad_path = str(
            Path(tempfile.gettempdir())
            / "studworks_lifecycle_test_missing_dir"
            / "model.sws"
        )

        with self.assertRaises(OSError):
            manager.save(bad_path)

        self.assertIsNone(manager.current_project.file_path)
        self.assertTrue(manager.current_project.dirty)

    def test_successful_write_still_sets_file_path_and_clears_dirty(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = Path(tmp_dir) / "model.sws"

            manager = ProjectManager()
            manager.current_project = Project()
            manager.current_project.mark_dirty()

            manager.save(path)

            self.assertEqual(manager.current_project.file_path, path)
            self.assertFalse(manager.current_project.dirty)


if __name__ == "__main__":
    unittest.main()
