"""
StudWorks Scene Serialization Golden-File Regression Tests (Package_025)

Mirrors Package_024's golden-file testing pattern exactly (see
tests/test_export_golden_files.py's own docstring for the full
rationale) -- byte-for-byte comparison, zero normalization, stdlib
unittest (no new test-framework dependency), golden files regenerated
only for intentional format changes, reviewed and committed alongside
the change that caused them, never simply because a test fails.

Canonical scenes are deliberately hand-built, not derived from real
generation: unlike Package_024's exporter (which specifically needed
proving against real LDraw data), Scene serialization has zero
dependency on PartCatalog/PaletteEngine, so hand-built Scenes exercise
the format itself -- shape variety, not generation provenance -- more
directly and keep these tests fast and fully self-contained.

- empty_scene: zero bricks -- the simplest possible case.
- single_brick: one brick, identity rotation.
- multi_brick_scene: several bricks, negative coordinates, a None
  color_code, non-sequential ids.
- rotated_brick: a genuinely non-identity rotation, exercising
  quaternion component serialization thoroughly.
"""

import tempfile
import unittest
from pathlib import Path

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.serialization.deserializer import deserialize_scene
from brickforge.serialization.schema import SceneSerializationError
from brickforge.serialization.serializer import serialize_scene

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "scenes"


def _brick(id_, part_name, x, y, z, rotation=None, color=4):

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


def build_empty_scene() -> Scene:

    return Scene()


def build_single_brick_scene() -> Scene:

    return _scene_of(
        _brick(1, "3005.dat", 0.0, 0.0, 0.0, color=4)
    )


def build_multi_brick_scene() -> Scene:

    return _scene_of(
        _brick(0, "3005.dat", -20.0, 0.0, 20.0, color=4),
        _brick(5, "3004.dat", 0.0, 24.0, -20.0, color=None),
        _brick(99, "3023.dat", 40.5, -8.25, 0.0, color=15),
    )


def build_rotated_brick_scene() -> Scene:

    rotation = glm.angleAxis(
        glm.radians(90.0),
        glm.vec3(0.0, 1.0, 0.0),
    )

    return _scene_of(
        _brick(1, "3004.dat", 0.0, 0.0, 0.0, rotation=rotation, color=1)
    )


CANONICAL_SCENES = {
    "empty_scene": build_empty_scene,
    "single_brick": build_single_brick_scene,
    "multi_brick_scene": build_multi_brick_scene,
    "rotated_brick": build_rotated_brick_scene,
}


def _scene_signature(scene: Scene):

    return [
        (
            brick.id,
            brick.part_name,
            (brick.position.x, brick.position.y, brick.position.z),
            (
                brick.rotation.x, brick.rotation.y,
                brick.rotation.z, brick.rotation.w,
            ),
            brick.color_code,
        )
        for brick in scene
    ]


