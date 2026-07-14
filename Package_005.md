# StudWorks

# Package 005

## Title

Rotated Bricks (Transform Completion)

---

# Mission

Wire `SceneBrick.rotation` into the per-brick `u_model` matrix, completing the
transform Package_004 started (position). Rotation data has existed on
`SceneBrick` since Package_002 but has never affected rendering until now.

---

# Scope

Modify only:

- `src/brickforge/render/renderer.py`
- `Package_005.md`

No other file may change.

---

# Requirements

1. Compose the model matrix as `translate(position) * mat4_cast(rotation)` so
   each brick rotates about its own local origin before being translated into
   world space.
2. Seed at least one initialized `SceneBrick` with a non-identity rotation
   (45° around Y), leaving the remaining seeded bricks at the default
   identity quaternion — exercising both paths.
3. Preserve all Package_001–004 behavior: identical startup, camera, grid
   rendering, graceful missing-part fallback, mesh-sharing behavior. No UI
   changes, no editing/manipulation, no scaling, no serialization changes.

---

# Definition of Done

- `render()` composes both `brick.position` and `brick.rotation` into
  `u_model`, per brick, immediately before that brick's draw call.
- Seeded brick `id=2` (`3003.dat`) carries a 45°-around-Y rotation; `id=1`
  and `id=3` keep the identity default.
- A brick with the identity quaternion produces a `u_model` numerically
  identical to Package_004's translate-only matrix.
- A brick with a non-identity rotation produces a different `u_model`, with
  its local origin still mapping exactly to its world `position`.
- `Scene`, `SceneBrick`, `BrickManager`, `Mesh`, `Shader`, `Camera`, `Grid`,
  shaders, and `ui/` are untouched.
- `py_compile` clean; live run confirms no crash, identical grid-only
  fallback.
- Mesh sharing confirmed unaffected by rotation.

---

# Completion Notes

## Architectural Reasoning

`Renderer.render()` already read `brick.position` per brick (Package_004) but
never read `brick.rotation`, even though the field has existed with a
verified identity default since Package_002. This was the smallest
unfinished thread directly flagged in Package_004's own recommendations:
completing the transform composition using data that already exists, without
introducing any new field, class, or abstraction.

The composition order — rotate about the brick's own local origin, then
translate to its world position — is the standard rigid-body model-matrix
convention (`M = T * R`, applied to a local vertex as `M * v = T * (R * v)`).
It is also the only order that keeps translation-only behavior (Package_004)
as a true special case: when `rotation` is the identity quaternion,
`mat4_cast(identity)` is the identity matrix, so `T * R` degenerates to
exactly `T` — the same expression Package_004 used. Composing in the other
order (`R * T`) would not preserve this property in general, and would rotate
a brick around the world origin rather than its own placement point, which
does not match how `SceneBrick.position` has been used since Package_004
(a per-brick placement point, not a pivot elsewhere in the scene).

## Exact Implementation

In `initialize()`, the second seeded brick (`id=2`, `part_name="3003.dat"`)
gained a `rotation` argument:

```python
rotation=glm.angleAxis(
    glm.radians(45.0),
    glm.vec3(0.0, 1.0, 0.0),
)
```

`id=1` (`3001.dat`) and `id=3` (`3004.dat`) were left unchanged — no
`rotation` argument, so they keep `SceneBrick`'s existing identity-quaternion
default.

In `render()`, the per-brick `u_model` computation changed from:

```python
glm.translate(glm.mat4(1.0), brick.position)
```

to:

```python
glm.translate(glm.mat4(1.0), brick.position) * glm.mat4_cast(brick.rotation)
```

The grid's own `u_model` (identity, set once before the grid draw) is
untouched. No shader change was required — the vertex shader already treats
`u_model` as an opaque `mat4` uniform.

## Matrix Composition Order and Why It Is Correct

`translate(position) * mat4_cast(rotation)`:

- For the identity quaternion, `mat4_cast(rotation)` is the identity matrix,
  so the product equals `translate(position)` exactly — verified
  numerically identical to Package_004's expression (see Verification).
- For a non-identity rotation, a point at the brick's local origin
  (`(0,0,0)`) is unaffected by the rotation component (rotating the zero
  vector is always the zero vector) and lands exactly at `position` after
  translation — verified numerically.
- A local `+X` point rotates 45° toward `-Z` (consistent with a right-handed
  rotation of +45° about `+Y`) and *then* shifts by `position` — verified
  numerically against the hand-computed expected offset
  `(cos 45°, 0, -sin 45°)`.

## Verification Performed

- `py_compile` clean on `renderer.py`.
- `git diff`/`git status` confirm only `renderer.py` changed — no other file
  touched.
- Live run of `src/main.py`: identical to Package_004 — grid renders, all 3
  seeded bricks (including the rotated one) individually log a missing-part
  warning and are skipped gracefully, no crash, no traceback, app stays
  alive.
- **Isolated matrix-composition check** (pure `glm` math, no GL context or
  LDraw dependency needed — `u_model` composition never touches `Mesh` or
  `LDrawLibrary`):
  - Identity-rotation `u_model` compared element-for-element against
    Package_004's `translate`-only expression for the same position:
    confirmed **exactly equal**, for both the unrotated seeded bricks
    (`id=1`, `id=3`) and a fresh identity-quaternion case — full backward
    compatibility confirmed.
  - Rotated-brick `u_model` confirmed **different** from the translate-only
    matrix.
  - Rotated-brick local origin `(0,0,0,1)` transformed by `u_model` confirmed
    to land within `1e-6` of the brick's `position` — translation preserved
    under rotation.
  - Rotated-brick local `+X` point transformed by `u_model` confirmed to
    match the hand-computed expected world point (rotate 45° about Y, then
    translate) within `1e-5` — composition order confirmed correct.
- **Mesh-sharing check**: rebuilt the Package_004-style synthetic LDraw
  fixture (throwaway directory in the scratch path, one minimal `.dat` file,
  `Mesh` swapped for a GL-free fake since `Mesh.__init__` requires a live
  OpenGL context). Two `SceneBrick`s sharing one `part_name` — one with the
  identity rotation, one with the 45°-around-Y rotation — confirmed to yield
  exactly **one** cached `Mesh` instance, shared by both `(brick, mesh)`
  pairs from `BrickManager.renderables()`. Rotation has no effect on part
  resolution or caching, as expected since `BrickManager` never reads
  `.position`/`.rotation`. Scratch fixture deleted after the test.

## Final Diff Summary

Single file changed: `src/brickforge/render/renderer.py`.

- `initialize()`: seeded brick `id=2` gained a `rotation` argument (45°
  around Y). Bricks `id=1` and `id=3` unchanged.
- `render()`: per-brick `u_model` now composes `translate(position) *
  mat4_cast(rotation)` instead of `translate(position)` alone.

No changes to `engine/scene.py`, `engine/scene_brick.py`,
`engine/brick_manager.py`, `render/mesh.py`, `render/shader.py`,
`render/camera.py`, `render/grid.py`, any shader file, or anything under
`ui/`.

## Recommendations for Future Packages

- **Scale remains entirely absent** from `SceneBrick` and `u_model` — no
  field, no composition. Explicitly out of scope again this package; would
  be the natural next transform-completion step if ever needed
  (`translate * rotate * scale`).
- **Real visual verification is still blocked** on the LDraw parts library
  being populated (Package_001/003/004 recommendation, still outstanding).
- LDraw subfile-reference resolution, LDraw library consolidation, and the
  two `Brick` concepts reconciliation (Package_001/002 recommendations)
  remain outstanding and unaffected by this package.
