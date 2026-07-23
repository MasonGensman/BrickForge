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

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import glm
import numpy as np
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.preparation.generation_input import GenerationInput
from brickforge.preparation.image_preparation import ImagePreparationSettings
from brickforge.project.project import Project, ProjectFileError
from brickforge.project.project_manager import ProjectManager
from brickforge.serialization.schema import SceneSerializationError

_app = QApplication.instance() or QApplication([])

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


def _write_test_image(directory: Path) -> Path:

    image = QImage(6, 4, QImage.Format_RGBA8888)

    for y in range(4):
        for x in range(6):
            image.setPixelColor(x, y, QColor((x * 30) % 255, (y * 40) % 255, 100, 255))

    path = directory / "source.png"
    image.save(str(path))

    return path


class ProjectGenerationInputTests(unittest.TestCase):
    """
    Not golden-file byte comparisons -- generation_input's serialized
    source_path is inherently environment-dependent (it names a real
    file on disk), so these are structural round-trip tests using a
    real, freshly-created test image instead (Package_034).
    """

    def test_project_without_generation_input_has_no_such_key(self):

        project = build_empty_project()
        data = project.to_dict()

        self.assertNotIn("generation_input", data)

    def test_round_trip_preserves_generation_input(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))

            generation_input = GenerationInput.from_source(
                image_path,
                ImagePreparationSettings(
                    max_dimension=48, crop_rect=(1, 1, 3, 2), rotation_degrees=90,
                ),
            )

            project = build_named_project_with_bricks()
            project.generation_input = generation_input

            save_path = Path(tmp_dir) / "project.sws"

            manager = ProjectManager()
            manager.current_project = project
            manager.save(save_path)

            reload_manager = ProjectManager()
            reloaded = reload_manager.load(save_path)

        reloaded_gi = reloaded.generation_input

        self.assertIsNotNone(reloaded_gi)
        self.assertEqual(reloaded_gi.source_path, image_path)
        self.assertEqual(reloaded_gi.content_hash, generation_input.content_hash)
        self.assertEqual(reloaded_gi.settings.crop_rect, (1, 1, 3, 2))
        self.assertEqual(reloaded_gi.settings.rotation_degrees, 90)
        self.assertTrue(
            np.array_equal(
                reloaded_gi.prepared_image.pixels,
                generation_input.prepared_image.pixels,
            )
        )

        # The Scene itself is untouched by any of this.
        self.assertEqual(
            _project_signature(reloaded)[2],
            _project_signature(project)[2],
        )

    def test_serialized_generation_input_contains_no_analysis_data(self):
        """Package_035: analysis lives only on the in-memory
        GenerationInput, regenerated via from_source() -- to_dict()
        must never embed its arrays (histogram/edges/etc.) in the
        saved file."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))
            generation_input = GenerationInput.from_source(image_path)

            project = build_named_project_with_bricks()
            project.generation_input = generation_input

            data = project.to_dict()
            gi_data = data["generation_input"]

            self.assertNotIn("analysis", gi_data)
            self.assertEqual(
                set(gi_data.keys()),
                {"source_path", "content_hash", "settings"},
            )

    def test_round_trip_regenerates_matching_analysis(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))
            generation_input = GenerationInput.from_source(image_path)

            project = build_named_project_with_bricks()
            project.generation_input = generation_input

            save_path = Path(tmp_dir) / "project.sws"

            manager = ProjectManager()
            manager.current_project = project
            manager.save(save_path)

            reload_manager = ProjectManager()
            reloaded = reload_manager.load(save_path)

        reloaded_analysis = reloaded.generation_input.analysis
        original_analysis = generation_input.analysis

        self.assertEqual(
            reloaded_analysis.dominant_colors, original_analysis.dominant_colors
        )
        self.assertEqual(
            reloaded_analysis.occupied_bounds, original_analysis.occupied_bounds
        )
        self.assertTrue(
            np.array_equal(reloaded_analysis.edges, original_analysis.edges)
        )

    def test_missing_source_image_degrades_gracefully_on_load(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            image_path = _write_test_image(Path(tmp_dir))

            generation_input = GenerationInput.from_source(image_path)

            project = build_named_project_with_bricks()
            project.generation_input = generation_input

            save_path = Path(tmp_dir) / "project.sws"

            manager = ProjectManager()
            manager.current_project = project
            manager.save(save_path)

            os.remove(image_path)

            reload_manager = ProjectManager()
            reloaded = reload_manager.load(save_path)

        self.assertIsNone(reloaded.generation_input)
        # The Scene must still load correctly despite the missing image.
        self.assertEqual(
            _project_signature(reloaded)[2],
            _project_signature(project)[2],
        )


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
