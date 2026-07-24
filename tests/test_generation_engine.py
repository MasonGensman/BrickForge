"""
StudWorks Generation Engine Tests (Package_038)

Uses a small, synthetic LDConfig.ldr fixture (a handful of !COLOUR
lines under a Solid Colours section) rather than depending on this
environment's real, installed LDraw library -- matching the
environment-independence discipline established for
tests/test_ldraw_catalog_builder.py's own synthetic fixture library.
Test images are written fresh via Qt (matching test_generation_input.py's
own established pattern), no committed binary fixtures.
"""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from brickforge.engine.scene import Scene
from brickforge.export.exporter import export_scene
from brickforge.generation.candidates import GenerationConstraints
from brickforge.generation.generation_engine import (
    _nearest_dominant_color,
    generate_scene,
    select_generation_brick,
)
from brickforge.models.part_definition import BrickDefinition
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.serialization.deserializer import document_to_scene
from brickforge.serialization.serializer import scene_to_document
from brickforge.services.part_catalog import PartCatalog

_app = QApplication.instance() or QApplication([])

_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Black CODE 0 VALUE #05131D EDGE #595959
0 !COLOUR Blue CODE 1 VALUE #0055BF EDGE #05131D
0 !COLOUR Green CODE 2 VALUE #237841 EDGE #072C11
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
0 !COLOUR White CODE 15 VALUE #FFFFFF EDGE #999999
"""


def _write_ldconfig(directory: Path) -> Path:

    path = directory / "LDConfig.ldr"
    path.write_text(_FIXTURE_LDCONFIG, encoding="utf-8")

    return path


def _write_test_image(
    directory: Path,
    width: int = 6,
    height: int = 6,
    fully_transparent: bool = False,
) -> Path:
    """A colored square (red-ish on the left half, blue-ish on the
    right half) surrounded by a transparent border, so occupied_bounds
    is a strict sub-region of the full canvas -- exercising the
    centering-on-content behavior directly."""

    image = QImage(width, height, QImage.Format_RGBA8888)
    image.fill(QColor(0, 0, 0, 0))

    if not fully_transparent:

        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if x < width // 2:
                    image.setPixelColor(x, y, QColor(200, 10, 10, 255))
                else:
                    image.setPixelColor(x, y, QColor(10, 10, 200, 255))

    path = directory / "source.png"
    image.save(str(path))

    return path


class _FixtureContext:
    """Bundles a temp dir's GenerationInput/catalog/palette so tests
    don't repeat the same setup boilerplate."""

    def __init__(self, tmp_dir: Path, fully_transparent: bool = False):

        image_path = _write_test_image(
            tmp_dir, fully_transparent=fully_transparent,
        )
        self.generation_input = GenerationInput.from_source(image_path)
        self.catalog = PartCatalog.from_seed()
        self.palette = PaletteEngine(_write_ldconfig(tmp_dir))


def _scene_signature(scene: Scene):

    return [
        (
            brick.id,
            brick.part_name,
            (brick.position.x, brick.position.y, brick.position.z),
            brick.color_code,
        )
        for brick in scene
    ]


def _make_definition(part_number, stud_width, stud_length) -> BrickDefinition:

    return BrickDefinition(
        part_number=part_number,
        name=f"Test Part {part_number}",
        category="Brick",
        ldraw_filename=f"{part_number}.dat",
        stud_width=stud_width,
        stud_length=stud_length,
        height_units=24.0,
    )


class SelectGenerationBrickTests(unittest.TestCase):

    def test_smallest_footprint_wins(self):

        candidates = [
            _make_definition("3001", 2, 4),
            _make_definition("3005", 1, 1),
            _make_definition("3003", 2, 2),
        ]

        self.assertEqual(
            select_generation_brick(candidates).part_number, "3005",
        )

    def test_tie_break_by_part_number(self):

        candidates = [
            _make_definition("9999", 1, 1),
            _make_definition("1111", 1, 1),
        ]

        self.assertEqual(
            select_generation_brick(candidates).part_number, "1111",
        )

    def test_empty_candidates_raises_value_error(self):

        with self.assertRaises(ValueError):
            select_generation_brick([])

    def test_deterministic(self):

        candidates = [
            _make_definition("3001", 2, 4),
            _make_definition("3005", 1, 1),
        ]

        first = select_generation_brick(candidates)
        second = select_generation_brick(candidates)

        self.assertEqual(first.part_number, second.part_number)


