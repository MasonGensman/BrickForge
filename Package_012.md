# StudWorks

# Package 012

## Title

Deterministic Scene Generator (Mosaic)

---

# Mission

Produce the first complete end-to-end pipeline: an imported image
deterministically becomes a renderable LEGO `Scene`, one non-transparent
pixel to one `SceneBrick`. No AI, no optimization, no variable brick
sizing, no merging — the `SceneGenerator` stage of the pipeline
(Image → ImageLoader → ImageAnalysis → PaletteEngine →
**SceneGenerator** → Scene → Renderer).

---

# Scope

New package:

- `src/brickforge/generation/__init__.py` (empty)
- `src/brickforge/generation/mosaic_generator.py`

Extended (not redesigned):

- `src/brickforge/engine/scene_brick.py`

---

# Requirements

1. `SceneBrick.color_code: int | None`, storing the raw LDraw color code.
2. Transparent pixels continue producing no `SceneBrick` (default
   behavior; configurable).
3. `GenerationSettings` structure instead of an ever-growing function
   signature — `default_part_number`, `skip_transparent_pixels`,
   `origin_mode`, `spacing`.
4. Explicit, documented image-coordinate → world-coordinate convention.
5. A mosaic-specific implementation, with documented reasoning for why,
   and how future generation modes coexist without breaking the public
   API.

---

# Definition of Done

- An imported image, via `generate_mosaic(image, palette, catalog)`,
  deterministically produces a `Scene` of correctly-positioned,
  correctly-colored, correctly-parted `SceneBrick`s — one per
  non-transparent pixel.
- The resulting `Scene` is structurally usable by the existing,
  unmodified `Renderer`/`BrickManager` — verified directly, not assumed.
- `renderer.py` and every other `render/` file are untouched.
- Package_008's `SceneBrick` construction/equality guarantees remain
  intact.

---

# Completion Notes

## Why Mosaic-Specific, and How Future Modes Coexist

No abstract base class or shared generator interface was introduced.
There is exactly one implementation to generalize from; a future
height-map or voxel-based mode might need fundamentally different inputs
(a depth image, a 3D mesh) that a base class designed today would almost
certainly guess wrong, forcing a breaking change later anyway. The
future-proofing instead comes from three things that don't require
guessing:
1. **Package boundary** — `generation/` holds `mosaic_generator.py`
   today; a future `height_map_generator.py` becomes a sibling module,
   not a rename or refactor of something that already claimed a generic
   name.
