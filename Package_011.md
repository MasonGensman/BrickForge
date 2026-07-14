# StudWorks

# Package 011

## Title

LEGO Palette Engine

---

# Mission

Teach StudWorks how to understand LEGO colors: a deterministic API that
converts arbitrary RGBA colors into the nearest available solid LDraw
color. No AI, no brick placement, no scene generation, no renderer work —
the `LEGO Palette Engine` stage of the pipeline
(Image → ImageLoader → ImageAnalysis → **LEGO Palette Engine** →
Brick Generator → AI Optimization → Studio Export).

---

# Scope

New package:

- `src/brickforge/palette/__init__.py` (empty)
- `src/brickforge/palette/palette_engine.py`

Extended (not duplicated):

- `src/brickforge/ldraw/ldraw_colors.py`

---

# Requirements

1. `PaletteEngine`, exactly as proposed.
2. Redmean weighted RGB distance as the initial matching algorithm.
3. Extend `ldraw_colors.py` rather than duplicating its parsing logic.
4. A `ColorCategory` enum (not a raw section string) stored on
   `LDrawColor`; `PaletteEngine` filters using the enum, not string
   comparison.
5. One public API: `map_color(rgba) -> MappedColor`.
6. A transparent sentinel for alpha below a configurable threshold.
7. Complete dependency isolation from renderer, engine, UI, AI.

---

# Definition of Done

- Deterministic LEGO color mapping exists; every RGBA color maps to either
  a solid `LDrawColor` match or an explicit transparent sentinel.
- `PaletteEngine.map_color(rgba)` is the one call a future package needs.
- `ColorCategory` correctly reflects `LDConfig.ldr`'s real section
  structure (verified against the actual file, not assumed).
- `PaletteEngine` matches only `ColorCategory.SOLID` colors.
- Package_007's original color-parsing assertions still pass unchanged.
- Renderer/UI/engine untouched; no brick generation introduced.

---

# Completion Notes

## Why `ldraw_colors.py` needed to change

