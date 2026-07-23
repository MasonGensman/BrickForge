# StudWorks

# Package 028

## Title

Transform System — Immutable Scene Editing Engine

---

# Mission

Establish the architecture for editing a selected brick: a deterministic,
immutable transformation engine future tools (Move, Rotate, Duplicate,
Undo, ...) will all build on. Not editing tools themselves — no UI.

---

# Scope

New:

- `transform/__init__.py`, `transform/scene_transform.py`
  (`TransformError`, `replace_brick`)

Modified:

- `ui/main_window.py` — new `set_current_scene()` helper; `on_generate_lego`,
  `on_new_project`, `on_open_project` refactored to call it instead of each
  independently reimplementing Scene replacement.

Tests:

- `tests/test_scene_transform.py`

Untouched (verified via `git status`): `generation/*`, `optimization/*`,
`preparation/*`, `export/*`, `serialization/*`, `project/*`, `services/*`,
`models/*`, `ldraw/*`, `selection/*`, `render/*`, `ui/widgets/*`,
`ui/toolbar.py`.

---

# Inspection Findings

**A real, verified pre-existing bug**: `on_new_project()` called
`project_manager.new_project()` (which builds a `Project` with its own
fresh `Scene()`) and *separately* called `renderer.set_scene(Scene())` with
a second, different `Scene()` instance — confirmed empirically
(`project.scene is renderer_scene` → `False`, distinct object ids). Both
were empty so it was silent, but `project_manager.current_project.scene`
and `renderer.scene` diverged immediately after New Project, unlike after
Generate (already explicitly synced) or Open Project (already correct,
since `on_open_project` passed the same `project.scene` object to both).
Fixed as a direct consequence of centralizing Scene replacement — see
below.

**`Scene.get()`** (added in Package_027) is sufficient for id-existence
validation; no new `Scene` helpers were needed.

