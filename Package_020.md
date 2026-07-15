# StudWorks

# Package 020

## Title

Optimization Pipeline — Architecture Design

---

# Mission

Design a shared, generation-mode-independent Optimization Pipeline
that sits between raw `Scene` output and the Renderer:

```
Image Import → Image Preparation → Generation Mode → Raw Scene
    → Optimization → Optimized Scene → Renderer → (future) Studio Export
```

This package is architecture-only, mirroring the role Architecture
Package A001 played for the Generation Mode registry. No optimizer
code was written. The actual framework and first optimizer are a
follow-up package ("Step 1," mirroring Package_016's role for
Generation Modes).

---

# Inspection Findings

- `Scene`/`SceneBrick` are plain, mutable types with no serialization
  and no immutability guarantee today (`Scene.remove_brick`/`.clear()`
  genuinely mutate in place — a real trap for an optimizer to avoid on
  its *input* Scene).
- `PartCatalog.get()` is keyed by `part_number` (e.g. `"3023"`), while
  `SceneBrick.part_name` stores the **LDraw filename** (e.g.
  `"3023.dat"`). There is currently no reverse lookup from a Scene
  brick's `part_name` back to its `BrickDefinition`. This is a real,
  concrete gap — flagged here, to be resolved by whichever
  implementation package first needs it (a linear scan over
  `catalog.all()`, or a small new `PartCatalog` helper), not decided in
  this planning pass.
- Flat Mosaic and Height Relief both currently produce single-part,
  single-fixed-part-per-generation Scenes — simplifies early optimizer
  geometry reasoning, but is a property of today's two modes, not a
  contract guarantee to assume forever.
- No BrickLink Studio export code or design exists anywhere yet
  (`bricklink/__init__.py` is empty). Optimization's only real
  obligation toward a future exporter is the same one it already has
  toward the Renderer: produce a plain `Scene`.
- Renderer/`BrickManager` are fully generic over `Scene` content and
  require zero changes to consume an optimized Scene — confirmed by
  inspection, not assumed.

---

# Approved Architecture

**Contract** (mirrors `GenerationMode`'s proven shape):

```python
class OptimizeCallable(Protocol):
    def __call__(self, scene: Scene, catalog: PartCatalog) -> Scene: ...

@dataclass(frozen=True, slots=True)
class Optimizer:
    id: str
    display_name: str
    description: str
    version: int
    optimize: OptimizeCallable
```

No `palette`/`image`/`settings` parameter — optimizers see only
`(scene, catalog)`, which is the direct enforcement mechanism for
"optimization must know nothing about images, preparation, generation
modes, UI, or renderer."

**Registry**: `optimization/registry.py` — `register_optimizer` /
`list_optimizers` / `get_optimizer`, structurally identical to
`generation/registry.py`. Same self-registration pattern via
`optimization/__init__.py`.

**Pipeline / public entry point**: a chain of independent optimizers,
composed behind one caller-facing function:

```python
def optimize_scene(scene, catalog, optimizer_ids=None) -> Scene:
    ids = optimizer_ids if optimizer_ids is not None else [o.id for o in list_optimizers()]
    for optimizer_id in ids:
        scene = get_optimizer(optimizer_id).optimize(scene, catalog)
    return scene
```

Renamed from the originally-proposed `run_pipeline` to `optimize_scene`
per your naming note — callers shouldn't need to know a pipeline exists
internally; `scene = optimize_scene(scene, catalog)` reads as a single
transformation, matching how `mode.generate(...)` and `prepare_image(...)`
already read.

**Immutability**: enforced by convention (as in Package_018's
`prepare_image()`), not by making `Scene`/`SceneBrick` frozen types.
Every optimizer builds a new `Scene`; unchanged bricks may be reused by
reference, modified bricks must be new `SceneBrick` instances. No
optimizer may call `remove_brick()`/`clear()` on its input Scene.

**Future extension point — not implemented now**: an `OptimizationResult`
wrapping `scene` alongside `statistics` (e.g. bricks removed, bricks
merged, estimated cost reduction, optimization time). The Renderer would
continue to consume `scene` only; a future UI could surface `statistics`
without re-running optimization. Reserved in this document, not built.

---

# Revised Roadmap (per your feedback)

The original recommendation proposed Hidden Brick Removal as the first
optimizer. **Revised per your review**: hidden-brick removal is
correct but low-visibility at this stage — users won't perceive it
until much more volumetric models exist, and correctly determining
"truly hidden" already requires full-enclosure neighbor reasoning,
which is more geometric complexity than a first optimizer needs to
prove the framework.

**Revised Step 1** (the next package):
1. Optimizer framework: `optimizer.py`, `registry.py`, `optimize_scene()`.
2. **Brick Merge optimizer** — conservative, using a small, explicit
   substitution table (e.g. two adjacent `1x1`s → one `1x2`, where a
   matching larger part exists in the catalog). Immediately
   user-visible: fewer bricks, larger parts replacing clusters — the
   value a user actually notices first.

**Deferred to a later package**: Hidden Brick Removal, once the
optimization framework has already been proven by the merge optimizer.

**Deferred indefinitely (no supporting data exists yet)**: cost-based
optimization, "favor common parts/colors," overhang/support reduction —
each needs a data source (pricing, usage-frequency, structural physics)
that doesn't exist anywhere in this codebase.

---

# UI Recommendation (not implemented)

Optimization should be optional and off by default when it first lands,
with the registry already supporting a future "selectable passes"
checklist UI — the same dropdown/panel pattern already proven for
Generation Modes extends naturally here. Not built in this package.

---

# Verification Plan (for the Step 1 implementation package)

- Immutability: output Scene is a new object; input Scene's bricks and
  fields are byte/value-identical before and after.
- Determinism: identical input twice → field-identical output.
- **Deterministic ordering** (added per your review): running
  Optimizer A → Optimizer B always produces the same result for the
  same input — worth verifying and documenting even before multiple
  optimizers exist, since order will matter once they do.
- Composition: chained optimizers produce valid intermediate Scenes at
  every stage.
- Renderer compatibility: an optimized Scene renders through the real
  `Renderer.render()` path with zero renderer changes (`git diff`
  empty on `render/`).
- Generation-mode independence: AST inspection confirming
  `optimization/*` imports nothing from `brickforge.generation` or
  `brickforge.ui`.
- Merge-optimizer correctness: hand-constructed Scenes with known
  mergeable clusters and known non-mergeable bricks; assert exactly the
  expected substitutions occur and nothing else changes.
- Full regression suite (Packages 003–019), live application launch.

---

# Definition of Done

- A complete optimization architecture is designed and documented here.
- Optimization is fully generation-mode independent by construction
  (the contract cannot see generation-specific data).
- `Scene` remains the universal interchange format across Generation →
  Optimization → Renderer → (future) Export.
- Future optimizers can be added without changing Generation Modes or
  each other — proven by the registry + chain design, to be validated
  concretely once a second optimizer exists (mirroring how Height
  Relief validated the Generation Mode registry in Package_019).

No code was written in this package.
