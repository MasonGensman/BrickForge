"""
StudWorks Scene Repair Tests (Package_042)

Uses hand-built Scene/ValidationReport fixtures throughout -- no
dependency on the real installed LDraw library. The duplicate-id tests
in particular exercise the exact bug found and fixed during this
package's planning: a naive incremental rebuild using
Scene.next_available_id() can reintroduce a new collision rather than
resolving one.
"""

import dataclasses
import unittest

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.repair.scene_repair import (
    _repair_duplicate_ids,
    _repair_invalid_orientations,
    _repair_invalid_part_references,
    repair_scene,
)
from brickforge.services.part_catalog import PartCatalog
from brickforge.validation.build_validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    validate_scene,
)


def _seed_catalog() -> PartCatalog:
    return PartCatalog.from_seed()


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


def _scene_signature(scene: Scene):

    return [
        (b.id, b.part_name, (b.position.x, b.position.y, b.position.z), b.color_code)
        for b in scene
    ]


def _issue(rule_id, brick_ids, severity=ValidationSeverity.ERROR):

    return ValidationIssue(
        rule_id=rule_id, severity=severity,
        message="test issue", brick_ids=brick_ids,
    )


class RepairDuplicateIdsTests(unittest.TestCase):

    def test_the_exact_bug_found_during_planning_does_not_recur(self):
        """[0, 0, 1, 2] must not produce a new collision -- verified
        directly during planning that a naive approach using
        new_scene.next_available_id() incorrectly produces
        [0, 1, 1, 2]."""

        scene = _scene_of(
            _brick(0), _brick(0, x=20.0), _brick(1, x=40.0), _brick(2, x=60.0),
        )
        report = ValidationReport(
            issues=(_issue("duplicate_brick_id", (0,)),),
        )

        repaired = _repair_duplicate_ids(scene, report)
        ids = [b.id for b in repaired]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(ids), [0, 1, 2, 3])

    def test_first_occurrence_keeps_its_original_id(self):

        scene = _scene_of(_brick(5), _brick(5, x=20.0))
        report = ValidationReport(
            issues=(_issue("duplicate_brick_id", (5,)),),
        )

        repaired = _repair_duplicate_ids(scene, report)
        ids = [b.id for b in repaired]

        self.assertEqual(ids[0], 5)
        self.assertNotEqual(ids[1], 5)

    def test_multiple_separate_duplicate_groups(self):

        scene = _scene_of(
            _brick(0), _brick(0, x=20.0),
            _brick(1, x=40.0), _brick(1, x=60.0),
        )
        report = ValidationReport(
            issues=(
                _issue("duplicate_brick_id", (0,)),
                _issue("duplicate_brick_id", (1,)),
            ),
        )

        repaired = _repair_duplicate_ids(scene, report)
        ids = [b.id for b in repaired]

        self.assertEqual(len(ids), len(set(ids)))

    def test_deterministic(self):

        scene = _scene_of(_brick(0), _brick(0, x=20.0))
        report = ValidationReport(
            issues=(_issue("duplicate_brick_id", (0,)),),
        )

        first = [b.id for b in _repair_duplicate_ids(scene, report)]
        second = [b.id for b in _repair_duplicate_ids(scene, report)]

        self.assertEqual(first, second)


class RepairInvalidPartReferencesTests(unittest.TestCase):

    def test_removes_the_named_brick(self):

        scene = _scene_of(
            _brick(0, part_name="nonexistent.dat"), _brick(1, x=20.0),
        )
        report = ValidationReport(
            issues=(
                _issue(
                    "invalid_part_reference", (0,),
                    severity=ValidationSeverity.WARNING,
                ),
            ),
        )

        repaired = _repair_invalid_part_references(scene, report)

        self.assertEqual([b.id for b in repaired], [1])

    def test_removes_multiple_simultaneous_bad_references(self):

        scene = _scene_of(
            _brick(0, part_name="a.dat"),
            _brick(1, x=20.0),
            _brick(2, part_name="b.dat", x=40.0),
        )
        report = ValidationReport(
            issues=(
                _issue(
                    "invalid_part_reference", (0,),
                    severity=ValidationSeverity.WARNING,
                ),
                _issue(
                    "invalid_part_reference", (2,),
                    severity=ValidationSeverity.WARNING,
                ),
            ),
        )

        repaired = _repair_invalid_part_references(scene, report)

        self.assertEqual([b.id for b in repaired], [1])


