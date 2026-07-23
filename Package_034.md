# StudWorks

# Package 034

## Title

Generation Input System — The Boundary Between Raw Images and Generation

---

# Mission

Establish how source images enter StudWorks and become deterministic
generation inputs, and how Projects own that asset. No LEGO generation
occurs in this package — it defines the boundary between raw user assets
and the future generation pipeline, following an explicit roadmap pivot
away from further editor-tool work.

---

# Scope

New:

- `preparation/generation_input.py` (`GenerationInput`)

Modified:

- `analysis/image_analysis.py` — new `rotate90()` primitive
- `io/image_loader.py` — EXIF orientation correction fix
- `preparation/image_preparation.py` — `ImagePreparationSettings` gains
  `crop_rect`/`rotation_degrees`; `prepare_image()` extended
  crop → rotate → resize
- `project/project.py` — `generation_input: GenerationInput | None`,
  serialization support with graceful degradation
- `ui/widgets/image_preview_widget.py` — builds one `GenerationInput` per
  import instead of two separate load/prepare calls; new `image_imported`
  signal
- `ui/main_window.py` — stores imported `GenerationInput` on the current
  Project

Tests:

- `tests/test_image_analysis.py`, `tests/test_image_preparation.py`,
  `tests/test_generation_input.py`, `tests/test_image_loader.py` (all new)
- `tests/test_project_serialization.py` — `ProjectGenerationInputTests`

**Untouched — confirmed via `git diff --stat`**: `render/*`, `tools/*`,
`selection/*`, `transform/*`, `engine/*`. This package touches only the
image-input and project-persistence layers.

---

# Inspection Findings

**Most of the needed infrastructure already existed, exactly shaped the
way this package wanted it.** `ImageResource` already served as both "the
imported original" and "the prepared result" (both are the same type).
`prepare_image()` (Package_018) was already deterministic, stateless, and
generation-mode-agnostic — its own docstring explicitly deferred "crop,
rotate, flip, padding" to a future package; this is that package.
`crop()`/`resize()` primitives already existed in `image_analysis.py`; no
`rotate` primitive did.

**A real, empirically-confirmed gap**: verified that
`QImageReader.autoTransform()` defaults to `False` in this Qt build, and
the bare `QImage(path)` convenience constructor `ImageLoader` was using
never applies EXIF orientation correction — meaning EXIF-rotated photos
(routine output from phone cameras) previously decoded in their raw,
un-rotated orientation. Fixed by switching to `QImageReader` +
`setAutoTransform(True)`. **Verified with real, hand-constructed EXIF
bytes, not just a configuration check**: a 4×2 test JPEG tagged
Orientation=6 ("rotate 90° clockwise to display correctly") loaded as
2×4, with a marker pixel correctly moved from top-left to top-right —
confirming the fix actually works end-to-end, not merely that the option
was set.

**`Project` had zero image-related fields** before this package — a
confirmed, clean gap. `ImagePreviewWidget`'s existing import flow was
entirely self-contained UI state, never touching `Project`/
`ProjectManager` at all.

**`ImageManager`** confirmed via grep to have no consumer besides
`ImagePreviewWidget` — free to stop using it there without any other
blast radius. Left in place, unmodified, as unrelated cleanup.

---

# Architecture Assessment

The two genuinely missing pieces were (a) a `rotate` primitive and
crop/rotate wiring into the existing `prepare_image()`, and (b) a way for
`Project` to own a reference to "the image + settings that produced this"
— nothing else needed to change. `optimize_scene`/`export_scene`/
`prepare_image` itself all being plain functions (not classes) throughout
this codebase directly informed extending `prepare_image()` rather than
wrapping it in a new pipeline class.

**Resolved a real inconsistency in the mission's own spec**: the "Image
Preparation Pipeline" section ordered `Crop → Rotate → Resize`, while the
"User Workflow" section ordered `Crop → Scale → Rotate`. Resolved by
separating *automatic* EXIF correction (must happen immediately after
decode, before any user-specified crop, since crop coordinates are
meaningless against a still-sideways image) from *user-specified*
rotation (kept in the Pipeline section's order, treated as the more
precise architectural statement of the two).

---

# Generation Input Architecture

`GenerationInput` (`preparation/generation_input.py`) — the mission's own
suggested name, chosen over `ImagePreparationPipeline` (would just be
`prepare_image()` again under a class wrapper — rejected, since every
pipeline stage in this codebase is a plain function) and `ImageAsset`/
`PreparedImage` (both under-describe the source+settings+result bundle
this needs to be):

