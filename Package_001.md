# StudWorks

# Package 001

## Title

Renderer Stabilization

---

# Mission

Create a stable, modern rendering subsystem that becomes the foundation for all future StudWorks development.

This package establishes the first engineering baseline.

---

# Scope

Primary review target:

src/brickforge/render/

Including:

- renderer.py
- shader.py
- shader loading
- OpenGL initialization
- render loop
- renderer utilities

Modify additional files only when required.

Document every additional modification.

---

# Goals

- Preserve existing functionality.
- Improve renderer stability.
- Improve maintainability.
- Improve readability.
- Reduce technical debt.
- Remove obsolete or duplicate renderer code.

---

# Out of Scope

- AI model generation
- Brick optimization
- Image import pipeline
- Studio export
- Scene graph redesign
- UI redesign
- New user-facing features

---

# Definition of Done

The renderer:

- launches successfully
- initializes OpenGL correctly
- compiles shaders successfully
- renders without crashes
- resizes correctly
- preserves existing behavior
- builds successfully

---

# Deliverables

Return:

- Updated project
- Complete replacement files
- Summary of every modified file
- Reason for every modification
- Remaining known issues
- Recommendations for Package_002

---

# Final Review

Before completion:

- Verify project builds.
- Perform one self-review.
- Simplify where appropriate.
- Confirm Package_001 Definition of Done.

Only then consider Package_001 complete.

---

# Completion Notes

## Modified Files

- `src/brickforge/render/camera.py` — Restored `Camera.pan()` / `pan_speed`, which had
  been deleted while `viewport_widget.py` still called `camera.pan(...)` on middle-mouse
  drag, crashing with `AttributeError`.
- `src/brickforge/render/shader.py` — Removed leftover debug scaffolding (full shader
  source dumps, per-uniform lookup prints). Kept `set_color()` / `glUniform3f`, the
  intentional addition backing per-draw-call color (grid vs. test brick).
- `src/brickforge/render/renderer.py` — Removed leftover `print()` debug lines. Wrapped
  LDraw test-part loading in `try/except OSError` with a `logging.warning` fallback, so
  a missing parts library degrades to grid-only rendering instead of crashing renderer
  initialization.
- `src/brickforge/render/shaders/grid.frag` — Was physically relocated to
  `render/grid.frag` while `renderer.py` still loaded it from `render/shaders/`,
  breaking shader compilation outright. Moved back to the correct path. Its uniform
  color content change (hardcoded gray → `uniform vec3 u_color`) is intentional and
  pairs with `Shader.set_color()`.

## Known Issue — External Dependency, Not a Code Defect

`src/brickforge/ldraw/ldraw/parts/` is intentionally incomplete in this repository —
the full LDraw parts library (including `3001.dat`, used as the renderer's test brick)
is not checked in there. This is a missing external data asset, not a rendering bug.

The renderer now handles this correctly: `Renderer.initialize()` catches the resulting
`OSError`, logs a warning, and continues rendering the grid only. The application
launches, runs, and resizes normally with the parts library absent.

**Prerequisite for future visual QA / Milestone 3.1 verification:** the LDraw parts
library must be populated at `src/brickforge/ldraw/ldraw/parts/` before the test-brick
rendering path can be visually verified. A duplicate, fully-populated library already
exists in this repository at `ldraw/part/` (repo root, singular naming) — see the
Package_002 recommendation below.

## Recommendations for Package_002

- **Consolidate the LDraw library.** The repo currently carries two overlapping trees:
  `ldraw/part/` + `ldraw/p/` at the repo root (33,500 + 2,827 files, fully tracked) and
  `src/brickforge/ldraw/ldraw/p/` (2,827 files, duplicate of the root primitives) with
  an empty `src/brickforge/ldraw/ldraw/parts/`. Naming is inconsistent (`part` vs.
  `parts`). A future package should pick one canonical location/naming convention and
  migrate via `git mv` to preserve history, rather than maintaining duplicate
  multi-thousand-file trees. This is a repository-structure change, out of scope for
  renderer stabilization.
- **Subfile resolution.** `LDrawParser` currently skips type-`1` subfile references
  ("handled in the next Build Kit"). Most real parts (studs, connectors) are built from
  subfile refs, so parsed geometry will be incomplete even once `parts/` is populated.
- **Shader path validation.** Consider a build/CI check that fails if any
  `render/shaders/*.frag|.vert` file referenced by `renderer.py` doesn't exist at the
  expected path, so a mismatch like the one fixed here is caught automatically.