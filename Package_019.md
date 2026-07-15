# StudWorks

# Package 019

## Title

Height Relief — First Additional Generation Mode

---

# Mission

Introduce Height Relief as the second registered `GenerationMode`,
proving the registry/UI/preparation architecture built in Packages
016–018 needs no changes to support a genuinely different Scene shape:
a variable number of bricks per pixel at variable Y (a true 3D relief),
rather than Flat Mosaic's fixed one-brick-per-pixel at `Y=0`.

**This is intentionally a simple, deterministic height generator meant
to validate the architecture — not a relief-quality algorithm.**
Advanced relief generation, smoothing, surface interpolation, adaptive
layer heights, structural analysis, and optimization are all out of
scope here and reserved for future packages.

---

# Scope

New:

- `generation/height_relief_generator.py`
- `generation/height_relief_registration.py`

Modified (one line):

- `generation/__init__.py` — added
  `from brickforge.generation import height_relief_registration  # noqa: F401`

Untouched (verified via `git diff`, not assumed):

- `generation/generation_mode.py`
- `generation/registry.py`
- `generation/flat_mosaic_registration.py`
- `generation/mosaic_generator.py`
- everything under `ui/`, `render/`, `engine/`, `services/`, `preparation/`

---

# Revisions Applied (per your approval)

1. **Renamed `max_height` → `max_layers`** on `HeightReliefSettings`,
   with a comment clarifying it's a layer count, not a physical height
   — the actual world-space height of a stack is
   `max_layers * definition.height_units`.
2. **Added a verification** confirming every stack shares identical
   X/Z and differs only in Y (see Verification Performed below —
   checked at both single-pixel and multi-pixel granularity).
3. **This document explicitly states** (see Mission above and
   Recommendations below) that this is a simple, deterministic
   validation vehicle, with advanced relief generation, smoothing,
   structural analysis, and optimization reserved for future packages.

---

# What Changed

## `generation/height_relief_generator.py` (new)

- `HeightReliefSettings` — `@dataclass(slots=True)`, independent of
  `GenerationSettings` (no shared fields, no inheritance):
  `default_part_number: str = "3023"`, `max_layers: int = 4`,
  `skip_transparent_pixels: bool = True`.
- `generate_height_relief(image, palette, catalog, settings) -> Scene`
  — for each non-transparent pixel: resolves one fixed part (once),
  maps one LDraw color via `palette.map_color()`, computes stack height
  from luminance, and places that many `SceneBrick`s stacked in Y.
- **Quantization** (deterministic, no smoothing/interpolation/adaptive
  scaling): luminance computed once via the existing
  `analysis.image_analysis.to_grayscale()`; per pixel,
  `height = 1 + round((luminance / 255.0) * (max_layers - 1))`.
  Luminance 0 → 1 layer (minimum); luminance 255 → `max_layers`
  (maximum) — purely a function of that pixel's own luminance, no
  neighbor influence, no image-wide adaptive component.
- **Placement**: X/Z use the same centered-origin formula shape as
  Flat Mosaic, written independently (not imported) to keep the two
  modes decoupled. Y stacks upward: layer `L` (0-indexed) sits at
  `y = L * definition.height_units`, confirmed correct against the
  renderer's actual camera up-vector (`glm.lookAt(..., up=(0,1,0))`,
  read directly from `render/camera.py` during planning — a verified
  fact, not an assumption).
- **Color**: one `MappedColor` resolved per pixel; every layer in that
  pixel's stack shares the same `color_code`.
- Brick ids: a running counter over row-major iteration, then
  bottom-to-top per pixel — deterministic, collision-free by
  construction.
- `_STUD_LDU = 20.0` is redefined locally rather than imported from
  `mosaic_generator.py`, keeping the two modes fully independent.

## `generation/height_relief_registration.py` (new)

- `HeightReliefSettingsPanel` — a real, standalone `SettingsPanel`
  implementation (not a stub), mirroring `FlatMosaicSettingsPanel`'s
  construction pattern exactly: its own `QWidget`/`QVBoxLayout`, a part
  `QComboBox` (from `PartCatalog.from_seed().all()`, default `"3023"`),
  a `QSpinBox` for `max_layers` (range 1–10, default 4), a `QCheckBox`
  for `skip_transparent_pixels` (default checked). Nothing shared with
  Flat Mosaic's panel or with `mosaic_generator.py`.
- `register_mode(GenerationMode(id="height_relief", display_name="Height Relief", version=1, ...))`
  at module scope — the same self-registration mechanism Flat Mosaic
  uses.

## `generation/__init__.py`

- One new import line for `height_relief_registration`'s self-registration
  side effect. `registry.py` itself was not touched — this file is, by
  design (per Package_016), "the one place that knows which concrete
  modes exist," not the registry's own logic.

---

# Definition of Done

