# StudWorks

# Package 037

## Title

Brick Catalog Enrichment — From Placeholder Metadata to Derived Geometric Fact

---

# Mission

Improve the quality of the production LEGO catalog identified in
Package_036's inspection as the primary blocker to meaningful
generation. No LEGO generation occurs in this package. Its purpose is
to transform the existing production catalog into a reliable source of
geometric and generation metadata.

---

# Scope

Modified:

- `services/ldraw_catalog_builder.py` — three new, independent, pure
  derivation helpers (`_derive_stud_footprint`, `_derive_height_units`,
  `_extract_category`); `build_catalog_parts()` now orchestrates them,
  applying each result only when independently validated
- `services/catalog_cache.py` — `CACHE_SCHEMA_VERSION` bumped 1 → 2

Tests:

- `tests/test_ldraw_catalog_builder.py` (new, 26 tests)
- `tests/test_catalog_cache.py` (new, 3 tests)

**Untouched — confirmed via `git diff --stat`**: `render/*`, `tools/*`,
`selection/*`, `transform/*`, `engine/*`, `ui/*`, `generation/*`,
`preparation/*`, `analysis/*`, `project/*`, and every file in `ldraw/`
(`parser.py`, `part.py`, `loader.py`, `library.py`). This package
touches only `services/ldraw_catalog_builder.py` and
`services/catalog_cache.py`.

---

# Inspection Findings

(Full detail in the approved planning turn; summarized here as the
basis for what got built.)

`build_catalog_parts()` already computed `bounding_box` from each
part's fully-resolved geometry (`LDrawLibrary.load()` recursively
flattens Type-1 subfile references, confirmed to include stud
geometry) but never converted it into `stud_width`/`stud_length`/
`height_units` — the raw material for partial enrichment was already
present and unused.

Empirically verified against a random 400-part sample of the real,
on-disk 24,297-part library: stud footprint reliably derivable for
~36%, height for ~54%, category (via an explicit `!CATEGORY` header
line) for ~23% — each field independently, not all-or-nothing. A first
hypothesis (derive height directly from full geometry Y-extent) was
wrong by exactly the real LEGO stud height (4 LDU) for every stud-bearing
seed part; a second hypothesis (derive category from the description's
leading word) matched the authoritative `!CATEGORY` value in only 3 of
488 cases and was discarded. `available_colors` and `family` have no
LDraw-native source at all (color tokens in geometry lines are
structural "inherit" sentinels, not availability data; no `!FAMILY`
convention exists) and were left untouched.

---

# Architecture Summary

Extended `build_catalog_parts()` in place — no new module, no new
pipeline stage, no duplicate geometry traversal. Three new private
helpers, each satisfying the approved independence requirements:

```python
def _derive_stud_footprint(bounding_box) -> tuple[int, int] | None:
    """Consumes only bounding_box. Whole-stud X/Z extent within
    tolerance, or None."""

def _derive_height_units(bounding_box) -> float | None:
    """Consumes only bounding_box. Y extent rounded down to the
    nearest 8 LDU plate unit, only if the remainder is close to 0 (no
    stud) or 4 (one stud layer); else None."""

def _extract_category(part_file: Path) -> str | None:
    """Consumes only the file path -- reads it directly and
    independently of the geometry parser. The '0 !CATEGORY <name>'
    header value if present in the first 40 lines; else None. No
    description-based guessing."""
```

None of the three calls another, or depends on another's output — each
was unit tested in complete isolation (e.g. `test_does_not_depend_on_height`,
`test_does_not_depend_on_footprint`, `test_does_not_depend_on_geometry`),
per the approved architectural requirement. `build_catalog_parts()`
computes `bounding_box` once (the single, unchanged source of geometric
truth), calls all three helpers against it independently, and applies
each result only when non-`None` — a part can end up with a real
footprint and a placeholder height, or any other combination; "unknown"
(the existing placeholder, unchanged) is a fully valid, expected
outcome, not a failure case.

`available_colors` and `family` are not touched anywhere in this
package — no inference, no guessing, exactly per the approved
requirement.

---

# Empirical Findings (shipped implementation, real library)

Run directly against the real, on-disk 24,297-part library in this
environment using the final, committed code (not the inspection-phase
prototype):

- **Total parts built: 24,297** — unchanged from before this package;
  no parts gained or lost.
- **Footprint derived (non-placeholder): 7,751 (31.9%)** — close to,
  slightly below, the 400-part sample's 36% estimate from planning;
  expected sampling variance between a 400-part sample and the full
  24,297-part population.
- **Category derived (non-placeholder): 5,628 (23.2%)** — an exact
  match to the raw header-scan figure gathered during planning,
  confirming the shipped `_extract_category` behaves identically to
  the validated prototype.
- **Full build time: 39.70s**, up from Package_023's own documented
  ~29s pre-enrichment baseline — the increase is the `_extract_category`
  helper's second file-open per part (a deliberate, isolated read,
  kept independent of the geometry parser per the architectural
  requirements). This cost is paid once per on-disk cache
  invalidation, not once per app launch — unchanged from the existing
  two-layer caching model, so no new performance concern.
- **Spot-checked known parts** against their seed-catalog equivalents:
  `3001` (Brick 2x4) → `stud_width=4, stud_length=2, height_units=24.0`
  — correct footprint and height, though notably **axis-assignment
  differs from the seed catalog's hand-curated labels** (seed:
  `stud_width=1, stud_length=2`, ordered narrow-first by naming
  convention; derived: axis-locked to the part's actual X/Z geometry,
  matching how `generate_mosaic()`/`generate_height_relief()` already
  consume these fields for world-space spacing). `3005` (Brick 1x1) →
  `(1, 1, 24.0)`, `3068` (Tile 2x2, no stud) → `(2, 2, 8.0)`, `3022`
  (Plate 2x2) → `(2, 2, 8.0)` — all correct. `category` stayed at the
  placeholder `"Part"` for all four (none of these specific files carry
  an explicit `!CATEGORY` header line) — an honest, expected result,
  not a defect.

