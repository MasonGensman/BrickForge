# StudWorks

# Package 025

## Title

Scene Serialization — StudWorks' Native Scene Format

---

# Mission

Define StudWorks' native, deterministic, versioned Scene serialization
format — how a `Scene` is represented on disk. Not a project manager,
not save/load UI, not session management: purely the `Scene ↔ file`
conversion.

---

# Scope

New package `serialization/` (zero existing files touched):

- `serialization/schema.py`
- `serialization/serializer.py`
- `serialization/deserializer.py`
- `serialization/__init__.py`

Tests:

- `tests/golden/scenes/{empty_scene,single_brick,multi_brick_scene,rotated_brick}.json`
- `tests/test_scene_serialization.py`

Untouched (verified via `git diff`, not assumed): `generation/*`,
`optimization/*`, `ui/*`, `render/*`, `engine/*`, `preparation/*`,
`export/*`, `services/*`, `models/*`, `ldraw/*`.

---

# Inspection Findings

**`Scene`/`SceneBrick`/`BrickDefinition`/`PartCatalog`** — confirmed
`SceneBrick` has never carried resolved `BrickDefinition` data; every
existing consumer resolves that fresh from a `PartCatalog` by
reference (`part_name`). Serialization preserves this exact
architecture: store only the reference, never embed catalog data.

