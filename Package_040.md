# StudWorks

# Package 040

## Title

Build Validation — Read-Only Structural Checks on What the Data Supports

---

# Mission

Implement the first structural validation stage: `validate_scene()`
receives an immutable Scene and returns a deterministic
`ValidationReport`, without ever modifying the Scene, catalog, or
Project. Generation decides what to build; optimization improves it;
validation only reports whether the result satisfies rules this
codebase's actual data can support — nothing is repaired, and nothing
about the represented image is reinterpreted.

---

# Scope

New:

- `validation/__init__.py` (empty, matching `analysis/`/`preparation/`'s
  own convention — no registry needed for four always-run rules)
- `validation/build_validation.py` (`ValidationSeverity`,
  `ValidationIssue`, `ValidationReport`, four independent rule
  functions, `validate_scene()`)

Tests:

- `tests/test_build_validation.py` (new, 26 tests)

**Untouched — confirmed via `git diff --stat`**: `engine/`, `render/`,
`selection/`, `transform/`, `serialization/`, `export/`, `project/`,
`ui/`, `generation/`, `optimization/`, `services/`, `ldraw/`. This
package adds exactly one new top-level package plus one test file.

---

# Inspection Findings

(Full detail in the approved planning turn.) Confirmed directly by
reading `Scene.add_brick()`: nothing prevents two `SceneBrick`s sharing
an id — a real, currently undetected condition, not a hypothetical one.
A `transform/scene_transform.py` comment confirms directly in its own
words that overlap has never been prevented anywhere in this codebase.
No connectivity, clutch-power, or structural-strength data exists
anywhere (confirmed via grep) — these must be deferred, not
approximated.

`BrickDefinition.bounding_box` is `None` for every seed-catalog part
(confirmed by reading `load_seed_bricks()`) despite the seed catalog
being the app's most metadata-reliable source — `stud_width`/
`stud_length`/`height_units` (always present, either genuinely derived
or a documented Package_037 placeholder) were used instead, matching
every other pipeline stage's existing reliance on those same fields.
`render/picking.py`'s geometry is ray-based, not box-vs-box, and
deliberately not reused — keeping `validation/` independent of
`render/`, matching every other pipeline package's own discipline.

Empirically verified before writing any production code:
quaternion-length drift from 200 accumulated rotation multiplications
is ~2×10⁻⁶ (corrected during implementation from an initial,
incorrectly-simulated ~1×10⁻⁷ estimate — see Test Summary); a
rotation-aware world-space AABB computes correctly for both identity
and 90°-rotated cases; the same overlap check produces **zero false
positives** against a real `generate_scene()` output (16 normally
tiled, edge-to-edge bricks); a worst-case 2,304-brick pairwise check
(the default `max_dimension=48` ceiling) completes in 1.84s — acceptable
for a once-per-Scene check, no spatial indexing added without stronger
evidence it's needed.

---

# Architecture Assessment

New top-level package `validation/`, matching `analysis/`/
`preparation/`/`optimization/`/`generation/` each owning one major
pipeline stage. No registry: unlike `GenerationMode`/`Optimizer`,
validation rules are not independently user-selectable — all four
always run as one pass, so a registry would be unjustified indirection.
Each rule is a standalone, independent pure function per the approved
architectural requirements — `_find_overlapping_bricks()` builds its
own `part_index` rather than reusing `_find_invalid_part_references()`'s,
a small, deliberate duplication in exchange for genuine independence,
matching the same choice both Package_039 optimizers already made.

---

# Validation Architecture Recommendation

```python
def _find_duplicate_ids(scene) -> list[ValidationIssue]: ...            # ERROR
def _find_invalid_part_references(scene, catalog) -> list[ValidationIssue]: ...  # WARNING
def _find_invalid_orientations(scene) -> list[ValidationIssue]: ...     # ERROR
def _find_overlapping_bricks(scene, catalog) -> list[ValidationIssue]: ... # WARNING

def validate_scene(scene: Scene, catalog: PartCatalog) -> ValidationReport:
    issues = []
    issues.extend(_find_duplicate_ids(scene))
    issues.extend(_find_invalid_part_references(scene, catalog))
    issues.extend(_find_invalid_orientations(scene))
    issues.extend(_find_overlapping_bricks(scene, catalog))
    return ValidationReport(issues=tuple(issues))
```

**Deterministic ordering, by explicit design**: issues are ordered
first by this fixed rule sequence, then by each rule's own internal
result — which itself follows the Scene's own iteration order (matching
`export_scene()`'s established "Scene's own existing order is already
deterministic" precedent), never incidental dict/set iteration. Sets
and dicts are used only for O(1) membership testing inside individual
rules, never iterated for output order.

**Overlap geometry helpers are private** (`_world_aabb`,
`_aabbs_overlap`), per the approved requirement — no reusable geometry
abstraction was introduced; `render/picking.py`'s ray-based geometry
solves a different problem and wasn't a candidate for reuse anyway.

**Severity distinction, documented in the module itself**: `ERROR`
means the data is objectively invalid regardless of which catalog is
active (a duplicate id, a non-unit quaternion). `WARNING` means the
finding's accuracy is bounded by catalog metadata completeness — an
unresolved part reference may still be valid in BrickLink's own
library (the same reasoning `export_scene()` already applies rather
than dropping unrecognized parts), and overlap detection is only as
reliable as the catalog's declared dimensions, which Package_037 showed
are placeholder values for most real, non-seed-catalog parts.

