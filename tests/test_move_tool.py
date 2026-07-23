"""
StudWorks Move Tool Tests (Package_029)

Pure unit tests -- no Qt, no OpenGL, no Renderer, no Scene mutation.
MoveTool does vector math over already-computed world-space points;
these tests verify its drag lifecycle and math directly.
"""

import unittest

import glm

from brickforge.engine.scene_brick import SceneBrick
from brickforge.tools.move_tool import MoveTool


def _brick(brick_id=1, x=10.0, y=0.0, z=5.0):

    return SceneBrick(
        id=brick_id,
        part_name="3005.dat",
        position=glm.vec3(x, y, z),
        rotation=glm.quat(),
        color_code=4,
    )


class MoveToolStateTests(unittest.TestCase):

    def test_starts_not_dragging(self):

        tool = MoveTool()

        self.assertFalse(tool.is_dragging)
        self.assertIsNone(tool.brick_id)

    def test_begin_starts_dragging(self):

        tool = MoveTool()
        brick = _brick()

        tool.begin(brick, glm.vec3(10.0, 0.0, 5.0))

        self.assertTrue(tool.is_dragging)
        self.assertEqual(tool.brick_id, brick.id)

    def test_plane_y_matches_the_brick_starting_height(self):

        tool = MoveTool()
        brick = _brick(y=24.0)

        tool.begin(brick, glm.vec3(10.0, 24.0, 5.0))

        self.assertEqual(tool.plane_y, 24.0)

    def test_cancel_clears_drag_state(self):

        tool = MoveTool()
        tool.begin(_brick(), glm.vec3(10.0, 0.0, 5.0))

        tool.cancel()

        self.assertFalse(tool.is_dragging)
        self.assertIsNone(tool.brick_id)

    def test_finish_clears_drag_state(self):

        tool = MoveTool()
        tool.begin(_brick(), glm.vec3(10.0, 0.0, 5.0))

        tool.finish(glm.vec3(50.0, 0.0, 5.0))

        self.assertFalse(tool.is_dragging)


class MoveToolGrabOffsetTests(unittest.TestCase):
    """
    The brick shouldn't jump to snap its origin under the cursor --
    the initial offset between the grab point and the brick's own
    origin is preserved for the whole drag.
    """

    def test_update_preserves_the_initial_grab_offset(self):

        tool = MoveTool()
        brick = _brick(x=10.0, y=0.0, z=5.0)

        # Click 3 units off from the brick's own origin.
        tool.begin(brick, glm.vec3(13.0, 0.0, 5.0))

        # Moving the grab point by (20, 0, 0) should move the brick
        # by the same (20, 0, 0), not snap to the new grab point.
        preview = tool.update(glm.vec3(33.0, 0.0, 5.0))

        self.assertAlmostEqual(preview.x, 30.0, places=5)
        self.assertAlmostEqual(preview.z, 5.0, places=5)

    def test_update_at_the_original_grab_point_returns_original_position(self):

        tool = MoveTool()
        brick = _brick(x=10.0, y=0.0, z=5.0)
        grab_point = glm.vec3(13.0, 0.0, 5.0)

        tool.begin(brick, grab_point)
        preview = tool.update(grab_point)

        self.assertAlmostEqual(preview.x, brick.position.x, places=5)
        self.assertAlmostEqual(preview.z, brick.position.z, places=5)

    def test_finish_returns_final_position_with_grab_offset_applied(self):

        tool = MoveTool()
        brick = _brick(x=10.0, y=0.0, z=5.0)

        tool.begin(brick, glm.vec3(13.0, 0.0, 5.0))
        result = tool.finish(glm.vec3(33.0, 0.0, 5.0))

        self.assertIsNotNone(result)

        brick_id, final_position = result

        self.assertEqual(brick_id, brick.id)
        self.assertAlmostEqual(final_position.x, 30.0, places=5)


class MoveToolZeroDistanceTests(unittest.TestCase):

    def test_finish_at_the_original_grab_point_returns_none(self):

        tool = MoveTool()
        brick = _brick()
        grab_point = glm.vec3(10.0, 0.0, 5.0)

        tool.begin(brick, grab_point)
        result = tool.finish(grab_point)

        self.assertIsNone(result)

    def test_finish_with_a_negligible_movement_returns_none(self):

        tool = MoveTool()
        brick = _brick()
        grab_point = glm.vec3(10.0, 0.0, 5.0)

        tool.begin(brick, grab_point)

        # Well below the zero-distance epsilon.
        result = tool.finish(grab_point + glm.vec3(1e-6, 0.0, 0.0))

        self.assertIsNone(result)

    def test_finish_with_a_real_movement_returns_a_result(self):

        tool = MoveTool()
        brick = _brick()
        grab_point = glm.vec3(10.0, 0.0, 5.0)

        tool.begin(brick, grab_point)
        result = tool.finish(grab_point + glm.vec3(20.0, 0.0, 0.0))

        self.assertIsNotNone(result)


class MoveToolDeterminismTests(unittest.TestCase):

    def test_deterministic(self):

        def run():
            tool = MoveTool()
            tool.begin(_brick(), glm.vec3(10.0, 0.0, 5.0))
            return tool.finish(glm.vec3(40.0, 0.0, 15.0))

        first = run()
        second = run()

        self.assertEqual(first[0], second[0])
        self.assertAlmostEqual(first[1].x, second[1].x, places=6)
        self.assertAlmostEqual(first[1].z, second[1].z, places=6)


if __name__ == "__main__":
    unittest.main()
