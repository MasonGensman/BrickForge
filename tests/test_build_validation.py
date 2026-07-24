"""
StudWorks Build Validation Tests (Package_040)

Uses hand-built Scene fixtures for per-rule unit tests (no dependency
on the real installed LDraw library), plus one end-to-end test running
validate_scene() against real generate_scene() output to prove overlap
detection produces zero false positives on ordinary, normally-tiled
generated Scenes -- the exact empirical check performed during this
package's planning, turned into a permanent regression test.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.generation.generation_engine import generate_scene
from brickforge.models.part_definition import BrickDefinition
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.serialization.deserializer import document_to_scene
from brickforge.serialization.serializer import scene_to_document
from brickforge.services.part_catalog import PartCatalog
from brickforge.validation.build_validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    _find_duplicate_ids,
    _find_invalid_orientations,
    _find_invalid_part_references,
    _find_overlapping_bricks,
    validate_scene,
)

_STUD_LDU = 20.0


def _seed_catalog() -> PartCatalog:
    return PartCatalog.from_seed()


def _brick(id_, part_name="3005.dat", x=0.0, y=0.0, z=0.0, rotation=None) -> SceneBrick:

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(x, y, z),
        rotation=rotation if rotation is not None else glm.quat(),
        color_code=4,
    )


def _scene_of(*bricks) -> Scene:

    scene = Scene()

    for brick in bricks:
        scene.add_brick(brick)

    return scene


class FindDuplicateIdsTests(unittest.TestCase):

    def test_no_duplicates_yields_no_issues(self):

        scene = _scene_of(_brick(0), _brick(1), _brick(2))

        self.assertEqual(_find_duplicate_ids(scene), [])

    def test_a_repeated_id_yields_one_issue(self):

        scene = _scene_of(
            _brick(0), _brick(1, x=20.0), _brick(0, x=40.0),
        )

        issues = _find_duplicate_ids(scene)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.ERROR)
        self.assertEqual(issues[0].brick_ids, (0,))

    def test_deterministic(self):

        scene = _scene_of(_brick(5), _brick(5, x=20.0))

        first = _find_duplicate_ids(scene)
        second = _find_duplicate_ids(scene)

        self.assertEqual(first, second)


class FindInvalidPartReferencesTests(unittest.TestCase):

    def test_valid_part_yields_no_issue(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0, part_name="3005.dat"))

        self.assertEqual(
            _find_invalid_part_references(scene, catalog), [],
        )

    def test_unresolvable_part_yields_a_warning(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0, part_name="nonexistent.dat"))

        issues = _find_invalid_part_references(scene, catalog)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.WARNING)
        self.assertEqual(issues[0].brick_ids, (0,))


class FindInvalidOrientationsTests(unittest.TestCase):

    def test_identity_rotation_yields_no_issue(self):

        scene = _scene_of(_brick(0))

        self.assertEqual(_find_invalid_orientations(scene), [])

    def test_an_ordinary_rotation_yields_no_issue(self):

        rotation = glm.angleAxis(glm.radians(37.0), glm.vec3(0, 1, 0))
        scene = _scene_of(_brick(0, rotation=rotation))

        self.assertEqual(_find_invalid_orientations(scene), [])

    def test_heavily_chained_rotation_still_within_tolerance(self):
        """Matches the drift measured during this package's planning:
        200 accumulated multiplications without renormalizing stay
        within ~2e-6 of unit length -- well inside the tolerance."""

        base = glm.angleAxis(glm.radians(1.0), glm.vec3(0, 1, 0))
        rotation = glm.quat()

        for _ in range(200):
            rotation = rotation * base

        scene = _scene_of(_brick(0, rotation=rotation))

        self.assertEqual(_find_invalid_orientations(scene), [])

    def test_non_unit_quaternion_yields_an_error(self):

        broken_rotation = glm.quat(2.0, 0.0, 0.0, 0.0)
        scene = _scene_of(_brick(0, rotation=broken_rotation))

        issues = _find_invalid_orientations(scene)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.ERROR)
        self.assertEqual(issues[0].brick_ids, (0,))


class FindOverlappingBricksTests(unittest.TestCase):

    def test_same_position_bricks_overlap(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1))

        issues = _find_overlapping_bricks(scene, catalog)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, ValidationSeverity.WARNING)
        self.assertEqual(issues[0].brick_ids, (0, 1))

    def test_edge_adjacent_bricks_do_not_overlap(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=_STUD_LDU))

        self.assertEqual(_find_overlapping_bricks(scene, catalog), [])

    def test_distant_bricks_do_not_overlap(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=1000.0))

        self.assertEqual(_find_overlapping_bricks(scene, catalog), [])

    def test_unresolvable_part_is_skipped_not_flagged(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="nonexistent.dat"),
            _brick(1, part_name="nonexistent.dat"),
        )

        self.assertEqual(_find_overlapping_bricks(scene, catalog), [])

    def test_rotation_is_accounted_for(self):
        """A 1x4 brick (3010.dat, stud_length=4 along local Z) rotated
        90 degrees around Y swings its long axis onto X instead -- its
        Z-reach shrinks from +-40 LDU to +-10 LDU. A 1x1 brick at
        z=25 sits inside the unrotated Z-reach (overlap) but outside
        the rotated one (no overlap); verified directly (both cases)
        before writing this test. If rotation were ignored and the
        unrotated box used regardless, this would incorrectly report
        an overlap."""

        catalog = _seed_catalog()

        rotation = glm.angleAxis(glm.radians(90.0), glm.vec3(0, 1, 0))

        scene = _scene_of(
            SceneBrick(
                id=0, part_name="3010.dat",
                position=glm.vec3(0.0, 0.0, 0.0),
                rotation=rotation, color_code=4,
            ),
            _brick(1, part_name="3005.dat", z=25.0),
        )

        self.assertEqual(_find_overlapping_bricks(scene, catalog), [])

    def test_brick_ids_normalized_regardless_of_scene_order(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(9), _brick(3))

        issues = _find_overlapping_bricks(scene, catalog)

        self.assertEqual(issues[0].brick_ids, (3, 9))

    def test_deterministic(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1))

        first = _find_overlapping_bricks(scene, catalog)
        second = _find_overlapping_bricks(scene, catalog)

        self.assertEqual(first, second)


class ValidationResultImmutabilityTests(unittest.TestCase):

    def test_validation_issue_is_frozen(self):

        issue = ValidationIssue(
            rule_id="x", severity=ValidationSeverity.ERROR,
            message="m", brick_ids=(0,),
        )

        with self.assertRaises(dataclasses.FrozenInstanceError):
            issue.message = "changed"

    def test_validation_report_is_frozen(self):

        report = ValidationReport(issues=())

        with self.assertRaises(dataclasses.FrozenInstanceError):
            report.issues = (None,)


class ValidateSceneTests(unittest.TestCase):

    def test_a_clean_scene_is_valid_with_no_issues(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, x=0.0), _brick(1, x=_STUD_LDU),
        )

        report = validate_scene(scene, catalog)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.issues, ())

    def test_multiple_simultaneous_problems_are_all_reported(self):

        catalog = _seed_catalog()
        broken_rotation = glm.quat(2.0, 0.0, 0.0, 0.0)

        scene = _scene_of(
            _brick(0),
            _brick(0, x=20.0),  # duplicate id
            _brick(2, part_name="nonexistent.dat", x=40.0),  # bad reference
            SceneBrick(
                id=3, part_name="3005.dat",
                position=glm.vec3(60.0, 0.0, 0.0),
                rotation=broken_rotation, color_code=4,
            ),  # invalid orientation
        )

        report = validate_scene(scene, catalog)

        rule_ids = {issue.rule_id for issue in report.issues}
        self.assertIn("duplicate_brick_id", rule_ids)
        self.assertIn("invalid_part_reference", rule_ids)
        self.assertIn("invalid_orientation", rule_ids)
        self.assertFalse(report.is_valid)

    def test_warnings_alone_do_not_invalidate(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0, part_name="nonexistent.dat"))

        report = validate_scene(scene, catalog)

        self.assertTrue(
            all(
                issue.severity is ValidationSeverity.WARNING
                for issue in report.issues
            )
        )
        self.assertTrue(report.is_valid)

    def test_issue_ordering_is_rule_then_scene_order_not_incidental(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0),
            _brick(0, x=20.0),
            _brick(5, part_name="nonexistent.dat", x=40.0),
        )

        report = validate_scene(scene, catalog)

        rule_sequence = [issue.rule_id for issue in report.issues]
        self.assertEqual(
            rule_sequence,
            ["duplicate_brick_id", "invalid_part_reference"],
        )

    def test_deterministic_across_repeated_calls(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=20.0))

        first = validate_scene(scene, catalog)
        second = validate_scene(scene, catalog)

        self.assertEqual(first, second)

    def test_does_not_mutate_scene_or_catalog(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(0, x=20.0))

        bricks_before = list(scene)
        catalog_before = [d.part_number for d in catalog.all()]

        validate_scene(scene, catalog)

        self.assertEqual(list(scene), bricks_before)
        self.assertEqual(
            [d.part_number for d in catalog.all()], catalog_before,
        )

    def test_validated_scene_serializes_without_modification(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=20.0))

        validate_scene(scene, catalog)

        document = scene_to_document(scene)
        reloaded = document_to_scene(document)

        self.assertEqual(list(scene)[0].id, list(reloaded)[0].id)
        self.assertEqual(len(list(reloaded)), len(list(scene)))


_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
"""


