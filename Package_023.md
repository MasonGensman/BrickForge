# StudWorks

# Package 023

## Title

Persistent Catalog Cache

---

# Mission

Eliminate repeated parsing of the full LDraw library during application
startup by adding a persistent, transparent cache to
`PartCatalog.load_best_available()`. No change to rendering,
generation, optimization, export, or catalog semantics — only how the
catalog is constructed and loaded.

---

# Scope

New:

- `services/catalog_cache.py`

Modified:

- `services/part_catalog.py`

Untouched (verified via `git diff`, not assumed): `generation/*`,
`optimization/*`, `ui/*`, `render/*`, `engine/*`, `preparation/*`,
`models/*`, `ldraw/*`, `ldraw_catalog_builder.py`,
`ldraw_library_locator.py`.

---

# Inspection Findings

**`BrickDefinition`/`BoundingBox`** — plain `@dataclass(slots=True)`
with only primitive fields, no custom types. Fully compatible with
`pickle` with zero custom serialization code, confirmed empirically
(exact field-by-field equality after a full round-trip of all 24,297
real entries).

**A structural finding that changed this package's shape**:
`PartCatalog.load_best_available()` is called from **two independent,
uncoordinated call sites** — `Renderer.initialize()` (a local variable,
never stored on `self`, used only for demo-brick lookups) and
`MainWindow.create_widgets()` (`self.catalog`, used for generation).
Neither knows the other exists, so the real LDraw library was being
parsed **twice** per startup, not once. This is why the fix had to live
inside `load_best_available()` itself rather than at either call site —
confirmed by the live-app test below, which shows both now sharing the
exact same in-memory instance.

**Timing, measured directly** (not estimated): three isolated
`build_catalog_parts()` calls: 29.37s / 29.45s / 29.73s. A later
full-app run showed more variance (33-39s per build across several
runs, and one anomalous 130s+31s run likely reflecting system/disk
contention at that moment) — real-world cold-start cost is best
characterized as "~30-40s per build, paid twice under today's
uncached code, so ~60-80s realistic total," not a single fixed number.
A lightweight fingerprint (file count/total size/latest mtime across
24,297 files, no content reads) consistently took ~1.4s — about 20-25x
cheaper than a full rebuild, making it a worthwhile validation cost.

**No `platformdirs`/`appdirs` installed**, and no existing code in this
project uses one — `%LOCALAPPDATA%` is hand-resolved directly, matching
the existing precedent in `ldraw_library_locator.py`'s own
Windows-path handling.

**No existing serialization support anywhere** in the codebase — this
is the first.

---

# Cache Design

**Format: pickle**, chosen over JSON (would need hand-written
`to_dict`/`from_dict` conversion for tuples and the nested
`BoundingBox` for zero benefit, since this cache is never read by a
human or another tool), msgpack (a new dependency for marginal gains
over an already sub-second, 5 MB format), and sqlite (real
over-engineering for a single "load the whole list" access pattern
with no querying or concurrent access).

**Cache content**: one file, one pickled dict — manifest and data
together, so a partial write can't desynchronize them:
```python
{
    "cache_schema_version": 1,
    "app_version": "0.2.0",   # informational only, not a validity gate
    "library_path": str,
    "file_count": int,
    "total_size": int,
    "latest_mtime": float,
    "parts": list[BrickDefinition],
}
```

