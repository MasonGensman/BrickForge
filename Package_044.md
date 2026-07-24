# StudWorks

# Package 044

## Title

Generation Pipeline UI Integration — Giving `generate_model()` Its First Real Caller

---

# Mission

Give the deterministic backend pipeline (`generate_model()`, Package_043)
a real application caller, while preserving every existing user-visible
capability — Flat Mosaic, Height Relief, and manual part selection all
continue working exactly as before.

---

# Background: How This Package Was Scoped

The first version of this planning turn proposed a new immutable
`GenerationProject` wrapper type. Rigorous re-examination against a
four-question evolution review (does it solve a real problem? reduce
coupling? remove complexity? materially help Package_050?) found every
answer was no — `GenerationResult` (Package_043) already bundles
everything needed, and `Project` (Package_026/034/036) already owns
every artifact the wrapper would have re-held. That proposal was
canceled, not implemented, in favor of this package: direct integration
between the application's existing UI and the existing backend, with no
new data type.

A second re-scoping happened during this package's own inspection: a
literal "replace the legacy generation path with `generate_model()`"
reading was rejected, because `generate_model()` has no equivalent of
Height Relief (a genuinely different 3D algorithm) or Flat Mosaic's
manual part-selection settings panel. Replacing the legacy path outright
would have been a real, user-visible feature regression, not an
architectural improvement. This package instead adds `generate_model()`
as a second, independent way to generate — additive, not a replacement.

---

# Scope

Modified:

- `pipeline/generation_pipeline.py` — `generate_model()`'s `image_path`
  parameter widened to `str | Path | GenerationInput`
- `ui/widgets/image_preview_widget.py` — new `generate_model_requested`
  signal, new "Generate (New Pipeline)" button, new
  `generate_via_new_pipeline()` handler
- `ui/main_window.py` — new `on_generate_model()` handler, wired to the
  new signal

Tests:

- `tests/test_generation_pipeline.py` — `AcceptsGenerationInputDirectlyTests`
  (3 new tests)
- `tests/test_ui_generation_integration.py` (new — the first test
  coverage for anything in `ui/`)

**Untouched — confirmed via `git diff --stat`**: `generation/generation_mode.py`,
`generation/registry.py`, `generation/mosaic_generator.py`,
`generation/height_relief_generator.py`, and both mode registration
modules (the entire legacy path); `optimization/`, `validation/`,
`scene_analysis/`, `repair/`, `services/`, `ldraw/`, `engine/`, `render/`,
and — notably — `project/` itself, confirming the "Project needs zero
additions" finding held up in practice, not just in planning.

---

# API Evolution Rationale: Why `generate_model()` Widens Here, Not Earlier

*(Preserved verbatim from the approved planning discussion — the
permanent record of why this API changed at this point in the roadmap.)*

**Why accepting only an image path was the correct design for
Package_043.** At the time Package_043 was built, `generate_model()` had
zero application callers — confirmed then and re-confirmed during this
package's own inspection. With no real caller to observe, the only
defensible signature was the one matching the mission's own literal
input list ("Image + Catalog + Generation Constraints"): a path, since
that's the concrete form "an image" takes for a function that must load
one from scratch. Package_043.md already documents that a pre-built
`GenerationInput` alternative was explicitly *considered and rejected*
at that time, for exactly this reason: *"no concrete consumer exists
yet ... widening the signature without one would be exactly the
speculative flexibility this project avoids."* That was the right call
given the evidence available then — not a gap to be embarrassed about,
but a deliberate deferral.

**The concrete workflow Package_044's inspection actually found.**
Reading `ImagePreviewWidget.import_image()` directly (not assumed, not
inferred) showed that it already constructs a complete `GenerationInput`
— `prepared_image` and `analysis` both already computed — the moment a
user imports an image, well before any "Generate" action fires. By the
time generation is requested, a fully-formed `GenerationInput` already
sits in memory, owned by the widget. If `generate_model()` still only
accepted a path, this integration would be forced to hand it
`generation_input.source_path` and let it silently reload the file,
re-run `prepare_image()`, and re-run `analyze_image()` — full duplicate
work against data the caller is already holding. This exact calling
shape did not exist, and had no evidence behind it, until this package's
own inspection surfaced it.

**Why this is evidence-driven, not speculative.** Package_043 didn't say
"never widen this" — it said "widen this if a real avoid-re-loading need
is evidenced then." That is precisely what happened: not a hypothetical
"a UI might someday want this," but a direct reading of an
already-existing, already-shipped widget's actual source code, which
today builds a `GenerationInput` before generation is ever requested.
The distinction that matters: speculative widening would have meant
adding `GenerationInput` support back in Package_043 "just in case" —
extra surface area with nothing backing it. Doing it now, cited against
a specific, inspected call site, is the API responding to a fact that
was discovered, not a guess about what might be convenient.

**How this preserves the project's API-evolution philosophy rather than
breaking it.** This is the same discipline this project has applied
repeatedly — Package_018 deferred crop/rotate until Package_034 had a
concrete need; Package_036 scoped `GenerationConstraints` only to fields
with evidenced use; Package_038 took a required `PaletteEngine` parameter
rather than building one speculatively. Package_044 doesn't reconsider or
invalidate Package_043's original judgment — it's the intended second
half of the same pattern: defer flexibility until a real caller exists,
then extend the API exactly when that caller's actual shape becomes
known.