```python
@dataclass(slots=True)
class GenerationInput:
    source_path: Path
    content_hash: str
    settings: ImagePreparationSettings
    prepared_image: ImageResource  # in-memory only, never serialized

    @classmethod
    def from_source(cls, path, settings=None) -> "GenerationInput":
        resource = ImageLoader().load(path)
        return cls(
            source_path=Path(path), content_hash=resource.content_hash,
            settings=settings or ImagePreparationSettings(),
            prepared_image=prepare_image(resource, settings),
        )
```

One canonical factory, used identically at fresh-import time and at
project-reload time — calling it twice with the same path and settings
reproduces byte-identical output, verified directly, by `prepare_image`'s
own existing determinism guarantee.

**Pipeline extension**: `ImagePreparationSettings` gains `crop_rect:
tuple[int,int,int,int] | None` and `rotation_degrees: int` (0/90/180/270
only). `prepare_image()` applies crop, then rotation (via the new
`rotate90()`, restricted to 90° multiples — arbitrary angles need an
interpolation algorithm choice, exactly the "algorithm-specific behavior"
this package's own Determinism section asks to avoid; deferred, not
built), then the existing fit-to-`max_dimension` resize.

**Capabilities recommendation, evaluated per the mission's own list**:
PNG/JPEG/transparency were already fully supported (no change). EXIF
orientation fixed as described above — always-on, not a user setting,
since there's no reasonable case for wanting it off. Crop and 90°-rotate
added. Aspect-ratio preservation already existed. **Optional padding
recommended out of scope**: no current generation mode requires a
specific target aspect ratio (Flat Mosaic and Height Relief both already
work with arbitrary width/height) — no real consumer yet, not built.

---

# Project Ownership

`Project` gains `generation_input: GenerationInput | None = None`
(starts `None` — unlike `scene`, which always exists even empty, a
brand-new project has no imported image at all). Owns the reference —
`source_path`, `content_hash`, `settings` — never the raw pixel data of
either the original or the prepared image, and not generation-mode
metadata (which mode/settings produced the current *Scene* — evaluated
and deferred, since that's explicitly a generation-side concern this
package stops short of).

**UI integration, kept minimal per this package's own requested planning
output** (six sections, none an "interaction model," unlike every prior
editing-tool package's explicit "Move Model"/"Delete Model" — a signal
this package is architecture/pipeline-focused, not UI-focused):
`ImagePreviewWidget.import_image()` now builds one `GenerationInput`
instead of its previous two separate `ImageManager.load()` +
`prepare_image()` calls, eliminating duplicate load/decode work, and
emits a new `image_imported` signal. `MainWindow` stores the result on
`project_manager.current_project.generation_input` and marks the project
dirty — the same widget-emits/MainWindow-reacts convention used
throughout this app. **No interactive crop/rotate UI was built** — those
settings are real, tested, and programmatically usable, ready for a
future package to build an actual UI on top of.

---

# Serialization

**Store the reference (path + content_hash + settings); regenerate the
prepared image on load.** Never store prepared or original pixel data in
the `.sws` file.

```json
"generation_input": {
    "source_path": "C:\\...\\photo.png",
    "content_hash": "9b537cef...",
    "settings": {"max_dimension": 48, "crop_rect": [1,1,3,2], "rotation_degrees": 90}
}
```

Justified by: (1) determinism — `prepare_image()` already guarantees
identical output from identical input+settings, verified directly, so
regenerating is exact, not approximate; (2) `.sws`'s human-readable,
diffable JSON philosophy (Package_025) — embedding pixel data would
destroy both properties for any project with an image; (3) simplicity —
no new binary-embedding machinery.

**Known, deliberately-accepted limitation**: if the source file has moved
or been deleted since save, it can't be regenerated on load.
`Project.from_dict()` catches the resulting `OSError`/`ValueError` from
`GenerationInput.from_source()`, logs a warning, and leaves
`generation_input` as `None` rather than blocking the whole project load
— matching this codebase's established graceful-degradation pattern
(`BrickManager`, `ColorResolver`). The Scene is completely unaffected
either way, since Scene and `generation_input` are independent fields —
verified directly. Considered and declined: copying the imported file
into a project-adjacent assets folder to eliminate this risk entirely —
real, additional infrastructure (folder management, relative-path
resolution, cleanup) with no evidence yet that this is an actual problem.

---

# Definition of Done

- Projects support generation assets (`generation_input`).
- Images can be imported — end-to-end through the real UI, verified.
- Deterministic preparation exists — crop/rotate/resize, all verified
  deterministic and immutable.
