"""
BrickForge Scene
"""

from brickforge.engine.scene_brick import SceneBrick


class Scene:
    """Holds the SceneBrick instances placed in the current scene."""

    def __init__(self):

        self.bricks: list[SceneBrick] = []

    def add_brick(
        self,
        brick: SceneBrick,
    ) -> None:

        self.bricks.append(brick)

    def remove_brick(
        self,
        brick_id: int,
    ) -> None:

        self.bricks = [
            brick
            for brick in self.bricks
            if brick.id != brick_id
        ]

    def get(
        self,
        brick_id: int,
    ) -> SceneBrick | None:
        """Look up a brick by id. Read-only -- never mutates the Scene."""

        for brick in self.bricks:

            if brick.id == brick_id:
                return brick

        return None

    def next_available_id(self) -> int:
        """
        Return an id guaranteed not to collide with any brick
        currently in this Scene. Read-only -- never mutates the
        Scene, and never reserves the returned id; a caller that
        doesn't use it may call this again and get the same value.

        Scene-local, not globally unique across the app's lifetime --
        every existing id-assignment scheme in this codebase (each
        generation mode, the demo bricks) already restarts freely
        with each new Scene, so this doesn't introduce a new kind of
        uniqueness guarantee, only extends the existing one to a
        fresh id a caller didn't already have in hand.
        """

        return max(
            (brick.id for brick in self.bricks),
            default=-1,
        ) + 1

    def clear(self) -> None:

        self.bricks = []

    def iterate(self):

        return iter(self.bricks)

    def __iter__(self):

        return iter(self.bricks)
