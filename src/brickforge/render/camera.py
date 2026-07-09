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

    pan_speed: float = 0.02

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

    def orbit(
        self,
        delta_x: float,
        delta_y: float,
    ):

        self.yaw += delta_x * 0.35

        self.pitch -= delta_y * 0.35

        self.pitch = max(
            -89.0,
            min(
                89.0,
                self.pitch,
            ),
        )

    def zoom(
        self,
        delta: float,
    ):

        self.distance = max(
            2.0,
            self.distance + delta,
        )

    def pan(
        self,
        delta_x: float,
        delta_y: float,
    ):

        yaw = glm.radians(self.yaw)

        right = glm.vec3(
            glm.cos(yaw),
            0.0,
            -glm.sin(yaw),
        )

        up = glm.vec3(
            0.0,
            1.0,
            0.0,
        )

        self.target -= (
            right * delta_x * self.pan_speed
        )

        self.target += (
            up * delta_y * self.pan_speed
        )

    def reset(self):

        self.distance = 15.0
        self.yaw = 45.0
        self.pitch = 30.0

        self.target = glm.vec3(
            0.0,
            0.0,
            0.0,
        )