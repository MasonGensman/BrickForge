# StudWorks

# Package 006

## Title

Recursive LDraw Subfile Resolution

---

# Mission

Load the hierarchical structure used by real LDraw parts: resolve Type-1
subfile references recursively, composing parent-to-child transforms, so
`Part.vertices` for a top-level part reflects its complete geometry
(including studs, connectors, and other referenced primitives) rather than
only its directly-authored triangles.

---

# Scope

Modify only:

- `src/brickforge/ldraw/part.py`
- `src/brickforge/ldraw/parser.py`
- `src/brickforge/ldraw/loader.py`
- `src/brickforge/ldraw/library.py`
- `Package_006.md`

No other file may change.

---

# Requirements

1. Recursive Type-1 subfile loading, through arbitrary nesting depth.
2. Parent→child transform composition.
3. Cycle detection.
4. Graceful handling of a missing *referenced* subfile — log and skip only
   that reference; loading fails only if the *top-level requested* part
   cannot be opened.
5. Reuse of the existing `LDrawLibrary` part cache — no second cache.
6. Parser stores translation and the native 3×3 transform exactly as parsed
   — no internal 4×4 abstraction.
7. `Renderer`, `Scene`, `SceneBrick`, `BrickManager`, `Camera`, `Shader`,
   `Grid`, and `ui/` require no modification.

---

# Definition of Done

- `Part` carries a `subfile_references: list[PartReference]` field;
  `PartReference` stores `file_name`, `translation` (3,), and `matrix` (3×3)
  exactly as parsed from the Type-1 line.
- `LDrawParser` captures Type-1 lines into `PartReference` instead of
  discarding them; all other record types behave exactly as before.
- `LDrawLoader` recursively resolves subfile references, searching `parts/`
  then `p/`; composes each resolved child's vertices by its reference's
  matrix/translation and flattens them into the parent's own vertex array;
  detects cycles via a per-instance visiting set and skips them with a
  warning rather than recursing infinitely; skips an individual unresolvable
  reference with a warning while still returning the parent's own geometry;
  still raises `FileNotFoundError` when the *top-level requested* filename
  cannot be found in either directory.
- `LDrawLibrary.load()` threads its cache through recursive resolution
  (`resolve=self.load`), so subfiles/primitives referenced from multiple
  places are parsed from disk once and reused — no second cache introduced.
- A file with zero Type-1 lines produces vertices identical to
  pre-Package_006 parsing.
- `engine/` and `render/` packages are untouched; their Package_003/004/005
  behavior is unaffected.
- `py_compile` clean; live run confirms no crash, identical grid-only
  fallback.

---

# Completion Notes

## Architectural Reasoning

Recursion and transform composition live entirely inside the `ldraw/`
package, at load time, producing one fully-flattened `Part.vertices` array
per top-level part — interface-identical in shape to what `Part.vertices`
already was. `BrickManager`, `Mesh`, and `Renderer` consume `Part.vertices`
as a flat triangle buffer regardless of whether it came from one file or
five levels of nested subfiles; none of them can tell the difference, and
none needed to change.

Composition happens through recursion's own call-stack nesting rather than
an explicit matrix stack: each recursive `load_part` call returns a `Part`
whose vertices are already fully resolved and flattened into *that file's*
local frame. When a parent incorporates a child's already-resolved
vertices, it applies exactly one transform — its own reference's
matrix/translation — to output already composed by the child's own
recursion. A grandchild's geometry is therefore transformed once by the
child (into the child's frame) and again by the parent (into the parent's
frame), which is mathematically equivalent to explicit matrix
multiplication, verified directly (see Verification).

Per your instruction, the parser stores the native LDraw 3×3
matrix + translation exactly as parsed (`PartReference.matrix`,
`PartReference.translation`) — no internal 4×4 homogeneous-transform type
was introduced. The 3×3-matrix-plus-vector representation is applied
directly via `points @ matrix.T + translation` (`numpy`, already a
dependency of this package) at the point each reference is resolved; no
4×4 composition, stack, or new math abstraction was needed to satisfy
nested composition (see Architectural Reasoning above).

