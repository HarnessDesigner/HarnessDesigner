# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Rotation and move math over many points / angles at once.

These are the array versions of what ``Quaternion`` / ``Angle`` / ``Point`` do
one object at a time, for the pooled storage in :mod:`.slot_pool`: a housing
rotates all of its points and angles with a few calls here instead of one
Python object at a time. They work on float64 internally (the pooled data is
float32, the same as the stored data of the single-object classes) and return
float64; the caller writes the result into the pool, which rounds it to float32.

Conventions match the single-object classes:

* A quaternion is ``(w, x, y, z)``.
* :func:`compose` is ``Quaternion.__add__``: ``a + b`` is ``b ⊗ a`` (``b`` applied
  in world space, before ``a``'s own rotation), normalised.
* The matrix is the column-vector matrix of ``Quaternion.as_matrix``.
* The Euler order and the continuity wrap are those of
  ``pjt_housing._euler_from_matrix_continuous`` (YXZ: pitch, yaw, roll in
  degrees, each kept within +-180 of the previous value).

Where they are used and why: the module docstring of ``database/project_db/pjt_housing.py``
("POOLED 3D STORAGE", section 9), and the rotation gizmo's protractor rings, which place
their degree labels with :func:`quaternions_from_matrices`, :func:`quaternions_from_directions`,
:func:`rotate_vectors` and :func:`compose` (``rotation_handlers/rotation_ring/_protractor_base.py``).
"""

import numpy as np

from .. import check_types as _check_types


@_check_types.do
def compose(base: np.ndarray, other: np.ndarray) -> np.ndarray:
    """
    ``other ⊗ base`` for quaternions of shape ``(..., 4)`` (they broadcast),
    normalised: the array form of ``base + other`` on ``Quaternion``.

    :param base: The quaternion(s) ``a`` of ``a + b``.
    :type base: :class:`numpy.ndarray`
    :param other: The quaternion(s) ``b`` of ``a + b``.
    :type other: :class:`numpy.ndarray`
    :returns: The normalised product, float64.
    :rtype: :class:`numpy.ndarray`
    """

    wa, xa, ya, za = base[..., 0], base[..., 1], base[..., 2], base[..., 3]
    wb, xb, yb, zb = other[..., 0], other[..., 1], other[..., 2], other[..., 3]

    product = np.stack([wb * wa - xb * xa - yb * ya - zb * za,
                        wb * xa + xb * wa + yb * za - zb * ya,
                        wb * ya - xb * za + yb * wa + zb * xa,
                        wb * za + xb * ya - yb * xa + zb * wa], axis=-1)

    return product / np.linalg.norm(product, axis=-1, keepdims=True)


@_check_types.do
def to_matrices(q: np.ndarray) -> np.ndarray:
    """
    Column-vector rotation matrices of quaternions of shape ``(..., 4)``
    (unit length), the array form of ``Quaternion.as_matrix``.

    :param q: Unit quaternions.
    :type q: :class:`numpy.ndarray`
    :returns: Matrices of shape ``(..., 3, 3)``, float64.
    :rtype: :class:`numpy.ndarray`
    """

    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]

    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    m = np.empty(q.shape[:-1] + (3, 3), dtype=np.float64)

    m[..., 0, 0] = 1.0 - 2.0 * (yy + zz)
    m[..., 0, 1] = 2.0 * (xy - wz)
    m[..., 0, 2] = 2.0 * (xz + wy)

    m[..., 1, 0] = 2.0 * (xy + wz)
    m[..., 1, 1] = 1.0 - 2.0 * (xx + zz)
    m[..., 1, 2] = 2.0 * (yz - wx)

    m[..., 2, 0] = 2.0 * (xz - wy)
    m[..., 2, 1] = 2.0 * (yz + wx)
    m[..., 2, 2] = 1.0 - 2.0 * (xx + yy)

    return m


@_check_types.do
def euler_from_matrices(matrices: np.ndarray, previous: np.ndarray) -> np.ndarray:
    """
    YXZ Euler angles in degrees of ``(n, 3, 3)`` matrices, each wrapped to
    stay within +-180 of the matching row of ``previous``: the array form of
    ``pjt_housing._euler_from_matrix_continuous``.

    :param matrices: Rotation matrices (columns are right, up, forward).
    :type matrices: :class:`numpy.ndarray`
    :param previous: Previous Euler angles in degrees, ``(n, 3)``.
    :type previous: :class:`numpy.ndarray`
    :returns: ``(n, 3)`` array of pitch, yaw, roll, float64.
    :rtype: :class:`numpy.ndarray`
    """

    pitch = np.degrees(np.arcsin(np.clip(-matrices[:, 1, 2], -1.0, 1.0)))
    yaw = np.degrees(np.arctan2(matrices[:, 0, 2], matrices[:, 2, 2]))
    roll = np.degrees(np.arctan2(matrices[:, 1, 0], matrices[:, 1, 1]))

    euler = np.stack([pitch, yaw, roll], axis=1)

    return euler - 360.0 * np.floor((euler - previous + 180.0) / 360.0)


@_check_types.do
def rotate_points(points: np.ndarray, center: np.ndarray, delta: np.ndarray) -> np.ndarray:
    """
    Rotate ``(n, 3)`` points about ``center`` by the unit quaternion ``delta``,
    the array form of what ``PJTHousing._update_angle3d`` does to its points.

    :param points: The points.
    :type points: :class:`numpy.ndarray`
    :param center: The point to rotate about, ``(3,)``.
    :type center: :class:`numpy.ndarray`
    :param delta: The rotation ``(w, x, y, z)``, ``(4,)``.
    :type delta: :class:`numpy.ndarray`
    :returns: The rotated points, float64.
    :rtype: :class:`numpy.ndarray`
    """

    relative = points.astype(np.float64) - center
    vector = delta[1:].astype(np.float64)
    cross = np.cross(vector, relative)

    return relative + 2.0 * float(delta[0]) * cross + 2.0 * np.cross(vector, cross) + center


@_check_types.do
def rotate_vectors(q: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """
    Rotate each row of *vectors* by the matching unit quaternion of *q*: the
    array form of ``Point @ Angle`` (``R @ v`` with the column-vector matrix).

    :param q: Unit quaternions ``(w, x, y, z)``, ``(n, 4)`` (or ``(4,)`` for
        one rotation applied to every row).
    :type q: :class:`numpy.ndarray`
    :param vectors: The vectors, ``(n, 3)``.
    :type vectors: :class:`numpy.ndarray`
    :returns: The rotated vectors, float64.
    :rtype: :class:`numpy.ndarray`
    """

    u = q[..., 1:].astype(np.float64)
    w = q[..., 0:1].astype(np.float64)
    v = vectors.astype(np.float64)

    cross = np.cross(u, v)

    return v + 2.0 * w * cross + 2.0 * np.cross(u, cross)


@_check_types.do
def quaternions_from_directions(directions: np.ndarray) -> np.ndarray:
    """
    The shortest-arc rotation that takes +Z to each unit vector of
    *directions*: the array form of ``Angle.from_direction`` (``w = 1 + dot``,
    ``xyz = cross(z, d)``, normalised; exactly antiparallel is the half turn
    about X, the same fixed choice ``from_direction`` makes).

    :param directions: Unit vectors, ``(n, 3)``.
    :type directions: :class:`numpy.ndarray`
    :returns: Unit quaternions ``(w, x, y, z)``, ``(n, 4)``, float64.
    :rtype: :class:`numpy.ndarray`
    """

    d = directions.astype(np.float64)
    count = d.shape[0]

    q = np.empty((count, 4), dtype=np.float64)

    q[:, 0] = 1.0 + d[:, 2]
    q[:, 1] = -d[:, 1]
    q[:, 2] = d[:, 0]
    q[:, 3] = 0.0

    antiparallel = d[:, 2] < -1.0 + 0.0001
    q[antiparallel] = (0.0, 1.0, 0.0, 0.0)

    return q / np.linalg.norm(q, axis=1, keepdims=True)


@_check_types.do
def quaternions_from_matrices(matrices: np.ndarray) -> np.ndarray:
    """
    Unit quaternions of ``(n, 3, 3)`` column-vector rotation matrices (the
    inverse of :func:`to_matrices`), by the largest-diagonal-term method so
    no case divides by something near zero. The sign of a quaternion is
    arbitrary (``q`` and ``-q`` are the same rotation); ``w`` is not forced
    positive here.

    :param matrices: Rotation matrices, ``(n, 3, 3)``.
    :type matrices: :class:`numpy.ndarray`
    :returns: Unit quaternions ``(w, x, y, z)``, ``(n, 4)``, float64.
    :rtype: :class:`numpy.ndarray`
    """

    m = matrices.astype(np.float64)

    m00, m01, m02 = m[:, 0, 0], m[:, 0, 1], m[:, 0, 2]
    m10, m11, m12 = m[:, 1, 0], m[:, 1, 1], m[:, 1, 2]
    m20, m21, m22 = m[:, 2, 0], m[:, 2, 1], m[:, 2, 2]

    trace = m00 + m11 + m22

    tiny = 1e-12

    s_w = np.sqrt(np.maximum(1.0 + trace, tiny)) * 2.0
    s_x = np.sqrt(np.maximum(1.0 + m00 - m11 - m22, tiny)) * 2.0
    s_y = np.sqrt(np.maximum(1.0 + m11 - m00 - m22, tiny)) * 2.0
    s_z = np.sqrt(np.maximum(1.0 + m22 - m00 - m11, tiny)) * 2.0

    by_w = np.stack([s_w / 4.0, (m21 - m12) / s_w, (m02 - m20) / s_w, (m10 - m01) / s_w], axis=1)
    by_x = np.stack([(m21 - m12) / s_x, s_x / 4.0, (m01 + m10) / s_x, (m02 + m20) / s_x], axis=1)
    by_y = np.stack([(m02 - m20) / s_y, (m01 + m10) / s_y, s_y / 4.0, (m12 + m21) / s_y], axis=1)
    by_z = np.stack([(m10 - m01) / s_z, (m02 + m20) / s_z, (m12 + m21) / s_z, s_z / 4.0], axis=1)

    use_w = trace > 0.0
    use_x = ~use_w & (m00 >= m11) & (m00 >= m22)
    use_y = ~use_w & ~use_x & (m11 >= m22)

    q = np.where(use_w[:, None], by_w,
                 np.where(use_x[:, None], by_x,
                          np.where(use_y[:, None], by_y, by_z)))

    return q / np.linalg.norm(q, axis=1, keepdims=True)
