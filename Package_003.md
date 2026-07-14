# StudWorks

# Package 003

## Title

Multi-Brick Scene Support

---

# Mission

Introduce true multi-brick scene support while preserving identical visual
behavior.

---

# Scope

Primary review target:

src/brickforge/engine/scene.py
src/brickforge/render/renderer.py

---

# Objectives

1. Replace the single hardcoded `SceneBrick` with a `Scene` capable of holding
   multiple bricks.
2. Add APIs for: `add_brick()`, `remove_brick()`, `clear()`, `iterate()`.
3. Keep `BrickManager` responsible for mesh lookup and caching.
4. Keep `Renderer` responsible only for rendering.
5. Continue rendering the existing single test brick by default.
6. Do not change any UI.
7. Do not change camera behavior.
8. Do not change shaders.
9. Do not change grid rendering.
10. Do not implement selection, transforms, colors, undo, or project saving yet.

---

# Definition of Done

- `Scene` exposes `add_brick()`, `remove_brick()`, `clear()`, `iterate()`, in
  addition to the existing `__iter__()`.
- `Renderer` seeds the same single `"3001.dat"` test brick via `add_brick()`.
- `BrickManager` and `Renderer.render()` require no changes — verified they
  were already multi-brick-correct.
- Package_001 and Package_002 behavior preserved: identical visual output,
  identical camera behavior, identical grid rendering, identical shader
  behavior, identical startup behavior, identical graceful handling of a
  missing LDraw parts library.
- Mesh sharing for identical part files preserved.
- `Scene` and `SceneBrick` remain independent of OpenGL.
- `BrickManager` remains the only class that understands LDraw meshes.
- `py_compile` clean on all touched files; live run confirms no crash.

---

# Completion Notes

## Architecture Inspection (performed before implementation)

`BrickManager.renderables(scene)` already iterated `for brick in scene` and
cached one `Mesh` per unique `part_name` — it made no assumption of exactly
one brick. `Renderer.render()` already looped
`for brick, mesh in self.brick_manager.renderables(self.scene)`. Both were
multi-brick-correct as built in Package_002. The only real gap was `Scene`'s
public API: it only had `add()` and `__iter__()`, with no `remove`, `clear`,
or explicitly-named `iterate()`.

This meant Package_003 required changes to exactly two files.

## Changes

- **`engine/scene.py`**:
  - Renamed `add(brick)` → `add_brick(brick)`.
  - Added `remove_brick(brick_id)` — filters the brick list by id. **Silent
    no-op if the id does not exist** (approved decision — no exception, no
    return value indicating whether anything was removed).
  - Added `clear()` — empties the brick list.
  - Added `iterate()` — returns `iter(self.bricks)`.
  - Kept `__iter__()` unchanged, delegating to the same list, so
    `for brick in scene` (used by `BrickManager.renderables`) continues to
    work exactly as before. `iterate()` is additive, not a replacement.
- **`render/renderer.py`**: one-line call-site update,
  `self.scene.add(...)` → `self.scene.add_brick(...)`. Still seeds exactly
  one `SceneBrick(id=1, part_name="3001.dat")` — the "continue rendering the
  existing single test brick by default" requirement.
- **`engine/brick_manager.py`**: no changes.
- **`render/renderer.py` render loop**: no changes beyond the call-site
  rename above.

## Decisions Applied (per approval)

- `remove_brick(id)` on a missing id is a silent no-op.
- The `BrickManager` mesh cache stays monotonic — no eviction was added.
  Removing/clearing bricks from a `Scene` does not touch `BrickManager`'s
  cache; a cached `Mesh` for a part no `SceneBrick` currently references may
  remain in memory. Explicitly deferred, not an oversight.
- `SceneBrick.id` remains caller-supplied. No automatic id generation was
  added — nothing in this package creates more than one brick, so this
  wasn't exercised, but `remove_brick(id)` only behaves correctly if callers
  avoid id collisions themselves.

## Verification Performed

- `py_compile` clean on `engine/scene.py` and `render/renderer.py`.
- Direct `Scene` API exercise: empty scene, `add_brick` of 3 bricks (two
  sharing a `part_name`), `iterate()`/`__iter__()` returning matching id
  order, `remove_brick` of an existing id, `remove_brick` of a **missing**
  id (confirmed silent no-op, list unchanged), `clear()` emptying the list.
- Direct `BrickManager` exercise against a `Scene` with two bricks sharing
  `part_name="3001.dat"`: confirmed only **one** cache entry and only **one**
  load attempt/warning logged for both bricks — mesh sharing preserved.
- Live run of `src/main.py`: identical to Package_001/002 — grid renders,
  missing LDraw parts library logs a warning and is skipped gracefully, no
  crash, no traceback, app stays alive.
- `git diff` confirms only `engine/scene.py` and `render/renderer.py`
  changed — no camera, shader, grid, or UI files touched.

## Recommendations for Future Packages

- **Mesh cache eviction/reference counting** in `BrickManager`, once scenes
  are actually mutated at runtime (e.g. by a placement or deletion tool) and
  memory growth from an ever-growing cache becomes a real concern.
- **Automatic `SceneBrick` id generation**, once something (UI or otherwise)
  actually creates more than one brick and needs to guarantee non-colliding
  ids.
- Package_001 (LDraw library consolidation, subfile-reference resolution) and
  Package_002 (`SceneBrick`/catalog `Brick` reconciliation) recommendations
  remain outstanding and unaffected by this package.
