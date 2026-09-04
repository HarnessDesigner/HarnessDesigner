# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..geometry import point as _point


class SnapPool:

    @_check_types.do
    def __init__(self, objects: list, snap_points: list["_point.Point"],
                 threshold: float = 5.00):

        self.objects = objects
        self.numpy_points = np.array([point.as_float for point in snap_points], dtype=np.float32).reshape(-1, 3)
        self.threshold_sq = threshold ** 2

    @_check_types.do
    def query(self, pos: "_point.Point"):
        if not self.objects:
            return None

        world_pos = pos.as_numpy

        diff = self.numpy_points - world_pos
        dist_sq = (diff * diff).sum(axis=1)
        idx = int(dist_sq.argmin())

        if dist_sq[idx] <= self.threshold_sq:
            return self.objects[idx]

    @_check_types.do
    def query_ray(self, origin: np.ndarray, direction: np.ndarray):
        """Snap by perpendicular distance from each point to the ray
        (*origin*, *direction*) instead of distance to a single fixed
        point.

        Point-to-point (see :meth:`query`) only works when the caller's
        "current position" estimate is already at the same depth as the
        real geometry being snapped to -- for a screen-space cursor over
        a perspective view, that's only ever true by coincidence unless
        the estimate came from unprojecting onto that geometry's own
        depth specifically (see :meth:`~harness_designer.gl.canvas_base.
        camera_base.CameraBase.get_mouse_ray`'s own docstring for why
        :meth:`~....camera_base.CameraBase.get_position_on_focal_plane`
        -- an arbitrary focal-plane depth, unrelated to any particular
        candidate's real position -- isn't that). Measuring against the
        ray itself instead needs no depth assumption at all: a point
        can be arbitrarily far along the view direction and still
        register as "under the cursor" as long as it's laterally close
        to the ray.
        """
        if not self.objects:
            return None

        to_points = self.numpy_points - origin
        t = to_points @ direction
        closest_on_ray = origin + np.outer(t, direction)

        diff = self.numpy_points - closest_on_ray
        dist_sq = (diff * diff).sum(axis=1)
        idx = int(dist_sq.argmin())

        if dist_sq[idx] <= self.threshold_sq:
            return self.objects[idx]
