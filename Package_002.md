# StudWorks

# Package 002

## Title

Brick Library Foundation

---

# Mission

Create a clean architecture for storing and rendering LEGO bricks, establishing the
foundation that later packages (placement, multiple bricks, save/load) will build on.

This package is strictly architectural. It must not change the application's visible
behavior.

---

# Scope

Primary review target:

src/brickforge/engine/ (new)
src/brickforge/render/renderer.py

---

# Objectives

1. Design a `SceneBrick` data model.
2. Design a `BrickManager` responsible for scene bricks.
3. Introduce a `Scene` abstraction.
4. Refactor the renderer so it renders a `Scene` instead of owning brick data.
5. Preserve current visual behavior by rendering one test brick through the new
   architecture.

---

# Out of Scope

- Image recognition
- Brick placement tools
- Selection
- Undo/Redo
- Saving/loading
- BrickLink Studio export
- Part browser
- GUI redesign
- Camera improvements

---

# Definition of Done

- `SceneBrick`, `Scene`, `BrickManager` exist in `engine/`, each with a single clear
  responsibility.
- `Renderer` no longer imports `LDrawLibrary` or `Part` directly, and no longer has
  `test_part`/`test_mesh` attributes.
- App renders the same single test brick, in the same position and color, through the
  new path — visual output is unchanged.
- Missing LDraw parts library still degrades to grid-only rendering with a logged
  warning — no crash, behavior preserved.
- Camera controls, grid rendering, and shader color-per-draw-call behavior are all
  unchanged.
- `py_compile` clean on all touched/added files; live run confirms no crash on startup.
- No UI changes.

---

# Completion Notes

## Architecture Summary

Three new classes were added under `src/brickforge/engine/`, a package that already
existed as an empty stub. `Renderer` no longer owns LDraw/GPU-mesh concerns directly —
it owns a `Scene` and a `BrickManager`, and renders by iterating
`BrickManager.renderables(scene)`.

```
ViewportWidget
  -> Renderer            (owns GL state, Scene, BrickManager)
       -> Scene           (list of SceneBrick — pure data)
       -> BrickManager     (LDrawLibrary + per-part Mesh cache)
            -> LDrawLibrary (existing, unchanged)
            -> Mesh         (existing, unchanged; one instance cached per part_name)
```

## New Class Responsibilities

- **`SceneBrick`** (`engine/scene_brick.py`) — pure data: `id`, `part_name`, `position`
  (`glm.vec3`, default origin), `rotation` (`glm.quat`, default identity — confirmed via
  `glm.quat()` producing `w=1, x=y=z=0`). No GL or LDraw knowledge. Named `SceneBrick`
  rather than `Brick` specifically to avoid colliding with the existing, unrelated
  `brickforge.models.brick.Brick` (a catalog/browser entry with `part_number`, `name`,
  `category`, `color`, `studs` — untouched by this package, confirmed via `git diff`
  showing no changes to that file).
- **`Scene`** (`engine/scene.py`) — holds an ordered `list[SceneBrick]`. `add()` and
  `__iter__()` only. No GL, no LDraw, no rendering knowledge.
- **`BrickManager`** (`engine/brick_manager.py`) — the only new class that touches both
  LDraw and GPU resources. Owns one `LDrawLibrary` instance. `renderables(scene)` yields
  `(SceneBrick, Mesh)` pairs, building and caching one `Mesh` per unique `part_name` so
  multiple bricks sharing a part will share one GPU mesh (not exercised by the single
  test brick in this package, but costs nothing extra to have in place now).
- **`Renderer`** (modified) — `__init__` now creates `self.scene = Scene()` and
  `self.brick_manager = None`; `initialize()` constructs `BrickManager(library_path)`
  and seeds one `SceneBrick(id=1, part_name="3001.dat")` into the scene; `render()`
  replaces the old hardcoded single-mesh draw with a loop over
  `self.brick_manager.renderables(self.scene)`.

## Implementation Notes