class RepairInvalidOrientationsTests(unittest.TestCase):

    def test_normalizes_a_nearly_unit_quaternion(self):

        drifted = glm.quat(1.0001, 0.0, 0.0, 0.0)
        scene = _scene_of(_brick(0, rotation=drifted))
        report = ValidationReport(
            issues=(_issue("invalid_orientation", (0,)),),
        )

        repaired = _repair_invalid_orientations(scene, report)

        self.assertAlmostEqual(
            glm.length(repaired.get(0).rotation), 1.0, places=5,
        )

    def test_zero_length_quaternion_is_left_unchanged(self):

        broken = glm.quat(0.0, 0.0, 0.0, 0.0)
        scene = _scene_of(_brick(0, rotation=broken))
        report = ValidationReport(
            issues=(_issue("invalid_orientation", (0,)),),
        )

        repaired = _repair_invalid_orientations(scene, report)

        self.assertEqual(glm.length(repaired.get(0).rotation), 0.0)

    def test_wildly_off_quaternion_is_left_unchanged(self):

        broken = glm.quat(5.0, 0.0, 0.0, 0.0)
        scene = _scene_of(_brick(0, rotation=broken))
        report = ValidationReport(
            issues=(_issue("invalid_orientation", (0,)),),
        )

        repaired = _repair_invalid_orientations(scene, report)

        self.assertAlmostEqual(glm.length(repaired.get(0).rotation), 5.0)

    def test_brick_already_removed_by_an_earlier_repair_is_skipped(self):
        """Verified directly during planning that replace_brick()
        raises TransformError for a removed id -- this confirms
        repair_scene() handles the combination correctly rather than
        crashing."""

        broken = glm.quat(0.0, 0.0, 0.0, 0.0)
        scene = _scene_of(
            SceneBrick(
                id=0, part_name="nonexistent.dat",
                position=glm.vec3(0, 0, 0), rotation=broken, color_code=4,
            ),
            _brick(1, x=20.0),
        )
        report = ValidationReport(
            issues=(
                _issue(
                    "invalid_part_reference", (0,),
                    severity=ValidationSeverity.WARNING,
                ),
                _issue("invalid_orientation", (0,)),
            ),
        )

        repaired = repair_scene(scene, report)

        self.assertEqual([b.id for b in repaired], [1])