**Real-world cache invalidation, verified against this environment's
actual pre-existing cache** (not just the synthetic unit test): this
machine already had an on-disk cache from earlier sessions, built under
`cache_schema_version=1` with every part still at the old placeholder
values (verified directly: sample part `1, 1, 24.0, "Part"`). Calling
`PartCatalog.load_best_available()` after this package's changes
correctly detected the stale schema version, rebuilt (33.07s, consistent
with a full rebuild rather than a cache hit), and wrote back a new cache
tagged `cache_schema_version=2` with the enriched values (`3001` now
`4, 2, 24.0, "Part"`). The on-disk cache read path itself remains fast
and unregressed: `load_cached_parts()` alone loads the full, enriched
24,297-part cache in ~1.5s, consistent with Package_023's own documented
figure.

---

# Validation Strategy Applied

- **Footprint/height consistency**: the per-field tolerance gates in
  §Architecture Summary *are* the validation — a value is assigned only
  if it round-trips cleanly; otherwise the existing, unchanged
  placeholder is kept.
- **Geometry consistency**: both geometric helpers guard against a
  `None`/degenerate (zero or negative extent) bounding box before
  attempting derivation.
- **Orientation correctness**: derivation operates on the same raw,
  LDraw-native (Y-down) coordinates `BrickManager._local_aabb()` already
  uses for rendering and picking — no new orientation assumption.
- **Placeholder detection**: exercised directly in
  `test_placeholder_fraction_drops_after_enrichment` and confirmed
  against the real catalog above (31.9%/23.2% non-placeholder) rather
  than only asserted in the abstract.

---

# Test Summary

- **26 tests, `tests/test_ldraw_catalog_builder.py`**: `_derive_stud_footprint`
  (clean 1x1 and 2x4, out-of-tolerance rejection, in-tolerance float
  noise accepted, sub-one-stud and zero-extent rejection, independence
  from height); `_derive_height_units` (no-stud exact match, one-stud
  offset correctly recognized, unrecognized remainder rejected,
  zero-extent rejection, independence from footprint); `_extract_category`
  (present, multi-word, absent, beyond the scan-line limit, missing
  file, independence from geometry); `build_catalog_parts()` integration
  against a small synthetic on-disk fixture library (a clean part with
  no category, a clean part with a category, a geometrically irregular
  part) — confirms derived values apply correctly, placeholders are
  fully preserved for the irregular part, `bounding_box` is unregressed,
  results are deterministic across repeated builds, and the
  placeholder-detection check.
- **3 tests, `tests/test_catalog_cache.py`**: `CACHE_SCHEMA_VERSION`
  equals 2; a cache written under the current schema loads back
  correctly; a cache manually downgraded to the prior schema version is
  correctly rejected (`None`) rather than silently served — using a
  temporarily redirected `LOCALAPPDATA` (`unittest.mock.patch.dict`,
  self-restoring) and a synthetic fixture library, not the real per-user
  cache location.

---

# Regression Results

Full suite: **265 tests**, all passing (236 pre-existing + 29 new).

---

# Scope Isolation Confirmation

`git diff --stat` confirms only `src/brickforge/services/ldraw_catalog_builder.py`
and `src/brickforge/services/catalog_cache.py` changed under `src/`.
`render/`, `tools/`, `selection/`, `transform/`, `engine/`, `ui/`,
`generation/`, `preparation/`, `analysis/`, `project/`, and every file
in `ldraw/` (including `parser.py`/`part.py`/`loader.py`/`library.py`,
deliberately left untouched per the approved plan's decision to read
category data independently rather than extend the shared `Part` type)
are completely untouched. An AST-based import check confirms
`ldraw_catalog_builder.py`'s dependency set is unchanged from before
this package (`brickforge.ldraw.library`, `brickforge.ldraw.library_layout`,
`brickforge.models.part_definition`, `logging`, `numpy`, `pathlib`) — no
new coupling introduced anywhere.

---

# Definition of Done

- A production metadata enrichment architecture exists — three
  independent, pure, unit-tested helpers plus orchestration inside the
  existing catalog builder.
- Placeholder metadata has an architectural replacement — verified
  against the real catalog: 31.9% of parts now carry a real footprint,
  23.2% a real category, with placeholders honestly preserved everywhere
  a derivation cannot be validated.
- The production catalog is now a meaningfully more reliable source of
  geometric metadata for a substantial minority of parts, with the
  remaining gap (irregular parts, and `available_colors`/`family`
  entirely) explicitly and honestly documented rather than papered over.
- The architecture is ready for the first generation engine — no
  interface changes to `BrickDefinition`/`PartCatalog`/`GenerationConstraints`/
  `candidates_for()` were needed; enrichment is transparent to every
  existing consumer.

---

# Recommendations for Future Packages

- `available_colors`/`family` remain unpopulated for every real part —
  genuinely require an external data source (BrickLink/Rebrickable/etc.),
  explicitly out of this package's scope.
- The ~16% of the real catalog with `~`-prefixed ("moved"/"obsolete")
  descriptions is a catalog-*composition* question (should these be
  excluded from candidate queries by default?), not a metadata-*quality*
  one — noted during inspection, not acted on here.
- A future generation engine could use the now-real `stud_width`/
  `stud_length`/`height_units`/`category` values directly via
  `generation/candidates.py`'s existing `candidates_for()` with zero
  further plumbing.
