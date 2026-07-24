"""
StudWorks Generation Pipeline Orchestrator Tests (Package_043)

Uses a real, freshly-written test image and a small synthetic
LDConfig.ldr fixture (matching patterns established in
test_generation_engine.py/test_optimization.py) for end-to-end tests.
The repair-loop tests use unittest.mock.patch to substitute
optimize_scene()'s output with a deliberately broken, hand-built Scene
-- this exercises generate_model()'s own real orchestration code path
(the while loop, _scene_signature comparison, iteration counting)
through its actual public API, rather than duplicating that logic in a
separate, unverified test-only reimplementation.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.generation.candidates import GenerationConstraints
from brickforge.generation.generation_engine import generate_scene
from brickforge.optimization.pipeline import optimize_scene
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.pipeline.generation_pipeline import (
    GenerationResult,
    _scene_signature,
    generate_model,
)
from brickforge.preparation.generation_input import GenerationInput
from brickforge.repair.scene_repair import repair_scene
from brickforge.scene_analysis.scene_analysis import analyze_scene
from brickforge.services.part_catalog import PartCatalog
from brickforge.validation.build_validation import validate_scene

_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
0 !COLOUR Blue CODE 1 VALUE #0055BF EDGE #05131D
"""


def _seed_catalog() -> PartCatalog:
    return PartCatalog.from_seed()


def _write_ldconfig(directory: Path) -> Path:

    path = directory / "LDConfig.ldr"
    path.write_text(_FIXTURE_LDCONFIG, encoding="utf-8")

    return path


def _write_test_image(directory: Path, width: int = 6, height: int = 6) -> Path:

    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])

    image = QImage(width, height, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if x < width // 2:
                image.setPixelColor(x, y, QColor(200, 10, 10, 255))
            else:
                image.setPixelColor(x, y, QColor(10, 10, 200, 255))

    path = directory / "source.png"
    image.save(str(path))

    return path


def _brick(id_, part_name="3005.dat", x=0.0, rotation=None) -> SceneBrick:

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(x, 0.0, 0.0),
        rotation=rotation if rotation is not None else glm.quat(),
        color_code=4,
    )


def _scene_of(*bricks) -> Scene:

    scene = Scene()

    for brick in bricks:
        scene.add_brick(brick)

    return scene


def _two_problem_scene() -> Scene:
    """Duplicate ids AND an invalid part reference simultaneously --
    the exact scenario verified during planning to resolve in 2 repair
    cycles."""

    return _scene_of(
        _brick(0),
        _brick(0, x=20.0),
        _brick(1, part_name="nonexistent.dat", x=40.0),
    )


class SceneSignatureTests(unittest.TestCase):

    def test_identical_content_yields_equal_signatures(self):

        a = _scene_of(_brick(0), _brick(1, x=20.0))
        b = _scene_of(_brick(0), _brick(1, x=20.0))

        self.assertEqual(_scene_signature(a), _scene_signature(b))

    def test_different_content_yields_different_signatures(self):

        a = _scene_of(_brick(0))
        b = _scene_of(_brick(0, x=20.0))

        self.assertNotEqual(_scene_signature(a), _scene_signature(b))


class _PipelineFixtureContext:

    def __init__(self, tmp_dir: Path):

        image_path = _write_test_image(tmp_dir)
        self.catalog = _seed_catalog()
        self.palette = PaletteEngine(_write_ldconfig(tmp_dir))
        self.image_path = image_path


