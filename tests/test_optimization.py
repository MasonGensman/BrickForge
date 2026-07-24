"""
StudWorks Optimization Pipeline Tests (Package_039)

The optimization architecture itself predates this package (Packages
020-022: optimizer.py/pipeline.py/registry.py/brick_merge_optimizer.py/
hidden_brick_removal_optimizer.py) and had zero dedicated test coverage
before now -- this file is the first. Package_039 widened the
OptimizeCallable contract with an optional GenerationConstraints
parameter and routed brick_merge_optimizer.py's replacement-part
discovery through generation.candidates.candidates_for() instead of a
direct PartCatalog scan; these tests focus on proving that change is
both genuinely effective (constraints change outcomes where a new part
is selected) and fully backward compatible (constraints=None behaves
exactly as before -- also verified independently by the existing
tests/test_export_golden_files.py::build_merged_column_scene golden
file, unmodified by this package).
"""

import unittest

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.generation.candidates import GenerationConstraints
from brickforge.generation.generation_engine import generate_scene
from brickforge.optimization.brick_merge_optimizer import (
    _find_merge_target,
    optimize_brick_merge,
)
from brickforge.optimization.hidden_brick_removal_optimizer import (
    optimize_hidden_brick_removal,
)
from brickforge.optimization.pipeline import optimize_scene
from brickforge.palette.palette_engine import PaletteEngine
from brickforge.preparation.generation_input import GenerationInput
from brickforge.serialization.deserializer import document_to_scene
from brickforge.serialization.serializer import scene_to_document
from brickforge.export.exporter import export_scene
from brickforge.services.part_catalog import PartCatalog

_STUD_LDU = 20.0


def _seed_catalog() -> PartCatalog:
    return PartCatalog.from_seed()


def _brick(id_, part_name, x, y, z, color=4, rotation=None) -> SceneBrick:

    return SceneBrick(
        id=id_,
        part_name=part_name,
        position=glm.vec3(x, y, z),
        rotation=rotation if rotation is not None else glm.quat(),
        color_code=color,
    )


def _two_adjacent_1x1_scene() -> Scene:
    """Two Z-adjacent 3005.dat (Brick 1x1) bricks -- the natural merge
    target, per the seed catalog, is 3004.dat (Brick 1x2)."""

    scene = Scene()
    scene.add_brick(_brick(0, "3005.dat", 0.0, 0.0, 0.0))
    scene.add_brick(_brick(1, "3005.dat", 0.0, 0.0, _STUD_LDU))

    return scene


def _fully_surrounded_scene() -> Scene:
    """A center 3005.dat brick with all six neighbor positions filled
    by the same part and rotation -- must be removed by hidden-brick
    removal regardless of constraints."""

    spacing_x = 1 * _STUD_LDU
    spacing_z = 1 * _STUD_LDU
    spacing_y = 24.0

    positions = [
        (0.0, 0.0, 0.0),
        (spacing_x, 0.0, 0.0),
        (-spacing_x, 0.0, 0.0),
        (0.0, spacing_y, 0.0),
        (0.0, -spacing_y, 0.0),
        (0.0, 0.0, spacing_z),
        (0.0, 0.0, -spacing_z),
    ]

    scene = Scene()

    for i, (x, y, z) in enumerate(positions):
        scene.add_brick(_brick(i, "3005.dat", x, y, z))

    return scene


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


class FindMergeTargetTests(unittest.TestCase):

    def test_unconstrained_finds_the_natural_target(self):

        catalog = _seed_catalog()
        source = catalog.get("3005")

        target = _find_merge_target(source, catalog, None)

        self.assertEqual(target.part_number, "3004")

    def test_excluding_the_natural_target_yields_none(self):

        catalog = _seed_catalog()
        source = catalog.get("3005")

        target = _find_merge_target(
            source, catalog,
            GenerationConstraints(excluded_part_numbers=["3004"]),
        )

        self.assertIsNone(target)

    def test_deterministic(self):

        catalog = _seed_catalog()
        source = catalog.get("3005")

        first = _find_merge_target(source, catalog, None)
        second = _find_merge_target(source, catalog, None)

        self.assertEqual(first.part_number, second.part_number)


class OptimizeBrickMergeTests(unittest.TestCase):

    def test_unconstrained_merges_as_before(self):

        catalog = _seed_catalog()
        scene = _two_adjacent_1x1_scene()

        optimized = optimize_brick_merge(scene, catalog)

        self.assertEqual(len(list(optimized)), 1)
        self.assertEqual(next(iter(optimized)).part_name, "3004.dat")

    def test_constraints_prevent_the_merge(self):
        """The one behavior this package makes newly possible:
        excluding the natural merge target via GenerationConstraints
        genuinely changes the outcome."""

        catalog = _seed_catalog()
        scene = _two_adjacent_1x1_scene()

        optimized = optimize_brick_merge(
            scene, catalog,
            GenerationConstraints(excluded_part_numbers=["3004"]),
        )

        self.assertEqual(len(list(optimized)), 2)

    def test_does_not_mutate_input_scene_catalog_or_constraints(self):

        catalog = _seed_catalog()
        scene = _two_adjacent_1x1_scene()
        before = _scene_signature(scene)
        catalog_before = [d.part_number for d in catalog.all()]
        constraints = GenerationConstraints(excluded_part_numbers=["3004"])

        optimize_brick_merge(scene, catalog, constraints)

        self.assertEqual(_scene_signature(scene), before)
        self.assertEqual(
            [d.part_number for d in catalog.all()], catalog_before,
        )
        self.assertEqual(constraints.excluded_part_numbers, ["3004"])

    def test_deterministic(self):

        catalog = _seed_catalog()

        first = optimize_brick_merge(_two_adjacent_1x1_scene(), catalog)
        second = optimize_brick_merge(_two_adjacent_1x1_scene(), catalog)

        self.assertEqual(
            _scene_signature(first), _scene_signature(second),
        )


