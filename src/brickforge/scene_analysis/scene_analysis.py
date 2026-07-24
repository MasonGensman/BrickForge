"""
BrickForge Scene Analysis

The first Scene-level description stage (Package_041): analyze_scene()
receives an immutable Scene and returns an immutable SceneAnalysisResult
describing measurable structural properties, without ever modifying the
Scene, catalog, or Project.

Generation creates. Optimization improves. Validation judges. Analysis
describes -- and only describes. Every field here is a neutral fact
(a count, a distribution, a bounding box); none expresses validity,
severity, or quality. Questions of whether a Scene is "valid" remain
exclusively Build Validation's responsibility (validation/
build_validation.py) -- this module never imports from it, and never
will: the two stages are architecturally independent by design, not by
oversight.

SceneAnalysisResult separates two conceptually distinct kinds of
output, matching Package_041's own explicit requirement:
- SceneMeasurements: primitive, directly-computed facts -- a single
  number or bounding box each, not an aggregation over many values.
- SceneSummaries: aggregate breakdowns -- how those same facts are
  distributed across the Scene's actual parts and layers.
A measurement like unique_part_count is always kept consistent with
its corresponding summary (len(summaries.part_distribution)) by
construction, in the same single pass -- see analyze_scene().

Geometry (world-space bounding box derivation) is deliberately
reimplemented independently here rather than imported from
validation/build_validation.py's own private _world_aabb(), even
though the two are structurally similar. This mirrors an established,
repeated project convention: pipeline-stage modules stay fully
independent of each other, even at the cost of small duplication,
rather than coupling across stage boundaries (e.g. every generation
mode and optimizer independently redefines the same _STUD_LDU constant
rather than importing it from a shared location). validation/'s helper
stays private to validation/; this module's stays private to it.

Independent of engine/render/ui/generation/optimization/validation
beyond Scene/SceneBrick/PartCatalog's existing, unmodified public API
-- depends only on those, plus glm for the bounds geometry.
"""

from dataclasses import dataclass

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.models.part_definition import BrickDefinition
from brickforge.services.part_catalog import PartCatalog

#
# 1 LDraw stud = 20 LDU -- the same physical constant every generation
# mode, optimizer, and validation rule independently defines. See the
# module docstring's "pipeline-stage independence" note for why this
# module does not import it from elsewhere.
#
_STUD_LDU = 20.0


@dataclass(frozen=True, slots=True)
class SceneMeasurements:
    """
    Primitive, directly-measured facts about a Scene: each field is one
    number or one bounding box, never an aggregation over many values.
    See SceneSummaries for the corresponding breakdowns.
    """

    brick_count: int
    unique_part_count: int
    color_count: int
    layer_count: int

    #
    # World-space (min, max) enclosing every brick whose part resolves
    # in the given catalog; None if the Scene is empty or no brick's
    # part_name resolves. glm.vec3 is immutable by the same convention
    # every other use of glm.vec3/glm.quat in this codebase already
    # follows (e.g. SceneBrick.position itself) -- never reassigned
    # after construction, though Python does not enforce this.
    #
    bounds: tuple[glm.vec3, glm.vec3] | None


@dataclass(frozen=True, slots=True)
class SceneSummaries:
    """
    Aggregate breakdowns of the Scene's own primitive measurements --
    how brick_count is distributed across distinct parts and distinct
    Y-layers. Ordering is explicit and deterministic (see
    analyze_scene()), never incidental container order.
    """

    #
    # (part_name, count) pairs, sorted by part_name. Always has exactly
    # SceneMeasurements.unique_part_count entries, and the counts
    # always sum to SceneMeasurements.brick_count.
    #
    part_distribution: tuple[tuple[str, int], ...]

    #
    # (position.y, count) pairs, sorted by Y ascending. Always has
    # exactly SceneMeasurements.layer_count entries, and the counts
    # always sum to SceneMeasurements.brick_count.
    #
    layer_distribution: tuple[tuple[float, int], ...]


