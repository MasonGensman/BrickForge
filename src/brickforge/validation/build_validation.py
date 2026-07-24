"""
BrickForge Build Validation

The first structural validation stage (Package_040): validate_scene()
receives an immutable Scene and returns a ValidationReport, without
ever modifying the Scene, catalog, or Project. Generation decides what
to build; optimization improves it; validation only reports whether it
satisfies rules this codebase's actual data can support -- it never
repairs, and it never reinterprets the image the Scene came from.

Each rule below is a standalone, independent pure function: it takes
only the arguments it needs, never calls another rule, and never
depends on another rule's output. validate_scene() is the only place
rule execution is orchestrated -- a fixed, documented sequence, not a
registry, since (unlike GenerationMode/Optimizer) validation rules are
not independently selectable at runtime; every rule always runs.

Severity is a confidence signal, not just a priority level:
- ERROR means the data itself is objectively invalid (a duplicate id,
  a rotation that isn't a valid unit quaternion) -- true regardless of
  which catalog is active.
- WARNING means the finding is only as reliable as available catalog
  metadata. An unresolved part reference may still be valid in
  BrickLink's own library (export_scene() already treats this the same
  way -- writing the part anyway, never silently dropping it). Overlap
  detection is bounded by the catalog's declared stud_width/
  stud_length/height_units, which Package_037 already showed are
  placeholder values for most real, non-seed-catalog parts -- an
  overlap finding reflects that uncertainty honestly rather than
  claiming a confidence the data doesn't support.

Explicitly deferred, not approximated (Package_040's own scope
boundary): disconnected-component detection would need real stud/tube
connectivity data, which does not exist anywhere in this codebase
(confirmed by inspection) -- a geometric-adjacency proxy would not be
real connectivity and was rejected as exactly the kind of unsupported
approximation this package avoids. Structural strength, stability, and
clutch power have no data source at all and are equally out of scope.

Independent of engine/render/ui/generation/optimization beyond Scene/
SceneBrick/PartCatalog's existing, unmodified public API -- depends
only on those, plus glm for the overlap geometry.
"""

from dataclasses import dataclass
from enum import Enum

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.models.part_definition import BrickDefinition
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDU -- the same physical constant every generation
# mode and optimizer independently defines (see e.g.
# brick_merge_optimizer.py's own docstring on why each module redefines
# it rather than sharing one).
#
_STUD_LDU = 20.0

#
# How far a quaternion's length may drift from 1.0 and still count as
# a valid rotation. Generous relative to measured reality: 200
# accumulated rotation multiplications without renormalizing drift by
# only ~2e-6 (verified during this package's planning) -- this
# tolerance exists to accept that kind of ordinary floating-point
# noise, not to paper over genuinely corrupt data.
#
_QUATERNION_LENGTH_TOLERANCE = 1e-3

#
# Sub-LDU slack for the overlap test, so two bricks placed exactly
# edge-to-edge (the normal, expected result of every existing
# generation mode) are never reported as overlapping due to
# floating-point rounding at the shared boundary.
#
_OVERLAP_EPSILON_LDU = 1e-4


class ValidationSeverity(Enum):
    """See the module docstring's "Severity is a confidence signal"
    section for what each value means and why."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One finding from one validation rule. Immutable -- a finished,
    reported fact, never mutated after construction."""

    rule_id: str
    severity: ValidationSeverity
    message: str
    brick_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """
    The result of one validate_scene() call. Immutable, and never
    owned by Scene -- a deterministic output of validation, not a
    Scene property.
    """

    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """True if no issue has ERROR severity. WARNING-only reports
        are still considered valid -- a warning reflects limited
        confidence, not a known-broken Scene."""

        return not any(
            issue.severity is ValidationSeverity.ERROR
            for issue in self.issues
        )


