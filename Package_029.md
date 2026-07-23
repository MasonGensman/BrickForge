# StudWorks

# Package 029

## Title

Move Tool — StudWorks' First Editing Tool

---

# Mission

Implement the Move Tool: the first consumer of Package_028's immutable
Transform System. Move a selected brick by producing a new Scene. No Scene
or SceneBrick is ever modified in place.

---

# Scope

New:

- `tools/__init__.py`, `tools/move_tool.py` (`MoveTool`)

Modified:

- `render/picking.py` — `ray_intersects_horizontal_plane`
- `render/renderer.py` — `ScenePreview`, `set_preview`, `project_to_ground`,
  render-loop preview consumption
- `ui/widgets/viewport_widget.py` — drag-vs-select disambiguation,
  `brick_moved` signal
- `ui/main_window.py` — `on_brick_moved` handler

Tests:

- `tests/test_move_tool.py`
- `tests/test_picking.py` — `RayIntersectsHorizontalPlaneTests` added

Untouched: `generation/*`, `optimization/*`, `preparation/*`, `export/*`,
`serialization/*`, `project/*`, `services/*`, `models/*`, `ldraw/*`,
`selection/*`, `transform/*` (used, not modified), `ui/toolbar.py`.

---

# Architectural Refinements Applied (per your review, before implementation)

