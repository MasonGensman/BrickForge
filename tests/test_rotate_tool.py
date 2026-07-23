"""
StudWorks Rotate Tool Tests (Package_030)

Pure unit tests -- no Qt, no OpenGL, no Renderer, no Scene mutation.
RotateTool does pure arithmetic over screen-space x coordinates and
quaternion math; these tests verify its drag lifecycle and math
directly.
"""

import unittest

import glm

from brickforge.engine.scene_brick import SceneBrick
from brickforge.tools.rotate_tool import RotateTool


def _brick(brick_id=1, rotation=None):

    return SceneBrick(
        id=brick_id,
        part_name="3005.dat",
        position=glm.vec3(0.0, 0.0, 0.0),
        rotation=rotation if rotation is not None else glm.quat(),
        color_code=4,
    )


class RotateToolStateTests(unittest.TestCase):

    def test_starts_not_dragging(self):

        tool = RotateTool()

        self.assertFalse(tool.is_dragging)
        self.assertIsNone(tool.brick_id)

    def test_begin_starts_dragging(self):

        tool = RotateTool()
        brick = _brick()

        tool.begin(brick, 100.0)

        self.assertTrue(tool.is_dragging)
        self.assertEqual(tool.brick_id, brick.id)

    def test_cancel_clears_drag_state(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        tool.cancel()

        self.assertFalse(tool.is_dragging)
        self.assertIsNone(tool.brick_id)

    def test_finish_clears_drag_state(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        tool.finish(400.0)

        self.assertFalse(tool.is_dragging)


class RotateToolAngleMathTests(unittest.TestCase):
    """
    Verify the actual rotated direction, not just "some quaternion
    changed" -- matching the empirical trig check done during
    planning.
    """

    def test_dragging_right_by_90_degrees_worth_of_pixels(self):

        tool = RotateTool()
        brick = _brick()

        tool.begin(brick, 100.0)

        # 90 degrees / 0.35 degrees-per-pixel.
        preview = tool.update(100.0 + 90.0 / 0.35)

        rotated_point = preview * glm.vec3(1.0, 0.0, 0.0)

        self.assertAlmostEqual(rotated_point.x, 0.0, places=4)
        self.assertAlmostEqual(rotated_point.z, -1.0, places=4)

    def test_dragging_left_rotates_the_opposite_direction(self):

        tool = RotateTool()
        brick = _brick()

        tool.begin(brick, 100.0)

        preview = tool.update(100.0 - 90.0 / 0.35)

        rotated_point = preview * glm.vec3(1.0, 0.0, 0.0)

        self.assertAlmostEqual(rotated_point.x, 0.0, places=4)
        self.assertAlmostEqual(rotated_point.z, 1.0, places=4)

    def test_rotation_starts_from_the_bricks_existing_rotation(self):
        """A brick that's already rotated 90 degrees, dragged another
        90 degrees, should land at 180 degrees -- not reset to 90."""

        tool = RotateTool()
        already_rotated = glm.angleAxis(
            glm.radians(90.0), glm.vec3(0.0, 1.0, 0.0)
        )
        brick = _brick(rotation=already_rotated)

        tool.begin(brick, 100.0)
        preview = tool.update(100.0 + 90.0 / 0.35)

        rotated_point = preview * glm.vec3(1.0, 0.0, 0.0)

        # 180 degrees from (1,0,0) around Y lands at (-1, 0, 0).
        self.assertAlmostEqual(rotated_point.x, -1.0, places=4)
        self.assertAlmostEqual(rotated_point.z, 0.0, places=4)

    def test_update_result_is_always_a_unit_quaternion(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        preview = tool.update(250.0)

        self.assertAlmostEqual(glm.length(preview), 1.0, places=6)

    def test_finish_returns_rotation_matching_update(self):

        tool = RotateTool()
        brick = _brick()

        tool.begin(brick, 100.0)
        expected = tool.update(300.0)

        tool2 = RotateTool()
        tool2.begin(brick, 100.0)
        result = tool2.finish(300.0)

        self.assertIsNotNone(result)

        brick_id, final_rotation = result

        self.assertEqual(brick_id, brick.id)
        self.assertAlmostEqual(final_rotation.x, expected.x, places=6)
        self.assertAlmostEqual(final_rotation.y, expected.y, places=6)
        self.assertAlmostEqual(final_rotation.z, expected.z, places=6)
        self.assertAlmostEqual(final_rotation.w, expected.w, places=6)


class RotateToolZeroAngleTests(unittest.TestCase):

    def test_finish_at_the_start_x_returns_none(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        result = tool.finish(100.0)

        self.assertIsNone(result)

    def test_finish_with_a_negligible_movement_returns_none(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        # 1e-6 pixels -> far below the zero-angle epsilon.
        result = tool.finish(100.0 + 1e-6)

        self.assertIsNone(result)

    def test_finish_with_a_real_rotation_returns_a_result(self):

        tool = RotateTool()
        tool.begin(_brick(), 100.0)

        result = tool.finish(200.0)

        self.assertIsNotNone(result)


class RotateToolStabilityTests(unittest.TestCase):
    """Directly exercises "repeated rotations remain stable": many
    separate rotate-and-commit cycles in a row must never let the
    quaternion's magnitude drift from 1.0."""

    def test_repeated_commits_stay_unit_length(self):

        rotation = glm.quat()

        for _ in range(200):

            tool = RotateTool()
            brick = SceneBrick(
                id=1, part_name="3005.dat",
                position=glm.vec3(0.0, 0.0, 0.0),
                rotation=rotation,
            )

            tool.begin(brick, 0.0)
            result = tool.finish(37.0)

            self.assertIsNotNone(result)

            _, rotation = result

        self.assertAlmostEqual(glm.length(rotation), 1.0, places=6)


class RotateToolDeterminismTests(unittest.TestCase):

    def test_deterministic(self):

        def run():
            tool = RotateTool()
            tool.begin(_brick(), 100.0)
            return tool.finish(325.0)

        first = run()
        second = run()

        self.assertEqual(first[0], second[0])
        self.assertAlmostEqual(first[1].x, second[1].x, places=6)
        self.assertAlmostEqual(first[1].w, second[1].w, places=6)


if __name__ == "__main__":
    unittest.main()
