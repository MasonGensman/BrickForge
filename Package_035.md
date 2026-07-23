# StudWorks

# Package 035

## Title

Image Analysis — Deterministic Facts About the Prepared Image

---

# Mission

Establish the deterministic image-analysis layer future generation
algorithms will consume, so they can work from structured facts about an
image (dominant colors, occupied content bounds, edge structure) rather
than re-deriving them from raw pixels each time. No LEGO generation
occurs in this package, and no existing generation mode is refactored to
consume it — this package builds the architecture for a future package to
use, following [[generation_input_system]]'s established "prepared image
is the stable boundary" pattern.

---

# Scope

New (functions in the existing `analysis/image_analysis.py`, no new
files):

- `sobel_edges(pixels) -> np.ndarray` — per-pixel edge magnitude
- `dominant_colors(pixels, count=5) -> list[tuple[int,int,int]]` —
  deterministic bucket-quantized color frequency
- `occupied_bounds(pixels) -> tuple[int,int,int,int] | None` — bounding
  box of non-fully-transparent content

Renamed (zero prior consumers, confirmed via grep — a safe rename, not a
breaking change):

- `ImageStatistics` → `ImageAnalysisResult`, extended with
  `dominant_colors`, `edges`, `edge_density`, `occupied_bounds`
- `analyze()` → `analyze_image()`, matching this codebase's `verb_noun`
  convention (`prepare_image`, `replace_brick`, `duplicate_brick`)

Modified:

- `preparation/generation_input.py` — `GenerationInput` gains an
  `analysis: ImageAnalysisResult` field, computed via
  `analyze_image(prepared_image)` inside the existing `from_source()`
  factory

Tests:

- `tests/test_image_analysis.py` — new `SobelEdgesTests`,
  `DominantColorsTests`, `OccupiedBoundsTests`, `AnalyzeImageTests`
- `tests/test_generation_input.py` — new `AnalysisFieldTests`
- `tests/test_project_serialization.py` — two new tests on
  `ProjectGenerationInputTests`

**Untouched — confirmed via `git diff --stat`**: `render/*`, `tools/*`,
`selection/*`, `transform/*`, `engine/*`, `ui/*`. This package touches
only `analysis/image_analysis.py` and `preparation/generation_input.py`.

---

# Inspection Findings

**`analyze()`/`ImageStatistics` had zero consumers anywhere in the
codebase**, confirmed by grepping every reference to either name outside
`image_analysis.py` itself — including in tests. They existed purely as
forward-looking infrastructure from an earlier package. This made the
rename to `ImageAnalysisResult`/`analyze_image()` risk-free: nothing
depended on the old shape.

**Both existing generation modes bypass any analysis layer today**,
confirmed by reading both in full:
[`mosaic_generator.py`](src/brickforge/generation/mosaic_generator.py)
calls `palette.map_color(image.pixels[row,col])` directly, per pixel,
never touching `analysis/` at all.
[`height_relief_generator.py`](src/brickforge/generation/height_relief_generator.py)
calls `to_grayscale(image.pixels)` directly, once, also bypassing
`analyze()`/`ImageStatistics`. This confirms the mission's own framing —
"future generators should consume analysis results" — describes a real,
unrealized gap, not a solved problem being re-documented. Migrating
either generator to consume the new result is explicitly out of this
package's scope (LEGO generation is excluded; the mission asks to
establish the architecture, future tense, not to retrofit it onto
existing consumers).

**`GenerationInput.from_source()`** ([[generation_input_system]],
Package_034) was confirmed to be the single canonical, already-eager,
already-deterministic factory that builds `prepared_image` from
`(source_path, settings)`. `Project`'s serialization
(`_generation_input_to_dict`/`_generation_input_from_dict` in
`project/project.py`) was confirmed, by reading the code directly, to
serialize only `source_path`/`content_hash`/`settings` and to
reconstruct via `GenerationInput.from_source()` on load — never touching
`prepared_image` directly. This is the exact shape a new `analysis`
field can piggyback on for free, verified rather than assumed.

