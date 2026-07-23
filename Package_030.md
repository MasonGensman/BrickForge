# StudWorks

# Package 030

## Title

Rotate Tool — StudWorks' Second Editing Tool

---

# Mission

Implement rotation of a single selected brick, reusing Selection, the
Transform package, the scene activation helper, and the generic renderer
preview system established by Packages 027–029 — validating that the
editing architecture is reusable, not just adding a feature.

---

# Scope

New:

- `tools/rotate_tool.py` (`RotateTool`)

Modified:

- `ui/widgets/viewport_widget.py` — Right-button drag-vs-orbit
  disambiguation, `brick_rotated` signal
- `ui/main_window.py` — `on_brick_rotated` handler

Tests:

- `tests/test_rotate_tool.py`

Untouched: `generation/*`, `optimization/*`, `preparation/*`, `export/*`,
`serialization/*`, `project/*`, `services/*`, `models/*`, `ldraw/*`,
`selection/*`, `transform/*`, `render/renderer.py`, `render/picking.py`,
`tools/move_tool.py`, `ui/toolbar.py`. **This is the headline result**:
rotation required zero changes to any of the shared infrastructure Packages
028–029 built.

---

# Inspection Findings

**`MoveTool`**'s shape: `begin(brick, grab_point: glm.vec3)` /
`update(grab_point) -> glm.vec3` / `finish(grab_point) -> tuple[int, glm.vec3] | None`
/ `cancel()`. Every `update()`/`finish()` computes the **absolute** result
fresh from an immutable anchor captured at `begin()` — never chains
frame-to-frame. Input throughout is a world-space `glm.vec3` from
`Renderer.project_to_ground()` (a ray/plane intersection that can
degenerate to `None`).

**`ViewportWidget`**: Left-button fully claimed by Move (press-on-selected
→ drag; else → select/clear). Right-button unconditionally armed camera
orbit with no brick-picking check at all — free to extend the same way.
`renderer.selected_id` already directly readable — no new coupling needed.

**`SceneBrick.rotation`**: a `glm.quat`, float32-backed. Every rotation
produced anywhere in this codebase to date is Y-axis-only.

**`replace_brick`**: confirmed completely field-agnostic — never inspects
which field of the replacement brick differs from the original.

**Empirically verified before finalizing the design**:
- `glm.angleAxis(90°, Y) * identity` applied to `(1,0,0)` → `(0,0,-1)` —
  confirms the chosen pre-multiplication convention behaves as a standard
  right-handed world-axis rotation.
- **200 repeated `delta * current` quaternion multiplications *without*
  renormalizing drift to length `1.0000031`** — small but real and
  growing. The same 200 iterations *with* an explicit `glm.normalize()`
  at each step stay at exactly `1.0`. This concretely justified including
  `glm.normalize()` in `RotateTool.update()` rather than treating it as
  decoration.
- No `contextMenuEvent`/context-menu policy anywhere in `ui/` — repurposing
  Right-button-on-selected-brick had no conflict to check for.

---

# Architecture Assessment

Packages 028–029's infrastructure needed **zero changes**:
- `ScenePreview(brick_id, position, rotation)` already carried both
  fields — Move already left `rotation` untouched while varying
  `position`; Rotate is the exact mirror. This is precisely what
  Package_029's refinement (a generic preview, not a move-specific one)
  was designed to prove out, and it held.
- `replace_brick`/`set_current_scene` are already 100% field-agnostic.
- `set_current_scene`'s "clear selection only if the id is gone" rule
  already covered Rotate for free — no new logic needed for selection to
  survive a rotate.

**No changes were made to `render/renderer.py`, `render/picking.py`,
`transform/scene_transform.py`, or `ui/main_window.set_current_scene()`
in this package.** That absence is the actual validation result the
mission asked for.

---

# Reuse Assessment: no shared base class between `MoveTool` and `RotateTool`