2. **The one true stable contract** — every generation mode, regardless
   of internal strategy, must produce a `Scene` (via `Scene`/
   `SceneBrick`'s existing, unmodified public API) for the renderer to
   consume it. That contract doesn't change no matter how many modes are
   added.
3. **`GenerationSettings`** — explicitly documented (in its own
   docstring) as extensible in spirit rather than in place: a future mode
   needing different configuration introduces its own settings type
   reusing this one's fields/spirit, rather than this type growing
   indefinitely to cover strategies it doesn't apply to.

## Coordinate Convention (as required, documented explicitly)

Full convention lives in `generate_mosaic()`'s docstring, not just this
file. Summary: image pixel `(row=0, col=0)` is top-left (standard raster
convention, matching `ImageResource.pixels`' own `(height, width, 4)`
layout). Column → world X, row → world Z, both increasing together
(`+col → +X`, `+row → +Z`). World Y is always `0.0` — a flat mosaic.
`OriginMode.CENTERED` (default) centers the whole grid on the world
origin using `(width-1)/2`/`(height-1)/2` offsets (the true geometric
center of the pixel grid, not `width/2`); `OriginMode.CORNER` anchors
pixel `(0,0)` at world `(0,0,0)`. This plane choice (XZ, Y=0) was chosen
specifically to match the *existing* `Grid`'s own plane — confirmed by
reading `render/grid.py` directly, every grid vertex has Y=0 — rather
than introducing a new spatial convention the renderer's existing visual
reference doesn't support.

## Exact Implementation

**`engine/scene_brick.py`**: added `color_code: int | None = None` and
extended `from_definition` with an optional `color_code` kwarg, following
the exact same "omit from kwargs when None, let the dataclass default
apply" pattern already used for `position`/`rotation`. Purely additive —
verified directly that pre-Package_012 `SceneBrick(...)` construction and
`from_definition(...)` calls still compare equal (both default to
`color_code=None`).

**`generation/mosaic_generator.py`**:
- `OriginMode` (`Enum`: `CENTERED`, `CORNER`).
- `GenerationSettings` (dataclass): `default_part_number="3005"` (the
  *only* 1×1 part in the seed catalog — confirmed by inspection during
  planning, no new catalog seed data added), `skip_transparent_pixels=True`,
  `origin_mode=OriginMode.CENTERED`, `spacing=None` (auto-derive from the
  resolved part's `stud_width`/`stud_length * 20` LDraw units — 1 stud —
  so bricks tile edge-to-edge; an explicit value overrides both axes
  uniformly).
- `generate_mosaic(image, palette, catalog, settings=None) -> Scene` —
  resolves the part once (not per-pixel), iterates pixels in row-major
  order, maps each via `PaletteEngine.map_color()` (reusing Package_011's
  already-verified transparency threshold, not reimplementing it), skips
  transparent pixels per `settings.skip_transparent_pixels`, and
  constructs each `SceneBrick` via the existing `from_definition()`
  bridge (Package_008) — no raw `.dat` literal anywhere in this file.
  Brick id = `row * width + col`.

## Verification Performed

All checks used a synthetic 3×2 test image (6 pixels: red, white,
*fully transparent*, red, red, white) with independently hand-computed
expected values — not just "runs without error."

- `py_compile` clean on both touched/new files.
- **Brick count**: 6 pixels, 1 transparent → exactly 5 `SceneBrick`s.
- **Scene correctness**: every brick's `part_name == "3005.dat"`.
- **Deterministic brick IDs**: confirmed exact expected id set
  `{0,1,3,4,5}` (id 2, the transparent pixel, correctly absent), all
  unique.
- **Correct coordinate mapping**: all 5 bricks' `(x, z)` positions
  compared exactly against the hand-computed `CENTERED` formula; `y == 0.0`
  for every brick.
- **Centered placement**: confirmed the generated grid's X and Z ranges
  are symmetric around `0` (`min == -max` on both axes).
- **Correct `color_code` assignment**: every brick's `color_code`
  cross-checked exactly against an independent, separate
  `PaletteEngine.map_color()` call on the same RGBA value (not merely
  "a code exists") — red pixels → `#4`, white pixels → `#15`, matching
  Package_011's own previously-verified values exactly.
- **Transparent-pixel skip**: confirmed pixel `(0,2)` (alpha `0`)
  produced no `SceneBrick` at all.
- **`OriginMode.CORNER`**: pixel `(0,0)` → world `(0,0,0)` exactly; pixel
  `(1,1)` → `(20, 0, 20)` exactly (1-stud spacing confirmed numerically).
- **Spacing override**: `settings.spacing=50.0` applied uniformly to both
  axes, confirmed exactly.
- **`skip_transparent_pixels=False`**: confirmed the previously-skipped
  pixel now produces a brick with `color_code=None` (no color could be
  determined for a transparent pixel, correctly represented as absent
  rather than a fabricated value).
- **Deterministic generation**: two independent `generate_mosaic()` calls
  on the identical image produce field-identical `Scene`s (id, part_name,
  color_code, position, rotation compared for every brick).
- **Package_008 `SceneBrick` compatibility**: re-ran the exact
  Package_008 equivalence check — still passes; both sides' `color_code`
  confirmed `None`.
- **Dependency isolation**: `ast`-parsed both touched/new files; zero
  references to `brickforge.render` or `brickforge.ui` in either.
- **Renderer integration**: constructed a real `BrickManager` and called
  `.renderables()` on a generator-produced `Scene` directly — iterated
  without exception (0 resolved, since the LDraw parts library is still
  empty in this environment — the same graceful degradation verified in
  every prior package, not a new failure mode).
- **Regression testing**: re-ran Package_003/005/007/008/009/010/011's
  existing checks — all still pass.
- **Live application verification**: `src/main.py` launches identically —
  same grid, same three missing-part warnings, no crash, no traceback.
- `git status`/`git diff --stat` confirm exactly the planned scope: one
  file modified (`scene_brick.py`, +13/-0) and one new package added.

## Recommendations for Future Packages

- **`render/renderer.py` still draws every brick in one hardcoded
  color**, regardless of `color_code`. Wiring `color_code` into an actual
  per-brick render color is the natural next step, mirroring exactly how
  Package_002 added `SceneBrick.rotation` as inert data and Package_005
  was the separate package that wired it into rendering.
- **No cross-validation against `BrickDefinition.available_colors`** — a
  mapped LDraw color is used as-is, without checking whether "3005" is
  actually molded in that color. A future package could validate and
  choose a fallback if not.
- **No image downsampling** — `generate_mosaic()` uses the given
  `ImageResource` at its native resolution; a very large source image
  produces a proportionally large `Scene`. Resizing to a target
  brick-canvas size is the caller's responsibility, reusing
  `analysis.resize()` (Package_010), deliberately not duplicated here.
- **`ImageStatistics` was not accepted as an input**, despite being
  listed as a candidate — no genuine use was found for it in this minimal
  1-pixel-1-brick strategy; noting this rather than accepting an unused
  parameter.
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
