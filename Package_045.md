# StudWorks

# Package 045

## Title

Export UI Integration — Completing Import → Generate → Export

---

# Mission

Give `export_scene()` (Package_024) a real application caller, so a
user can export the current Scene to a `.ldr` file BrickLink Studio can
open — while preserving the backend, `Project`, and the legacy
generation pipeline exactly as they are.

---

# Scope

Modified:

- `ui/main_window.py` — new "Export Model..." File menu action, new
  `on_export_model()` (dialog handling) and `_export_model_to()`
  (actual export) methods, mirroring `on_save_project_as()`/
  `_save_project_to()`'s existing split exactly

Tests:

- `tests/test_ui_export_integration.py` (new, 7 tests)

**Untouched — confirmed via `git diff --stat`**: `export/exporter.py`,
`export/ldraw_writer.py`, `generation/`, `optimization/`, `validation/`,
`scene_analysis/`, `repair/`, `pipeline/`, and — notably — `project/`
itself. This package touches only `ui/main_window.py`.

---

# Inspection Predictions

Per the explicit request to compare inspection against implementation,
not just report passing tests:

- **✓ Confirmed — `export_scene()` required no changes.**
  `git diff --stat` shows zero modification to `export/exporter.py` or
  `export/ldraw_writer.py`. Every call in `_export_model_to()` uses the
  function exactly as it already existed.

- **✓ Confirmed — `Project` required no modifications.**
  `git diff --stat` shows `project/` completely untouched. Export only
  reads `project.scene`/`project.name`; no write, not even
  `mark_dirty()`, was ever needed.

- **✓ Confirmed — the backend export subsystem remained fully
  untouched.** No new module, no wrapper, no signature change anywhere
  in `export/`.

- **✓ Confirmed — the existing Save workflow was directly reusable.**
  `on_export_model()`/`_export_model_to()` mirror
  `on_save_project_as()`/`_save_project_to()`'s dialog/cancellation/
  extension-normalization/try-except-status-message shape exactly, with
  no adaptation needed beyond substituting the export-specific filter
  string and call.

- **✓ Confirmed — export needed no "library not available" guard.**
  Unlike `on_generate_model()` (Package_044), which must check
  `renderer.brick_manager`/`library` before constructing a
  `PaletteEngine`, `_export_model_to()` needed only `self.catalog`,
  already always present. No such guard was written, and none was
  needed — verified directly by the passing empty/populated export
  tests requiring no special-cased setup.

- **✓ Confirmed — empty-Scene export required no special-casing.**
  `test_empty_scene_exports_successfully` calls `_export_model_to()`
  against a brand-new `Project()`'s default empty `Scene` with zero
  additional logic, and it produces a valid file and a correct
  "Exported 0 bricks" message — exactly the graceful behavior predicted
  from reading `write_ldraw_file()` during inspection.

- **✓ Confirmed — cancellation is silent, matching
  `on_save_project_as()`'s convention.**
  `test_cancellation_exports_nothing` confirms `window.status.last_message`
  is `None` after a canceled dialog — no message shown, no export
  attempted, exactly matching the existing Save-As behavior this
  package intentionally mirrored rather than inventing new UX for.

- **✓ Confirmed — no toolbar button was needed.**
  Implemented as a File-menu-only action, matching Duplicate's
  (Package_033) own precedent that not every action needs toolbar
  prominence. No toolbar change was made.

- **✓ Confirmed — the duck-typed `MainWindow` stand-in needed less
  setup than Package_044's.** `_FakeMainWindow` in this package needs
  only `catalog`, `status`, and `project_manager` — no viewport,
  renderer, or selection manager at all, exactly as predicted, since
  export never touches the render/selection layer.

- **✓ Confirmed, with direct evidence added — this package completes
  Import → Generate → Export.** The original inspection inferred this
  from each half being independently correct; implementation added a
  genuine end-to-end test
  (`GenerateThenExportEndToEndTests.test_generated_scene_can_be_exported`)
  chaining a real `on_generate_model()` call directly into a real
  `_export_model_to()` call, through the actual, unmodified production
  methods. It passes, turning an inference into direct proof.

No prediction was refuted or only partially confirmed. This package's
inspection differed from Package_044's in exactly the way predicted:
no signature mismatch, no feature-regression risk, no re-scoping needed
— the simpler case the "Public API Review" section anticipated.

---

# Architecture Summary

`export_scene(scene, catalog, path)` is unchanged and remains the
correct long-term API — every parameter it needs was already available
on `MainWindow` in exactly the right shape. `on_export_model()` shows a
save dialog (default filename from `project.name`, `.ldr` extension
normalized if omitted, silent return on cancellation);
`_export_model_to()` performs the actual export inside a
`try/except OSError`, reporting success (brick count + filename) or
failure via the existing status bar — the same shape
`_save_project_to()` already established.

---

# Test Summary

**7 tests, `tests/test_ui_export_integration.py`**:

- Successful export (real Scene → real file, content verified, correct
  status message).
- Empty-Scene export (no special-casing, graceful by construction).
- Write failure reported via status message, not raised.
- An unrecognized part is still exported, matching `export_scene()`'s
  own documented "never silently drop" behavior.
- Dialog cancellation exports nothing and shows no message.
- Missing `.ldr` extension is normalized before export.
- Full Import → Generate → Export chain, through the real
  `on_generate_model()`/`_export_model_to()` methods together.

---

# Regression Results

Full suite: **393 tests**, all passing (386 pre-existing + 7 new).

---

# Scope Isolation Confirmation

`git diff --stat` confirms the only change is to `ui/main_window.py`.
`export/`, `generation/`, `optimization/`, `validation/`,
`scene_analysis/`, `repair/`, `pipeline/`, and `project/` are completely
untouched.

---

# Public API / Architectural Evolution

No API evolution occurred, and none was warranted — documented in the
approved planning turn as the correct engineering decision precisely
because inspection found no mismatch to justify one, unlike
Package_044's genuinely evidenced `generate_model()` widening. This
package is the confirming case for that distinction: evolve APIs when
inspection finds a real gap; leave them alone when it doesn't.

---

# Project Phase Status

- **Current Phase**: Application Integration
- **Completed Packages**: Package_044 (Generation Pipeline UI
  Integration), Package_045 (Export UI Integration)
- **Remaining Packages**: Package_046, Package_047 (scope not yet
  specified)
- **Package_050 alignment**: a user can now complete Import Image →
  Generate Model → Export Model entirely through the new deterministic
  pipeline, verified end to end by this package's own test — the gap
  identified in Package_044's own "Recommendations for Future Packages"
  is now closed.
- **Readiness for Release Preparation (048–049)**: not yet — contingent
  on 046/047, whose content remains unspecified. This package's
  inspection surfaced no reason to reorder or reconsider them.
