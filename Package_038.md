# StudWorks

# Package 038

## Title

The First Generation Engine — From Analyzed Image to Immutable Scene

---

# Mission

Implement the first package that produces an actual LEGO model:
`generate_scene()` converts a `GenerationInput`'s analyzed image data
into a standard, immutable `Scene`, using only the existing Generation
Candidate System for part selection. No optimization occurs in this
package. Architectural correctness, determinism, and integration are
the goals — not generation quality.

---

# Scope

New:

- `generation/generation_engine.py` (`select_generation_brick()`,
  `_nearest_dominant_color()`, `generate_scene()`)

Tests:

- `tests/test_generation_engine.py` (new, 19 tests)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `transform/`, `serialization/`, `export/`, `project/`,
`ui/`, `services/`, `ldraw/`, `palette/`, `preparation/`, `analysis/`,
`models/`, and every other file already in `generation/`
(`mosaic_generator.py`, `height_relief_generator.py`, `registry.py`,
`generation_mode.py`, `candidates.py`). This package adds exactly one
new file.

---

# Inspection Findings

(Full detail in the approved planning turn.) `Scene`/`SceneBrick`,
`GenerationInput`, `ImageAnalysisResult`, and `candidates_for()` were
all already shaped correctly for this package — no changes needed to
any of them. `GenerationInput` bundles both `prepared_image` (per-pixel
access) and `analysis` (aggregate facts) from one `from_source()` call,
confirming the engine should take `GenerationInput` as a whole rather
than `ImageAnalysisResult` in isolation. `PaletteEngine` is a required,
caller-constructed dependency with no substitute (it's the only way to
produce a real LDraw `color_code`) and isn't part of the Candidate
System — a deliberate, explicitly-flagged departure from the mission's
literal pipeline diagram, approved in the planning turn. The existing
`GenerateCallable`/`GenerationMode` registry contract was confirmed
incompatible with "never bypass candidate queries" (both existing
generators call `catalog.get()` directly) and was correctly not reused.

---

# Architecture Summary

`generate_scene()` is a plain function (no class, matching every other
pipeline stage in this codebase), and per the approved architectural
requirements:

**Brick-selection policy is fully isolated.** `select_generation_brick(candidates)`
is a standalone, public, pure function — `generate_scene()` calls it and
uses the result without knowing why that part was chosen. Today's
policy (smallest stud footprint, tie-broken by `part_number`) lives
entirely inside this one function; a future optimization package can
replace its internals without touching `generate_scene()` or the rest
of the pipeline at all.

**Scene IDs use the standard mechanism.** Every brick is added via
`scene.next_available_id()` immediately before `scene.add_brick()` —
the exact same primitive `duplicate_brick()` (Package_033) already
uses, not a generation-specific formula. Verified empirically before
committing to this: 2,304 sequential `next_available_id()` calls (the
worst case at the default `max_dimension=48`) took ~82ms — no
performance concern, so the literal, architecture-consistent approach
was used rather than a bespoke, faster-but-different ID scheme.

**Color reduction is a second, independent pure helper.**
`_nearest_dominant_color(pixel_rgb, dominant_colors)` never calls or
depends on `select_generation_brick()` — the two decisions (which part,
which color) are fully decoupled, each independently unit tested.

**Standard Scene output.** Built exclusively through `Scene()`,
`scene.add_brick()`, and `SceneBrick.from_definition()` — the exact
construction path every existing generator already uses. Verified
directly (not just asserted) that a generated Scene round-trips through
the existing `scene_to_document()`/`document_to_scene()` and
`export_scene()` with zero modification to either.

**Candidate System only.** `candidates_for(catalog, constraints)` is the
only way this module touches `PartCatalog` — no `catalog.get()` or
`catalog.all()` call appears anywhere in `generation_engine.py`.

---

# Generation Summary

Algorithm (row-by-row, one brick per occupied pixel, one part for the
whole Scene — deliberately as simple as the existing generators):

1. `candidates_for(catalog, constraints)` → `select_generation_brick()`
   — raises `ValueError` if no candidates exist (empty catalog, or
   constraints eliminating every part). No new exception type, matching
   `generate_mosaic()`'s own existing `ValueError` convention.
2. If `analysis.occupied_bounds is None` (fully transparent image),
   return an empty `Scene()` immediately — a valid, ordinary Scene, not
   an error, matching every existing generator's own "skip transparent
   pixels" convention taken to its limit.
3. `analysis.dominant_colors` (at most 5, already deterministically
   ordered by Package_035) is mapped to LDraw colors once via
   `PaletteEngine`, not per pixel.
