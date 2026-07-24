# StudWorks Engineering Handoff

**This is the project's canonical architectural reference.** It is written as
permanent engineering documentation, not a conversation transcript. A new
Claude session should be able to read only this file and continue development
with no other context.

Last updated: after Package_048 (commit `efac418b`), 2026-07-24.

---

# 1. Project Overview

**StudWorks** transforms user-supplied images into accurate, editable LEGO
models and exports them to BrickLink Studio for refinement.

```
Image → Analysis → LEGO Model → Visualization → BrickLink Studio Export
```

StudWorks is **not** a BrickLink Studio replacement. Studio remains the
preferred environment for editing, instructions, and final refinement.
StudWorks' job ends at producing a structurally valid, exportable model.

**Engineering philosophy** (from `CLAUDE.md`, the project's binding
instructions): favor maintainability, readability, simplicity, stability, and
incremental improvement. Avoid large rewrites without justification,
unnecessary abstractions, premature optimization, and scope creep. Every
feature is delivered as a numbered **Package_XXX** with its own Mission,
Scope, Definition of Done, and a `Package_XXX.md` written at completion.

**Long-term architecture**: a fully deterministic backend pipeline
(image → Scene) sits behind one canonical entry point, `generate_model()`,
which the application layer (UI, and eventually project management and a
Windows executable) calls rather than reaching into individual pipeline
stages. The backend and the application are deliberately decoupled: backend
stages never know the UI exists, and the UI is free to evolve (or keep a
legacy path alongside the new one) without the backend changing.

---

# 2. Current Architecture

Each subsystem below is described by purpose, responsibilities, public API,
dependencies, and the design decisions that shaped it.

## 2.1 Scene / SceneBrick — the foundational data model

`engine/scene.py`, `engine/scene_brick.py`

- **`SceneBrick`**: `id: int`, `part_name: str`, `position: glm.vec3`,
  `rotation: glm.quat` (identity default), `color_code: int | None`. Pure
  data — no GPU/OpenGL knowledge. `SceneBrick.from_definition(definition, *,
  id, position=None, rotation=None, color_code=None)` is the one authoritative
  place a catalog `BrickDefinition` becomes a placed `SceneBrick`.
- **`Scene`**: `list[SceneBrick]` plus `add_brick()`, `get(id)`,
  `next_available_id()` (`max(ids, default=-1) + 1`, scene-local, read-only),
  `clear()`, `__iter__`. A mutating `remove_brick(id)` method also exists
  (pre-dates the immutable pipeline) but nothing in the modern pipeline calls
  it.
- **Immutable by convention, not by Python enforcement**: no pipeline stage
  or `Transform` function ever mutates a `Scene` in place — every
  transformation builds a fresh `Scene`, reusing untouched `SceneBrick`s by
  reference. This is the single most load-bearing convention in the codebase;
  nearly everything downstream assumes it.
- Depends only on `glm`. No render/UI/engine-internal coupling.

## 2.2 BrickDefinition / PartCatalog — the catalog layer

`models/part_definition.py`, `services/part_catalog.py`,
`services/ldraw_catalog_builder.py`, `services/catalog_cache.py`,
`services/ldraw_library_locator.py`

- **`BrickDefinition`**: `part_number`, `name`, `category`, `ldraw_filename`
  (aliased as `.part_name`), `stud_width`, `stud_length`, `height_units`,
  `available_colors: list[int]`, `bounding_box: BoundingBox | None`,
  `description`, plus unused-so-far `weight_g`/`aliases`/`family`.
- **`PartCatalog`**: `.all()`, `.get(part_number)`, `.from_seed()` (9
  hand-curated parts with fully real metadata), `.load_best_available()` (the
  real, ~24,297-part LDraw-derived catalog if a library is found via 4-tier
  discovery, else the seed fallback — never raises). Two-layer caching:
  process-local `functools.lru_cache` + an on-disk pickle keyed by resolved
  library path and a cheap content fingerprint (`CACHE_SCHEMA_VERSION = 2`).
- **Critical, load-bearing finding (Package_037)**: the real catalog's
  `stud_width`/`stud_length`/`height_units`/`category`/`available_colors` are
  placeholder values (`1, 1, 24.0, "Part", []`) for most parts —
  `build_catalog_parts()` derives real values only when they can be
  confidently validated against actual geometry/header data: **31.9%** of
  real parts get a genuine stud footprint, **23.2%** a genuine category (via
  an explicit `!CATEGORY` LDraw header line). `available_colors`/`family`
  have **no derivable source at all** in the LDraw format — they remain
  placeholder for every real part and would need an external data source
  (BrickLink/Rebrickable) to ever populate. Only the 9-part seed catalog has
  fully real metadata across the board.

## 2.3 Generation Candidate System — the searchable part space

`generation/candidates.py` (Package_036)

- **`GenerationConstraints`**: `permitted_colors`/`permitted_categories`/
  `permitted_families` (each `None` = unconstrained, explicit `[]` =
  constrained to nothing), `min_stud_width`/`max_stud_width`/
  `min_stud_length`/`max_stud_length`, `excluded_part_numbers` (defaults to
  `[]`).
- **`candidates_for(catalog, constraints=None) -> list[BrickDefinition]`**:
  the one sanctioned way to discover eligible parts — AND-combines every
  active constraint field, deterministic order (matches `catalog.all()`
  exactly when `constraints=None`).
- Matching is **strict** against placeholder metadata: an empty
  `available_colors` never satisfies a `permitted_colors` constraint, even
  though `properties_widget.py`'s UI treats that same emptiness as "Unknown"
  for *display*. This is deliberate — a query system should never silently
  pretend to satisfy a constraint it can't verify.

## 2.4 GenerationInput / Image Preparation — the image-to-pipeline boundary

`preparation/generation_input.py`, `preparation/image_preparation.py`
(Package_034/035)

- **`GenerationInput`**: `source_path`, `content_hash`, `settings:
  ImagePreparationSettings`, `prepared_image: ImageResource` (in-memory
  only), `analysis: ImageAnalysisResult` (in-memory only, added Package_035).
  `GenerationInput.from_source(path, settings=None)` is the **one** canonical
  factory — deterministic, so calling it twice with the same path/settings
  reproduces byte-identical output. This determinism is what lets `Project`
  store only a lightweight reference and regenerate everything expensive on
  load.
- **`ImagePreparationSettings`**: `max_dimension=48`, `crop_rect=None`,
  `rotation_degrees=0`. Pipeline: crop → rotate → resize.
- A real EXIF-orientation bug was found and fixed here: `QImageReader` +
  `setAutoTransform(True)` replaced a bare `QImage(path)` call, which never
  applied EXIF rotation (verified against real, hand-constructed EXIF bytes).

## 2.5 Image Analysis — deterministic image description

`analysis/image_analysis.py` (Package_035, extending pre-existing
`ImageStatistics`/`analyze()` which had zero prior consumers, confirmed via
grep, making the rename to `ImageAnalysisResult`/`analyze_image()` risk-free)

- **`ImageAnalysisResult`**: `width`/`height`/`pixel_count`/`aspect_ratio`,
  `average_color`, `histogram`, `dominant_colors` (top-5, deterministic
  bucket-quantized, transparent pixels excluded), `mean`/`min`/`max`/
  `std_luminance`, `edges` (Sobel magnitude map), `edge_density`,
  `occupied_bounds` (bounding box of non-transparent content, or `None`).
- **`analyze_image(image: ImageResource) -> ImageAnalysisResult`** is the one
  entry point; `crop`/`resize`/`rotate90`/`to_grayscale`/`average_color`/
  `histogram`/`sobel_edges`/`dominant_colors`/`occupied_bounds` are
  independent pure helpers.
