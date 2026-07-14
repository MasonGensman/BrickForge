# StudWorks

# Package 014

## Title

Generate LEGO Mosaic — First End-to-End Workflow

---

# Mission

Make the application usable without Python code: import an image, click
"Generate LEGO Mosaic," watch the mosaic appear in the viewport. Connects
the already-independently-working Package_009-012 pieces through the UI
for the first time. No AI, no optimization, no Studio export.

---

# Scope

- `src/brickforge/render/renderer.py` (add `set_scene()`)
- `src/brickforge/ui/widgets/image_preview_widget.py` (Generate button +
  settings controls)
- `src/brickforge/ui/main_window.py` (signal wiring, generation handler,
  downsampling cap)

---

# Sequencing Note

This work was originally going to be numbered Package_013, but Package_013
was already committed (`7f6cc574`, per-brick color rendering) before this
scope was defined. A later message referred to this workflow as an
already-completed "Package_013" while proposing new work as "Package_014"
— that assumption was incorrect; nothing beyond planning existed yet. Per
your explicit choice, this workflow is Package_014; the real-LDraw-library
catalog work becomes Package_015.

---

# Definition of Done

- A user can launch the app, import an image, click "Generate LEGO
  Mosaic," and see the generated, correctly-colored mosaic replace the
  demo scene in the viewport.
- Multiple generations replace cleanly (no accumulation).
- No image loaded → a clear message, no crash. Generation failure → a
  clear message, application keeps running.
- Renderer shaders, camera, grid, and OpenGL pipeline untouched.

---

# Completion Notes

## Resolved Decisions

