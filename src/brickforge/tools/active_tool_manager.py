"""
StudWorks Active Tool Manager

Centralizes editing-tool ownership and dispatch, replacing implicit
mouse-button branching in ViewportWidget with explicit tool routing.
Owned by ViewportWidget (raw mouse events are viewport-local, and
MainWindow never needs to know *how* a drag was interpreted -- only
its outcome), continuing the ownership already established for
MoveTool/RotateTool in Packages 029-030, not changing it.

A deliberate, documented difference from MoveTool/RotateTool
themselves: this class *does* accept a Renderer reference (passed per
call, never stored) and references Qt.MouseButton. MoveTool/RotateTool
are pure algorithmic state machines with no rendering or UI-framework
awareness (still true, still verified via AST); ActiveToolManager is a
coordination layer, and coordinators legitimately depend on what they
coordinate -- the same relationship Renderer.pick() already has with
BrickManager/Camera.

Tool INPUT shapes remain independent by design, not oversight:
MoveTool consumes a world-space point (from a ray/plane intersection
that can degenerate to None), RotateTool a raw screen-space float
with no degenerate case at all. Unifying those into a single input
type would either be a lossy artificial common denominator or force
a Renderer dependency into the tools themselves, undoing a property
both prior packages explicitly verified and valued. What genuinely
*is* shared across both tools today -- confirmed by their existing,
already-duplicated MainWindow handlers, not invented for this
package -- is captured in ToolResult below: both tools produce
"one brick id, one changed SceneBrick field, one new value."
"""

from dataclasses import dataclass

from PySide6.QtCore import Qt

from brickforge.render.renderer import Renderer, ScenePreview
from brickforge.tools.move_tool import MoveTool
from brickforge.tools.rotate_tool import RotateTool


@dataclass(frozen=True, slots=True)
class ToolResult:
    """
    The outcome of a completed tool interaction: replace one field of
    one SceneBrick. Fits every tool that exists today (Move changes
    position, Rotate changes rotation) because both are single-field
    replacements -- not a guess at what a future Delete/Duplicate
    tool (which don't fit this shape at all) will need.
    """

    brick_id: int
    field: str
    value: object
    verb: str


class ActiveToolManager:
    """Owns MoveTool and RotateTool, and dispatches to whichever is active."""

    def __init__(self):

        self._move_tool = MoveTool()
        self._rotate_tool = RotateTool()
        self._active: MoveTool | RotateTool | None = None

    @property
    def is_dragging(self) -> bool:
        return self._active is not None

    @property
    def active_tool_name(self) -> str | None:

        if self._active is self._move_tool:
            return "move"

        if self._active is self._rotate_tool:
            return "rotate"

        return None

    def try_begin(
        self,
        button,
        renderer: Renderer,
        brick_id: int | None,
        screen_x: float,
        screen_y: float,
    ) -> bool:
        """
        Attempt to begin a drag for the brick under the cursor.
        Returns True if a tool began (the caller should treat the
        press as consumed); False if nothing did -- no brick was
        picked, the picked brick isn't the current selection, the
        button isn't tool-bound, or (Move only) the initial ray
        missed the ground plane. The caller is expected to have
        already called renderer.pick() once and pass its result in,
        rather than this method picking again.
        """

        if brick_id is None or brick_id != renderer.selected_id:
            return False

        brick = renderer.scene.get(brick_id)

        if button == Qt.LeftButton:

            grab_point = renderer.project_to_ground(
                screen_x,
                screen_y,
                brick.position.y,
            )

            if grab_point is None:
                return False

            self._move_tool.begin(brick, grab_point)
            self._active = self._move_tool

            return True

        if button == Qt.RightButton:

            self._rotate_tool.begin(brick, screen_x)
            self._active = self._rotate_tool

            return True

        return False

    def update(
        self,
        renderer: Renderer,
        screen_x: float,
        screen_y: float,
    ) -> None:
        """Update the active tool's preview. No-op if nothing is dragging."""

        if self._active is self._move_tool:

            brick = renderer.scene.get(self._move_tool.brick_id)

            grab_point = renderer.project_to_ground(
                screen_x,
                screen_y,
                self._move_tool.plane_y,
            )

            if grab_point is not None:

                renderer.set_preview(
                    ScenePreview(
                        brick_id=self._move_tool.brick_id,
                        position=self._move_tool.update(grab_point),
                        rotation=brick.rotation,
                    )
                )

        elif self._active is self._rotate_tool:

            brick = renderer.scene.get(self._rotate_tool.brick_id)

            renderer.set_preview(
                ScenePreview(
                    brick_id=self._rotate_tool.brick_id,
                    position=brick.position,
                    rotation=self._rotate_tool.update(screen_x),
                )
            )

    def finish(
        self,
        renderer: Renderer,
        screen_x: float,
        screen_y: float,
    ) -> ToolResult | None:
        """
        End the active drag. Always clears the renderer preview and
        the active tool, whether or not a real result was produced.
        Returns None if nothing was dragging, if the drag ended with
        no meaningful movement, or (Move only) if the final ray
        missed the ground plane.
        """

        result = None

        if self._active is self._move_tool:

            grab_point = renderer.project_to_ground(
                screen_x,
                screen_y,
                self._move_tool.plane_y,
            )

            if grab_point is not None:
                move_result = self._move_tool.finish(grab_point)
            else:
                self._move_tool.cancel()
                move_result = None

            if move_result is not None:

                brick_id, position = move_result

                result = ToolResult(
                    brick_id=brick_id,
                    field="position",
                    value=position,
                    verb="Moved",
                )

        elif self._active is self._rotate_tool:

            rotate_result = self._rotate_tool.finish(screen_x)

            if rotate_result is not None:

                brick_id, rotation = rotate_result

                result = ToolResult(
                    brick_id=brick_id,
                    field="rotation",
                    value=rotation,
                    verb="Rotated",
                )

        renderer.set_preview(None)
        self._active = None

        return result

    def cancel(self) -> None:
        """Abandon the active drag without returning a result."""

        if self._active is self._move_tool:
            self._move_tool.cancel()

        elif self._active is self._rotate_tool:
            self._rotate_tool.cancel()

        self._active = None