- Region segmentation, connected components, contours, and general "feature
  extraction" are deliberately deferred — no concrete consumer, too
  AI-adjacent for this deterministic layer.
- Became genuinely load-bearing (not just present) for the first time in
  Package_038: `occupied_bounds` drives cropping/centering,
  `dominant_colors` drives palette reduction.

## 2.6 PaletteEngine — color matching

`palette/palette_engine.py` (pre-existing)

- `PaletteEngine(config_path, alpha_threshold=16)`: loads and filters an
  `LDConfig.ldr` file to solid colors only. `map_color(rgba) -> MappedColor
  (color, distance, is_transparent)` via redmean RGB distance.
- Always caller-constructed and passed in explicitly — never built internally
  by a pipeline stage, since it needs a filesystem path a pure pipeline stage
  shouldn't need to know about. This precedent (established when
  `generate_scene()` was built, Package_038) was deliberately preserved when
  the canonical orchestrator was built (Package_043): `generate_model()`
  also takes `palette` as a required, caller-supplied parameter.

## 2.7 Generation Engine — the first deterministic generator

`generation/generation_engine.py` (Package_038)

- **`generate_scene(generation_input, catalog, palette, constraints=None)
  -> Scene`**. Algorithm: `candidates_for()` → `select_generation_brick()`
  (one part for the whole Scene) → crop/center on `occupied_bounds` → map
  each of ≤5 `dominant_colors` once via `palette` → one brick per occupied
  pixel, snapped to the nearest pre-mapped color.
- **`select_generation_brick(candidates) -> BrickDefinition`**: an isolated,
  independently-replaceable policy hook (smallest stud footprint, tie-broken
  by `part_number`). The generation engine calls it and never knows *why* a
  part was chosen — this isolation exists specifically so a future
  optimization package can improve part selection without touching the
  pipeline.
- Brick IDs come from `scene.next_available_id()` — the same mechanism every
  other Scene producer uses, not a bespoke formula.
- Never performs optimization, validation, or repair.

## 2.8 Legacy Generation (`GenerationMode`) — still fully intact

`generation/generation_mode.py`, `generation/registry.py`,
`generation/mosaic_generator.py`, `generation/height_relief_generator.py`,
plus their registration modules (pre-034, deliberately preserved)

- **`GenerationMode(id, display_name, description, version,
  create_settings_panel, generate: GenerateCallable)`**, where
  `GenerateCallable = (image: ImageResource, palette, catalog, settings) ->
  Scene`. Two registered modes:
  - **Flat Mosaic**: one brick per non-transparent pixel, unconstrained
    per-pixel palette matching, user picks the exact part and
    origin-mode/skip-transparent options via a settings panel.
  - **Height Relief**: 3D stacked height-map generation from luminance — a
    genuinely different algorithm with **no equivalent** in the new pipeline.
- **This path is fully user-selectable today, unchanged, alongside the new
  pipeline.** Package_044 explicitly evaluated and *rejected* replacing it:
  `generate_model()` has no manual-part-override and no 3D/height concept, so
  removing this path would be a real, user-visible feature regression, not an
  architectural improvement. Full retirement remains a deliberate, unmade
  future product decision.

## 2.9 Optimization

`optimization/optimizer.py`, `pipeline.py`, `registry.py`,
`brick_merge_optimizer.py`, `hidden_brick_removal_optimizer.py`
(Packages 020–022, integrated with the Candidate System in Package_039)

- **`Optimizer(id, display_name, description, version, optimize:
  OptimizeCallable)`**, `OptimizeCallable = (scene, catalog, constraints) ->
  Scene`.
- **`optimize_scene(scene, catalog, constraints=None, optimizer_ids=None) ->
  Scene`**: runs every registered optimizer sequentially, each consuming the
  previous one's output.
- **Brick Merge**: conservatively merges groups of identical, adjacent
  bricks into a larger catalog-declared part, discovered via
  `candidates_for(catalog, constraints)` (Package_039 refactor — previously a
  raw `catalog.all()` scan, now respects user constraints). Runs to a fixed
  point within one call.
- **Hidden Brick Removal**: removes bricks fully surrounded on all six sides
  by identical part+rotation neighbors. Single deterministic pass against
  the *original* Scene, inherently idempotent. Its `constraints` parameter is
  accepted (protocol conformance) but never used — it never selects a new
  part.
- This subsystem existed, fully built and tested, for two packages
  (020–022) before it had any relationship to the Candidate System, and
  had **zero production callers** until Package_039 wired it into the
  constraint-aware architecture.

## 2.10 Validation

`validation/build_validation.py` (Package_040)

- **`validate_scene(scene, catalog) -> ValidationReport`**. Read-only, never
  mutates its inputs.
- **`ValidationReport`**: `issues: tuple[ValidationIssue, ...]`, `is_valid`
  property (true iff no `ERROR`-severity issue).
- **`ValidationIssue`**: `rule_id`, `severity` (`ERROR`/`WARNING`),
  `message`, `brick_ids`.
