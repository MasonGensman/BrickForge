# StudWorks

# Package 048

## Title

Data Integrity & Application Lifecycle — Protecting Unsaved Work

---

# Mission

Inspect the application's lifecycle (New, Open, Save, Save As, Export,
Close, Exit) and fix confirmed data-integrity risks before Release
Preparation continues — without redesigning the backend or expanding
scope beyond what inspection found.

---

# Scope

Modified:

- `ui/main_window.py` — new `_confirm_discard_unsaved_changes()` gate
  (Save/Discard/Cancel via `QMessageBox.question()`), a new
  `closeEvent()` override, guards added to `on_new_project()`/
  `on_open_project()`, a new File > Exit action (`Ctrl+Q`, wired to
  `self.close`, reusing the same guarded `closeEvent()` for free), and
  `on_save_project_as()` now derives `Project.name` from the chosen
  filename.
- `project/project_manager.py` — `save()` reordered so `file_path`/
  `mark_saved()` only commit after the write succeeds, not before.

Tests:

- `tests/test_ui_project_lifecycle.py` (new, 16 tests) — the
  confirmation gate's five branches (clean/Cancel/Discard/Save-with-
  path/Save-with-nested-cancel), New/Open's guard, `closeEvent()`'s
  three outcomes, Save-As name derivation (with and without a
  pre-existing `.sws` extension), and `ProjectManager.save()`'s
  reordering on both the failure and success paths.

**Untouched — confirmed via `git diff --stat`**: `generation/`,
`optimization/`, `validation/`, `scene_analysis/`, `repair/`,
`pipeline/`, `export/`, `render/`, `serialization/`, `transform/`,
`tools/`. `project/project.py` itself is untouched — only
`project_manager.py`'s `save()` changed, and only its statement order.

---

# Inspection Predictions

