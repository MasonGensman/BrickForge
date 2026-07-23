"""
StudWorks Active Tool Manager Tests (Package_031)

Pure unit tests against a lightweight duck-typed fake renderer (same
"fake at the boundary" approach used throughout this project's Qt
tests) -- no real OpenGL context, no Qt event loop. Verifies
ActiveToolManager's dispatch, ToolResult shape, and that preview/
active state are always cleared regardless of outcome.
"""

import unittest

import glm
from PySide6.QtCore import Qt

from brickforge.engine.scene import Scene
from brickforge.engine.scene_brick import SceneBrick
from brickforge.tools.active_tool_manager import ActiveToolManager, ToolResult


class FakeRenderer:
    """Duck-typed stand-in exposing exactly what ActiveToolManager uses:
    .scene, .selected_id, .project_to_ground(), .set_preview()."""

    def __init__(self, scene, selected_id=None, ground_hit=None):

        self.scene = scene
        self.selected_id = selected_id
        self.preview = None

        # A fixed world point every project_to_ground() call returns,
        # or None to simulate the ray-parallel-to-plane degenerate case.
        self._ground_hit = ground_hit

    def project_to_ground(self, screen_x, screen_y, plane_y):
        return self._ground_hit

    def set_preview(self, preview):
        self.preview = preview


def _scene_with_one_brick(brick_id=1, position=None, rotation=None):

    scene = Scene()

    scene.add_brick(
        SceneBrick(
            id=brick_id,
            part_name="3005.dat",
            position=position if position is not None else glm.vec3(0.0, 0.0, 0.0),
            rotation=rotation if rotation is not None else glm.quat(),
            color_code=4,
        )
    )

    return scene