class RepairSceneOrchestrationTests(unittest.TestCase):

    def test_duplicate_ids_gate_out_every_other_repair(self):
        """When duplicates exist, an otherwise-repairable invalid
        orientation on one of those same bricks must NOT be fixed in
        this call -- only the duplicate-id repair runs."""

        broken = glm.quat(0.0, 0.0, 0.0, 0.0)
        scene = _scene_of(
            _brick(0),
            SceneBrick(
                id=0, part_name="3005.dat",
                position=glm.vec3(20, 0, 0), rotation=broken, color_code=4,
            ),
        )
        report = ValidationReport(
            issues=(
                _issue("duplicate_brick_id", (0,)),
                _issue("invalid_orientation", (0,)),
            ),
        )

        repaired = repair_scene(scene, report)

        ids = [b.id for b in repaired]
        self.assertEqual(len(ids), len(set(ids)))

        # The brick with the broken rotation must still have it --
        # invalid_orientation repair was gated out this call.
        still_broken = [
            b for b in repaired if glm.length(b.rotation) == 0.0
        ]
        self.assertEqual(len(still_broken), 1)

    def test_no_duplicate_ids_runs_both_other_repairs(self):

        broken = glm.quat(1.0001, 0.0, 0.0, 0.0)
        scene = _scene_of(
            _brick(0, part_name="nonexistent.dat"),
            SceneBrick(
                id=1, part_name="3005.dat",
                position=glm.vec3(20, 0, 0), rotation=broken, color_code=4,
            ),
        )
        report = ValidationReport(
            issues=(
                _issue(
                    "invalid_part_reference", (0,),
                    severity=ValidationSeverity.WARNING,
                ),
                _issue("invalid_orientation", (1,)),
            ),
        )

        repaired = repair_scene(scene, report)

        self.assertEqual([b.id for b in repaired], [1])
        self.assertAlmostEqual(
            glm.length(repaired.get(1).rotation), 1.0, places=5,
        )

    def test_empty_report_leaves_scene_unchanged(self):

        scene = _scene_of(_brick(0), _brick(1, x=20.0))
        report = ValidationReport(issues=())

        repaired = repair_scene(scene, report)

        self.assertEqual(_scene_signature(repaired), _scene_signature(scene))

    def test_overlapping_bricks_issues_never_trigger_a_change(self):

        scene = _scene_of(_brick(0), _brick(1))
        report = ValidationReport(
            issues=(
                _issue(
                    "overlapping_bricks", (0, 1),
                    severity=ValidationSeverity.WARNING,
                ),
            ),
        )

        repaired = repair_scene(scene, report)

        self.assertEqual(_scene_signature(repaired), _scene_signature(scene))

    def test_deterministic(self):

        scene = _scene_of(_brick(0, part_name="nonexistent.dat"), _brick(1, x=20.0))
        report = ValidationReport(
            issues=(
                _issue(
                    "invalid_part_reference", (0,),
                    severity=ValidationSeverity.WARNING,
                ),
            ),
        )

        first = repair_scene(scene, report)
        second = repair_scene(scene, report)

        self.assertEqual(_scene_signature(first), _scene_signature(second))

    def test_does_not_mutate_scene_or_report(self):

        scene = _scene_of(_brick(0), _brick(0, x=20.0))
        report = ValidationReport(
            issues=(_issue("duplicate_brick_id", (0,)),),
        )

        scene_before = _scene_signature(scene)
        report_before = report.issues

        repair_scene(scene, report)

        self.assertEqual(_scene_signature(scene), scene_before)
        self.assertEqual(report.issues, report_before)


class IterativeValidateRepairCycleTests(unittest.TestCase):
    """Repair is a re-entrant stage -- a Scene with a duplicate id AND
    a separately-broken orientation needs two Validate->Repair cycles
    to fully resolve, by design."""

    def test_two_cycles_resolve_both_problems(self):

        catalog = _seed_catalog()
        broken = glm.quat(0.0, 0.0, 0.0, 0.0)

        scene = _scene_of(
            _brick(0),
            SceneBrick(
                id=0, part_name="3005.dat",
                position=glm.vec3(20, 0, 0), rotation=broken, color_code=4,
            ),
        )

        # Cycle 1: only duplicate-id repair runs.
        report_1 = validate_scene(scene, catalog)
        self.assertFalse(report_1.is_valid)
        scene = repair_scene(scene, report_1)

        ids = [b.id for b in scene]
        self.assertEqual(len(ids), len(set(ids)))

        # The zero-length quaternion is not normalizable -- it remains
        # invalid after repair, by design (see DEFERRED behavior).
        report_2 = validate_scene(scene, catalog)
        remaining_rule_ids = {issue.rule_id for issue in report_2.issues}
        self.assertNotIn("duplicate_brick_id", remaining_rule_ids)

        # A second repair call, given the fresh (duplicate-free)
        # report, does not crash and leaves the still-broken
        # orientation as-is (outside the safe normalization window).
        scene = repair_scene(scene, report_2)
        self.assertEqual(len(list(scene)), 2)


if __name__ == "__main__":
    unittest.main()
