# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Sphere mesh generation helpers.

The generated sphere uses latitude/longitude-style tessellation and is later
converted into a cached :class:`harness_designer.gl.vbo.PooledVBOHandler`.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.PooledVBOHandler = None


def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached sphere VBO.

    :returns: Cached VBO data for a default sphere mesh.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, resolution=40)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'sphere', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(radius=1.0, resolution=None) -> tuple[np.ndarray, np.ndarray]:
    """Create vertices and faces for a sphere mesh.

    :param radius: Sphere radius.
    :type radius: float
    :param resolution: Number of vertical subdivisions. If ``None``, a value
        derived from ``radius`` is used.
    :type resolution: int or None
    :returns: Vertex and triangle index arrays for the sphere mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    if resolution is None:
        resolution = int(max(20.0, _utils.remap(radius, 0.35, 19.0, 20.0, 30.0)))

    count = 2 * resolution * (resolution - 1) + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float32)

    vertices[0] = np.array([0.0, 0.0, radius], dtype=np.float32)
    vertices[1] = np.array([0.0, 0.0, -radius], dtype=np.float32)

    step = math.pi / float(resolution)

    for i in range(1, resolution, 1):
        alpha = step * i
        base = int(2 + 2 * resolution * (i - 1))
        for j in range(2 * resolution):
            theta = step * j

            alpha_sin = math.sin(alpha)
            alpha_cos = math.cos(alpha)
            theta_sin = math.sin(theta)
            theta_cos = math.cos(theta)

            vertices[base + j] = np.array(
                [alpha_sin * theta_cos,
                 alpha_sin * theta_sin,
                 alpha_cos], dtype=np.float32) * radius

    # Triangles for poles.
    faces = []

    for j in range(2 * resolution):
        j1 = (j + 1) % (2 * resolution)
        base = 2
        faces.append([0, base + j, base + j1])
        base = 2 + 2 * resolution * (resolution - 2)
        faces.append([1, base + j1, base + j])

    # Triangles for non-polar region.
    for i in range(1, resolution - 1, 1):
        base1 = 2 + 2 * resolution * (i - 1)
        base2 = base1 + 2 * resolution
        for j in range(2 * resolution):
            j1 = int((j + 1) % (2 * resolution))
            faces.append([base2 + j, base1 + j1, base1 + j])
            faces.append([base2 + j, base2 + j1, base1 + j1])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
