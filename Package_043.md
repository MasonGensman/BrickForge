# StudWorks

# Package 043

## Title

Generation Pipeline Orchestrator — One Canonical Entry Point for the Backend

---

# Mission

Create a deterministic orchestration layer that executes the complete
backend pipeline (Packages 034–042) through a single public API:
`generate_model(...) -> GenerationResult`. This package introduces no
new generation, optimization, validation, repair, or analysis logic —
it only coordinates existing stages, establishing itself as the
preferred application entry point while every lower-level stage
remains fully independent and directly usable.

---

# Scope

New:

- `pipeline/__init__.py` (empty, matching every other pipeline
  package's own convention)
- `pipeline/generation_pipeline.py` (`GenerationResult`,
  `generate_model()`, private `_scene_signature()`)

Tests:

- `tests/test_generation_pipeline.py` (new, 13 tests)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `transform/`, `serialization/`, `export/`, `project/`,
`ui/`, `generation/`, `optimization/`, `validation/`, `scene_analysis/`,
`repair/`, `preparation/`, `services/`, `ldraw/`, `palette/`,
`analysis/`, `models/`. This package adds exactly one new top-level
package plus one test file — every stage it coordinates is completely
unmodified.

---

# Architecture Summary

`generate_model()` is a single pure function — no class, no registry,
matching every prior stage's own style. It performs zero domain logic
of its own: every line either calls an existing stage function or
implements the repair loop's stopping condition, which is orchestration
control-flow, not repair logic — the loop decides *whether* another
`repair_scene()` call is needed and *when* the pipeline stops, while
`repair_scene()` itself continues to decide *how* any given repair is
performed.

**`GenerationInput.from_source()` is treated as this pipeline's first
stage in its entirety** — image analysis is already fully encapsulated
inside it (Package_035's own design), so no separate "image analysis"
step exists to orchestrate on top of it, per the approved requirement.

**Repair-loop termination is based on whether the Scene itself stopped
changing, not on `ValidationReport` contents** — verified during
planning that every current repair rule is provably monotonic, so "the
Scene stopped changing" is both correct and guaranteed to terminate,
unlike "no more errors remain," which would never trigger for a
permanently-deferred issue (an out-of-window quaternion, or an
`overlapping_bricks` warning). Comparison uses a private
`_scene_signature()` helper, since `repair_scene()` always returns a
newly constructed `Scene` object even when nothing changed, making
object identity/equality unusable directly.

**A defensive `_MAX_REPAIR_ITERATIONS = 10` safety cap** exists purely
as a safety net, never expected to be reached under normal operation —
verified directly that a Scene with two simultaneous problems
(duplicate ids and an invalid part reference together) resolves in
exactly 2 cycles. If the cap were ever reached, the loop simply stops
and returns the current state without raising — a safety net must not
itself become a new failure mode.

**No exception wrapping** — `FileNotFoundError`/`ValueError` from
`GenerationInput.from_source()` and `ValueError` from `generate_scene()`
(no usable candidates) propagate completely unchanged, verified
directly. Both already identify exactly what went wrong; a new
`PipelineError` would remove information, not add it.

---

# Pipeline Summary

```
GenerationInput.from_source(image_path, settings)   # includes image analysis
  -> generate_scene(generation_input, catalog, palette, constraints)
  -> optimize_scene(scene, catalog, constraints)
  -> validate_scene(scene, catalog)
  -> [repair_scene(scene, report) -> validate_scene(scene, catalog)]*
     repeated until the Scene stops changing (or the defensive cap)
  -> analyze_scene(scene, catalog)
```

`generate_model(image_path, catalog, palette, constraints=None,
settings=None) -> GenerationResult` is the resulting public API — the
exact name and shape the mission's own "Architectural Goals" section
specifies. Every parameter besides `image_path` mirrors an underlying
stage's own signature exactly (`constraints`/`settings` both default to
`None`, matching `generate_scene()`/`GenerationInput.from_source()`
respectively).

**Deliberately not accepting an already-built `GenerationInput`** as an
alternative to a path — no concrete consumer exists yet (UI wiring is
explicitly out of scope for this package); a future integration package
can widen this if a real "avoid re-loading" need is evidenced then,
rather than building the flexibility speculatively now.

---

# GenerationResult Summary

```python
@dataclass(frozen=True, slots=True)
class GenerationResult:
    scene: Scene
    generation_input: GenerationInput
    validation_report: ValidationReport
    scene_analysis: SceneAnalysisResult
    repair_iterations: int
```

`generation_input` is included specifically because the orchestrator
builds it internally from a raw path — the caller has no other way to
obtain it, and `Project.generation_input`/`Project.generation_constraints`
(Packages 034/036) already exist to hold exactly this kind of data for a
future project-management integration. `constraints` itself is **not**
included — the caller already has it, since they passed it in; `catalog`
and `palette` are likewise caller-owned and not echoed back.
`validation_report` is the *final* report, honestly reflecting any
issues that remain after the repair loop settles — including
permanently-deferred ones. `repair_iterations` is a direct,
already-computed by-product of the loop, not a new calculation invented
for the result type.

---

# Test Summary

**13 tests, `tests/test_generation_pipeline.py`**:

- `_scene_signature()`: identical content produces equal signatures;
  different content produces different ones.
- Full pipeline execution against a real, freshly-built test image:
  correct `GenerationResult` shape, non-empty Scene, a valid final
  report and `repair_iterations == 0` for an already-clean generated
  model; determinism across repeated calls (Scene signature, report,
  analysis, and iteration count all compared directly); `constraints`/
  `settings` accepted; no mutation of `catalog`.
- `GenerationResult` immutability: raises on attempted attribute
  assignment.
- Failure propagation: a missing image path raises `FileNotFoundError`
  unchanged; constraints that eliminate every candidate raise
  `ValueError` unchanged.
- **Repair loop, exercised through `generate_model()`'s real public
  API** by substituting `optimize_scene()`'s output with a
  deliberately broken, hand-built Scene via `unittest.mock.patch` —
  this runs the orchestrator's actual code path (the while loop, the
  signature comparison, iteration counting) rather than duplicating
  that logic in a separate, unverified reimplementation: the exact
  "duplicate ids + invalid part reference" scenario resolves in
  `repair_iterations == 2` with a valid final result; a Scene with a
  zero-length quaternion (outside `repair_scene()`'s safe-normalization
  window) terminates immediately via "Scene stopped changing"
  (`repair_iterations == 0`, nowhere near the safety cap), with
  `invalid_orientation` still visible in the final report — the
  deferred-issue case the mission explicitly asked to verify; an
  already-clean injected Scene needs zero repair iterations.
