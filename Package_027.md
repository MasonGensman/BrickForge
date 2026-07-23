# StudWorks

# Package 027

## Title

Selection System — Single-Brick Selection, CPU Ray Picking, Wireframe Highlight

---

# Mission

Establish how bricks become selected, how selection state is stored, and how
the renderer visualizes selection. Not editing — selection is the foundation
future editing operations build on.

---

# Scope

New:

- `selection/__init__.py`, `selection/selection_manager.py`
- `render/picking.py`

Modified:

- `engine/brick_manager.py` — local-space AABB cache, computed alongside
  the existing mesh cache.
- `engine/scene.py` — `Scene.get(brick_id)`, read-only.
- `render/renderer.py` — `selected_id`, `set_selected_id()`, `pick()`,
  wireframe highlight pass.
- `ui/widgets/viewport_widget.py` — `brick_clicked` signal, left-click
  handling.
- `ui/main_window.py` — owns `SelectionManager`, wires the click signal,
  clears selection on every Scene replacement.

Tests:

- `tests/test_selection_manager.py`, `tests/test_picking.py`

Untouched (verified via `git status`/AST inspection): `generation/*`,
`optimization/*`, `preparation/*`, `export/*`, `serialization/*`,
`project/*`, `services/*`, `models/*`, `ldraw/*`.

---

# Selection Model

`SceneBrick.id` (`int`), never an object reference, renderer object, or list
index — matches `Scene.remove_brick(brick_id)`'s existing identity
convention, and survives a `Scene` being swapped wholesale via
`set_scene()` without holding a dangling reference into the old Scene.

---

# Ownership

New `selection/` package. `SelectionManager` is owned by `MainWindow` as
`self.selection_manager` — a focused manager object, mirroring
`self.project_manager`'s existing shape, not a raw field MainWindow
manipulates itself.

- **Not `Scene`** — Selection must never mutate Scene; giving Scene a
  "selected" concept would make every Scene consumer (export, serialization,
  optimization) responsible for ignoring it.
- **Not `Renderer`** — Renderer consumes `selected_id`, nothing more.
  Confirmed by AST inspection: `render/renderer.py` has zero import of
  `brickforge.selection` — Renderer has no way to know `SelectionManager`
  exists.
- **Not `Project`** — selection is session state, not document state (see
  "Why selection clears" below); bolting a non-persisted field onto the
  class whose entire job is the persisted document is a standing trap for
  `to_dict()`/`from_dict()` to remember to exclude.

`SelectionManager` itself holds nothing but `int | None` — confirmed by AST
inspection to have zero imports at all, so it structurally cannot reach for
Scene or rendering state even by accident.

---

# Public API

```python
class SelectionManager:
    def select(self, brick_id: int) -> None: ...  # TypeError for non-int, bool, None
    def clear(self) -> None: ...
    def selected_id(self) -> int | None: ...
    def has_selection(self) -> bool: ...
```

---

# Why Selection Clears Whenever the Active Scene Changes

Selection is only ever valid for the currently active Scene. Because
`SelectionManager` has no Scene reference, it cannot detect a Scene swap
itself — `MainWindow` clears it explicitly at every point the active Scene
is replaced:

- **New Project** (`on_new_project`)
- **Open Project** (`on_open_project`)
- **Generate LEGO Model** (`on_generate_lego`) — a freshly generated Scene
  restarts its own id sequence; without clearing here, a previously-selected
  id could silently resolve to a *different*, coincidentally same-numbered
  brick in the new Scene.

Any future Scene replacement must do the same — documented as the
extension point for the "selecting a deleted brick" case once a delete
feature exists (unreachable today, since delete is out of scope).

---

# Picking

CPU ray-vs-local-AABB, no ID buffers, no FBOs, no BVH:

1. `render/picking.py::screen_to_ray` unprojects a screen click (Qt
   convention: origin top-left, y down) through the inverse
   view-projection matrix into a world-space ray.
2. `Renderer.pick()` transforms that ray into each brick's local space
   (inverse of `translate(position) * mat4_cast(rotation)` — rigid, no
   scale anywhere in this codebase, so distances are preserved exactly).
3. `render/picking.py::ray_intersects_aabb` runs the slab method against
   the brick's cached local-space AABB.
4. The brick with the smallest non-negative hit distance wins; its `id` is
   returned, or `None` if nothing was hit.

**Geometry source**: `BrickManager.aabb_for(part_name)` computes the local
AABB in the *same* lazy-load pass as `_mesh_for()` (the `Part` object is
already loaded there and was previously discarded after extracting
`.vertices` for the `Mesh`) — picking always tests against the exact
geometry that gets rendered, never an independent source.

**A real bug caught by the unit tests before it ever reached the live
renderer**: the initial slab-method implementation's final branch
(`t_near if t_near >= 0 else t_far`) returned the *exit* point when the ray
origin started inside the box, instead of `0.0`. `test_ray_origin_inside_
box_hits_at_t_zero` caught this immediately. Fixed to `max(t_near, 0.0)` —
the standard, correct form.

---

# Rendering

Wireframe overlay: after each brick's normal solid draw, if
`brick.id == self.selected_id`, the same mesh is redrawn with
`glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)` in a distinct highlight color
(`(0.1, 0.95, 1.0)`, chosen to not collide with any default LDConfig color
this app uses), then polygon mode is reset to `GL_FILL`. Zero new shader,
zero new geometry — reuses the existing single flat-color unlit shader and
the same draw call already in `render()`'s loop.

