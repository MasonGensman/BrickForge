"""
BrickForge Scene
"""

from brickforge.engine.scene_brick import SceneBrick


class Scene:
    """Holds the SceneBrick instances placed in the current scene."""

    def __init__(self):

        self.bricks: list[SceneBrick] = []

    def add(
        self,
        brick: SceneBrick,
    ) -> None:

        self.bricks.append(brick)

    def __iter__(self):

        return iter(self.bricks)