- Height Relief exists as a fully independent `GenerationMode` —
  confirmed zero imports from `brickforge.ui` or `mosaic_generator.py`
  in either new file (AST inspection).
- The registry-driven UI automatically supports it — no `ui/` file was
  touched; the mode dropdown and settings panel swap picked it up
  purely from `list_modes()`.
- No architectural changes were required — `generation_mode.py`,
  `registry.py`, `flat_mosaic_registration.py`, `mosaic_generator.py`,
  and everything under `ui/`, `render/`, `engine/`, `services/`,
  `preparation/` are byte-for-byte untouched.
- Both modes coexist without special-case logic — nothing in the
  codebase branches on `mode.id` anywhere (still true; `MainWindow`
  remains completely mode-agnostic).
- Both modes produce valid `Scene` objects, verified through the real
  UI and a real GL context.

---

# Verification Performed

- `py_compile` clean on all new/modified files.
- **AST inspection**: zero imports of `brickforge.ui` or
  `mosaic_generator`/`flat_mosaic_registration` in either new file; zero
  `GenerationMode.id` branches anywhere.
- **Untouched-scope**: `git diff --stat` empty for
  `generation_mode.py`, `registry.py`, `flat_mosaic_registration.py`,
  `mosaic_generator.py`, and everything under `ui/`, `render/`,
  `engine/`, `services/`, `preparation/`.
- **Registry state**: `list_modes()` returns exactly
  `["flat_mosaic", "height_relief"]`; `get_mode("height_relief")`
  resolves with the correct `display_name`/`version`.
- **Determinism**: `generate_height_relief()` called twice on identical
  input produces field-identical `Scene`s (id, position, color_code
  compared per brick).
- **Quantization correctness**: 6 hand-computed luminance/`max_layers`
  cases (0, 128, 255 at various `max_layers` values) matched the
  formula exactly, including the `max_layers=1` degenerate case
  (always exactly 1 layer) and the `max_layers=10` boundary case.
- **X/Z identity within a stack** (your requested addition): for a
  single bright pixel producing a 5-layer stack, confirmed all 5
  bricks share identical X and identical Z, with 5 distinct Y values
  matching `L * height_units` exactly. Re-confirmed at multi-pixel
  granularity: two adjacent pixels produce two stacks with distinct
  X values, each internally uniform in X/Z.
- **Color-per-stack**: confirmed every brick in one pixel's stack
  shares one `color_code`.
- **Transparency**: a fully transparent pixel with
  `skip_transparent_pixels=True` produces zero bricks.
- **Real widget interaction** (real `MainWindow`, real GL context): mode
  dropdown has exactly 2 entries (`Flat Mosaic`, `Height Relief`);
  selecting Height Relief swaps in its own settings panel widget
  (distinct object from Flat Mosaic's); changing Height Relief's
  `max_layers` spin box and then reselecting the mode confirmed each
  mode's panel is independently constructed with no cross-contamination
  between modes.
- **Real button-click generation for both modes**:
  - Flat Mosaic on a 4×4 synthetic image: 16 bricks, status text
    `"Generated 16 bricks."` — byte-identical to Package_017/018's own
    tests, confirming zero regression.
  - Height Relief on a 4×4 near-white synthetic image (luminance ≈255,
    default `max_layers=4`): 64 bricks (16 pixels × 4 layers) across
    exactly 4 distinct Y levels (`0.0, 8.0, 16.0, 24.0`, matching
    `3023`'s `height_units=8.0`), rendered through the real
    `Renderer.render()` path with no crash or traceback.
- **Live application launch**: real GPU context (NVIDIA GeForce RTX
  3060 Ti), mode dropdown shows both modes, same pre-existing
  missing-geometry warnings as every prior package (now including
  `3023.dat`, absent from the bundled dev-test LDraw library —
  non-fatal, identical graceful handling to `3001`/`3003`/`3004`/`3005`
  already seen in every prior package's verification), no new
  tracebacks.
- `git status` confirms exactly the planned scope: two new files, one
  file with a single added import line, `Package_019.md` added, plus
  the long-standing pre-existing unstaged changes to
  `docs/ARCHITECTURE.md` and `.vscode/settings.json` (left alone, as
  always).

---

# Recommendations for Future Packages

This package is deliberately a **simple, deterministic validation
vehicle** for the Generation Mode architecture — not a finished relief
algorithm. Explicitly out of scope here and left for future packages:

- Advanced relief generation (e.g. non-linear or perceptual luminance
  curves, multiple parts per stack, edge-aware height changes).
- Smoothing / surface interpolation across neighboring pixels.
- Adaptive layer heights (image-content-driven `max_layers` scaling).
- Structural analysis, stability checking, automatic support generation.
- Cost/structural optimization of any kind — the raw `Scene` is
  produced as-is, exactly as required.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