Verified visually (`viewport.grabFramebuffer()` screenshots, see
Verification below): the highlight renders correctly, is applied to only
the selected brick (not others in the same Scene), and no z-fighting was
observed against the coincident solid pass at any camera distance tested —
no `glPolygonOffset` mitigation was needed in practice.

`Renderer.selected_id` and `set_selected_id()` mirror `scene`/`set_scene()`
exactly — MainWindow pushes the current selection in; Renderer never reaches
for it.

---

# Event Flow

```
Left-click in viewport
    -> ViewportWidget.mousePressEvent (Qt.LeftButton, new branch)
       -> brick_id = self.renderer.pick(x, y)
       -> emit brick_clicked(brick_id)              [Signal(object)]
    -> MainWindow.on_brick_clicked(brick_id)
       -> selection_manager.select(brick_id) / .clear()
       -> status bar text
       -> renderer.set_selected_id(selection_manager.selected_id())
       -> viewport.update()
    -> Renderer.render() reads self.selected_id, draws the highlight pass
```

Matches the existing widget-emits/MainWindow-connects-and-reacts idiom used
by `BrickLibraryWidget.brick_selected` and
`ImagePreviewWidget.generate_requested` — `ViewportWidget` never touches
`MainWindow` state directly; `Signal(object)` matches `brick_selected`'s
exact convention.

---

# Error Handling

- **Empty space**: `pick()` returns `None` -> `on_brick_clicked` calls
  `clear()`.
- **Invalid id type**: `SelectionManager.select()` raises `TypeError` for
  anything that isn't a plain `int` — `None` (use `clear()` instead) and
  `bool` (an `int` subclass in Python, the same recurring gotcha guarded
  against in `serialization/schema.py`) are explicitly rejected.
- **Loading a new Scene / generating a new Scene**: selection cleared at
  every one of the three call sites listed above.
- **Selecting a deleted brick**: unreachable today (no delete feature
  exists) — documented invariant for whichever future package adds one.

---

# Definition of Done

- One brick can be selected by clicking it in the viewport.
- Selection can be cleared (click empty space, New/Open Project, Generate).
- Renderer visually indicates the selected brick (wireframe highlight).
- Scene remains immutable — confirmed via object-identity and content
  checks before/after every selection operation.
- Selection remains independent from rendering — confirmed via AST
  inspection (Renderer never imports `brickforge.selection`).
- Loading a project clears selection.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- AST inspection: `SelectionManager` has zero imports (cannot reach Scene
  or Renderer even by accident); `render/picking.py` imports only `math`/
  `glm` (no `brickforge` dependency); `render/renderer.py` has no import of
  `brickforge.selection`.
- **23 pure unit tests** (`test_selection_manager.py`,
  `test_picking.py`): selection state transitions, rejection of `None`/
  bool/non-int ids, determinism; ray/AABB hit/miss/edge/inside-origin/
  nearest-of-two cases and screen-to-ray NDC/y-flip/normalization checks —
  no live GL context needed. **Caught the t=0 bug above before any
  live-renderer testing.**
- **Real end-to-end UI test**, mirroring Packages 024–026's pattern
  (`MainWindow`, real Qt event path via a duck-typed mouse-event stand-in
  — same "fake at the boundary, drive real handlers" approach used for
  `QFileDialog` in Package_026): a generated brick is aimed at directly
  (camera target set to its world position, which always projects to
  screen center regardless of distance/yaw/pitch — used to make the test
  independent of the generated Scene's real-world coordinate range) and
  clicked through the actual `mousePressEvent` -> signal -> `MainWindow` ->
  `SelectionManager` -> `Renderer` chain; confirmed: startup has no
  selection; a real click selects the correct id end-to-end; Scene
  object/contents unchanged by selection; clicking empty space clears
  selection; regenerating, New Project, and Open Project each clear
  selection; invalid id types raise `TypeError` without changing state;
  repeated identical clicks are deterministic.
- **Visual verification** (`QOpenGLWidget.grabFramebuffer()` screenshots):
  confirmed the wireframe highlight renders in the intended cyan color,
  applies to only the selected brick among several in the same Scene, and
  showed no z-fighting or GL errors (`glGetError()` checked after render)
  at multiple camera distances.
- Full regression suite re-run: 55 tests across
  `test_export_golden_files`, `test_scene_serialization`,
  `test_project_serialization`, `test_selection_manager`, `test_picking` —
  all pass.
- `git status` confirms exactly the planned scope — plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Future Extension Points

- **Multi-select**: `SelectionManager`'s `int | None` shape is deliberately
  minimal so it can extend to `set[int]` later without breaking today's
  `select`/`clear`/`selected_id`/`has_selection` callers.
- **Inspector editing / Properties panel integration**: explicitly out of
  scope this package (mission excluded "inspector editing"); a natural next
  step once move/rotate/delete operations exist.
- **Drag selection, rectangle/lasso, hierarchy, groups**: all explicitly
  deferred, per mission.
- **`glPolygonOffset` for the wireframe pass**: not needed in practice
  (verified visually), but noted as the mitigation if a future part shape
  or camera angle ever produces visible z-fighting.
- The renderer's upside-down LDraw geometry bug (Package_024, still
  unfixed) and `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026, still unrestructured) remain outstanding and unaffected by
  this package.