The two tools' *input shapes are fundamentally different*: `MoveTool`
consumes a world-space `glm.vec3` from a ray/plane intersection (which can
degenerate to `None`); `RotateTool` consumes a raw screen-space `float`
with no raycasting and no degenerate case at all — confirmed directly: no
`mouseReleaseEvent` branch for rotate ever needs a `project_to_ground`-style
`None`-guard. Forcing a shared generic base for two concrete tools with
genuinely different data shapes — to share a `begin/update/finish/cancel`
*name pattern* and a ~3-line `_reset()`/epsilon-check idiom — would be the
speculative abstraction the mission warns against. The parts that *are*
genuinely, concretely shared (the preview mechanism, the commit mechanism)
are already shared, with zero new code required by this package. If a
third tool later reveals an actual stable shape worth extracting, that's
real evidence to act on then.

---

# Rotation Model

Horizontal drag maps directly to yaw around the fixed world-space Y axis,
triggered by Right-button-drag on the *already-selected* brick — extends
`MoveTool`'s own "already-selected brick overrides this button's default
behavior" convention onto Right-button instead of Left. `angle_degrees =
(current_x - start_x) * 0.35`, reusing `Camera.orbit`'s exact existing
sensitivity constant so the gesture feels like the same rotational speed
as orbiting the camera. `update()` always computes
`glm.normalize(glm.angleAxis(radians(angle_degrees), Y) * original_rotation)`
— one multiplication from the immutable `original_rotation` captured at
`begin()`, never chained. "No arbitrary pivot editing" is satisfied by
construction: always the brick's own origin, always world Y.

---

# `RotateTool`

```python
class RotateTool:
    @property
    def is_dragging(self) -> bool: ...
    @property
    def brick_id(self) -> int | None: ...

    def begin(self, brick: SceneBrick, screen_x: float) -> None: ...
    def update(self, screen_x: float) -> glm.quat: ...
    def finish(self, screen_x: float) -> tuple[int, glm.quat] | None: ...
    def cancel(self) -> None: ...
```

`finish()` compares the scalar `angle_degrees` (already directly available
from the same arithmetic `update()` uses) against a `0.01°` epsilon —
simpler than Move's world-distance comparison, since Rotate computes that
scalar itself rather than deriving it from an external raycast result.

---

# Event Flow

```
mousePressEvent (Qt.RightButton):
    brick_id = renderer.pick(x, y)
    if brick_id is not None and brick_id == renderer.selected_id:
        brick = renderer.scene.get(brick_id)
        rotate_tool.begin(brick, x)
        return                              # no camera orbit armed
    last_mouse_position = event.position()  # existing camera-orbit arming, unchanged

mouseMoveEvent:
    if move_tool.is_dragging: ... (unchanged, Move still checked first)
    if rotate_tool.is_dragging:
        brick = renderer.scene.get(rotate_tool.brick_id)
        renderer.set_preview(ScenePreview(
            rotate_tool.brick_id, brick.position, rotate_tool.update(x)
        ))
        return
    ... existing camera orbit/pan, unchanged ...

mouseReleaseEvent:
    if move_tool.is_dragging: ... (unchanged)
    if rotate_tool.is_dragging:
        result = rotate_tool.finish(x)      # no None-input case -- pure arithmetic
        renderer.set_preview(None)
        if result is not None:
            brick_rotated.emit(*result)
        return
    if event.button() in (Qt.RightButton, Qt.MiddleButton):
        last_mouse_position = None
```

```
MainWindow.on_brick_rotated(brick_id, new_rotation):
    scene = viewport.renderer.scene
    updated = dataclasses.replace(scene.get(brick_id), rotation=new_rotation)
    try:
        new_scene = replace_brick(scene, updated)
    except TransformError as error:
        status.showMessage(f"Rotate failed: {error}")
        return
    set_current_scene(new_scene)            # selection survives, id unchanged
    project_manager.current_project.mark_dirty()
    status.showMessage(f"Rotated brick #{brick_id}.")