Matching against the full, unfiltered 322-color palette produces unusable
results — verified directly before writing any code: pure red matched
`Metallic_Bright_Red`, pure blue matched `Trans_Dark_Blue`, pure white and
pure black both matched transparent novelty colors at distance `0.0`.
`LDConfig.ldr` has 16 sections (Solid, Transparent, Chrome Plated,
Pearlescent Plastic, Metallic Paint, Fluorescent Paint, Milky, Glitter,
Opalescent, Speckle, Modulex, Rubber, Transparent Rubber, Fabric,
Obsolete, Internal Common Material), and that section membership was
being discarded during parsing — no field on `LDrawColor` recorded it.
Recovering it correctly requires reading it where it actually lives (the
file's own section-header comments), not guessing from color names. A
`Metallic_Bright_Red` (code 184) turned out to genuinely be filed under
**Pearlescent Plastic** in the real file, not Metallic — confirming a
name-based heuristic would have been wrong in a way that section-tracking
isn't, and that verifying against the real file rather than assumptions
mattered concretely here, not just in principle.

## Exact Implementation

**`ldraw/ldraw_colors.py`**:
- Added `ColorCategory` (`Enum`), one member per real section, using each
  section's exact header text as the enum value (`SOLID = "Solid"`, etc.)
  so parsing is a direct `ColorCategory(section_text)` construction — no
  separate mapping table to keep in sync.
- Added `_SECTION_LINE` regex (`^0\s*//\s*LDraw\s+(.+?)\s+Colours\s*$`),
  matched *before* the existing `_COLOUR_LINE` check in the same loop.
- `LDrawColor` gained one field: `category: ColorCategory`.
- `load_ldraw_colors()` tracks the most recently seen section as state
  while iterating (same loop, same function — not a second parsing pass,
  not a duplicated regex), and raises `ValueError` if a `!COLOUR` line is
  ever encountered before any section header (a defensive check; every
  real color in the file is preceded by one, verified).
- The existing `_COLOUR_LINE` regex, the existing four fields, and every
  other line of parsing logic are byte-for-byte unchanged — this is an
  addition, not a rewrite.

**`palette/palette_engine.py`**:
- `MappedColor` (dataclass) — `color: LDrawColor | None`, `distance:
  float | None`, `is_transparent: bool`. Holds a reference to the actual
  `LDrawColor`, not copies of its fields (mirrors the `SceneBrick`/
  `BrickDefinition` precedent from Package_008).
- `_redmean_distance(rgb, palette_rgb)` — the weighted formula
  `sqrt((2+r̄/256)ΔR² + 4ΔG² + (2+(255-r̄)/256)ΔB²)`, vectorized against the
  whole palette array at once via numpy broadcasting.
- `PaletteEngine.__init__(config_path, alpha_threshold=16)` — calls
  `load_ldraw_colors()` once, filters to `category is ColorCategory.SOLID`
  (identity comparison against the enum, never a string), and
  pre-computes one `(102, 3)` numpy RGB array — the expensive setup
  happens exactly once, mirroring `LDrawLibrary`'s shape.
- `map_color(rgba)` — the one public entry point. Alpha below
  `alpha_threshold` short-circuits to the transparent sentinel before any
  distance computation runs; otherwise computes redmean distance to all
  102 solid colors and returns the nearest via `argmin`.

## Verification Performed

- `py_compile` clean on all three touched/new files.
- **Category parsing correctness**: parsed the real `LDConfig.ldr`;
  confirmed `colors[4]` (Red) is `SOLID`, `colors[32]`
  (Trans_Black_IR_Lens) is `TRANSPARENT`, `colors[184]`
  (Metallic_Bright_Red) is `PEARLESCENT` (the file's actual answer, not my
  initial name-based guess — corrected during verification, see above);
  confirmed all 16 categories are present with counts summing to exactly
  322, and `SOLID` count is exactly 102.
- **`PaletteEngine` filters only SOLID**: confirmed the engine's internal
  palette holds exactly 102 entries, every one independently re-checked
  as `category is ColorCategory.SOLID`.
- **Known-color validation**: pure red → `Red` (#4); pure white → `White`
  (#15); an exact LDraw-Red hex value fed back in matches itself at
  distance `0.0`.
- **Transparent sentinel and threshold boundary**: alpha `0` → sentinel;
  alpha exactly at the threshold (16) → real match; alpha one below the
  threshold (15) → sentinel — boundary condition checked exactly, not
  just a coarse above/below case.
- **Redmean determinism**: `map_color()` called three times on identical
  input → identical `MappedColor` (color code and distance both compared
  exactly) every time. A *second*, independently-constructed
  `PaletteEngine` instance (re-parsing the same file separately) agrees
  exactly with the first on the same input — determinism holds across
  instances, not just repeated calls on one object.
- **Package_007 backward compatibility**: re-ran Package_007's original
  assertions (`colors[4]`/`colors[14]`/`colors[15]` names and hex values,
  total count against an independent `grep -c` count) against the new
  parser — all still pass unchanged.
- **Dependency isolation**: `ast`-parsed all three files, enumerated
  actual imports directly. `ldraw_colors.py`: `re`, `dataclasses`, `enum`,
  `pathlib`. `palette_engine.py`: `dataclasses`, `pathlib`, `numpy`,
  `brickforge.ldraw.ldraw_colors`. Zero references to
  `brickforge.engine`, `brickforge.render`, or `brickforge.ui` in either.
- **Regression testing**: re-ran Package_003/005/007/008/009/010's
  existing checks — all still pass.
- **Live application verification**: `src/main.py` launches identically —
  same grid, same three missing-part warnings, no crash, no traceback.
- `git status`/`git diff --stat` confirm exactly the planned scope: one
  file modified (`ldraw_colors.py`, +54/-1) and one new package added.

## Recommendations for Future Packages

- **CIE Lab / ΔE** remains a viable future upgrade if redmean's accuracy
  is ever measured to be insufficient — `map_color()`'s public signature
  wouldn't need to change, only the private `_redmean_distance` function
  would be replaced or made selectable.
- **Matching against non-solid finishes** (transparent, chrome, pearlescent,
  metallic, etc.) was deliberately not implemented — a real future
  capability (e.g. translucent bricks for windows) once a concrete need
  exists; `ColorCategory` already gives a future package everything
  needed to opt into other categories without re-deriving them.
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
