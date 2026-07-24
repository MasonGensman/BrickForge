"""
StudWorks Scene Analysis Tests (Package_041)

Uses hand-built Scene fixtures for correctness tests (no dependency on
the real installed LDraw library), plus one end-to-end test running
analyze_scene() against real generate_scene() output.
"""

import dataclasses
import tempfile
import unittest
from pathlib import Path

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.generation.generation_engine import generate_scene
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.scene_analysis.scene_analysis import (
    SceneAnalysisResult,
    SceneMeasurements,
    SceneSummaries,
    analyze_scene,
)
from brickforge.services.part_catalog import PartCatalog

_STUD_LDU = 20.0


def _seed_catalog() -> PartCatalog:
    return PartCatalog.from_seed()


def _brick(id_, part_name="3005.dat", x=0.0, y=0.0, z=0.0, color=4, rotation=None) -> SceneBrick:

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


class EmptySceneTests(unittest.TestCase):

    def test_empty_scene_yields_all_zero_measurements(self):

        catalog = _seed_catalog()
        result = analyze_scene(Scene(), catalog)

        self.assertEqual(result.measurements.brick_count, 0)
        self.assertEqual(result.measurements.unique_part_count, 0)
        self.assertEqual(result.measurements.color_count, 0)
        self.assertEqual(result.measurements.layer_count, 0)
        self.assertIsNone(result.measurements.bounds)
        self.assertEqual(result.summaries.part_distribution, ())
        self.assertEqual(result.summaries.layer_distribution, ())


class BrickAndPartCountTests(unittest.TestCase):

    def test_brick_count(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=20.0), _brick(2, x=40.0))

        result = analyze_scene(scene, catalog)

        self.assertEqual(result.measurements.brick_count, 3)

    def test_unique_part_count_and_distribution(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="3005.dat"),
            _brick(1, part_name="3005.dat", x=20.0),
            _brick(2, part_name="3004.dat", x=40.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertEqual(result.measurements.unique_part_count, 2)
        self.assertEqual(
            result.summaries.part_distribution,
            (("3004.dat", 1), ("3005.dat", 2)),
        )


class ColorCountTests(unittest.TestCase):

    def test_distinct_colors_are_counted(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, color=4), _brick(1, color=1, x=20.0),
            _brick(2, color=4, x=40.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertEqual(result.measurements.color_count, 2)

    def test_none_color_counts_as_its_own_value(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, color=4), _brick(1, color=None, x=20.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertEqual(result.measurements.color_count, 2)


class LayerTests(unittest.TestCase):

    def test_layer_count_and_distribution(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, y=0.0), _brick(1, y=0.0, x=20.0),
            _brick(2, y=24.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertEqual(result.measurements.layer_count, 2)
        self.assertEqual(
            result.summaries.layer_distribution,
            ((0.0, 2), (24.0, 1)),
        )

    def test_layer_distribution_ordering_is_not_insertion_order(self):
        """Bricks are added highest-layer-first -- if ordering were
        incidental (insertion order) rather than explicit (sorted by
        Y), this would come back in the wrong order."""

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, y=48.0), _brick(1, y=0.0, x=20.0),
            _brick(2, y=24.0, x=40.0),
        )

        result = analyze_scene(scene, catalog)

        ys = [y for y, _count in result.summaries.layer_distribution]
        self.assertEqual(ys, [0.0, 24.0, 48.0])


class BoundsTests(unittest.TestCase):

    def test_bounds_for_a_single_brick(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0, part_name="3005.dat"))

        result = analyze_scene(scene, catalog)

        min_bound, max_bound = result.measurements.bounds
        self.assertAlmostEqual(min_bound.x, -10.0)
        self.assertAlmostEqual(max_bound.x, 10.0)
        self.assertAlmostEqual(min_bound.y, 0.0)
        self.assertAlmostEqual(max_bound.y, 24.0)

    def test_unresolvable_part_is_excluded_from_bounds(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="nonexistent.dat", x=1000.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertIsNone(result.measurements.bounds)

    def test_bounds_is_none_when_every_part_is_unresolvable(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="nonexistent.dat"),
            _brick(1, part_name="also_missing.dat", x=20.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertIsNone(result.measurements.bounds)

    def test_rotation_is_accounted_for_in_bounds(self):
        """A 1x4 brick (3010.dat) rotated 90 degrees around Y swaps its
        long axis from Z onto X -- verified directly (both orientations)
        before writing this test, matching Package_040's own technique
        for the same underlying geometry question."""

        catalog = _seed_catalog()
        rotation = glm.angleAxis(glm.radians(90.0), glm.vec3(0, 1, 0))

        unrotated = _scene_of(
            SceneBrick(
                id=0, part_name="3010.dat",
                position=glm.vec3(0.0, 0.0, 0.0),
                rotation=glm.quat(), color_code=4,
            )
        )
        rotated = _scene_of(
            SceneBrick(
                id=0, part_name="3010.dat",
                position=glm.vec3(0.0, 0.0, 0.0),
                rotation=rotation, color_code=4,
            )
        )

        unrotated_bounds = analyze_scene(unrotated, catalog).measurements.bounds
        rotated_bounds = analyze_scene(rotated, catalog).measurements.bounds

        # Unrotated: long axis (stud_length=4) is along Z.
        self.assertAlmostEqual(unrotated_bounds[1].z, 40.0)
        self.assertAlmostEqual(unrotated_bounds[1].x, 10.0)

        # Rotated 90 degrees: long axis swings onto X instead.
        self.assertAlmostEqual(rotated_bounds[1].x, 40.0)
        self.assertAlmostEqual(rotated_bounds[1].z, 10.0)

    def test_bounds_encloses_multiple_bricks(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, x=-100.0), _brick(1, x=100.0),
        )

        result = analyze_scene(scene, catalog)

        min_bound, max_bound = result.measurements.bounds
        self.assertAlmostEqual(min_bound.x, -110.0)
        self.assertAlmostEqual(max_bound.x, 110.0)


class MeasurementSummaryConsistencyTests(unittest.TestCase):

    def test_unique_part_count_matches_distribution_length(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="3005.dat"),
            _brick(1, part_name="3004.dat", x=20.0),
            _brick(2, part_name="3005.dat", x=40.0),
        )

        result = analyze_scene(scene, catalog)

        self.assertEqual(
            result.measurements.unique_part_count,
            len(result.summaries.part_distribution),
        )

    def test_part_distribution_counts_sum_to_brick_count(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, part_name="3005.dat"),
            _brick(1, part_name="3004.dat", x=20.0),
            _brick(2, part_name="3005.dat", x=40.0),
        )

        result = analyze_scene(scene, catalog)

        total = sum(
            count for _name, count in result.summaries.part_distribution
        )
        self.assertEqual(total, result.measurements.brick_count)

    def test_layer_count_matches_distribution_length(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0, y=0.0), _brick(1, y=24.0))

        result = analyze_scene(scene, catalog)

        self.assertEqual(
            result.measurements.layer_count,
            len(result.summaries.layer_distribution),
        )

    def test_layer_distribution_counts_sum_to_brick_count(self):

        catalog = _seed_catalog()
        scene = _scene_of(
            _brick(0, y=0.0), _brick(1, y=0.0, x=20.0), _brick(2, y=24.0),
        )

        result = analyze_scene(scene, catalog)

        total = sum(
            count for _y, count in result.summaries.layer_distribution
        )
        self.assertEqual(total, result.measurements.brick_count)


