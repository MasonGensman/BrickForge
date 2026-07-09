from dataclasses import dataclass, field

import numpy as np


@dataclass
class Camera:
    """Simple orbit camera."""

    distance: float = 15.0
    yaw: float = 45.0
    pitch: float = 30.0

    target: np.ndarray = field(
        default_factory=lambda: np.array(
            [0.0, 0.0, 0.0],
            dtype=float,
        )
    )

    def zoom(self, delta: float):
        self.distance = max(1.0, self.distance + delta)

    def rotate(self, dx: float, dy: float):
        self.yaw += dx
        self.pitch += dy
        self.pitch = max(-89.0, min(89.0, self.pitch))