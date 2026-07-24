# StudWorks

# Package 041

## Title

Scene Analysis — Describing, Never Judging, a Scene's Structural Properties

---

# Mission

Implement the Scene Analysis architecture: `analyze_scene()` receives
an immutable Scene and returns an immutable `SceneAnalysisResult`
describing measurable structural properties, without ever modifying
the Scene, catalog, or Project. Generation creates; optimization
improves; validation judges; analysis describes — and only describes.

---

# Scope

New:

- `scene_analysis/__init__.py` (empty, matching `analysis/`/
  `preparation/`'s own convention)
- `scene_analysis/scene_analysis.py` (`SceneMeasurements`,
  `SceneSummaries`, `SceneAnalysisResult`, `analyze_scene()`, private
  `_world_aabb()`/`_scene_bounds()`)

Tests:

- `tests/test_scene_analysis.py` (new, 22 tests)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `transform/`, `serialization/`, `export/`, `project/`,
`ui/`, `generation/`, `optimization/`, `validation/`, `services/`,
`ldraw/`, and the existing image-focused `analysis/` package. This
package adds exactly one new top-level package plus one test file.

---

# Inspection Findings

(Full detail in the approved planning turn.) `ValidationReport`/
`ValidationIssue` (Package_040) are judgments — pass/fail with
severity — cleanly distinct in kind from the neutral measurements this
package produces; analysis doesn't consume validation's output at all.
Package_040's private `_world_aabb()` computes almost exactly what this
package's `bounds` measurement needs — considered importing it, and
recommended against: this codebase has a strong, repeated, deliberate
precedent of pipeline-stage modules staying fully independent even at
the cost of small duplication (`_STUD_LDU = 20.0` alone is
independently redefined in six separate modules across generation,
optimization, and validation, each documented as a deliberate choice).
This module reimplements the same geometry independently rather than
importing from `validation/`.

`BrickDefinition.bounding_box` remains `None` for every seed-catalog
part (confirmed again by inspection, same finding as Package_040) —
`stud_width`/`stud_length`/`height_units` are used instead, for the
same reason Package_040 already established.

Verified empirically, end-to-end, against real `generate_scene()`
output before finalizing the design: a 16-brick generated Scene (2
colors, 1 part, 1 layer) produced exactly the expected `brick_count`,
`unique_part_count`, `color_count`, `layer_count`, and world-space
`bounds`.

---

# Architecture Summary

New top-level package `scene_analysis/` — not nested inside the
existing, image-only `analysis/` package (which has zero `Scene`/
`SceneBrick` dependency, confirmed via AST import check), matching
Package_040's own precedent of a new top-level package per major
pipeline stage. One pure function, one immutable result type, no
registry.

**Measurements and summaries are structurally separated**, per the
approved architectural requirement — not just documented by comment,
but two distinct nested frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class SceneMeasurements:
    brick_count: int
    unique_part_count: int
    color_count: int
    layer_count: int
    bounds: tuple[glm.vec3, glm.vec3] | None

@dataclass(frozen=True, slots=True)
class SceneSummaries:
    part_distribution: tuple[tuple[str, int], ...]   # sorted by part_name
    layer_distribution: tuple[tuple[float, int], ...] # sorted by Y

@dataclass(frozen=True, slots=True)
class SceneAnalysisResult:
    measurements: SceneMeasurements
    summaries: SceneSummaries
```

`SceneMeasurements` holds single numbers/bounds; `SceneSummaries` holds
breakdowns across the Scene's own parts and layers. The two are kept
consistent by construction — `unique_part_count`/`layer_count` and
`len(part_distribution)`/`len(layer_distribution)` are computed from
the exact same underlying dict in the same pass, never independently
— and this consistency is directly tested, not just assumed.

**Single combined pass for the four cheap aggregates**
(`brick_count`/`part_distribution`/`color_count`/`layer_distribution`),
per the mission's own "avoid duplicate Scene traversal" guidance —
these are all simple counts over the same per-brick fields, unlike
Build Validation's four rules, which each check a genuinely distinct
problem and are independently justified in doing their own full pass.
`bounds` is computed separately, since it alone needs a catalog lookup
and rotation geometry.

**Deterministic distribution ordering, by explicit design, not
incidental container order**: `part_distribution` sorted by
`part_name`, `layer_distribution` sorted by Y ascending — verified
directly with a test that inserts bricks in reverse-Y order and
confirms the result still comes back ascending.

**Describes, never judges** — every field is a neutral fact (a count,
a distribution, a bounding box); none expresses validity, severity, or
quality. Questions of Scene validity remain exclusively Build
Validation's responsibility.

---

# Analysis Summary

`analyze_scene(scene, catalog) -> SceneAnalysisResult` — required
`catalog` (needed for `bounds`; making it optional would only add a
confusing "some fields are `None` without a catalog" mode for no real
benefit). A brick whose `part_name` doesn't resolve in `catalog` is
excluded from `bounds` only — every other measurement needs no catalog
lookup at all.

**Deliberately scoped down from the mission's full example list**: no
separate "height statistics" field — `bounds` (vertical extent) plus
`layer_count`/`layer_distribution` (Y-structure) already describe what
that would report, and a third, overlapping field would be redundant.
No `color_distribution` — only `color_count` is named in the mission's
own list; a full breakdown is easy to add later but wasn't evidenced as
needed now. No connectivity-derived measurements — matches Package_040's
own reasoning: no stud/tube data exists anywhere in this codebase.

---

# Test Summary

**22 tests, `tests/test_scene_analysis.py`**:

- Empty Scene: every count is `0`, both distributions are `()`,
  `bounds` is `None` — no special-casing needed, verified directly.
- Brick/part/color/layer counts and their distributions, against
  hand-built fixtures, including `color_code=None` correctly counted
  as its own distinct value.
- `bounds`: single-brick and multi-brick enclosure, an unresolvable
  part correctly excluded (and correctly yields `None` when *every*
  part is unresolvable), and a genuinely discriminating rotation test
  (a 3010's long axis measurably swings from Z onto X after a 90°
  rotation — both orientations checked directly, matching Package_040's
  own technique for the identical underlying geometry question).
- Deterministic distribution ordering, proven with a Scene built in
  deliberately reversed insertion order.
- Measurement/summary consistency: `unique_part_count`/`layer_count`
  match their distributions' lengths, and each distribution's counts
  sum to `brick_count` — the explicit cross-check the approved
  architectural requirement asked for.
- Immutability: `SceneAnalysisResult`, `SceneMeasurements`, and
  `SceneSummaries` each raise `dataclasses.FrozenInstanceError` on
  attempted attribute assignment.
- Determinism (repeated calls produce an equal result) and no mutation
  of `Scene`/`catalog`.
- The exact end-to-end check performed during planning, turned into a
  permanent regression test against real `generate_scene()` output.

---

# Regression Results

Full suite: **346 tests**, all passing (324 pre-existing + 22 new).

---

# Scope Isolation Confirmation

`git status`/`git diff --stat` confirm the only change is the addition
of `src/brickforge/scene_analysis/` (two files) and
`tests/test_scene_analysis.py`. `engine/`, `render/`, `selection/`,
`transform/`, `serialization/`, `export/`, `project/`, `ui/`,
`generation/`, `optimization/`, `validation/`, `services/`, `ldraw/`,
and the existing `analysis/` package are completely untouched. An
AST-based import check confirms `scene_analysis.py` depends only on
`brickforge.engine.scene`, `brickforge.engine.scene_brick`,
`brickforge.models.part_definition`, `brickforge.services.part_catalog`,
`dataclasses`, and `glm` — in particular, no import from `validation/`,
confirming pipeline-stage independence was actually kept, not just
claimed.

---

# Definition of Done

- A deterministic Scene Analysis stage exists — `analyze_scene()`,
  verified identical output across repeated calls on the same input.
- Analysis never modifies Scene — verified directly, not just asserted.
- Analysis returns immutable result objects — three frozen dataclasses,
  each tested for immutability directly.
- Only directly measurable properties are reported — every field traces
  to a `SceneBrick`/`BrickDefinition` field with no inference beyond
  arithmetic (counting, sorting, bounding-box enclosure).
- Shared measurements are identified and documented based on actual
  reuse potential — the mission's own named examples (brick/part/color/
  layer counts, distributions, bounds), with reasoning given for each
  measurement *not* included (height statistics, color distribution,
  connectivity).

---

# Deferred Measurements (documented, not built)

- **Height statistics** as a distinct field — redundant with `bounds`
  (vertical extent) and `layer_count`/`layer_distribution` (Y-structure)
  together; not added to avoid an overlapping third representation of
  the same underlying facts.
- **Color distribution** (a full color → count breakdown, mirroring
  `part_distribution`) — not named in the mission's own example list;
  trivially addable later at the same cost/shape as `part_distribution`
  if a concrete consumer emerges, but not built speculatively now.
- **Any connectivity-, strength-, or physics-derived measurement** — no
  supporting data exists anywhere in this codebase, the same finding
  Package_040 already established for the identical reason.
