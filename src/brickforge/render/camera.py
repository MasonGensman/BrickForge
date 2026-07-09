"""
BrickForge Camera
"""

from dataclasses import dataclass, field

import glm


@dataclass
class Camera:
    """Orbit camera."""

    distance: float = 15.0

    yaw: float = 45.0
    pitch: float = 30.0

    target: glm.vec3 = field(
        default_factory=lambda: glm.vec3(
            0.0,
            0.0,
            0.0,
        )
    )

    fov: float = 45.0

    near: float = 0.1
    far: float = 1000.0

    def view_matrix(self):

        yaw = glm.radians(self.yaw)
        pitch = glm.radians(self.pitch)

        position = glm.vec3(
            self.distance * glm.cos(pitch) * glm.sin(yaw),
            self.distance * glm.sin(pitch),
            self.distance * glm.cos(pitch) * glm.cos(yaw),
        )

        return glm.lookAt(
            position + self.target,
            self.target,
            glm.vec3(0.0, 1.0, 0.0),
        )

    def projection_matrix(
        self,
        width: int,
        height: int,
    ):

        aspect = max(width, 1) / max(height, 1)

        return glm.perspective(
            glm.radians(self.fov),
            aspect,
            self.near,
            self.far,
        )

    def zoom(
        self,
        delta: float,
    ):

        self.distance = max(
            1.0,
            self.distance + delta,
        )