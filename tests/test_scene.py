"""
StudWorks Scene Tests (Package_033)

Pure unit tests for Scene.next_available_id() -- Scene's other
methods (add_brick, get, remove_brick, clear, __iter__) are already
exercised indirectly throughout the rest of this test suite; this
file focuses on the one genuinely new piece of behavior.
"""

import unittest

import glm

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick


def _brick(brick_id):

    return SceneBrick(
        id=brick_id,
        part_name="3005.dat",
        position=glm.vec3(0.0, 0.0, 0.0),
        rotation=glm.quat(),
        color_code=4,
    )


class NextAvailableIdTests(unittest.TestCase):

    def test_empty_scene_returns_zero(self):

        scene = Scene()

        self.assertEqual(scene.next_available_id(), 0)

    def test_single_brick_returns_one_past_it(self):

        scene = Scene()
        scene.add_brick(_brick(0))

        self.assertEqual(scene.next_available_id(), 1)

    def test_returns_one_past_the_highest_existing_id(self):

        scene = Scene()
        scene.add_brick(_brick(0))
        scene.add_brick(_brick(5))
        scene.add_brick(_brick(2))

        self.assertEqual(scene.next_available_id(), 6)

    def test_handles_non_contiguous_ids_after_deletions(self):
        """A gap left by a deleted brick doesn't confuse the result --
        it's always relative to the highest id still present."""

        scene = Scene()
        scene.add_brick(_brick(0))
        scene.add_brick(_brick(3))
        # id 1 and 2 are "missing", simulating prior deletions.

        self.assertEqual(scene.next_available_id(), 4)

    def test_does_not_collide_with_any_existing_id(self):

        scene = Scene()

        for brick_id in (0, 1, 2, 3, 4):
            scene.add_brick(_brick(brick_id))

        next_id = scene.next_available_id()
        existing_ids = {b.id for b in scene}

        self.assertNotIn(next_id, existing_ids)

    def test_does_not_mutate_the_scene(self):

        scene = Scene()
        scene.add_brick(_brick(0))
        original_bricks = list(scene)

        scene.next_available_id()

        self.assertEqual(list(scene), original_bricks)

    def test_does_not_reserve_the_returned_id(self):
        """Calling it twice without using the result returns the same
        value both times -- it's a pure query, not a counter."""

        scene = Scene()
        scene.add_brick(_brick(0))

        first = scene.next_available_id()
        second = scene.next_available_id()

        self.assertEqual(first, second)

    def test_deterministic(self):

        def run():
            scene = Scene()
            scene.add_brick(_brick(3))
            scene.add_brick(_brick(7))
            return scene.next_available_id()

        self.assertEqual(run(), run())


if __name__ == "__main__":
    unittest.main()
