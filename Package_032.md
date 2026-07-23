# StudWorks

# Package 032

## Title

Delete Tool — StudWorks' Third Editing Tool, First Removal Operation

---

# Mission

Delete a selected brick by producing a new immutable Scene, reusing the
existing editing architecture. Validates that architecture supports
operations that *remove* Scene elements, not just modify them.

---

# Scope

New: nothing at the package level — extends existing files only.

Modified:

- `transform/scene_transform.py` — `remove_brick(scene, brick_id)`
- `tools/active_tool_manager.py` — `ToolResult` gains optional
  `field`/`value` (representing "no field, this brick was removed") and an
  `is_removal` property; new `try_delete(button, renderer, brick_id)`
- `ui/widgets/viewport_widget.py` — `mousePressEvent` tries delete before
  drag-begin
- `ui/main_window.py` — `on_brick_transformed` branches on
  `result.is_removal`

Tests:

- `tests/test_scene_transform.py` — `RemoveBrickTests`
- `tests/test_active_tool_manager.py` — `TryDeleteTests`

**Untouched — confirmed via `git diff --stat` and AST**: `tools/move_tool.py`,
`tools/rotate_tool.py`, `render/renderer.py`, `render/picking.py`,
`selection/*`, `project/*`, `serialization/*`. `render/renderer.py` still
has zero import of `brickforge.tools`.

---

# Inspection Findings

**`ActiveToolManager`'s existing `try_begin`/`update`/`finish` lifecycle
assumes a continuous parameter** (a live position/angle to preview and
later commit) — Delete has none, so it isn't routed through that
lifecycle at all, rather than forcing it in artificially.

