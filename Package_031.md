# StudWorks

# Package 031

## Title

Active Tool Framework — Centralized Editing-Tool Ownership and Dispatch

---

# Mission

Replace implicit mouse-button ownership of editing behavior with explicit
tool ownership. Architecture only — no new editing capabilities, no UI.
Validates and consolidates the pattern Packages 029–030 established with
two real tools, rather than inventing structure for tools that don't
exist yet.

---

# Scope

New:

- `tools/active_tool_manager.py` (`ToolResult`, `ActiveToolManager`)

Modified:

- `ui/widgets/viewport_widget.py` — mouse handlers rewritten around
  `ActiveToolManager`; `brick_moved`/`brick_rotated` replaced with one
  `brick_transformed` signal.
- `ui/main_window.py` — `on_brick_moved`/`on_brick_rotated` replaced with
  one `on_brick_transformed`.

Tests:

- `tests/test_active_tool_manager.py`

**Untouched — the key architectural result**: `tools/move_tool.py`,
`tools/rotate_tool.py`, `render/renderer.py`, `render/picking.py`,
`transform/scene_transform.py`, `selection/*`, `project/*`. Confirmed via
`git status` and re-run of `git diff --stat`.

---

# Inspection Findings

**The duplication targeted here is real, not hypothetical** — re-read
line-by-line before touching anything:
- `ViewportWidget.mousePressEvent`'s Left- and Right-button branches each
  independently did `pick()` → check `brick_id == renderer.selected_id` →
  `scene.get(brick_id)` → `<tool>.begin(...)`. Identical preamble, twice.
- `mouseMoveEvent`/`mouseReleaseEvent` each had a separate
  `if move_tool.is_dragging: ... elif rotate_tool.is_dragging: ...` pair,
  each branch independently building a `ScenePreview` or handling
  `finish()`/`cancel()`/preview-clearing.
- `MainWindow.on_brick_moved`/`on_brick_rotated`: identical bodies except
  which `dataclasses.replace()` keyword was set and two words of status
  text. A second, independent instance of the same pattern.

**`MoveTool`/`RotateTool`** — re-confirmed unchanged, still renderer-
ignorant (AST: `move_tool.py`/`rotate_tool.py` import only
`brickforge.engine.scene_brick` and `glm`). Their input shapes still
genuinely differ (world-space `glm.vec3` from a ray/plane intersection
that can degenerate to `None`, vs. a raw screen-space `float` with no
degenerate case) — this remains true and remains the reason no shared
base class was introduced between them, now or before.

**Preview architecture** — `ScenePreview` needed no changes; confirmed
`render/renderer.py` still has zero import of `brickforge.tools`.

**Selection / tool activation** — nothing in this codebase ever gave
`ActiveToolManager` (or its predecessor dispatch code) a reference to
`SelectionManager`; both read `renderer.selected_id` only. "Changing the
active tool" has no explicit user-facing trigger in this app (implicit in
which mouse button is pressed) — the mission's "changing tools must never
invalidate selection" requirement was already structurally satisfied
before this package, and remains so.

---

# Architecture Assessment

Two, and only two, real instances of duplication existed, both addressed
here with evidence, not speculation:
1. Viewport-side dispatch (three mouse handlers, each re-implementing the
   same pick/check/begin and drag/preview/finish shape per tool).
2. MainWindow-side commit handlers (two near-identical bodies).

No third instance of duplication was found or invented. Nothing outside
these two spots was touched.

---

# Active Tool Recommendation — `ActiveToolManager`

New `tools/active_tool_manager.py`, owned by `ViewportWidget` — continuing,
not changing, Package_029/030's ownership reasoning (raw mouse events are
viewport-local; MainWindow never needs to know *how* a drag was
interpreted, only its outcome). Named to match this codebase's established
`*Manager` convention (`SelectionManager`, `ProjectManager`,
`BrickManager`) over `ToolController`/`ToolHost`.

**A deliberate, documented exception to "tools stay renderer-ignorant"**:
`ActiveToolManager` accepts a `Renderer` reference (passed per call, never
stored) and references `Qt.MouseButton`. This is a different, legitimate
tradeoff from `MoveTool`/`RotateTool` themselves: `ActiveToolManager` is a
coordination layer, and coordinators depend on what they coordinate — the
same relationship `Renderer.pick()` already has with `BrickManager`/
`Camera`. Inventing a framework-agnostic button enum purely to avoid
importing `Qt.MouseButton`, when Qt is the only UI framework this app will
ever use, would itself have been speculative.

