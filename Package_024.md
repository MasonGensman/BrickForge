# StudWorks

# Package 024

## Title

Studio Export — First LDraw Export System

---

# Mission

Export any generated or optimized `Scene` as a valid `.ldr` LDraw model
that opens correctly in BrickLink Studio. Export capability only — no
change to generation, optimization, rendering, catalog construction,
caching, or UI architecture.

---

# Scope

New package `export/` (zero existing files touched):

- `export/exporter.py`
- `export/ldraw_writer.py`
- `export/__init__.py`

Untouched (verified via `git diff`, not assumed): `generation/*`,
`optimization/*`, `ui/*`, `render/*`, `engine/*`, `preparation/*`,
`services/*`, `models/*`, `ldraw/*`.

---

# Inspection Findings

**`Scene`/`SceneBrick`** — unchanged: `part_name` (LDraw filename),
`position: glm.vec3`, `rotation: glm.quat`, `color_code: int | None`.

**A significant, previously-undiscovered finding** — traced the
coordinate pipeline from raw file parsing through to the GPU:
`LDrawParser.parse()` extracts Type-3/4 vertex coordinates completely
unmodified (no flip, no sign change), and neither the shader
(`grid.vert`, a pure passthrough MVP transform) nor the camera
(`glm.lookAt(..., up=(0,1,0))`, standard right-handed glm) apply any
compensating transform. I then confirmed LDraw's real coordinate
convention directly against actual geometry rather than recollection:
`ldraw/part/3005.dat`'s subfile places its **stud at translation Y=0**
and its **main body box at translation Y=24**
(`1 16 0 24 0 ... box4t.dat`). Since a stud must sit physically above
the body, and has the *smaller* Y value, this confirms LDraw's Y+
points down, origin at stud-top level — and that this renderer, with
zero compensating flip anywhere, currently displays real LDraw
geometry upside-down. Not fixed here (explicitly out of scope), but
directly informed the coordinate-system decision below.

**Rotations**: `glm.mat3_cast` stores column-major (`m[col][row]`);
extracting LDraw's row-major `a..i` values requires
`m[col][row]` with column/row swapped from what "row-major" suggests
at a glance. Verified against a known 90°-around-Y case
(`m * (1,0,0) = (0,0,-1)`) before writing any code.

**Colors**: `SceneBrick.color_code` already **is** the canonical LDraw
color ID (parsed directly from `LDConfig.ldr`'s `!COLOUR` lines by
`PaletteEngine`) — no second color system, no conversion.

**Part names**: `BrickDefinition.ldraw_filename`/`SceneBrick.part_name`
are already genuine LDraw filenames in both catalog sources — no
normalization needed.

**No existing `export/` package**; `bricklink/__init__.py` remains
empty and unrelated (future BrickLink *API* integration, not LDraw
file export).

---

# Decisions Applied (per your approval)

1. **Native LDraw coordinates, no renderer-orientation compensation.**
   The exporter writes `SceneBrick.position`/`rotation` exactly as
   given — geometrically correct, native LDraw output that opens
   right-side-up in BrickLink Studio, even though it will *not*
   visually match this app's own (separately, pre-existing) upside-down
   viewport. Correctness over matching a known bug.
2. **Unknown parts are validated and warned about, but always
   written** — never silently omitted. An unrecognized `part_name` (not
   found in the active `PartCatalog`) logs a warning and is exported
   anyway, so a gap in the *local* catalog's metadata can never cause
   generated geometry to silently vanish from the export.
3. **`PartCatalog` stays in the public API** (`export_scene(scene,
   catalog, path)`), not resolved internally. This matches the
   established dependency-injection shape `GenerationMode.generate()`
   and `Optimizer.optimize()` already use — callers own and share one
   `PartCatalog` instance rather than each stage resolving its own —
   and its validation role (decision 2) is genuinely active, not
   vestigial.

---

# Export Format: `.ldr`

Chosen over `.mpd` (unnecessary multi-model container for a flat brick
list) and `.io` (BrickLink Studio's own undocumented proprietary
format — real reverse-engineering risk for zero benefit, since Studio
already imports `.ldr` directly via File → Import).

---

# What Changed

## `export/ldraw_writer.py` (new)

- `rotation_to_ldraw_matrix(rotation) -> tuple[9 floats]` — the one
  place the quaternion→matrix conversion happens, verified against the
  90°-around-Y case above.