class OptimizeHiddenBrickRemovalTests(unittest.TestCase):

    def test_removes_the_fully_surrounded_brick(self):

        catalog = _seed_catalog()
        scene = _fully_surrounded_scene()

        optimized = optimize_hidden_brick_removal(scene, catalog)

        self.assertEqual(len(list(optimized)), 6)

    def test_behavior_is_identical_regardless_of_constraints(self):
        """This optimizer never selects a new part -- constraints must
        never change its outcome."""

        catalog = _seed_catalog()

        unconstrained = optimize_hidden_brick_removal(
            _fully_surrounded_scene(), catalog, None,
        )
        constrained = optimize_hidden_brick_removal(
            _fully_surrounded_scene(), catalog,
            GenerationConstraints(excluded_part_numbers=["3005"]),
        )

        self.assertEqual(
            _scene_signature(unconstrained), _scene_signature(constrained),
        )

    def test_does_not_mutate_input(self):

        catalog = _seed_catalog()
        scene = _fully_surrounded_scene()
        before = _scene_signature(scene)

        optimize_hidden_brick_removal(scene, catalog)

        self.assertEqual(_scene_signature(scene), before)


class OptimizeScenePipelineTests(unittest.TestCase):

    def test_unconstrained_matches_previous_behavior(self):
        """Direct check mirroring test_export_golden_files.py's own
        merged_column golden file, at the unit level."""

        catalog = _seed_catalog()
        scene = _two_adjacent_1x1_scene()

        optimized = optimize_scene(scene, catalog)

        self.assertEqual(len(list(optimized)), 1)

    def test_constraints_thread_through_every_optimizer(self):

        catalog = _seed_catalog()
        scene = _two_adjacent_1x1_scene()

        optimized = optimize_scene(
            scene, catalog,
            GenerationConstraints(excluded_part_numbers=["3004"]),
        )

        self.assertEqual(len(list(optimized)), 2)

    def test_deterministic(self):

        catalog = _seed_catalog()

        first = optimize_scene(_two_adjacent_1x1_scene(), catalog)
        second = optimize_scene(_two_adjacent_1x1_scene(), catalog)

        self.assertEqual(
            _scene_signature(first), _scene_signature(second),
        )


_FIXTURE_LDCONFIG = """\
0 // LDraw Solid Colours
0 !COLOUR Black CODE 0 VALUE #05131D EDGE #595959
0 !COLOUR Blue CODE 1 VALUE #0055BF EDGE #05131D
0 !COLOUR Green CODE 2 VALUE #237841 EDGE #072C11
0 !COLOUR Red CODE 4 VALUE #C91A09 EDGE #591409
0 !COLOUR White CODE 15 VALUE #FFFFFF EDGE #999999
"""


class EndToEndGenerateThenOptimizeTests(unittest.TestCase):
    """generate_scene() (Package_038) -> optimize_scene() (this
    package): proves the full pipeline this package's mission diagram
    describes actually composes, end to end."""

    def _build_generation_input(self, tmp_path):

        from PySide6.QtGui import QColor, QImage
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication([])

        image = QImage(6, 6, QImage.Format_RGBA8888)
        image.fill(QColor(0, 0, 0, 0))

        for y in range(1, 5):
            for x in range(1, 5):
                image.setPixelColor(x, y, QColor(200, 10, 10, 255))

        image_path = tmp_path / "source.png"
        image.save(str(image_path))

        return GenerationInput.from_source(image_path)

    def test_generated_scene_can_be_optimized_and_stays_valid(self):

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:

            tmp_path = Path(tmp_dir)
            generation_input = self._build_generation_input(tmp_path)

            catalog = _seed_catalog()
            (tmp_path / "LDConfig.ldr").write_text(
                _FIXTURE_LDCONFIG, encoding="utf-8",
            )
            palette = PaletteEngine(tmp_path / "LDConfig.ldr")

            generated = generate_scene(generation_input, catalog, palette)
            optimized = optimize_scene(generated, catalog)

            self.assertLessEqual(
                len(list(optimized)), len(list(generated)),
            )
            self.assertGreater(len(list(optimized)), 0)

            # Serializes without modification.
            document = scene_to_document(optimized)
            reloaded = document_to_scene(document)
            self.assertEqual(
                _scene_signature(optimized), _scene_signature(reloaded),
            )

            # Exports without modification.
            out_path = tmp_path / "optimized.ldr"
            export_scene(optimized, catalog, out_path)
            self.assertTrue(out_path.is_file())
            self.assertGreater(out_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
