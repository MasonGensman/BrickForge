"""
StudWorks Project Save/Load Golden-File Regression Tests (Package_026)

Mirrors Packages 024/025's golden-file testing pattern exactly (see
tests/test_export_golden_files.py's module docstring for the full
rationale) -- byte-for-byte comparison, zero normalization, stdlib
unittest, golden files regenerated only for intentional format
changes, reviewed and committed alongside the change that caused them.

Golden files live under tests/golden/sws_projects/, not
tests/golden/projects/ -- the repo's .gitignore has a pre-existing
bare `projects/` rule (for the app's own runtime project-save
directory, alongside renders/ and exports/) that would otherwise
silently exclude a same-named test fixture directory anywhere in the
tree.

Canonical projects use FIXED, explicit created/modified timestamps
(never datetime.now()) -- Project's default construction uses
datetime.now(), which would make byte-for-byte golden-file comparison
impossible to reproduce across runs. This is the Project-level
equivalent of Package_025's own "use PartCatalog.from_seed(), not
load_best_available()" reproducibility discipline.

Scene-shape variety (rotations, colors, multiple bricks) is already
covered by Package_025's own golden-file suite -- these tests focus on
the Project *wrapper* concerns instead: metadata fields, timestamps,
app_version, and correct nesting of a nested "StudWorks Scene"
document inside the "StudWorks Project" document.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.project.project import Project, ProjectFileError
from brickforge.project.project_manager import ProjectManager
from brickforge.serialization.schema import SceneSerializationError

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "sws_projects"

_FIXED_CREATED = datetime(2026, 1, 1, 0, 0, 0)
_FIXED_MODIFIED = datetime(2026, 1, 1, 0, 5, 0)
_FIXED_APP_VERSION = "0.2.0"


def build_empty_project() -> Project:

    return Project(
        name="Untitled Project",
        created=_FIXED_CREATED,
        modified=_FIXED_MODIFIED,
        app_version=_FIXED_APP_VERSION,
    )


def build_named_project_with_bricks() -> Project:

    scene = Scene()

    scene.add_brick(
        SceneBrick(
            id=0,
            part_name="3005.dat",
            position=glm.vec3(0.0, 0.0, 0.0),
            rotation=glm.quat(),
            color_code=4,
        )
    )

    scene.add_brick(
        SceneBrick(
            id=1,
            part_name="3004.dat",
            position=glm.vec3(20.0, 0.0, 0.0),
            rotation=glm.angleAxis(
                glm.radians(90.0),
                glm.vec3(0.0, 1.0, 0.0),
            ),
            color_code=None,
        )
    )

    return Project(
        name="My House",
        scene=scene,
        created=_FIXED_CREATED,
        modified=_FIXED_MODIFIED,
        app_version=_FIXED_APP_VERSION,
    )


CANONICAL_PROJECTS = {
    "empty_project": build_empty_project,
    "named_project_with_bricks": build_named_project_with_bricks,
}


def _project_signature(project: Project):

    return (
        project.name,
        project.app_version,
        [
            (
                brick.id,
                brick.part_name,
                (brick.position.x, brick.position.y, brick.position.z),
                (
                    brick.rotation.x, brick.rotation.y,
                    brick.rotation.z, brick.rotation.w,
                ),
                brick.color_code,
            )
            for brick in project.scene
        ],
    )


class GoldenFileProjectTests(unittest.TestCase):
    """Byte-for-byte comparisons against tests/golden/projects/*.sws."""

    def test_golden_files_exist(self):

        for name in CANONICAL_PROJECTS:

            golden_path = GOLDEN_DIR / f"{name}.sws"

            self.assertTrue(
                golden_path.is_file(),
                f"Missing golden file: {golden_path}",
            )

    def test_saved_output_matches_golden_files(self):

        for name, build_project in CANONICAL_PROJECTS.items():

            with self.subTest(project=name):

                golden_path = GOLDEN_DIR / f"{name}.sws"
                golden_bytes = golden_path.read_bytes()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    out_path = Path(tmp_dir) / f"{name}.sws"

                    manager = ProjectManager()
                    manager.current_project = build_project()
                    manager.save(out_path)

                    actual_bytes = out_path.read_bytes()

                self.assertEqual(
                    actual_bytes,
                    golden_bytes,
                    f"Saved output for {name!r} no longer matches its "
                    f"golden file byte-for-byte. If this is an "
                    f"INTENTIONAL format change, regenerate the golden "
                    f"file deliberately and review the diff before "
                    f"committing -- do not update it just to make this "
                    f"test pass.",
                )

    def test_round_trip_equality(self):
        """Project -> save -> load -> equivalent Project (and Scene)."""

        for name, build_project in CANONICAL_PROJECTS.items():

            with self.subTest(project=name):

                original = build_project()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    path = Path(tmp_dir) / f"{name}.sws"

                    manager = ProjectManager()
                    manager.current_project = original
                    manager.save(path)

                    reload_manager = ProjectManager()
                    reloaded = reload_manager.load(path)

                self.assertEqual(
                    _project_signature(original),
                    _project_signature(reloaded),
                )

    def test_loading_golden_files_reconstructs_expected_projects(self):

        for name, build_project in CANONICAL_PROJECTS.items():

            with self.subTest(project=name):

                golden_path = GOLDEN_DIR / f"{name}.sws"

                manager = ProjectManager()
                reloaded = manager.load(golden_path)

                self.assertEqual(
                    _project_signature(build_project()),
                    _project_signature(reloaded),
                )

    def test_save_is_deterministic_on_repeat(self):

        for name, build_project in CANONICAL_PROJECTS.items():

            with self.subTest(project=name):

                with tempfile.TemporaryDirectory() as tmp_dir:

                    path = Path(tmp_dir) / f"{name}.sws"

                    manager = ProjectManager()
                    manager.current_project = build_project()

                    manager.save(path)
                    first = path.read_bytes()

                    manager.current_project = build_project()
                    manager.save(path)
                    second = path.read_bytes()

                self.assertEqual(first, second)

    def test_save_does_not_mutate_scene(self):

        project = build_named_project_with_bricks()
        before = _project_signature(project)

        with tempfile.TemporaryDirectory() as tmp_dir:

            manager = ProjectManager()
            manager.current_project = project
            manager.save(Path(tmp_dir) / "out.sws")

        # name/app_version are untouched; only dirty/modified/file_path
        # are expected to change on save -- scene contents must not.
        after = _project_signature(project)
        self.assertEqual(before[2], after[2])  # scene signature unchanged


class ProjectErrorHandlingTests(unittest.TestCase):
    """
    Project-level problems raise ProjectFileError; problems in the
    embedded Scene are left to SceneSerializationError, uncaught and
    unwrapped by the Project layer -- confirming the two validation
    layers stay separate, per Package_026's architecture.
    """

    def _write_and_expect(self, content: str, expected_exception):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = Path(tmp_dir) / "bad.sws"
            path.write_text(content, encoding="utf-8")

            manager = ProjectManager()

            with self.assertRaises(expected_exception):
                manager.load(path)

            self.assertIsNone(manager.current_project)

    def test_invalid_json(self):
        self._write_and_expect("not json {{{", ProjectFileError)

    def test_wrong_format_identifier(self):
        self._write_and_expect(
            '{"format": "Not A Project", "schema_version": 1, "scene": {}}',
            ProjectFileError,
        )

    def test_unsupported_schema_version(self):
        self._write_and_expect(
            '{"format": "StudWorks Project", "schema_version": 999, '
            '"scene": {}}',
            ProjectFileError,
        )

    def test_missing_scene_field(self):
        self._write_and_expect(
            '{"format": "StudWorks Project", "schema_version": 1}',
            ProjectFileError,
        )

    def test_corrupt_embedded_scene_raises_scene_error_not_project_error(self):
        self._write_and_expect(
            '{"format": "StudWorks Project", "schema_version": 1, '
            '"scene": {"format": "Not A Scene", "schema_version": 1, '
            '"bricks": []}}',
            SceneSerializationError,
        )

    def test_missing_file_raises_oserror(self):

        manager = ProjectManager()

        with self.assertRaises(OSError):
            manager.load("this_file_does_not_exist_at_all.sws")

        self.assertIsNone(manager.current_project)

    def test_save_with_no_project_open_raises_runtime_error(self):

        manager = ProjectManager()

        with tempfile.TemporaryDirectory() as tmp_dir:

            with self.assertRaises(RuntimeError):
                manager.save(Path(tmp_dir) / "x.sws")


if __name__ == "__main__":
    unittest.main()
