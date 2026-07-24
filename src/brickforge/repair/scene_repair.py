"""
BrickForge Scene Repair

The first Scene-correction stage (Package_042): repair_scene() receives
an immutable Scene and an immutable ValidationReport (Package_040) and
returns a newly constructed, repaired immutable Scene, without ever
modifying either input.

Generation creates. Optimization improves. Validation detects.
Analysis measures. Repair corrects -- and only what validation has
already detected. Repair never performs validation, and never
discovers a new kind of problem on its own: every repair strategy here
corresponds directly to one existing ValidationIssue.rule_id. Where a
fix would require guessing, multiple equally valid solutions, or
metadata this codebase doesn't have, the Scene is left unchanged for
that issue -- an honest "not confidently repairable" outcome, not an
approximation.

Reuses transform/scene_transform.py's existing, already-tested
immutable editing primitives (replace_brick, remove_brick) rather than
introducing parallel Scene-editing logic. transform/ is not treated as
a peer pipeline stage to stay independent from (unlike how generation/
optimization/validation/scene_analysis each independently redefine
small geometry constants rather than importing across stage
boundaries) -- it is the same kind of foundational, shared editing
layer every UI editing tool already depends on, and reusing it avoids
two divergent implementations of "remove a brick" existing side by
side. transform/ itself is never modified by this package.

Repair is intentionally a re-entrant pipeline stage, not a
single-pass fixer:

    Validation -> Repair -> Validation -> Repair -> ...

repeated until no further deterministic repair is available. A single
repair_scene() call is not required, or expected, to resolve every
issue in one pass -- see "Duplicate-id gating" below for the concrete
reason why, and DEFERRED REPAIRS for what is never resolved
automatically at all.

Independent of engine/render/ui/generation/optimization/scene_analysis
beyond Scene/SceneBrick's existing, unmodified public API, plus
transform/scene_transform.py and validation/build_validation.py (for
the ValidationReport/ValidationIssue types it consumes) -- depends only
on those, plus glm for quaternion normalization.
"""

import dataclasses

import glm

from brickforge.engine.scene import Scene
from brickforge.transform.scene_transform import remove_brick, replace_brick
from brickforge.validation.build_validation import ValidationReport

#
# How far a quaternion's length may be from 1.0 and still be
# confidently, safely normalized rather than left unchanged. Far
# looser than realistic drift (~2e-6 for 200 accumulated rotations,
# measured in Package_040) but deliberately bounded: a quaternion
# outside this window (including exactly zero, which is mathematically
# undefined to normalize) is treated as not confidently repairable --
# its "intended" rotation cannot be recovered with any real confidence,
# so it is left unchanged, still invalid, and still reported by a
# subsequent validation pass. This is a conservative, documented
# choice, not a measured threshold -- no real-world corruption data
# exists to derive one from.
#
_SAFE_NORMALIZATION_MIN_LENGTH = 0.5
_SAFE_NORMALIZATION_MAX_LENGTH = 1.5

_DUPLICATE_ID_RULE = "duplicate_brick_id"
_INVALID_PART_REFERENCE_RULE = "invalid_part_reference"
_INVALID_ORIENTATION_RULE = "invalid_orientation"


def _has_duplicate_ids(
    report: ValidationReport,
) -> bool:

    return any(
        issue.rule_id == _DUPLICATE_ID_RULE
        for issue in report.issues
    )


def _repair_duplicate_ids(
    scene: Scene,
    report: ValidationReport,
) -> Scene:
    """
    Reassign a new, unique id to every occurrence of a duplicated id
    beyond its first -- the first occurrence (in Scene order) always
    keeps its original id.

    Architectural contract, discovered during this package's planning
    and empirically confirmed before writing any other code: the
    replacement id is computed ONCE, from every id in the *complete*
    original scene, before any rebuilding begins, then incremented
    deterministically as each replacement is made. Scene.
    next_available_id() is NOT used here, even though its formula is
    the same (max(ids, default=-1) + 1) -- calling it against a
    Scene under incremental construction only sees the ids added so
    far, not the ids still to come from the rest of the original
    Scene, and can reintroduce a new collision with one of them.
    Verified directly: rebuilding a Scene with ids [0, 0, 1, 2] via
    new_scene.next_available_id() at each step produces [0, 1, 1, 2]
    -- a NEW collision with the original id 1, not a fix. Computing
    next_id = max(all_original_ids, default=-1) + 1 upfront and
    incrementing it manually produces [0, 3, 1, 2] instead -- fully
    unique, verified the same way.
    """

    all_ids = [brick.id for brick in scene]
    next_id = max(all_ids, default=-1) + 1

    new_scene = Scene()
    seen: set[int] = set()

    for brick in scene:

        if brick.id in seen:

            brick = dataclasses.replace(brick, id=next_id)
            next_id += 1

        else:
            seen.add(brick.id)

        new_scene.add_brick(brick)

    return new_scene