```

Identical shape to `on_brick_moved`, differing only in which
`dataclasses.replace` field is set — confirms no duplicate Scene-rebuilding
logic exists anywhere.

---

# Validation

- **No selection**: `brick_id == renderer.selected_id` can never be true
  with nothing selected — rotate can never begin; Right-drag behaves
  exactly as before this package.
- **Cancelled rotation**: `RotateTool.cancel()` exists for API symmetry
  with `MoveTool` and as a future extension point, but — genuine finding,
  documented rather than glossed over — **there is no reachable path to it
  in this package's scope**, since Rotate's screen-x arithmetic never
  fails (unlike Move's raycasting).
- **Zero-angle rotation**: `finish()` returns `None` below `0.01°` — no
  signal, no Transform call, no Scene replacement. Verified via
  object-identity check.
- **Invalid rotation**: no reachable case beyond "id not found," already
  handled generically by `replace_brick`'s `TransformError`.
- **Numerical precision**: addressed by construction (always-fresh-from-
  immutable-original + explicit `normalize()`) and directly tested — 200
  repeated separate rotate-and-commit cycles hold the quaternion at exactly
  unit length.

---

# Error Handling

Same shape as Move: `on_brick_rotated` either fully commits via
`set_current_scene` or catches `TransformError` and leaves everything
untouched — never a partial update.

---

# Definition of Done

- A selected brick can be rotated by Right-button drag.
- Rotation reuses Selection, Transform, `set_current_scene`, and
  `ScenePreview` — confirmed via `git status` that none of those files
  were touched.
- A new immutable Scene is produced; brick id unchanged.
- Selection survives the rotate.
- No duplicate editing infrastructure was introduced (no shared tool base
  class; the only genuinely shared parts — preview, commit — already
  existed).

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- AST inspection: `tools/rotate_tool.py` imports only
  `brickforge.engine.scene_brick` and `glm` — same isolation level as
  `MoveTool`.
- **14 pure unit tests** (`test_rotate_tool.py`): drag lifecycle;
  angle-math correctness verified by rotating a known point and checking
  it lands where trigonometry predicts (not just "some quaternion
  changed"), including dragging left vs. right and rotating a
  brick that's already rotated (confirms the delta composes with the
  existing rotation rather than resetting it); zero-angle detection;
  determinism; **200-iteration repeated-commit stability test** — the
  quaternion stays at exactly unit length across 200 separate rotate
  gestures.
- **Real end-to-end UI test**, driving the actual `mousePressEvent`/
  `mouseMoveEvent`/`mouseReleaseEvent` → signal → `MainWindow` chain:
  confirmed right-drag on empty space still orbits the camera (regression
  check, run *before* any selection exists); confirmed right-press on the
  already-selected brick begins a rotate drag, not camera orbit; confirmed
  the live preview holds `position` constant while `rotation` updates;
  confirmed the Scene is *completely* untouched (object identity and field
  values) throughout an in-progress rotate drag; confirmed the committed
  rotation is geometrically correct, id preserved, every other brick
  untouched by value, selection survives, project stays synced and marked
  dirty; confirmed a zero-angle press-release produces no Scene replacement
  at all; confirmed **MoveTool still functions correctly** after
  RotateTool was wired in (direct regression check on the two tools
  coexisting).
- **Full disk round-trip on a rotated Scene**, through the real Save/New/
  Open UI path — every field of every brick matched after Save → New
  Project → Open.
- Full regression suite re-run: **101 tests** across all eight suites —
  all pass.
- `git status` confirms exactly the planned scope, and — the key
  architectural result — that `render/renderer.py`, `render/picking.py`,
  `transform/scene_transform.py`, and `tools/move_tool.py` were **not
  touched at all**.

---

# Relationship to MoveTool / Future Tools

- **MoveTool**: unmodified, unaffected, still fully functional (directly
  regression-tested above). The two tools coexist by checking
  `move_tool.is_dragging` before `rotate_tool.is_dragging` in every
  handler, an explicit, minor priority decision (same precedent set in
  Package_029) in case both were somehow triggered simultaneously.
- **Delete**: still needs no drag lifecycle at all — unaffected by this
  package's additions.
- **Duplicate/Paint/Measure/other future tools**: each gets its own small,
  independent tool class following the same `begin/update/finish/cancel`
  naming convention where a drag lifecycle applies, reusing `ScenePreview`
  and the `MainWindow` commit pattern — no shared base class yet, and none
  needed until a third tool's actual implementation reveals real shared
  structure beyond names.

---

# Recommendations for Future Packages

- Right-button-drag-to-rotate has no visual affordance (no cursor change)
  telling the user it's available — same limitation already noted for
  Move in Package_029, worth addressing together once a real modeling UI
  is in scope.
- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
