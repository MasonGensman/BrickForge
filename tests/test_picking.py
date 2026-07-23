"""
StudWorks Picking Tests (Package_027)

Pure unit tests for render/picking.py -- no live OpenGL context, no
Renderer, no BrickManager. Camera matrices are built directly with
glm, matching how Package_024's LDraw rotation math was verified
independently of any renderer.
"""

import unittest

import glm

from brickforge.render.picking import ray_intersects_aabb, screen_to_ray

_WIDTH = 800
_HEIGHT = 600

# Camera looking down -Z at the origin from (0, 0, 10).
_VIEW = glm.lookAt(
    glm.vec3(0.0, 0.0, 10.0),
    glm.vec3(0.0, 0.0, 0.0),
    glm.vec3(0.0, 1.0, 0.0),
)
_PROJECTION = glm.perspective(
    glm.radians(45.0),
    _WIDTH / _HEIGHT,
    0.1,
    100.0,
)

_UNIT_BOX_MIN = glm.vec3(-1.0, -1.0, -1.0)
_UNIT_BOX_MAX = glm.vec3(1.0, 1.0, 1.0)


class ScreenToRayTests(unittest.TestCase):

    def test_center_click_points_down_negative_z(self):

        origin, direction = screen_to_ray(
            _WIDTH / 2,
            _HEIGHT / 2,
            _WIDTH,
            _HEIGHT,
            _VIEW,
            _PROJECTION,
        )

        self.assertAlmostEqual(origin.x, 0.0, places=4)
        self.assertAlmostEqual(origin.y, 0.0, places=4)

        self.assertAlmostEqual(direction.x, 0.0, places=4)
        self.assertAlmostEqual(direction.y, 0.0, places=4)
        self.assertLess(direction.z, 0.0)

    def test_direction_is_normalized(self):

        _, direction = screen_to_ray(
            100,
            50,
            _WIDTH,
            _HEIGHT,
            _VIEW,
            _PROJECTION,
        )

        length = glm.length(direction)
        self.assertAlmostEqual(length, 1.0, places=5)

    def test_top_left_and_bottom_right_produce_different_rays(self):
        """Sanity check against a degenerate always-same-ray bug."""

        _, top_left_dir = screen_to_ray(
            0, 0, _WIDTH, _HEIGHT, _VIEW, _PROJECTION
        )
        _, bottom_right_dir = screen_to_ray(
            _WIDTH, _HEIGHT, _WIDTH, _HEIGHT, _VIEW, _PROJECTION
        )

        self.assertNotAlmostEqual(
            top_left_dir.x, bottom_right_dir.x, places=3
        )
        self.assertNotAlmostEqual(
            top_left_dir.y, bottom_right_dir.y, places=3
        )

    def test_qt_y_down_convention_top_of_screen_is_positive_ndc_y(self):
        """
        Qt's screen_y grows downward; a click near the top of the
        widget (small screen_y) must unproject toward positive world
        Y (upward), not negative -- this is the y-flip screen_to_ray
        must apply.
        """

        _, direction = screen_to_ray(
            _WIDTH / 2, 0, _WIDTH, _HEIGHT, _VIEW, _PROJECTION
        )

        self.assertGreater(direction.y, 0.0)


class RayIntersectsAabbTests(unittest.TestCase):

    def test_ray_through_center_hits(self):

        origin = glm.vec3(0.0, 0.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, 9.0, places=5)

    def test_ray_missing_the_box_returns_none(self):

        origin = glm.vec3(5.0, 5.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNone(t)

    def test_ray_grazing_just_outside_the_edge_misses(self):

        origin = glm.vec3(1.0001, 0.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNone(t)

    def test_ray_just_inside_the_edge_hits(self):

        origin = glm.vec3(0.9999, 0.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNotNone(t)

    def test_box_behind_ray_origin_returns_none(self):

        origin = glm.vec3(0.0, 0.0, -10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNone(t)

    def test_ray_origin_inside_box_hits_at_t_zero(self):

        origin = glm.vec3(0.0, 0.0, 0.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, 0.0, places=5)

    def test_nearer_of_two_boxes_wins_by_smaller_t(self):

        origin = glm.vec3(0.0, 0.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        near_box = (glm.vec3(-1, -1, 4), glm.vec3(1, 1, 6))
        far_box = (glm.vec3(-1, -1, -6), glm.vec3(1, 1, -4))

        t_near = ray_intersects_aabb(origin, direction, *near_box)
        t_far = ray_intersects_aabb(origin, direction, *far_box)

        self.assertIsNotNone(t_near)
        self.assertIsNotNone(t_far)
        self.assertLess(t_near, t_far)

    def test_axis_aligned_ray_exercises_degenerate_direction_guard(self):
        """
        A ray parallel to two of the box's axes has a direction
        component of exactly 0.0 on both -- the slab test's
        degenerate-division guard (avoiding a ZeroDivisionError) is
        exercised on both, and the ray still correctly hits since its
        origin is within the box's slab on those axes.
        """

        origin = glm.vec3(0.0, 0.5, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNotNone(t)
        self.assertAlmostEqual(t, 9.0, places=5)

    def test_axis_aligned_ray_outside_slab_misses(self):
        """Same degenerate direction, but the origin's fixed y is
        outside the box's slab on that axis -- must miss, not hit."""

        origin = glm.vec3(0.0, 5.0, 10.0)
        direction = glm.vec3(0.0, 0.0, -1.0)

        t = ray_intersects_aabb(
            origin, direction, _UNIT_BOX_MIN, _UNIT_BOX_MAX
        )

        self.assertIsNone(t)


if __name__ == "__main__":
    unittest.main()