class GoldenFileSerializationTests(unittest.TestCase):
    """Byte-for-byte comparisons against tests/golden/scenes/*.json."""

    def test_golden_files_exist(self):

        for name in CANONICAL_SCENES:

            golden_path = GOLDEN_DIR / f"{name}.json"

            self.assertTrue(
                golden_path.is_file(),
                f"Missing golden file: {golden_path}",
            )

    def test_serialized_output_matches_golden_files(self):

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                golden_path = GOLDEN_DIR / f"{name}.json"
                golden_bytes = golden_path.read_bytes()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    out_path = Path(tmp_dir) / f"{name}.json"

                    serialize_scene(build_scene(), out_path)

                    actual_bytes = out_path.read_bytes()

                self.assertEqual(
                    actual_bytes,
                    golden_bytes,
                    f"Serialized output for {name!r} no longer matches "
                    f"its golden file byte-for-byte. If this is an "
                    f"INTENTIONAL format change, regenerate the golden "
                    f"file deliberately and review the diff before "
                    f"committing -- do not update it just to make this "
                    f"test pass.",
                )

    def test_round_trip_equality(self):
        """Scene -> serialize -> deserialize -> equivalent Scene."""

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                original = build_scene()

                with tempfile.TemporaryDirectory() as tmp_dir:

                    path = Path(tmp_dir) / f"{name}.json"

                    serialize_scene(original, path)
                    reconstructed = deserialize_scene(path)

                self.assertEqual(
                    _scene_signature(original),
                    _scene_signature(reconstructed),
                )

    def test_deserializing_golden_files_reconstructs_expected_scenes(self):
        """The committed golden files themselves deserialize correctly."""

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                golden_path = GOLDEN_DIR / f"{name}.json"
                reconstructed = deserialize_scene(golden_path)

                self.assertEqual(
                    _scene_signature(build_scene()),
                    _scene_signature(reconstructed),
                )

    def test_serialization_is_deterministic_on_repeat(self):

        for name, build_scene in CANONICAL_SCENES.items():

            with self.subTest(scene=name):

                with tempfile.TemporaryDirectory() as tmp_dir:

                    path = Path(tmp_dir) / f"{name}.json"

                    serialize_scene(build_scene(), path)
                    first = path.read_bytes()

                    serialize_scene(build_scene(), path)
                    second = path.read_bytes()

                self.assertEqual(first, second)

    def test_serialize_does_not_mutate_input_scene(self):

        scene = build_multi_brick_scene()
        before = _scene_signature(scene)

        with tempfile.TemporaryDirectory() as tmp_dir:

            serialize_scene(scene, Path(tmp_dir) / "out.json")

        self.assertEqual(before, _scene_signature(scene))


class MalformedFileTests(unittest.TestCase):
    """
    Every malformed-input case must raise SceneSerializationError, not
    silently repair or partially deserialize.
    """

    def _write_and_expect_error(self, content: str):

        with tempfile.TemporaryDirectory() as tmp_dir:

            path = Path(tmp_dir) / "bad.json"
            path.write_text(content, encoding="utf-8")

            with self.assertRaises(SceneSerializationError):
                deserialize_scene(path)

    def test_invalid_json(self):
        self._write_and_expect_error("not json at all {{{")

    def test_wrong_format_identifier(self):
        self._write_and_expect_error(
            '{"format": "Something Else", "schema_version": 1, "bricks": []}'
        )

    def test_unsupported_schema_version(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 999, "bricks": []}'
        )

    def test_missing_bricks_field(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1}'
        )

    def test_short_position_array(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1, "bricks": '
            '[{"id": 1, "part_name": "x.dat", "position": [0, 0], '
            '"rotation": [0, 0, 0, 1], "color_code": null}]}'
        )

    def test_boolean_color_code_rejected(self):
        # bool is a subclass of int in Python -- must be explicitly
        # excluded, not silently accepted as a color code.
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1, "bricks": '
            '[{"id": 1, "part_name": "x.dat", "position": [0, 0, 0], '
            '"rotation": [0, 0, 0, 1], "color_code": true}]}'
        )

    def test_boolean_id_rejected(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1, "bricks": '
            '[{"id": true, "part_name": "x.dat", "position": [0, 0, 0], '
            '"rotation": [0, 0, 0, 1], "color_code": null}]}'
        )

    def test_non_numeric_position_value_rejected(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1, "bricks": '
            '[{"id": 1, "part_name": "x.dat", '
            '"position": [0, 0, "NaN"], '
            '"rotation": [0, 0, 0, 1], "color_code": null}]}'
        )

    def test_empty_part_name_rejected(self):
        self._write_and_expect_error(
            '{"format": "StudWorks Scene", "schema_version": 1, "bricks": '
            '[{"id": 1, "part_name": "", "position": [0, 0, 0], '
            '"rotation": [0, 0, 0, 1], "color_code": null}]}'
        )


if __name__ == "__main__":
    unittest.main()
