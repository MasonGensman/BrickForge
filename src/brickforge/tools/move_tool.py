"""
StudWorks Move Tool

An interaction subsystem, not a rendering or Scene-mutation one:
MoveTool tracks the transient state of a single brick-drag gesture
and does pure vector math over already-computed world-space points.
It has no reference to Renderer, Scene, or the Transform package --
it never draws anything and never touches Scene or SceneBrick.

The owning widget (ViewportWidget) is responsible for turning screen
coordinates into the world-space points this class consumes (via
Renderer.project_to_ground()), and for turning finish()'s result into
an actual Scene edit -- that happens later, in MainWindow, through
transform.replace_brick() and the scene activation helper
(Package_029). MoveTool's finish() does not commit anything to Scene;
it only ends the drag interaction, returns the requested final
position, and clears temporary state.
"""

import glm

from brickforge.engine.scene_brick import SceneBrick

#
# Below this distance, a completed drag is treated as no movement at
# all -- swallows floating-point noise from the ray/plane math (a
# perfectly still press-release reproduces the same world point to
# within float precision, not exactly bit-for-bit) without masking
# any real mouse-driven drag, which moves by many LDraw units.
#
_ZERO_DISTANCE_EPSILON = 1e-4


class MoveTool:
    """Tracks one in-progress brick-drag gesture."""

    def __init__(self):

        self._brick_id: int | None = None
        self._original_position: glm.vec3 | None = None
        self._grab_offset: glm.vec3 | None = None

    @property
    def is_dragging(self) -> bool:
        return self._brick_id is not None

    @property
    def brick_id(self) -> int | None:
        return self._brick_id

    @property
    def plane_y(self) -> float:
        """The fixed height the drag moves along, captured at begin().
        Only meaningful while is_dragging is True."""

        return self._original_position.y

    def begin(
        self,
        brick: SceneBrick,
        grab_point: glm.vec3,
    ) -> None:
        """
        Start dragging brick, anchored at grab_point (the world-space
        point on the ground plane under the initial click). The
        offset between grab_point and the brick's own origin is
        preserved for the rest of the drag, so the brick doesn't jump
        to snap its origin under the cursor.
        """

        self._brick_id = brick.id
        self._original_position = brick.position
        self._grab_offset = brick.position - grab_point

    def update(
        self,
        grab_point: glm.vec3,
    ) -> glm.vec3:
        """Return the live preview position for the current grab_point.
        Only meaningful while is_dragging is True."""

        return grab_point + self._grab_offset

    def finish(
        self,
        grab_point: glm.vec3,
    ) -> tuple[int, glm.vec3] | None:
        """
        End the drag and clear temporary state. Returns
        (brick_id, final_position) if the drag moved the brick by
        more than a negligible distance, or None if it didn't --
        either way, the drag is over once this returns. Never touches
        Scene; the caller decides what to do with the result.
        """

        brick_id = self._brick_id
        original_position = self._original_position
        final_position = self.update(grab_point)

        self._reset()

        if glm.length(final_position - original_position) < _ZERO_DISTANCE_EPSILON:
            return None

        return brick_id, final_position

    def cancel(self) -> None:
        """Abandon the current drag without returning a result."""

        self._reset()

    def _reset(self) -> None:

        self._brick_id = None
        self._original_position = None
        self._grab_offset = None