class TryBeginTests(unittest.TestCase):

    def test_no_brick_picked_declines(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        began = manager.try_begin(Qt.LeftButton, renderer, None, 10.0, 10.0)

        self.assertFalse(began)
        self.assertFalse(manager.is_dragging)

    def test_picked_brick_not_selected_declines(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=1), selected_id=2)

        began = manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        self.assertFalse(began)

    def test_middle_button_never_begins_a_tool(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(
            _scene_with_one_brick(), selected_id=1,
            ground_hit=glm.vec3(0.0, 0.0, 0.0),
        )

        began = manager.try_begin(Qt.MiddleButton, renderer, 1, 10.0, 10.0)

        self.assertFalse(began)

    def test_left_button_on_selected_brick_begins_move(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(
            _scene_with_one_brick(), selected_id=1,
            ground_hit=glm.vec3(0.0, 0.0, 0.0),
        )

        began = manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        self.assertTrue(began)
        self.assertTrue(manager.is_dragging)
        self.assertEqual(manager.active_tool_name, "move")

    def test_right_button_on_selected_brick_begins_rotate(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        began = manager.try_begin(Qt.RightButton, renderer, 1, 10.0, 10.0)

        self.assertTrue(began)
        self.assertTrue(manager.is_dragging)
        self.assertEqual(manager.active_tool_name, "rotate")

    def test_move_declines_when_ground_ray_misses(self):
        """The rare degenerate case: project_to_ground() returns None."""

        manager = ActiveToolManager()
        renderer = FakeRenderer(
            _scene_with_one_brick(), selected_id=1, ground_hit=None,
        )

        began = manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        self.assertFalse(began)
        self.assertFalse(manager.is_dragging)

    def test_not_dragging_before_any_begin(self):

        manager = ActiveToolManager()

        self.assertFalse(manager.is_dragging)
        self.assertIsNone(manager.active_tool_name)


class UpdateTests(unittest.TestCase):

    def test_move_update_holds_rotation_constant_and_varies_position(self):

        manager = ActiveToolManager()
        rotation = glm.angleAxis(glm.radians(30.0), glm.vec3(0.0, 1.0, 0.0))
        scene = _scene_with_one_brick(position=glm.vec3(0.0, 0.0, 0.0), rotation=rotation)
        renderer = FakeRenderer(scene, selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0))

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        renderer._ground_hit = glm.vec3(20.0, 0.0, 0.0)
        manager.update(renderer, 30.0, 10.0)

        self.assertIsNotNone(renderer.preview)
        self.assertEqual(renderer.preview.brick_id, 1)
        self.assertAlmostEqual(renderer.preview.position.x, 20.0, places=4)
        self.assertAlmostEqual(renderer.preview.rotation.y, rotation.y, places=6)

    def test_rotate_update_holds_position_constant_and_varies_rotation(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick(position=glm.vec3(5.0, 0.0, 5.0))
        renderer = FakeRenderer(scene, selected_id=1)

        manager.try_begin(Qt.RightButton, renderer, 1, 100.0, 10.0)
        manager.update(renderer, 100.0 + 90.0 / 0.35, 10.0)

        self.assertIsNotNone(renderer.preview)
        self.assertEqual(renderer.preview.brick_id, 1)
        self.assertAlmostEqual(renderer.preview.position.x, 5.0, places=4)
        self.assertAlmostEqual(renderer.preview.position.z, 5.0, places=4)

        rotated_point = renderer.preview.rotation * glm.vec3(1.0, 0.0, 0.0)
        self.assertAlmostEqual(rotated_point.z, -1.0, places=4)

    def test_update_without_dragging_is_a_no_op(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        manager.update(renderer, 10.0, 10.0)

        self.assertIsNone(renderer.preview)


class FinishTests(unittest.TestCase):

    def test_move_finish_returns_position_result(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick(position=glm.vec3(0.0, 0.0, 0.0))
        renderer = FakeRenderer(scene, selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0))

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        renderer._ground_hit = glm.vec3(20.0, 0.0, 0.0)
        result = manager.finish(renderer, 30.0, 10.0)

        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.brick_id, 1)
        self.assertEqual(result.field, "position")
        self.assertEqual(result.verb, "Moved")
        self.assertAlmostEqual(result.value.x, 20.0, places=4)

    def test_rotate_finish_returns_rotation_result(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick()
        renderer = FakeRenderer(scene, selected_id=1)

        manager.try_begin(Qt.RightButton, renderer, 1, 100.0, 10.0)
        result = manager.finish(renderer, 100.0 + 90.0 / 0.35, 10.0)

        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.brick_id, 1)
        self.assertEqual(result.field, "rotation")
        self.assertEqual(result.verb, "Rotated")

    def test_finish_always_clears_preview_and_active_state(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick()
        renderer = FakeRenderer(scene, selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0))

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)
        manager.update(renderer, 30.0, 10.0)
        self.assertIsNotNone(renderer.preview)

        manager.finish(renderer, 30.0, 10.0)

        self.assertIsNone(renderer.preview)
        self.assertFalse(manager.is_dragging)
        self.assertIsNone(manager.active_tool_name)

    def test_zero_distance_move_finish_returns_none_but_still_clears_state(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick(position=glm.vec3(0.0, 0.0, 0.0))
        renderer = FakeRenderer(scene, selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0))

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)
        result = manager.finish(renderer, 10.0, 10.0)

        self.assertIsNone(result)
        self.assertFalse(manager.is_dragging)
        self.assertIsNone(renderer.preview)

    def test_zero_angle_rotate_finish_returns_none_but_still_clears_state(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        manager.try_begin(Qt.RightButton, renderer, 1, 100.0, 10.0)
        result = manager.finish(renderer, 100.0, 10.0)

        self.assertIsNone(result)
        self.assertFalse(manager.is_dragging)

    def test_move_finish_with_ground_ray_miss_cancels_and_returns_none(self):

        manager = ActiveToolManager()
        scene = _scene_with_one_brick(position=glm.vec3(0.0, 0.0, 0.0))
        renderer = FakeRenderer(scene, selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0))

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)

        renderer._ground_hit = None
        result = manager.finish(renderer, 999.0, 999.0)

        self.assertIsNone(result)
        self.assertFalse(manager.is_dragging)
        self.assertIsNone(renderer.preview)

    def test_finish_without_dragging_is_a_no_op(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        result = manager.finish(renderer, 10.0, 10.0)

        self.assertIsNone(result)


class TryDeleteTests(unittest.TestCase):

    def test_middle_button_on_selected_brick_returns_a_removal_result(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=7)

        result = manager.try_delete(Qt.MiddleButton, renderer, 7)

        self.assertIsInstance(result, ToolResult)
        self.assertEqual(result.brick_id, 7)
        self.assertEqual(result.verb, "Deleted")
        self.assertTrue(result.is_removal)
        self.assertIsNone(result.field)
        self.assertIsNone(result.value)

    def test_try_delete_does_not_touch_active_state(self):
        """Delete has no drag lifecycle -- it never arms self._active."""

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=7)

        manager.try_delete(Qt.MiddleButton, renderer, 7)

        self.assertFalse(manager.is_dragging)
        self.assertIsNone(manager.active_tool_name)

    def test_left_button_does_not_delete(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=7)

        result = manager.try_delete(Qt.LeftButton, renderer, 7)

        self.assertIsNone(result)

    def test_right_button_does_not_delete(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=7)

        result = manager.try_delete(Qt.RightButton, renderer, 7)

        self.assertIsNone(result)

    def test_no_brick_picked_declines(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=7)

        result = manager.try_delete(Qt.MiddleButton, renderer, None)

        self.assertIsNone(result)

    def test_picked_brick_not_selected_declines(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=99)

        result = manager.try_delete(Qt.MiddleButton, renderer, 7)

        self.assertIsNone(result)

    def test_no_selection_declines(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(brick_id=7), selected_id=None)

        result = manager.try_delete(Qt.MiddleButton, renderer, 7)

        self.assertIsNone(result)

    def test_declines_while_another_tool_is_already_dragging(self):
        """Guards against deleting a brick out from under an active
        Move/Rotate drag."""

        manager = ActiveToolManager()
        renderer = FakeRenderer(
            _scene_with_one_brick(brick_id=7), selected_id=7,
            ground_hit=glm.vec3(0.0, 0.0, 0.0),
        )

        manager.try_begin(Qt.LeftButton, renderer, 7, 10.0, 10.0)
        self.assertTrue(manager.is_dragging)

        result = manager.try_delete(Qt.MiddleButton, renderer, 7)

        self.assertIsNone(result)
        # The in-progress move drag must be unaffected.
        self.assertTrue(manager.is_dragging)
        self.assertEqual(manager.active_tool_name, "move")


class CancelTests(unittest.TestCase):

    def test_cancel_clears_move_drag(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(
            _scene_with_one_brick(), selected_id=1, ground_hit=glm.vec3(0.0, 0.0, 0.0),
        )

        manager.try_begin(Qt.LeftButton, renderer, 1, 10.0, 10.0)
        manager.cancel()

        self.assertFalse(manager.is_dragging)
        self.assertIsNone(manager.active_tool_name)

    def test_cancel_clears_rotate_drag(self):

        manager = ActiveToolManager()
        renderer = FakeRenderer(_scene_with_one_brick(), selected_id=1)

        manager.try_begin(Qt.RightButton, renderer, 1, 10.0, 10.0)
        manager.cancel()

        self.assertFalse(manager.is_dragging)

    def test_cancel_without_dragging_is_a_no_op(self):

        manager = ActiveToolManager()

        manager.cancel()

        self.assertFalse(manager.is_dragging)


if __name__ == "__main__":
    unittest.main()