class NearestDominantColorTests(unittest.TestCase):

    def test_exact_match(self):

        result = _nearest_dominant_color(
            (200, 10, 10), [(200, 10, 10), (10, 10, 200)],
        )

        self.assertEqual(result, (200, 10, 10))

    def test_nearest_among_several(self):

        result = _nearest_dominant_color(
            (190, 15, 15), [(200, 10, 10), (10, 10, 200), (0, 0, 0)],
        )

        self.assertEqual(result, (200, 10, 10))

    def test_tie_break_prefers_first_in_list(self):

        result = _nearest_dominant_color(
            (100, 100, 100), [(0, 0, 0), (200, 200, 200)],
        )

        self.assertEqual(result, (0, 0, 0))

    def test_does_not_depend_on_brick_selection(self):
        """Independent helper -- must work with no candidates/selection
        context at all."""

        result = _nearest_dominant_color((5, 5, 5), [(5, 5, 5)])

        self.assertEqual(result, (5, 5, 5))


class GenerateSceneTests(unittest.TestCase):

    def test_identical_inputs_produce_identical_scene_signatures(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))

            first = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)
            second = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            self.assertEqual(
                _scene_signature(first), _scene_signature(second),
            )

    def test_produces_a_non_empty_scene_for_a_normal_image(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            self.assertGreater(len(list(scene)), 0)

    def test_fully_transparent_image_yields_an_empty_scene(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir), fully_transparent=True)
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            self.assertEqual(list(scene), [])

    def test_no_candidates_raises_value_error(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))

            all_part_numbers = [
                d.part_number for d in ctx.catalog.all()
            ]
            constraints = GenerationConstraints(
                excluded_part_numbers=all_part_numbers,
            )

            with self.assertRaises(ValueError):
                generate_scene(
                    ctx.generation_input, ctx.catalog, ctx.palette,
                    constraints,
                )

    def test_constraints_change_the_selected_part(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))

            unconstrained = generate_scene(
                ctx.generation_input, ctx.catalog, ctx.palette,
            )
            default_part_name = next(iter(unconstrained)).part_name

            excluded_number = default_part_name.replace(".dat", "")
            constrained = generate_scene(
                ctx.generation_input, ctx.catalog, ctx.palette,
                GenerationConstraints(
                    excluded_part_numbers=[excluded_number],
                ),
            )
            constrained_part_name = next(iter(constrained)).part_name

            self.assertNotEqual(default_part_name, constrained_part_name)

    def test_brick_ids_are_unique(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            ids = [brick.id for brick in scene]

            self.assertEqual(len(ids), len(set(ids)))

    def test_placement_is_centered_on_occupied_bounds(self):
        """The generated grid must be centered on the image's actual
        content, not the full (transparent-bordered) canvas."""

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            xs = [brick.position.x for brick in scene]

            self.assertAlmostEqual(min(xs), -max(xs), places=3)

    def test_does_not_mutate_generation_input(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))

            pixels_before = ctx.generation_input.prepared_image.pixels.copy()
            analysis_before = ctx.generation_input.analysis

            generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            self.assertTrue(
                np.array_equal(
                    ctx.generation_input.prepared_image.pixels,
                    pixels_before,
                )
            )
            self.assertIs(ctx.generation_input.analysis, analysis_before)

    def test_does_not_mutate_catalog_or_constraints(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))

            catalog_before = [d.part_number for d in ctx.catalog.all()]
            constraints = GenerationConstraints(permitted_colors=[4, 1])

            generate_scene(
                ctx.generation_input, ctx.catalog, ctx.palette, constraints,
            )

            self.assertEqual(
                [d.part_number for d in ctx.catalog.all()], catalog_before,
            )
            self.assertEqual(constraints.permitted_colors, [4, 1])

    def test_serializes_without_modification(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            document = scene_to_document(scene)
            reloaded = document_to_scene(document)

            self.assertEqual(
                _scene_signature(scene), _scene_signature(reloaded),
            )

    def test_exports_without_modification(self):

        with tempfile.TemporaryDirectory() as tmp_dir:

            ctx = _FixtureContext(Path(tmp_dir))
            scene = generate_scene(ctx.generation_input, ctx.catalog, ctx.palette)

            out_path = Path(tmp_dir) / "generated.ldr"
            export_scene(scene, ctx.catalog, out_path)

            self.assertTrue(out_path.is_file())
            self.assertGreater(out_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