- A reusable Generation Input pipeline is established
  (`GenerationInput.from_source()`), independent of any specific AI or
  generation algorithm.
- Architecture is ready for future image analysis — `prepared_image` is
  the one stable interface; no generation algorithm depends on raw files.

---

# Verification Performed

- `py_compile` clean on every new/modified file.
- `git diff --stat` confirms `render/`, `tools/`, `selection/`,
  `transform/`, `engine/` are **completely untouched**.
- Empirically verified before implementation: `np.rot90(pixels, k=-1)`
  produces a clockwise rotation; `QImageReader.autoTransform()` defaults
  `False`; `setAutoTransform(True)` correctly fixes it (confirmed against
  real hand-constructed EXIF bytes, not just configuration).
- **8 tests, `test_image_analysis.py`**: `rotate90()` at 0/90/180/270
  verified by exact corner-pixel movement (not just "something changed"),
  four consecutive 90°s return to the original, invalid degrees raise
  `ValueError`, always returns a copy, determinism.
- **10 tests, `test_image_preparation.py`**: existing no-op and
  resize-only behavior unchanged (explicit regression check against
  Package_018); crop produces correct dimensions *and* extracts the
  correct region (verified by pixel position, not just size); rotate-90
  swaps dimensions, rotate-180 doesn't; full crop+rotate+resize pipeline;
  `content_hash` always preserved from source; original image never
  mutated; determinism.
- **7 tests, `test_generation_input.py`**: builds correctly from a real
  (Qt-written, no new dependency) test image; `content_hash` matches the
  underlying loader; settings correctly applied; defaults used when none
  given; missing source raises `FileNotFoundError`; unsupported format
  raises `ValueError`; determinism across two independent calls.
- **6 tests, `test_image_loader.py`**: plain PNG loads correctly; missing
  file and unsupported extension raise correctly; a plain JPEG with no
  EXIF loads unaffected (confirms the fix doesn't disturb ordinary
  images); **Orientation=6 and Orientation=3 verified against real,
  hand-constructed EXIF bytes** — dimensions and marker-pixel position
  both checked, not just "no crash" (JPEG's lossy compression required
  tolerance-based pixel assertions rather than exact equality — a
  real compression-artifact finding, not a bug).
- **3 new tests in `test_project_serialization.py`**: a project with no
  `generation_input` has no such key in its serialized output; a real
  round-trip (Save → Open) through `ProjectManager` preserves
  `source_path`/`content_hash`/`settings` and regenerates a
  byte-identical `prepared_image`, with the Scene completely unaffected;
  a missing source image on reload degrades gracefully (`generation_input`
  is `None`, Scene still loads correctly) — all 13 pre-existing tests in
  this file, including the byte-for-byte golden-file comparisons,
  re-confirmed passing unchanged, since `generation_input` is a purely
  additive, optional field.
- **Real end-to-end UI test**: fresh project starts with no
  `generation_input`; a real import through `ImagePreviewWidget`/
  `MainWindow` populates `project_manager.current_project.generation_input`
  and marks the project dirty; Generate LEGO still works after the widget
  refactor (regression check); a full Save/New/Open round-trip preserves
  `generation_input` with the prepared image regenerated identically; a
  missing source file on reload degrades gracefully while the Scene still
  loads.
- Full regression suite re-run: **197 tests** across fourteen suites (163
  pre-existing + 34 new) — all pass.
- `git status` confirms exactly the planned scope.

---

# Readiness for Image Analysis

`analysis/image_analysis.py`'s existing `analyze(image) -> ImageStatistics`
entry point already consumes a plain `ImageResource` — exactly what
`GenerationInput.prepared_image` is. A future analysis package calls
`analyze(generation_input.prepared_image)` with zero new plumbing. The
pipeline boundary this package establishes — future packages consume only
`prepared_image`, never a raw file — is already load-bearing: nothing in
`GenerationInput`'s public surface exposes raw file bytes at all.

---

# Recommendations for Future Packages

- An interactive crop/rotate UI (drag handles, a crop-rectangle selector)
  is the natural next step to make `ImagePreparationSettings`' new fields
  reachable by users, not just programmatically.
- Optional padding/letterboxing remains deferred until a generation mode
  actually needs a fixed target aspect ratio.
- `ui/toolbar.py`'s module-level `project_manager` singleton
  (Package_026) and the renderer's upside-down LDraw geometry bug
  (Package_024) remain outstanding and unaffected by this package.