**A real, pre-flagged naming collision**: `Scene.remove_brick(brick_id)`
already exists (Package_021, used internally by the Brick Merge / Hidden
Brick Removal optimizers) and **mutates in place**. Package_030.md's own
"Relationship to Future Tools" section explicitly deferred this decision
("a future Delete tool decides whether to keep using it directly or wrap
it in an immutable equivalent... Not decided here") — this package makes
that call: the new `transform.remove_brick(scene, brick_id)` is a
free function that never calls the mutating method at all (builds a
fresh `Scene()` and filters during iteration, exactly matching
`replace_brick`'s own pattern), disambiguated from the existing method at
every call site by calling convention (`scene.remove_brick(id)` vs.
`remove_brick(scene, id)`) rather than by a name change to either.
`Scene.remove_brick()` itself is untouched — renaming pre-existing,
working, tested optimization-internal code would be unrelated scope
creep with real regression risk.

**`MainWindow.set_current_scene`'s existing rule already produces correct
delete-selection behavior with zero new code**: it clears selection only
if the previously-selected id is absent from the new Scene. A deleted
brick's id is, by definition, absent from `remove_brick`'s output — the
exact same code that *preserves* selection for Move/Rotate (because their
ids persist) *clears* it for Delete (because the id doesn't), driven
entirely by what the Transform operation did, not by any Delete-specific
logic.

**Preview architecture** — re-examined, not assumed: `ScenePreview`
describes *how* to draw a brick differently, with no concept of *whether*
to draw it. See §Preview below for why this isn't extended.

---

# Architecture Assessment

The `ActiveToolManager` / `ToolResult` / `set_current_scene` architecture
built across Packages 028–031 required only two genuinely new additions
to support removal: a Transform-level operation that changes brick
*count* (irreducible — `replace_brick` cannot express this) and a small,
principled extension to the existing result/dispatch layer. No new
renderer capability, no new tool class with a drag lifecycle, no changes
to `MoveTool`/`RotateTool`, no new selection-handling code.

---

# Delete Model

**Middle-button press (not drag) on the already-selected brick, evaluated
immediately.** Extends the same "already-selected brick overrides this
button's default gesture" convention Move (Left) and Rotate (Right)
established, onto the one remaining button (previously only camera-pan).
No confirmation, no drag, no preview:

- Explicitly *not* "click confirmation" — confirmation dialogs are out of
  scope, and the mission's own exclusions (no confirmation, no undo) mean
  there's currently no safety net available even if one were wanted. This
  is a real, acknowledged UX gap this package doesn't address, stated
  plainly rather than glossed over.
- Explicitly *not* routed through a press-then-release drag lifecycle —
  `try_delete` needs no screen coordinates at all, only `button`,
  `renderer`, and the already-picked `brick_id`. Evaluating on press alone
  is simplest and avoids inventing new press-vs-drag disambiguation logic
  for a gesture that has no continuous parameter to disambiguate.

---

# Transform

```python
def remove_brick(scene: Scene, brick_id: int) -> Scene:
    if scene.get(brick_id) is None:
        raise TransformError(f"No brick with id {brick_id} in this Scene.")
    new_scene = Scene()
    for brick in scene:
        if brick.id != brick_id:
            new_scene.add_brick(brick)
    return new_scene
```

Same file as `replace_brick` (a peer operation, not a separate module —
same exception type, same immutability convention). One deliberate
contract difference, tested explicitly: `replace_brick`'s output id set
always equals its input's; `remove_brick`'s is always a strict subset
missing exactly the removed id. Removing the last brick in a Scene
produces an ordinary, valid empty `Scene()` — the same state New Project
already produces everywhere else in this app, not a special case.

---

# Selection

Handled entirely by `set_current_scene`'s existing, unmodified rule (see
Inspection Findings above) — zero new selection-handling code anywhere.
Verified directly: after a real delete through the UI,
`selection_manager.selected_id()` is `None` and `renderer.selected_id` is
`None`, with no Delete-specific code path involved in producing that
result.

---

# Preview: none

Re-examined rather than assumed unnecessary: a "ghost/ hide this brick"
preview would require `ScenePreview` to represent *visibility*, not just
transform — a genuinely new renderer capability, and one the mission
explicitly forbids introducing as delete-specific. More importantly,
there's no second consumer for "hide a brick" (Move/Rotate never needed
it), so generalizing `ScenePreview` for a single, non-generalizable use
would be exactly the premature abstraction this project has consistently
declined. The existing selection wireframe highlight already shows "this
is the targeted brick" — sufficient context for an action with no
continuous parameter to visualize. `Renderer`/`ScenePreview` are
completely untouched by this package.

---

# Event Flow

```
mousePressEvent (any button):
    brick_id = renderer.pick(x, y)

    delete_result = active_tool_manager.try_delete(event.button(), renderer, brick_id)
    if delete_result is not None:
        brick_transformed.emit(delete_result)
        return

    if active_tool_manager.try_begin(event.button(), renderer, brick_id, x, y):
        return

    ... existing select/camera-arm fallback, unchanged ...
```

```
MainWindow.on_brick_transformed(result):
    if result.is_removal:
        new_scene = remove_brick(scene, result.brick_id)
    else:
        updated = dataclasses.replace(scene.get(result.brick_id), **{result.field: result.value})
        new_scene = replace_brick(scene, updated)
    set_current_scene(new_scene)   # selection clears automatically -- id is gone
    mark_dirty(); status text
```

No changes needed to `mouseMoveEvent`/`mouseReleaseEvent` — verified
directly: `try_delete` never sets `self._active`, so `is_dragging` stays
`False`, and the eventual Middle-button release falls through the
existing (already-a-no-op-here) `last_mouse_position = None` reset
harmlessly.

---

# Validation

- **No selection**: `try_delete` requires both a picked id and a match
  against `renderer.selected_id`; with nothing selected, delete can never
  fire.
- **Invalid brick id**: unreachable through normal UI flow; tested
  directly at the engine layer for defense-in-depth.
- **Deleting the last brick**: produces a valid, ordinary empty Scene —
  verified end-to-end (deleted down to and including the final brick in
  a 4-brick generated Scene).
- **Repeated delete requests**: self-preventing at the UI layer
  (selection clears the instant the first delete commits) *and*
  independently verified at the engine layer — calling `remove_brick`
  twice in a row with the same now-stale id correctly raises
  `TransformError` the second time.
- **A guarded edge case found and defended against during
  implementation**: `try_delete` declines while another tool's drag is
  already in progress (`self.is_dragging`), preventing a Middle-button
  press from deleting a brick out from under an active Move/Rotate.

---

# Error Handling

Same shape as Move/Rotate: `on_brick_transformed` either fully commits via
`set_current_scene` or catches `TransformError` and leaves the Scene
completely untouched — never a partial update.

---

# Definition of Done

- A selected brick can be deleted via Middle-click.
- Deletion uses the Transform package (`remove_brick`).
- A new immutable Scene is produced; original Scene verified unchanged.
- Selection updates correctly (clears) with zero new selection code.
- Renderer remains tool-agnostic — re-confirmed via AST.
- No duplicate editing infrastructure introduced — no parallel result
  type, no parallel signal/handler, no new tool class with an unneeded
  drag lifecycle.

---

# Verification Performed

- `py_compile` clean on every modified file.
- AST re-confirmation: `render/renderer.py` still has no import of
  `brickforge.tools`; `git diff --stat` confirms `tools/move_tool.py`,
  `tools/rotate_tool.py`, `render/renderer.py`, `render/picking.py`, and
  `selection/*` are **completely untouched**.
- **26 tests in `test_scene_transform.py`** (12 new for `remove_brick`,
  14 pre-existing for `replace_brick` re-confirmed passing): different
  Scene object; original unchanged; target actually removed; remaining
  bricks preserved *by reference*; id set shrinks by exactly the removed
  id (the deliberate contract difference from `replace_brick`); brick
  count decreases by one; order preserved; invalid id raises
  `TransformError` without changing the original; last-brick removal
  produces a valid empty Scene; repeated removal of the same id raises
  the second time; determinism.
- **28 tests in `test_active_tool_manager.py`** (8 new for `try_delete`):
  Middle-button-on-selected-brick returns a removal `ToolResult`; Left/
  Right buttons never delete; no brick picked, wrong brick, and no
  selection all decline; declines while another tool is already
  dragging, without disturbing that drag.
- **Real end-to-end UI test**: middle-drag on empty space with nothing
  selected still pans the camera; middle-click away from the selected
  brick (camera deliberately zoomed out first, after a prior package's
  visual debugging showed a "corner" click can still land inside a
  nearby brick's silhouette at the default close camera distance) does
  not delete anything; middle-click on the already-selected brick deletes
  it (Scene shrinks by exactly one, `is_dragging` stays `False`
  throughout — confirming no drag lifecycle was ever entered); original
  pre-delete Scene completely unchanged; selection automatically cleared;
  remaining bricks unchanged by value; project synced and marked dirty;
  deleting down to and including the last brick leaves a valid, empty
  Scene; Move and Rotate both re-verified still functioning correctly
  after Delete was wired into the same dispatch path.
- **Full disk round-trip** (Save → New → Open) on a post-delete Scene —
  the deleted brick stays gone, every remaining field matched.
- Full regression suite re-run: **141 tests** across all nine suites —
  all pass.
- `git status` confirms exactly the planned scope.

---

# Extension Toward Duplicate and Undo/Redo

- **Duplicate** is an insert, not a replace or remove — doesn't fit
  `ToolResult`'s current shape (which represents "one brick, one change"
  or "one brick, gone") any more than Delete fit it before this package.
  When actually built, it will need its own extension to the result
  layer (or its own path), informed by that real implementation — not
  guessed at here, matching how this package itself only extended
  `ToolResult` once removal was a real, concrete requirement.
- **Undo/Redo** benefits directly from every edit — including removals —
  producing a distinct new `Scene` object. A history stack of `Scene`
  references (or a stack of `(operation, inverse)` pairs) becomes
  straightforward once a tool exists to populate one; `remove_brick`'s
  natural inverse would need the *removed brick's full data* preserved
  somewhere to restore it, which Undo/Redo will need to capture at the
  point of deletion — not decided or built here.

---

# Recommendations for Future Packages

- The lack of any confirmation or undo for delete is a real, acknowledged
  UX gap — explicitly out of scope per the mission, not overlooked.
- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
