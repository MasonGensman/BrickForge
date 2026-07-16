# StudWorks

# Package 022

## Title

Hidden Brick Removal — Second Scene Optimizer

---

# Mission

Implement Hidden Brick Removal as the second optimizer to run through
the Optimization Pipeline (Package_020/021): remove bricks fully
surrounded on all six sides, since they can never be visible. Proves
that the Optimization Pipeline architecture supports *multiple*
independent optimizers composing correctly — Brick Merge alone only
proved a single-optimizer pipeline works.

---

# Scope

New:

- `optimization/hidden_brick_removal_optimizer.py`

Modified (one line):

- `optimization/__init__.py` — added the self-registration import.

Untouched (verified via `git diff`, not assumed):

- `optimization/optimizer.py`, `registry.py`, `pipeline.py`,
  `brick_merge_optimizer.py`, `generation/*`, everything under `ui/`,
  `render/`, `engine/`, `services/`, `preparation/`.

---

# Inspection Findings

Re-confirmed the `Optimizer`/registry/`optimize_scene()` contract is
unchanged since Package_020/021 — no redesign needed, used exactly as
approved. `optimize_scene()`'s existing default behavior (run every
registered optimizer, in registration order, when no explicit
`optimizer_ids` is given) means a plain `optimize_scene(scene,
catalog)` call now runs Brick Merge *then* Hidden Brick Removal
automatically — exactly what "future optimizers can be added without
changing existing ones" was designed to support.

**A concrete, verified fact that simplified the design**: re-checked
`palette_engine.py` — `PaletteEngine` only ever maps
`ColorCategory.SOLID` colors, and both Flat Mosaic and Height Relief
skip transparent pixels entirely rather than emitting a colorless
brick. Every `SceneBrick` this codebase produces today is therefore
provably opaque, so the occlusion check never needs to reason about
color/transparency at all.

---

# Design

**Legal "hidden" definition**: a brick is hidden iff, in the *original,
unmodified* Scene, another brick exists at all six neighbor offsets
(±X by `stud_width*20`, ±Z by `stud_length*20`, ±Y by `height_units`,
all from the brick's own `BrickDefinition`) sharing its exact
`part_name` and `rotation`. Deliberately conservative — requiring the
same part+rotation (not just "any brick present") avoids reasoning
about whether a differently-sized or differently-oriented neighbor's
footprint actually covers the checked face, the same kind of
scope-narrowing Brick Merge applied to itself (Z-adjacent-only).

**Single pass, no fixed-point loop**: unlike Brick Merge, "hidden" is
evaluated entirely against a position index built once from the
original Scene, never updated mid-pass. This is provably idempotent:
a brick that survives one pass (because ≥1 of its 6 neighbors was
missing or non-matching) can never become "more surrounded" in a
later pass, since removal only shrinks the position index further —
proved by construction, then confirmed empirically.

**Composition with Brick Merge — a real, documented interaction**:
because `optimize_scene()`'s default runs Brick Merge first, a dense
region built from a part *that Brick Merge can merge* gets restructured
before Hidden Brick Removal ever sees it (verified directly: a solid
3×3×3 cube of `3005` bricks, run through the full default pipeline,
first collapses via Brick Merge into a mix of `3004`/`3005` bricks per
column, which no longer share a uniform part+rotation everywhere, so
Hidden Brick Removal's stricter same-part rule then applies to that
already-restructured geometry rather than the original cube). This
is expected, correct emergent behavior of two independent optimizers
composing in sequence — not a bug — and is exactly the kind of
interaction the architecture was designed to allow without either
optimizer needing to know the other exists.

---

# Definition of Done

- Hidden Brick Removal is fully implemented as an independent
  Optimizer, registered alongside Brick Merge.
- The optimization framework's multi-optimizer composition is
  validated — confirmed via `optimize_scene()`'s default running both
  in sequence correctly.
- Merge rules (here, removal rules) are deterministic — proven by
  construction (position-index lookup, no sequential/greedy state) and
  confirmed empirically.
- Input Scenes remain immutable — confirmed.
- Renderer and Generation Modes require no changes — confirmed via
  `git diff`.

---

# Verification Performed

- `py_compile` clean on the new file and updated `__init__.py`.
- **AST inspection**: zero imports from `brickforge.generation`,
  `brickforge.ui`, `brickforge.render`, or `brick_merge_optimizer`
  (kept fully independent of the sibling optimizer, matching how
  Height Relief doesn't import from Flat Mosaic).
- **Untouched-scope**: `git diff --stat` empty for
  `optimization/optimizer.py`, `registry.py`, `pipeline.py`,
  `brick_merge_optimizer.py`, and everything under `generation/`,
  `ui/`, `render/`, `engine/`, `services/`, `preparation/`.
- **Registry state**: exactly two optimizers registered
  (`brick_merge`, `hidden_brick_removal`).
- **3×3×3 uniform cube**: exactly the single center brick removed, all
  26 surface bricks (every corner, edge, and face-center) survive.
- **3 negative cases**, each independently constructed from the same
  27-brick cube: a mismatched neighbor part, a mismatched neighbor
  rotation, and one neighbor missing entirely — each correctly leaves
  the would-be-hidden brick in place.
- **Determinism**: identical input run twice → field-identical output.
- **Idempotence**: running the optimizer twice on an already-optimized
  Scene produces an identical Scene.
- **Input Scene never mutated**: confirmed the original 27-brick Scene
  is unchanged after `optimize()` runs.
- **Composition**: a combined Scene (an unmergeable-by-design 3×3×3
  cube of `3622` bricks, confirmed to have no valid Brick Merge target
  in the seed catalog, plus a separate mergeable `3005` pair) run
  through `optimize_scene()`'s default correctly merges the pair *and*
  removes the cube's center in the same call.
- **Real generation → optimization → render, end to end**: a genuine
  3×3 uniformly bright synthetic image run through the real
  `generate_height_relief()` (not hand-built Scene data) with
  `max_layers=3` produces 27 bricks across 9 equal-height columns;
  Hidden Brick Removal correctly identifies and removes exactly the
  center column's interior layer (27 → 26), confirmed the raw
  generated Scene was untouched, and rendered the optimized Scene
  through the real `Renderer.render()` path with a real GL context —
  no crash, no renderer changes required.
- `git status` confirms exactly the planned scope: one new file, one
  file with a single added import line, `Package_022.md` added, plus
  the long-standing pre-existing unstaged changes to
  `docs/ARCHITECTURE.md` and `.vscode/settings.json` (left alone, as
  always).

---

# Recommendations for Future Packages

- **023 Catalog Cache**: the real ~29s catalog-build cost (documented
  in Package_020.5) remains unaddressed; still recommended as its own
  dedicated package.
- **024 Studio Export**, **025 Cost Estimation**, **026
  Inventory-aware Optimization**: per the stated roadmap — 025/026 in
  particular would finally supply the "favor common parts"/"lower
  estimated cost" data sources Package_020 identified as missing.
- **Wiring into the UI**: `optimize_scene()` still isn't called from
  `MainWindow` — remains a separate future package.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
