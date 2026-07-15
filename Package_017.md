# StudWorks

# Package 017

## Title

Generation Mode UI Migration (Architecture Package A001, Step 2)

---

# Mission

Migrate `ImagePreviewWidget` and `MainWindow` to consume the
`GenerationMode` registry built in Package_016, replacing the
hardcoded "Flat Mosaic" controls and generation call with a
registry-driven mode selector, a swappable per-mode settings panel, and
a mode-agnostic generation handler. This is Step 2 of the A001 roadmap:
the application now runs Flat Mosaic *through* the registry rather than
calling it directly, and adding a second mode in the future requires no
UI changes.

---

# Scope

Modified:

- `ui/widgets/image_preview_widget.py`
- `ui/main_window.py`

Untouched (verified via `git diff`, not assumed):

- `generation/generation_mode.py`
- `generation/registry.py`
- `generation/flat_mosaic_registration.py`
- `generation/__init__.py`
- `generation/mosaic_generator.py`
- everything under `render/`, `engine/`, `services/`

---

# Revisions Applied (per your approval)

1. **No synthetic second mode.** The plan originally proposed
   registering a throwaway second `GenerationMode` purely to prove
   multi-mode UI behavior structurally. Per your instruction, this was
   dropped — Package_018 will validate multi-mode behavior naturally
   once a real second mode exists. The registry still holds exactly one
   mode after this package (confirmed in verification).
2. **`MAX_MOSAIC_DIMENSION` → `MAX_GENERATION_DIMENSION`.** Renamed in
   `main_window.py`, and its comment rewritten to describe it as a
   generation-agnostic preprocessing safeguard rather than a
   mosaic-specific one.

# Architectural Rule Enforced

**`MainWindow` never branches on `GenerationMode.id`.**
`on_generate_lego` calls `mode.generate(image, palette, self.catalog,
settings)` unconditionally — there is no `if mode.id == "flat_mosaic"`
anywhere in either modified file. Confirmed by AST inspection (no
`Compare` node anywhere compares a `.id` attribute) in addition to
manual review.

---

# What Changed

## `ImagePreviewWidget`

- Removed: the mosaic-specific part `QComboBox`, transparency
  `QCheckBox`, and origin `QComboBox`, along with their imports
  (`GenerationSettings`, `OriginMode` from `mosaic_generator`,
  `PartCatalog`). The widget no longer imports anything mosaic-specific
  — confirmed by AST import inspection.
- Added: a "Generation Mode" label + `QComboBox` populated from
  `list_modes()`, storing each `GenerationMode` as item data. A
  `settings_container`/`settings_layout` that holds whichever widget
  the current mode's `create_settings_panel()` produces, swapped
  whenever the combo box selection changes. The widget keeps a live
  reference to the current `SettingsPanel` instance
  (`self._current_panel`) so `get_settings()` can be called on demand
  at generate time, and to the current `GenerationMode`
  (`self._current_mode`).
- The Generate button is relabeled "Generate LEGO" (generic, no
  mode name baked in).
- `generate_requested` is now `Signal(object, object, object)`,
  emitting `(image, mode, settings)` instead of `(image, settings)`.
- Layout order follows the approved mockup: Import Image → Generation
  Mode label/dropdown → separator → settings panel → separator →
  Generate LEGO → separator → thumbnail → info.
- `import_image()` and `display()` are untouched in behavior.

## `MainWindow`

- Removed the `generate_mosaic` import; added a `GenerationMode` import
  (type-hint only — `MainWindow` never constructs or looks up modes
  itself, it only receives one via the signal).
- `MAX_MOSAIC_DIMENSION` renamed to `MAX_GENERATION_DIMENSION`
  (value unchanged: `48`).
- `on_generate_lego(self, image, settings)` became
  `on_generate_lego(self, image, mode: GenerationMode, settings)`.
  The body is otherwise the same shape as before — resolve the LDraw
  library, build the palette, run generation, set the scene, update the
  status bar — except the generation call is now `mode.generate(image,
  palette, self.catalog, settings)` instead of a direct call to
  `generate_mosaic(...)`.
- The status message text is unchanged
  (`f"Generated {len(list(scene))} bricks."`) — no additional visible
  UI text was introduced beyond the mode selector itself, per the
  approved scope.

---

# Definition of Done

- `ImagePreviewWidget` has zero hardcoded knowledge of Flat Mosaic —
  confirmed by AST-based import inspection (no import of
  `mosaic_generator`, `GenerationSettings`, or `OriginMode`).
