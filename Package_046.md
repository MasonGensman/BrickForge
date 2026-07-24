# StudWorks

# Package 046

## Title

Generation Workflow Polish — Closing First-Time-User Friction in the Existing Workflow

---

# Mission

Inspect the complete user workflow from project creation through export
and fix unnecessary friction, inconsistent behavior, and missing
feedback — without redesigning the backend, without expanding scope
beyond what inspection actually found, and without inventing new
workflows alongside the two that already exist.

---

# Scope

Modified:

- `ui/widgets/image_preview_widget.py` — bold section captions
  ("Standard Pipeline (Recommended)" / "Legacy Generation (manual mode,
  no validation)") and explanatory tooltips on both Generate buttons;
  reordered so the recommended path appears first.
- `ui/toolbar.py` — Undo/Redo now `setEnabled(False)` with an updated
  status tip, instead of being wired to nothing and silently doing
  nothing when clicked; new Export toolbar action beside Save.
- `ui/main_window.py` — removed the permanently-empty View/Project/Help
  menu stubs; viewport brick selection now feeds `PropertiesWidget` the
  same way Brick Library selection already did; Properties clears when
  a Delete removes the currently-selected brick; the status bar's
  initial message is `"StudWorks Ready"` (was `"BrickForge Ready"`); new
  `_refresh_window_title()` shows the current project's name and a `*`
  dirty marker, called from every project/scene mutation site.

Tests:

- `tests/test_ui_generation_integration.py`,
  `tests/test_ui_export_integration.py` — extended the existing
  duck-typed `_FakeMainWindow` stand-ins with a `setWindowTitle`
  recorder (required once `on_generate_model()` started touching it)
  plus new assertions on the recorded title.
- `tests/test_ui_workflow_polish.py` (new, 10 tests) — toolbar
  Undo/Redo disabled state and the new Export action, window-title
  dirty-marker formatting, viewport-selection → Properties wiring
  (including the unresolvable-part case), Properties clearing on
  Delete-of-selected but not on Move-of-selected, and the two Generate
  buttons' distinct tooltips/captions.

