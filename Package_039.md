# StudWorks

# Package 039

## Title

Scene Optimization — Modernizing the Existing Pipeline for Candidates and Constraints

---

# Mission

Integrate the Generation Candidate System (Packages 036–038) into the
existing Scene Optimization architecture (Packages 020–022), so
optimizers that select or replace bricks route candidate discovery
through `candidates_for()` and respect `GenerationConstraints`, exactly
as generation itself already does. No new optimization algorithm, no
duplicate infrastructure — this package modernizes an architecture that
already exists rather than expanding its capabilities.

---

# Scope

Modified:

- `optimization/optimizer.py` — `OptimizeCallable` widened with a
  `constraints: GenerationConstraints | None` parameter
- `optimization/pipeline.py` — `optimize_scene()` gains an optional
  `constraints` parameter, threaded to every optimizer in the chain
- `optimization/brick_merge_optimizer.py` — `_find_merge_target()`
  sources candidates via `candidates_for()` instead of a direct
  `catalog.all()` scan; `constraints` threaded through
  `optimize_brick_merge()` → `_merge_pass()` → `_find_merge_target()`
- `optimization/hidden_brick_removal_optimizer.py` — accepts
  `constraints` for protocol conformance, documented as intentionally
  unused

Tests:

- `tests/test_optimization.py` (new, 14 tests — first dedicated
  coverage for any file in `optimization/`)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `transform/`, `serialization/`, `export/`, `project/`,
`ui/`, `services/`, `ldraw/`, and every existing file in `generation/`
(`mosaic_generator.py`, `height_relief_generator.py`, `registry.py`,
`generation_mode.py`, `candidates.py`, `generation_engine.py`). This
package touches only the four files in `optimization/`.

---

# Inspection Findings

(Full detail in the approved planning turn.) The Scene Optimization
stage this mission asked to "implement" already existed, nearly fully
formed, from Packages 020–022: `optimize_scene()` was already the one
public entry point, already deterministic, already returned new
immutable Scenes built only through `Scene()`/`add_brick()`, and both
registered optimizers (`brick_merge_optimizer.py`,
`hidden_brick_removal_optimizer.py`) already isolated their decisions
behind small pure helpers (`_find_merge_target`, `_is_hidden`) —
precisely the architecture this mission's own "keep optimization policy
separate" section asks for, already in place.

The one genuine, load-bearing gap: `optimize_scene()` had zero real
consumers anywhere (confirmed via grep — mirroring `analyze()` before
Package_038), and neither optimizer accepted or respected
`GenerationConstraints`. `brick_merge_optimizer.py`'s
`_find_merge_target()` selected replacement parts via a raw
`catalog.all()` scan — a direct contradiction of this package's "never
bypass candidate queries" instruction, since it predates Package_036.
`hidden_brick_removal_optimizer.py`'s own `catalog.all()` usage was
confirmed to be metadata *lookup* of an already-placed brick's own
definition, never *selection* of a new one — correctly left unchanged
per the approved plan's lookup-vs-selection distinction.

A real, existing regression anchor was found and preserved:
`tests/test_export_golden_files.py::build_merged_column_scene()` calls
`optimize_scene(raw, catalog)` with no constraints argument and expects
four bricks to collapse to one. Verified directly, both by inspection
(`candidates_for(catalog, None) == catalog.all()`, same content and
order) and by running the actual golden-file test before and after
implementation — byte-identical, unchanged.

---

# Architecture Summary

Extended, not replaced — no second pipeline, no duplicate registry, no
alternate entry point, per the approved requirements. `OptimizeCallable`
now reads `(scene, catalog, constraints) -> Scene`; `optimize_scene()`
gained one new optional parameter (`constraints=None`), threaded
unchanged to every optimizer in the registered chain.

`_find_merge_target()` now calls `candidates_for(catalog, constraints)`
instead of `catalog.all()`, with its dimensional-match predicate and
deterministic lowest-part-number tie-break otherwise untouched. This
means a user's `GenerationConstraints` (an excluded part, a category
restriction, a permitted-colors list) is now honored during
optimization exactly as it already is during generation — a merge can
no longer introduce a part the user explicitly excluded.
`optimize_brick_merge()`/`_merge_pass()` thread `constraints` straight
down this existing call chain with no restructuring.

`hidden_brick_removal_optimizer.py`'s `optimize_hidden_brick_removal()`
gained the same parameter for uniform `OptimizeCallable` conformance,
but never reads it — documented explicitly as: this optimizer only
removes bricks, it never selects or introduces a new one, so there is
nothing for constraints to narrow. Verified directly (not just
asserted): passing an arbitrary, non-`None` `GenerationConstraints`
produces byte-identical output to passing `None`.

