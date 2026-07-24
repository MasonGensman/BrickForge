# Changelog

All notable changes to StudWorks are documented in this file. Format
loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [v0.2.0-preview.1] — 2026-07-24

The first public Preview Release. Concludes the initial development
roadmap (Backend Foundation → Application Integration → Release
Preparation).

### Added

- A complete, deterministic image → LEGO model generation pipeline
  (`generate_model()`): image analysis, catalog-aware candidate
  selection, generation, optimization, validation, and repair,
  coordinated behind one canonical entry point.
- A full application shell around that pipeline: project
  create/open/save/save-as, image import, two independent generation
  paths (a legacy manual-mode path with Flat Mosaic and Height Relief,
  and the new deterministic pipeline), a 3D viewport with brick
  selection and Move/Rotate/Delete/Duplicate editing tools, a
  Properties panel, and export to BrickLink-Studio-compatible `.ldr`
  files.
- Data-integrity protections: unsaved-changes confirmation on New,
  Open, and window close; an accurate window title reflecting the
  current project's name and save state.
- Keyboard shortcuts for every core File/Edit action.
- A Windows Preview executable (`StudWorks.exe`, PyInstaller onefile
  build) with no installation required.

### Known Limitations

See `docs/RELEASE_NOTES.md` for the full list. The most significant:
the Preview build does not bundle a real LDraw parts library (to keep
the download small), so the 3D viewport shows no visible brick
geometry unless a real LDraw library is separately installed. Project
data, save/load, and export are entirely unaffected by this.

### Known Issues Deferred Past This Release

- No automated CI (regression suite is currently run manually before
  every commit).
- `src/brickforge/__main__.py` (an alternate `python -m brickforge`
  entry point) is broken; the packaged executable is unaffected, since
  it uses `src/main.py` directly.
- Delete-key support in the 3D viewport (Delete is currently
  Middle-click only).
- No confirmation-free Undo/Redo (the toolbar buttons are present but
  intentionally disabled — no undo/redo history exists yet).

---

Earlier development (Packages 001–049) is documented in this
repository's `Package_XXX.md` files and `docs/HANDOFF.md`; this
changelog begins at the first tagged release rather than reconstructing
that history entry-by-entry.