class GenerateModelEndToEndTests(unittest.TestCase):

    def test_full_pipeline_produces_a_valid_result(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            result = generate_model(ctx.image_path, ctx.catalog, ctx.palette)

            self.assertIsInstance(result, GenerationResult)
            self.assertGreater(
                result.scene_analysis.measurements.brick_count, 0,
            )
            self.assertIsInstance(result.generation_input, GenerationInput)
            self.assertTrue(result.validation_report.is_valid)
            self.assertEqual(result.repair_iterations, 0)

    def test_deterministic_across_repeated_calls(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            first = generate_model(ctx.image_path, ctx.catalog, ctx.palette)
            second = generate_model(ctx.image_path, ctx.catalog, ctx.palette)

            self.assertEqual(
                _scene_signature(first.scene), _scene_signature(second.scene),
            )
            self.assertEqual(
                first.validation_report, second.validation_report,
            )
            self.assertEqual(first.scene_analysis, second.scene_analysis)
            self.assertEqual(first.repair_iterations, second.repair_iterations)

    def test_constraints_and_settings_are_accepted(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            result = generate_model(
                ctx.image_path, ctx.catalog, ctx.palette,
                constraints=GenerationConstraints(),
            )

            self.assertGreater(
                result.scene_analysis.measurements.brick_count, 0,
            )

    def test_does_not_mutate_catalog(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))
            catalog_before = [d.part_number for d in ctx.catalog.all()]

            generate_model(ctx.image_path, ctx.catalog, ctx.palette)

            self.assertEqual(
                [d.part_number for d in ctx.catalog.all()], catalog_before,
            )


class AcceptsGenerationInputDirectlyTests(unittest.TestCase):
    """Package_044: generate_model() also accepts an already-built
    GenerationInput, avoiding a redundant reload for callers (like
    ImagePreviewWidget) that already have one before generation is
    requested."""

    def test_accepts_a_prebuilt_generation_input(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            generation_input = GenerationInput.from_source(ctx.image_path)

            result = generate_model(
                generation_input, ctx.catalog, ctx.palette,
            )

            self.assertGreater(
                result.scene_analysis.measurements.brick_count, 0,
            )
            self.assertIs(result.generation_input, generation_input)

    def test_matches_the_result_of_passing_the_equivalent_path(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            generation_input = GenerationInput.from_source(ctx.image_path)

            from_input = generate_model(
                generation_input, ctx.catalog, ctx.palette,
            )
            from_path = generate_model(
                ctx.image_path, ctx.catalog, ctx.palette,
            )

            self.assertEqual(
                _scene_signature(from_input.scene),
                _scene_signature(from_path.scene),
            )

    def test_performs_no_redundant_reload(self):
        """Deletes the source file after building the GenerationInput --
        if generate_model() tried to reload from the path, this would
        raise FileNotFoundError. It must not, since a GenerationInput
        was passed directly."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            generation_input = GenerationInput.from_source(ctx.image_path)

            Path(ctx.image_path).unlink()

            result = generate_model(
                generation_input, ctx.catalog, ctx.palette,
            )

            self.assertGreater(
                result.scene_analysis.measurements.brick_count, 0,
            )


class GenerationResultImmutabilityTests(unittest.TestCase):

    def test_generation_result_is_frozen(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))
            result = generate_model(ctx.image_path, ctx.catalog, ctx.palette)

            with self.assertRaises(dataclasses.FrozenInstanceError):
                result.repair_iterations = 99


class FailurePropagationTests(unittest.TestCase):

    def test_missing_image_raises_file_not_found_error_unchanged(self):

        catalog = _seed_catalog()

        with tempfile.TemporaryDirectory() as tmp_dir:

            palette = PaletteEngine(_write_ldconfig(Path(tmp_dir)))

            with self.assertRaises(FileNotFoundError):
                generate_model(
                    "this_file_does_not_exist.png", catalog, palette,
                )

    def test_no_candidates_raises_value_error_unchanged(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            all_parts = [d.part_number for d in ctx.catalog.all()]

            with self.assertRaises(ValueError):
                generate_model(
                    ctx.image_path, ctx.catalog, ctx.palette,
                    constraints=GenerationConstraints(
                        excluded_part_numbers=all_parts,
                    ),
                )


class RepairLoopTests(unittest.TestCase):
    """Exercises generate_model()'s real orchestration code path by
    substituting optimize_scene()'s output with a deliberately broken
    Scene, rather than duplicating the loop's logic in a separate
    reimplementation."""

    def test_two_simultaneous_problems_resolve_in_two_cycles(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            with patch(
                "brickforge.pipeline.generation_pipeline.optimize_scene",
                return_value=_two_problem_scene(),
            ):
                result = generate_model(
                    ctx.image_path, ctx.catalog, ctx.palette,
                )

            self.assertEqual(result.repair_iterations, 2)
            self.assertTrue(result.validation_report.is_valid)
            self.assertEqual(
                result.scene_analysis.measurements.brick_count, 2,
            )

    def test_deferred_issue_remains_visible_after_repair_settles(self):
        """A zero-length quaternion cannot be safely normalized
        (repair/scene_repair.py's own documented limit) -- the loop
        must terminate because the Scene stops changing, not because
        the report became clean, and the residual issue must still be
        visible in the final result."""

        broken_rotation = glm.quat(0.0, 0.0, 0.0, 0.0)
        unrepairable_scene = _scene_of(
            SceneBrick(
                id=0, part_name="3005.dat",
                position=glm.vec3(0, 0, 0),
                rotation=broken_rotation, color_code=4,
            )
        )

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            with patch(
                "brickforge.pipeline.generation_pipeline.optimize_scene",
                return_value=unrepairable_scene,
            ):
                result = generate_model(
                    ctx.image_path, ctx.catalog, ctx.palette,
                )

            self.assertFalse(result.validation_report.is_valid)
            rule_ids = {
                issue.rule_id for issue in result.validation_report.issues
            }
            self.assertIn("invalid_orientation", rule_ids)

            # Terminated via "scene stopped changing", nowhere near the
            # defensive safety cap.
            self.assertEqual(result.repair_iterations, 0)

    def test_already_valid_scene_needs_zero_repair_iterations(self):

        clean_scene = _scene_of(_brick(0), _brick(1, x=20.0))

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            with patch(
                "brickforge.pipeline.generation_pipeline.optimize_scene",
                return_value=clean_scene,
            ):
                result = generate_model(
                    ctx.image_path, ctx.catalog, ctx.palette,
                )

            self.assertEqual(result.repair_iterations, 0)
            self.assertTrue(result.validation_report.is_valid)


class LowerLevelApisRemainIndependentTests(unittest.TestCase):
    """Every stage function generate_model() calls remains directly,
    independently usable and behaviorally unchanged."""

    def test_stage_functions_are_still_directly_callable(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _PipelineFixtureContext(Path(tmp_dir))

            generation_input = GenerationInput.from_source(ctx.image_path)
            scene = generate_scene(generation_input, ctx.catalog, ctx.palette)
            scene = optimize_scene(scene, ctx.catalog)
            report = validate_scene(scene, ctx.catalog)
            repaired = repair_scene(scene, report)
            analysis = analyze_scene(repaired, ctx.catalog)

            self.assertGreater(analysis.measurements.brick_count, 0)


if __name__ == "__main__":
    unittest.main()