**A meaningful difference from Package_024's exporter**: the mission's
validation checklist never mentions unrecognized part names (unlike
Package_024's, which explicitly did) — read as intentional:
serialization is a structural/byte-level concern, not a
semantic/catalog one. **`serialize_scene`/`deserialize_scene` take no
`PartCatalog` parameter at all** — simpler and more decoupled than the
exporter's `export_scene(scene, catalog, path)`.

**Package_024's number formatting must not be reused**: its `.6f`
truncation and near-zero normalization are deliberately lossy, correct
for clean LDraw output but wrong here, where exact round-trip fidelity
is the goal. Verified empirically that Python's `json` module encodes
floats via shortest-round-trip representation, reproducing every
float64 test value (`-0.0`, `~1e-7` noise, `1e20`) bit-for-bit — no
custom formatting needed.

**A real, non-obvious finding surfaced during verification**: `glm.vec3`/
`glm.quat` inherently store components as **float32**, not float64 — a
value is already truncated the moment it enters a `SceneBrick`, true
throughout this entire codebase, not something serialization
introduces. My first round-trip test compared against the wrong
"expected" value (the pre-`glm` float64 literal) and failed; fixed by
comparing against what's actually stored. Documented directly in
`serializer.py` so a future reader doesn't misunderstand what "exact
round-trip fidelity" means here.

**PyGLM's `quat` constructor argument order verified empirically**,
not assumed: `glm.quat(w, x, y, z)` — confirmed by round-tripping a
known `glm.angleAxis()` result through both possible orderings and
checking which one matches.

---

# Decisions Applied (per your approval)

1. **`id` included in the schema.** A serialized Scene preserves the
   complete identity of every `SceneBrick`, not merely its visible
   geometry — matters for `Scene.remove_brick`, matters more as
   editing features are added later.
2. **Top-level `"format": "StudWorks Scene"` identifier**, checked
   *before* `schema_version`, so an unrelated JSON file is rejected
   with a clear, specific error rather than a confusing "unknown
   schema version" message.

---

# Format: JSON

Chosen over MessagePack/CBOR (binary, fail "human-readable" and "easy
to diff" outright, and both would need a new dependency) and
YAML/TOML (new dependency for JSON, or a poor fit for a list of many
similar records). Pretty-printed (`indent=2`) for genuine diffability.

---

# Schema (version 1)

```json
{
  "format": "StudWorks Scene",
  "schema_version": 1,
  "bricks": [
    {
      "id": 0,
      "part_name": "3005.dat",
      "position": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "color_code": 4
    }
  ]
}
```

`rotation` is the quaternion's native `[x, y, z, w]` components
directly — not LDraw's 3×3 matrix (that conversion is export-specific,
not this format's concern). `color_code` is `null` or an integer.
Bricks are written in the `Scene`'s own existing order — already
deterministic transitively from whichever pipeline stages produced it,
so no re-sorting.

---

# Public API

```python
def serialize_scene(scene: Scene, path: str | Path) -> None: ...
def deserialize_scene(path: str | Path) -> Scene: ...
```

No `PartCatalog`, no singleton/manager — two plain functions, matching
`export_scene`/`optimize_scene`/`prepare_image`'s established shape.

---

# Validation Strategy

One exception type, `SceneSerializationError`, used consistently for
every structural/content problem: wrong `format`, unsupported
`schema_version` (checked first and second respectively, before any
brick parsing), missing `bricks`, a brick missing a required field, a
`position`/`rotation` array of the wrong length, non-finite (`NaN`/
`Infinity`) numeric values, an empty `part_name`, or a `color_code`
that's neither `null` nor an integer. **A real bug caught and fixed
during implementation**: Python's `bool` is a subclass of `int`, so a
naive `isinstance(value, int)` check would silently accept JSON
`true`/`false` as a valid `id` or `color_code` — `_is_int`/`_is_number`
explicitly exclude `bool`, verified with dedicated test cases for both
fields. No silent repair anywhere; any validation failure raises
before any `Scene` is returned. Raw I/O failures propagate as `OSError`
unwrapped, matching Package_024's precedent.

---

# Definition of Done

- Any valid `Scene` can be serialized and reconstructed.
- Serialization is deterministic — verified same Scene, same path →
  byte-identical output.
- Files contain an explicit schema version, checked before anything
  else is parsed.
- Round-trip equality verified — both via hand-built canonical scenes
  and a real generate → optimize → serialize → deserialize pipeline.
- Fully independent of rendering, exporting, optimization, generation,
  and UI — confirmed via `git diff`, and `PartCatalog` is not even a
  dependency (stronger independence than Package_024's exporter).

---

# Verification Performed

- `py_compile` clean; AST inspection confirms zero imports from
  `brickforge.generation`, `brickforge.ui`, `brickforge.render`,
  `brickforge.optimization`, `brickforge.export`, or
  `brickforge.services.part_catalog`.
- **Round trip**: empty Scene, single brick, and a multi-brick Scene
  (negative/fractional coordinates, non-identity rotation, `None`
  color, non-sequential ids) all round-trip to an exactly equivalent
  Scene.
- **Exact float precision**: confirmed round-trip preserves the actual
  stored (float32-via-glm) value bit-for-bit — the finding above.
- **Determinism**: same Scene, same path, serialized twice → byte-
  identical.
- **Input Scene never mutated** — confirmed directly.
- **9 malformed-file cases**, each independently constructed and
  confirmed to raise `SceneSerializationError`: invalid JSON, wrong
  format identifier, unsupported schema version, missing `bricks`,
  short `position` array, boolean `color_code`, boolean `id`,
  non-numeric position value, empty `part_name`.
- **Golden-file suite** (15 tests, mirroring Package_024's pattern
  exactly): golden files exist; serialized output matches byte-for-
  byte; deserializing the golden files themselves reconstructs the
  expected scenes; round-trip equality; determinism; no mutation; all
  9 malformed-file cases.
- **Confirmed the harness actually detects regressions**: deliberately
  corrupted `single_brick.json`, re-ran the suite, got two clear
  failures pointing at the exact mismatch, restored the file byte-
  exact, re-confirmed all 15 tests pass.
- **Real end-to-end pipeline, not hand-built data**: a genuine 6-brick
  Flat Mosaic column, optimized to 2 bricks (matching Package_021's
  own known result), serialized and deserialized — every field of
  every brick (including ids `0` and `4`, matching Brick Merge's own
  `min(id_a, id_b)` assignment) matches exactly.
- Re-ran Package_024's own test suite as a cross-check — unaffected.
- `git status` confirms exactly the planned scope: one new package
  directory, `tests/golden/scenes/` (4 files),
  `tests/test_scene_serialization.py`, `Package_025.md` — plus the
  long-standing pre-existing unstaged changes to `docs/ARCHITECTURE.md`
  and `.vscode/settings.json` (left alone, as always).

---

# Recommendations for Future Packages

- **Project Manager / save-load UI / recent files / autosave**: all
  explicitly out of scope here, and this format is exactly what such a
  future package would build on.
- **Schema v2**: no migration infrastructure was built for hypothetical
  future versions — the version-dispatch point in `deserializer.py` is
  the obvious place to extend when a real v2 need arises.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
