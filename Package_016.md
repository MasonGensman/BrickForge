# StudWorks

# Package 016

## Title

Generation Mode Registry (Architecture Package A001, Step 1)

---

# Mission

Establish the `GenerationMode` registry infrastructure approved in
Architecture Package A001, and register the existing Flat Mosaic
implementation as its first entry — without modifying the UI, renaming
any existing file, or changing generation behavior. Step 1 of the
roadmap only; the UI continues to consume mosaic generation exactly as
it did before this package.

---

# Scope

New files:

- `generation/generation_mode.py`
- `generation/registry.py`
- `generation/flat_mosaic_registration.py`

Modified:

- `generation/__init__.py` (populated from empty — imports the mosaic
  registration module for its self-registration side effect)

---

# Constraints (as instructed)

- Do not modify the UI.
- Do not rename existing files.
- Do not change generation behavior.

---

# Definition of Done

- `GenerationMode`, `SettingsPanel`, `GenerateCallable` exist as the
  approved contract.
- `registry.py` is mode-agnostic — no knowledge of mosaics or any other
  specific mode.
- The existing `generate_mosaic()` is registered as `GenerationMode(id="flat_mosaic", ...)`
  without any change to `mosaic_generator.py`.
- A registry-mediated call (`get_mode → create_settings_panel → get_settings → generate`)
  produces output identical to calling `generate_mosaic()` directly.
- `ImagePreviewWidget`, `MainWindow`, and every other UI file are
  byte-for-byte untouched.
- Live application behavior is unchanged.

---

# Completion Notes

## Architecture, as approved in A001 (with your three revisions)

- **Contract**: `GenerationMode` — a frozen dataclass (`id`,
  `display_name`, `description`, `version`, `create_settings_panel`,
  `generate`) wrapping a plain function, not a class hierarchy. No
  abstract base class was introduced, matching how every other "pure
  transform" in this codebase (`analyze()`, `load_ldraw_colors()`,
  `generate_mosaic()` itself) is already shaped.
- **Settings ownership**: per your revision, the registry does *not*
  auto-generate settings UI from dataclass fields. Each mode provides
  `create_settings_panel() -> SettingsPanel`, where `SettingsPanel` is a
  `Protocol` exposing only `.widget` (a `QWidget` to embed) and
  `.get_settings()` (the mode's own settings object). The shared UI —
  once a future package wires it up — will never see a field name,
  checkbox, or dropdown belonging to a specific mode.
- **Naming**: `GenerationMode`, not `GenerationModeInfo`, per your
  revision.
- **Versioning**: `version: int` is informational metadata on the
  record, not part of the registry key — `id` alone stays the unique
  lookup key. A future "v2" of an algorithm offered alongside the
  original would register under a new `id` (e.g. `"flat_mosaic_v2"`)
  with its own `version=2`, rather than the registry supporting multiple
  versions per id. Flagged in the A001 discussion as my reading of "add
  versioning" pending confirmation if true multi-version-per-id was
  intended instead.
- **Registration mechanism**: explicit self-registration, not directory
  scanning. `flat_mosaic_registration.py` calls `register_mode(...)` at
  module scope; `generation/__init__.py` is the one place that imports
  known mode modules, triggering that side effect. `registry.py` itself
  never imports anything mosaic-specific — confirmed via `ast`
  inspection, not assumed.

## Why `FlatMosaicSettingsPanel` Is a Real Implementation, Not a Stub

Registering `GenerationMode` with a placeholder `create_settings_panel`
would not be a genuine registration of the contract just approved — the
field isn't optional in spirit. `FlatMosaicSettingsPanel` faithfully
reproduces `ImagePreviewWidget`'s existing three controls (part dropdown
sourced from `PartCatalog.from_seed()`, transparency checkbox, origin
dropdown) as a new, standalone, independently constructible unit. It is
a new file — it does not modify `ImagePreviewWidget`, and nothing in the
running application calls it yet. This satisfies "do not modify the UI"
literally while giving Step 2 (wiring the shared UI to the registry) a
proven, working panel to swap in rather than a stub that would need to
be built from scratch later.

## Verification Performed

- `py_compile` clean on all four touched/new files.
- **Registration**: exactly one mode registered after importing
  `brickforge.generation`; `id`, `display_name`, `version` all correct.
  `get_mode()` returns it by id, `None` for an unknown id. Duplicate-id
  registration confirmed to raise `ValueError` rather than silently
  overwrite.
- **Settings panel**: `create_settings_panel()` produces a real `QWidget`;
  default `get_settings()` output matches `ImagePreviewWidget`'s existing
  hardcoded defaults exactly (`"3005"`, `skip_transparent_pixels=True`,
  `OriginMode.CENTERED`); changing the panel's controls (part, checkbox,
  origin) confirmed to correctly change the next `get_settings()` call's
  output.
- **Behavioral equivalence, the critical check**: built a scene both by
  calling `generate_mosaic()` directly and by going through the full
  registry path (`get_mode → create_settings_panel → get_settings →
  generate`) against the identical synthetic test image — confirmed
  field-identical `Scene`s (id, part_name, color_code, position,
  rotation compared for every brick). The registry wrapper changes
  nothing about generation behavior.
- **Mode-agnosticism**: `ast`-parsed `registry.py` and
  `generation_mode.py` — confirmed no import of `brickforge.ui` and no
  mosaic-specific import in either file.
- **Untouched files, confirmed by empty diff output, not assumed**:
  `git diff --stat` on `generation/mosaic_generator.py` and everything
  under `ui/` both produced zero output — byte-for-byte untouched.
- **Regression testing**: re-ran Package_003/007/008/011/012/013 checks
  — all still pass, including a direct (non-registry) call to
  `generate_mosaic()` confirming it's completely unaffected.
- **Live application verification**: `src/main.py` launches identically
  to Package_015 — same grid, same three missing-part warnings, no
  crash, no traceback. Expected and confirmed: the registry now exists
  in the codebase, but nothing in the running application calls into it
  yet, so there is no behavior change to observe.
- `git status` confirms exactly the planned scope: three new files, one
  file changed from empty to populated.

## Recommendations for Future Packages

- **Step 2** (per the A001 roadmap): wire `ImagePreviewWidget`/
  `MainWindow` to consume the registry generically — a mode-selection
  dropdown populated from `list_modes()`, embedding whichever mode's
  `create_settings_panel().widget` is current, and a mode-agnostic
  generation handler. This is the milestone where
  `ImagePreviewWidget`'s hardcoded "Generate LEGO Mosaic" button and
  three controls get replaced by `FlatMosaicSettingsPanel` (already
  built and verified in this package) via the registry, rather than
  inline code.
- **Terminology**: per A001, `GenerationSettings` → `FlatMosaicSettings`
  and `generation/mosaic_generator.py` → a `generation/modes/` subpackage
  remain recommended once a second mode exists to validate the
  restructuring is actually needed — deliberately not done here.
- **Optimization registry**: A001 recommended mirroring this exact
  pattern (contract + mode-agnostic registry + explicit self-registration)
  for the optimization stage once it exists, rather than inventing a
  different shape for it.
- All prior packages' outstanding recommendations remain outstanding and
  unaffected by this package.
