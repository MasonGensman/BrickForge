# StudWorks

# Package 009

## Title

Image Foundation

---

# Mission

Establish the cleanest architecture for importing, storing, and displaying
images that future AI packages can build upon. Not AI, not image analysis
— the foundation those packages will consume.

---

# Scope

New files:

- `src/brickforge/io/image_resource.py`
- `src/brickforge/io/image_loader.py`
- `src/brickforge/io/image_manager.py`
- `src/brickforge/ui/widgets/image_preview_widget.py`

Minimal additive edits:

- `src/brickforge/ui/widgets/__init__.py` (+1 line, export)
- `src/brickforge/ui/main_window.py` (+4 lines, one more dock widget)

---

# Requirements

1. `ImageResource` / `ImageLoader` / `ImageManager`, mirroring the `ldraw/`
   (loader+data) and `project/` (current-state manager) conventions.
2. PNG / JPEG / BMP support via Qt image decoding.
3. All loaded images normalized to RGBA uint8 numpy arrays.
4. A stable SHA-256 source identifier on `ImageResource`.
5. Image subsystem independent of `engine/`, `render/`, and AI.
6. A minimal user-visible confirmation that loading works — no OpenGL
   textures, no renderer redesign, no UI redesign.

---

# Definition of Done

- `ImageResource`, `ImageLoader`, `ImageManager` exist in `io/`, verified
  against real PNG/JPEG/BMP files.
- No AI, no image analysis, no brick generation, no export, no renderer
  change, no UI redesign.
- The `io/` image subsystem depends on nothing in `engine/`/`render/`/`ui/`
  — verified via AST inspection, not assumed.
- A working, user-triggerable preview confirms the pipeline end-to-end.
- Existing Package_001–008 behavior fully unchanged.

---

# Completion Notes

## Architecture

Mirrors two existing, established conventions rather than inventing new
ones:

- **`ldraw/`'s loader+data shape**: `ImageResource` (pure data — `path`,
  `width`, `height`, `format`, `pixels`, `content_hash`) sits alongside
  `ImageLoader` (resolves/validates/decodes) in `io/`, the same way `Part`
  sits alongside `LDrawLoader`/`LDrawParser` in `ldraw/` rather than in
  `models/` — raw imported data lives with its import mechanism.
- **`project/ProjectManager`'s current-state shape**: `ImageManager` holds
  `self.current_image: ImageResource | None`, with `load()`/`clear()`/
  `has_image` — the same shape as `ProjectManager.current_project`, not
  the static lookup-catalog shape of `BrickDatabase`/`PartCatalog`.

`QImage` (PySide6, already the project's only formal dependency) is used
purely as the *decode mechanism* — the moment decoding finishes, the data
is converted to a plain `numpy` RGBA array and `QImage` is discarded. The
*stored* representation (`ImageResource.pixels`) is Qt-independent, even
though the *loading* step uses Qt. `Pillow` was considered and rejected:
it isn't installed or declared as a dependency anywhere in this project
(confirmed by inspection), and `QImage` was empirically verified to
already decode all three target formats correctly in this environment
before any code was written.

## Source Hash

`content_hash` is SHA-256 of the **raw source file bytes**, computed via
`path.read_bytes()` before decoding — not a hash of the normalized pixel
array. "Stable source identifier" was read as identifying *this exact
imported file*, matching how content-addressable caching keys are
conventionally computed (hash the input, not a derived representation),
independent of any future change to how pixels get normalized.

## The "Displaying" Question — Resolved

The plan flagged a genuine ambiguity between "provide a minimal
user-visible confirmation" and "no renderer redesign / no UI redesign."
Resolved per your refinement: no OpenGL texture (would require adding
sampler-uniform support to `Shader` and a new draw path — real renderer
surface area), no `QMessageBox`-only confirmation (wouldn't actually prove
pixel decoding worked, only metadata extraction). Instead: a small,
self-contained `ImagePreviewWidget` — one more dock widget, added exactly
the way `BrickLibraryWidget`/`PropertiesWidget` already are, with its own
"Import Image..." button, thumbnail, and info label. It owns its own
`ImageManager` internally; nothing about `MainWindow`'s existing widgets,
signal wiring, or layout logic was touched — `connect_signals()` is
byte-for-byte unchanged.

## Verification Performed

- `py_compile` clean on all 6 touched/new files.
- **PNG/JPEG/BMP loading**: built real test images in all three formats,
  loaded each through `ImageLoader`/`ImageManager`, confirmed correct
  `width`/`height`/`format` for all three.
- **RGBA normalization**: confirmed `pixels.shape == (height, width, 4)`
  and `dtype == uint8` for all three formats; confirmed a PNG (lossless)
  pixel value round-trips byte-exact (`(255, 0, 0, 255)` at a known
  coordinate).
- **Hash verification**: confirmed `ImageResource.content_hash` matches an
  independently computed `hashlib.sha256(path.read_bytes()).hexdigest()`
  for each loaded file — not merely "a hash exists," but numerically
  correct against a separate computation.
- **Dependency isolation**: `ast`-parsed all three `io/` files and
  enumerated their actual `import`/`from...import` statements (not a text
  search, which previously produced a false positive in Package_008 —
  learned from that and used the rigorous method from the start this
  time). Confirmed zero references to `brickforge.engine`,
  `brickforge.render`, or `brickforge.ui` in any of the three files.
- **Widget end-to-end verification**: drove `ImagePreviewWidget.manager.load()`
  → `.display()` directly (bypassing the file dialog, which needs real
  user interaction) against a real PNG — confirmed the thumbnail `QPixmap`
  is non-null and decodable, and the info label shows the correct
  filename, dimensions, format, and hash prefix.
- **Regression testing**: re-ran Package_003's `Scene` API checks,
  Package_005's `u_model` matrix checks, Package_007's catalog/color
  checks, and Package_008's `from_definition` equivalence check — all
  still pass.
- **Live application verification**: `src/main.py` launches identically to
  Package_008 — same grid, same three missing-part warnings, no crash, no
  traceback — with the new Image Preview dock now present in the window.
- `git status`/`git diff --stat` confirm exactly the planned files
  changed: 4 new files, and 5 total inserted lines across
  `main_window.py`/`widgets/__init__.py`, with `connect_signals()` and
  every other existing widget's behavior untouched.

## Recommendations for Future Packages

- **`content_hash` enables future caching**: a future package could skip
  re-decoding a file whose hash was already seen, or use it as an AI
  analysis cache key — the field exists now specifically for that, unused
  by this package beyond being computed and displayed.
- **Texture upload** (GPU `Mesh`-equivalent for images) remains
  unimplemented — deliberately deferred; `ImageResource.pixels` is already
  exactly the array shape a future `glTexImage2D` call would need.
- **Additional formats** (GIF, TIFF, WEBP — confirmed available via Qt in
  this environment but not enabled) belong in a future package if a
  concrete need arises; the allowlist in `image_loader.py` is a one-line
  change.
- All prior packages' outstanding recommendations (LDraw library
  consolidation, BrickLink ID mapping, per-brick color, `bounding_box`
  computation, `SceneBrick`/`BrickDefinition` reconciliation with catalog
  UI) remain outstanding and unaffected by this package.
