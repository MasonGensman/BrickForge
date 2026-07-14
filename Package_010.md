# StudWorks

# Package 010

## Title

Image Analysis Foundation

---

# Mission

Build deterministic image-processing primitives that every future AI
package will consume. No AI, no LEGO generation, no renderer work — the
`ImageAnalysis` stage of the pipeline
(Image → ImageLoader → **ImageAnalysis** → Palette Mapping → Brick
Selection AI → Scene Generation → Studio Export).

---

# Scope

New package:

- `src/brickforge/analysis/__init__.py` (empty)
- `src/brickforge/analysis/image_analysis.py`

No existing file changes.

---

# Requirements

1. New `analysis/` package, exactly as proposed.
2. `ImageAnalysis` (the module) stays stateless.
3. `analyze(image)` is the primary public entry point.
4. Helper functions (`crop`, `resize`, `histogram`, `average_color`,
   `to_grayscale`) may exist, but future packages should primarily consume
   `analyze()`.
5. `ImageStatistics` gains `aspect_ratio` and `pixel_count`, computed once
   during analysis.
6. Histograms stay separated by channel (R, G, B, A) — never combined.
7. Resize uses deterministic nearest-neighbor sampling only.
8. Independent of `renderer`, `engine`, OpenGL, UI, AI.

---

# Definition of Done

- Deterministic image-analysis services exist in `analysis/`.
- `analyze(image: ImageResource) -> ImageStatistics` is the primary,
  documented entry point; helper functions are pure and independently
  usable but not the intended primary interface.
- `ImageStatistics` includes `width`, `height`, `pixel_count`,
  `aspect_ratio`, `average_color`, `histogram` (shape `(4, bins)`, R/G/B/A
  separated), `mean_luminance`, `min_luminance`, `max_luminance`,
  `std_luminance`.
- Renderer behavior unchanged. UI behavior unchanged. No LEGO generation
  introduced.
- `analysis/image_analysis.py` depends only on `dataclasses`, `numpy`, and
  `brickforge.io.image_resource` — verified via AST inspection.

---

# Completion Notes

## Implementation

`analysis/image_analysis.py` — one file, matching the project's existing
"a few closely related things in one focused file" convention (same shape
as `ldraw_colors.py`, `part_definition.py`):

- **`ImageStatistics`** (dataclass) — the structured output. `pixel_count`
  = `width * height`; `aspect_ratio` = `width / height`; both computed
  once inside `analyze()`, not re-derived by callers.
- **`crop(pixels, x, y, width, height)`** — numpy slicing, bounds-checked,
  raises `ValueError` on an out-of-bounds region, returns a `.copy()` (not
  a view, so mutating the result never affects the source).
- **`resize(pixels, width, height)`** — nearest-neighbor only, via integer
  floor-division index arrays (`np.arange(n) * source // target`) rather
  than float-division-then-cast, avoiding any floating-point rounding
  variance in the index computation. No interpolation. Returns a `.copy()`.
- **`to_grayscale(pixels)`** — per-pixel luminance, Rec. 709 weights
  (`0.2126R + 0.7152G + 0.0722B`), clipped to `[0, 255]`, `uint8`.
- **`average_color(pixels)`** — `pixels.reshape(-1, 4).mean(axis=0)`,
  `uint8`.
- **`histogram(pixels, bins=256)`** — shape `(4, bins)`; each channel
  (R, G, B, A) histogrammed independently via a per-channel loop calling
  `np.histogram` — never flattened or combined across channels.
- **`analyze(image)`** — the primary entry point. Computes all of the
  above once and returns one `ImageStatistics`.

## Verification Performed

- `py_compile` clean on both new files.
- **Functional correctness**: `crop`/`resize`/`to_grayscale`/
  `average_color`/`histogram` each checked against hand-computed expected
  values on a synthetic 4×2 half-red/half-white test image (verified
  during planning *and* re-verified against the final implementation,
  since the final `resize` uses integer floor-division rather than the
  float-division draft checked during planning) — all exact matches.
  `crop` confirmed to raise `ValueError` on an out-of-bounds region.
- **`analyze()` output**: confirmed `pixel_count`, `aspect_ratio`,
  `histogram.shape == (4, 256)`, and `average_color` all correct against
  the same known test image.
- **Determinism**: called `analyze()` three times on the identical
  `ImageResource` — every field of `ImageStatistics` (including array
  fields, compared with `np.array_equal`) identical across all three
  calls. Additionally built a *second*, distinct `ImageResource` instance
  wrapping a `.copy()` of the same pixel data (different `content_hash`,
  different object identity) and confirmed `analyze()` produces identical
  statistics — proving determinism holds across instances, not just
  repeated calls on one object.
- **Helper-function purity**: for each of `crop`/`resize`/`histogram`/
  `to_grayscale`/`average_color` — confirmed the input array is never
  mutated (compared against a `.copy()` taken before the call) and that
  the returned array is an independent copy (mutating a `crop`/`resize`
  result and re-calling on the same untouched source produces a
  *different* result than the mutated one, proving no shared buffer/view
  is returned).
- **Dependency isolation**: `ast`-parsed `image_analysis.py`, enumerated
  actual imports directly — `dataclasses`, `numpy`,
  `brickforge.io.image_resource` only. Zero references to
  `brickforge.engine`, `brickforge.render`, or `brickforge.ui`.
- **Regression testing**: re-ran Package_003's `Scene` API checks,
  Package_005's `u_model` matrix checks, Package_007's catalog/color
  checks, Package_008's `from_definition` equivalence check, and
  Package_009's image-loading/hash check — all still pass.
- **Live application verification**: `src/main.py` launches identically to
  Package_009 — same grid, same three missing-part warnings, no crash, no
  traceback.
- `git status` confirms only the new `analysis/` package was added — no
  existing file touched.

## Recommendations for Future Packages

- **`analyze()` is the intended integration point for Palette Mapping**
  (the pipeline's next stage) — it would consume `ImageStatistics.histogram`
  to derive dominant colors via clustering/quantization, deliberately not
  implemented here since that's conceptually palette-mapping work, not
  raw analysis.
- **Bilinear/higher-quality resize** was deliberately not implemented —
  nearest-neighbor only, per this package's explicit requirement. A future
  package could add an interpolated variant alongside `resize()` if image
  quality (rather than determinism/speed) becomes the priority for some
  consumer.
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