- Lower-level independence: every stage function `generate_model()`
  calls (`GenerationInput.from_source`, `generate_scene`,
  `optimize_scene`, `validate_scene`, `repair_scene`, `analyze_scene`)
  remains directly, independently callable and produces a correct
  result on its own.

---

# Regression Results

Full suite: **376 tests**, all passing (363 pre-existing + 13 new).

---

# Scope Isolation Confirmation

`git status`/`git diff --stat` confirm the only change is the addition
of `src/brickforge/pipeline/` (two files) and
`tests/test_generation_pipeline.py`. Every stage this package
coordinates — `engine/`, `render/`, `selection/`, `transform/`,
`serialization/`, `export/`, `project/`, `ui/`, `generation/`,
`optimization/`, `validation/`, `scene_analysis/`, `repair/`,
`preparation/`, `services/`, `ldraw/`, `palette/`, `analysis/`,
`models/` — is completely untouched. An AST-based import check confirms
`generation_pipeline.py` depends only on the six stages' own public
modules plus `services.part_catalog`/`palette.palette_engine` and
stdlib — no coupling to `engine/` beyond the plain `Scene` type every
stage already exposes.

---

# Definition of Done

- A deterministic Generation Pipeline Orchestrator exists —
  `generate_model()`, verified identical output across repeated calls
  on identical inputs.
- Existing pipeline stages remain independent — zero modification to
  any of the six stages, confirmed via `git diff --stat`; each remains
  directly callable, verified with a dedicated test.
- Repair is integrated through deterministic iteration — a
  provably-monotonic, Scene-stability-based loop with a defensive,
  never-triggered safety cap.
- `GenerationResult` exposes the appropriate immutable outputs — only
  what the orchestrator uniquely produces, never caller-owned inputs
  echoed back.
- The orchestrator is established as the canonical application entry
  point — `generate_model()` is the one function future UI, project
  management, automation, and the Package_050 Windows executable should
  call, per the mission's own explicit framing.
