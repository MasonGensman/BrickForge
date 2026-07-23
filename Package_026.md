# StudWorks

# Package 026

## Title

Project Save/Load — Wiring a Persistent StudWorks Project to the UI

---

# Mission

Give StudWorks a persistent, named `.sws` Project that owns a `Scene`
and can be created, saved, and reopened from the real application UI —
built on top of Package_025's Scene serialization rather than
duplicating it.

---

# Scope

Modified (no new top-level packages — extends pre-existing,
half-built infrastructure discovered during inspection):

- `serialization/serializer.py`, `serialization/deserializer.py` —
  extract `scene_to_document()` / `document_to_scene()` as reusable,
  path-agnostic primitives.
- `project/project.py`, `project/project_manager.py` — rewritten to
  give `Project` direct ownership of a `Scene`.
- `ui/toolbar.py`, `ui/main_window.py` — wire the previously dead
  Open/Save toolbar buttons and empty File menu to real handlers.

Tests:

- `tests/golden/sws_projects/{empty_project,named_project_with_bricks}.sws`
- `tests/test_project_serialization.py`

Untouched (verified via `git diff`, not assumed): `generation/*`,
`optimization/*`, `render/*`, `engine/*`, `preparation/*`, `export/*`,
`services/*`, `models/*`, `ldraw/*`, `ui/widgets/*`.

---

# Inspection Findings

**A major, unplanned-for discovery**: `project/project.py` and
`project/project_manager.py` already existed, as did toolbar
Open/Save `QAction`s — but `Project` used a stale `.bfp` extension and
a hardcoded `version="0.1.0"` field never wired to `_version.py`, and
only `toolbar.py`'s `new_action` was connected to anything
(`lambda: project_manager.new_project()`, no UI feedback at all).
`open_action`/`save_action` existed on the toolbar and did nothing.
The File menu had zero `QAction`s. Confirmed with you this was the
correct thing to extend rather than a parallel system to build
alongside.

**`QMessageBox` is not used anywhere in this codebase** — confirmed
via grep before choosing an error-reporting mechanism; all errors
reported through `BrickForgeStatusBar` text, matching
`on_generate_lego`'s existing precedent exactly.

**Scene ownership re-evaluated per your request, and simplified**:
originally proposed `ProjectManager.save(scene, path)`. Re-checked
whether `Project` owning `Scene` directly was actually a bigger change
— it wasn't. Three small additions were sufficient: `MainWindow`
calls `project_manager.new_project()` once at startup (so
`current_project` is never `None` during normal operation), one sync
line at the end of `on_generate_lego` (`current_project.scene = scene;
current_project.mark_dirty()`), and `ProjectManager.save(path)` reads
`self.current_project` with no `Scene` parameter at all. Simpler than
the original proposal, and it's what you asked for.

---

# Decisions Applied (per your approval)

1. **`scene_to_document()` / `document_to_scene()` exposed** as
   reusable primitives (extracted from Package_025's
   `serialize_scene`/`deserialize_scene` bodies, additive only — full
   Package_025 15-test suite re-confirmed passing after the
   extraction). `Project.to_dict()` embeds a full `"StudWorks Scene"`
   document via these; `Project.from_dict()` reconstructs via the
   same.
2. **Project owns its Scene directly.** `ProjectManager.save(path)`
   takes no `Scene` parameter.
3. **Wrapped project format, minimal metadata** — see schema below.
4. **Reused the existing toolbar/menu structure** rather than
   redesigning it — the pre-existing `project_manager` module-level
   singleton in `ui/toolbar.py` was flagged as a minor inconsistency
   during planning (a UI module owning application state) but
   deliberately left as-is, per "do not redesign the UI."

---

# Format: `.sws` (StudWorks Project)