@dataclass(frozen=True, slots=True)
class SceneAnalysisResult:
    """
    The result of one analyze_scene() call. Immutable, deterministic,
    and independent of Project and UI -- a plain description of a
    Scene at a point in time, safe for a future caller to cache or
    reuse without any architectural change here.
    """

    measurements: SceneMeasurements
    summaries: SceneSummaries


def _world_aabb(
    brick: SceneBrick,
    definition: BrickDefinition,
) -> tuple[glm.vec3, glm.vec3]:
    """
    A brick's world-space axis-aligned bounding box, derived from the
    catalog's declared stud_width/stud_length/height_units (not the
    sometimes-absent BrickDefinition.bounding_box -- None for every
    seed-catalog part, confirmed by inspection) and accounting for
    rotation: each of the local box's 8 corners is rotated and
    translated into world space, and the enclosing box of those 8
    points is returned. Exact for an identity rotation; conservative
    (never smaller than the true rotated box) otherwise.

    Private to this module -- deliberately not imported from
    validation/build_validation.py's own equivalent helper. See the
    module docstring's "pipeline-stage independence" note.
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


def _scene_bounds(
    bricks: list[SceneBrick],
    catalog: PartCatalog,
) -> tuple[glm.vec3, glm.vec3] | None:
    """
    The world-space (min, max) enclosing every brick in `bricks` whose
    part_name resolves in `catalog`. None if there are no such bricks
    (an empty Scene, or every part is unresolvable) -- there is no
    dimension to derive a box from in either case, so this is a fact
    left unmeasured rather than approximated.
    """

    part_index = {
        definition.part_name: definition
        for definition in catalog.all()
    }

    mins: list[glm.vec3] = []
    maxs: list[glm.vec3] = []

    for brick in bricks:

        definition = part_index.get(brick.part_name)

        if definition is None:
            continue

        brick_min, brick_max = _world_aabb(brick, definition)

        mins.append(brick_min)
        maxs.append(brick_max)

    if not mins:
        return None

    return (
        glm.vec3(
            min(v.x for v in mins),
            min(v.y for v in mins),
            min(v.z for v in mins),
        ),
        glm.vec3(
            max(v.x for v in maxs),
            max(v.y for v in maxs),
            max(v.z for v in maxs),
        ),
    )


def analyze_scene(
    scene: Scene,
    catalog: PartCatalog,
) -> SceneAnalysisResult:
    """
    Measure scene and return the result as an immutable
    SceneAnalysisResult. Read-only: never modifies scene, catalog, or
    any Project.

    Deterministic: given identical (scene, catalog), always returns an
    identical result. brick_count/unique_part_count/color_count/
    layer_count and their corresponding distributions are computed in
    one combined pass over scene -- avoiding the repeated Scene
    traversal that four independently-written aggregate functions
    would otherwise cost, since each is a simple count over the same
    per-brick fields (unlike Build Validation's rules, which each
    check a genuinely distinct problem and are independently justified
    in their own full pass). bounds is computed separately, since it
    alone needs a catalog lookup and rotation geometry.
    """

    bricks = list(scene)

    part_counts: dict[str, int] = {}
    colors_seen: set[int | None] = set()
    layer_counts: dict[float, int] = {}

    for brick in bricks:

        part_counts[brick.part_name] = (
            part_counts.get(brick.part_name, 0) + 1
        )

        colors_seen.add(brick.color_code)

        layer_counts[brick.position.y] = (
            layer_counts.get(brick.position.y, 0) + 1
        )

    part_distribution = tuple(sorted(part_counts.items()))
    layer_distribution = tuple(sorted(layer_counts.items()))

    measurements = SceneMeasurements(
        brick_count=len(bricks),
        unique_part_count=len(part_distribution),
        color_count=len(colors_seen),
        layer_count=len(layer_distribution),
        bounds=_scene_bounds(bricks, catalog),
    )

    summaries = SceneSummaries(
        part_distribution=part_distribution,
        layer_distribution=layer_distribution,
    )

    return SceneAnalysisResult(
        measurements=measurements,
        summaries=summaries,
    )