4. Iterate only the `occupied_bounds` rectangle — a direct, justified
   use of `analysis`, not the full canvas — skipping individual
   transparent pixels within it. Each remaining pixel gets one brick of
   the selected part, positioned centered on `occupied_bounds` (not the
   full image — more intuitive for images with transparent padding
   around a small subject) and colored by whichever pre-mapped dominant
   color is nearest to that pixel's own RGB.

This makes `ImageAnalysisResult` genuinely load-bearing for the first
time (`occupied_bounds` for cropping and centering, `dominant_colors`
for color reduction) — closing the gap Package_035 and Package_037 both
flagged as future work, rather than re-skinning the existing
`mosaic_generator.py`'s unconstrained per-pixel `PaletteEngine.map_color()`
approach with a candidate-selected part swapped in.

---

# Test Summary

**19 tests, `tests/test_generation_engine.py`**:

- `select_generation_brick()`: smallest footprint wins, deterministic
  tie-break by `part_number`, empty candidates raises `ValueError`,
  determinism across repeated calls.
- `_nearest_dominant_color()`: exact match, nearest-among-several,
  deterministic tie-break (first in list wins), independence from any
  brick-selection context.
- `generate_scene()` integration, using a hand-built `GenerationInput`
  (a Qt-written test image, transparent-bordered so `occupied_bounds`
  is a genuine sub-region) and a small synthetic `LDConfig.ldr` fixture
  (not this environment's real, installed LDraw library — matching
  Package_037's own environment-independence precedent): identical
  inputs produce identical scene signatures; a normal image produces a
  non-empty Scene; a fully transparent image produces an empty Scene;
  no candidates raises `ValueError`; excluding the default-selected part
  via `GenerationConstraints` genuinely changes which part is used;
  every brick id is unique; placement is verifiably centered on
  `occupied_bounds`, not the full canvas; `generate_scene()` mutates
  neither `generation_input` (pixels and analysis object identity both
  checked) nor `catalog`/`constraints`; a generated Scene round-trips
  through the existing serializer/deserializer unmodified; a generated
  Scene exports through the existing `export_scene()` unmodified.

---

# Regression Results

Full suite: **284 tests**, all passing (265 pre-existing + 19 new).

---

# Scope Isolation Confirmation

`git diff --stat`/`git status --porcelain` confirm the only source
change is the addition of `src/brickforge/generation/generation_engine.py`
— `engine/`, `render/`, `selection/`, `transform/`, `serialization/`,
`export/`, `project/`, `ui/`, `services/`, `ldraw/`, `palette/`,
`preparation/`, `analysis/`, `models/`, and every pre-existing file in
`generation/` are completely untouched. An AST-based import check
confirms `generation_engine.py`'s dependencies are exactly
`brickforge.engine.scene`, `brickforge.engine.scene_brick`,
`brickforge.generation.candidates`, `brickforge.models.part_definition`,
`brickforge.palette.palette_engine`, `brickforge.preparation.generation_input`,
`brickforge.services.part_catalog`, and `glm` — no render/UI/OpenGL
coupling anywhere.

---

# Definition of Done

- A deterministic Generation Engine exists — `generate_scene()`,
  composed entirely of already-deterministic primitives plus new pure
  helpers verified deterministic in isolation.
- It produces valid immutable Scenes — built exclusively through the
  existing `Scene`/`SceneBrick` construction path.
- Generated Scenes integrate with every existing subsystem without
  special handling — verified directly against serialization and
  export, not just asserted; nothing in `engine/`, `render/`,
  `selection/`, `transform/` needed to change.
- The architecture is ready for optimization in Package_039 —
  brick-selection policy is isolated behind `select_generation_brick()`
  specifically so a future package can improve it without touching the
  pipeline.

---

# Current Limitations (deliberate, not defects)

- One part for the entire Scene, one brick per pixel — no region
  detection, no variable brick sizing, no structural awareness. Exactly
  the mission's own "correctness over quality" scope for a first engine.
- Color is reduced to at most 5 dominant colors, not full per-pixel
  fidelity — a deliberate trade matching "dominant-color placement,"
  the mission's own first-listed example capability.
- `select_generation_brick()`'s policy (smallest footprint) inherits
  Package_037's known catalog-metadata gap: against the real,
  non-seed-catalog production data, most parts still report placeholder
  `stud_width`/`stud_length`, so "smallest footprint" often can't
  distinguish a genuinely-1x1 part from a placeholder-defaulted one —
  an existing, documented limitation this package doesn't change.
- No UI wiring — matches Packages 034–037's own precedent of stopping
  at architecture; nothing in this package's Definition of Done
  required it.