- `format_type1_line(color_code, position, rotation, part_name) -> str`
  — one `SceneBrick` as one LDraw Type-1 line. Position/rotation used
  exactly as given, per decision 1.
- `_format_number(value) -> str` — deterministic fixed-point formatting
  (`.6f`, never scientific notation). **A real bug found and fixed
  during verification**: my first `_NEAR_ZERO` threshold (`1e-9`) was
  too tight to catch the actual floating-point noise `glm`'s own
  quaternion math produces (measured: ~6e-8 for a "clean" 90° angle),
  so small negative noise was formatting as `-0.000000` instead of the
  intended clean `0.000000`. Widened to `5e-7` (half a unit in the last
  displayed decimal place) and re-verified.
- `write_ldraw_file(path, model_name, lines)` — a minimal header
  (`0 <name>` / `0 Name:` / `0 Author: StudWorks`) plus one line per
  brick. Raises `OSError` unwrapped on write failure.

## `export/exporter.py` (new)

- `export_scene(scene, catalog, path) -> None` — the one public entry
  point. Builds a local `{part_name: BrickDefinition}` index from
  `catalog.all()` (same pattern `brick_merge_optimizer.py` and
  `hidden_brick_removal_optimizer.py` already use, since
  `PartCatalog.get()` is keyed by `part_number`, not the LDraw filename
  `SceneBrick.part_name` carries) purely for validation — an
  unrecognized part logs a warning and is still written. Iterates
  `scene` in its existing order (already deterministic, transitively,
  from every generation/optimization stage that could have produced
  it) — no re-sorting. Never mutates `scene`.

---

# Definition of Done

