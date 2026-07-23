"""
StudWorks Scene Transform Tests (Package_028, extended in Packages 032-033)

Pure unit tests for transform/scene_transform.py -- no Qt, no OpenGL,
no SelectionManager/Renderer/Project. replace_brick()/remove_brick()/
duplicate_brick() are stateless Scene -> (new) Scene functions; these
tests verify their immutability contracts directly.
"""

import dataclasses
import unittest

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.transform.scene_transform import (
    TransformError,
    duplicate_brick,
    remove_brick,
    replace_brick,
)


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


class RemoveBrickTests(unittest.TestCase):

    def test_returns_a_different_scene_object(self):

        scene = _three_brick_scene()

        result = remove_brick(scene, 1)

        self.assertIsNot(result, scene)
        self.assertIsNot(result.bricks, scene.bricks)

    def test_original_scene_is_unchanged(self):

        scene = _three_brick_scene()
        original_bricks = list(scene)

        remove_brick(scene, 1)

        self.assertEqual(list(scene), original_bricks)
        self.assertEqual(len(list(scene)), 3)

    def test_target_brick_is_removed(self):

        scene = _three_brick_scene()

        result = remove_brick(scene, 1)

        self.assertIsNone(result.get(1))

    def test_other_bricks_preserved_by_reference(self):

        scene = _three_brick_scene()
        brick_0 = scene.get(0)
        brick_2 = scene.get(2)

        result = remove_brick(scene, 1)

        self.assertIs(result.get(0), brick_0)
        self.assertIs(result.get(2), brick_2)

    def test_id_set_shrinks_by_exactly_the_removed_id(self):
        """Unlike replace_brick, the id set is NOT preserved -- it's a
        strict subset missing exactly the removed id."""

        scene = _three_brick_scene()

        result = remove_brick(scene, 1)

        self.assertEqual({b.id for b in result}, {0, 2})

    def test_brick_count_decreases_by_one(self):

        scene = _three_brick_scene()

        result = remove_brick(scene, 1)

        self.assertEqual(len(list(result)), len(list(scene)) - 1)

    def test_order_is_preserved(self):

        scene = _three_brick_scene()

        result = remove_brick(scene, 1)

        self.assertEqual([b.id for b in result], [0, 2])

    def test_invalid_id_raises_transform_error(self):

        scene = _three_brick_scene()

        with self.assertRaises(TransformError):
            remove_brick(scene, 999)

    def test_invalid_id_does_not_change_original_scene(self):

        scene = _three_brick_scene()
        original_count = len(list(scene))

        try:
            remove_brick(scene, 999)
        except TransformError:
            pass

        self.assertEqual(len(list(scene)), original_count)

    def test_removing_the_last_brick_produces_a_valid_empty_scene(self):

        scene = Scene()
        scene.add_brick(_brick(0))

        result = remove_brick(scene, 0)

        self.assertEqual(list(result), [])
        self.assertEqual(len(list(result)), 0)

    def test_repeated_removal_of_the_same_id_raises_the_second_time(self):
        """Defense-in-depth: even though the UI layer can't naturally
        reach this (selection clears the instant the first delete
        commits), the engine itself must independently refuse a
        second removal of an id that's already gone."""

        scene = _three_brick_scene()

        first_result = remove_brick(scene, 1)

        with self.assertRaises(TransformError):
            remove_brick(first_result, 1)

        # The original 3-brick scene is still untouched by either call.
        self.assertEqual(len(list(scene)), 3)

    def test_deterministic(self):

        def run():
            scene = _three_brick_scene()
            result = remove_brick(scene, 1)
            return [b.id for b in result]

        self.assertEqual(run(), run())


