# StudWorks

# Package 042

## Title

Scene Repair — Correcting Only What Validation Has Already Proven Safe

---

# Mission

Implement the Scene Repair architecture: `repair_scene()` receives an
immutable Scene and an immutable `ValidationReport` (Package_040) and
returns a newly constructed, repaired immutable Scene, without ever
modifying either input. Repair performs only deterministic,
well-defined repairs — where a fix would require guessing or
unavailable metadata, the Scene is left unchanged for that issue.

---

# Scope

New:

- `repair/__init__.py` (empty, matching every other pipeline package's
  own convention)
- `repair/scene_repair.py` (`repair_scene()`, `_repair_duplicate_ids()`,
  `_repair_invalid_part_references()`, `_repair_invalid_orientations()`,
  `_has_duplicate_ids()`)

Tests:

- `tests/test_scene_repair.py` (new, 17 tests)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `serialization/`, `export/`, `project/`, `ui/`,
`generation/`, `optimization/`, `validation/`, `scene_analysis/`,
`services/`, `ldraw/`. Critically, **`transform/` itself is untouched**
— its existing primitives are consumed, never modified. This package
adds exactly one new top-level package plus one test file.

---

# Architecture Summary

`repair_scene(scene, report) -> Scene` — one pure orchestrator, three
independent private repair functions, no registry, no class wrapper.
Reuses `transform/scene_transform.py`'s existing, already-tested
`replace_brick()`/`remove_brick()` rather than introducing parallel
Scene-editing logic, per the approved requirement — a deliberate
departure from the "pipeline stages stay fully independent" convention
`optimization/`↔`validation/`↔`scene_analysis/` established (each
redefines its own small geometry constants rather than importing across
stages): `transform/` isn't a peer pipeline stage, it's the same
foundational, shared editing layer every UI tool already depends on,
predating the generation pipeline entirely.

