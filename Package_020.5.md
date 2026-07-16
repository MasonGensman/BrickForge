# StudWorks

# Package 020.5

## Title

First Distributable Windows Preview Build — Packaging, Branding, Discovery

---

# Mission

Prepare StudWorks for its first distributable Windows Preview build
(`StudWorks Preview 0.2.0`) — packaging, application-facing branding,
and runtime resource discovery only. No generation, optimization, or
rendering *logic* was changed; the only rendering-adjacent edits are
*where* the renderer looks for its data files, not how it renders.

---

# Scope

New:

- `src/brickforge/_version.py`, `src/brickforge/resources.py`
- `src/brickforge/ldraw/library_layout.py`
- `src/brickforge/ui/resources/icon.ico`, `icon.png`
- `StudWorks.spec`, `packaging/version_info.txt`
- `scripts/build.ps1`, `scripts/clean.ps1`

Modified:

- `src/brickforge/app.py`, `src/brickforge/ui/main_window.py`
- `src/brickforge/render/renderer.py`, `render_context.py`
- `src/brickforge/services/ldraw_library_locator.py`,
  `ldraw_catalog_builder.py`
- `src/brickforge/ldraw/loader.py`, `ldraw/__init__.py`
- `pyproject.toml`, `requirements.txt`, `README.md`

Removed: `BrickForge.spec` (replaced by `StudWorks.spec`).

Untouched (verified via `git diff`, not assumed): `generation/*`,
`optimization/*`, `preparation/*`, `engine/*`, `palette/*`,
`ui/widgets/*`, `models/*`, `io/*`, `analysis/*` — and, critically,
`src/brickforge/` itself was never renamed, and no `import` statement
anywhere was changed to reference a different package name.

---

# Revisions Applied (per your approval)

## 1. LDraw library strategy — four-tier discovery order

`find_ldraw_library()` (`services/ldraw_library_locator.py`) now tries,
in order: (1) `LDRAW_LIBRARY_PATH`, (2) standard Windows install
locations, (3) the project-root `ldraw/` directory (skipped entirely
when `sys.frozen` is set — meaningless in a packaged build), (4) the
bundled fallback library shipped with the application. This function
was already `PartCatalog`'s discovery mechanism; the real change is
that **`Renderer.initialize()` now calls it too**, instead of
hardcoding its own separate path. Previously the catalog and the
renderer could silently resolve to *different* libraries; now both
always agree on "the best available library," which is what "developers
automatically use the complete library, users with LDraw installed
receive full rendering, Preview builds still launch without a large
bundled library" actually requires.

**A real, previously-unknown bug this surfaced and fixed**: the
project-root `ldraw/` directory (590 MB, 36,481 git-tracked files —
confirmed to contain real, standard part files including `3001.dat`/
`3005.dat`) uses a non-standard `part/` (singular) directory name
instead of the official LDraw `parts/` (plural). Both `LDrawLoader`
and `build_catalog_parts()` hardcoded `"parts"` only, so even after
implementing the discovery order, this library was still functionally
unusable — silently falling back to the seed catalog with just a log
warning. Added `ldraw/library_layout.py`'s `resolve_parts_directory()`
(tries `"parts"` first, falls back to `"part"`) and wired it into both
call sites. This was outside the five bullet points you approved, but
without it the discovery-order change would have been correctly
*implemented* while still not *working* for the actual data in this
repository — flagging this clearly rather than silently expanding
scope. Happy to revert this specific piece if you'd rather it be a
separate, dedicated package.

**Real, measured consequence worth knowing about**: with the real
library now discoverable, building the full catalog from its 24,297
parts takes **~29 seconds** in this dev environment (measured
directly). This is a genuine, real cost of using the complete library,
not a bug — and it does *not* affect Preview build users: the bundled
tier-4 fallback's `parts/` directory is empty (confirmed: catalog build
from it is instant, 0 parts), so this cost is specific to development
machines with the real library present. The splash screen (below)
covers this wait with visible "StudWorks Preview 0.2.0" text rather
than a frozen-looking blank window, but 29 seconds is still a long
splash. Flagging as a known limitation, not fixing it here — caching or
async loading would be a real architecture change, out of scope for a
packaging package.

