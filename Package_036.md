# StudWorks

# Package 036

## Title

Generation Candidate System — The Searchable LEGO Design Space

---

# Mission

Establish the deterministic query architecture that lets a future
generation engine ask "what LEGO elements are valid candidates for
generation?", independent of any specific generation algorithm. No LEGO
model generation occurs in this package, and no existing generator is
modified.

---

# Scope

New:

- `generation/candidates.py` (`GenerationConstraints`, `candidates_for()`)

Modified:

- `project/project.py` — `Project.generation_constraints:
  GenerationConstraints | None`, with direct (not regenerate-on-load)
  serialization

Tests:

- `tests/test_generation_candidates.py` (new, 14 tests)
- `tests/test_project_serialization.py` — `ProjectGenerationConstraintsTests`
  (3 new tests)

**Untouched — confirmed via `git diff --stat`**: `render/*`, `tools/*`,
`selection/*`, `transform/*`, `engine/*`, `ui/*`, `ldraw/*`, `services/*`,
`analysis/*`, `preparation/*`. This package touches only
`generation/candidates.py` (new) and `project/project.py`.

---

# Inspection Findings

**`BrickDefinition` already is almost exactly the minimum data model this
mission asks for** — `part_number`, `name`, `category`, `ldraw_filename`,
`stud_width`, `stud_length`, `height_units`, `available_colors`,
`bounding_box`, `family`, already indexed by `PartCatalog` and already
threaded through every `GenerateCallable`
([generation_mode.py](src/brickforge/generation/generation_mode.py)).
The real gap wasn't a missing data model — it was a missing **query
layer**: `PartCatalog.get(part_number)` was the only lookup that existed;
nothing could answer "give me every part matching {color, size,
category}." Confirmed both existing generators
([mosaic_generator.py](src/brickforge/generation/mosaic_generator.py),
[height_relief_generator.py](src/brickforge/generation/height_relief_generator.py))
resolve exactly one fixed `default_part_number` and never consider
alternatives — "candidate selection" genuinely doesn't exist anywhere
yet.