A `"StudWorks Project"` JSON document wrapping a nested
`"StudWorks Scene"` document (Package_025's own format, unmodified).
Each has its own independent `format`/`schema_version` pair, so either
can evolve without the other changing.

---

# Schema (version 1)

```json
{
  "format": "StudWorks Project",
  "schema_version": 1,
  "name": "My House",
  "created": "2026-01-01T00:00:00",
  "modified": "2026-01-01T00:05:00",
  "app_version": "0.2.0",
  "scene": {
    "format": "StudWorks Scene",
    "schema_version": 1,
    "bricks": [ ]
  }
}
```

`created`/`modified` are ISO-8601 timestamps. `app_version` is sourced
dynamically from `_version.APP_VERSION` at save time (fixing a
previously-hardcoded, stale literal). Extension is `.sws`, replacing a
previously-stale `.bfp` reference found during inspection.

---

# Public API

```python
class Project:
    name: str
    file_path: Path | None
    scene: Scene
    created: datetime
    modified: datetime
    dirty: bool
    app_version: str

    def mark_dirty(self) -> None: ...
    def mark_saved(self) -> None: ...
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "Project": ...


class ProjectManager:
    current_project: Project | None

    @property
    def has_project(self) -> bool: ...
    def new_project(self, name: str = "Untitled Project") -> Project: ...
    def save(self, path: str | Path) -> None: ...
    def load(self, path: str | Path) -> Project: ...
```

---

# Responsibilities Split / Error Handling

- **`ProjectFileError`** — raised for a problem in the project
  document itself: not `"StudWorks Project"`, unsupported
  `schema_version`, or missing `"scene"` field. Never raised for a
  problem inside the embedded scene.
- **`SceneSerializationError`** — raised (uncaught, propagated as-is
  from `document_to_scene()`) for a problem in the embedded scene
  data. `Project.from_dict()` deliberately does not catch it, so
  callers can tell which layer actually failed. Verified directly: a
  corrupted embedded scene inside an otherwise-valid project document
  raises `SceneSerializationError`, not `ProjectFileError`.
- **`OSError`** — unwrapped, for missing files / unwritable paths,
  matching Packages 024/025's precedent.
- **`RuntimeError`** — `ProjectManager.save()` with no project open
  (shouldn't happen in normal UI operation, since `MainWindow` always
  has an implicit project, but the manager itself doesn't assume a
  particular caller).
- `MainWindow` catches `(OSError, ProjectFileError,
  SceneSerializationError)` around Open, and `OSError` around Save,
  reporting failures via the status bar — no exception ever reaches
  the user as a crash or a Qt error dialog.

---

# UI Wiring

- File menu: New Project / Open Project... / (separator) / Save
  Project / Save Project As..., each a real `QAction` connected to a
  `MainWindow` handler.
- Toolbar: New/Open/Save buttons now delegate to the same
  `MainWindow` handlers (previously New called `ProjectManager`
  directly with no feedback; Open/Save were fully dead).
- `MainWindow.create_widgets()` calls `project_manager.new_project()`
  once at startup, so an implicit "Untitled Project" always exists.
- `on_generate_lego()` syncs `current_project.scene` and calls
  `mark_dirty()` after a successful generation — the only place a
  `Scene` changes, so the only place that needs to keep it in sync.
- `undo_action`/`redo_action` deliberately left unwired — out of
  scope.

---

# Out of Scope (deliberately not built)

- Recent-files list, autosave, unsaved-changes-on-close prompt, undo
  integration, multi-project/tabs — none requested, none built.
- No migration infrastructure for a hypothetical schema v2, matching
  Package_025's own precedent.

---

# Definition of Done

- A `Project` can be created, saved to `.sws`, and reopened, restoring
  its `Scene` exactly.
- File → New/Open/Save/Save As and the matching toolbar buttons work
  end-to-end from the real UI.
- Project-level and Scene-level validation failures are distinguishable
  by exception type.
- Fully independent of `generation/`, `render/`, `optimization/`,
  `export/` — confirmed via `git diff` and AST inspection.

---

# Verification Performed

- `py_compile` clean; AST inspection confirms `project/` has zero
  dependency on `generation/`, `ui/`, `render/`, `optimization/`, or
  `export/`; no circular imports.
- Re-ran Package_025's full 15-test suite after extracting
  `scene_to_document()`/`document_to_scene()` — unaffected.
- **Real end-to-end UI test** (`MainWindow`, `QFileDialog` faked at
  the Qt layer only): implicit Untitled Project at startup; real
  generation through the UI producing 4 bricks; `current_project.scene
  is renderer.scene` and marked dirty; Save Project As wrote a real,
  correctly-structured `.sws` file and cleared dirty; Save Project
  reused the existing path without re-prompting (verified with a
  dialog stub that raises if called); New Project reset the viewport;
  Open Project restored the exact original 4-brick scene field-for-
  field; cancelled Open/Save-As dialogs left all state untouched.
- **Dedicated error-handling test**: invalid JSON, wrong format
  identifier, wrong schema version, and missing `"scene"` field all
  raise `ProjectFileError`; a corrupted embedded scene raises
  `SceneSerializationError` instead; a missing file raises `OSError`
  unwrapped; `save()` with no project open raises `RuntimeError`.
  `current_project` confirmed to remain `None` after every failed
  load (no partial state).
- **Golden-file suite** (13 tests, mirroring Packages 024/025's
  pattern exactly): 2 canonical projects (`empty_project`,
  `named_project_with_bricks`, the latter covering a non-identity
  rotation and a `None` color code) built with fixed, explicit
  `created`/`modified` timestamps (never `datetime.now()`, which would
  make byte-for-byte comparison unreproducible); golden files exist;
  saved output matches byte-for-byte; loading the golden files
  reconstructs the expected projects; round-trip equality;
  determinism; save doesn't mutate the input scene; all 7
  error-handling cases.
- **Confirmed the harness actually detects regressions**: deliberately
  corrupted `empty_project.sws`'s `name` field, re-ran the suite, got
  clear failures pointing at the exact mismatch, restored the file
  byte-exact, re-confirmed all 13 tests pass.
- Re-ran Packages 024's and 025's own test suites as a final cross-
  check (32 tests total across all three suites) — all pass.
- `git status`/`git diff --stat` confirm exactly the planned scope —
  plus the long-standing pre-existing unstaged changes to
  `docs/ARCHITECTURE.md` and `.vscode/settings.json` (left alone, as
  always).

---

# Recommendations for Future Packages

- **Recent-files list / unsaved-changes-on-close prompt**: natural
  next additions now that `dirty`/`file_path` are tracked correctly.
- **`ui/toolbar.py`'s module-level `project_manager` singleton**: a UI
  module currently owns application state that `MainWindow` also
  holds a reference to. Not restructured here (out of scope, per "do
  not redesign the UI"), but worth revisiting if a second window or
  a testing harness ever needs an independent `ProjectManager`.
- **Undo/Redo**: `undo_action`/`redo_action` remain fully unwired —
  still out of scope, called out again for visibility.
- **The renderer's upside-down LDraw geometry bug** (discovered during
  Package_024, native LDraw is Y-down, this app's viewport applies no
  compensating flip): still real, still unfixed, still out of scope.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