**Empirically verified before writing any implementation** (not
guessed): a vectorized 3×3 Sobel operator with edge-replicated padding
produces a clean, symmetric edge response at a known vertical boundary
and exactly zero elsewhere, with output shape matching the input; bucket
quantization (÷16 per channel) with `alpha == 0` exclusion and a
`(-count, bucket)` sort key produces fully reproducible dominant-color
ordering, including ties; `occupied_bounds` correctly returns `None` for
an all-transparent image and a tight box otherwise.

---

# Architecture Assessment

The existing `analyze()` → `ImageStatistics` shape — one orchestrator
function calling small, independent, stateless pure helpers, assembled
into one dataclass result — was already exactly right and needed no
structural change, only extension. Every pipeline stage elsewhere in this
codebase (`prepare_image`, `optimize_scene`, `export_scene`) is a plain
function, not a class, which is why an `ImageAnalyzer`/`AnalysisPipeline`
class-based design was considered and rejected, for the same reason
`ImagePreparationPipeline` was rejected in Package_034.

Region segmentation, connected components, contours, and generic
"feature extraction" were considered and explicitly deferred: no
concrete consumer needs them yet, they're meaningfully more complex than
the deterministic primitives this module is scoped to, and they lean
toward AI interpretation rather than structured facts — matching the
mission's own "defer advanced AI interpretation" instruction and this
project's standing discipline against speculative abstractions
([[no_speculative_scaffolding]]).

No new settings type was introduced. `analyze_image()` keeps
`analyze()`'s existing no-parameters shape, using fixed, documented
constants (5 dominant colors, a `128` edge-density threshold) rather than
a speculative `AnalysisSettings` with no evidenced need for
configurability yet.

---

# Image Analysis Architecture Recommendation

Three new pure helper functions, alongside the existing
`to_grayscale`/`average_color`/`histogram`:

```python
def sobel_edges(pixels: np.ndarray) -> np.ndarray:
    """Per-pixel edge magnitude, shape (H, W), uint8. Edge-replicated
    padding keeps output shape equal to input shape."""

def dominant_colors(pixels: np.ndarray, count: int = 5) -> list[tuple[int, int, int]]:
    """Most frequent colors, bucket-quantized (not k-means), fully-
    transparent pixels excluded, deterministic tie-break ordering."""

def occupied_bounds(pixels: np.ndarray) -> tuple[int, int, int, int] | None:
    """Bounding box of alpha > 0 content, or None if fully transparent."""
```

`ImageAnalysisResult` (renamed from `ImageStatistics`) gains
`dominant_colors`, `edges`, `edge_density`, and `occupied_bounds`
alongside its existing fields:

```python
@dataclass(slots=True)
class ImageAnalysisResult:
    width: int; height: int; pixel_count: int; aspect_ratio: float
    average_color: np.ndarray
    histogram: np.ndarray
    dominant_colors: list[tuple[int, int, int]]
    mean_luminance: float; min_luminance: float
    max_luminance: float; std_luminance: float
    edges: np.ndarray
    edge_density: float
    occupied_bounds: tuple[int, int, int, int] | None
```

`edge_density` (fraction of pixels above a fixed magnitude threshold) is
a cheap scalar summary alongside the full `edges` map — the same shape
this module already used for luminance (`mean_luminance` alongside the
full `histogram`), not a new pattern.

Analysis runs on the **prepared** image, not the original source —
`analyze_image(prepared)` inside `GenerationInput.from_source()` — so
analysis results (e.g. edge positions) correspond exactly to the pixel
grid a future generator will actually iterate over.

---

# Project Ownership Recommendation

`GenerationInput` gains a fourth field, `analysis: ImageAnalysisResult`,
computed in the same `from_source()` call that already produces
`prepared_image`:

```python
resource = ImageLoader().load(path)
prepared = prepare_image(resource, settings)
return cls(
    source_path=Path(path), content_hash=resource.content_hash,
    settings=settings, prepared_image=prepared,
    analysis=analyze_image(prepared),
)
```

`analyze_image()` is just as pure a function of `prepared_image` as
`prepare_image()` is of the source image, so bundling it into the same
canonical factory is the natural extension rather than a new ownership
concept. `Project` does not gain a separate `analysis_result` field — it
already transitively owns analysis via `project.generation_input.analysis`,
exactly mirroring how it already transitively owns `prepared_image`.

