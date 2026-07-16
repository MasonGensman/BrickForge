# StudWorks

# Package 021

## Title

Brick Merge Optimizer — First Concrete Scene Optimizer

---

# Mission

Implement the first optimizer to run through the Optimization Pipeline
designed in Package_020: a conservative Brick Merge optimizer that
replaces groups of identical, adjacent bricks with a larger equivalent
part whenever the replacement is exact, validating the optimization
architecture while giving generated models an immediately visible
improvement (fewer, larger bricks).

---

# Scope

New package `optimization/` (zero existing files touched):

- `optimization/optimizer.py`
- `optimization/registry.py`
- `optimization/pipeline.py`
- `optimization/brick_merge_optimizer.py`
- `optimization/__init__.py`

Untouched (verified via `git diff`, not assumed):

- `generation/*`, everything under `ui/`, `render/`, `engine/`,
  `services/`, `preparation/`

---

# Revisions Applied (per your approval)

1. **No hardcoded substitution table.** The originally-proposed
   3-entry hardcoded `{"3005.dat": "3004.dat", ...}` table was replaced
   with `_find_merge_target()`, which inspects the *active* catalog at
   runtime for a part whose `category`/`stud_width`/`height_units`
   match the source and whose `stud_length` is exactly double —
   deterministic tie-break by lowest `part_number` if more than one
   candidate matches. This scales to any catalog without code changes;
   verified it independently rediscovers the same 3 seed-catalog cases
   the original plan proposed, purely from the catalog's own declared
   dimensions.
2. **No delay over the midpoint-placement question.** The merged
   brick's position is the exact midpoint of the two source positions
   — the same centered-grid convention Flat Mosaic/Height Relief
   already use, per your instruction to follow the generation
   pipeline's own convention rather than block on independent
   geometric proof.
3. **Added idempotence verification**: running the optimizer twice on
   an already-optimized Scene produces an identical Scene (see
   Verification Performed).

**Design consequence of these revisions**: satisfying true idempotence
with a catalog-driven (not artificially-restricted) target search
required the optimizer to run its pairwise pass **to a fixed point**
within one `optimize()` call, not just once. A chain of merges (e.g.
four `1x1`s in a column) will cascade — first pass produces two `1x2`s,
which are themselves now adjacent by the identical rule, so a second
internal pass merges them into one `1x4` — entirely within a single
call. This is a natural consequence of deriving targets from the
catalog rather than an ad hoc addition; documented in the module
docstring and confirmed by testing below.

---

# What Changed

## `optimization/optimizer.py` (new)

- `OptimizeCallable` Protocol, `Optimizer` frozen dataclass (`id`,
  `display_name`, `description`, `version`, `optimize`) — exactly the
  Package_020-approved contract, no settings-panel field (optimizers
  have no per-optimizer UI in this design).

## `optimization/registry.py` (new)

- `register_optimizer`/`list_optimizers`/`get_optimizer`, structurally
  identical to `generation/registry.py`.

## `optimization/pipeline.py` (new)

- `optimize_scene(scene, catalog, optimizer_ids=None) -> Scene` — the
  public entry point (renamed from the originally-proposed
  `run_pipeline` back in Package_020). Runs every registered optimizer
  in registration order by default, or an explicit ordered subset.

## `optimization/brick_merge_optimizer.py` (new)

- `_find_merge_target(source, catalog)` — catalog-driven target
  discovery (no hardcoded table), described above.
- `_merge_pass(bricks, ...)` — one deterministic pairwise pass:
  bricks grouped by `(part_name, color_code, rotation, Y, X)`; within
  each group, sorted by Z and greedily paired left-to-right when the
  gap between consecutive bricks exactly equals the source part's own
  `stud_length * 20`. Resolves ties deterministically (3-in-a-row:
  rows 0–1 merge, row 2 stands alone).
- `optimize_brick_merge(scene, catalog) -> Scene` — repeats
  `_merge_pass` until a full pass finds nothing left to merge (a fixed
  point), then builds and returns a new `Scene`. Never mutates the
  input `Scene`; unmerged bricks are passed through by reference,
  merged bricks are new `SceneBrick` instances.
- Registers itself as `Optimizer(id="brick_merge", ..., version=1)`.

## `optimization/__init__.py` (new)

- Imports `brick_merge_optimizer` for its self-registration side
  effect — the one place that knows which concrete optimizers exist,
  mirroring `generation/__init__.py`'s role exactly.

---

# Definition of Done

- The Brick Merge optimizer is fully designed and implemented.
- Every merge preserves identical geometry: only bricks with identical
  part, color, rotation, and Y layer, at an exact adjacency gap, are
  merged; the result sits at the exact midpoint of the two sources.
- The optimizer validates the Optimization Pipeline architecture —
  confirmed by running it through `optimize_scene()` against a real
  Flat-Mosaic-generated Scene (not just hand-built test data).
- Renderer and Generation Modes remain completely unchanged (`git
  diff` empty on both).

---

# Verification Performed

- `py_compile` clean on all five new files.
- **AST inspection**: zero imports from `brickforge.generation`,
  `brickforge.ui`, or `brickforge.render` anywhere in `optimization/`.