class ImmutabilityTests(unittest.TestCase):

    def test_scene_analysis_result_is_frozen(self):

        result = analyze_scene(_scene_of(_brick(0)), _seed_catalog())

        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.measurements = None

    def test_scene_measurements_is_frozen(self):

        measurements = SceneMeasurements(
            brick_count=1, unique_part_count=1, color_count=1,
            layer_count=1, bounds=None,
        )

        with self.assertRaises(dataclasses.FrozenInstanceError):
            measurements.brick_count = 2

    def test_scene_summaries_is_frozen(self):

        summaries = SceneSummaries(
            part_distribution=(), layer_distribution=(),
        )

        with self.assertRaises(dataclasses.FrozenInstanceError):
            summaries.part_distribution = (("x", 1),)


class DeterminismAndNoMutationTests(unittest.TestCase):

    def test_repeated_analysis_produces_identical_results(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=20.0, color=1))

        first = analyze_scene(scene, catalog)
        second = analyze_scene(scene, catalog)

        self.assertEqual(first, second)

    def test_does_not_mutate_scene_or_catalog(self):

        catalog = _seed_catalog()
        scene = _scene_of(_brick(0), _brick(1, x=20.0))

        bricks_before = list(scene)
        catalog_before = [d.part_number for d in catalog.all()]

        analyze_scene(scene, catalog)

        self.assertEqual(list(scene), bricks_before)
        self.assertEqual(
            [d.part_number for d in catalog.all()], catalog_before,
        )


_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
0 !COLOUR Blue CODE 1 VALUE #0055BF EDGE #05131D
"""


class RealGeneratedSceneEndToEndTests(unittest.TestCase):

    def test_generated_scene_analysis_matches_expectations(self):

        from PySide6.QtGui import QColor, QImage
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)

            image = QImage(6, 6, QImage.Format_RGBA8888)
            image.fill(QColor(0, 0, 0, 0))

            for y in range(1, 5):
                for x in range(1, 5):
                    if x < 3:
                        image.setPixelColor(x, y, QColor(200, 10, 10, 255))
                    else:
                        image.setPixelColor(x, y, QColor(10, 10, 200, 255))

            image_path = tmp_path / "source.png"
            image.save(str(image_path))

            generation_input = GenerationInput.from_source(image_path)
            catalog = _seed_catalog()

            (tmp_path / "LDConfig.ldr").write_text(
                _FIXTURE_LDCONFIG, encoding="utf-8",
            )
            palette = PaletteEngine(tmp_path / "LDConfig.ldr")

            scene = generate_scene(generation_input, catalog, palette)
            result = analyze_scene(scene, catalog)

            self.assertEqual(result.measurements.brick_count, 16)
            self.assertEqual(result.measurements.unique_part_count, 1)
            self.assertEqual(result.measurements.color_count, 2)
            self.assertEqual(result.measurements.layer_count, 1)
            self.assertIsNotNone(result.measurements.bounds)

            total = sum(
                count for _n, count in result.summaries.part_distribution
            )
            self.assertEqual(total, result.measurements.brick_count)


if __name__ == "__main__":
    unittest.main()