- **Missing-parts graceful degradation moved, not removed.** The `try/except OSError`
  that Package_001 added around LDraw loading now lives inside `BrickManager`
  (`__init__` for a missing library path, `_mesh_for()` for a missing individual part),
  rather than in `Renderer.initialize()`. Both paths log a `logging.warning` and return
  `None` instead of raising, so `Renderer` no longer needs — or has — any LDraw-aware
  error handling at all, matching "Renderer no longer owns LDraw parts directly."
  Confirmed behaviorally identical by live run: same grid-only fallback, no crash.
  (The warning's exact log text changed — e.g. now "LDraw part could not be loaded,
  skipping" instead of "...continuing with grid only" — this is an internal log
  message only, not part of the DoD's visual-output requirement.)
- **Failed/geometry-less part lookups are cached as `None`.** `BrickManager.renderables()`
  runs every frame (~60/sec). Without caching the failure, a missing part would retry
  the disk read and re-log a warning on every frame. `_mesh_for()` caches `None` in
  `_mesh_cache` on first failure so subsequent frames short-circuit with no I/O and no
  repeated logging.
- **No per-brick transform is applied yet.** `u_model` remains a hardcoded
  `glm.mat4(1.0)` in `render()`, identical to Package_001. `SceneBrick.position` and
  `.rotation` exist as pure data only, per the explicit instruction that "no additional
  rendering behavior is required in this package." Since the one seeded brick defaults
  to the identity position and rotation, this produces pixel-identical output to before.
- **Unanticipated circular import, found and fixed during verification.** `BrickManager`
  imports `brickforge.render.mesh.Mesh`. `src/brickforge/render/__init__.py` was
  eagerly importing `Renderer` at package-import time (`from .renderer import
  Renderer`), so importing `render.mesh` from inside `engine` transitively re-entered
  `renderer.py`, which now imports `engine` — a cycle. Fixed by removing the `Renderer`
  re-export from `render/__init__.py` (`Camera`, `Grid`, `Shader`, `VertexArray`,
  `VertexBuffer` re-exports were left in place). Verified safe: grepped the codebase and
  confirmed nothing imports `Renderer` via the `brickforge.render` package root —
  every consumer (e.g. `viewport_widget.py`) already imports
  `from brickforge.render.renderer import Renderer` directly.

## Verification Performed

- `py_compile` clean on all new files (`engine/__init__.py`, `engine/scene_brick.py`,
  `engine/scene.py`, `engine/brick_manager.py`) and all modified files
  (`render/__init__.py`, `render/renderer.py`).
- Interactive import check confirmed no circular-import failure and correct
  `SceneBrick`/`Scene` construction (`glm.vec3(0,0,0)` position,
  `glm.quat(1,0,0,0)` identity rotation).
- Live run of `src/main.py`: identical startup behavior to Package_001 — grid renders,
  missing LDraw parts library logs a warning and is skipped gracefully, no crash, no
  traceback, app stays alive.
- `git diff` confirms `src/brickforge/models/brick.py` (the existing catalog `Brick`
  class) has zero changes.
- Camera (`camera.py`), shader (`shader.py`), and grid fragment shader
  (`shaders/grid.frag`) were not touched in this package — confirmed via `git status`.

## Recommendations for Future Packages

- **Wire `SceneBrick.position`/`.rotation` into the per-brick `u_model` matrix** once a
  package is scoped to actually place more than one brick — straightforward given the
  data already exists (`glm.translate(glm.mat4(1.0), brick.position) *
  glm.mat4_cast(brick.rotation)`), but explicitly deferred here per "no additional
  rendering behavior."
- **Reconcile the two `Brick` concepts eventually.** `models.brick.Brick` (catalog
  entry) and `engine.scene_brick.SceneBrick` (placed instance) will likely need to
  relate to each other once the part browser can place bricks into the scene — e.g. a
  `SceneBrick` constructed from a selected catalog `Brick`'s `part_number`. Not needed
  yet; flagging so the eventual design accounts for both.
- LDraw library consolidation and subfile-reference resolution recommendations from
  Package_001 remain outstanding and unaffected by this package.
