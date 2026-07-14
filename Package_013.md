# StudWorks

# Package 013

## Title

Per-Brick Color Rendering

---

# Mission

Teach the renderer to display per-brick LEGO colors. `SceneBrick` already
stores `color_code` (Package_012); `PaletteEngine` already maps image
colors to LDraw colors (Package_011); the renderer ignored both,
hardcoding one brick color for every draw call. This package completes
the visual Image → LEGO pipeline
(Image → ImageLoader → ImageAnalysis → PaletteEngine → Generation →
Scene (contains color_code) → **Renderer**).

---

# Scope

- `src/brickforge/render/color_resolver.py` (new)
- `src/brickforge/render/renderer.py` (modified)

---

# Requirements

1. `ColorResolver.resolve()` returns an immutable `ResolvedColor`
   (`code`, `name`, `rgb`, `edge_rgb`), not a bare RGB tuple.
2. Renderer uses only `.rgb` this package.
3. `BrickManager` stays geometry-only, `PaletteEngine` stays
   matching-only, `ColorResolver` stays lookup-only.
4. Grid rendering unchanged.

---

# Definition of Done

- `SceneBrick.color_code` is honored during rendering via
  `ColorResolver`.
- Different bricks with different `color_code`s render in different
  colors — verified with distinct hand-computed RGB values, not just
  "runs without error."
- Legacy `SceneBrick`s (no `color_code`, including every brick
  `renderer.py` itself seeds) render in exactly the renderer's original
  hardcoded color — unchanged.
- Grid rendering is byte-for-byte untouched.
- No optimization, AI, or generation logic introduced.

---

# Completion Notes

## Why `ColorResolver`, Not `PaletteEngine` or `BrickManager`

`PaletteEngine` is a *matching* service (Package_011) — RGB→nearest-code,
deliberately filtered to `ColorCategory.SOLID` because that filter suits
photo-color matching specifically. The renderer's job is different: given
a code already decided by whatever produced the `SceneBrick`, display it
— including, in principle, a non-`SOLID` code, if some future producer
ever sets one. Borrowing `PaletteEngine`'s filter for a general display
lookup would conflate two different concerns. Extending
`BrickManager.renderables()` to a 3-tuple was rejected as a breaking
change to an API already relied on since Package_003/004, for a
responsibility (`BrickManager`'s own docstring: "Owns the LDraw library
and the GPU mesh cache") that has never been about appearance.
`ColorResolver` is a direct structural mirror of `BrickManager` instead:
same shape (load once, cache derived results, resolve-by-key), same
graceful-degradation pattern (`try/except OSError`, log and fall back
rather than crash), living in the same package as its one consumer.

## Exact Implementation

**`render/color_resolver.py`**:
- `ResolvedColor` — `@dataclass(frozen=True, slots=True)`: `code`, `name`,
  `rgb`, `edge_rgb`. Immutable per your refinement — verified directly
  (attribute assignment raises `FrozenInstanceError`). Carries more than
  `Renderer` uses this package specifically so future rendering, export,
  debugging, and selection work can reuse the same result without another
  lookup layer.
- `ColorResolver.__init__(config_path)` — loads `load_ldraw_colors()`
  once; on `OSError` (missing/unreadable `LDConfig.ldr`), logs a warning
  and falls back to an empty color table rather than crashing, mirroring
  `BrickManager`'s exact pattern.
- `resolve(color_code)` — cached by code (including `None` as a valid
  cache key). `None` or any code absent from the loaded table resolves to
  the **default** — `DEFAULT_RGB = (0.80, 0.05, 0.05)`, the renderer's
  own pre-existing hardcoded value, preserved verbatim rather than
  reinvented, so every brick that doesn't specify a color keeps rendering
  exactly as it always has. The unresolved case still reports the
  originally-requested `code` (not `None`) in the fallback
  `ResolvedColor`, so a future debugging consumer can see *what* failed
  to resolve, not just that something did.
- `_hex_to_rgb()` — a small, private, renderer-local hex parser. Not
  shared with `PaletteEngine`'s own private `_hex_to_rgb` (different
  package, different output convention — 0-255 ints there vs. `[0,1]`
  floats here) and not promoted to a shared location in `ldraw_colors.py`
  — the duplication is a few lines of standard, low-risk hex parsing, and
  avoiding it wasn't judged worth touching a third file for.

