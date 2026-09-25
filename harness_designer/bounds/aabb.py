# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np

from . import array_pool as _array_pool
from .. import check_types as _check_types


class AABB(_array_pool.ArrayPool):
    """Axis-aligned bounding box pool -- each row is a ``(2, 3)`` array,
    ``row[0]`` the min corner and ``row[1]`` the max corner.
    """

    def __init__(self) -> None:
        super().__init__([[0.0] * 3] * 2)

    @_check_types.do
    def extent(self) -> tuple[np.ndarray, np.ndarray] | None:
        """The box enclosing every live box in the pool: the outermost
        min and max corner on each axis, as float64 ``(3,)`` arrays.

        ``None`` if the pool holds nothing usable. Skips non-finite
        rows, and all-zero rows -- an object with no real geometry in
        this view (e.g. a placeholder) still owns a slot, but its row is
        never written, so it would otherwise drag the extent to the
        origin.
        """
        rows = self.snapshot_live().astype(np.float64)
        if not rows.shape[0]:
            return None

        usable = np.isfinite(rows).all(axis=(1, 2)) & rows.any(axis=(1, 2))
        rows = rows[usable]
        if not rows.shape[0]:
            return None

        return rows[:, 0, :].min(axis=0), rows[:, 1, :].max(axis=0)

    @_check_types.do
    def _vectorized_ray_test(self, rows: np.ndarray, origin: np.ndarray,
                              direc: np.ndarray, t0: float, t1: float) -> tuple[np.ndarray, np.ndarray]:
        """Vectorized slab test -- same math as
        ``gl.object_picker._ray_intersect_aabb``, batched over every row
        in *rows* at once instead of looping in Python.
        """
        n = rows.shape[0]
        aabb_min = rows[:, 0, :]
        aabb_max = rows[:, 1, :]

        tmin = np.full(n, t0, dtype=np.float64)
        tmax = np.full(n, t1, dtype=np.float64)
        hit = np.ones(n, dtype=bool)

        for i in range(3):
            d = float(direc[i])
            if abs(d) > 1e-8:
                inv_d = 1.0 / d
                t_a = (aabb_min[:, i] - origin[i]) * inv_d
                t_b = (aabb_max[:, i] - origin[i]) * inv_d
                t_near = np.minimum(t_a, t_b)
                t_far = np.maximum(t_a, t_b)
                tmin = np.maximum(tmin, t_near)
                tmax = np.minimum(tmax, t_far)
            else:
                # Ray parallel to this slab -- only survives where the
                # origin is already inside it on this axis.
                outside = (origin[i] < aabb_min[:, i]) | (origin[i] > aabb_max[:, i])
                hit &= ~outside

        hit &= (tmin <= tmax) & (tmax >= 0.0)
        return hit, tmin
