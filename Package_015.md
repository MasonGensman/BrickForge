# StudWorks

# Package 015

## Title

Real LDraw Library & Full Part Catalog

---

# Mission

Replace the temporary 10-part seed catalog with a catalog generated from
a real, installed LDraw library, while preserving complete backward
compatibility. Replacing the catalog *source*, not redesigning the
catalog system or building a complete part taxonomy.

---

# Scope

New files:

- `services/ldraw_library_locator.py`
- `services/ldraw_catalog_builder.py`

Modified:

- `services/part_catalog.py` (one new classmethod)
- `render/renderer.py` (catalog source swap + defensive None-checks)
- `ui/main_window.py` (shared catalog, wired to both consumers)
- `ui/widgets/brick_library_widget.py` (constructor now takes a catalog)
- `ui/widgets/properties_widget.py` (display real `BrickDefinition` fields)

---

# Decisions (as approved)

1. Environment-variable override: `LDRAW_LIBRARY_PATH` (project-name
   independent, per your instruction).
2. `stud_width`/`stud_length`/`height_units` are **not** derived from
   geometry — conservative, documented placeholder defaults instead
   (`1`, `1`, `24.0`). Only `part_number`, `filename`, `description`, and
   `bounding_box` are populated from confidently-available real data.
3. `PropertiesWidget` update treated as necessary compatibility work, not
   scope expansion.

---

# Definition of Done

- The application transparently uses a real installed LDraw library
  whenever one is found (override or standard location); every existing
  workflow (Renderer, Brick Library, Generate LEGO Mosaic) requires no
  changes from the user's perspective.
- The seed catalog remains a permanent, first-class fallback — not
  deleted, not deprecated.
- No persistent cache, no speculative metadata inference.

---

# Completion Notes

## Architecture

