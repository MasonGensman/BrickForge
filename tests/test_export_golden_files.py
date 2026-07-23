"""
StudWorks Export Golden-File Regression Tests (Package_024 amendment)

Permanently detects unintended changes in exported LDraw output by
comparing four canonical Scenes' exported .ldr files, byte-for-byte,
against fixed reference files under tests/golden/.

Why golden files exist: the exporter (Package_024) is documented as
deterministic -- identical Scene input must always produce identical
output. A golden-file test is the most direct way to enforce that
promise permanently: if any future change to export/, generation/, or
optimization/ ever alters exported output for these fixed inputs, this
test fails immediately, rather than the drift going unnoticed until
someone manually inspects a .ldr file.

Why byte-for-byte, with no normalization: the whole point is to catch
*any* unintended difference -- formatting, floating-point precision,
line order, whitespace, newline convention. A comparison that
normalizes any of these away would silently accept the exact class of
regression this test exists to catch.

Golden-file update policy: these files are only ever regenerated when
an export-behavior change is INTENTIONAL. A failing test here is a
signal to investigate why output changed, not an instruction to
regenerate the golden file to make the test pass again. If, after
review, the change is confirmed intentional (e.g. a deliberate
Package_02X change to number formatting, header content, or brick
ordering), regenerate deliberately by running this file's
CANONICAL_SCENES builders through export_scene() again and reviewing
the diff before committing the updated golden file alongside the
change that caused it -- never as a silent, separate commit.

Canonical scenes:
- single_brick: the simplest possible case (one brick).
- merged_column: exercises optimizer-produced output (Brick Merge
  collapsing four 1x1 bricks into one 1x4).
- flat_mosaic_3x3: real (not hand-built) Flat Mosaic generation output.
- height_relief_3x3: real (not hand-built) Height Relief generation
  output, including multi-layer/3D stacking.

Uses PartCatalog.from_seed() (not load_best_available()) and the
bundled fallback LDConfig.ldr (not find_ldraw_library()'s resolved
result) deliberately -- both are fixed, version-controlled, and
identical on every machine, unlike whichever real LDraw library a
given environment happens to resolve. Golden-file tests must not
depend on what's installed locally.

No production code changes -- test-only.
"""

import tempfile
import unittest
from pathlib import Path

import glm
import numpy as np

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.export.exporter import export_scene
from brickforge.generation.height_relief_generator import (
    HeightReliefSettings,
    generate_height_relief,
)
from brickforge.generation.mosaic_generator import (
    GenerationSettings,
    generate_mosaic,
)
from brickforge.io.image_resource import ImageResource
from brickforge.optimization.pipeline import optimize_scene
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.resources import resource_path
from brickforge.services.part_catalog import PartCatalog

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

_STUD_LDU = 20.0


def _catalog() -> PartCatalog:
    """
    Always the seed catalog -- stable and identical on every machine,
    unlike load_best_available() which depends on whatever LDraw
    library happens to be installed/discoverable locally.
    """

    return PartCatalog.from_seed()


def _palette() -> PaletteEngine:
    """
    Always the bundled fallback LDConfig.ldr -- always present in the
    repo, unlike find_ldraw_library()'s resolved result.
    """

    ldconfig_path = resource_path("ldraw", "ldraw", "LDConfig.ldr")

    return PaletteEngine(ldconfig_path)


def _brick(
    id_,
    part_name,
    x,
    y,
    z,
    color=4,
    rotation=None,
):

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(x, y, z),
        rotation=rotation if rotation is not None else glm.quat(),
        color_code=color,
    )


def _scene_of(*bricks) -> Scene:

    scene = Scene()

    for brick in bricks:
        scene.add_brick(brick)

    return scene


def build_single_brick_scene() -> Scene:
    """The simplest possible case: one brick."""

    return _scene_of(
        _brick(1, "3005.dat", 0.0, 0.0, 0.0, color=4)
    )