- **✓ Confirmed — one shared gate covers New, Open, and window-close.**
  `_confirm_discard_unsaved_changes()` reuses the *existing*
  `on_save_project()` (including its own already-correct "no path yet
  → Save As → possibly canceled" handling) rather than duplicating any
  dialog logic three times. `test_save_with_no_path_cancels_nested_save_as_and_returns_false`
  directly proves the nested-cancel case falls out of checking the
  final `dirty` state, with no special-case code needed for it.

- **✓ Confirmed — reordering `ProjectManager.save()` doesn't affect
  golden-file output.** Predicted during inspection because neither
  `file_path` nor statement order is part of the serialized JSON — ran
  `test_project_serialization.py` directly (not just reasoned about it)
  both before and after the change; all 21 of its tests, including the
  two byte-for-byte golden-file comparisons, pass unchanged.

- **✓ Confirmed — the Save-As name fix belongs in `on_save_project_as()`,
  not `ProjectManager.save()`.** `test_project_serialization.py`'s
  golden-file tests call `ProjectManager.save()` directly with a
  `Project.name` that deliberately does *not* match the save path's
  filename — exactly the collision predicted during inspection. Putting
  the derivation in the UI-layer caller instead avoided it entirely;
  confirmed by that test suite still passing untouched.

No prediction was refuted.

---

# Architecture Assessment

Every change stays inside the existing `Project`/`ProjectManager`/
`MainWindow` shapes. `_confirm_discard_unsaved_changes()` is the only
new method with real logic; `closeEvent()` is a standard Qt override
with no new concepts. `ProjectManager.save()`'s change is a pure
reordering — identical behavior on the success path, safer behavior on
failure. No new persistence format, no new domain type, no pipeline
involvement.

Worth noting explicitly since it's a real boundary shift from
Package_047: that package's own scope named `project/` (Persistence)
off-limits; this package's mission is specifically about project
lifecycle/ownership, so touching `project_manager.py` here is a
deliberate, mission-appropriate exception, not scope creep.

---

# Data Integrity Recommendations — Implemented

1. **Unguarded window close** (previously discarded unsaved work with
   zero warning on X/Alt+F4) — now gated by `closeEvent()`.
2. **New/Open replacing an unsaved project silently** — now gated the
   same way, via the same shared helper.
3. **`ProjectManager.save()`'s file_path-before-write ordering bug** —
   fixed; a failed save no longer leaves `file_path` pointing at a
   location that was never actually written.
4. **`Project.name` never reflecting the saved filename** — fixed in
   `on_save_project_as()`; the window title, the "Saved ..." status
   message, and the next Save-As dialog's default filename are now all
   accurate.

---

# Lifecycle Recommendations — Implemented

5. **No File > Exit action** — added, reusing the guarded `closeEvent()`
   automatically via `self.close()`.
6. **Zero prior test coverage for New/Open/Save/Save-As** — closed for
   everything this package touched (16 new tests).

---

# Test Summary

**16 new tests, `tests/test_ui_project_lifecycle.py`**:

- `ConfirmDiscardUnsavedChangesTests` (5) — not-dirty short-circuit
  (no dialog shown), Cancel, Discard, Save with an existing path, Save
  with no path whose nested Save-As dialog is itself canceled.
- `OnNewProjectGuardTests` (3) — Cancel leaves the project untouched,
  Discard replaces it as before, not-dirty skips the dialog entirely.
- `OnOpenProjectGuardTests` (1) — Cancel means the file dialog is never
  even shown.
- `CloseEventTests` (3) — not-dirty accepts, dirty+Cancel ignores,
  dirty+Discard accepts.
- `OnSaveProjectAsOwnershipTests` (2) — name derived from the chosen
  filename, with and without a pre-existing `.sws` extension.
- `ProjectManagerSaveOrderingTests` (2) — a failed write leaves
  `file_path` at its prior value; a successful write still sets it and
  clears `dirty` exactly as before.

Also re-ran `tests/test_project_serialization.py` (21 tests) directly
and separately, specifically to confirm the `ProjectManager.save()`
reorder produces byte-identical golden-file output — not inferred from
reading the code, verified.

Also verified live: launched the real app (`src/main.py`) after all
changes — ran 10+ seconds with zero error output.

---

# Regression Results

Full suite: **429 tests**, all passing (413 pre-existing + 16 new).

---

# Scope Isolation Confirmation

`git diff --stat` confirms changes confined to `ui/main_window.py` and
`project/project_manager.py`, plus the one new test file. Only one new
import was introduced (`QMessageBox`, required for the confirmation
dialog) — checked directly against the diff. `generation/`,
`optimization/`, `validation/`, `scene_analysis/`, `repair/`,
`pipeline/`, `export/`, `render/`, `serialization/`, `transform/`,
`tools/`, and `project/project.py` itself are completely untouched.

---

# Project Phase Status

| Phase | Packages | Status |
|---|---|---|
| Backend Foundation | — | ✓ complete |
| Application Integration | 044–047 | ✓ complete |
| Release Preparation | **048**, 049 | **048 done**, 049 next |
| Preview Release | 050 | not started |

---

# Secondary Architectural Recommendations

- `ui/toolbar.py`'s module-level `project_manager` singleton remains
  untouched — nothing in this package required it, and restructuring it
  now would be scope creep for a data-integrity package.
- A future, separate nice-to-have (not implemented, not requested):
  `ProjectManager.load()` falling back to the filename when an
  *existing*, pre-this-fix `.sws` file's embedded name doesn't match
  its filename on disk. Speculative UX polish for old files, not a
  data-integrity fix — left for whoever picks it up, if anyone does.
- Package_047's F11 (`__main__.py`'s corruption) remains unresolved and
  untouched by this package.

---

# Architectural Evolution Documentation

**Lifecycle principle established this package**: any action that
would replace or discard the current project's in-memory state funnels
through exactly one gate (`_confirm_discard_unsaved_changes()`), which
itself reuses the existing Save/Save-As machinery rather than
re-implementing a parallel "are you sure" flow. Three call sites (New,
Open, window-close) share one tested piece of logic instead of three
copies — the same pattern Package_047 established with
`_resolve_ldraw_library()` for the two generation handlers, now applied
to a second, independent case. Worth carrying forward: whenever a
future action needs the same "is it safe to proceed" question, it
should extend this one gate rather than growing a second one.

---

# Architectural Decision Review

**How**: `ui/main_window.py` (one new method, one new override, two
existing methods gated, one new menu action, one existing method
slightly extended) and `project/project_manager.py` (reordering only).

**Whether justified**: yes — every change traces directly to a finding
from this package's own approved inspection; nothing beyond that scope
was touched.

**Ready for Package_049?** Yes — the golden-file suite was directly
re-verified (not assumed) unaffected, and all six release risks from
this package's own Release Risk Review now have a final "Implemented"
state.

---

# Release Readiness Assessment

Before this package, a first-time user's work could vanish with zero
warning from the single most common action in any desktop app (closing
the window) or from New/Open. After this package, all three require an
explicit choice, and the save-state information the user relies on
(window title, status messages, default filenames) is now accurate
rather than permanently showing "Untitled Project" regardless of the
real file. The application now protects user work at the level a
public Preview Release needs.