**Refinement #1 — generic renderer preview, not `set_move_preview`.**
Added `ScenePreview(brick_id, position, rotation)`, a small frozen
dataclass matching exactly what `render()`'s model-matrix construction
already needs — nothing tool-specific, nothing MoveTool-shaped. Consumed
via `Renderer.set_preview(preview | None)` / `self.preview`, mirroring
`set_selected_id`/`self.selected_id` exactly, including reusing
`set_preview(None)` to clear rather than adding a separate `clear_preview()`
(there's no `clear_selected_id()` either — a parallel method would have
been *less* consistent with existing precedent, not more). `MoveTool`
never imports or references `ScenePreview`, `Renderer`, or anything in
`render/` — confirmed via AST inspection (`move_tool.py` imports only
`brickforge.engine.scene_brick` and `glm`). `ViewportWidget`, which already
owns both `Renderer` and `MoveTool`, is the one that bridges between them.
Including `rotation` alongside `position` isn't speculative — it's not
narrowing the preview to "position-only" (which would itself have been a
Move-shaped assumption leaking into the renderer); it costs nothing today
(`MoveTool` never changes rotation, `ViewportWidget` just passes the
brick's own unchanged rotation through) and means a future Rotate tool
reuses this exact mechanism with zero Renderer changes.

**Refinement #2 — `commit()` renamed to `finish()`.** Docstring now states
plainly: ends the drag, returns the requested final position, clears
temporary state — no Scene involvement implied. The actual Scene commit
(`replace_brick` + `set_current_scene`) happens later, in
`MainWindow.on_brick_moved`, matching the mission's own boundary diagram.

---

# Inspection Findings

**`ViewportWidget`** had exactly one existing Left-button behavior (pick +
emit `brick_clicked`); Right/Middle-button drag state (`last_mouse_position`)
is fully independent, so a new Left-button drag path could be added with
zero risk of interfering with camera controls. **`Renderer.selected_id`**
is already a plain public attribute MainWindow keeps synced — reading it
directly from `ViewportWidget` to answer "is this press on the
already-selected brick" required no new coupling to `SelectionManager` at
all. **Verified empirically before finalizing the design**: at the default
camera pitch (30°), `screen_to_ray`'s vertical direction component never
comes close to zero across sampled pixels (min `|direction.y|` ≈ 0.116),
confirming the "ray parallel to ground plane" degenerate case is real but
rare — a simple `None`-return guard is sufficient, no elaborate recovery
needed. Also verified: repeating the exact same screen-space ray/plane
computation twice produces bit-identical results (zero noise) — the
zero-distance epsilon (`1e-4` LDU) is a generous safety margin, not
compensation for actual float noise in the math.

---

# Move Model

Click-and-drag on an **already-selected** brick, translation only, on the
horizontal plane at the brick's own starting height. No new mode, button,
or gizmo: pressing an unselected brick or empty space behaves exactly as
Package_027 established (select/clear); pressing the *currently selected*
brick begins a drag instead. Matches "the simplest architecture that fits
the current codebase" — one new branch in an existing handler, not a new
UI surface.

---

# Tool State — `MoveTool`

New `tools/` package (mirroring `selection/`, `project/`, `transform/` as
single-concern top-level packages), owned by `ViewportWidget` (a peer of
`self.renderer`). Not a plain attribute (like `last_mouse_position`)
because its state is multiple related values plus a self-contained
algorithm (grab-offset math), not a single point. Not folded into
`transform/`, which is deliberately stateless and UI-agnostic — `MoveTool`
is inherently a stateful interaction lifecycle. Not built on a shared
abstract `Tool` base class — only one tool exists; a future `RotateTool`
mirroring this shape is evidence to extract common structure *then*, not a
guess to bake in now.

```python
class MoveTool:
    @property
    def is_dragging(self) -> bool: ...
    @property
    def brick_id(self) -> int | None: ...
    @property
    def plane_y(self) -> float: ...

    def begin(self, brick: SceneBrick, grab_point: glm.vec3) -> None: ...
    def update(self, grab_point: glm.vec3) -> glm.vec3: ...
    def finish(self, grab_point: glm.vec3) -> tuple[int, glm.vec3] | None: ...
    def cancel(self) -> None: ...
```

Pure vector math only. Preserves the offset between the initial click point
and the brick's own origin so the brick doesn't jump to snap under the
cursor at drag start.

---

# Transform Integration

`replace_brick` is called exactly **once** in the entire feature, inside
`MainWindow.on_brick_moved` — no Scene-rebuilding logic exists anywhere
else. `MoveTool` never touches Scene; `ViewportWidget` never touches Scene;
only `MainWindow` does, through the Transform package.

---

# Preview Strategy: visual preview, single commit

Rejected continuously rebuilding Scene on every `mouseMoveEvent`: would
thrash `mark_dirty()`, create and discard many intermediate Scene objects
per drag, and complicate "never partially modify a Scene" (a cancelled
drag would need to restore a prior committed state). Instead, the real
Scene/SceneBrick data is untouched until the single commit point — verified
directly: `renderer.scene is original_scene` (same object, same values)
throughout an entire in-progress drag. `Renderer.set_preview(ScenePreview(...))`
during the drag, `Renderer.set_preview(None)` unconditionally on release —
whether the drag committed or not.

---

# Event Flow

```
mousePressEvent (Qt.LeftButton):
    brick_id = renderer.pick(x, y)
    if brick_id is not None and brick_id == renderer.selected_id:
        brick = renderer.scene.get(brick_id)
        grab_point = renderer.project_to_ground(x, y, brick.position.y)
        if grab_point is not None:
            move_tool.begin(brick, grab_point)
        return                              # selection unchanged, no signal
    else:
        brick_clicked.emit(brick_id)        # Package_027 behavior, unchanged

mouseMoveEvent:
    if move_tool.is_dragging:
        grab_point = renderer.project_to_ground(x, y, move_tool.plane_y)
        if grab_point is not None:
            brick = renderer.scene.get(move_tool.brick_id)
            renderer.set_preview(ScenePreview(
                move_tool.brick_id, move_tool.update(grab_point), brick.rotation
            ))
        return
    ... existing camera orbit/pan, unchanged ...

mouseReleaseEvent:
    if move_tool.is_dragging:
        grab_point = renderer.project_to_ground(x, y, move_tool.plane_y)
        result = move_tool.finish(grab_point) if grab_point is not None else (move_tool.cancel(), None)[1]
        renderer.set_preview(None)
        if result is not None:
            brick_moved.emit(*result)       # Signal(object, object)
        return
    ... existing camera release, unchanged ...
```

```
MainWindow.on_brick_moved(brick_id, new_position):
    scene = viewport.renderer.scene
    updated = dataclasses.replace(scene.get(brick_id), position=new_position)
    try:
        new_scene = replace_brick(scene, updated)
    except TransformError as error:
        status.showMessage(f"Move failed: {error}")
        return
    set_current_scene(new_scene)            # selection survives -- id unchanged
    project_manager.current_project.mark_dirty()
    status.showMessage(f"Moved brick #{brick_id}.")
```

A brick-move drag takes priority over camera orbit/pan if both were somehow
held simultaneously (checked first in every handler).

---

# Validation

- **No selection**: `brick_id == renderer.selected_id` can never be true
  when nothing is selected — drag can never begin; falls through to
  ordinary select/clear.
- **Cancelled move**: no dedicated cancel gesture is in scope (keyboard
  shortcuts excluded). `MoveTool.cancel()` is exercised by the one
  reachable path: `project_to_ground` returning `None` at release.
- **Invalid movement**: `project_to_ground` returning `None` at drag start
  means the drag never begins — no crash, no partial state.
- **Zero-distance move**: `MoveTool.finish()` returns `None` if the final
  position is within `1e-4` LDU of the original — no signal, no Transform
  call, no Scene replacement. Verified via object-identity check.

---

# Error Handling

`on_brick_moved` either calls `set_current_scene` with a fully-formed new
Scene, or catches `TransformError` and leaves everything untouched
(status message only) — never a partial update. `MoveTool` cannot raise
mid-drag (pure vector math over already-valid inputs).

---

# Definition of Done

- One selected brick can be moved by click-and-drag.
- Movement uses the Transform package — exactly one `replace_brick` call
  site in the whole feature.
- A new Scene is produced; brick id unchanged.
- Selection survives the move (via Package_028's existing
  `set_current_scene` validate-not-clear rule — no new logic needed there).
- Original Scene remains unchanged — verified during an in-progress drag,
  not just after.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- AST inspection: `tools/move_tool.py` imports only
  `brickforge.engine.scene_brick`; `render/renderer.py` has no import of
  `brickforge.tools` — the boundary in both directions holds exactly as
  designed.
- **31 pure unit tests** (`test_move_tool.py`, `test_picking.py`
  additions): drag lifecycle (begin/update/finish/cancel state
  transitions); grab-offset math (brick doesn't snap to the cursor);
  zero-distance detection (exact, negligible, and real movement cases);
  determinism; `ray_intersects_horizontal_plane` hit/parallel-miss/
  behind-origin/nonzero-height/origin-on-plane cases.
- **Real end-to-end UI test**, driving the actual `mousePressEvent`/
  `mouseMoveEvent`/`mouseReleaseEvent` → signal → `MainWindow` chain
  through duck-typed mouse events (same pattern as every prior package):
  a generated brick is selected via a real click, then a real press-on-
  the-already-selected-brick begins a drag; confirmed the live preview
  activates and the Scene is *completely* untouched (object identity and
  field values) throughout the in-progress drag; confirmed the committed
  move produces a new Scene with the correct new position, preserved id,
  every other brick untouched by value; confirmed selection survives and
  `project_manager.current_project` stays synced and marked dirty;
  confirmed a zero-distance press-release produces no Scene replacement at
  all (object-identity check); confirmed clicking a genuinely different
  brick still selects normally rather than triggering a drag.
- **Full disk round-trip on a moved Scene**, through the real Save/New/
  Open UI path (not just calling `replace_brick` directly) — every field
  of every brick matched after Save → New Project → Open.
- Full regression suite re-run: **87 tests** across all seven suites — all
  pass.
- `git status` confirms exactly the planned scope — plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Relationship to Future Rotate / Delete Tools

- **Rotate**: reuses `ScenePreview` as-is (it already carries `rotation`);
  a `RotateTool` with the same `begin/update/finish/cancel` shape,
  different math (drag-angle instead of drag-position), calling
  `dataclasses.replace(brick, rotation=...)` + `replace_brick` at the same
  single `MainWindow` commit point. No Renderer or Transform changes
  needed.
- **Delete**: no drag lifecycle needed at all — `Scene.remove_brick(id)`
  already exists (Package_021) but mutates in place, outside this
  package's immutability guarantees; a future Delete tool decides whether
  to keep using it directly or wrap it in an immutable equivalent matching
  `replace_brick`'s shape. Not decided here.
- **Undo**: still benefits directly from every edit producing a new Scene
  object, unaffected by this package.

---

# Recommendations for Future Packages

- The Move Tool interaction (drag-on-already-selected-brick) has no
  visual affordance telling the user it's possible (no cursor change, no
  tooltip) — acceptable for "establishes editing workflow, not a complete
  modeling UI," worth revisiting once a real modeling UI is in scope.
- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