## Exact Implementation

- **`part.py`**: added `PartReference` (`file_name: str`,
  `translation: np.ndarray`, `matrix: np.ndarray`) and
  `Part.subfile_references: list[PartReference]` (default empty list).
- **`parser.py`**: the Type-1 branch now parses `tokens[2:5]` (translation),
  `tokens[5:14]` reshaped `(3, 3)` row-major (matching the LDraw spec's
  `a b c / d e f / g h i` layout), and `tokens[14:]` joined (handles
  filenames containing spaces) with `\` normalized to `/` (LDraw's `s\`
  subpart-folder convention) — appended as a `PartReference`. The colour
  token (`tokens[1]`) is read-and-discarded, matching how Type-3/4 lines
  already discard their colour token; per-part/per-subfile colour remains
  out of scope, as in every prior package.
- **`loader.py`**:
  - Added `primitives_path = library_path / "p"` alongside the existing
    `parts_path`. `_resolve_path()` tries `parts_path` first, then
    `primitives_path` — matching LDraw's own PARTS-before-P search order,
    and naturally covering `parts/s/` subparts since a reference like
    `s/6141.dat` joins correctly onto `parts_path`.
  - Added `self._visiting: set[str]`, a mutable recursion guard added to
    on entry and removed (via `finally`, so it's correct even on
    exceptions) on exit of every `load_part` call.
  - `load_part(filename, resolve=None)`: `resolve` defaults to
    `self.load_part`, so the loader recurses correctly even used standalone
    without a `LDrawLibrary`. A filename already in `_visiting` is a cycle
    — logged and returned as an empty `Part` rather than recursing further.
    Each subfile reference is resolved via `resolve(...)`; a `FileNotFoundError`
    from an individual reference is caught, logged, and skipped — the loop
    continues with whatever other references *do* resolve. Only the
    top-level `filename` passed into this call raises if unresolvable.
  - The `FileNotFoundError` message reports both searched paths
    (`parts/<file>` and `p/<file>`) for diagnostics.
- **`library.py`**: one line — `self.loader.load_part(filename,
  resolve=self.load)` instead of `self.loader.load_part(filename)`. This is
  what makes recursive/subfile lookups share the *same* cache as top-level
  lookups (see Verification, cache-reuse-during-recursion), rather than
  caching only top-level part names and re-parsing every subfile reference
  from disk on every use.

## Matrix Composition — Order and Correctness

LDraw Type-1 semantics: a local point `v` maps to the parent's frame as
`v' = M @ v + t`, where `M` is the row-major 3×3 matrix
`[[a,b,c],[d,e,f],[g,h,i]]` parsed directly from `tokens[5:14]`. For a
`numpy` array of row-vector points `P` (shape `(N, 3)`), the equivalent
vectorized form is `P @ M.T + t`, implemented exactly as written in
`loader.py`. This was verified directly against hand-computed expected
coordinates for both a pure-translation reference and a 90°-rotation
reference nested two levels deep (see Verification) — not inferred from the
implementation, computed independently and compared.

## Verification Performed

All verification used a synthetic LDraw-like fixture tree in the scratch
directory (the real library remains empty, unchanged since Package_001),
deleted after the run. `py_compile` was clean on all four touched files
throughout.

1. **Recursive loading + transform propagation (2 levels, `parts/` and
   `p/`, translation and rotation)**: `parent.dat` (own triangle + a
   translated reference to `child.dat`) → `child.dat` (own triangle + a
   *90°-about-Z-rotated and translated* reference to `grandchild.dat` in
   `p/`) → `grandchild.dat` (own triangle). Loaded `parent.dat` and
   compared all 9 resulting vertices against independently hand-computed
   expected coordinates (rotating and translating by hand, not by running
   the code being tested) — **exact match**, confirming both multi-level
   recursion across both search directories and correct rotation+
   translation composition through nesting.
