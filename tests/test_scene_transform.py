"""
StudWorks Scene Transform Tests (Package_028)

Pure unit tests for transform/scene_transform.py -- no Qt, no OpenGL,
no SelectionManager/Renderer/Project. replace_brick() is a stateless
Scene -> Scene function; these tests verify its immutability contract
directly.
"""

import dataclasses
import unittest

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.transform.scene_transform import TransformError, replace_brick


def _brick(brick_id, x=0.0, color_code=4):

    return SceneBrick(
        id=brick_id,
        part_name="3005.dat",
        position=glm.vec3(x, 0.0, 0.0),
        rotation=glm.quat(),
        color_code=color_code,
    )


def _three_brick_scene():

    scene = Scene()

    scene.add_brick(_brick(0, x=0.0))
    scene.add_brick(_brick(1, x=20.0))
    scene.add_brick(_brick(2, x=40.0))

    return scene


class ReplaceBrickTests(unittest.TestCase):

    def test_returns_a_different_scene_object(self):

        scene = _three_brick_scene()
        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))

        result = replace_brick(scene, updated)

        self.assertIsNot(result, scene)
        self.assertIsNot(result.bricks, scene.bricks)

    def test_original_scene_is_unchanged(self):

        scene = _three_brick_scene()
        original_bricks = list(scene)
        original_positions = [
            (b.id, b.position.x, b.position.y, b.position.z)
            for b in original_bricks
        ]

        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))
        replace_brick(scene, updated)

        after_positions = [
            (b.id, b.position.x, b.position.y, b.position.z)
            for b in scene
        ]

        self.assertEqual(original_positions, after_positions)
        self.assertEqual(list(scene), original_bricks)

    def test_target_brick_is_not_mutated_in_place(self):
        """dataclasses.replace() already guarantees this, but confirm
        replace_brick() doesn't reach back and mutate the original
        object some other way."""

        scene = _three_brick_scene()
        original = scene.get(1)
        original_position = glm.vec3(original.position)

        updated = dataclasses.replace(original, position=glm.vec3(99.0, 0.0, 0.0))
        replace_brick(scene, updated)

        self.assertEqual(
            (original.position.x, original.position.y, original.position.z),
            (original_position.x, original_position.y, original_position.z),
        )

    def test_updated_brick_present_with_new_values(self):

        scene = _three_brick_scene()
        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))

        result = replace_brick(scene, updated)
        found = result.get(1)

        self.assertIsNotNone(found)
        self.assertEqual((found.position.x, found.position.y, found.position.z), (99.0, 0.0, 0.0))

    def test_other_bricks_preserved_by_reference(self):

        scene = _three_brick_scene()
        brick_0 = scene.get(0)
        brick_2 = scene.get(2)

        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))
        result = replace_brick(scene, updated)

        self.assertIs(result.get(0), brick_0)
        self.assertIs(result.get(2), brick_2)

    def test_id_set_is_unchanged(self):

        scene = _three_brick_scene()
        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))

        result = replace_brick(scene, updated)

        self.assertEqual(
            {b.id for b in scene},
            {b.id for b in result},
        )

    def test_brick_count_is_unchanged(self):

        scene = _three_brick_scene()
        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))

        result = replace_brick(scene, updated)

        self.assertEqual(len(list(result)), len(list(scene)))

    def test_order_is_preserved(self):

        scene = _three_brick_scene()
        updated = dataclasses.replace(scene.get(1), position=glm.vec3(99.0, 0.0, 0.0))

        result = replace_brick(scene, updated)

        self.assertEqual([b.id for b in result], [0, 1, 2])

    def test_invalid_id_raises_transform_error(self):

        scene = _three_brick_scene()
        phantom = _brick(999, x=0.0)

        with self.assertRaises(TransformError):
            replace_brick(scene, phantom)

    def test_invalid_id_does_not_change_original_scene(self):

        scene = _three_brick_scene()
        original_count = len(list(scene))
        phantom = _brick(999, x=0.0)

        try:
            replace_brick(scene, phantom)
        except TransformError:
            pass

        self.assertEqual(len(list(scene)), original_count)

    def test_no_op_replace_succeeds(self):
        """Replacing a brick with an identical copy is valid, not an error."""

        scene = _three_brick_scene()
        same_values = dataclasses.replace(scene.get(1))

        result = replace_brick(scene, same_values)

        self.assertEqual(list(result), list(scene))

    def test_replacing_with_the_exact_same_object_works(self):

        scene = _three_brick_scene()
        brick = scene.get(1)

        result = replace_brick(scene, brick)

        self.assertIs(result.get(1), brick)

    def test_deterministic(self):

        def run():
            scene = _three_brick_scene()
            updated = dataclasses.replace(scene.get(1), position=glm.vec3(5.0, 6.0, 7.0))
            result = replace_brick(scene, updated)
            return [
                (b.id, b.position.x, b.position.y, b.position.z)
                for b in result
            ]

        self.assertEqual(run(), run())

    def test_empty_scene_raises_transform_error(self):

        scene = Scene()
        phantom = _brick(0)

        with self.assertRaises(TransformError):
            replace_brick(scene, phantom)


if __name__ == "__main__":
    unittest.main()
