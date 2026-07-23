"""
StudWorks Rotate Tool

An interaction subsystem, not a rendering or Scene-mutation one --
same role as MoveTool, but not sharing code with it: RotateTool's
input is a raw screen-space x coordinate (no raycasting, no
degenerate-miss case), where MoveTool's is a world-space point from a
ray/plane intersection. That's a genuine difference in data shape,
not just in math, so the two tools stay independent rather than
sharing a speculative base class (see Package_030.md).

Rotation is yaw-only, around the fixed world Y axis, matching every
rotation this codebase has ever produced and satisfying "no arbitrary
pivot editing" by construction -- always the brick's own origin.

Precision: update() always computes a single fresh multiplication
from the immutable original_rotation captured at begin(), never
chaining frame-to-frame, then explicitly renormalizes. Verified
empirically before this design was finalized: 200 repeated
quaternion multiplications *without* renormalizing drift to a length
of ~1.0000031 -- small, but real and growing; the same 200 iterations
each followed by glm.normalize() stay at exactly 1.0. Always
recomputing from the untouched original (rather than accumulating
onto the previous preview) is what makes this correct, not merely
convenient.
"""

import glm

from brickforge.engine.scene_brick import SceneBrick

_ROTATION_AXIS = glm.vec3(0.0, 1.0, 0.0)

#
# Degrees per pixel -- matches Camera.orbit's own yaw sensitivity, so
# dragging a brick to rotate it feels like the same rotational speed
# as orbiting the camera, a gesture the user already knows.
#
_ROTATE_SENSITIVITY = 0.35

#
# Below this angle, a completed drag is treated as no rotation at
# all. Unlike MoveTool's epsilon, this isn't compensating for
# ray-cast noise (there is none here -- angle_degrees is plain
# arithmetic on screen coordinates) -- it just rejects a
# press-release with no meaningful drag.
#
_ZERO_ANGLE_EPSILON_DEGREES = 0.01


class RotateTool:
    """Tracks one in-progress brick-rotation gesture."""

    def __init__(self):

        self._brick_id: int | None = None
        self._original_rotation: glm.quat | None = None
        self._start_screen_x: float | None = None

    @property
    def is_dragging(self) -> bool:
        return self._brick_id is not None

    @property
    def brick_id(self) -> int | None:
        return self._brick_id

    def begin(
        self,
        brick: SceneBrick,
        screen_x: float,
    ) -> None:
        """Start rotating brick, anchored at the screen-space x of the
        initial press."""

        self._brick_id = brick.id
        self._original_rotation = brick.rotation
        self._start_screen_x = screen_x

    def _angle_degrees(
        self,
        screen_x: float,
    ) -> float:

        return (
            (screen_x - self._start_screen_x)
            * _ROTATE_SENSITIVITY
        )

    def update(
        self,
        screen_x: float,
    ) -> glm.quat:
        """Return the live preview rotation for the current screen_x.
        Only meaningful while is_dragging is True."""

        delta = glm.angleAxis(
            glm.radians(self._angle_degrees(screen_x)),
            _ROTATION_AXIS,
        )

        return glm.normalize(delta * self._original_rotation)

    def finish(
        self,
        screen_x: float,
    ) -> tuple[int, glm.quat] | None:
        """
        End the drag and clear temporary state. Returns
        (brick_id, final_rotation) if the drag rotated the brick by
        more than a negligible angle, or None if it didn't -- either
        way, the drag is over once this returns. Never touches Scene;
        the caller decides what to do with the result.
        """

        brick_id = self._brick_id
        angle_degrees = self._angle_degrees(screen_x)
        final_rotation = self.update(screen_x)

        self._reset()

        if abs(angle_degrees) < _ZERO_ANGLE_EPSILON_DEGREES:
            return None

        return brick_id, final_rotation

    def cancel(self) -> None:
        """Abandon the current drag without returning a result."""

        self._reset()

    def _reset(self) -> None:

        self._brick_id = None
        self._original_rotation = None
        self._start_screen_x = None
