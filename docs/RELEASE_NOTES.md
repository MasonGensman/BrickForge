# StudWorks v0.2.0-preview.1 — Preview Release Notes

**Release date**: 2026-07-24
**Release type**: Windows Preview Build (not a stable release)

---

## What StudWorks Is

StudWorks turns an image into an editable LEGO model and exports it to
BrickLink Studio for refinement. It's a companion to Studio, not a
replacement — StudWorks' job ends at producing a structurally valid,
exportable model.

## What Works in This Preview

A first-time user can, start to finish:

1. **Create a project** — a fresh, empty project on launch, or via
   File > New (`Ctrl+N`).
2. **Import an image** — via the Image Preview panel's Import button.
3. **Generate a LEGO model** from it, via either of two independent
   paths:
   - **Standard Pipeline (Recommended)** — fully automatic: part
     selection, optimization, validation, and repair, end to end.
   - **Legacy Generation** — manual mode selection (Flat Mosaic or
     Height Relief), with manual part/settings control the Standard
     Pipeline doesn't offer yet.
4. **Inspect the generated bricks** — click any brick in the 3D
   viewport or browse the Brick Library; both populate a Properties
   panel with the part's details.
5. **Edit the model** — Move (left-drag), Rotate (right-drag), Delete
   (middle-click), Duplicate (Edit menu / `Ctrl+D`).
6. **Save the project** (`Ctrl+S` / `Ctrl+Shift+S` for Save As) and
   **reload it** later (`Ctrl+O`) — your work, including the source
   image reference, is preserved.
7. **Export the model** to a `.ldr` file (`Ctrl+E`) that BrickLink
   Studio can open directly.
8. **Exit safely** — closing StudWorks (the window's close button,
   `Ctrl+Q`, or File > Exit) will ask before discarding any unsaved
   changes.

## Known Limitations

These are intentional, documented limitations of this Preview — not
bugs. Each is a candidate for a future milestone, not this release.

| # | Limitation | User Impact | Severity | Future Milestone |
|---|---|---|---|---|
| 1 | **No LDraw parts library is bundled.** The 3D viewport shows no visible brick geometry unless a real LDraw library is separately installed (free, from ldraw.org) or `LDRAW_LIBRARY_PATH` is set. Project data, save/load, and export are completely unaffected — an exported `.ldr` file opens and renders correctly in BrickLink Studio regardless. | High for evaluators without LDraw already installed — the viewport itself will appear empty. | Medium-High | v0.3.0 — bundle a small curated parts subset, or surface an in-app notice when no real geometry is available. |
| 2 | **Most real catalog parts have placeholder dimensional metadata.** Only ~32% get a genuinely-derived stud footprint and ~23% a genuine category from the LDraw library itself; the rest default to a generic 1×1 placeholder. `available_colors`/`family` have no source in the LDraw format at all. | Low-Medium — generation and validation still work; some catalog browsing/filtering is less precise than it could be. | Medium | Future — needs an external data source (BrickLink/Rebrickable) not yet integrated. |
| 3 | **Two independent generation paths coexist by design.** The legacy manual-mode path (Flat Mosaic, Height Relief) and the new deterministic pipeline both work, but aren't unified — the new pipeline has no manual part override or 3D height-relief equivalent yet. | Low — both paths work; a user just needs to pick the one matching their need. | Low | v0.3.0+ — a deliberate future product decision, not yet made. |
| 4 | **No Undo/Redo.** The toolbar buttons exist (with `Ctrl+Z`/`Ctrl+Y` shortcuts) but are intentionally disabled — no undo history exists yet. | Medium — mistakes during editing require Delete + manual re-creation, not a single undo. | Medium | Future — deferred since the original editing-tools milestone. |
| 5 | **No Delete key in the viewport.** Deleting a brick requires middle-click; pressing Delete/Backspace does nothing. | Low | Low | Next Release Preparation cycle. |
| 6 | **`GenerationConstraints` has no settings UI.** The backend already reads and respects per-project generation constraints (permitted colors/categories/sizes), but nothing in the UI lets a user set them yet. | Low | Low | Future, if requested. |
| 7 | **Rendering issue**: LDraw geometry (when real geometry *is* available) renders upside-down relative to the intended orientation. | Low-Medium once limitation #1 is resolved for a given setup | Medium | Future — a known, unfixed rendering-layer bug. |
| 8 | **No stud/tube connectivity validation.** StudWorks can't detect whether bricks are actually physically connected, only whether they geometrically overlap. | Low | Low | Future — would need an external connectivity data source. |
| 9 | **No automated CI.** The 429-test regression suite is comprehensive but currently run manually, not on every push. | None (doesn't affect the shipped application) | Low | Deferred past this release by deliberate choice. |
| 10 | **`python -m brickforge` doesn't work from source** (an alternate entry point is currently broken). The packaged executable and `python src/main.py` are both unaffected. | None for Preview users (only affects running from source a specific way) | Low | Being tracked separately from the numbered release roadmap. |

## Feedback

This is an early Preview build, meant for evaluation. Please report
anything that crashes, behaves unexpectedly, or gets in your way.

## What's Next

With this Preview shipped, the initial StudWorks development roadmap
(Backend Foundation → Application Integration → Release Preparation →
Preview Release) is complete. Future development will proceed as
milestone-based releases (e.g., v0.3.0) rather than continuing the
original numbered-package sequence. See `docs/HANDOFF.md`'s Post-Release
Roadmap for candidates under consideration.
