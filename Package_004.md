# StudWorks

# Package 004

## Title

Multiple Rendered Bricks

---

# Mission

Render multiple `SceneBrick`s instead of only the single hardcoded test brick,
while preserving all existing rendering behavior. First feature package built
on the Package_002/003 architecture.

---

# Scope

Primary review target:

src/brickforge/render/renderer.py

---

# Requirements

1. `Renderer.initialize()` seeds several `SceneBrick`s into the `Scene` rather
   than one.
2. `BrickManager` continues sharing one `Mesh` per unique part.
3. Rendering continues iterating over `renderables(scene)`.
4. No UI changes.
5. No rotation, scaling, selection, editing, undo, or project serialization.
6. Visual behavior identical except multiple bricks are now visible.
7. Graceful handling of a missing LDraw parts library preserved.

---

# Definition of Done

- `Renderer.initialize()` seeds 3 `SceneBrick`s with distinct positions.
- `render()` computes a per-brick `u_model` from `SceneBrick.position`
  immediately before each mesh draw; the grid keeps its own identity
  `u_model`, set once, unchanged.
- `BrickManager` and `Scene` require no changes — confirmed already correct
  for this objective.
- Package_001–003 behavior preserved: identical camera, grid, shader, and
  startup behavior; identical graceful handling of a missing LDraw parts
  library.
- Mesh sharing for identical part files preserved.
- `py_compile` clean; live run confirms no crash.

---

# Completion Notes

## Architecture Inspection (performed before implementation)

`BrickManager.renderables(scene)` and `Renderer.render()`'s iteration were
already multi-brick-correct as of Package_003. The one real gap: `render()`
set `u_model` to a hardcoded identity matrix once, before the grid draw, and
never updated it per brick — every brick drew at the coordinate-space origin
regardless of its `.position` value. This was flagged as a decision point
before implementation: without consuming `SceneBrick.position`, "multiple
bricks visible" could not be made spatially true, since bricks would draw
coincident and overlapping.

**Decision (per approval):** `SceneBrick.position` is applied to a per-brick
`u_model` inside the render loop. This is treated as rendering existing scene
state (the position data has existed since Package_002), not as introducing
transform/editing functionality — no rotation, scaling, or interactive
manipulation was added.

## Changes

- **`render/renderer.py`**:
  - `initialize()`: seeds 3 `SceneBrick`s instead of 1 — `id=1
    part_name="3001.dat"` at `(0,0,0)`, `id=2 part_name="3003.dat"` at
    `(100,0,0)`, `id=3 part_name="3004.dat"` at `(200,0,0)`. Part numbers
    reused from the existing catalog (`BrickDatabase`) for consistency: 2x4
    brick, 2x2 brick, 1x2 brick. 100-unit spacing chosen to keep bricks
    clear of each other's bounding boxes once real LDraw geometry is
    available (typical brick/plate parts span tens of LDU).
  - `render()`: inside the scene-brick loop, `u_model` is now recomputed per
    brick as `glm.translate(glm.mat4(1.0), brick.position)`, set
    immediately before that brick's `set_color`/`mesh.draw()` call. The
    grid's `u_model` (identity, set once before the grid draw) is
    unchanged. `SceneBrick.rotation` is not consumed — rotation stays
    explicitly out of scope, exactly as instructed.
- **No changes** to `engine/scene.py`, `engine/scene_brick.py`,
  `engine/brick_manager.py`, `camera.py`, `shader.py`, any `.frag`/`.vert`,
  `grid.py`, or anything under `ui/`.

## Verification Performed

- `py_compile` clean on `render/renderer.py`.
- Live run of `src/main.py`: identical to Packages 001-003 — grid renders,
  all 3 seeded bricks individually log a missing-part warning and are
  skipped gracefully, no crash, no traceback, app stays alive.
- **Synthetic-library pipeline test**, since the real LDraw parts library
  remains empty in this environment (0 files, unchanged since Package_001):
  built a throwaway LDraw-like directory in the scratch directory with two
  minimal synthetic `.dat` part files (real triangle geometry, not real
  bricks). Constructed a `Scene` with 3 `SceneBrick`s — two sharing one
  `part_name`, one using a different `part_name` — and called
  `BrickManager.renderables(scene)` directly (with `Mesh` swapped for a
  GL-free fake, since `Mesh.__init__` requires a live OpenGL context that a
  standalone script doesn't have). Confirmed: 3 renderable pairs returned,
  each retaining its own distinct `position`; exactly 2 `Mesh` objects
  constructed (one per unique part); the two same-part bricks share the
  identical `Mesh` instance; the different-part brick does not. Scratch
  fixture deleted after the test.
- `git diff` confirms only `render/renderer.py` changed.

## Recommendations for Future Packages

- **Real visual verification is still blocked** on the LDraw parts library
  being populated (Package_001/003 recommendation, still outstanding).
- **`SceneBrick.rotation` remains unused by rendering.** Wiring it into
  `u_model` via `glm.mat4_cast(brick.rotation) * glm.translate(...)` is
  straightforward whenever a future package is scoped to actually rotate
  bricks — not done here per "no rotation."
- LDraw library consolidation, subfile-reference resolution, and the two
  `Brick` concepts reconciliation (Package_001/002 recommendations) remain
  outstanding and unaffected by this package.