- `MainWindow` has zero hardcoded knowledge of Flat Mosaic and never
  branches on `mode.id` — confirmed by AST inspection.
- Selecting a mode and clicking Generate produces output identical to
  calling that mode's `generate()` function directly.
- `generation/*` (registry, contract, Flat Mosaic registration,
  `mosaic_generator.py`) and `render/`, `engine/`, `services/` are
  byte-for-byte untouched — confirmed via `git diff --stat`, empty
  output.
- The registry contains exactly one mode after this package (no
  synthetic mode was added).
- `MAX_GENERATION_DIMENSION` exists; `MAX_MOSAIC_DIMENSION` does not.
- Live application launches and a real click-through (import → select
  mode → Generate) produces bricks in the viewport.

---

# Verification Performed

- `py_compile` clean on both modified files.
- **AST import inspection**: `image_preview_widget.py` imports only
  `GenerationMode` and `list_modes` from `brickforge.generation.*` —
  nothing from `mosaic_generator` or `flat_mosaic_registration`.
  `main_window.py` imports only `GenerationMode` — no
  `generate_mosaic`, `GenerationSettings`, or `OriginMode` anywhere.
- **AST `.id`-branch inspection**: walked both files' `Compare` nodes
  looking for any comparison against a `.id` attribute access — none
  found in either file.
- **Untouched-scope confirmation**: `git diff --stat` against
  `generation/generation_mode.py`, `generation/registry.py`,
  `generation/flat_mosaic_registration.py`, `generation/__init__.py`,
  `generation/mosaic_generator.py`, and everything under `render/`,
  `engine/`, `services/` produced zero output.
- **Registry state**: `list_modes()` returns exactly one
  `GenerationMode` (`id="flat_mosaic"`) after this package — the
  synthetic-mode step was correctly omitted.
- **Widget-level check**: constructed `ImagePreviewWidget` standalone —
  mode combo has exactly one entry ("Flat Mosaic"), a settings panel is
  embedded automatically on construction, and its default
  `get_settings()` output matches Package_016's verified defaults
  (`"3005"`, `skip_transparent_pixels=True`, `OriginMode.CENTERED`).
- **Direct-call equivalence**: built a `Scene` via `mode.generate(...)`
  directly and via `MainWindow.on_generate_lego(image, mode,
  settings)` against an identical synthetic 4x4 image — every
  `SceneBrick` field (`id`, `part_name`, `color_code`, `position`,
  `rotation`) matched exactly between the two paths.
- **True end-to-end test**: wrote a real PNG to disk, loaded it through
  `image_preview.manager.load()`, called `.display()`, then fired the
  *actual* `generate_button.click()` (not a direct method call) and
  confirmed via `app.processEvents()` that `generate_requested` reached
  `MainWindow.on_generate_lego`, produced 16 bricks for the 4x4 image,
  and updated the status bar to `"Generated 16 bricks."` — the same
  text format as before this package.
- **Live application verification**: `MainWindow` launched with a real
  GPU context (NVIDIA GeForce RTX 3060 Ti, confirmed via the renderer's
  own startup banner), same pre-existing missing-part warnings as prior
  packages (test LDraw library genuinely lacks `3001`/`3003`/`3004`;
  `3005` also logged as missing once actual generation ran and the
  renderer tried to load its geometry — expected, graceful, non-fatal,
  identical handling to Package_015's fix), no crash, no traceback.
- `git status` confirms exactly the planned scope: two files modified,
  `Package_017.md` added, plus the long-standing pre-existing unstaged
  changes to `docs/ARCHITECTURE.md` and `.vscode/settings.json` (left
  alone, as always).

---

# Recommendations for Future Packages

- **Package_018** (per your own framing): the natural next step is a
  real second `GenerationMode`. This will be the first genuine proof
  that the mode dropdown, settings-panel swap, and mode-agnostic
  `on_generate_lego` all behave correctly with more than one entry —
  deliberately not simulated here.
- **Terminology** (carried over from Package_016, still not yet
  needed): `GenerationSettings` → `FlatMosaicSettings` and
  `generation/mosaic_generator.py` → a `generation/modes/` subpackage
  remain reasonable renames once a second mode exists to prove the
  restructuring is actually needed.
- All prior packages' outstanding recommendations remain outstanding
  and unaffected by this package.