def _repair_invalid_part_references(
    scene: Scene,
    report: ValidationReport,
) -> Scene:
    """
    Remove every brick named by an invalid_part_reference issue --
    there is no deterministic way to know what part should have been
    there instead, so removal is the only confidently safe repair.
    Assumes ids in `scene` are unique (repair_scene() only calls this
    when _has_duplicate_ids(report) is False).
    """

    invalid_ids = [
        issue.brick_ids[0]
        for issue in report.issues
        if issue.rule_id == _INVALID_PART_REFERENCE_RULE
    ]

    for brick_id in invalid_ids:

        if scene.get(brick_id) is not None:
            scene = remove_brick(scene, brick_id)

    return scene


def _repair_invalid_orientations(
    scene: Scene,
    report: ValidationReport,
) -> Scene:
    """
    Normalize the rotation of every brick named by an
    invalid_orientation issue, but only when its length falls within
    [_SAFE_NORMALIZATION_MIN_LENGTH, _SAFE_NORMALIZATION_MAX_LENGTH] --
    see that constant's own comment for why values outside this range
    are left unchanged rather than guessed at.

    A brick already removed by an earlier repair in the same call
    (i.e. it also had an invalid_part_reference issue) is skipped, not
    treated as an error -- verified directly that this is a real,
    reachable case: replace_brick() raises TransformError for a
    brick id no longer present, so this check is required, not
    defensive-for-its-own-sake.

    Assumes ids in `scene` are unique, for the same reason as
    _repair_invalid_part_references().
    """

    invalid_ids = [
        issue.brick_ids[0]
        for issue in report.issues
        if issue.rule_id == _INVALID_ORIENTATION_RULE
    ]

    for brick_id in invalid_ids:

        brick = scene.get(brick_id)

        if brick is None:
            continue

        length = glm.length(brick.rotation)

        if not (
            _SAFE_NORMALIZATION_MIN_LENGTH
            <= length
            <= _SAFE_NORMALIZATION_MAX_LENGTH
        ):
            continue

        updated = dataclasses.replace(
            brick,
            rotation=glm.normalize(brick.rotation),
        )

        scene = replace_brick(scene, updated)

    return scene


def repair_scene(
    scene: Scene,
    report: ValidationReport,
) -> Scene:
    """
    Return a newly constructed Scene with every confidently-repairable
    issue in `report` corrected. Never modifies scene or report.

    Duplicate-id gating (Package_042's own architectural contract): a
    duplicated id makes ValidationIssue.brick_ids ambiguous -- it can
    no longer uniquely identify which physical brick an *other* issue
    meant, since scene.get(id) only ever returns the first match. If
    `report` contains any duplicate_brick_id issue, this call performs
    ONLY that repair and returns immediately; no other repair is
    attempted in the same invocation. The intended workflow is
    iterative: Validation -> Repair -> Validation -> Repair -> ...,
    re-validating the result and calling repair_scene() again with a
    fresh report, until no further deterministic repair applies. A
    single call resolving everything in one pass is not required, or
    expected, by this design.

    Every repair here corresponds directly to one existing
    ValidationIssue.rule_id (duplicate_brick_id,
    invalid_part_reference, invalid_orientation) -- overlapping_bricks,
    and any issue rule_id this function doesn't recognize, is left
    entirely alone: repair never invents a strategy validation didn't
    already name. See the module's DEFERRED REPAIRS note (and
    Package_042.md) for why overlap has no automatic repair.

    Deterministic: given identical (scene, report), always returns an
    identical Scene.
    """

    if _has_duplicate_ids(report):
        return _repair_duplicate_ids(scene, report)

    scene = _repair_invalid_part_references(scene, report)
    scene = _repair_invalid_orientations(scene, report)

    return scene
