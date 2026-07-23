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

    def clear(self) -> None:

        self.bricks = []

    def iterate(self):

        return iter(self.bricks)

    def __iter__(self):

        return iter(self.bricks)