## 2. Resource discovery — centralized where it could be done cleanly

`brickforge/resources.py` is a small, new, dependency-free module:
`resource_root()` resolves to the `brickforge` package root in both
source form (`Path(__file__).parent`) and frozen form
(`sys._MEIPASS/brickforge`, when `sys.frozen` is set); `resource_path(*parts)`
joins onto it. `Renderer.initialize()`'s shader path and bundled-LDraw
fallback path, and `MainWindow`'s icon path, all go through this now
instead of each independently constructing `Path(__file__)`-relative
paths. This is the standard, well-documented PyInstaller pattern
(`sys._MEIPASS` is the only reliable way to locate bundled data at
runtime in a frozen build) rather than something invented for this
package.

**Deliberately not centralized further**: LDraw library discovery
stays a separate mechanism (`find_ldraw_library()`). It has a
genuinely different shape — searching *outside* the package first,
falling back to a bundled copy last — versus `resources.py`'s "always
bundled, just dev-vs-frozen" concern. Merging them would blur two
different resolution strategies rather than simplify anything, so per
your instruction ("if it would require significant architectural
changes, document it... rather than forcing it"), this stays a
documented recommendation, not a forced unification.

## 3. Dependencies — packaging metadata corrected

`requirements.txt` and `pyproject.toml`'s `dependencies` now declare
`numpy>=2.4`, `PyOpenGL>=3.1`, and `PyGLM>=2.8` alongside
`PySide6>=6.11` (previously only PySide6 was declared, despite all
four being actually imported throughout the codebase). Versions match
what's actually installed and working in this environment.

## 4. Rename — application-facing branding only

Changed: window title (`main_window.py`), console startup banner
(`render_context.py`), `pyproject.toml`'s `name`/`description`,
`StudWorks.spec` (replacing `BrickForge.spec`), README.md's title and
status line (also fixed an existing self-inconsistency — the README's
own first two lines said "Brick-Forge" and "BrickForge" in the same
breath).

**Not touched, confirmed by `git diff`**: `src/brickforge/` itself,
every `import brickforge...` statement across the whole codebase,
internal docstring headers ("BrickForge Image Manager," etc. — cosmetic,
zero functional impact). `pyproject.toml`'s `[project].name` and the
actual Python package name are independent in this project's setup
(`[tool.setuptools.packages.find]` discovers whatever's under `src/`
regardless of `[project].name`), which is exactly what made this
split possible without touching a single import.

## 5. Versioning — one source of truth

`src/brickforge/_version.py`: `APP_NAME = "StudWorks"`,
`APP_VERSION = "0.2.0"`, `BUILD_LABEL = "Preview"`, plus
`window_title()` and `display_version()` helpers. The window title,
console banner, and splash screen all import from here now, rather
than each hardcoding its own copy — this is what fixes the
previously-existing inconsistency (window title said "v0.1.0" while
`pyproject.toml` said "0.1.0-alpha.1"). `packaging/version_info.txt`
embeds matching `FileVersion`/`ProductVersion`/`ProductName` metadata
into the compiled `.exe` via PyInstaller's `version=` parameter, so
Windows Explorer's Properties dialog shows correct info.

---

# What Else Was Implemented

- **Splash screen** (`app.py`): a lightweight, self-drawn
  `QSplashScreen` (no external image dependency — built with
  `QPainter`) showing "StudWorks" and "Preview 0.2.0", shown before
  `MainWindow()` construction and closed automatically via
  `splash.finish(window)` once the main window is ready.
- **Application icon**: a placeholder `.ico`/`.png` (a simple red
  rounded-square with a centered stud circle, generated programmatically
  via `QPainter` — no external asset needed), wired into both
  `MainWindow.setWindowIcon()` and the `.spec`'s `icon=` parameter.
  Single-resolution (256×256) — Qt's ICO writer did not support
  writing genuine multi-resolution `.ico` files in this environment;
  Windows scales a single high-res icon down cleanly, and the mission
  explicitly allows a temporary icon.
- **`StudWorks.spec`**: bundles `render/shaders`, the tier-4 fallback
  `ldraw/ldraw` (18 MB — the 590 MB project-root library is
  intentionally *not* bundled, per your framing), and the icon files;
  `hiddenimports` for `PySide6.QtOpenGL`/`QtOpenGLWidgets` (used by
  `ViewportWidget`, a known PyInstaller/PySide6 risk area). Reads
  `STUDWORKS_DEBUG_CONSOLE` to toggle `console=True/False` from one
  spec rather than maintaining two.
- **`scripts/build.ps1`** / **`clean.ps1`**: `build.ps1` cleans, builds
  via the spec, and reports `dist/StudWorks.exe`; `-Debug` switch
  builds the console variant.

---

# Definition of Done

- A complete Windows packaging architecture is designed and
  implemented: spec, build scripts, version metadata, icon, splash.
- Required runtime assets identified and bundled (shaders, bundled
  LDraw fallback, icon) or correctly left external (the real
  project-root library, per the discovery-order design).
- Build process documented and scripted (`scripts/build.ps1`).
- Branding transition completed for the application-facing surface
  only; the Python package rename is explicitly deferred.
- Preview distribution process fully specified: `StudWorks Preview
  0.2.0`, one command (`scripts/build.ps1`) to `dist/StudWorks.exe`.

---

# Verification Performed

- `py_compile` clean on every new/modified Python file.
- **Discovery-order correctness**: dedicated test script confirming
  all four tiers fire in the correct priority order (env var beats
  standard locations beats project-root beats bundled fallback), that
  an invalid env var value falls through gracefully rather than
  crashing, and that tier 3 is correctly skipped when `sys.frozen` is
  set (falling through to tier 4).
- **Untouched-scope**: `git diff --stat` empty for `generation/*`,
  `optimization/*`, `preparation/*`, `engine/*`, `palette/*`,
  `ui/widgets/*`, `models/*`, `io/*`, `analysis/*`; confirmed via
  `git status`/`git diff` that `src/brickforge/` was never renamed and
  no import statement anywhere references a different package name.
- **Real, comprehensive end-to-end run** (not just unit-level): a
  single live `MainWindow` launch through the actual splash → window
  flow, confirming: correct window title/icon; `MainWindow.catalog`
  genuinely resolved to the real 24,297-part project-root library (not
  the seed catalog) with real `bounding_box` data on `3005`;
  Generation Mode registry still exposes exactly `flat_mosaic` and
  `height_relief`; Optimization registry still exposes exactly
  `brick_merge`; a real button-driven Flat Mosaic generation (16
  bricks) and Height Relief generation both rendered correctly against
  the real catalog; `optimize_scene()` still runs correctly against
  the real catalog's placeholder metadata (correctly finds zero merge
  opportunities, since every real-catalog part shares the same
  placeholder `stud_length=1` — a safe, expected degradation, not a
  bug, matching Package_021's own documented reasoning).
- **Bundled tier-4 fallback confirmed instant** (0 parts, 0.000s),
  isolating the ~29s cost to development-only tier-3 usage.
- Live application launch produces the same graceful missing-geometry
  handling as every prior package for any part not present in whichever
  library was resolved — no new crash class introduced.

---

# Recommendations for Future Packages

- **Internal package rename** (`brickforge` → `studworks`, every
  import statement): a large, dedicated, mechanical package of its
  own, deliberately not touched here.
- **Catalog build performance**: ~29s to scan the real 24,297-part
  library is a real developer-experience cost worth addressing
  eventually (caching the built catalog to disk, or making the load
  async) — not attempted here since it would be a genuine application
  architecture change.
- **Offline installer bundling the complete library**: explicitly
  named in your own framing as a future possibility; nothing in this
  package precludes it, but nothing here builds it either.
- **Multi-resolution `.ico`**: the current icon is single-resolution;
  revisit alongside final branding/logo work.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