class DuplicateBrickTests(unittest.TestCase):

    def test_returns_a_different_scene_object(self):

        scene = _three_brick_scene()

        result, _ = duplicate_brick(scene, 1)

        self.assertIsNot(result, scene)
        self.assertIsNot(result.bricks, scene.bricks)

    def test_original_scene_is_unchanged(self):

        scene = _three_brick_scene()
        original_bricks = list(scene)

        duplicate_brick(scene, 1)

        self.assertEqual(list(scene), original_bricks)
        self.assertEqual(len(list(scene)), 3)

    def test_original_brick_is_not_mutated(self):

        scene = _three_brick_scene()
        original = scene.get(1)
        original_position = glm.vec3(original.position)

        duplicate_brick(scene, 1)

        self.assertEqual(
            (original.position.x, original.position.y, original.position.z),
            (original_position.x, original_position.y, original_position.z),
        )
        self.assertEqual(original.id, 1)

    def test_new_brick_has_a_unique_id(self):

        scene = _three_brick_scene()

        result, new_id = duplicate_brick(scene, 1)

        self.assertNotIn(new_id, {b.id for b in scene})
        self.assertIsNotNone(result.get(new_id))

    def test_returned_id_matches_the_actual_duplicate(self):

        scene = _three_brick_scene()

        result, new_id = duplicate_brick(scene, 1)

        found = result.get(new_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, new_id)

    def test_duplicate_copies_part_name_rotation_and_color(self):

        scene = Scene()

        rotation = glm.angleAxis(glm.radians(37.0), glm.vec3(0.0, 1.0, 0.0))

        scene.add_brick(
            SceneBrick(
                id=0,
                part_name="3004.dat",
                position=glm.vec3(10.0, 5.0, -10.0),
                rotation=rotation,
                color_code=14,
            )
        )

        result, new_id = duplicate_brick(scene, 0)
        duplicate = result.get(new_id)

        self.assertEqual(duplicate.part_name, "3004.dat")
        self.assertEqual(duplicate.color_code, 14)
        self.assertAlmostEqual(duplicate.rotation.x, rotation.x, places=6)
        self.assertAlmostEqual(duplicate.rotation.y, rotation.y, places=6)
        self.assertAlmostEqual(duplicate.rotation.z, rotation.z, places=6)
        self.assertAlmostEqual(duplicate.rotation.w, rotation.w, places=6)

    def test_duplicate_position_is_offset_from_the_original(self):

        scene = _three_brick_scene()
        original = scene.get(1)

        result, new_id = duplicate_brick(scene, 1)
        duplicate = result.get(new_id)

        self.assertNotEqual(
            (duplicate.position.x, duplicate.position.y, duplicate.position.z),
            (original.position.x, original.position.y, original.position.z),
        )
        self.assertAlmostEqual(duplicate.position.x, original.position.x + 20.0, places=5)
        self.assertAlmostEqual(duplicate.position.y, original.position.y, places=5)
        self.assertAlmostEqual(duplicate.position.z, original.position.z, places=5)

    def test_original_brick_still_present_unchanged(self):

        scene = _three_brick_scene()

        result, _ = duplicate_brick(scene, 1)
        still_there = result.get(1)

        self.assertIsNotNone(still_there)
        self.assertAlmostEqual(still_there.position.x, 20.0, places=5)

    def test_other_bricks_preserved_by_reference(self):

        scene = _three_brick_scene()
        brick_0 = scene.get(0)
        brick_2 = scene.get(2)

        result, _ = duplicate_brick(scene, 1)

        self.assertIs(result.get(0), brick_0)
        self.assertIs(result.get(2), brick_2)

    def test_brick_count_increases_by_one(self):

        scene = _three_brick_scene()

        result, _ = duplicate_brick(scene, 1)

        self.assertEqual(len(list(result)), len(list(scene)) + 1)

    def test_new_id_does_not_collide_even_with_non_contiguous_ids(self):
        """Simulates duplicating in a Scene that already has gaps from
        prior deletions."""

        scene = Scene()
        scene.add_brick(_brick(0))
        scene.add_brick(_brick(5))

        result, new_id = duplicate_brick(scene, 0)

        self.assertNotIn(new_id, {0, 5})
        self.assertEqual(len(list(result)), 3)

    def test_invalid_id_raises_transform_error(self):

        scene = _three_brick_scene()

        with self.assertRaises(TransformError):
            duplicate_brick(scene, 999)

    def test_invalid_id_does_not_change_original_scene(self):

        scene = _three_brick_scene()
        original_count = len(list(scene))

        try:
            duplicate_brick(scene, 999)
        except TransformError:
            pass

        self.assertEqual(len(list(scene)), original_count)

    def test_deterministic(self):

        def run():
            scene = _three_brick_scene()
            result, new_id = duplicate_brick(scene, 1)
            return [b.id for b in result], new_id

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