**Explicitly deferred, not approximated**: disconnected-component
detection would need real stud/tube connectivity data that doesn't
exist anywhere in this codebase — a geometric-adjacency proxy was
considered and rejected as exactly the unsupported approximation this
package's mission warns against. Structural strength, stability, and
clutch power have no data source at all.

---

# Validation Result Recommendation

```python
class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"

@dataclass(frozen=True, slots=True)
class ValidationIssue:
    rule_id: str
    severity: ValidationSeverity
    message: str
    brick_ids: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not any(i.severity is ValidationSeverity.ERROR for i in self.issues)
```

Both `frozen=True` — immutable value objects, never owned by `Scene`,
matching the approved requirement directly. `is_valid` is defined
purely by absence of `ERROR`-severity issues; a warnings-only report is
still considered valid.

---

# Public API Recommendation

One function: `validate_scene(scene: Scene, catalog: PartCatalog) ->
ValidationReport`. No `constraints` parameter — this mission's own
determinism section lists only `Scene, catalog`, and validation
concerns structural soundness, not a user's generation preferences. No
UI wiring in this package, matching Packages 038–039's own precedent.

---

# Test Summary

**26 tests, `tests/test_build_validation.py`**:

- Per-rule unit tests using hand-built Scene fixtures (no dependency on
  the real installed LDraw library): duplicate ids correctly flagged
  (and only once per duplicated id), unique ids pass; unresolvable part
  references correctly flagged as `WARNING`; identity and ordinary
  rotations pass, a deliberately non-unit quaternion is flagged as
  `ERROR`; same-position and edge-adjacent overlap cases (the latter
  must **not** false-positive — the critical case for any real
  generated Scene), an unresolvable-part brick correctly skipped rather
  than flagged by this rule, and a genuinely discriminating
  rotation-accounted-for case (a 3010 rotated 90° no longer overlaps a
  brick its unrotated footprint would have reached — verified both ways
  before writing the test).
- **A test-writing bug caught and fixed during implementation, worth
  recording**: the first version of the "heavily chained rotation"
  test used `rotation = rotation * rotation` (repeated squaring, which
  explodes the angle exponentially) instead of `rotation = rotation *
  base` (repeated accumulation, matching how rotation actually compounds
  under real, repeated edits). The squaring version produced a
  degenerate, near-zero-length quaternion and failed the test it was
  meant to pass — caught immediately by running the suite, not assumed
  correct. Fixed to accumulate against a fixed base rotation, matching
  Package_030's own original drift-measurement methodology; re-measured
  drift at 200 iterations is ~2×10⁻⁶, comfortably inside the
  `1e-3` tolerance.
- `validate_scene()` orchestration: a clean Scene is valid with zero
  issues; multiple simultaneous problems are all reported together;
  warnings alone don't invalidate; issue ordering is explicitly rule-
  then-scene-order, verified directly, not assumed; determinism across
  repeated calls (frozen dataclasses compared directly by value); no
  mutation of `Scene` or `catalog`; a validated Scene still serializes
  through the existing, unmodified `scene_to_document()`/
  `document_to_scene()`.
- `ValidationIssue`/`ValidationReport` immutability: both raise
  `dataclasses.FrozenInstanceError` on attempted attribute assignment.
- The exact empirical "zero false positives" check performed during
  planning, turned into a permanent regression test against real
  `generate_scene()` output.

---

# Regression Results

Full suite: **324 tests**, all passing (298 pre-existing + 26 new).

---

# Scope Isolation Confirmation

`git status`/`git diff --stat` confirm the only change is the addition
of `src/brickforge/validation/` (two files) and
`tests/test_build_validation.py`. `engine/`, `render/`, `selection/`,
`transform/`, `serialization/`, `export/`, `project/`, `ui/`,
`generation/`, `optimization/`, `services/`, `ldraw/` are completely
untouched. An AST-based import check confirms `build_validation.py`
depends only on `brickforge.engine.scene`,
`brickforge.engine.scene_brick`, `brickforge.models.part_definition`,
`brickforge.services.part_catalog`, `dataclasses`, `enum`, and `glm` —
no render/UI/generation/optimization coupling anywhere.

---

# Definition of Done

- A deterministic Build Validation stage exists — `validate_scene()`,
  composed of four independent, pure, individually-tested rules.
- Validation never mutates the Scene — verified directly, not just
  asserted.
- Validation reports issues without repairing them — every rule only
  ever appends a `ValidationIssue`; nothing in this package writes to a
  `Scene`.
- Every implemented rule is directly supported by available project
  data — duplicate ids (Scene's own structure), invalid part references
  and overlap (catalog data), invalid orientations (pure math on
  `SceneBrick.rotation`).
- Unsupported rules are explicitly documented and deferred — see
  "Current Validation Limitations" below.
- Existing downstream systems require no modification — verified
  directly against serialization.

---

# Current Validation Limitations (deliberate, not defects)

- Disconnected-component detection is not implemented — real stud/tube
  connectivity data doesn't exist anywhere in this codebase, and a
  geometric-adjacency proxy would be exactly the unsupported
  approximation this package's mission explicitly warns against.
- No structural strength, stability, or clutch-power validation — no
  physical metadata source exists at all.
- Overlap and invalid-part-reference findings are `WARNING`, not
  `ERROR`, specifically because they inherit Package_037's known
  catalog-metadata gap: most real, non-seed-catalog parts still report
  placeholder dimensions, so a finding's accuracy is bounded by catalog
  quality, not just Scene correctness.
- No UI wiring — matches Packages 038–039's own precedent; nothing in
  this package's Definition of Done required it.