def _find_duplicate_ids(
    scene: Scene,
) -> list[ValidationIssue]:
    """
    ERROR: one issue per brick id used by more than one SceneBrick.
    Nothing in Scene.add_brick() prevents this today (confirmed by
    inspection) -- a duplicate id makes Scene.get() ambiguous.

    Deterministic: a set is used only for O(1) "have we seen this id"
    membership testing, never iterated for output order. The returned
    order follows the Scene's own iteration order (the order each
    duplicated id was first re-encountered), matching
    export_scene()'s own established "Scene's own existing order is
    already deterministic" precedent.
    """

    seen: set[int] = set()
    duplicated: list[int] = []

    for brick in scene:

        if brick.id in seen:

            if brick.id not in duplicated:
                duplicated.append(brick.id)

        else:
            seen.add(brick.id)

    return [
        ValidationIssue(
            rule_id="duplicate_brick_id",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Brick id {brick_id} is used by more than one brick "
                f"in the Scene."
            ),
            brick_ids=(brick_id,),
        )
        for brick_id in duplicated
    ]


def _find_invalid_part_references(
    scene: Scene,
    catalog: PartCatalog,
) -> list[ValidationIssue]:
    """
    WARNING: one issue per brick whose part_name does not resolve in
    the given catalog. WARNING, not ERROR -- an unresolved reference
    may still be a valid part BrickLink's own library recognizes, the
    same reasoning export_scene() already applies when it writes an
    unrecognized part rather than dropping it.

    Deterministic: part_index is a dict used only for membership
    testing (`not in`), never iterated for output order; issues follow
    the Scene's own iteration order.
    """

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    return [
        ValidationIssue(
            rule_id="invalid_part_reference",
            severity=ValidationSeverity.WARNING,
            message=(
                f"Brick {brick.id} references part {brick.part_name!r}, "
                f"which is not present in the current catalog."
            ),
            brick_ids=(brick.id,),
        )
        for brick in scene
        if brick.part_name not in part_index
    ]


def _find_invalid_orientations(
    scene: Scene,
) -> list[ValidationIssue]:
    """
    ERROR: one issue per brick whose rotation is not, within
    _QUATERNION_LENGTH_TOLERANCE, a valid unit quaternion. A
    non-unit-length quaternion isn't a valid rotation at all,
    regardless of which catalog is active -- an objective data problem.

    Deterministic: pure Scene iteration, no dict/set involved.
    """

    issues = []

    for brick in scene:

        length = glm.length(brick.rotation)

        if abs(length - 1.0) > _QUATERNION_LENGTH_TOLERANCE:

            issues.append(
                ValidationIssue(
                    rule_id="invalid_orientation",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Brick {brick.id}'s rotation is not a valid "
                        f"unit quaternion (length={length:.6f})."
                    ),
                    brick_ids=(brick.id,),
                )
            )

    return issues


def _world_aabb(
    brick: SceneBrick,
    definition: BrickDefinition,
) -> tuple[glm.vec3, glm.vec3]:
    """
    A brick's world-space axis-aligned bounding box, derived from the
    catalog's declared stud_width/stud_length/height_units (not the
    sometimes-absent BrickDefinition.bounding_box -- confirmed by
    inspection to be None for every seed-catalog part, the app's most
    metadata-reliable source) and accounting for rotation: each of the
    local box's 8 corners is rotated and translated into world space,
    and the enclosing box of those 8 points is returned. Exact for an
    identity rotation; conservative (never smaller than the true
    rotated box) for any other rotation -- verified directly during
    this package's planning against both cases.

    Private to this module -- Package_040's own architectural
    requirement is to avoid a reusable geometry abstraction here unless
    multiple consumers are demonstrated; render/picking.py's ray-based
    geometry is a different problem (ray-vs-box, not box-vs-box) and
    deliberately not reused.
    """

    half_x = definition.stud_width * _STUD_LDU / 2.0
    half_z = definition.stud_length * _STUD_LDU / 2.0
    height = definition.height_units

    local_min = glm.vec3(-half_x, 0.0, -half_z)
    local_max = glm.vec3(half_x, height, half_z)

    corners = [
        brick.position + brick.rotation * glm.vec3(x, y, z)
        for x in (local_min.x, local_max.x)
        for y in (local_min.y, local_max.y)
        for z in (local_min.z, local_max.z)
    ]

    xs = [corner.x for corner in corners]
    ys = [corner.y for corner in corners]
    zs = [corner.z for corner in corners]

    return (
        glm.vec3(min(xs), min(ys), min(zs)),
        glm.vec3(max(xs), max(ys), max(zs)),
    )