```python
@dataclass(frozen=True, slots=True)
class ToolResult:
    brick_id: int
    field: str
    value: object
    verb: str

class ActiveToolManager:
    @property
    def is_dragging(self) -> bool: ...
    @property
    def active_tool_name(self) -> str | None: ...

    def try_begin(self, button, renderer, brick_id, screen_x, screen_y) -> bool: ...
    def update(self, renderer, screen_x, screen_y) -> None: ...
    def finish(self, renderer, screen_x, screen_y) -> ToolResult | None: ...
    def cancel(self) -> None: ...
```

`try_begin` centralizes the pick-eligibility check once, then dispatches
on `button` to the matching tool's own `begin()` — including Move's
degenerate-ray-at-start case (declines, no drag begins), unchanged
behavior. `update`/`finish` dispatch on *which tool object is currently
active*, calling that tool's own typed methods and — for `finish` —
wrapping its `(id, value)` result into a `ToolResult` by attaching the
field name/verb `ActiveToolManager` already knows for that tool.
`ViewportWidget` picks the brick once per press and passes the id in,
rather than `try_begin` re-picking internally.

---

# Event Routing

`mouseMoveEvent`/`mouseReleaseEvent` no longer branch per-tool at all —
one `active_tool_manager.is_dragging` check each, replacing the previous
two-tool if/elif pairs:

```python
def mousePressEvent(self, event):
    brick_id = self.renderer.pick(x, y)
    if self.active_tool_manager.try_begin(event.button(), self.renderer, brick_id, x, y):
        return
    if event.button() == Qt.LeftButton:
        self.brick_clicked.emit(brick_id)
        return
    if event.button() in (Qt.RightButton, Qt.MiddleButton):
        self.last_mouse_position = event.position()

def mouseMoveEvent(self, event):
    if self.active_tool_manager.is_dragging:
        self.active_tool_manager.update(self.renderer, x, y)
        self.update()
        return
    ... existing camera orbit/pan, unchanged ...

def mouseReleaseEvent(self, event):
    if self.active_tool_manager.is_dragging:
        result = self.active_tool_manager.finish(self.renderer, x, y)
        if result is not None:
            self.brick_transformed.emit(result)
        self.update()
        return
    if event.button() in (Qt.RightButton, Qt.MiddleButton):
        self.last_mouse_position = None
```

The remaining Left/Right button checks in `mousePressEvent` reflect
genuine, irreducible input-binding differences (which button arms which
camera gesture when no tool claims the press) — not the routing
duplication this package targets.

`brick_moved`/`brick_rotated` (`Signal(object, object)` × 2) are replaced
with one `brick_transformed = Signal(object)` carrying a `ToolResult`,
matching `brick_clicked`'s existing single-rich-payload convention.
`MainWindow.on_brick_moved`/`on_brick_rotated` collapse into one:

```python
def on_brick_transformed(self, result: ToolResult):
    scene = self.viewport.renderer.scene
    updated = dataclasses.replace(scene.get(result.brick_id), **{result.field: result.value})
    try:
        new_scene = replace_brick(scene, updated)
    except TransformError as error:
        self.status.showMessage(f"{result.verb} failed: {error}")
        return
    self.set_current_scene(new_scene)
    self.project_manager.current_project.mark_dirty()
    self.status.showMessage(f"{result.verb} brick #{result.brick_id}.")
```

---

# Preview Architecture Review

Confirmed unchanged and still fully generic: `ScenePreview`'s shape needed
no modification, `render()`'s consumption of `self.preview` has no
tool-specific branching, and `Renderer` still has zero import of
`brickforge.tools`. No improvement was warranted here — this package
doesn't touch `render/` at all.

---

# Tool Input — reaffirmed, no shared base class between `MoveTool`/`RotateTool`

Unchanged conclusion from Package_030, re-examined rather than assumed:
the tools' input shapes still genuinely differ. What the evidence *does*
support — and what's new in this package — is shared infrastructure
**above** the tools (dispatch/coordination in `ActiveToolManager`) and
shared infrastructure **downstream** of them (`ToolResult`, grounded in
already-duplicated MainWindow handlers, not invented). Both are
evidence-backed; neither required touching `MoveTool`/`RotateTool`
themselves.

---

# Selection / Document State / Error Handling

- **Selection**: `ActiveToolManager` never references `SelectionManager`;
  reads only `renderer.selected_id`. Tool activation structurally cannot
  touch selection state. Verified in the e2e test: selection survives
  both a real Move and a real Rotate performed back-to-back through the
  new dispatch path.
- **Document state**: `ActiveToolManager` never calls `replace_brick` or
  `set_current_scene` — it only returns a `ToolResult`; `MainWindow`
  remains the sole caller of both, unchanged.
- **Error handling**: `finish()` always clears `renderer.preview` and the
  active tool regardless of outcome (verified directly, including the
  zero-movement/zero-angle and ray-miss cases). The only place a real
  failure (`TransformError`) can occur is inside
  `MainWindow.on_brick_transformed`, unchanged from before.