Per your explicit selection when approving sequencing:
- **Downsampling cap**: added. `generate_mosaic()` runs at native image
  resolution with one brick per pixel (Package_012's deliberate scope) —
  unchecked, a real photo could attempt millions of bricks on the very
  first thing a user tries. `MainWindow._capped_image()` deterministically
  downscales to `MAX_MOSAIC_DIMENSION = 48` on the longer side (aspect
  ratio preserved), reusing the existing, already-deterministic
  `analysis.resize()` — not a new resize implementation, not a user-facing
  control (satisfying "no resizing UI").
- **Part dropdown default**: `"3005"` (Brick 1×1), matching
  `GenerationSettings`'s existing programmatic default rather than the
  mockup's listed first item (2×4).
- **Error reporting split**: the "no image loaded" precondition is
  reported locally by `ImagePreviewWidget` (it owns that state, checked
  before any signal fires). A failure during generation is reported via
  `MainWindow`'s status bar, matching the existing `on_brick_selected`
  feedback convention, rather than reaching back into the widget's
  internals.

## Exact Implementation

**`render/renderer.py`**: one new method, `set_scene(scene: Scene) ->
None` — `self.scene = scene`. Nothing else changes; `render()` already
re-reads `self.scene` fresh every frame (confirmed by inspection before
implementing), so no loop logic needed touching.

**`ui/widgets/image_preview_widget.py`**: added `generate_button`,
`part_combo` (populated from `PartCatalog.from_seed().all()`, all 10 seed
parts, default `"3005"`), `skip_transparent_checkbox` (checked by
default), `origin_combo` (`OriginMode.CENTERED`/`CORNER`, default
Centered), a separator, and `generate_requested = Signal(object, object)`.
Layout follows the given mockup order exactly (Import → Generate →
settings → separator → existing thumbnail/info). `generate_lego()`
checks `self.manager.has_image` locally (message + no signal if false),
otherwise builds one `GenerationSettings` from the three controls'
current values and emits it with the current `ImageResource`. `import_image()`/`display()` are byte-for-byte unchanged.

**`ui/main_window.py`**: `connect_signals()` gained one line wiring
`image_preview.generate_requested` → `on_generate_lego` — the same
pattern already used for `library.brick_selected`. `on_generate_lego(image, settings)`:
reuses `self.viewport.renderer.brick_manager.library.library_path`
(never re-derives the LDraw path independently — a second,
independently-computed `Path(__file__)...` in a new file would use a
different relative hop-count than `renderer.py`'s own, a real way to get
it wrong); applies `_capped_image()`; constructs `PaletteEngine` and
`PartCatalog.from_seed()` fresh (both cheap, no persistent `MainWindow`
state introduced); calls `generate_mosaic()`; calls `renderer.set_scene()`
and `self.viewport.update()`; reports success or failure via the status
bar. `create_widgets()`/`create_menu()`/`on_brick_selected()` are
byte-for-byte unchanged.

## Verification Performed

- `py_compile` clean on all three files.
- **`ImagePreviewWidget` in isolation**: Generate clicked with no image →
  exact message, no signal emitted. Generate clicked with an image loaded
  → signal fires with the correct `(ImageResource, GenerationSettings)`,
  settings matching control defaults exactly. Changing each of the three
  controls (part, checkbox, origin) individually verified to change the
  corresponding field in the next emitted `GenerationSettings`. Part
  dropdown confirmed to list exactly the 10 seed catalog part numbers.
- **Full `MainWindow` integration**, driven against a real initialized
  `Renderer` with a real GPU/GL context (this environment has one
  available): confirmed the demo scene (3 original bricks, `3001.dat`/
  `3003.dat`/`3004.dat`) is present before any generation. Called
  `on_generate_lego()` directly with a synthetic 3×2 test image (matching
  Package_012's exact verification pattern: red/white/transparent/
  red/red/white) — confirmed `renderer.scene` is completely replaced with
  exactly 5 bricks (the transparent pixel correctly excluded), all using
  the default part. Confirmed the 3 original demo bricks are entirely
  gone (clean replacement, not accumulation) via exact id-set comparison.
  Confirmed the status bar shows `"Generated 5 bricks."`.
- **Multiple generations replace cleanly**: called `on_generate_lego()` a
  second time with a different part number and `OriginMode.CORNER` —
  confirmed the scene is fully replaced again (not merged with the
  first), all bricks use the new part, and `CORNER` placement is exactly
  correct (`(0,0)` pixel at world `(0,0,0)`) — proving part-dropdown and
  origin-mode selections both genuinely propagate through to generation
  output, not just accepted and ignored.
- **Downsampling cap**: an already-small image (`10×8`) returned
  literally unchanged (`is` identity, not just equal — confirming the
  no-op path avoids unnecessary work). A `200×100` image capped to
  exactly `48×24` (aspect ratio preserved exactly, longer side capped). A
  `50×300` image capped to `8×48` (capping correctly applied to whichever
  side is longer). Both oversized cases confirmed byte-identical across
  two independent calls (deterministic).
- **Generation-failure path**: forced a failure via an invalid
  `default_part_number`; confirmed the status bar reports
  `"Generation failed: PartCatalog has no part '9999999-does-not-exist'"`
  and the application — and the renderer — remain fully functional
  afterward (no crash, no corrupted state).
- **Regression testing**: re-ran the full Package_003/005/007/008/009/
  010/011/012/013 suite — all still pass.
- **Live application verification**: `src/main.py` launches identically
  to Package_013 — same grid, same three missing-part warnings, no
  crash, no traceback, before any button is clicked.
- `git status` confirms exactly the three planned files changed.

## Recommendations for Future Packages

- **Package_015** (per your direction): replace the 10-part seed catalog
  with a real, installed LDraw library — the natural next step, since
  every piece this package wires together (`PartCatalog`, `PaletteEngine`,
  `generate_mosaic`) is already built to consume whatever `PartCatalog`
  it's given, with no changes needed here to support a larger catalog.
- **`MAX_MOSAIC_DIMENSION = 48`** is a placeholder default — worth
  revisiting once real generated mosaics can be visually inspected (the
  LDraw parts library is still empty in this environment, so no brick has
  ever actually been visible on screen in any package so far).
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
