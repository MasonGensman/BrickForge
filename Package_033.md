# StudWorks

# Package 033

## Title

Duplicate Tool — StudWorks' First Editing Operation That Creates New Scene Data

---

# Mission

Duplicate a selected brick by producing a new immutable Scene, reusing the
existing editing architecture wherever possible. Validates that the
architecture also supports *creation*, not just modification (Move,
Rotate) or removal (Delete).

---

# Scope

New: nothing at the package level — extends existing files only.

Modified:

- `engine/scene.py` — `Scene.next_available_id()`
- `transform/scene_transform.py` — `duplicate_brick(scene, brick_id) ->
  (Scene, int)`
- `ui/main_window.py` — Edit menu gains a "Duplicate Selected Brick"
  action; new `on_duplicate_selected` handler

Tests:

- `tests/test_scene.py` (new) — `next_available_id()`
- `tests/test_scene_transform.py` — `DuplicateBrickTests`

**Untouched — confirmed via `git diff --stat`**: `tools/*`,
`ui/widgets/viewport_widget.py`, `render/*`, `selection/*`. Duplicate has
no mouse-gesture entry point at all, so none of the viewport/tool dispatch
machinery needed to change.

---

# Inspection Findings

**Id generation is completely decentralized, confirmed by re-reading every
assignment site**: `mosaic_generator.py` uses `row * width + col`;
`height_relief_generator.py` uses a local running counter; the Brick Merge
optimizer derives ids via `min(id_a, id_b)`; demo bricks are hardcoded.
There has never been a global counter or registry anywhere in this
codebase — every existing scheme is scene-local and restarts freely with
each new Scene. `Scene.next_available_id()` extends this existing norm,
it doesn't introduce a new kind of uniqueness guarantee.

**The Edit menu was genuinely, completely empty** — `menu.addMenu("Edit")`'s
return value wasn't even captured in a variable before this package.

**A real architectural constraint discovered during planning**: Move
(Left), Rotate (Right), and Delete (Middle) had already exhausted every
standard mouse button for the "press on the already-selected brick"
pattern established since Package_029. This directly ruled out giving
Duplicate its own viewport gesture and shaped the recommendation below.

---

# Architecture Assessment

Three of the four editing operations now built (Move, Rotate, Delete) all
flow through `ActiveToolManager`/`ToolResult`/`brick_transformed`, machinery
that exists specifically to solve "a viewport mouse gesture needs to tell
MainWindow what happened." Duplicate has no mouse gesture to translate —
forcing it through that plumbing anyway would have been artificial, not
genuine reuse. What *is* genuinely reused: `set_current_scene` (Scene
activation, unmodified), `SelectionManager` (read/written directly, no new
coupling), and `transform/scene_transform.py` as the file (a new peer
function, not a new module) — confirmed by the fact that zero lines
changed in `render/`, `tools/`, or `ui/widgets/viewport_widget.py`.

---

# Duplicate Tool Recommendation

**No dedicated tool class, no `ActiveToolManager` involvement.** A single
QAction, "Duplicate Selected Brick," added to the previously-empty Edit
menu, wired directly to `MainWindow.on_duplicate_selected()` — mirroring
exactly how `on_new_project`/`on_open_project` are already self-contained
`QAction → MainWindow method` handlers with no viewport-signal plumbing.

Rejected the mission's first candidate model ("activate Duplicate Tool →
click selected brick → duplicate"): with no mouse button left to bind,
this would require inventing a genuinely new concept — a persistent,
stateful "current mode" the user toggles into and remains in. Nothing in
this app has ever needed that; Move/Rotate/Delete are all momentary,
single-gesture triggers, never modes. Building mode-switching state for
one one-shot action would have been speculative infrastructure introduced
for its own sake.

---

# Transform API

**`Scene.next_available_id() -> int`** (new, read-only, mirrors `get()`'s
shape):

```python
def next_available_id(self) -> int:
    return max((brick.id for brick in self.bricks), default=-1) + 1
```

Scene-local, not globally monotonic — consistent with every existing id
scheme. Verified robust against non-contiguous ids left by prior
deletions, and confirmed to be a pure query (doesn't mutate the Scene,
doesn't reserve the id — calling it twice without using the result
returns the same value both times).