`PartCatalog.load_best_available()` is the one new entry point — it ties
detection (`find_ldraw_library()`) and building (`build_catalog_parts()`)
together with the seed fallback, so `Renderer` and `MainWindow` both call
the same function instead of duplicating fallback logic, and neither
needs to know which source produced the result (matching your pipeline
diagram's own stated goal). `PartCatalog.from_seed()` and
`load_seed_bricks()` are completely untouched — the seed catalog is
exactly as permanent as before, just no longer the *only* option.

**Within `MainWindow`**, one `PartCatalog` is built once (in
`create_widgets()`) and shared by `BrickLibraryWidget` and
`on_generate_lego()` — avoids re-parsing the library on every Generate
click. `Renderer.initialize()` builds its own separate instance (it runs
inside `ViewportWidget.initializeGL()`, with no natural wiring to
`MainWindow`'s instance without restructuring widget construction order)
— one known, accepted duplication, explicitly acceptable per your
"defer caching unless proven necessary" instruction, and currently moot
in this environment since there's no real library here to make it slow.

## Metadata — Exactly the Approved List

- `part_number` — from the filename stem.
- `ldraw_filename` — the literal filename.
- `name` / `description` — both reuse `Part.description` (the file's own
  first comment line) rather than inventing a second derivation.
- `bounding_box` — computed directly from resolved geometry (`min`/`max`
  over the fully-resolved vertex array — Package_006's recursive
  resolution makes this correct, not just a top-level-triangle
  approximation); `None` when a part has no geometry at all.
- `stud_width=1`, `stud_length=1`, `height_units=24.0`, `category="Part"`
  — fixed, documented placeholders on every library-derived
  `BrickDefinition`, regardless of the part's real size. **Verified
  directly** that these stay constant even across parts with very
  different real bounding-box extents (1 through 12 units in the test
  library) — confirming they are genuinely not derived from geometry,
  not just usually-correct-by-coincidence.
- `available_colors`, `weight_g`, `aliases`, `family` — untouched
  dataclass defaults (`[]`/`None`), exactly matching the seed catalog's
  own precedent for these fields.

## Robustness

- A malformed part file (bad numeric token) is logged and skipped —
  verified directly that it does not abort the rest of the catalog
  build.
- A part with zero geometry gets `bounding_box=None`, not a fabricated
  zero-size box.
- Non-`.dat` files in `parts/` are ignored.
- Primitives in `p/` are correctly excluded from the catalog (only
  top-level `parts/` entries become catalog items — `p/` holds building
  blocks referenced *by* parts, not standalone purchasable/placeable
  parts).
- **`Renderer.initialize()`'s demo-brick seeding previously had no
  None-check** on `catalog.get(...)` — a latent crash risk if a loaded
  catalog (real *or* seed) ever lacked `"3001"`/`"3003"`/`"3004"`.
  Refactored into a small loop with an explicit `if definition is None:
  continue` — **verified directly**, using the real-catalog test library
  (which genuinely lacks all three), that the demo scene now gracefully
  ends up with zero bricks rather than crashing.

## Verification Performed

All using a synthetic LDraw-like library (correct `parts/`+`p/` naming,
13 parts with real, varied geometry, one deliberately malformed part, one
deliberately empty-geometry part, a stray non-`.dat` file, and a
primitive in `p/`) via the `LDRAW_LIBRARY_PATH` override — the only
loader-compatible real-geometry source available in this environment (no
standard-location install exists here, and the repo-root duplicate
library has an incompatible `part`/`parts` naming, a separate,
already-flagged issue not addressed by this package).

- `py_compile` clean on all seven touched/new files.
- **Library locator**: env var name confirmed; no-override-and-no-standard-location
  case confirmed to correctly return `None` in this actual environment
  (not simulated); valid override returns the exact path; invalid
  override logs a warning and falls through to standard-location search
  rather than raising.
- **Catalog builder**: exactly the 12 valid synthetic parts built (13
  including the intentionally-empty-geometry one); malformed part
  correctly skipped without aborting the build; non-`.dat` file ignored;
  `p/` primitive correctly excluded; bounding boxes checked against
  hand-computed expected extents for two different parts (5-unit and
  12-unit); empty-geometry part confirmed `bounding_box=None`;
  placeholder defaults confirmed identical across parts with different
  real sizes (proving non-derivation, not coincidence).
- **`PartCatalog.load_best_available()`**: no library found → exact
  10-part seed catalog; library found → the real 13-part catalog is used
  *instead of* seed (not merged); `catalog.get()` confirmed to behave
  identically regardless of source.
- **`BrickLibraryWidget`**: new `(catalog, parent)` constructor;
  search/filter/selection re-verified against the shared catalog;
  confirmed `brick_selected` emits a real `BrickDefinition`.
- **`PropertiesWidget`**: `display_brick()` renders correct fields for a
  seed-catalog brick (with populated `available_colors`) and a
  library-derived brick (`available_colors` empty → shows "Unknown"
  gracefully, not a crash or blank).
- **Full `MainWindow` integration**, against a real GPU/GL context, in
  both states:
  - No library present: shared catalog has the 10 seed parts; demo scene
    has the expected 3 bricks; Brick Library shows 10 items.
  - Real library present (via override): shared catalog has the real 13
    parts; demo scene has **zero** bricks (proving the new None-check
    works, since none of 3001/3003/3004 exist in the test library) with
    no crash; Brick Library shows the real 13 items; Generate LEGO
    Mosaic run against a real catalog part (`9001.dat`) produced the
    correct brick count.
- **Performance measurement, as instructed**: building the 13-part
  synthetic catalog took ~3ms total (~0.23ms/part) over 5 runs. A rough
  linear extrapolation to a ~20,000-part real library suggests ~4.6
  seconds — but this is very likely an underestimate, since real parts
  resolve significantly more geometry per part (studs, connectors, via
  recursive subfile resolution) than these single-triangle synthetic
  test parts. **Not implementing caching**, per your instruction — see
  Recommendations below for what I'd measure/build if a real library
  later proves this too slow in practice.
- **Regression testing**: re-ran the full Package_003/005/007-014 suite
  — all still pass.
- **Live application verification**: `src/main.py` launches identically
  to Package_014 in its default state (no `LDRAW_LIBRARY_PATH` set, no
  standard location present) — same grid, same three missing-part
  warnings, no crash, no traceback.
- `git status`/`git diff` confirm exactly the planned seven files
  changed.

## Recommendations for Future Packages

- **Caching, if real-library startup proves too slow**: a fingerprint
  (SHA-256 over sorted `(filename, size, mtime)` tuples for every file in
  `parts/`, computed via `stat()` only, not full reads) stored alongside
  a JSON-serialized `list[BrickDefinition]`, in a StudWorks-owned
  location outside the LDraw install directory (e.g.
  `Path.home() / ".studworks" / "catalog_cache.json"` — writing into
  `C:\Program Files\LDraw` would plausibly fail on a non-admin Windows
  account). Rebuild automatically whenever the fingerprint changes; treat
  any cache-read failure exactly like a cache miss. Documented here per
  your instruction, not implemented.
- **Metadata enrichment**: `stud_width`/`stud_length`/`height_units`
  could be derived from `bounding_box` (1 stud = 20 LDU) once there's
  appetite for that inference; `category` could parse LDraw's optional
  `!CATEGORY` meta-command (not currently parsed by `LDrawParser`)
  instead of a flat placeholder. Both deliberately deferred here.
- **LDraw library consolidation** (Package_001's original finding: the
  repo-root duplicate library uses `part`/`parts` naming inconsistent
  with the loader's expectations) remains outstanding, unaffected by
  this package, and is why this package's real-data verification used a
  synthetic library rather than that repo-root data.
- All other prior packages' outstanding recommendations remain
  outstanding and unaffected.
