# StudWorks

# Package 007

## Title

Brick Intelligence Foundation

---

# Mission

Teach StudWorks what LEGO parts are — part number, dimensions, colors,
LDraw filename, and metadata useful for future AI reasoning — so future
packages (AI-driven part selection, BrickLink Studio export) have a real
data foundation to build on. Improves internal knowledge, not the UI.

---

# Scope

New files only:

- `src/brickforge/ldraw/ldraw_colors.py`
- `src/brickforge/models/part_definition.py`
- `src/brickforge/services/part_catalog.py`

No existing file changes.

---

# Definition of Done

- `BrickDefinition` (catalog part-type data) is clearly distinct from
  `models.brick.Brick` (UI display row, untouched) and
  `engine.scene_brick.SceneBrick` (placed instance, untouched).
- `available_colors` stores LDraw color IDs (`list[int]`), not RGB values.
- Optional metadata fields (`weight_g`, `aliases`, `family`) exist with
  appropriate defaults, unpopulated beyond seed data.
- `ldraw_colors.py` parses the real, already-present `LDConfig.ldr` — not
  a hardcoded/synthetic color list.
- `PartCatalog` loads seed data and any future data source through the
  same constructor — no architecture that assumes only the initial seed.
- `models/brick.py`, `services/brick_database.py`, all `ui/` files,
  `engine/`, `render/`, and all four Package_006 `ldraw/` files are
  byte-for-byte untouched.
- `py_compile` clean; live run confirms no regression.

---

# Completion Notes

## Architectural Reasoning

**Why a new abstraction rather than extending `Brick`:** `Brick.color` is a
single free-text field; "available colors" is inherently one-to-many (a
part is molded in many colors) and can't be shoehorned into that field
without a breaking change. `properties_widget.py` and
`brick_library_widget.py` actively consume `Brick`'s exact current shape —
changing it would touch UI code, explicitly excluded from this package.
Introducing `BrickDefinition` as a sibling, not a replacement, means zero
risk to the working catalog browser.

**Naming**, per your direction: `BrickDefinition` (catalog part-type data)
sits alongside `SceneBrick` (placed instance) as the long-term two-concept
split, with the existing UI-only `Brick` left as a third, separate,
untouched concept.

**Same loading path for today's seed data and tomorrow's full catalog**:
`PartCatalog.__init__` takes any `Iterable[BrickDefinition]` — it has no
knowledge of where entries came from. `load_seed_bricks()` (today's 10
hand-curated entries) and `PartCatalog.from_seed()` are just the current
*caller* of that constructor; a future loader deriving `BrickDefinition`s
from the full LDraw parts library would return the same
`list[BrickDefinition]` shape and pass through the identical constructor —
verified directly by constructing a `PartCatalog` from an
externally-supplied list that never touches `load_seed_bricks()` at all
(see Verification).

**Why `ldraw_colors.py` lives in `ldraw/`, not `models/`**: parsing
`LDConfig.ldr` is LDraw-file-format parsing, the same domain as
`parser.py`/`loader.py`. `BrickDefinition.available_colors` stores LDraw
color *codes* (`list[int]`) rather than duplicating color data — resolving
a code to its name/hex goes through `ldraw_colors.load_ldraw_colors()`
on demand. Named `ldraw_colors.py` rather than `colors.py`, per your
direction, so BrickLink/LEGO/Studio/rendering-material color systems can
be added later as siblings without a name collision.

## Exact Implementation

- **`ldraw/ldraw_colors.py`**: `LDrawColor` dataclass (`code`, `name`,
  `hex`, `edge_hex`) and `load_ldraw_colors(config_path)`, which regex-parses
  `0 !COLOUR <name> ... CODE <n> VALUE #RRGGBB EDGE #RRGGBB` lines from an
  `LDConfig.ldr` file into a `dict[int, LDrawColor]`. Trailing tokens
  (`ALPHA`, `LUMINANCE`, `MATERIAL`, present on some special colors) are
  tolerated since the regex isn't anchored at end-of-line.
- **`models/part_definition.py`**: `BoundingBox` (`min`/`max` 3-tuples, LDraw
  units) and `BrickDefinition` — `part_number`, `name`, `category`,
  `ldraw_filename`, `stud_width`, `stud_length`, `height_units`,
  `available_colors: list[int]` (default empty), `bounding_box:
  BoundingBox | None` (default `None` — no real geometry exists to compute
  one from yet), `description` (default `""`), and the three new optional
  fields: `weight_g: float | None = None`, `aliases: list[str]` (default
  empty), `family: str | None = None`.
