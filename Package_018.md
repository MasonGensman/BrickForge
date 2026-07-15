# StudWorks

# Package 018

## Title

Shared Image Preparation Pipeline

---

# Mission

Insert a shared, generation-mode-agnostic Image Preparation stage
between Image Import and every Generation Mode:

```
Image Import → Image Preparation → Generation Mode → Scene
```

Migrate `MainWindow`'s existing inline resize-to-fit logic
(`_capped_image`) into this shared stage, unchanged in behavior, so
every present and future Generation Mode receives an already-prepared
image and never performs its own preprocessing.

---

# Scope

New:

- `preparation/__init__.py`
- `preparation/image_preparation.py`

Modified:

- `ui/widgets/image_preview_widget.py`
- `ui/main_window.py`

Untouched (verified via `git diff`, not assumed):

- `generation/*` (contract, registry, Flat Mosaic registration, `__init__.py`, `mosaic_generator.py`)
- `analysis/image_analysis.py` (reused as-is — `resize()` is the only primitive Package_018 needed)
- everything under `render/`, `engine/`, `services/`

---

# Decisions Applied (per your approval)

1. **Option B**: `ImagePreviewWidget` calls `prepare_image()` itself,
   once, immediately after import. The resulting `ImageResource` is
   stored as `self._prepared_image` and is the *same object* used for
   both the thumbnail (`display()`) and the value emitted via
   `generate_requested`. The signal shape is unchanged from
   Package_017 (`Signal(object, object, object)` — `image, mode,
   settings`); `MainWindow.on_generate_lego` needed no signature
   change at all, only the removal of its own preparation logic.
2. **`max_dimension` stays an internal default** (`48`, on
   `ImagePreparationSettings`), not exposed as a UI control. No
   spin box or other control was added.
3. **Only Fit mode was implemented.** No `FitMode` enum was
   introduced — since Stretch doesn't exist yet, a single-value enum
   would be speculative scaffolding for a deferred feature.
   `prepare_image()` performs exactly one transform: aspect-ratio-
   preserving fit to `max_dimension`, byte-for-byte reproducing the
   old `_capped_image` formula. Crop, center crop, fill, padding,
   rotate, and flip were not implemented.

# Architectural Principle Added

**Image Preparation is deterministic, stateless, and generation-mode
agnostic. It performs pure image transformations only.** Stated
directly in `preparation/image_preparation.py`'s module docstring,
mirroring how `generation_mode.py`'s docstring states Generation
Modes' own responsibility boundary.

---

# What Changed

## `preparation/image_preparation.py` (new)

- `ImagePreparationSettings` — `@dataclass(slots=True)` (matching
  `GenerationSettings`'s convention: user-adjustable configuration,
  not a frozen computed result), one field: `max_dimension: int = 48`.
  Completely independent of `GenerationSettings` — no shared fields,
  no inheritance.
- `prepare_image(image, settings=None) -> ImageResource` — the only
  transform. If the image already fits within `max_dimension` on both
  axes, returns the same object unchanged (no copy). Otherwise scales
  uniformly (`max_dimension / max(width, height)`), rounds, and
  resizes via the existing `analysis.image_analysis.resize()` — no new
  resize primitive was written.
- Zero imports from `brickforge.generation` or `brickforge.ui` —
  confirmed by AST inspection, not assumed.

## `ImagePreviewWidget`

- New `self._prepared_image: ImageResource | None` field.
- `import_image()`: after a successful `manager.load()`, immediately
  calls `prepare_image(resource)` and stores the result as
  `self._prepared_image`; `display()` is called with the *prepared*
  image, not the raw one.
- `generate_lego()`: emits `self._prepared_image` (was
  `self.manager.current_image`). `self.manager.current_image` (the raw
  import) is left completely untouched and still reachable — Imported
  Image and Prepared Image remain two distinct, separately-held
  concepts, per your requirement that they stay separate internally
  even though the UI only ever shows the prepared one.
- No new visible UI controls were added — no settings panel for
  preparation exists in this package, since both configurable knobs
  (`max_dimension`, mode selection) were explicitly kept
  non-user-facing/single-valued by your decisions 2 and 3.

## `MainWindow`