def build_merged_column_scene() -> Scene:
    """
    Four Z-adjacent 1x1 bricks, run through the real optimization
    pipeline -- exercises optimizer-produced (not raw generation)
    output. Brick Merge collapses this to one 1x4 (3010.dat) at the
    column's midpoint.
    """

    catalog = _catalog()

    d3005 = catalog.get("3005")
    spacing_z = d3005.stud_length * _STUD_LDU

    raw = _scene_of(*[
        _brick(i, "3005.dat", 0.0, 0.0, i * spacing_z, color=4)
        for i in range(4)
    ])

    return optimize_scene(raw, catalog)


def build_flat_mosaic_3x3_scene() -> Scene:
    """Real (not hand-built) Flat Mosaic generation output."""

    catalog = _catalog()
    palette = _palette()

    pixels = np.zeros((3, 3, 4), dtype=np.uint8)
    pixels[:, :, 0] = 200
    pixels[:, :, 3] = 255

    image = ImageResource(
        path="golden_flat_mosaic_3x3.png",
        width=3,
        height=3,
        format="PNG",
        pixels=pixels,
        content_hash="0" * 64,
    )

    settings = GenerationSettings(default_part_number="3005")

    return generate_mosaic(image, palette, catalog, settings)


def build_height_relief_3x3_scene() -> Scene:
    """
    Real (not hand-built) Height Relief generation output, including
    multi-layer/3D stacking.
    """

    catalog = _catalog()
    palette = _palette()

    pixels = np.zeros((3, 3, 4), dtype=np.uint8)
    pixels[:, :, :3] = 255
    pixels[:, :, 3] = 255

    image = ImageResource(
        path="golden_height_relief_3x3.png",
        width=3,
        height=3,
        format="PNG",
        pixels=pixels,
        content_hash="1" * 64,
    )

    settings = HeightReliefSettings(
        default_part_number="3023",
        max_layers=3,
    )

    return generate_height_relief(image, palette, catalog, settings)


CANONICAL_SCENES = {
    "single_brick": build_single_brick_scene,
    "merged_column": build_merged_column_scene,
    "flat_mosaic_3x3": build_flat_mosaic_3x3_scene,
    "height_relief_3x3": build_height_relief_3x3_scene,
}


class GoldenFileExportTests(unittest.TestCase):
    """
    Byte-for-byte comparisons against tests/golden/*.ldr. No
    normalization anywhere -- see module docstring for why.
    """

    def test_golden_files_exist(self):

        for name in CANONICAL_SCENES:

            golden_path = GOLDEN_DIR / f"{name}.ldr"

            self.assertTrue(
                golden_path.is_file(),
                f"Missing golden file: {golden_path}",
            )

    def test_exported_output_matches_golden_files(self):

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                golden_path = GOLDEN_DIR / f"{name}.ldr"
                golden_bytes = golden_path.read_bytes()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    out_path = Path(tmp_dir) / f"{name}.ldr"

                    export_scene(
                        build_scene(),
                        _catalog(),
                        out_path,
                    )

                    actual_bytes = out_path.read_bytes()

                self.assertEqual(
                    actual_bytes,
                    golden_bytes,
                    f"Exported output for {name!r} no longer matches "
                    f"its golden file byte-for-byte. If this is an "
                    f"INTENTIONAL export-behavior change, regenerate "
                    f"the golden file deliberately and review the diff "
                    f"before committing (see this file's module "
                    f"docstring) -- do not update it just to make this "
                    f"test pass.",
                )

    def test_export_is_deterministic_on_repeat(self):
        """Same Scene, same path, exported twice -> byte-identical."""

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                catalog = _catalog()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    out_path = Path(tmp_dir) / f"{name}.ldr"

                    export_scene(build_scene(), catalog, out_path)
                    first = out_path.read_bytes()

                    export_scene(build_scene(), catalog, out_path)
                    second = out_path.read_bytes()

                self.assertEqual(first, second)

    def test_merged_column_scene_is_actually_optimized(self):
        """
        Sanity check that this golden file genuinely exercises
        optimizer output, not accidentally just raw input: four bricks
        in must become one brick out.
        """

        raw_count = 4
        optimized = build_merged_column_scene()

        self.assertEqual(len(list(optimized)), 1)
        self.assertLess(len(list(optimized)), raw_count)


if __name__ == "__main__":
    unittest.main()
