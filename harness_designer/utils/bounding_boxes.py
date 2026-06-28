# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np

from ..geometry import point as _point


def compute_aabb(verts: np.ndarray) -> tuple[_point.Point, _point.Point]:
    """
    Compute an axis-aligned bounding box from vertex positions.

    :param verts: Vertex positions.
    :type verts: np.ndarray
    :returns: Minimum and maximum corner points.
    :rtype: tuple[_point.Point, _point.Point]
    """

    p1 = _point.Point(*verts.min(axis=0))
    p2 = _point.Point(*verts.max(axis=0))
    return p1, p2


def compute_obb(p1: _point.Point, p2: _point.Point) -> np.ndarray:
    """
    Construct bounding-box corner coordinates from two opposite points.

    :param p1: Minimum corner.
    :type p1: _point.Point
    :param p2: Maximum corner.
    :type p2: _point.Point
    :returns: Eight corner coordinates.
    :rtype: numpy.ndarray
    """

    x1, y1, z1 = p1.as_float
    x2, y2, z2 = p2.as_float

    corners = np.array([
                [x1, y1, z1],  # 0: bottom-left-front
                [x2, y1, z1],  # 1: bottom-right-front
                [x2, y2, z1],  # 2: top-right-front
                [x1, y2, z1],  # 3: top-left-front
                [x1, y1, z2],  # 4: bottom-left-back
                [x2, y1, z2],  # 5: bottom-right-back
                [x2, y2, z2],  # 6: top-right-back
                [x1, y2, z2],  # 7: top-left-back
            ], dtype=np.float32)
    return corners


def adjust_aabb(aabb: np.ndarray) -> np.ndarray:
    """
    Normalise an AABB array to explicit min/max rows.

    :param aabb: Bounding-box coordinates.
    :type aabb: numpy.ndarray
    :returns: Two-row array containing min and max coordinates.
    :rtype: numpy.ndarray
    """

    return np.array([aabb.min(axis=0), aabb.max(axis=0)], dtype=np.float32)