def _aabbs_overlap(
    a_min: glm.vec3,
    a_max: glm.vec3,
    b_min: glm.vec3,
    b_max: glm.vec3,
) -> bool:
    """
    True if two world-space AABBs overlap on all three axes, with
    _OVERLAP_EPSILON_LDU of slack so exact edge-to-edge adjacency (the
    normal result of every existing generation mode) is never reported
    as overlap -- verified directly against real generate_scene()
    output during this package's planning: zero false positives on a
    normally tiled Scene.
    """

    return (
        a_min.x < b_max.x - _OVERLAP_EPSILON_LDU
        and b_min.x < a_max.x - _OVERLAP_EPSILON_LDU
        and a_min.y < b_max.y - _OVERLAP_EPSILON_LDU
        and b_min.y < a_max.y - _OVERLAP_EPSILON_LDU
        and a_min.z < b_max.z - _OVERLAP_EPSILON_LDU
        and b_min.z < a_max.z - _OVERLAP_EPSILON_LDU
    )


def _find_overlapping_bricks(
    scene: Scene,
    catalog: PartCatalog,
) -> list[ValidationIssue]:
    """
    WARNING: one issue per pair of bricks whose world-space bounding
    boxes overlap, derived from the catalog's own declared dimensions.
    WARNING, not ERROR -- Package_037 already showed those dimensions
    are placeholder values for most real, non-seed-catalog parts, so a
    finding here is only as reliable as the active catalog's metadata.

    A brick whose part_name doesn't resolve in `catalog` is skipped
    from this check entirely (there is no dimension to derive an AABB
    from) -- it is separately reported by
    _find_invalid_part_references(), never by this function; the two
    rules never call each other.

    Deterministic and independent: builds its own part_index rather
    than reusing _find_invalid_part_references()'s (Package_040's own
    "rules must never depend on one another" requirement); pairwise
    comparison follows the Scene's own fixed iteration order, and each
    issue's brick_ids is normalized to (lower_id, higher_id) so the
    representation doesn't depend on which of the pair the Scene
    happened to iterate first.
    """

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    bricks = list(scene)

    aabbs: list[tuple[glm.vec3, glm.vec3] | None] = [
        (
            _world_aabb(brick, part_index[brick.part_name])
            if brick.part_name in part_index
            else None
        )
        for brick in bricks
    ]

    issues = []

    for i in range(len(bricks)):

        if aabbs[i] is None:
            continue

        for j in range(i + 1, len(bricks)):

            if aabbs[j] is None:
                continue

            if _aabbs_overlap(*aabbs[i], *aabbs[j]):

                brick_ids = tuple(
                    sorted((bricks[i].id, bricks[j].id))
                )

                issues.append(
                    ValidationIssue(
                        rule_id="overlapping_bricks",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Bricks {brick_ids[0]} and {brick_ids[1]} "
                            f"appear to overlap based on catalog-"
                            f"declared dimensions, which may be "
                            f"placeholder data for this part."
                        ),
                        brick_ids=brick_ids,
                    )
                )

    return issues


def validate_scene(
    scene: Scene,
    catalog: PartCatalog,
) -> ValidationReport:
    """
    Run every validation rule against scene and return the combined,
    immutable ValidationReport. Read-only: never modifies scene,
    catalog, or any Project.

    Deterministic: given identical (scene, catalog), always returns an
    identical report. Issues are ordered first by rule, in this fixed
    sequence, then by each rule's own internal (Scene-iteration-order)
    result -- never by incidental dict/set iteration.
    """

    issues: list[ValidationIssue] = []

    issues.extend(_find_duplicate_ids(scene))
    issues.extend(_find_invalid_part_references(scene, catalog))
    issues.extend(_find_invalid_orientations(scene))
    issues.extend(_find_overlapping_bricks(scene, catalog))

    return ValidationReport(issues=tuple(issues))