**`render/renderer.py`**: `initialize()` constructs one
`ColorResolver(library_path / "LDConfig.ldr")` alongside the existing
`BrickManager` construction. `render()`'s brick loop replaces the
hardcoded `set_color(0.80, 0.05, 0.05)` with
`self.shader.set_color(*self.color_resolver.resolve(brick.color_code).rgb)`.
The grid's own `set_color(0.35, 0.35, 0.35)` call, and everything else in
`render()`/`initialize()`, is untouched — confirmed via `git diff`
showing zero changes in that region of the file. No shader or GLSL file
was touched: `Shader.set_color()`/`u_color` already fully supported
per-draw-call color (proven by the grid and bricks already using
different values before this package) — this package only changes *what
value* is passed for a brick, not the mechanism.

## Verification Performed

- `py_compile` clean on both files.
- **Correct LDraw color lookup**: `resolve(4)` (Red) and `resolve(15)`
  (White) checked against independently hand-computed RGB from their
  known hex values (`#B40000`, `#F4F4F4`) — exact match, not approximate.
- **Multiple brick colors**: codes 4/15/14 confirmed to produce three
  mutually distinct RGB triples.
- **`edge_rgb` present and correct** (unused by `Renderer` this package,
  per your instruction) — checked against `#333333` exactly.
- **Immutability**: `ResolvedColor` is `frozen=True`; assigning to
  `.rgb` after construction raises `FrozenInstanceError`, confirmed
  directly.
- **Fallback behavior**: `resolve(None)` and `resolve(<unrecognized
  code>)` both return `DEFAULT_RGB`/`DEFAULT_NAME`; the unrecognized case
  preserves the originally-requested code rather than discarding it.
- **Deterministic / identical across repeated calls**: `resolve(4)`
  called twice returns equal `ResolvedColor` values; a second,
  independently-constructed `ColorResolver` agrees exactly with the
  first.
- **Legacy `SceneBrick` rendering unchanged**: constructed
  `SceneBrick`s the pre-Package_013 way (bare constructor and
  `from_definition()` without `color_code`, matching exactly how
  Package_004/005/008 built them) — confirmed `color_code is None` and
  `resolve(None).rgb == (0.80, 0.05, 0.05)`. Directly re-checked all
  three bricks `renderer.py` itself seeds in `initialize()` — confirmed
  none carry a `color_code`, all resolve to the unchanged original red.
- **Grid color unchanged**: `git diff` on the grid's `set_color(0.35,
  0.35, 0.35)` region shows zero output — byte-for-byte untouched, not
  merely visually equivalent.
- **Dependency isolation**: `ast`-parsed `color_resolver.py` — imports
  are `logging`, `dataclasses`, `pathlib`,
  `brickforge.ldraw.ldraw_colors` only. Zero reference to `engine/`,
  `palette/`, or `ui/` — confirming `ColorResolver` stays lookup-only,
  `BrickManager` stays untouched (geometry-only), `PaletteEngine` stays
  untouched (matching-only).
- **Regression testing**: re-ran Package_003/005/007/008/009/010/011/012's
  existing checks — all still pass.
- **Live application verification**: `src/main.py` launches identically —
  same grid, same three missing-part warnings (LDraw parts library still
  empty in this environment, consistent with every prior package), no
  crash, no traceback. `ColorResolver` construction against the real
  `LDConfig.ldr` succeeded without any new warning.
- `git status`/`git diff --stat` confirm exactly the planned scope: one
  new file, one file modified (+11/-3).

## Recommendations for Future Packages

- **`edge_rgb` is parsed and available but unused** by `Renderer` this
  package, per your explicit instruction — a natural candidate for a
  future outline/silhouette rendering pass.
- **`ResolvedColor.name`** is available now for a future debug overlay or
  selection UI without any new lookup — exactly the motivation behind
  returning a structured result instead of a bare tuple.
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