---

# Definition of Done

- `ActiveToolManager` exists as an explicit active-tool architecture.
- Event routing in `mouseMoveEvent`/`mouseReleaseEvent` is centered on
  `is_dragging`/`update`/`finish` rather than per-tool branching.
- Move and Rotate continue to function — re-verified end-to-end through
  the refactored path, not assumed from the unit tests alone.
- `Renderer` remains tool-agnostic — re-confirmed via AST.
- Preview remains generic — `ScenePreview` untouched.
- No speculative abstraction was introduced — no `Tool` protocol/base
  class, no multi-tool registry, no string-based tool lookup; only the
  two evidence-backed consolidations described above.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- AST re-confirmation: `render/renderer.py` still has no import of
  `brickforge.tools`; `tools/move_tool.py`/`tools/rotate_tool.py` still
  import nothing from `render/` — only `active_tool_manager.py` gained
  the `Renderer`/`Qt` dependency, exactly as designed.
- **20 pure unit tests** (`test_active_tool_manager.py`) against a
  duck-typed fake renderer: `try_begin` correctness per button/selection
  combination (no brick picked, wrong brick, Middle button, Move's
  ground-ray-miss case); Left begins Move, Right begins Rotate;
  `update`/`finish` dispatch correctly per active tool; `ToolResult`
  field/verb correctness for each tool; zero-movement/zero-angle →
  `None`; preview and active state always cleared on `finish`/`cancel`,
  including the failure paths.
- **`test_move_tool.py`/`test_rotate_tool.py` re-run unchanged and still
  passing** — confirms the individual tools' behavior is untouched by
  this refactor (these files were not modified).
- **Real end-to-end UI test re-running Package_029/030's own scenarios**
  through the refactored dispatch path: confirmed `ViewportWidget` no
  longer exposes `move_tool`/`rotate_tool` as separate attributes and
  `MainWindow` no longer exposes `on_brick_moved`/`on_brick_rotated`;
  right-drag on empty space still orbits the camera; Move and Rotate both
  still work correctly end-to-end (Scene updated, id preserved, selection
  survived, preview cleared, project marked dirty); zero-distance/
  zero-angle press-releases still produce no Scene replacement; clicking
  a different unselected brick still selects normally.
- **Full disk round-trip** (Save → New → Open) on a Scene modified via
  both tools through the new dispatch path — every field matched.
- Full regression suite re-run: **121 tests** across all nine suites —
  all pass.
- `git status` confirms exactly the planned scope, and specifically that
  `tools/move_tool.py`, `tools/rotate_tool.py`, `render/renderer.py`,
  `render/picking.py`, and `transform/scene_transform.py` were **not
  touched at all**.

---

# Why No Tool Base Class Exists (still true)

Re-examined, not assumed: `MoveTool`/`RotateTool`'s `begin`/`update`/
`finish` still take genuinely different-shaped arguments. A shared base
class would need either an artificial common input type (lossy) or a
Renderer dependency pushed into the tools (undoing a verified, valued
property). The parts that *are* genuinely shared — dispatch and result
shape — now have a real, evidence-backed home in `ActiveToolManager`/
`ToolResult`, without touching the tools themselves.

---

# Extension Path for Delete, Duplicate, Paint, Measure, AI-Assisted Editing

- A tool whose result is "replace one field of one brick" (a hypothetical
  future Scale tool, for instance) plugs into `ActiveToolManager` with a
  few lines in `try_begin`/`update`/`finish` and reuses `ToolResult` and
  `MainWindow.on_brick_transformed` completely unchanged.
- **Delete does not fit `ToolResult`'s shape at all** — it removes a
  brick rather than replacing a field. Documenting this honestly rather
  than pre-generalizing `ToolResult` to guess at a shape that fits an
  operation that doesn't exist yet: when Delete is actually built, it
  will need either its own result type and its own `MainWindow` handler,
  or a genuine generalization informed by that real implementation — not
  a guess made here.
- **Duplicate** is an insert, not a replace or remove — same situation as
  Delete.
- **Paint/Measure/AI-assisted editing**: too undefined today to plan for
  meaningfully; the architecture doesn't foreclose any of them, but
  nothing here was built in anticipation of their specific needs.
- If a third *drag-lifecycle* tool (one with `begin`/`update`/`finish`/
  `cancel` shaped like Move/Rotate) is eventually built and its
  concrete input type turns out to coincide with an existing tool's, or
  reveals a real shared pattern, that's the moment to reconsider a shared
  base class — not before.

---

# Recommendations for Future Packages

- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
- No visual affordance exists for either tool (no cursor change) — noted
  again, unaddressed, as in Packages 029–030.