- Four independent rules, each a standalone pure function:
  `duplicate_brick_id` (ERROR), `invalid_part_reference` (WARNING — an
  unresolved part may still be valid in BrickLink's own library),
  `invalid_orientation` (ERROR — quaternion length outside `1e-3` of 1.0),
  `overlapping_bricks` (WARNING — rotation-aware world-space AABB derived
  from `stud_width`/`stud_length`/`height_units`, **not**
  `BrickDefinition.bounding_box`, which is `None` for every seed-catalog
  part).
- **Severity is a confidence signal**: `ERROR` = objectively invalid
  regardless of catalog; `WARNING` = accuracy bounded by known catalog
  metadata incompleteness (§2.2).
- Disconnected-component / structural / physical validation is explicitly
  **not implemented** — no stud/tube connectivity data exists anywhere in
  this codebase, and a geometric-adjacency proxy would be an unsupported
  approximation, not real connectivity.

## 2.11 Scene Analysis

`scene_analysis/scene_analysis.py` (Package_041)

- **`analyze_scene(scene, catalog) -> SceneAnalysisResult`**. Describes,
  never judges — a categorically different job from Validation, and this
  module never imports from `validation/`.
- **`SceneAnalysisResult`** structurally splits **`SceneMeasurements`**
  (`brick_count`, `unique_part_count`, `color_count`, `layer_count`, `bounds`
  — world-space AABB or `None`) from **`SceneSummaries`**
  (`part_distribution`, `layer_distribution`, both sorted tuples) — kept
  consistent by construction (computed from the same underlying pass) and
  tested for that consistency directly.
- Deliberately reimplements its own world-AABB geometry rather than
  importing Validation's — the established "pipeline stages stay
  independent, even at minor duplication cost" convention.

## 2.12 Scene Repair

`repair/scene_repair.py` (Package_042)

- **`repair_scene(scene, report: ValidationReport) -> Scene`**. Read-only on
  its inputs; only ever *consumes* a `ValidationReport`, never re-validates.
- Three repairs, each tracing directly to one `ValidationIssue.rule_id`:
  - `duplicate_brick_id`: every occurrence beyond the first gets a fresh id.
    **Critical implementation detail**: the replacement id is computed
    *once*, upfront, from every id in the *complete* original Scene
    (`max(all_ids, default=-1) + 1`, incremented manually thereafter) — NOT
    via `Scene.next_available_id()` called mid-rebuild, which was proven
    (empirically, before writing the fix) to reintroduce a *new* collision
    with a not-yet-processed original id.
  - `invalid_part_reference`: the named brick is removed via
    `transform.remove_brick()` — no way to know what part should have been
    there instead.
  - `invalid_orientation`: normalized via `transform.replace_brick()` only if
    the quaternion's length is within `[0.5, 1.5]` — outside that
    (including exactly zero, mathematically undefined to normalize), the
    brick is left unchanged and still reported by a later validation pass.
- **Duplicate-id repair gates every other repair in the same call** — a
  duplicated id makes `ValidationIssue.brick_ids` ambiguous, so
  `repair_scene()` performs *only* the duplicate-id fix when any exist, and
  returns immediately. This makes repair **intentionally re-entrant**:
  `Validate → Repair → Validate → Repair → ...` until the Scene stops
  changing, not a single-pass fixer.
- `overlapping_bricks` has **no automatic repair** — no deterministic way to
  choose which brick should move without altering the represented model.
- **Deliberately reuses `transform/scene_transform.py`'s `remove_brick()`/
  `replace_brick()`** — the one considered exception to "pipeline stages
  stay independent," justified because `transform/` is a foundational,
  shared editing-primitive layer (predating the generation pipeline,
  already depended on by UI editing tools), not a peer pipeline stage.

## 2.13 Generation Pipeline Orchestrator — the canonical entry point

`pipeline/generation_pipeline.py` (Package_043, widened in Package_044)

- **`generate_model(image_path: str | Path | GenerationInput, catalog,
  palette, constraints=None, settings=None) -> GenerationResult`**. THE
  application entry point — UI, project management, automation, and the
  Package_050 Windows executable are all meant to call this rather than
  coordinating individual stages.
- **`GenerationResult`** (frozen): `scene`, `generation_input`,
  `validation_report` (the *final* report, after the repair loop settles —
  may still legitimately name deferred issues), `scene_analysis`,
  `repair_iterations`. Deliberately excludes anything the caller already
  owns (`constraints`, `catalog`, `palette` are never echoed back).
- Sequence: `GenerationInput.from_source()` (skipped entirely if a
  `GenerationInput` is passed directly — see §2.14) → `generate_scene()` →
  `optimize_scene()` → `validate_scene()` → `[repair_scene() →
  validate_scene()]*` until the Scene stops changing (compared via a
  private `_scene_signature()` helper, not `ValidationReport` contents —
  every current repair rule is provably monotonic, so this always
  terminates) → `analyze_scene()`.
- A defensive `_MAX_REPAIR_ITERATIONS = 10` safety cap exists but is never
  expected to trigger.
- **No exception wrapping**: `FileNotFoundError`/`ValueError` propagate
  completely unchanged from the stages it calls — this project has
  consistently rejected wrapping already-informative exceptions.
- Performs none of the six stages' own work — pure coordination.

## 2.14 Application Integration layer

`ui/main_window.py`, `ui/toolbar.py`, `ui/widgets/image_preview_widget.py`,
`ui/widgets/properties_widget.py`, `project/project_manager.py`
(Packages 044–048)

This is where the deterministic backend meets the actual application for the
first time.

- **Generation (Package_044)**: `ImagePreviewWidget` gained a **second,
  independent** "Generate (New Pipeline)" button/signal
  (`generate_model_requested`), deliberately *not* folded into the existing
  mode dropdown (the `GenerationMode`/`SettingsPanel` protocol doesn't fit
  `generate_model()`'s shape). `MainWindow.on_generate_model(generation_input)`
  builds a `PaletteEngine` the same way the legacy handler does, reads
  `Project.generation_constraints` (dormant since Package_036, now actually
  respected), calls `generate_model()`, and updates the Scene/Project/status
  bar through the exact same `set_current_scene()`/`mark_dirty()` calls the
  legacy path already used.
- **`generate_model()`'s signature widened** to accept an already-built
  `GenerationInput` directly (`str | Path | GenerationInput`) — found during
  Package_044's inspection that `ImagePreviewWidget.import_image()` already
  builds a complete `GenerationInput` at import time, well before generation
  is requested; passing only a path would force a redundant second
  load+prepare+analyze pass. Package_043 had explicitly deferred this exact
  widening pending a real, evidenced consumer — this is that consumer.
- **Export (Package_045)**: a new "Export Model..." File menu action wired
  to `on_export_model()` (file dialog, cancellation, `.ldr` extension
  normalization) → `_export_model_to(path)` (`export_scene()` call inside
  `try/except OSError`, status message). Mirrors `on_save_project_as()`/
  `_save_project_to()`'s existing shape exactly. **`export_scene()` and
  `Project` needed zero changes** — confirmed via `git diff --stat`, the
  clean contrasting case to the generation widening above.
- **A user can now complete Import Image → Generate Model → Export Model
  entirely through the new deterministic pipeline** — verified directly with
  an end-to-end test chaining the real `on_generate_model()` into the real
  `_export_model_to()`.
- `Project.generation_constraints` is respected but still has **no UI
  control** to set it — a real, open gap for a future package.
- First-ever test coverage for `ui/` was added across these two packages,
  using a **duck-typed `MainWindow` stand-in** pattern: a lightweight object
  carrying only the attributes a handler actually touches, with the real
  unbound methods bound onto it via `SomeMethod.__get__(fake_self)` — not a
  live `MainWindow` instance, which does real, slow setup (a real catalog
  scan, a real OpenGL viewport) this pattern deliberately avoids. Every
  package below reuses and extends this same pattern rather than inventing
  a new one.
- **Workflow Polish (Package_046)**: the first package scoped purely as
  UI-friction cleanup, not new capability. The two Generate buttons gained
  bold section captions ("Standard Pipeline (Recommended)" /
  "Legacy Generation") and tooltips distinguishing them; Undo/Redo went
  from silently wired-to-nothing to explicitly `setEnabled(False)`; an
  Export toolbar button was added beside Save; viewport brick selection
  was wired into `PropertiesWidget` for the first time (previously only
  Brick Library selection populated it); a `"BrickForge Ready"` vs.
  `"StudWorks"` branding drift was fixed; `MainWindow._refresh_window_title()`
  was introduced, showing `"{project.name}{'*' if dirty} — {window_title()}"`,
  called explicitly at the end of every handler that changes project/dirty
  state (not from `set_current_scene()` itself — several callers mark dirty
  *after* calling it, so refreshing there would always show stale state).
  Introduced the "UI Readiness Review" as a standing deliverable: an
  explicit first-time-user walkthrough performed after implementation.
- **Final Application Integration Review (Package_047)**: closed the
  Application Integration phase. Added keyboard shortcuts (`Ctrl+N/O/S`,
  `Ctrl+Shift+S`, `Ctrl+E`, `Ctrl+D` on the menu `QAction`s only — the
  toolbar's separate `QAction` instances for the same operations
  deliberately carry none, since two enabled `QAction`s sharing an
  identical shortcut in the same window is ambiguous to Qt and neither
  fires; Undo/Redo are the one exception, since they have no menu
  equivalent to collide with). Extracted `MainWindow._resolve_ldraw_library()`,
  deduplicating a guard `on_generate_lego()`/`on_generate_model()` had
  both carried verbatim, and gave `on_generate_lego()` its first-ever test
  coverage in the process. Removed confirmed-dead code: `models/brick.py`/
  `services/brick_database.py` (a pre-`PartCatalog` prototype whose own
  docstring called itself "Temporary"), the empty `ui/dialogs/`/`ui/icons/`
  scaffolding packages, and a stray empty nested file. Introduced a formal
  per-finding disposition table (every inspection finding ends in exactly
  one of Implemented/Deferred+owner/Already Resolved) as a standing
  practice for phase-closing packages.
- **Data Integrity & Application Lifecycle (Package_048)**, first package
  of Release Preparation: found and fixed the single most severe risk in
  the app's history — `MainWindow` had **no `closeEvent()` override at
  all**, so the window's own X button/Alt+F4 discarded unsaved work with
  zero warning. Fixed with one shared `_confirm_discard_unsaved_changes()`
  gate (`QMessageBox.question()`: Save/Discard/Cancel) reused by
  `closeEvent()`, `on_new_project()`, and `on_open_project()` alike — the
  gate reuses the *existing* `on_save_project()` rather than duplicating
  its "no path yet → Save As → possibly canceled" handling a second time.
  A File > Exit action (`Ctrl+Q`) reuses the same guarded `closeEvent()`
  for free via `self.close()`. Also fixed two bugs found by inspection, not
  assumed from the mission: `ProjectManager.save()` previously committed
  `file_path` *before* attempting the write (a failed write left it
  pointing at a location never actually written); and `Project.name`
  never updated anywhere in the save path, so a project saved as
  `"MyModel.sws"` permanently showed `"Untitled Project"` in the window
  title, status messages, and the next Save-As dialog's own default
  filename. The name-derivation fix deliberately lives in
  `on_save_project_as()`, **not** inside `ProjectManager.save()` itself —
  `tests/test_project_serialization.py`'s golden-file tests call `save()`
  directly with a `Project.name` that intentionally does *not* match the
  save path, to prove serialization is filename-independent; deriving the
  name inside `save()` would have broken those two passing tests. Verified
  by re-running that suite directly both before and after the change, not
  just reasoning about it.

## 2.15 Rendering

`render/renderer.py`, `render/camera.py`, `render/mesh.py`,
`render/picking.py`, `render/color_resolver.py`, `engine/brick_manager.py`,
`ldraw/` package

- **`Renderer`**: owns GL state, `Camera`, `Shader`, `Grid`, the current
  `Scene` reference, and `BrickManager`. Draws via
  `BrickManager.renderables(scene)`. `set_scene()`, `set_selected_id()`,
  `set_preview(ScenePreview | None)` (generic, tool-agnostic preview
  mechanism), `pick()` (CPU ray-AABB picking).
- **Known, unfixed bug**: LDraw geometry renders upside-down (LDraw's
  native Y-down convention vs. the renderer's Y-up assumption) — surfaced
  during Package_024, never fixed, still outstanding.
- **`BrickManager`**: owns `LDrawLibrary` + a per-part GPU `Mesh` cache +
  `aabb_for(part_name)` (lazy, computed in the same pass as the mesh, from
  *real* geometry — this is a **different, independent** AABB source from
  the pipeline layers' catalog-declared-dimension AABBs in §2.10/§2.11;
  `BrickManager`'s is sometimes `None` when geometry doesn't resolve, the
  pipeline layers' is always present but sometimes placeholder).
- **`ColorResolver`**: resolves `SceneBrick.color_code` → `ResolvedColor`
  (RGB) for shaders. Lookup only, never touches geometry or color matching.
- **Selection** (`selection/selection_manager.py`, Package_027):
  `SelectionManager.select(id)`/`clear()`/`selected_id()`, backed by CPU
  ray-AABB picking in `render/picking.py`.

## 2.16 Editing Tools

`transform/scene_transform.py`, `tools/`, Packages 027–033

- **`transform/scene_transform.py`**: `replace_brick(scene, updated_brick)
  -> Scene`, `remove_brick(scene, brick_id) -> Scene`, `duplicate_brick(scene,
  brick_id) -> tuple[Scene, int]`. All immutable (build a fresh `Scene`),
  raise `TransformError` if the target id doesn't exist. This is the
  foundational, shared editing-primitive layer — reused directly by Scene
  Repair (§2.12), not duplicated.
- **`ActiveToolManager`** (`tools/active_tool_manager.py`, Package_031):
  centralizes mouse-button dispatch; `ToolResult(brick_id, verb, field,
  value, is_removal)` unifies Move/Rotate/Delete into one `MainWindow`
  handler.
- **`MoveTool`/`RotateTool`**: deliberately no shared base class — genuinely
  different input shapes (world-space drag vs. screen-space angle). Bound to
  Left-drag / Right-drag / Middle-click (Delete) / Edit-menu action
  (Duplicate — no mouse button left to claim).

## 2.17 Persistence (Project save/load)

`project/project.py`, `project/project_manager.py`,
`serialization/schema.py`, `serialization/serializer.py`,
`serialization/deserializer.py` (Packages 025/026, extended 034/036)

- **`Project`** (deliberately **mutable**, unlike every newer domain type):
  `name`, `file_path`, `scene`, `generation_input: GenerationInput | None`,
  `generation_constraints: GenerationConstraints | None`, `created`,
  `modified`, `dirty`, `app_version`. `mark_dirty()`/`mark_saved()` mutate in
  place. `to_dict()`/`from_dict()` embed a native Scene JSON document
  (`scene_to_document()`/`document_to_scene()`) inside the Project's own
  document, with independent format/schema identifiers for each layer.
- **Why `Project` stays mutable**: this was directly, rigorously evaluated
  during Package_044's planning. Real, already-working `MainWindow` code
  mutates `Project` at 8+ call sites (`mark_dirty()` alone at 5+ sites,
  direct field assignment elsewhere). Converting it to an immutable
  `frozen=True` dataclass would provably break that code. A proposed
  alternative immutable wrapper type (`GenerationProject`) was designed,
  then **canceled** after rigorous review found `GenerationResult`
  (§2.13) already served that purpose and `Project` already owned every
  artifact the wrapper would have re-held — see §4's Package_044 entry.
- **`ProjectManager`**: `current_project`, `new_project()`, `save(path)`,
  `load(path)`. Owns file I/O. Currently a **module-level singleton** in
  `ui/toolbar.py` — a known architectural smell, not yet addressed (§7).
- **Serialization doctrine, established and never violated since**: store
  only what's needed to *regenerate* expensive/derived data
  (`generation_input` stores a reference and regenerates `prepared_image`/
  `analysis` on load, since `GenerationInput.from_source()` is
  deterministic); store plain user intent verbatim
  (`generation_constraints`, nothing to regenerate); **never** store
  `ValidationReport`/`SceneAnalysisResult`/`GenerationResult` at all — they
  are cheap, pure, deterministic functions of `(Scene, catalog)`, so a future
  UI can always re-derive them on demand rather than persisting a stale
  snapshot.
- Golden-file, byte-for-byte regression testing (fixed timestamps, zero
  normalization) was established here and reused for export (§2.18) and
  every subsequent serialization-adjacent test.

## 2.18 Export

`export/exporter.py`, `export/ldraw_writer.py` (Package_024)

- **`export_scene(scene, catalog, path) -> None`**: writes a `.ldr` file
  BrickLink Studio can open. Raises `OSError` unwrapped on write failure;
  never raises over per-brick data (an unrecognized part is written anyway,
  with a logged warning — export never produces an incomplete model just
  because the local catalog is missing metadata for a part that may be
  perfectly valid in BrickLink's own library). Deterministic (Scene's own
  existing order). Empty Scene handled gracefully — a valid, minimal
  (header-only) file, no special-casing required anywhere.
- `write_ldraw_file()`/`format_type1_line()`/`rotation_to_ldraw_matrix()`:
  low-level LDraw text formatting; the quaternion → LDraw row-major 3×3
  matrix conversion was verified empirically against a known 90°-rotation
  case.
- **Confirmed (Package_045) to already be the correct long-term API** — no
  changes were needed to integrate it with the application; every parameter
  it needs was already available on `MainWindow` in exactly the right shape.

---

# 3. Package History

Every completed package, in order. Commit hashes verified directly via
`git log`. Earlier packages (pre-034) are summarized more briefly; this
session's own packages (034–045) carry the full architectural reasoning,
since that reasoning is the primary value of this document.

## Foundational packages (pre-numbered → Package_017)

Core rendering/scene-graph bring-up: `Scene`/`SceneBrick`/`BrickManager`/
`Renderer` architecture, LDraw parsing (including recursive Type-1 subfile
resolution), multi-brick rendering, `BrickDefinition` catalog foundation,
Image Foundation (`ImageResource`/`ImageLoader`/`ImageManager`), the first
deterministic Palette Engine and Mosaic Generator, `ColorResolver`, real
LDraw library detection replacing the seed-only catalog, and the
`GenerationMode` registry (Package_017 migrated the generation UI onto it).
Key early commits: `27db5c27` (Scene/BrickManager/SceneBrick architecture),
`4322c876` (recursive subfile resolution), `c109eef9` (BrickDefinition
catalog), `1afa7131` (Palette Engine), `27e4e66b` (Mosaic Generator),
`45206788` (real LDraw detection), `6b0c577f` (GenerationMode registry),
`4de92b1d` (Package_017).

## Package_018 — Image Preparation Pipeline (`68a573ad`)
Shared, mode-agnostic image prep stage (fit-to-`max_dimension` originally);
later extended with crop/rotate in Package_034.

## Package_019 — Height Relief Generator (`c065c3d6`)
Second `GenerationMode`: 3D stacked height-map generation. Validated that
the registry/UI/preparation architecture needed no changes to support a
genuinely different Scene shape (variable bricks per pixel, variable Y).

## Package_020 / 020.5 / 021 / 022 — Optimization Pipeline (`ce06d785`,
`f893d82b`, `779af9b0`, `c5c41f1d`, `a3bc9688`, `d9bc8aad`)
Designed the shared `Optimizer`/`optimize_scene()` architecture; built Brick
Merge (catalog-driven, no hardcoded part table) and Hidden Brick Removal.
Package_020.5 was the first distributable Windows Preview build. This
subsystem then sat **fully built but with zero production callers** for
years of roadmap time, until Package_039 finally integrated it.

## Package_023 — Catalog Cache (`6df4dd55`)
Two-layer `PartCatalog` caching. Found and fixed a real bug: the catalog was
being built *twice* per startup, not once.

## Package_024 — Studio Export (`9b2f2afd`, amended `3d653c4f`)
First `.ldr` export system. Surfaced (but didn't fix) the renderer's
upside-down LDraw rendering bug. Established golden-file byte-for-byte
regression testing.

## Package_025 — Scene Serialization (`6ae903d9`)
Native Scene JSON format. Roadmap had drifted here from an originally
planned "Cost Estimation" package — the first of several roadmap redirects.

## Package_026 — Project Save/Load (`7a13771e`)
`Project`/`ProjectManager`, `.sws` files. Found pre-existing half-built
infrastructure and a `.gitignore` collision (bare `projects/` rule silently
excluding golden test fixtures).

## Package_027 — Selection System (`cdc74182`)
`SelectionManager` + CPU ray-AABB picking (`render/picking.py`).

## Package_028 — Transform System (`b4ea29da`)
`transform/scene_transform.py`'s immutable `replace_brick()`. Introduced
`MainWindow.set_current_scene()`, the centralizing helper every Scene
replacement still goes through today.

## Package_029 / 030 / 031 / 032 / 033 — Editing Tools
Move (`8cff78c9`), Rotate (`cf968f00`), Active Tool Framework centralizing
mouse dispatch (`797d3bfa`), Delete (`962b1c33`), Duplicate (`17c3a500` —
the first Transform function returning more than a `Scene`). After
Package_033, the user explicitly pivoted the roadmap: the editing
foundation was declared sufficient; Undo/Redo was deferred (not canceled);
the next objective became the generation pipeline.

## Package_034 — Generation Input System (`dd675072`)
First package of the pivoted roadmap. `GenerationInput`, crop/rotate added
to `prepare_image()`, a real EXIF-orientation bug found and fixed against
hand-constructed EXIF bytes, `Project.generation_input` with
regenerate-not-store serialization.

## Package_035 — Image Analysis (`b95fa7e7`)
`ImageStatistics` → `ImageAnalysisResult` (zero prior consumers, confirmed
via grep — a risk-free rename). Added `dominant_colors`/`occupied_bounds`/
Sobel `edges`. Bundled into `GenerationInput.analysis` with zero new
`Project` serialization code.

## Package_036 — Generation Candidate System (`eac8d599`)
`GenerationConstraints` + `candidates_for()` over the existing
`PartCatalog`. Found the real catalog's metadata (color/category/family)
is uniform placeholders outside the 9-part seed catalog — the finding that
directly motivated Package_037.

## Package_037 — Brick Catalog Enrichment (`e6163ef6`)
Three independent pure helpers derive stud footprint/height/category from
real geometry/header data when confidently validated; real coverage
31.9%/23.2% respectively. Caught two wrong hypotheses empirically before
shipping (naive height-from-geometry was off by exactly the LEGO stud
height; description-based category guessing matched only 3/488 real
cases). `CACHE_SCHEMA_VERSION` bumped and verified against this machine's
actual pre-existing stale cache.

## Package_038 — First Generation Engine (`3865739a`)
`generate_scene()`. Isolated `select_generation_brick()` as a replaceable
policy hook. Used `Scene.next_available_id()` (user-corrected from an
earlier `row*width+col` plan). Dominant-color placement made
`ImageAnalysisResult` finally load-bearing.

## Package_039 — Scene Optimization Integration (`4ba92b25`)
Discovered Packages 020–022's optimizer already existed, fully built, with
zero callers. Extended `OptimizeCallable` with `GenerationConstraints`;
refactored Brick Merge to use `candidates_for()`; verified backward
compatibility against a real, pre-existing golden file.

## Package_040 — Build Validation (`b8e53d89`)
`validate_scene()`. Four independent pure rules; honest `ERROR`/`WARNING`
tied to catalog confidence; rotation-aware overlap AABB verified
zero-false-positive against real generated Scenes.

## Package_041 — Scene Analysis (`c7764bfb`)
`analyze_scene()`. Describes, never judges. `SceneMeasurements`/
`SceneSummaries` structural split. Independently reimplemented Package_040's
bounds geometry to preserve pipeline-stage independence.

## Package_042 — Scene Repair (`18122c4e`)
`repair_scene()`. Found and fixed a real `next_available_id()` bug
*before* writing production code. Duplicate-id gating makes repair
re-entrant. Deliberately reused `transform/` primitives — the first,
justified exception to pipeline-stage independence.

## Package_043 — Generation Pipeline Orchestrator (`5da30188`)
`generate_model()`, the canonical entry point coordinating all six backend
stages. Repair loop stops on Scene stability, not report cleanliness —
a proven, correctness-driven distinction, not a style choice.

## Package_044 — Generation Pipeline UI Integration (`f1cc5475`)
Two re-scopings in one package, both worth remembering as a pattern:
1. A first-draft immutable `GenerationProject` wrapper type was **canceled**
   after rigorous review found `GenerationResult`/`Project` already
   sufficient — see §7's "questions already answered" note.
2. A literal "replace the legacy generation path" reading was **rejected**
   in favor of an **additive** second button, after finding Height Relief
   and Flat Mosaic's manual part selection have no equivalent in the new
   pipeline — replacing the legacy path would have been a real regression.
`generate_model()` was widened to accept a pre-built `GenerationInput`
directly — a genuinely evidence-driven API change (Package_043 had
explicitly deferred this pending a real consumer; this package found one).
First test coverage for anything in `ui/`.

## Package_045 — Export UI Integration (`77d84d23`)
Gave `export_scene()` its first application caller. The clean contrasting
case to Package_044: inspection found **no** API mismatch and **no**
backend/`Project` changes needed at all — confirmed, not just predicted.
Completes Import → Generate → Export end to end, verified with a real
chained test. Introduced the "Inspection Predictions" report format
(§6) as permanent practice.

## Package_046 — Generation Workflow Polish (`4228ea02`)
First package scoped purely as UI-friction cleanup, not new capability.
Distinguished the two Generate buttons (captions/tooltips), disabled
(not silently no-op) Undo/Redo, added an Export toolbar button, wired
viewport brick selection into `PropertiesWidget` for the first time,
fixed a "BrickForge"/"StudWorks" branding drift, added a window-title
dirty-state indicator. Introduced the "UI Readiness Review" as a
standing post-implementation deliverable.

## Package_047 — Final Application Integration Review (`ca6840a4`)
Closed the Application Integration phase. Keyboard shortcuts, a
deduplicated `_resolve_ldraw_library()` helper (giving `on_generate_lego()`
its first-ever test coverage), a status-message grammar fix, a
`PropertiesWidget` empty-state follow-through, and removal of
confirmed-dead code (an orphaned pre-`PartCatalog` prototype, empty
`ui/dialogs`/`ui/icons` scaffolding, a stray empty file). Introduced a
formal per-finding disposition table (every inspection finding ends in
exactly one of Implemented/Deferred+owner/Already Resolved).

## Package_048 — Data Integrity & Application Lifecycle (`efac418b`)
First package of Release Preparation. Found and fixed the most severe
data-loss risk in the app's history: no `closeEvent()` guard at all,
so the window's own close button discarded unsaved work with zero
warning. One shared `_confirm_discard_unsaved_changes()` gate now
covers New, Open, and window-close together. Also fixed a
`ProjectManager.save()` ordering bug (`file_path` was committed before
the write succeeded) and a `Project.name` bug (never updated on Save
As, permanently showing "Untitled Project" regardless of the real
filename) — the latter fixed in the UI layer specifically to avoid
breaking `test_project_serialization.py`'s golden-file tests, which
rely on `ProjectManager.save()` staying filename-independent.

---

# 4. Current Roadmap

**Phase structure** (introduced explicitly during Packages 044/045):

| Phase | Packages | Status |
|---|---|---|
| Application Integration | 044, 045, 046, 047 | ✓ **complete** |
| Release Preparation | 048, 049 | 048 ✓, 049 **in progress** |
| Preview Release | 050 (Windows Preview) | not started |

**Application Integration is complete** (044-047): a user can complete the
full **Import Image → Generate Model → Export Model** journey through the
new deterministic pipeline (044/045), the workflow itself is legible to a
first-time user — labeled generation paths, working viewport-selection
feedback, accurate branding/title state, no silently-broken toolbar
controls (046), and keyboard shortcuts/deduplicated generation guard/dead
code removal closed out the phase (047).

**Release Preparation is in progress** (048-049). Package_048 fixed the
data-integrity risks found by inspecting the application's lifecycle (see
§2.14's Package_048 entry) — most notably an unguarded window close that
discarded unsaved work with zero warning. Package_049 (Release Candidate
Validation) is a documentation/consistency/cleanup pass with no
architecture changes — this document's own refresh is part of it.

**Deferred, with explicit ownership, not silently dropped**:
- A `GenerationConstraints`-editing settings panel (the backend already
  reads and respects `Project.generation_constraints`; no UI sets it) —
  unassigned, a candidate for whenever it's actually requested.
- Eventual legacy generation path retirement (a deliberate product decision,
  not yet made — would need `generate_model()` to first gain multi-algorithm
  support or manual part override to avoid the regression Package_044
  identified) — unassigned.
- External metadata integration (BrickLink/Rebrickable) to close the
  `available_colors`/`family` gap (§2.2) — unassigned.
- Delete-key support in the viewport, and an unsaved-changes-aware New/Open
  guard's *edge cases beyond what Package_048 already covers* — both
  explicitly assigned to Package_048 by Package_047's own handoff; the
  unsaved-changes guard was in fact delivered by Package_048. Delete-key
  support (a genuinely new input pathway, not a polish of an existing
  trigger) remains open — Package_047 assigned it to "Package_048," but
  Package_048's actual mission was data integrity, not input handling; this
  should be re-assigned explicitly (Release Preparation continuation or
  Package_050) rather than assumed still pending in 048.
- `src/brickforge/__main__.py` is still corrupted (contains literal
  shell-command text, not Python) — flagged since Package_046, still
  unresolved as of Package_049's own re-check. Does not block packaging
  (`StudWorks.spec`'s entry point is `src/main.py` directly), but breaks
  `python -m brickforge` for anyone running from source. Tracked
  separately, not phase-numbered; needs a definitive resolution before
  Release Preparation is considered fully closed.
- CI (a GitHub Actions workflow running the regression suite automatically)
  was evaluated during Package_049 and explicitly deferred past the
  Preview Release, not overlooked.

**Package_050 (Windows Preview Release) goals**, as named across recent
package missions: a distributable Windows build demonstrating the complete,
working application — Import → Generate → Export is the core journey it
needs to support, architecturally complete since Package_045 and now safe
for a first-time user since Package_048. Packaging mechanics themselves
remain fully unaddressed — `StudWorks.spec`/`packaging/version_info.txt`/
`scripts/build.ps1` all exist and are internally consistent (verified
during Package_049), but no package has yet actually run and validated a
full build.

---

# 5. Architectural Principles

These are the rules that have actually governed decisions throughout this
project's history, not aspirational statements.

1. **Inspection before implementation.** Every package begins in an explicit
   "INSPECTION AND PLANNING MODE ONLY" phase: read the real, current code
   (never assume), verify tricky behavior empirically (small Bash scripts
   testing library/math/framework behavior before committing to a design),
   produce a structured plan, and wait for explicit approval before touching
   any file.
2. **Evidence-driven architecture, never speculative.** Recommendations are
   grounded in what was actually found by reading code and running
   verification scripts — not assumption, not "seems reasonable." Multiple
   packages (037, 038, 040, 042) found and fixed real bugs, or caught wrong
   hypotheses, purely through this discipline, before any production code
   existed.
3. **APIs evolve only when a real, inspected workflow demonstrates the
   need — never speculatively.** Package_043 deliberately declined to widen
   `generate_model()`'s signature with zero evidence of a real caller;
   Package_044 widened it once inspection found the actual UI already held a
   `GenerationInput` before generation was requested. Package_045's
   `export_scene()` needed no such change because no such gap existed — both
   outcomes are correct applications of the same rule.
4. **Preserve subsystem/pipeline-stage ownership and independence.** Each
   stage (generation, optimization, validation, analysis, repair) does
   exactly one thing and stays decoupled from its siblings — small constants
   and geometry helpers are *deliberately* duplicated across stages rather
   than shared, to avoid cross-stage coupling. `transform/` being reused by
   Scene Repair is the one considered, justified exception (§2.12), because
   it's a foundational shared layer, not a peer stage.
5. **Prefer integration over redesign, especially during Application
   Integration.** Connect existing subsystems; don't rebuild them. Both
   Package_044 and 045 confirmed the existing `Project`/backend APIs were
   already correct and left them completely unchanged.
6. **Inspection findings override roadmap assumptions.** When evidence
   contradicts a package's own mission framing, say so and recommend a
   different path — including canceling or re-scoping a package entirely
   (Package_044's `GenerationProject` cancellation; its "additive, not
   replacement" re-scoping).
7. **Reuse immutable domain objects; keep exactly one type intentionally
   mutable.** `Scene`, `GenerationInput`, `GenerationConstraints`,
   `ValidationReport`, `SceneAnalysisResult`, and `GenerationResult` are all
   immutable (by convention or `frozen=True`). `Project` is the one
   deliberate exception, because real UI code depends on in-place mutation
   and converting it would break working functionality for no evidenced
   benefit.
8. **Maintain scope isolation, and prove it.** After every implementation,
   `git diff --stat` confirms only the intended files changed, and an
   AST-based import check confirms no unintended new coupling was
   introduced. This is done every single package, not spot-checked.
9. **Regression is required after every package.** The full test suite is
   re-run and must pass 100% before any commit — currently 429 tests. No
   automated CI runs this yet (evaluated and explicitly deferred past the
   Preview Release during Package_049) — it is enforced by this discipline
   alone, not by tooling.
10. **"Unknown" is a valid, preferred outcome over guessing.** Validation
    and Repair both use conservative thresholds and explicitly leave data
    unrepaired/unjudged rather than approximate — an honest gap beats a
    confident wrong answer.
11. **Never fabricate results.** When a tool or credential is genuinely
    unavailable (e.g., no `gh` CLI, no authenticated GitHub session for PR
    creation), that limitation is reported honestly with a concrete
    workaround for the user, never faked.
12. **Commits stay scoped to the active package.** Only the package's own
    files are staged, always excluding pre-existing, unrelated diffs
    (`.vscode/settings.json`, `docs/ARCHITECTURE.md` — both left alone
    throughout this entire project's history at the user's original
    direction).
13. **Document *why*, not just *what*.** Every `Package_XXX.md` captures
    inspection findings, the reasoning behind design choices, and explicitly
    deferred/rejected alternatives — this document (`docs/HANDOFF.md`)
    exists for the same reason, at a project-wide scope.

---

# 6. Standard Package Report Format

Every completed package produces a report with these sections (introduced
progressively; the full 12-part form has been standard since Package_045):

1. **Files Modified**
2. **Architecture Summary** — what was built and why, referencing the
   approved inspection
3. **Feature Summary** — what capability now exists
4. **Public API Summary** — new or changed public functions/types; explicit
   confirmation when *no* API changed
5. **Inspection Prediction Results** — for each major claim made during
   planning, explicitly mark ✓ Confirmed / ⚠ Partially Confirmed /
   ✗ Refuted with a brief explanation; if anything is refuted, explain what
   was discovered, why the inspection was wrong, and whether architectural
   guidance should change
6. **Test Summary**
7. **Regression Results** — full suite pass count (pre-existing + new)
8. **Scope Isolation Confirmation** — `git diff --stat` proof that only
   intended files changed
9. **Project Phase Status** — current phase, completed/remaining packages
10. **Secondary Architectural Observations** — anything noticed beyond the
    immediate scope worth recording
11. **Lessons Learned** — durable takeaways for future packages
12. **Commit Hash**

---

# 7. Known Technical Debt

- **Renderer's LDraw geometry renders upside-down** (Y-down native LDraw
  convention vs. the renderer's Y-up assumption). Surfaced Package_024,
  never fixed, still outstanding. Does not affect any backend pipeline
  stage — purely a rendering-layer display issue.
- **`ui/toolbar.py`'s module-level `project_manager` singleton.** Flagged as
  an architectural smell since Package_026; never restructured.
- **Undo/Redo toolbar buttons are correctly disabled (Package_046), not
  wired to anything (still true).** Actually implementing Undo/Redo itself
  remains deferred since the Package_033-era roadmap pivot toward the
  generation pipeline; not revisited since. They do have standard shortcuts
  (`Ctrl+Z`/`Ctrl+Y`, Package_047) that simply never fire while disabled.
- **No Delete-key support in the viewport** — Delete is Middle-click only.
  Flagged during Package_047's inspection (F10), assigned to "Package_048"
  by that package's own handoff, but Package_048's actual mission was data
  integrity, not input handling, so this was never actually picked up.
  Needs explicit re-assignment (Release Preparation continuation or
  Package_050), not assumed still pending in 048.
- **`src/brickforge/__main__.py` is still corrupted** (contains literal
  shell-command text, not Python) — flagged since Package_046 (F11),
  re-confirmed broken as of Package_049. Doesn't block packaging
  (`StudWorks.spec` uses `src/main.py` directly), but breaks
  `python -m brickforge` for anyone running from source. A background task
  was spun off to fix this after Package_046 and ended with zero trace in
  this repo (no new commit, branch, or reachable worktree change) — don't
  assume it's handled without checking directly.
- **No CI.** `.github/` exists but is empty — the 429-test regression suite
  runs only when manually invoked. Evaluated and explicitly deferred past
  the Preview Release during Package_049, not overlooked.
- **`available_colors`/`family` catalog metadata gap.** No LDraw-native
  source exists for either (confirmed, Package_037) — every real,
  non-seed-catalog part has empty `available_colors` and unset `family`.
  Closing this needs an external data source (BrickLink/Rebrickable) that
  doesn't exist in this codebase yet.
- **Most real catalog parts still have placeholder dimensional metadata.**
  Only 31.9%/54%(approx.)/23.2% of real parts get genuinely-derived stud
  footprint/height/category respectively (Package_037's measured
  coverage) — the rest fall back to `1×1×24.0, category="Part"`.
- **`GenerationConstraints` has no UI.** The field on `Project` is read and
  respected by `on_generate_model()` (Package_044), but nothing lets a user
  set it yet.
- **Two parallel generation paths coexist in the UI, by design, for now.**
  The legacy `GenerationMode` path (Flat Mosaic + Height Relief) and the new
  `generate_model()` path both work. Consolidating or retiring the legacy
  path is an open, deliberate future product decision — not a bug.
- **No stud/tube connectivity data exists anywhere in this codebase.**
  Blocks any real disconnected-component validation or repair, permanently,
  until an external data source is integrated. A geometric-adjacency proxy
  was explicitly considered and rejected as an unsupported approximation.
- **`overlapping_bricks` has no automatic repair**, and may never get one
  without additional data — there is no deterministic way to choose which
  of two overlapping bricks should move, or where, without altering the
  represented model.
- **`BrickManager.aabb_for()` (render-layer, real-geometry-based) and the
  pipeline layers' world-AABB derivation (catalog-declared-dimension-based)
  are two independent, differently-sourced AABB concepts** — this is
  intentional (§2.15/§2.10/§2.11), but worth remembering so the two are
  never conflated.

---

# 8. Testing Strategy

- **Philosophy**: verify empirically before committing to a design (small,
  throwaway Bash scripts probing real library/math/framework behavior),
  then write permanent, committed tests proving the same thing — never
  assume behavior, especially for anything involving floating-point math,
  Qt/PySide6 behavior, or numpy/PyGLM conventions.
- **Regression is mandatory, not optional.** The full suite (429 tests as of
  Package_048) is re-run before every commit and must pass completely.
- **Scope isolation is verified, not assumed.** `git diff --stat` after
  every implementation confirms only the intended files changed; an
  AST-based import check confirms no unintended new module coupling was
  introduced.
- **Golden-file, byte-for-byte regression testing** (fixed timestamps, zero
  normalization) is used for anything serialization- or export-shaped —
  established in Package_024/025, still the pattern for
  `test_export_golden_files.py` and `test_project_serialization.py`.
- **UI testing uses duck-typed stand-ins, not live windows.** A real
  `MainWindow` does expensive, potentially fragile setup (a real
  `PartCatalog` scan, a real OpenGL viewport). Tests instead build a
  lightweight object carrying only the attributes a handler touches, with
  the real unbound methods from `MainWindow` bound onto it via
  `SomeMethod.__get__(fake_self)` — this exercises actual production code,
  not a reimplementation.
- **`unittest.mock.patch` is used to inject controlled or deliberately
  broken state through real production code paths** (e.g., Package_043's
  repair-loop tests patch `optimize_scene`'s return value to inject a
  hand-built broken Scene) rather than duplicating pipeline logic separately
  inside a test.
- **Inspection Prediction reporting** (introduced Package_045, now
  standard): every completion report explicitly re-examines each major
  claim made during planning against what implementation actually found,
  rather than only reporting whether tests passed. This has already once
  surfaced a genuine implementation-time discovery worth escalating (see
  Package_042's `next_available_id()` finding, though that was caught
  *during planning* rather than after — the format exists specifically to
  catch cases where it's caught *after*, honestly).

---

# 9. Most Recently Completed Package (048) — Full Detail

**Package_048 — Data Integrity & Application Lifecycle** (commit `efac418b`)

- **Inspection findings**: `MainWindow` had no `closeEvent()` override at
  all — the window's X button/Alt+F4 (the app's only quit path; there was
  no File > Exit either) discarded unsaved work with zero warning, the
  single most severe risk found in the app's whole history. `New`/`Open`
  had the same gap (carried over as F12 from Packages 046/047). Separately,
  `ProjectManager.save()` committed `file_path` before the write succeeded,
  and `Project.name` never updated anywhere in the save path (permanently
  "Untitled Project" regardless of the real filename).
- **Approved architecture**: one shared `_confirm_discard_unsaved_changes()`
  gate (`QMessageBox.question()`: Save/Discard/Cancel) reused by
  `closeEvent()`, `on_new_project()`, and `on_open_project()` — it reuses
  the *existing* `on_save_project()` rather than re-implementing its
  "no path yet → Save As → possibly canceled" handling. A File > Exit
  action reuses the same guarded `closeEvent()` via `self.close()`.
  `ProjectManager.save()` reordered (file_path/mark_saved only commit
  after a successful write). `Project.name` derivation moved to
  `on_save_project_as()` specifically, not into `ProjectManager.save()`
  itself, to avoid breaking `test_project_serialization.py`'s golden-file
  tests (which call `save()` directly with a name that intentionally
  doesn't match the path, to prove serialization is filename-independent).
- **Implementation scope**: `ui/main_window.py` and
  `project/project_manager.py` only. New test file
  `tests/test_ui_project_lifecycle.py` (16 tests).
- **Every inspection prediction was confirmed** — none refuted, none
  partial; the golden-file suite was re-run directly (not just reasoned
  about) both before and after the `ProjectManager.save()` change. Full
  detail in `Package_048.md`.

**Package_049 — Release Candidate Validation is in progress** (this
document's own refresh is part of it — see the commit this package
produces for its final hash). A documentation/consistency/cleanup pass:
fixed a factual misattribution in `README.md`, removed six empty doc
stubs and assorted empty/stale filesystem cruft, refreshed this document,
deduplicated a `.gitignore` line. No architecture changes. CI was
evaluated and explicitly deferred past the Preview Release.

**Package_050 (Windows Preview Release) has not been started.**

---

# 10. Next Steps

1. Confirm Package_049 has been committed (check `git log` for its commit
   hash and `Package_049.md`), then wait for the user to issue
   Package_050's mission specification, in the same "Begin Package_050 in
   INSPECTION AND PLANNING MODE ONLY" format every prior package has used.
2. Follow the established workflow exactly: inspect the real, current code
   (do not assume anything from this document is still accurate without
   re-checking anything that matters for the new package — this document is
   a snapshot as of Package_048/049, not a live source of truth for future
   state) → produce a structured plan matching whatever sections the
   mission requests → wait for explicit approval → implement → verify
   (compile, full regression suite, scope isolation, AST import check) →
   write `Package_050.md` (including Inspection Predictions) → commit,
   staging only the package's own files → update the auto-memory system.
3. Do not assume Package_050's content beyond what HANDOFF/roadmap already
   name as its goal (a distributable Windows build) — the actual packaging
   mechanics remain fully unaddressed as of Package_049, and Package_049's
   own inspection found `StudWorks.spec`/`packaging/version_info.txt`/
   `scripts/build.ps1` consistent but never yet validated by an actual
   package running a real build end to end.
4. Two carried-forward, unassigned items worth resolving before or during
   050, per Package_049's own review: `src/brickforge/__main__.py`'s
   corruption (open since Package_046, does not block packaging but breaks
   `python -m brickforge`), and Delete-key support in the viewport
   (Package_047's F10, never actually picked up by Package_048 despite
   that package's own handoff naming it — needs explicit re-assignment).

---

# 11. Context for the Next Claude Instance

You're picking up StudWorks (`brickforge` package, `C:\projects\BrickForge`,
git branch `develop`) right after Package_048 (with Package_049 having just
run as part of producing/updating this very document). Read this document
fully before doing anything else — it is written to be sufficient on its
own.

**Where things stand**: a complete, deterministic backend pipeline
(image → Scene, `generate_model()`) was built across Packages 034–043.
Packages 044–047 connected that backend to the actual application and then
polished the result into something legible to a first-time user — labeled
generation paths, working viewport-selection feedback, keyboard shortcuts,
no dead code, no silently-broken controls. Package_048 then closed the
data-integrity gap that mattered most for a public release: unsaved work
could previously vanish with zero warning from the single most common
action in any desktop app (closing the window). Package_049 was a
documentation/cleanup pass preparing for Package_050, the Windows Preview
Release itself, which has not yet started.

**The governing philosophy** is inspection-first, evidence-driven,
change-averse engineering: read the real code before proposing anything,
verify anything uncertain empirically, and only evolve an API or introduce
a new abstraction when a concretely inspected workflow demands it — never
speculatively. This project has repeatedly concluded that the
*architecturally correct* answer was to build *less* than what a literal
reading of a mission asked for (Package_044's canceled `GenerationProject`
wrapper; Package_048's name-derivation fix deliberately kept out of
`ProjectManager.save()` specifically because inspection found it would
break existing golden-file tests) — and said so explicitly rather than
forcing an implementation or silently working around the tension. That is
not a failure mode here; it is exactly what rigorous inspection is for, and
the user has consistently rewarded it.

**The development workflow, unchanged across 49 packages**: every package
begins with an explicit "INSPECTION AND PLANNING MODE ONLY" instruction —
no files are touched until a structured plan is presented and approved.
Implementation then proceeds in one continuous pass: build, test rigorously
(unit tests plus a full regression run — specifically re-run any existing
test suite a change could plausibly affect, not just reason about it, as
Package_048 did for the golden-file tests), verify scope isolation via
`git diff --stat` and an AST import check, write a `Package_XXX.md`
capturing *why* decisions were made (not just what changed), and commit —
staging only that package's own files, always excluding the pre-existing,
user-owned `.vscode/settings.json`/`docs/ARCHITECTURE.md` diffs. A
persistent memory system at
`C:\Users\mason\.claude\projects\C--projects-BrickForge\memory\` (index at
`MEMORY.md`) is updated after every package — read it, and specifically
check `upcoming_package_roadmap.md` for the latest phase/package status,
since it's updated more frequently than this document will be.

**What to do first**: confirm whether Package_049 has actually been
committed (this document may have been updated as part of that package's
own work before the commit landed — check `git log`). Package_050 has not
been specified. When the user provides it, treat this document as your
starting context — but re-verify anything you're about to build on by
reading the actual current source, the same discipline every prior package
has applied to everything before it. This document describes the state as
of Package_048/049; the codebase may have moved by the time you're reading
this if any work happened between then and now that this document wasn't
updated to reflect.