**Location**: `%LOCALAPPDATA%\StudWorks\cache\part_catalog.pkl` — not
roaming (cache data shouldn't sync across machines), outside `src/`,
the repo, and the LDraw library. No separate dev-mode fallback needed;
`%LOCALAPPDATA%` resolves identically in both contexts.

**Security note**: pickle can execute code from untrusted input, but
this cache is written and read only by the same application under the
same user account — the same trust boundary as any other local app
cache. No additional hardening (signing, restricted unpicklers) was
added, as that would be disproportionate here.

**Validation**: valid iff `cache_schema_version` matches (a dedicated
constant, independent of `_version.py`'s `APP_VERSION` so unrelated
app/branding bumps don't force needless rebuilds — bumped only when
`BrickDefinition`'s shape or `build_catalog_parts()`'s logic changes),
`library_path` matches exactly, and the fingerprint matches exactly.
Any failure at any step (missing file, corrupt pickle, wrong schema,
wrong library, fingerprint mismatch, unexpected shape) is treated
identically: return `None`, fall through to a normal rebuild.

**Failure handling**: `load_cached_parts()` never raises — a
deliberately broad `except Exception` around the unpickling step
specifically, since corrupted/incompatible pickle data can raise a
wide range of exception types, and every one of them must degrade to
"rebuild" per the requirement that the app never fail solely because
of the cache. `write_cache()` similarly swallows and logs `OSError`
(e.g. an unwritable cache directory) rather than propagating it.

---

# In-Memory Cache (added per your follow-up)

Verified, not assumed: grepped the entire codebase for any assignment
to a `BrickDefinition` field after construction — the only hit is
`ldraw/parser.py` mutating an unrelated `Part` (geometry) object during
parsing, before a `BrickDefinition` ever exists. `PartCatalog` itself
exposes no mutation methods (`__init__`, `from_seed`,
`load_best_available`, `all`, `get` — that's the complete public
surface). **`PartCatalog` is architecturally immutable in practice
today, though not type-enforced** (`BrickDefinition`/`BoundingBox`
aren't `frozen=True`) — this caveat is documented directly in
`load_best_available()`'s docstring as a flag for whoever adds catalog
mutation in the future.

Given this, the process-local layer caches the **`PartCatalog`
instance itself**, via `functools.lru_cache(maxsize=1)` (your requested
adjustment from `functools.cache`, to leave room for a future
parameterized variant without a cache-strategy change — behaves
identically to `functools.cache` today) wrapping a new module-level
`_load_best_available_catalog()` function. `PartCatalog.load_best_available()`
becomes a one-line wrapper. Documented explicitly as process-local and
assuming the LDraw library does not change while the application is
running — safe today since nothing watches the filesystem or offers a
"reload catalog" action.

This is what actually fixes the double-build problem: since both
`Renderer.initialize()` and `MainWindow.create_widgets()` call the same
`PartCatalog.load_best_available()`, they now transparently receive the
exact same cached instance — confirmed directly (`MainWindow.catalog
is renderer's catalog` → `True` in the live-app test below), with zero
changes to either call site.

---

# Definition of Done

- Persistent catalog caching is implemented (disk + in-memory).
- Startup no longer reparses the library unnecessarily — confirmed the
  real double-build is now a single real build plus one free in-memory
  hit.
- Automatic cache invalidation works — verified for schema, library
  path, and fingerprint mismatches independently.
- Existing application behavior is unchanged — `git diff` empty
  everywhere except the two files in scope; cached and freshly-built
  catalogs are exactly field-equal.
- The cache is completely transparent — `load_best_available()`'s
  signature and return type are unchanged; neither call site was
  touched.
- Measured startup performance improvement is documented below.

---

# Verification Performed

- `py_compile` clean on both files; import confirmed with no circular
  import issues.
- **AST inspection**: zero imports from `brickforge.generation`,
  `brickforge.ui`, `brickforge.render`, `brickforge.optimization`, or
  `brickforge.engine` in either file.
- **Untouched-scope**: `git diff --stat` empty for `generation/*`,
  `optimization/*`, `ui/*`, `render/*`, `engine/*`, `preparation/*`,
  `models/*`, `ldraw/*`, and the two other `services/` modules.
- **Missing cache**: rebuilds correctly, writes a cache file, resulting
  catalog exactly matches a direct `build_catalog_parts()` call
  (compared by part_number/name/ldraw_filename/description across all
  24,297 entries).
- **Valid disk cache**: loaded (not rebuilt), still exactly matches a
  direct build, consistently 1.9-2.05s across runs (vs. 29-39s cold).
- **Corrupted cache file**: rebuilds gracefully with no crash (a
  deliberately garbled file triggered `pickle`'s `UnpicklingError`,
  caught and logged as designed), and the corrupted file is replaced
  with a valid one.
- **Cache for a different `library_path`**: correctly rejected, not
  reused.
- **Fingerprint mismatch** (simulated stale `file_count`): correctly
  rejected, not reused.
- **In-memory cache**: two calls to `PartCatalog.load_best_available()`
  within one process return the identical object (`is` comparison); a
  third call measured at 0.00000s.
- **Real generation/optimization regression**: re-ran Brick Merge and
  Hidden Brick Removal directly against the real, cached 24,297-part
  catalog — Brick Merge correctly finds no merge targets (matching the
  already-documented placeholder-metadata behavior from Package_021),
  Hidden Brick Removal correctly reduces a 27-brick cube to 26, and the
  full `optimize_scene()` pipeline produces the same result — Packages
  021/022 continue to function unchanged.
- **Live application, end to end**: a real `MainWindow` launch showed
  `MainWindow.catalog is` (the renderer's own catalog) → `True`,
  confirming the double-build fix in the actual running app, not just
  in isolated tests. No new tracebacks; same graceful missing-geometry
  handling as every prior package.
- `git status` confirms exactly the planned scope: one new file, one
  file modified, `Package_023.md` added, plus the long-standing
  pre-existing unstaged changes to `docs/ARCHITECTURE.md` and
  `.vscode/settings.json` (left alone, as always).

---

# Measured Performance

| Metric | Value |
|---|---|
| Cold build (isolated, 3 trials) | 29.37s / 29.45s / 29.73s |
| Cold build (full app, several runs) | 33-39s (one outlier at 130s+31s) |
| Warm (disk cache hit) | 1.9-2.05s |
| In-memory cache hit | ~0.00000s |
| Cache file size | 5.07 MB |
| Speed improvement, warm vs. cold | ~15-20x per build |
| Realistic total startup, before this package | ~60-80s (two full builds) |
| Realistic total startup, after (warm) | ~2-3s (one disk-cache load + one free in-memory hit) |

---

# Recommendations for Future Packages

- **Cache size growth**: not a concern today (5 MB for the full real
  library), but worth revisiting if `BrickDefinition` ever grows
  significantly richer metadata.
- **`frozen=True` on `BrickDefinition`/`BoundingBox`**: would
  type-enforce the immutability this package's in-memory sharing
  currently only verifies by inspection — worth doing if a future
  package ever introduces catalog mutation, at which point the
  in-memory sharing here needs revisiting regardless.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
