# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from ..geometry import point as _point


class SnapPool:

    def __init__(self, objects: list, snap_points: list["_point.Point"],
                 threshold: float = 5.00):

        self.objects = objects
        self.numpy_points = np.array([point.as_float for point in snap_points], dtype=np.float32).reshape(-1, 3)
        self.threshold_sq = threshold ** 2

    def query(self, pos: "_point.Point"):
        if not self.objects:
            return None

        world_pos = pos.as_numpy

        diff = self.numpy_points - world_pos
        dist_sq = (diff * diff).sum(axis=1)
        idx = int(dist_sq.argmin())

        if dist_sq[idx] <= self.threshold_sq:
            return self.objects[idx]