**A critical, empirically-confirmed data-completeness gap, found by
reading `services/ldraw_catalog_builder.py` directly and verifying its
consequence with a synthetic 24,297-part catalog** (matching Package_023's
measured real library size): `build_catalog_parts()` — which backs
`PartCatalog.load_best_available()`, the catalog actually used at
runtime — builds every real, LDraw-library-derived part with **uniform
placeholder values**: `stud_width=1, stud_length=1, height_units=24.0,
category="Part", available_colors=[]`, `family` left unset. Its own
docstring confirms this is deliberate, deferred work. **Practical
consequence, verified**: any color/category/family/dimension constraint
returns few or zero results against the real production catalog today —
every real part reports identical metadata on every field this package
filters by. Only the 9-part hand-curated seed catalog has real,
differentiated values. The query architecture built here is correct and
ready; the data it operates on is currently placeholder-only outside the
seed catalog. This is a pre-existing gap this package does not fix (that
module's own docstring calls it out as separate "metadata-enrichment
work"), but it materially affects this package's real-world value today,
so it's documented prominently rather than quietly built around.

**Existing "unknown vs. excluded" precedent, found in
[properties_widget.py:34-39](src/brickforge/ui/widgets/properties_widget.py)**:
an empty `available_colors` list already displays as *"Unknown,"* not
*"no colors permitted."* Used as precedent for reading this field, but
deliberately **not** carried into filtering semantics — see Constraint
Model below.

**`PartCatalog` is never Project-owned** — confirmed via
`services/catalog_cache.py`: loaded once at app startup
(`MainWindow.catalog`), cached in a per-user pickle file keyed by library
path + fingerprint, entirely outside `.sws`. This bounds candidate data
to the app level, not Project level.

**No inventory infrastructure exists anywhere** — `bricklink/` is an
empty stub package (confirmed via directory listing); the only
"inventory" reference in the codebase is `generation_mode.py`'s own
docstring explicitly disclaiming it as out of a generation mode's
responsibility.

**Empirically verified before implementation**: `PartCatalog.all()`
preserves deterministic insertion order across repeated calls (checked
directly against a synthetic catalog, not assumed). A linear-scan filter
with several simultaneous constraints over 24,297 synthetic parts takes
~11ms per call — no indexing or caching needed at this scale.

---

# Architecture Assessment

No new part-level data model was needed — `BrickDefinition`/`PartCatalog`
already fill that role. What was missing was exactly two small, additive
pieces: a constraint/settings type describing what's permitted, and a
pure query function applying it. Every prior package this session has
converged on "plain function over a plain dataclass," not a class with
methods, for pipeline stages (`prepare_image`, `analyze_image`,
`optimize_scene`) — the same reasoning applies here: no `CandidateProvider`
class, no `GenerationCatalog` wrapper, no registry (unlike `GenerationMode`,
there's only one query strategy needed, not several pluggable ones).

---

# Generation Candidate Architecture Recommendation

`generation/candidates.py` — naming mirrors the existing
`generation/generation_mode.py`'s in-package convention; placed inside
the existing `generation/` package (not a new top-level package like
`analysis/`/`preparation/`) since this is generation-specific
infrastructure, unlike those two which have broader applicability beyond
generation:

```python
@dataclass(slots=True)
class GenerationConstraints:
    permitted_colors: list[int] | None = None
    permitted_categories: list[str] | None = None
    permitted_families: list[str] | None = None
    min_stud_width: int | None = None
    max_stud_width: int | None = None
    min_stud_length: int | None = None
    max_stud_length: int | None = None
    excluded_part_numbers: list[str] = field(default_factory=list)


def candidates_for(
    catalog: PartCatalog,
    constraints: GenerationConstraints | None = None,
) -> list[BrickDefinition]:
    ...
```

`candidates_for()` returns a plain `list[BrickDefinition]`, matching
`PartCatalog.all()`'s own existing return shape — no `CandidateSet`
wrapper type; no evidenced need yet for extra state (caching, provenance)
that would justify one.

---

# Constraint Model Recommendation

Each list-type field: **`None` means unconstrained; an explicit `[]`
means constrained to nothing** — Python's `None`-vs-empty-collection
distinction maps cleanly onto "not specified" vs. "specified as empty,"
avoiding the ambiguity a single "empty means don't care" rule would
introduce. `excluded_part_numbers` alone defaults to `[]`, since "no
exclusions" has no meaningful `None`/`[]` distinction.

Scoped to stud **width/length** only, not height — neither existing
generator selects a part *by* height (mosaic doesn't use it at all;
height-relief only stacks a fixed part by height count, never chooses
parts by it), so a height constraint has no evidenced consumer.

**Inventory restrictions explicitly deferred** — no infrastructure exists
to check against (confirmed empty `bricklink/` package); adding even a
stub field would be exactly the speculative scaffolding this project
avoids.

**`permitted_families` included** despite being inert everywhere today
(`family` is unset on every seed *and* real part currently) — cheap,
mission-requested, the field already exists on `BrickDefinition`, and
it's ready the moment it's populated.

**Matching against placeholder/incomplete metadata is strict, not
permissive** — a part with `available_colors == []` (the real catalog's
"not yet measured" placeholder) never satisfies a `permitted_colors`
constraint, even though the UI already treats that same emptiness as
"Unknown" for *display*. Considered extending that display-only
precedent into filtering behavior (treat unknown as "don't exclude") and
rejected it: a query system should never silently pretend to satisfy a
constraint it can't verify. The visible consequence — most constrained
queries return few or no results against the real catalog — is an honest
signal of the real metadata gap, not a bug to hide.

---

# Query Architecture Recommendation

One general entry point, `candidates_for(catalog, constraints)`, rather
than separate `candidates_for_color()`/`candidates_for_category()`/
`candidates_for_dimensions()` functions — the mission's three example
query shapes are each just one `GenerationConstraints` field left
populated with the rest at their `None` default; three near-duplicate
functions would be the "premature complexity" the mission explicitly
warns against. Scales to new constraint types by adding a field and a
clause, not a new function.

---

# Project Ownership Recommendation

`Project` gains `generation_constraints: GenerationConstraints | None =
None`. This is architecturally different from `generation_input`'s
"store reference, regenerate on load" pattern: `GenerationConstraints` is
pure user intent (which colors/sizes/categories a project should
generate with), not derived from anything, so there's nothing to
regenerate — losing it on reload would mean losing real configuration,
unlike `analysis`, which is safely reconstructable from `prepared_image`.

`PartCatalog` itself, and any candidate query *results*, remain outside
Project ownership — confirmed above that `PartCatalog` lives entirely at
the app level. "Candidate settings" (from the mission text) is treated as
the same concept as "active generation constraints" — no evidence was
found for a second, meaningfully distinct type. "Inventory preferences":
not added, per the Constraint Model section.

---

# Serialization Recommendation

`GenerationConstraints` is flat, already-JSON-native data (`list[int]`,
`list[str]`, `int`, `None`) — no numpy, no regenerate-vs-store tension at
all, the simplest serialization case in this project so far. Stored
verbatim, key omitted when `None` (mirrors `generation_input`'s existing
omit-when-absent convention):

```json
"generation_constraints": {
    "permitted_colors": [4, 14, 15],
    "permitted_categories": ["Brick", "Plate"],
    "permitted_families": null,
    "min_stud_width": 1, "max_stud_width": 4,
    "min_stud_length": null, "max_stud_length": null,
    "excluded_part_numbers": ["3068"]
}
```

`from_dict()` reconstructs directly — no external-file dependency, so
(unlike `generation_input`) there is no missing-source graceful
degradation case.

---

# Definition of Done

- `GenerationConstraints` and `candidates_for()` exist and are fully
  deterministic — verified against a hand-built fixture catalog covering
  every constraint axis in isolation and combined.
- `Project.generation_constraints` round-trips through save/load with
  zero data loss, including the `None`-vs-`[]` distinction.
- No existing generator, or any of `render/`, `tools/`, `selection/`,
  `transform/`, `engine/`, `ui/`, `ldraw/`, `services/`, `analysis/`,
  `preparation/`, is touched — confirmed via `git diff --stat`.
- The real, production catalog's metadata-completeness gap is documented,
  not silently worked around.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- `git diff --stat` confirms `render/`, `tools/`, `selection/`,
  `transform/`, `engine/`, `ui/`, `ldraw/`, `services/`, `analysis/`,
  `preparation/` are **completely untouched** — this package touches only
  `generation/candidates.py` (new) and `project/project.py`.
- AST-based import check: `candidates.py` imports only `dataclasses`,
  `brickforge.models.part_definition`, and
  `brickforge.services.part_catalog` — no engine/render/UI coupling,
  matching its own documented boundary claim.
- Empirically verified before implementation, not assumed:
  `PartCatalog.all()`'s deterministic insertion-order guarantee; a
  24,297-synthetic-part linear-scan filter's real timing (~11ms/call,
  justifying "no indexing needed" without guessing).
- **14 tests, `test_generation_candidates.py`**: no-constraints returns
  the full catalog in order; each constraint field in isolation (color,
  category, family, min/max width, min/max length, exclusions) against a
  4-part fixture catalog including one "placeholder metadata" part
  (`available_colors=[]`, `category="Part"`, `family=None`, matching what
  the real catalog actually produces); combined AND-semantics across
  simultaneous constraints; the `None`-vs-explicit-`[]` distinction for
  `permitted_colors`; the placeholder part confirmed excluded (not
  silently matched) by any color constraint; determinism across repeated
  calls.
- **3 new tests in `test_project_serialization.py`**: a project with no
  `generation_constraints` has no such key in its serialized output; a
  real round-trip (Save → Open) through `ProjectManager` preserves every
  field exactly, including `None` fields; an explicit empty
  `permitted_colors=[]` round-trips as `[]`, not `None` — proving the
  distinction survives serialization, not just construction. All 13
  pre-existing tests in this file, including the byte-for-byte golden-file
  comparisons, re-confirmed passing unchanged, since `generation_constraints`
  is a purely additive, optional field.
- Full regression suite re-run: **236 tests** across all suites — all
  pass.
- `git status` confirms exactly the planned scope.

---

# Recommendations for Future Packages

- **Highest-value next step, surfaced by this package's own inspection**:
  populating real `stud_width`/`stud_length`/`height_units`/`category`/
  `available_colors`/`family` values in `build_catalog_parts()`
  (`services/ldraw_catalog_builder.py`) from actual LDraw geometry/
  metadata, rather than uniform placeholders. Without it, neither this
  package's candidate queries nor the existing generators' spacing logic
  can meaningfully differentiate any of the ~24,000 real, non-seed parts.
- A Generation Engine package that actually consumes `candidates_for()`
  and `Project.generation_constraints`, replacing the existing
  generators' single-fixed-part model — not built here, per this
  package's explicit "no generation" scope boundary.
- `PaletteEngine.map_color()` matching against all solid LDraw colors,
  unfiltered by a specific candidate's `available_colors`, remains an
  outstanding, unaffected gap for a future Generation Engine to close.
