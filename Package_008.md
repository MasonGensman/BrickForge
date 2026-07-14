# StudWorks

# Package 008

## Title

Catalog-to-Scene Bridge

---

# Mission

Bridge the catalog layer (Package_007) with the runtime scene layer: give
`BrickDefinition` exactly one authoritative path to become a renderable
`SceneBrick`, and eliminate the duplicated `.dat` filename literals that
existed only because no such path existed before.

---

# Scope

- `src/brickforge/engine/scene_brick.py`
- `src/brickforge/render/renderer.py`
- `src/brickforge/models/part_definition.py` (already carries the
  `part_name` property added in the prior turn; unchanged in this package's
  implementation beyond that)

---

# Architecture Decision

**`SceneBrick.from_definition(...)`** (Option B), not
`BrickDefinition.create_scene_brick(...)` (Option A). `engine/` already
depends on `glm`; adding one downward edge to `models/` matches the
existing pattern of `engine/` reaching into lower layers to construct
itself (`BrickManager` already reaches into `ldraw/` the same way).
`models/part_definition.py` gains zero new imports and stays a leaf —
verified directly (see Verification) rather than assumed.

---

# Definition of Done

- `SceneBrick.from_definition(...)` is the one authoritative
  `BrickDefinition → SceneBrick` conversion point.
- `renderer.py` no longer manually constructs `SceneBrick` — all three
  seeded bricks go through `SceneBrick.from_definition()`.
- No `.dat` filename literal remains in `renderer.py`.
- No rendering behavior changed: same ids, same positions, same rotation,
  same draw calls, same shader/GL state.
- `BrickDefinition`/`models/part_definition.py` remains independent of
  `engine/`, `render/`, and `glm`.
- Live application behavior identical to Package_007.

---

# Completion Notes

## Exact Implementation

**`engine/scene_brick.py`** — added `from_definition`:

```python
@classmethod
def from_definition(
    cls,
    definition: BrickDefinition,
    *,
    id: int,
    position: glm.vec3 | None = None,
    rotation: glm.quat | None = None,
) -> "SceneBrick":

    kwargs = {}

    if position is not None:
        kwargs["position"] = position

    if rotation is not None:
        kwargs["rotation"] = rotation

    return cls(
        id=id,
        part_name=definition.part_name,
        **kwargs,
    )
```

`position`/`rotation` default to `None` and are omitted from the
constructor call entirely when unset, rather than restating
`glm.vec3(0,0,0)`/`glm.quat()` — `SceneBrick`'s own `field(default_factory=...)`
defaults fire naturally. There is exactly one place that knows what "no
position specified" means: the dataclass field itself.

**`render/renderer.py`** — `initialize()` now constructs
`catalog = PartCatalog.from_seed()` and replaces all three
`SceneBrick(id=..., part_name="....dat", ...)` literals with
`SceneBrick.from_definition(catalog.get("...."), id=..., position=..., [rotation=...])`.
Ids, positions, and the one non-identity rotation are unchanged — only how
`part_name` is populated changed, from a hand-typed string to
`definition.part_name` (itself an alias for `ldraw_filename`).
`render()` — the actual draw loop, `u_model` composition, shader calls,
grid rendering, camera handling — was not touched at all.

## Verification Performed

- `py_compile` clean on all three touched files.
- **Filename mapping exists in exactly one location**: grepped
  `renderer.py` for `SceneBrick(` direct construction (0 matches outside
  `from_definition`) and for `.dat"` literals (0 matches) — confirmed
  renderer.py no longer manually constructs `SceneBrick` or duplicates
  filenames; exactly 3 `SceneBrick.from_definition(` calls found.
- **Unit**: `SceneBrick.from_definition(definition, id=1).part_name ==
  definition.part_name == definition.ldraw_filename` for all 10 real seed
  `BrickDefinition`s from `PartCatalog.from_seed()`.
- **Equivalence proof**: constructed each of the 3 seeded bricks the *old*
  hand-typed way (matching pre-Package_008 `renderer.py` exactly) and via
  the *new* `SceneBrick.from_definition(catalog.get(...), ...)` path —
  asserted dataclass equality for all 3; identical, including the
  45°-around-Y rotation on brick `id=2`.
- **Default-passthrough proof**: `SceneBrick.from_definition(definition,
  id=99)` with `position`/`rotation` omitted equals a bare
  `SceneBrick(id=99, part_name=...)` exactly — confirmed no duplicated
  default logic between the factory and the dataclass.
- **`BrickDefinition` independence check**: parsed
  `models/part_definition.py` with `ast` and enumerated its actual
  `import`/`from...import` statements directly (not a text search, which
  gave a false positive against the module's own docstring mentioning
  `engine`/`render` in prose) — confirmed the only import is `dataclasses`.
- **Regressions**: re-ran Package_003's `Scene` API checks, Package_005's
  `u_model` matrix checks, and Package_007's catalog/color checks — all
  still pass.
- **Live run of `src/main.py`**: identical to Package_007 — grid renders,
  the same three missing-part warnings for `3001.dat`/`3003.dat`/`3004.dat`
  (both searched paths shown), no crash, no traceback, app stays alive.
  The filenames in the warning output are now produced by
  `catalog.get(...).part_name`, not typed literals, and are byte-identical
  to before.
- `git diff --stat` confirms exactly the three planned files changed (45
  insertions, 6 deletions total) — no shader, camera, grid, `BrickManager`,
  `Scene`, or `ui/` file touched.

## Recommendations for Future Packages

- `renderer.py` now has its first real dependency on `services/`
  (`PartCatalog`) in addition to `engine/`. This is the expected shape for
  the eventual "Scene generation" step of the AI pipeline
  (Image → AI analysis → Brick selection → Scene generation → Studio
  export) — a future package would replace `PartCatalog.from_seed()` with
  a catalog populated from real analysis output, without touching
  `SceneBrick.from_definition()` at all.
- All prior recommendations (LDraw library consolidation, subfile
  resolution already done in Package_006, BrickLink ID mapping, per-brick
  color, `bounding_box` computation) remain outstanding and unaffected by
  this package.