---

# Serialization Recommendation

**Regenerate, don't store** — the same rule [[generation_input_system]]
already established for `prepared_image`, for the same reason:
`analyze_image()` is deterministic, and several of its fields
(`histogram`, `average_color`, `edges`) are numpy arrays with no natural
JSON representation.

Because `analysis` lives inside `GenerationInput` (in-memory only) rather
than as a new `Project` field, **`Project.to_dict()`/`from_dict()` needed
zero new code** — confirmed by reading `project/project.py` directly
before writing any code, then confirmed again by a dedicated test
(`test_serialized_generation_input_contains_no_analysis_data`) asserting
the serialized `generation_input` dict contains exactly
`{source_path, content_hash, settings}` and nothing else. The existing
"regenerate `generation_input` via `from_source()` on load" path
reconstructs `analysis` for free.

---

# Definition of Done

- `ImageAnalysisResult` (renamed from `ImageStatistics`) carries
  dominant colors, occupied bounds, and edge information alongside its
  existing statistics — verified correct against known fixtures, not
  just "runs without error."
- `GenerationInput.analysis` is populated automatically by
  `from_source()`, with zero new `Project` serialization code.
- Architecture is ready for a future generation package to consume
  `generation_input.analysis` directly — no plumbing required.
- Existing generation modes (`mosaic_generator`, `height_relief_generator`)
  are unaffected — confirmed unchanged by `git diff --stat`.

---

# Verification Performed

- `py_compile` clean on every modified file.
- `git diff --stat` confirms `render/`, `tools/`, `selection/`,
  `transform/`, `engine/`, `ui/` are **completely untouched** — this
  package touches only `analysis/image_analysis.py` and
  `preparation/generation_input.py`.
- AST-based import check: `image_analysis.py` still imports only
  `numpy`, `dataclasses`, and `ImageResource` — no new coupling to
  engine/render/UI, matching its own documented boundary claim.
  `generation_input.py` gained exactly the one intended new import
  (`brickforge.analysis.image_analysis`).
- Empirically verified before implementation, not assumed: Sobel edge
  response at a known boundary, dominant-color bucket quantization and
  transparency exclusion, occupied-bounds edge cases (partial content,
  fully transparent).
- **17 new tests, `test_image_analysis.py`**: `sobel_edges` (boundary
  detection, zero elsewhere, flat-image has no edges, shape/dtype match,
  determinism); `dominant_colors` (correct 3-color result from a known
  fixture, transparent-quadrant exclusion, `count` parameter respected,
  fully-transparent image returns `[]`, deterministic ordering);
  `occupied_bounds` (tight box for partial content, `None` for fully
  transparent, deterministic); `analyze_image()` (all fields assembled
  correctly including the renamed pre-existing ones, luminance stats
  unchanged by the rename, determinism).
- **3 new tests, `test_generation_input.py`**: `analysis` populated and
  matching `prepared_image`'s dimensions; matches a direct
  `analyze_image(prepared_image)` call exactly; deterministic across two
  separate `from_source()` calls.
- **2 new tests, `test_project_serialization.py`**: serialized
  `generation_input` dict contains no analysis data at all (exact key-set
  assertion); a full Save → Open round-trip regenerates `analysis`
  matching the original exactly (dominant colors, occupied bounds, edge
  map) — proving the "zero new serialization code" claim, not just
  asserting it.
- Full regression suite re-run: **219 tests** across all suites — all
  pass, including all 13 pre-existing `test_project_serialization.py`
  tests and the byte-for-byte golden-file comparisons (unaffected, since
  `analysis` never touches the serialized format).
- `git status` confirms exactly the planned scope.

---

# Recommendations for Future Packages

- Migrating `mosaic_generator`/`height_relief_generator` to consume
  `generation_input.analysis` (e.g. edge-aware brick placement, palette
  seeding from `dominant_colors`) is the natural next step to make this
  package's architecture actually load-bearing, not just present.
- Region segmentation, connected components, and contour detection remain
  deferred until a concrete generation algorithm actually needs them.
- The interactive crop/rotate UI and the renderer's upside-down LDraw
  geometry bug (Package_024) remain outstanding and unaffected by this
  package.