- Removed `_capped_image`, `MAX_GENERATION_DIMENSION`, and the
  `resize`/`ImageResource` imports that only that method used.
- `on_generate_lego`'s signature and body are otherwise unchanged — it
  now simply uses the `image` it receives directly, since it already
  arrives prepared.

---

# Definition of Done

- A shared Image Preparation architecture exists, fully independent of
  any Generation Mode — confirmed via AST import inspection (zero
  imports of `brickforge.generation` from `preparation/`).
- `GenerationMode`/`GenerateCallable`/`registry.py` needed **zero**
  changes — the existing contract already treated `image` as an opaque
  `ImageResource`, so no future mode will ever need to perform its own
  preprocessing to satisfy this pipeline.
- Renderer, engine, services, and generation/* are byte-for-byte
  untouched (`git diff --stat`, empty output).
- Optimization is untouched and unmentioned — preparation and
  generation remain clearly separate responsibilities from it.

---

# Verification Performed

- `py_compile` clean on all new/modified files.
- **Determinism**: `prepare_image()` called twice on identical input
  produces identical output (`np.array_equal`).
- **No mutation**: source `ImageResource.pixels` byte-identical before
  and after `prepare_image()`.
- **Exact equivalence to the old formula**: compared `prepare_image()`
  against a reimplementation of the pre-Package_018 `_capped_image`
  math across 6 cases (below cap, exactly at cap, over on width only,
  over on height only, over on both, extreme aspect ratio) — dimensions
  and pixel content matched exactly in every case.
- **Same-object short-circuit**: confirmed an in-bounds image returns
  the identical object; an out-of-bounds image returns a new one.
- **Settings respected**: a custom `max_dimension=10` produced a
  correctly-scaled result.
- **Widget-level, real button-driven end-to-end** (not direct method
  calls — `QFileDialog.getOpenFileName` was monkeypatched and the real
  `import_button`/`generate_button` were clicked):
  - Small image (4x4, within the 48px cap): `_prepared_image is
    resource` (same object) confirmed; Generate produced 16 bricks and
    the exact status text `"Generated 16 bricks."` — byte-identical
    outcome to Package_017's own end-to-end test, proving default
    behavior is unchanged.
  - Large image (200x100, above the cap): prepared to 48x24
    (aspect-preserving), and generation produced exactly 1,152 bricks
    (48×24) — proving the renderer/generation pipeline consumed the
    *prepared* image, not the raw 200×100 one (which would have
    produced 20,000 bricks). This is the single strongest proof that
    Image Preparation now genuinely sits in the pipeline.
  - Confirmed `ImageManager.current_image` retained its original
    200×100 dimensions throughout — the raw import is never mutated
    or replaced.
- **AST inspection**: zero mosaic-specific imports and zero
  `GenerationMode.id` branches in any of the three touched/new files
  (re-confirmed for `image_preview_widget.py`, `main_window.py`, and
  newly for `preparation/image_preparation.py`).
- **Untouched-scope confirmation**: `git diff --stat` against
  `generation/*`, `analysis/image_analysis.py`, and everything under
  `render/`, `engine/`, `services/` produced zero output.
- **Live application launch**: real GPU context (NVIDIA GeForce RTX
  3060 Ti), same pre-existing missing-part warnings as every prior
  package, no new tracebacks.
- `git status` confirms exactly the planned scope: one new directory
  (`preparation/`), two files modified, `Package_018.md` added, plus
  the long-standing pre-existing unstaged changes to
  `docs/ARCHITECTURE.md` and `.vscode/settings.json` (left alone, as
  always).

---

# Recommendations for Future Packages

- **Stretch mode**: when a real second Fit strategy is needed, add a
  `mode: FitMode` field to `ImagePreparationSettings` and a second
  branch in `prepare_image()` at that time — deliberately not built
  now per your decision 3.
- **User-facing `max_dimension` control**: a `QSpinBox` in a small
  preparation settings panel is a natural, low-risk future addition
  once there's an actual need to let users trade off detail vs. brick
  count.
- **Crop / fill / padding / rotate / flip**: `analysis.image_analysis`
  already has `crop()` ready to build on; none of these have a present
  consumer, so none were added.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