- **`services/part_catalog.py`**: `load_seed_bricks()` returns 10
  `BrickDefinition`s — the same 10 part numbers already in `BrickDatabase`,
  now with real dimensions (`stud_width`/`stud_length`/`height_units` —
  bricks at 24 LDraw height-units, plates and the tile at 8) and real,
  verified LDraw color codes (`0` Black, `1` Blue, `2` Green, `4` Red, `14`
  Yellow, `15` White — each independently confirmed against the actual
  `LDConfig.ldr`, not guessed). `PartCatalog` wraps any
  `Iterable[BrickDefinition]` into a `part_number`-keyed lookup, with
  `.all()`, `.get(part_number)`, and `.from_seed()` as one particular,
  swappable source.

## Verification Performed

- **Unit verification**: `BrickDefinition` and `BoundingBox` constructed
  directly; confirmed `bounding_box=None`, `available_colors=[]`,
  `weight_g=None`, `aliases=[]`, `family=None` defaults.
- **Real-data parsing check**: parsed the actual `LDConfig.ldr` already in
  the repo (not synthetic). Confirmed `colors[4] == Red #B40000`,
  `colors[14] == Yellow #FAC80A`, `colors[15] == White #F4F4F4`,
  `colors[0] == Black`, `colors[1] == Blue`, `colors[2] == Green` — exact
  matches. Parsed color count (**322**) matches an independent
  `grep -c "^0 !COLOUR"` count on the same file exactly, confirming no
  lines were dropped or misparsed.
- **Same-loading-path architecture check**: built a `PartCatalog` from an
  externally-supplied `list[BrickDefinition]` that never calls
  `load_seed_bricks()` or `from_seed()` — confirmed lookup works
  identically, proving the constructor doesn't assume the seed source is
  the only source.
- **Data integrity**: no duplicate `part_number`s across the 10 seed
  entries; every `available_colors` code in every seed entry resolves in
  the real parsed color table (cross-validating the two new data sources
  against each other); every seed's `ldraw_filename` matches the
  `f"{part_number}.dat"` convention; confirmed the catalog covers every
  `part_name` `renderer.py` actually seeds into the `Scene`
  (`3001.dat`/`3003.dat`/`3004.dat`) as a real-world cross-check.
- **Backward compatibility**: `git status` confirms `models/brick.py`,
  `services/brick_database.py`, and every file under `ui/` are
  byte-for-byte untouched. Re-ran `BrickDatabase().all()` directly —
  identical 10 `Brick` objects, same fields, same values as before.
- **No regressions**: re-ran Package_003's `Scene` API checks and
  Package_005's `u_model` matrix-composition checks — both still pass,
  confirming `engine/`/`render/` are unaffected. `py_compile` clean on all
  three new files. Live run of `src/main.py`: identical to Package_006 —
  grid renders, all 3 seeded bricks log a missing-part warning (both
  searched paths shown) and are skipped gracefully, no crash, no
  traceback, app stays alive.
- `git status` confirms only the three new files were added — no existing
  file modified.

## Recommendations for Future Packages

- **`bounding_box` remains unpopulated.** Once the real LDraw parts
  library exists, a future package could compute it directly from a
  resolved `Part.vertices` (Package_006's recursive resolution already
  produces complete, flattened geometry) — this package only defines the
  field, deliberately not the computation, to stay within "new files only."
- **BrickLink-specific ID mapping** (distinct from LDraw color/part codes)
  remains unimplemented — needed only for direct BrickLink API/cart
  integration, not for basic LDraw-format Studio-compatible export. The
  empty `bricklink/` stub package is presumably reserved for this.
- **`render/material.py` remains an empty stub.** This package produces
  color *data* (LDraw codes, names, hex values); wiring any of it into
  actual rendering is a `render/` change, explicitly out of scope here.
- **Catalog/`SceneBrick` bridging** (constructing a `SceneBrick` from a
  selected `BrickDefinition`) remains unimplemented — flagged since
  Package_002, still the natural eventual connective step, still deferred.
- **"Commonly buildable" classification** (distinguishing basic
  bricks/plates/tiles from the tens of thousands of rare/specialty LDraw
  parts) was considered for the AI-reasoning use case but deliberately not
  added — speculative without a concrete near-term consumer; the schema's
  optional fields (`family`, `aliases`) leave room for it later without a
  breaking change.
- LDraw library consolidation (Package_001) and full LDraw-derived catalog
  loading (this package's `PartCatalog` is architecturally ready for it,
  per requirement 2) remain outstanding future work.