- **Untouched-scope**: `git diff --stat` empty for `generation/*` and
  everything under `ui/`, `render/`, `engine/`, `services/`,
  `preparation/`.
- **Registry state**: exactly one optimizer registered (`brick_merge`).
- **Catalog-driven discovery**: `_find_merge_target()` independently
  rediscovers all 3 seed-catalog cases (`3005→3004`, `3004→3010`,
  `3003→3001`) purely from declared dimensions — no table consulted.
  Also confirmed a part with no valid target (`3010`, would need a
  nonexistent `1x8`) correctly returns `None`.
- **Exact merge correctness**: hand-built two-brick case — correct
  target part, correct midpoint position, correct id (`min` of the
  two), correct shared color/rotation.
- **5 negative cases**, each independently tested: different color,
  different rotation, different Y layer, non-adjacent (gap between),
  different part — every case correctly produces zero merges.
- **3-in-a-row**: confirmed deterministic — rows 0–1 merge, row 2 left
  standalone, never the reverse.
- **Chained/cascading merge**: 4× identical bricks in a column
  collapse through the internal fixed-point loop directly to one
  `1x4`, at the correct midpoint of the full span.
- **Determinism**: identical input run twice → field-identical output.
- **Idempotence** (your added requirement): running the optimizer
  twice on an already-optimized Scene produces an identical Scene —
  checked both for a fully-reduced case and for a case with a leftover
  unmerged brick (3-in-a-row's result).
- **Input Scene never mutated**: confirmed the original Scene's brick
  count/values are unchanged after `optimize()` runs.
- **Real generation → optimization → render, end to end**: generated
  an actual 6-brick Flat Mosaic `Scene` (not hand-built) from a
  synthetic image, ran it through `optimize_scene()`, confirmed it
  reduces to 2 bricks (`1x4` + `1x2`, correctly cascading rather than
  stopping at the naive 3×`1x2` first-pass result), confirmed the raw
  Scene was untouched, and rendered the optimized Scene through the
  real `Renderer.render()` path with a real GL context — no crash, no
  renderer changes required.
- **Live application launch**: real GPU context, `optimization/` loads
  and registers independently of `MainWindow` (not yet wired in, per
  Package_020's own roadmap), same pre-existing missing-geometry
  warnings as every prior package, no new tracebacks.
- `git status` confirms exactly the planned scope: one new package
  directory, `Package_021.md` added, plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Post-Package_020.5 Audit Amendment (2026-07-16)

Documentation-only addendum. Package_021 predates Package_020.5, so at
the time this package was originally built and verified there was no
way to confirm its behavior against Package_020.5's later changes
(the four-tier LDraw discovery order, and `Renderer`/`PartCatalog`
now sharing that resolution instead of resolving independently). A
follow-up audit re-issued this package's spec with three additional,
more explicit verification requirements; no code changes were made or
needed — `git diff 779af9b0 HEAD -- src/brickforge/optimization/` is
empty.

- **Explicit occupied-volume equality**: the original verification
  confirmed the 3 seed-catalog merge cases matched by checking
  `stud_width`/`stud_length`/`height_units` dimension equality. The
  audit added a direct numeric check (`stud_width * stud_length *
  height_units`) confirming the combined volume of two source bricks
  exactly equals the target's own volume in all 3 cases (`2× 3005 =
  48.0 = 1× 3004`; `2× 3004 = 96.0 = 1× 3010`; `2× 3003 = 192.0 = 1×
  3001`) — exact, not approximate.
- **Deterministic traversal-order verification**: the original
  verification confirmed determinism as "identical input run twice →
  identical output." The audit added a stronger check: the same four
  bricks inserted into a `Scene` in forward, reversed, and shuffled
  order all produce the identical merge result, confirming the
  optimizer's output depends only on brick values/positions, never on
  `Scene` insertion order.
- **Package_020.5 compatibility**: confirmed `render/renderer.py`'s
  `render()` draw loop is byte-identical since Package_021's commit —
  Package_020.5 only touched `initialize()`'s path resolution, an
  unrelated packaging concern. Also re-confirmed (originally verified
  live during Package_020.5's own end-to-end test) that
  `optimize_scene()` still runs correctly against the real,
  Package_020.5-discovered catalog, correctly finding zero merge
  opportunities there since that catalog's placeholder metadata gives
  every part identical `stud_length` — a safe, expected degradation
  already documented above, not a regression.

---

# Recommendations for Future Packages

- **Wiring into the UI**: `MainWindow` calling `optimize_scene()`
  after `mode.generate(...)` and before `renderer.set_scene(...)` is a
  separate future package, mirroring how Package_017 wired the
  Generation Mode registry into the UI after Package_016 built it
  unwired. Not done here, per Package_020's own stated roadmap.
- **Hidden Brick Removal**: still the recommended second optimizer,
  once the framework (now proven by Brick Merge) is established.
- **X-adjacent merges**: deliberately deferred — would require the
  replacement brick to carry a 90°-around-Y rotation, adding real
  complexity beyond this package's conservative scope.
- **`OptimizationResult`**: still reserved, still unbuilt — nothing in
  this package needed it.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