**Every repair strategy corresponds directly to one existing
`ValidationIssue.rule_id`** — `duplicate_brick_id`,
`invalid_part_reference`, `invalid_orientation`. Repair reads only the
`rule_id`s and `brick_ids` it needs from the report and never
re-derives a validity judgment itself (e.g. it never re-checks
`glm.length()` against Package_040's own validity tolerance) — it only
inspects a brick's own data to decide *how* to fix something the report
already identified, never *whether* something needs fixing at all.
`overlapping_bricks`, and any future rule_id repair doesn't recognize,
is simply never acted on — forward-compatible by construction, not by
special-case handling.

## The duplicate-id discovery (an architectural contract, not an incidental detail)

Careful reasoning during planning — verified concretely before any
production code was written — found that `Scene.next_available_id()`
(`max(existing ids, default=-1) + 1`), while completely safe for adding
one brick to an *already-complete* Scene (how `duplicate_brick()`
already uses it), is **not** safe when rebuilding a Scene from scratch
while reassigning *multiple* duplicate ids in the same pass. A
partially-rebuilt Scene only knows about the ids added to it so far —
not the ids still to come from the rest of the original Scene — so
calling `next_available_id()` mid-rebuild can reintroduce a *new*
collision rather than resolving the original one.

Verified directly: rebuilding a Scene with ids `[0, 0, 1, 2]` by calling
`new_scene.next_available_id()` at each reassignment step produces
`[0, 1, 1, 2]` — the newly-assigned id `1` collides with the *original*
brick that already had id `1`. Computing `next_id = max(all_original_ids,
default=-1) + 1` once, upfront, from the *complete* original Scene,
before any rebuilding begins, and incrementing it manually for each
reassignment, produces `[0, 3, 1, 2]` instead — fully unique.

**This is part of this package's architectural contract, not an
implementation detail**: `_repair_duplicate_ids()` computes its
replacement id exactly this way, and the exact `[0, 0, 1, 2]` case that
exposed the bug is a permanent regression test (`test_the_exact_bug_
found_during_planning_does_not_recur`).

## Duplicate-id repair is a gating step

A duplicated id makes `ValidationIssue.brick_ids` ambiguous —
`scene.get(id)` returns only the first match, so a *different* issue
naming that same id can no longer unambiguously identify which physical
brick it meant. `repair_scene()` therefore checks
`_has_duplicate_ids(report)` first: if true, it performs **only** the
duplicate-id repair and returns immediately, attempting nothing else in
that call — verified directly with a Scene where one of two
duplicate-id-sharing bricks also has an invalid orientation: the
orientation is confirmed *not* repaired in that same call.

## Repair is intentionally re-entrant

```
Validation -> Repair -> Validation -> Repair -> ...
```

repeated until no further deterministic repair applies. A single
`repair_scene()` call is not required, or expected, to resolve every
issue — this is a direct, correct consequence of duplicate-id gating
(above), not a limitation. A new test
(`IterativeValidateRepairCycleTests`) exercises this directly: a Scene
with both a duplicate id and a separately-broken orientation needs two
full Validate → Repair cycles to fully resolve as far as it can be.

---

# Repair Summary

- **`duplicate_brick_id`**: every occurrence of a duplicated id beyond
  its first (in Scene order) is reassigned a fresh, unique id via the
  upfront-computed counter described above. The first occurrence always
  keeps its original id.
- **`invalid_part_reference`**: the named brick is removed via
  `transform.remove_brick()` — there is no deterministic way to know
  what part should have been there instead, so removal is the only
  confidently safe repair.
- **`invalid_orientation`**: the named brick's rotation is normalized
  via `transform.replace_brick()`, but *only* if its length falls
  within `[0.5, 1.5]` — a deliberately conservative, documented window,
  far looser than realistic drift (~2×10⁻⁶ for 200 accumulated
  rotations, per Package_040's own measurement) but bounded, so a
  zero-length (mathematically undefined to normalize) or wildly-off
  quaternion is left unchanged rather than guessed at.
- A brick already removed by an earlier repair in the same call (i.e.
  it had *both* an invalid part reference and an invalid orientation)
  is skipped, not treated as an error — verified directly beforehand
  that `replace_brick()` raises `TransformError` for a removed id, so
  this check is required, not defensive-for-its-own-sake.

---

# Deferred Repairs

- **`overlapping_bricks`** — no automatic repair, per the approved
  scope. Current project data provides no deterministic way to choose
  which brick should move, or where, without altering the represented
  model — multiple equally valid "fixes" exist (move brick A, move
  brick B, remove either), and none is provably correct from available
  data. `repair_scene()` never acts on this rule_id at all.
- **Quaternions outside `[0.5, 1.5]`**, including exactly zero-length —
  left unchanged, still invalid, still reported by a subsequent
  validation pass. Their "intended" rotation cannot be recovered with
  real confidence from the data alone.
- **Any issue rule_id repair doesn't recognize** (including any future
  validation rule) — never acted on, by construction, not by an
  explicit exclusion list.

---

# Test Summary

**17 tests, `tests/test_scene_repair.py`**:

- `_repair_duplicate_ids`: the exact `[0, 0, 1, 2]` regression case;
  first occurrence keeps its original id; multiple separate duplicate
  groups in one Scene; determinism.
- `_repair_invalid_part_references`: single and multiple simultaneous
  removals; unaffected bricks left alone.
- `_repair_invalid_orientations`: a nearly-unit quaternion normalized;
  a zero-length quaternion left unchanged; a wildly-off (length 5.0)
  quaternion left unchanged; a brick already removed by an earlier
  repair in the same call correctly skipped rather than raising.
- `repair_scene()` orchestration: duplicate ids gate out every other
  repair in that call (verified by confirming an otherwise-repairable
  orientation issue is *not* fixed); no duplicate ids runs both other
  repairs; an empty report leaves the Scene byte-for-byte unchanged;
  `overlapping_bricks` issues never trigger any change; determinism; no
  mutation of either input.
- The full iterative Validate → Repair → Validate → Repair cycle,
  proving the re-entrant design actually works end to end against real
  `validate_scene()` output, not just hand-constructed reports.

---

# Regression Results

Full suite: **363 tests**, all passing (346 pre-existing + 17 new).

---

# Scope Isolation Confirmation

`git status`/`git diff --stat` confirm the only change is the addition
of `src/brickforge/repair/` (two files) and `tests/test_scene_repair.py`.
`engine/`, `render/`, `selection/`, `serialization/`, `export/`,
`project/`, `ui/`, `generation/`, `optimization/`, `validation/`,
`scene_analysis/`, `services/`, `ldraw/` are completely untouched —
**`transform/scene_transform.py` itself was not modified**, confirming
its primitives were reused, not forked. An AST-based import check
confirms `scene_repair.py` depends only on `brickforge.engine.scene`,
`brickforge.transform.scene_transform`,
`brickforge.validation.build_validation`, `dataclasses`, and `glm`.

---

# Definition of Done

- A deterministic Scene Repair stage exists — `repair_scene()`,
  verified identical output across repeated calls on the same input.
- Repair never modifies its inputs — verified directly for both `Scene`
  and `ValidationReport`, not just asserted.
- Only provably safe repairs are implemented — each one traced directly
  to an existing `ValidationIssue.rule_id`, with a documented,
  conservative safety boundary (the `[0.5, 1.5]` window) where
  confidence runs out.
- Unsupported repairs are explicitly documented and deferred —
  `overlapping_bricks`, out-of-window quaternions, and any unrecognized
  rule_id, all covered above.