- Any valid `Scene` can be exported to a `.ldr` file.
- The file is genuinely valid LDraw — verified structurally (every
  Type-1 line parses per `LDrawParser`'s own documented Type-1 format)
  and via real generation→optimization→export content (a 6-brick Flat
  Mosaic column correctly optimizes to 2 bricks and exports with
  correct positions/colors/rotations).
- Export is deterministic — verified same Scene, same path → byte-
  identical output; same Scene, different path → identical brick data.
- Scene objects remain unchanged — verified directly.
- The exporter is fully separated — `git diff` empty on `generation/`,
  `optimization/`, `render/`, `ui/`, `services/`, `models/`, `ldraw/`.

---

# Verification Performed

- `py_compile` clean; AST inspection confirms zero imports from
  `brickforge.generation`, `brickforge.ui`, `brickforge.render`, or
  `brickforge.optimization`.
- **Rotation conversion**: identity → identity matrix; 90°-around-Y →
  matches the planning-verified case exactly.
- **Type-1 line format**: exact string match against a hand-computed
  expected line.
- **Round trip structural validity**: every Type-1 line in a real
  exported file parses correctly per `LDrawParser`'s own Type-1 token
  layout (`tokens[2:5]`/`tokens[5:14]`/`tokens[14:]`).
- **Determinism**: same Scene + same path → byte-identical file
  content across two exports; same Scene + different path → identical
  Type-1 lines (only the filename-derived header differs, correctly).
- **Input Scene never mutated** — confirmed directly.
- **Unknown part**: written with a logged warning, not omitted —
  confirmed the part name appears in the output file.
- **`color_code=None`**: defaults to LDraw color `16`, confirmed in
  output.
- **Real end-to-end pipeline, not hand-built data**: a genuine 6-brick
  Flat Mosaic-generated column (uniform red image, part `3005`), run
  through `optimize_scene()` (reducing to 2 bricks: `3010` + `3004`,
  matching Package_021's own known result), exported both before and
  after optimization — raw export has exactly 6 Type-1 lines, optimized
  export has exactly 2, correct part names/colors/positions/identity
  rotations in the output, neither Scene mutated.
- `git status` confirms exactly the planned scope: one new package
  directory, `Package_024.md` added, plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Recommendations for Future Packages

- **Renderer orientation bug**: this package's inspection surfaced a
  real, separate finding — this app's own 3D viewport currently
  displays LDraw geometry upside-down (no Y-flip anywhere in the
  render pipeline, despite LDraw's native Y-down convention).
  Recommended as its own dedicated future package; not touched here.
- **Manual verification still needed**: opening an actual exported
  file in real BrickLink Studio hasn't been done (no automated way to
  drive Studio from this environment) — recommended as a manual
  confirmation step before relying on this in a release.
- **`.mpd`/steps/groups**: explicitly deferred, per scope.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.

---

# Amendment: Golden-File Regression Tests (2026-07-22)

Documentation-and-test-only addendum — no production code changed
(`git diff --stat -- src/` is empty for this amendment).

## Why golden files exist

Package_024 documents the exporter as deterministic: identical `Scene`
input must always produce identical output. That's a claim, verified
manually during the original package work but not permanently
enforced anywhere. A golden-file test closes that gap: four canonical
`Scene`s are exported and compared, byte-for-byte, against fixed
reference files on every run, so any future change to `export/`,
`generation/`, or `optimization/` that alters output for these fixed
inputs is caught immediately rather than discovered later by manual
inspection.

**No test framework dependency was added.** `requirements.txt`/
`pyproject.toml` declare no test framework today, and this amendment's
scope is explicitly "tests + test assets + docs only." The suite uses
Python's standard-library `unittest` rather than introducing `pytest`
as a new dependency — zero footprint beyond the `tests/` directory
itself.

## What was added

- `tests/golden/single_brick.ldr`, `merged_column.ldr`,
  `flat_mosaic_3x3.ldr`, `height_relief_3x3.ldr` — generated using the
  exporter itself (`export_scene()`), as instructed, then reviewed
  before being treated as immutable references.
- `tests/test_export_golden_files.py` — builds each canonical `Scene`
  and compares its exported output against the corresponding golden
  file.

**Canonical scene coverage, deliberately spanning both raw and
optimized output**: `single_brick` (the simplest possible case);
`merged_column` (four `1x1` bricks run through the real
`optimize_scene()` pipeline, collapsing to one `1x4` — exercises
optimizer-produced output specifically, confirmed by a dedicated
sanity-check test that four bricks in become exactly one brick out);
`flat_mosaic_3x3` and `height_relief_3x3` (real, not hand-built,
generation output from both registered `GenerationMode`s — the latter
exercises multi-layer/3D stacking, the most geometrically complex case
export handles today).

**Environment independence, a deliberate and necessary design
choice**: golden-file construction uses `PartCatalog.from_seed()`
(never `load_best_available()`) and the bundled fallback
`LDConfig.ldr` via `resources.resource_path()` (never
`find_ldraw_library()`'s resolved result). Both are fixed and
version-controlled, identical on every machine. Building golden-file
tests against whichever real LDraw library happens to be installed
locally would make the tests non-reproducible across environments —
exactly the kind of hidden dependency a regression test must not have.

## Why byte-for-byte comparison, with no normalization

The entire purpose of this test is to catch *any* unintended
difference — line order, number formatting, floating-point precision,
whitespace, newline convention. Normalizing any of these away in the
comparison would silently accept the exact class of regression the
test exists to catch. This was verified directly, not just asserted:
the golden file comparison was deliberately broken (corrupting one
reference file), confirmed the test suite fails with a clear diff, then
the file was restored and confirmed byte-identical to its original
before being treated as the reference again. (Incidentally, this also
confirmed golden files are written with Windows CRLF line endings —
Python's default text-mode newline translation on this platform,
matching traditional LDraw file convention, not something explicitly
forced in `ldraw_writer.py`.)

## Golden-file update policy

Golden files are regenerated **only** when an export-behavior change
is intentional — never simply because a test fails. A failing
golden-file test is a signal to investigate *why* output changed
first; if, after review, the change is confirmed deliberate (e.g. a
future package intentionally changes number formatting, header
content, or brick ordering), the golden files are regenerated using
the same builder functions in `test_export_golden_files.py`, the diff
is reviewed, and the updated golden files are committed **alongside**
the change that caused them — never as a silent, separate commit that
just makes a failing test pass again.

## Verification performed

- All 4 tests pass: golden files exist, exported output matches each
  byte-for-byte, repeated exports of the same Scene remain identical,
  and `merged_column` is confirmed to genuinely exercise optimizer
  output (4 bricks in, 1 out).
- Confirmed the test suite actually detects regressions (not
  vacuously passing): deliberately corrupted `single_brick.ldr`,
  re-ran the suite, confirmed a clear failure with a diff pointing at
  the exact mismatch, then restored the file and confirmed byte-exact
  restoration before re-running to confirm a pass.
- `git diff --stat -- src/` confirms zero production code changes.
- `git status` confirms exactly the planned scope: `tests/golden/`
  (4 new files), `tests/test_export_golden_files.py`, and this
  amendment to `Package_024.md` — plus the long-standing pre-existing
  unstaged changes to `docs/ARCHITECTURE.md` and `.vscode/settings.json`
  (left alone, as always).