2. **Cache reuse during recursion (your additional requirement)**:
   `two_refs.dat` contains two separate Type-1 lines both referencing
   `shared.dat` at different placements. Instrumented `LDrawParser.parse`
   with a call counter. Confirmed `shared.dat` is parsed from disk **exactly
   once** despite two references, and that both resulting placements have
   the correct, independently-translated vertex coordinates (proving the
   *cached* `Part` was reused and correctly re-transformed per reference,
   not merely deduplicated incorrectly).
3. **Cycle detection**: `cycle_a.dat` references `cycle_b.dat`, which
   references `cycle_a.dat` back. Loading `cycle_a.dat` completed without
   hanging or raising `RecursionError`, logged a warning, and still
   returned `cycle_a.dat`'s own directly-authored geometry.
4. **Missing referenced subfile**: `missing_ref.dat` (own triangle + a
   reference to a nonexistent file). Load succeeded, returned the own
   triangle, logged a warning for the unresolved reference — did not raise.
5. **Backward compatibility**: `plain.dat` (Type-3 and Type-4 lines only,
   no Type-1 references) produced vertices identical to the pre-Package_006
   parser's output, and `subfile_references == []`.
6. **Top-level missing part still raises**: requesting a nonexistent
   top-level filename still raises `FileNotFoundError` — confirming the
   graceful-skip behavior applies only to *referenced* subfiles, per your
   instruction, not to the top-level request itself.
7. **No regressions in untouched layers**: re-ran Package_003's `Scene` API
   checks (`add_brick`/`remove_brick`/`clear`/`iterate`/`__iter__`) and
   Package_005's isolated `u_model` matrix-composition checks (identity and
   rotated cases) — both still pass unchanged, confirming `engine/` and
   `render/` are unaffected, as the architecture predicted.
8. **Live run of `src/main.py`**: identical to Package_005 — grid renders,
   all 3 seeded bricks individually log a missing-part warning (now
   reporting both searched paths) and are skipped gracefully, no crash, no
   traceback, app stays alive.
9. `git diff`/`git status` confirm only the four planned `ldraw/` files
   changed.

## Final Diff Summary

4 files changed, 162 insertions, 12 deletions:

- `src/brickforge/ldraw/part.py` (+19) — `PartReference` dataclass,
  `Part.subfile_references` field.
- `src/brickforge/ldraw/parser.py` (+42/-4) — Type-1 branch captures a
  `PartReference` instead of discarding the line.
- `src/brickforge/ldraw/loader.py` (+112/-4, effectively rewritten) —
  broadened search path, recursive resolution, transform composition,
  cycle detection, per-reference graceful degradation.
- `src/brickforge/ldraw/library.py` (+1) — threads the existing cache
  through recursive resolution.

No changes to `engine/`, `render/`, `ui/`, or any other file.

## Recommendations for Future Packages

- **BFC winding/`INVERTNEXT` handling** remains unimplemented. The renderer
  never enables `GL_CULL_FACE`, so winding order has no visible effect
  today — flagged again as a future item, not a defect, consistent with the
  Package_006 plan's scope decision.
- **LDraw colour codes** (Type-1's colour token, and Type-3/4's) remain
  parsed-and-discarded. Materials/per-part colour remain out of scope, as
  in every prior package; `render/material.py` is still an empty stub.
- **Missing-subfile lookups are not cache-negative.** A reference to a
  permanently-missing file will re-check the filesystem (a cheap `.exists()`
  call, not a re-parse) every time it's referenced, rather than being
  cached as "known missing." Not implemented here to keep the change
  minimal, as requested; worth revisiting if scenes with many missing
  references show up in practice.
- **The real LDraw parts library is still empty** in this environment —
  visual verification of actual bricks (Package_001/003/004/005
  recommendation) remains outstanding. This package makes the *parsing*
  side ready for real geometry; it doesn't populate the library itself.
- LDraw library consolidation (root `ldraw/part/` vs.
  `src/.../ldraw/parts/`, Package_001) and the two `Brick` concepts
  reconciliation (Package_002) remain outstanding and unaffected by this
  package.