---

# Integration Architecture Summary

`generate_model()`'s `image_path` parameter now accepts `str | Path |
GenerationInput`; when already a `GenerationInput`, `GenerationInput.from_source()`
is skipped entirely (and `settings` is ignored, since the input has
already been prepared). Fully backward compatible — every existing
path-based caller, including Package_043's own tests, is unaffected.

`ImagePreviewWidget` gains a second, independent button
("Generate (New Pipeline)") and signal (`generate_model_requested`),
deliberately **not** folded into the existing mode dropdown — the
`GenerationMode`/`SettingsPanel` protocol (`ImageResource` in, `Scene`
out, mode-specific settings) doesn't fit `generate_model()`'s shape
(`GenerationInput`/`GenerationConstraints` in, `GenerationResult` out),
and forcing a fit would have meant bolting a mismatched shape onto a
protocol built for something else. A separate button touches none of
the existing mode-selection machinery.

`MainWindow.on_generate_model()` mirrors `on_generate_lego()`'s existing
structure exactly: same `PaletteEngine` construction from
`renderer.brick_manager.library`, same `except (OSError, ValueError)`
clause (already covers everything `generate_model()` can raise — no
adaptation needed), same `set_current_scene()` call, same
`mark_dirty()`. It additionally reads `Project.generation_constraints`
(already existed since Package_036, always `None` today since no UI
sets it yet, but now correctly respected the moment a future package
adds one) and reports a validation summary in the status message.

**`Project` required zero changes** — confirmed by `git diff --stat`
showing `project/` completely untouched. `scene`, `generation_input`,
`generation_constraints`, and `mark_dirty()` already existed and were
sufficient.

---

# Verification Performed

- `py_compile` clean on every modified file.
- `git diff --stat` confirms the legacy generation path
  (`generation_mode.py`, `registry.py`, both generators, both
  registration modules) and every other pipeline stage
  (`optimization/`, `validation/`, `scene_analysis/`, `repair/`,
  `services/`, `ldraw/`, `engine/`, `render/`, `project/`) are
  **completely untouched** — this package only modified
  `pipeline/generation_pipeline.py` and two `ui/` files.
- **3 new tests, `test_generation_pipeline.py`**: `generate_model()`
  accepts a pre-built `GenerationInput` directly; produces an identical
  result to passing the equivalent path; performs no redundant reload
  (verified by deleting the source file after building the
  `GenerationInput`, then confirming generation still succeeds).
- **7 new tests, `test_ui_generation_integration.py`** (the first test
  coverage for anything in `ui/`): the new button emits
  `generate_model_requested` with the current `GenerationInput`, or
  shows a message and emits nothing without an imported image; the
  existing button/signal are confirmed present and distinct, proving
  additivity; `on_generate_model()` — tested via a lightweight,
  duck-typed stand-in carrying only the attributes it actually touches
  (not a real `MainWindow`, which does real, slow setup this test
  deliberately avoids depending on) — correctly updates the viewport
  Scene and `Project` (`scene`, `generation_input`, `dirty`) on success,
  reports validation status in the message, shows the existing "LDraw
  library not available" message without generating when no library is
  present, reports (not raises) a "no candidates" failure, and
  correctly narrows candidate selection when `Project.generation_constraints`
  is set — proving that field, though nothing sets it via UI yet, is
  already live and respected.
- Full regression suite re-run: **386 tests**, all passing (376
  pre-existing + 10 new).

---

# Definition of Done

- `generate_model()` has a real application caller for the first time.
- Existing user-visible behavior is fully preserved — Flat Mosaic,
  Height Relief, and manual part selection are byte-for-byte unchanged,
  confirmed via `git diff --stat` on every legacy file.
- `Project` required no redesign or new fields — confirmed, not just
  predicted.
- The new integration is additive and fully reversible — removing the
  new button/handler/signal would cleanly revert the application to its
  pre-Package_044 behavior with no other trace.

---

# What This Package Deliberately Does Not Do

- Does not remove, deprecate, or alter `GenerationMode`, the mode
  dropdown, or either registered generation mode — both remain fully
  functional and user-selectable.
- Does not add a `GenerationConstraints`-editing UI — `Project.generation_constraints`
  is read and respected, but nothing yet lets a user set it. A future
  package could add this without any further backend change.
- Does not add progress reporting — matches the legacy path's own
  existing (single blocking call, no intermediate feedback) behavior
  exactly; not a regression, since neither path had this before.
- Does not touch export, save/load, rendering, or editing, per the
  approved scope.

---

# Recommendations for Future Packages

- **Export Integration** remains independent of this package — both
  generation paths produce a plain `Scene` consumed identically by
  `set_current_scene()`, so wiring `export_scene()` to a menu action is
  unaffected by which path produced the current Scene.
- A future package could add a `GenerationConstraints`-editing settings
  panel (mirroring the existing per-mode `SettingsPanel` pattern),
  immediately usable by `on_generate_model()` with no further wiring.
- Full legacy-path retirement (removing `GenerationMode`/Flat
  Mosaic/Height Relief) remains a deliberate future product decision,
  not something this package forces — it would need `generate_model()`
  to first gain either multi-algorithm support or a manual part-override
  capability to avoid the regression this package's inspection
  identified and avoided.