class RealGeneratedSceneHasNoFalsePositivesTests(unittest.TestCase):
    """The exact empirical check performed during this package's
    planning, turned into a permanent regression test: an ordinary,
    normally-tiled generate_scene() output must never trigger overlap
    (or any other) false positives."""

    def test_generated_scene_has_no_overlap_false_positives(self):

        from PySide6.QtGui import QColor, QImage
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)

            image = QImage(6, 6, QImage.Format_RGBA8888)
            image.fill(QColor(0, 0, 0, 0))

            for y in range(1, 5):
                for x in range(1, 5):
                    image.setPixelColor(x, y, QColor(200, 10, 10, 255))

            image_path = tmp_path / "source.png"
            image.save(str(image_path))

            generation_input = GenerationInput.from_source(image_path)
            catalog = _seed_catalog()

            (tmp_path / "LDConfig.ldr").write_text(
                _FIXTURE_LDCONFIG, encoding="utf-8",
            )
            palette = PaletteEngine(tmp_path / "LDConfig.ldr")

            scene = generate_scene(generation_input, catalog, palette)
            report = validate_scene(scene, catalog)

            overlap_issues = [
                issue for issue in report.issues
                if issue.rule_id == "overlapping_bricks"
            ]

            self.assertEqual(overlap_issues, [])


if __name__ == "__main__":
    unittest.main()