**Deferred, not implemented** (see "What This Package Deliberately Does
Not Do" below): keyboard shortcuts, and deduplicating
`on_generate_lego()`/`on_generate_model()`'s near-identical
`PaletteEngine`-construction guard.

**Untouched — confirmed via `git diff --stat`**: every backend/pipeline
module (`generation/`, `optimization/`, `validation/`, `scene_analysis/`,
`repair/`, `pipeline/`, `export/`), and — notably — `project/` itself.
This package touches only three files under `ui/`, plus tests.

---

# Inspection Predictions

- **✓ Confirmed — Undo/Redo, empty menus, and the status-bar string.**
  Implemented exactly as inspected: disable rather than silently
  no-op; remove rather than leave permanently empty; fix the one
  drifted string.

- **✓ Confirmed — Export toolbar button.** Added beside Save, matching
  New/Open/Save's existing pattern, for parity with the other two
  headline verbs of this phase's journey.

- **⚠ Partially confirmed, corrected during implementation — the
  Properties-widget lookup.** The approved plan said to resolve a
  clicked `SceneBrick` via `catalog.get(brick.part_name)`. Implementing
  it required reading `models/part_definition.py` and
  `engine/scene_brick.py` directly, which showed `PartCatalog.get()` is
  keyed on the bare `part_number` (e.g. `"3005"`), while
  `SceneBrick.part_name` is the `.dat`-suffixed LDraw filename (e.g.
  `"3005.dat"`) — confirmed against the seed catalog's own data and
  `ldraw_catalog_builder.py:311`'s `part_number=entry.stem`. The literal
  plan as written would have silently returned `None` for every real
  brick. Fixed to `catalog.get(Path(brick.part_name).stem)`, reusing
  the exact idiom `ldraw_catalog_builder.py` already established for
  this same filename → part_number conversion, rather than inventing a
  new one. Caught before any test ran, by re-reading the actual
  dataclasses rather than trusting the plan's shorthand.

- **⚠ Partially confirmed, corrected during implementation — where the
  window-title refresh lives.** The plan described refreshing the
  title from a single central point. Implementing it against the real
  call sites showed `set_current_scene()` cannot be that point:
  `on_brick_transformed()`, `on_generate_model()`,
  `on_generate_lego()`, and `on_duplicate_selected()` all call
  `mark_dirty()` *after* `set_current_scene()` returns, so a refresh
  inside `set_current_scene()` would always show the previous, stale
  dirty state. Corrected to a small `_refresh_window_title()` helper
  called explicitly at the true end of every handler that changes
  project or dirty state (8 call sites) — mechanical duplication
  consistent with this file's existing style, not a new violation of
  the project's "stages stay independent" principle, since these are
  all in the same file already following the same pattern.

- **✓ Confirmed, with a discovered PySide6/shiboken gotcha along the
  way.** Writing `ToolbarTests` initially failed with `RuntimeError:
  Internal C++ object (PySide6.QtGui.QAction) already deleted` — a
  helper method built a local `QMainWindow` + toolbar and returned only
  the individual `QAction` objects; once the helper returned, nothing
  Python-side referenced the parent window anymore, so garbage
  collection tore down the whole Qt parent-child tree (window →
  toolbar → actions) even though the actions dict still pointed at the
  now-dead C++ objects. Fixed by keeping the window referenced on
  `self` for the test's lifetime. Not a Package_046-specific bug — a
  reusable lesson for any future test that builds a live Qt widget tree
  inside a helper method.

No prediction was refuted outright; both partial corrections were
caught and fixed before implementation completed, and are recorded here
per this project's standing "Inspection Prediction" discipline
(honesty about what inspection got wrong, not just whether tests pass).

---

# Architecture Summary

Every change is UI-presentation-only: labels, tooltips, a disabled
state, a menu removal, a status-bar string, a toolbar action wired to
an already-existing handler (`on_export_model()`, unchanged since
Package_045), and one new `MainWindow` helper
(`_refresh_window_title()`) plus two small additions to existing
handlers (`on_brick_clicked()`, `on_brick_transformed()`). No backend
signature changed, no new module was created, and no domain type was
touched — consistent with this phase's explicit "avoid backend
redesign, avoid feature expansion" guidance.

`PropertiesWidget` itself needed no changes — `display_brick()` and
`clear()` already existed and already accepted exactly what
`on_brick_clicked()` now passes them; the gap was purely that nothing
in `MainWindow` called them from the viewport-selection path.

---

# UI Readiness Review

Performed as a first-time-user walkthrough after implementation, per
the explicit request that closed out this package's approval turn.
Recorded here rather than only in chat, since it documents *why* the
remaining gaps are believed non-blocking, not just that they exist.

**How to begin**: toolbar/menu are clean (no dead empty menus); the
Image Preview dock's "Import Image..." button is the obvious first
action. Residual gap: the central 3D viewport has no in-viewport
onboarding hint for an empty project.

**How to generate a model / which workflow to use**: "Standard
Pipeline (Recommended)" is now the first, bold-captioned option
directly under Import, with its own tooltip; "Legacy Generation
(manual mode, no validation)" is clearly secondary. Residual softness:
this relies on the user reading a caption/tooltip — nothing actively
prevents picking either blindly, and there's still no in-app
explanation of *when* Legacy is the deliberate right choice (Height
Relief, manual part selection) beyond the caption text itself.

**How to inspect results**: the core gap is closed — viewport selection
now feeds `PropertiesWidget` exactly as Brick Library selection always
did, and clears correctly when the selected brick is deleted.

**How to export**: consistent now — File-menu action and a toolbar
button beside Save, mirroring the established Save pattern exactly.

**Verdict**: no remaining issue blocks a first-time user from
completing Import → Generate → Export. The friction identified in
inspection (unlabeled duplicate buttons, silently-broken Undo/Redo,
missing Properties feedback, branding drift, a stale title) is
resolved. The Application Integration phase is approaching completion
for the golden path, with one non-cosmetic residual item worth
prioritizing for Package_047 (below).

---

# Test Summary

**10 new tests, `tests/test_ui_workflow_polish.py`**, plus 2 new
assertions added to existing `test_ui_generation_integration.py` tests:

- Toolbar: Undo/Redo report `isEnabled() == False`; Export action is
  present alongside New/Open/Save.
- `_refresh_window_title()`: no dirty marker when clean, `*` marker
  once `Project.mark_dirty()` has been called.
- `on_brick_clicked()`: selecting a placed brick displays its resolved
  `BrickDefinition` in Properties; clicking empty space clears it; a
  brick whose part can't be resolved in the catalog clears Properties
  rather than guessing (matches the Candidate System's own "unknown
  over wrong" precedent).
- `on_brick_transformed()`: deleting the selected brick clears
  Properties; moving the selected brick leaves it untouched (still
  accurate, since neither part nor identity changed).
- `ImagePreviewWidget`: the two Generate buttons have distinct,
  non-empty tooltips, and the new section captions read "Recommended"
  / "Legacy" respectively.

Also verified live: launched the real app (`src/main.py`) as a smoke
test — ran 20+ seconds with zero error output, confirming nothing
crashes. Full pixel-level visual confirmation (button labels, tooltip
text, disabled-button rendering) was **not** possible — no tool
available here can screenshot a native PySide6/OpenGL window (only
browser tabs are drivable). Recorded as a known verification gap
rather than claimed as confirmed.

---

# Regression Results

Full suite: **403 tests**, all passing (393 pre-existing + 10 new).

---

# Scope Isolation Confirmation

`git diff --stat` confirms changes are confined to
`ui/widgets/image_preview_widget.py`, `ui/toolbar.py`,
`ui/main_window.py`, and the three test files listed above. No new
`import`/`from` statements were introduced anywhere (checked directly
against the diff, not assumed). Every backend/pipeline module and
`project/` itself are untouched.

---

# What This Package Deliberately Does Not Do

- Does not add keyboard shortcuts (`Ctrl+S` etc.) — deferred as a
  lower-priority, still-open item rather than bundled in, to keep this
  package's diff focused on the inspected findings.
- Does not deduplicate `on_generate_lego()`/`on_generate_model()`'s
  near-identical `PaletteEngine`-construction guard — same reasoning.
- Does not add an unsaved-changes confirmation on New/Open — see
  Recommendations below; this is real, but wasn't part of the approved
  Tier-1 scope and touches more call sites than the rest of this
  package.
- Does not change the legacy generation path's feedback (still
  brick-count-only, no validation summary) — `GenerationMode.generate()`
  genuinely has no validation step; the new tooltip now says so
  up front, but closing the asymmetry itself would mean changing the
  legacy pipeline's behavior, out of scope for a UI-polish package.
- Does not fix `src/brickforge/__main__.py` (found corrupted — contains
  shell-command text, not Python — while smoke-testing the app for this
  package's readiness review). Unrelated to workflow polish; spun off
  separately rather than folded in here.

---

# Recommendations for Future Packages

- **Unsaved-changes guard on New/Open** (the one item from the
  readiness review worth prioritizing): the title bar's `*` now makes
  dirty state visible, but nothing stops silently discarding it via New
  or Open. A confirmation dialog gated on `project.dirty` would close
  this with no backend change.
- `PropertiesWidget`'s empty-state text
  (`"Select a brick from the library."`) is now stale wording — it
  doesn't mention viewport selection, even though this package made
  that path work too.
- No onboarding hint exists in an empty project's 3D viewport.
- `src/brickforge/__main__.py`'s corruption (see above) — tracked as a
  separate background task, not part of Package_046/047's roadmap.
- Package_047 remains otherwise unspecified; nothing above narrows or
  assumes its scope beyond these candidates.

---

# Project Phase Status

- **Current Phase**: Application Integration
- **Completed Packages**: Package_044 (Generation Pipeline UI
  Integration), Package_045 (Export UI Integration), Package_046
  (Generation Workflow Polish)
- **Remaining Packages**: Package_047 (scope not yet specified)
- **Package_050 alignment**: the Import → Generate → Export journey is
  now not just functionally complete (Package_045) but legible to a
  first-time user — labeled generation paths, working feedback on
  viewport selection, accurate branding/title state, and no
  silently-broken toolbar controls.
- **Readiness for Release Preparation (048–049)**: contingent on
  Package_047; this package's own readiness review found nothing that
  reorders or invalidates that dependency, beyond flagging the
  unsaved-changes guard as a concrete candidate for it.