---

# Integration Summary

`GenerationConstraints`, first introduced for the Generation Candidate
System (Package_036) and made load-bearing for generation itself
(Package_038), now flows through the *entire* pipeline the mission's
own diagram describes:

```
Generation Engine → Immutable Scene → Scene Optimization → Renderer / Export / Save
```

`optimize_scene(scene, catalog, constraints=None)` is confirmed to
compose directly with Package_038's `generate_scene()` — a new
end-to-end test builds a `GenerationInput`, generates a Scene, and
optimizes it in one pipeline, verifying the result serializes and
exports without modification, with no code changes needed in either
`serialization/` or `export/`. No production call site invokes this
composition yet — matching Package_038's own precedent of stopping at
architecture, since nothing in this package's Definition of Done
required UI wiring.

---

# Test Summary

**14 tests, `tests/test_optimization.py`** (first dedicated coverage
for any file in `optimization/`):

- `_find_merge_target()`: unconstrained finds the natural target (3005
  → 3004 on the seed catalog); excluding that target via
  `GenerationConstraints` correctly yields `None`; determinism.
- `optimize_brick_merge()`: unconstrained behavior unchanged (two
  adjacent 1x1 bricks merge into one 1x2); constraints genuinely
  prevent a merge that would otherwise happen — the one behavior this
  package makes newly possible; no mutation of Scene, catalog, or
  constraints; determinism.
- `optimize_hidden_brick_removal()`: removes a fully-surrounded brick;
  behavior is byte-identical regardless of which constraints are
  passed (proving it's genuinely unused, not silently broken); no
  input mutation.
- `optimize_scene()` pipeline: unconstrained behavior matches the
  pre-Package_039 implementation directly (mirroring the existing
  golden-file test at the unit level); constraints thread through
  every optimizer in the chain; determinism.
- End-to-end: a real `GenerationInput` → `generate_scene()` →
  `optimize_scene()` composition produces a valid Scene with brick
  count no greater than the input, that serializes and exports through
  the existing, unmodified `serialization/`/`export/` code paths.

---

# Regression Results

Full suite: **298 tests**, all passing (284 pre-existing + 14 new).
`tests/test_export_golden_files.py`'s `merged_column` golden file and
its `test_merged_column_scene_is_actually_optimized` check specifically
re-verified passing, byte-for-byte and behaviorally unchanged.

---

# Scope Isolation Confirmation

`git diff --stat` confirms only the four files in `optimization/`
changed: `optimizer.py`, `pipeline.py`, `brick_merge_optimizer.py`,
`hidden_brick_removal_optimizer.py`. `engine/`, `render/`, `selection/`,
`transform/`, `serialization/`, `export/`, `project/`, `ui/`,
`services/`, `ldraw/`, and every pre-existing file in `generation/` are
completely untouched. An AST-based import check confirms the only new
dependency across all four modified files is
`brickforge.generation.candidates` — no render/UI/OpenGL coupling
introduced anywhere.

---

# Definition of Done

- A deterministic Scene Optimization stage exists — confirmed already
  present from Packages 020–022, now integrated with the Candidate
  System.
- Optimization returns new immutable Scenes — unchanged, verified via
  no-mutation tests on every modified function.
- Optimization strategy is isolated behind small pure helpers —
  `_find_merge_target()`/`_is_hidden()` continue to be exactly this,
  extended rather than restructured.
- Existing downstream systems require no modification — verified
  directly against serialization and export, not just asserted.
- The architecture is ready for structural validation — `constraints`
  now flows end-to-end from generation through optimization, giving a
  future validation package the same consistent input shape to build on.

---

# Current Optimization Limitations (deliberate, not defects)

- No new optimization algorithm was added — `brick_merge`/
  `hidden_brick_removal` remain the only two registered optimizers,
  covering four of the mission's five "possible example" optimizations
  already. "Simplify rectangular regions" (2D region merging, a
  meaningfully more complex undertaking) remains unbuilt, per the
  approved scope.
- `brick_merge_optimizer.py`'s merge target discovery inherits
  Package_037's known catalog-metadata gap: against the real,
  non-seed-catalog production data, most parts still report placeholder
  dimensions, so merge targets are only reliably found within the
  9-part seed catalog today — an existing, documented limitation this
  package doesn't change.
- No UI wiring — matches Package_038's own precedent; nothing in this
  package's Definition of Done required it.