**`transform.duplicate_brick(scene, brick_id) -> tuple[Scene, int]`** (same
file as `replace_brick`/`remove_brick`):

```python
def duplicate_brick(scene: Scene, brick_id: int) -> tuple[Scene, int]:
    original = scene.get(brick_id)
    if original is None:
        raise TransformError(f"No brick with id {brick_id} in this Scene.")
    new_id = scene.next_available_id()
    duplicate = dataclasses.replace(
        original, id=new_id, position=original.position + _DUPLICATE_OFFSET,
    )
    new_scene = Scene()
    for brick in scene:
        new_scene.add_brick(brick)
    new_scene.add_brick(duplicate)
    return new_scene, new_id
```

`_DUPLICATE_OFFSET = glm.vec3(20.0, 0.0, 0.0)` — one stud (the same
`_STUD_LDU` every generator uses) along +X. Fixed, not derived from the
part's actual footprint: Transform functions deliberately take no
`PartCatalog` (Package_025's established precedent), and a bare
`SceneBrick` doesn't carry stud dimensions. Satisfies the mission's actual
requirement ("avoid occupying exactly the same location") without
guaranteeing zero visual overlap for parts larger than 1×1 — a deliberate,
documented tradeoff, not an oversight.

**A deliberate deviation from `replace_brick`/`remove_brick`'s "returns
only `Scene`" shape, documented in the module docstring rather than
silently introduced**: `duplicate_brick` is the only Transform operation
whose result isn't fully described by the input id — it creates an id the
caller has no way to know in advance without redundantly re-deriving it.
Considered and declined: forcing `replace_brick`/`remove_brick` into a
matching tuple shape for cosmetic symmetry, which would give every
existing caller a meaningless second value for zero benefit.

---

# Identity / Placement / Selection

- **Identity**: `next_available_id()` guarantees no collision with
  anything currently in the Scene, verified with non-contiguous ids
  (simulating post-deletion gaps).
- **Placement**: fixed `+20 LDU` along X, addressed above.
- **Selection transfers to the new duplicate, not the original.**
  `set_current_scene`'s existing rule alone is insufficient here — it only
  preserves-if-present or clears, it has no mechanism to redirect
  selection to a *different*, newly created id. `on_duplicate_selected`
  explicitly calls `selection_manager.select(new_id)` after
  `set_current_scene` — **the first operation in this session that needs
  to reassign selection to a different id**, rather than relying on the
  existing rule alone. Justified by matching every other tool in this app
  (Move/Rotate operate on "the currently selected brick" — leaving
  selection on the original would force an extra click before the user
  could adjust their fresh copy) and near-universal convention in design
  tools generally.

---

# Preview

None — no continuous parameter exists to preview, same reasoning as
Delete. The entire duplicate is fully determined at the moment of the
menu click. `Renderer`/`ScenePreview` are completely untouched.

---

# Event Flow

```
MainWindow.on_duplicate_selected():
    selected_id = selection_manager.selected_id()
    if selected_id is None:
        status "No brick selected to duplicate."; return

    scene = viewport.renderer.scene
    try:
        new_scene, new_id = duplicate_brick(scene, selected_id)
    except TransformError as error:
        status f"Duplicate failed: {error}"; return

    set_current_scene(new_scene)          # preserves selection on the ORIGINAL by default
    selection_manager.select(new_id)      # explicitly move it to the duplicate
    viewport.renderer.set_selected_id(new_id)

    project_manager.current_project.mark_dirty()
    status f"Duplicated brick #{selected_id} -> #{new_id}."
```

Menu wiring mirrors the existing File-menu pattern exactly:
`edit_menu = menu.addMenu("Edit")` (capturing the previously-discarded
return value), one new `QAction`, `.triggered.connect(...)`,
`edit_menu.addAction(...)`.

---

# Validation

- **No selection**: early return, status message, zero Transform calls,
  zero state changes — verified directly (Scene object identity unchanged).
- **Invalid id**: unreachable through normal flow; `duplicate_brick`'s own
  `TransformError` tested directly for defense-in-depth.
- **Duplicate id collision**: prevented by construction; tested explicitly
  with non-contiguous ids.
- **Duplicate into an occupied position**: not prevented — deliberate,
  consistent with the total absence of overlap-prevention anywhere else
  in Scene/SceneBrick/Move.

---

# Error Handling

Same shape as every prior Transform-backed operation: `on_duplicate_selected`
either fully commits (Scene, selection, and dirty flag all updated
together) or returns early on failure with nothing touched.

---

# Architectural Review (Move + Rotate + Delete + Duplicate, all four in hand)

**A genuine, evidence-based Undo/Redo observation, documented but not
acted on** (matching the mission's explicit "recommend changes only if
implementation experience demonstrates genuine need" — the need is real,
but building Undo/Redo itself is out of scope): none of the four current
handlers retain the *pre-operation* Scene anywhere — each reads `scene`,
computes a new one, and the old reference is dropped the instant
`set_current_scene` reassigns `renderer.scene`. Since every Transform
operation already produces a complete, independent `Scene` object, the
simplest viable future Undo design is a plain history stack of past
`Scene` references, captured before each `set_current_scene` swap —
requiring no Transform-layer API changes at all, since Move, Rotate,
Delete, and Duplicate all already produce a fully-formed new Scene as
their natural output.

**No generalization of `replace_brick`/`remove_brick`'s return shape is
warranted** — reaffirmed from Package_032, now with a third data point
(`duplicate_brick`'s genuinely different tuple return) rather than
retrofitting artificial symmetry onto the other two.

---

# Definition of Done

- A selected brick can be duplicated via the Edit menu.
- A new unique `SceneBrick.id` is created (`Scene.next_available_id()`).
- A new immutable Scene is produced; original Scene verified unchanged.
- The original brick remains completely unchanged.
- Selection behavior is correct — moves to the new duplicate.
- Renderer remains tool-agnostic — confirmed untouched.
- No duplicate editing infrastructure introduced — no new tool class, no
  forced `ActiveToolManager`/`ToolResult` routing for a gesture that
  doesn't exist.

---

# Verification Performed

- `py_compile` clean on every modified file.
- `git diff --stat` confirms `tools/*`, `ui/widgets/viewport_widget.py`,
  `render/*`, and `selection/*` are **completely untouched**.
- **8 tests in `test_scene.py`** (new): empty Scene, single brick,
  multiple/non-contiguous ids, no-collision guarantee, read-only (Scene
  unchanged by calling it), not a reserving counter (repeat calls without
  use return the same value), determinism.
- **15 new tests in `test_scene_transform.py`** (`DuplicateBrickTests`,
  alongside 25 pre-existing `replace_brick`/`remove_brick` tests
  re-confirmed passing): different Scene object; original Scene and
  original brick completely unchanged; new id unique and matches the
  actual duplicate present in the result; part_name/rotation/color_code
  copied exactly; position offset correctly from the original; original
  brick still present post-duplicate; other bricks preserved *by
  reference*; brick count increases by exactly one; no collision even
  with non-contiguous ids; invalid id raises `TransformError` without
  changing the original; determinism.
- **Real end-to-end UI test**: no-selection duplicate is a no-op (object
  identity check); a real duplicate via `on_duplicate_selected()` produces
  a new Scene with one more brick; original brick and Scene unchanged;
  selection moved to the new duplicate, not the original; duplicate's
  part/color/rotation copied exactly and position correctly offset; other
  bricks unaffected; project synced and marked dirty; **duplicating the
  duplicate** produces yet another unique id (not a collision); Move,
  Rotate, and Delete all re-verified still functioning correctly after
  Duplicate was wired into the same MainWindow.
- **Full disk round-trip** (Save → New → Open) on a post-duplicate Scene —
  every field of every brick, including the duplicate, matched.
- Full regression suite re-run: **163 tests** across all ten suites — all
  pass.
- `git status` confirms exactly the planned scope.

---

# Readiness for Undo/Redo

See Architectural Review above — the four Transform operations built
across Packages 029–033 already produce the shape a Scene-stack-based Undo
implementation would need (a complete, independent `Scene` per operation);
what's missing is only the *retention* of prior Scenes, not any change to
how they're produced. Not built here.

---

# Recommendations for Future Packages

- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
- The Duplicate menu action has no keyboard shortcut and no toolbar
  presence beyond the Edit menu — consistent with this package's explicit
  exclusions, worth revisiting once broader UI polish is in scope.
