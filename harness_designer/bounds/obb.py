# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np

from . import array_pool as _array_pool
from .. import check_types as _check_types


class OBB(_array_pool.ArrayPool):
    """Oriented bounding box pool -- each row is an ``(8, 3)`` array of
    corners, ordered per ``utils.bounding_boxes.compute_obb``: corner 0
    = (x1,y1,z1), 1 toggles x, 3 toggles y, 4 toggles z.
    """

    def __init__(self):
        super().__init__([[0.0] * 3] * 8)

    @_check_types.do
    def _vectorized_ray_test(self, rows: np.ndarray, origin: np.ndarray,
                              direc: np.ndarray, t0: float, t1: float):
        """Vectorized slab test against each row's own oriented edge
        axes -- same math as ``gl.object_picker._ray_intersect_obb``,
        batched over every row in *rows* at once instead of looping in
        Python.
        """
        n = rows.shape[0]
        c0 = rows[:, 0, :]
        c1 = rows[:, 1, :]
        c3 = rows[:, 3, :]
        c4 = rows[:, 4, :]

        edges = (c1 - c0, c3 - c0, c4 - c0)
        center = c0 + 0.5 * (edges[0] + edges[1] + edges[2])

        tmin = np.full(n, t0, dtype=np.float64)
        tmax = np.full(n, t1, dtype=np.float64)
        hit = np.ones(n, dtype=bool)

        p = center - origin  # (N, 3)

        for edge in edges:
            length = np.linalg.norm(edge, axis=1)
            degenerate = length < 1e-8

            axis = np.zeros_like(edge)
            safe_length = np.where(degenerate, 1.0, length)
            axis[~degenerate] = edge[~degenerate] / safe_length[~degenerate, None]
            half_extent = length * 0.5

            e = np.einsum('ij,ij->i', axis, p)
            f = axis.dot(direc)

            parallel = np.abs(f) <= 1e-8
            safe_f = np.where(parallel, 1.0, f)

            t_a = (e - half_extent) / safe_f
            t_b = (e + half_extent) / safe_f
            t_near = np.minimum(t_a, t_b)
            t_far = np.maximum(t_a, t_b)

            tmin = np.where(parallel, tmin, np.maximum(tmin, t_near))
            tmax = np.where(parallel, tmax, np.minimum(tmax, t_far))

            # Parallel to this slab and outside it -- dead on arrival.
            hit &= ~(parallel & (np.abs(e) > half_extent))
            # A degenerate (near-zero-length) edge can't define an axis.
            hit &= ~degenerate

        hit &= (tmin <= tmax) & (tmax >= 0.0)
        return hit, tmin