**`SceneBrick` equality/replace, verified empirically before design**:
confirmed `SceneBrick(...) == SceneBrick(...)` works correctly by field
value (PyGLM's `vec3`/`quat` support `==`), and `dataclasses.replace()`
works cleanly with `slots=True` dataclasses, producing a genuinely new,
unmutated instance. This confirms the pattern a future Move/Rotate tool
will use: `dataclasses.replace(scene.get(id), position=new_position)`, then
hand the result to `replace_brick`.

---

# Transform Architecture

Plain stateless function, **not** a class (`TransformService`/
`SceneTransformer`/`SceneEditor`/`TransformManager` were all considered and
rejected). Every existing Scene → Scene pipeline stage in this codebase —
`optimize_scene`, `export_scene`, `scene_to_document` — is a stateless plain
function; the classes that do exist (`SelectionManager`, `ProjectManager`,
`BrickManager`) all hold genuine state between calls. A transform has no
such state, so a manager/service class would hold nothing. New
`transform/` package, mirroring `project/`/`serialization/`/`export/`/
`optimization/`/`selection/` as a single-concern top-level package.

---

# Public API

```python
class TransformError(Exception): ...

def replace_brick(scene: Scene, updated_brick: SceneBrick) -> Scene:
    """Raises TransformError if updated_brick.id isn't in scene."""
```

Chose this over the mission's other suggested shape,
`transform_scene(scene, brick_id, transform)`: that implies a generic
`transform` callable/object parameter — an abstraction with no second
concrete user yet, since Move/Rotate don't exist. `replace_brick` is the
minimal, concrete primitive the mission's own scope asked for ("replace one
SceneBrick while preserving every other brick"); a future Move tool
computes its new `SceneBrick` and calls this directly. If a second and
third transform kind later reveal a genuine common wrapper shape, that's a
decision for *that* package, made with real evidence — not guessed now.

---

# Immutability

`replace_brick` builds a new `Scene`, reusing every untouched `SceneBrick`
by reference and substituting only the target — the same "new container,
unchanged elements reused by reference" convention already established by
`optimization/pipeline.py` and `brick_merge_optimizer.py`. Neither the
input `Scene` nor any `SceneBrick` is ever mutated. Verified directly:
object-identity checks on both the original `Scene` and every untouched
`SceneBrick` before/after every test.

---

# Validation Strategy

- **Invalid brick id**: `updated_brick.id` not found via `scene.get(...)` →
  raises `TransformError`.
- **Duplicate id**: not a distinct case for this function — `replace_brick`
  performs a strict one-for-one swap, so the output Scene's id set is
  provably identical to the input's (verified by test). It can never
  introduce a duplicate. Pre-existing duplicate ids in a malformed input
  Scene are a precondition issue for whoever built that Scene, not audited
  here (Scene has never enforced global id-uniqueness anywhere in this
  codebase).
- **Invalid transform**: doesn't apply to this API shape — there's no
  separate "transform" object to validate, `updated_brick` is already a
  complete, concrete `SceneBrick`. No speculative geometric validation
  (NaN checks, etc.) was added — no caller can produce such values yet (no
  UI tool exists in this package's scope), and `SceneBrick` construction
  elsewhere in this codebase performs none either.
- **No-op transform**: not rejected — succeeds normally, producing a
  structurally-equal new Scene. "Every edit produces a new Scene" is about
  mechanism (immutability), not a ban on semantic no-ops.

---

# Scene Replacement: `MainWindow.set_current_scene(scene)`

Implemented (not just recommended) — it directly fixes the New Project bug
above and reduces three near-duplicated blocks to one.

```python
def set_current_scene(self, scene: Scene) -> None:
    self.project_manager.current_project.scene = scene
    self.viewport.renderer.set_scene(scene)

    selected_id = self.selection_manager.selected_id()
    if selected_id is not None and scene.get(selected_id) is None:
        self.selection_manager.clear()

    self.viewport.renderer.set_selected_id(self.selection_manager.selected_id())
    self.viewport.update()
```

**Why validate, not unconditionally clear**: Package_027 established "clear
selection on every Scene replacement." This package's mission also requires
"selection remains valid after a successful transform." Those two rules
would conflict under a naive "always clear" implementation, since a
Transform's output Scene is a *new Scene object* too. The resolution: one
rule — clear selection only if the currently-selected id is no longer
present in the new Scene — produces correct behavior for both cases without
the caller needing to declare which kind of replacement this is:

- **New / Open / Generate**: the new Scene has an entirely different id
  space, so the old id is never found → cleared, exactly matching
  Package_027's existing behavior (verified: unaffected).
- **Transform**: `replace_brick`'s contract guarantees the exact same id
  set as the input → the id is always found → selection survives.

This is SelectionManager's own documented invariant — `selected_id` is
either `None` or references an existing `SceneBrick.id` in the active
Scene — implemented as enforced code in one place, rather than left as a
convention each caller has to remember.

**Dirty-marking stays outside the helper, deliberately**: New/Open must
*not* mark the project dirty (fresh/just-loaded-from-disk state — Open
already calls `mark_saved()` internally), while Generate (today) and a
future Transform-driven tool (later) should. That's a distinct concern
from "where is the Scene now installed," so each caller marks dirty (or
doesn't) itself, after calling `set_current_scene()`. Verified directly:
`set_current_scene()` alone does not flip `dirty`.

`on_generate_lego`, `on_new_project`, `on_open_project` were refactored to
call this helper — each now only does what's genuinely specific to it
(dirty-marking, status text, error handling), not a broader UI refactor.

---

# Event Flow (documented for future tool packages, not implemented beyond the engine)

```
Tool (future package)
    -> dataclasses.replace(scene.get(id), ...)
    -> replace_brick(scene, updated_brick)
New Scene
    -> MainWindow.set_current_scene(new_scene)
       -> Project.current_project.scene = new_scene
       -> Renderer.set_scene(new_scene)
       -> selection validated (survives, since the id space is unchanged)
       -> Renderer.set_selected_id(...)
       -> viewport.update()
```

---

# Error Handling

`replace_brick` either returns a valid new `Scene` or raises
`TransformError` — never a silent no-op that looks like success. No UI call
site exists yet to catch it (no tools in this package's scope); a future
tool package will catch `TransformError` the same way `on_open_project`
already catches `ProjectFileError`/`SceneSerializationError`.

---

# Definition of Done

- A reusable immutable transformation engine exists (`replace_brick`).
- Future editing tools can reuse it directly.
- Scene replacement follows one consistent architecture
  (`set_current_scene`), used by all three existing Scene-replacing call
  sites.
- Selection remains valid after a successful transform — verified
  end-to-end.
- No editing UI was introduced.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- AST inspection: `transform/scene_transform.py` imports only
  `brickforge.engine.scene` and `brickforge.engine.scene_brick` — no
  coupling to Renderer, Selection, Project, or UI.
- **14 pure unit tests** (`test_scene_transform.py`): different Scene
  object returned; original Scene unchanged (value *and* identity checks);
  target brick never mutated in place; updated brick present with new
  values; every other brick preserved *by reference* (`is`, not just
  `==`); id set and brick count unchanged; order preserved; invalid id
  raises `TransformError` without changing the original Scene; no-op
  replace succeeds; replacing with the exact same object works;
  determinism; empty-Scene edge case.
- **Serialization round-trip**, confirming a Transform-produced Scene isn't
  special-cased anywhere: `scene_to_document`/`document_to_scene`,
  `serialize_scene`/`deserialize_scene` (real file), and a full `Project`
  save/load cycle — all matched field-for-field after a `replace_brick`
  call.
- **Real end-to-end verification** against the actual `MainWindow`:
  confirmed New Project now installs one shared Scene object
  (`project.scene is renderer.scene` — the bug fix); Generate LEGO still
  keeps them in sync and still marks the project dirty; a real click-driven
  selection survives being pushed through `set_current_scene()` with a
  Transform-produced Scene; a genuinely different Scene (simulating
  New/Open) clears that same selection; `set_current_scene()` alone does
  not mark the project dirty; Open Project keeps `project.scene` and
  `renderer.scene` as one object.
- Full regression suite re-run: **69 tests** across
  `test_export_golden_files`, `test_scene_serialization`,
  `test_project_serialization`, `test_selection_manager`, `test_picking`,
  `test_scene_transform` — all pass.
- `git status` confirms exactly the planned scope — plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Relationship to Future Move/Rotate/Delete Tools

- **Move/Rotate**: compute a new `SceneBrick` via
  `dataclasses.replace(scene.get(id), position=...)` or `rotation=...`,
  then call `replace_brick(scene, updated)` and
  `MainWindow.set_current_scene(result)`. No new engine code needed.
- **Duplicate**: not directly served by `replace_brick` (it's an insert,
  not a swap) — a future package's own concern, likely a sibling function
  in `transform/` once a second, third real use case exists to justify its
  exact shape.
- **Delete**: `Scene.remove_brick(id)` already exists (Package_021) and is
  not part of this package's immutability guarantees (it mutates in
  place) — a future Delete tool should decide whether to keep using it
  directly or wrap it in an immutable equivalent matching `replace_brick`'s
  shape; not decided here, out of scope.
- **Undo**: benefits directly from every edit producing a new `Scene`
  object — a history stack of `Scene` references becomes straightforward
  once a tool exists to populate one; not built here.

---

# Recommendations for Future Packages

- The first real editing tool (Move or Rotate) is the natural next step,
  built entirely on `replace_brick` + `set_current_scene` with no further
  engine work.
- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026, still unrestructured) and the renderer's upside-down
  LDraw geometry bug (Package_024, still unfixed) remain outstanding and
  unaffected by this package.
