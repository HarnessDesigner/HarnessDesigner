# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cylinder mesh generation helpers.

The generated mesh is centered around the origin before being converted into a
cached :class:`harness_designer.gl.vbo.VBOHandler`.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    """Create or return the cached cylinder VBO.

    :returns: Cached VBO data for a default cylinder mesh.
    :rtype: :class:`harness_designer.gl.vbo.VBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 1.0, 360, 1)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.VBOHandler(
            'cylinder', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(radius, length, resolution=None, split=None) -> tuple[np.ndarray, np.ndarray]:
    """Create vertices and faces for a cylindrical side wall.

    The current implementation generates only the curved surface; end caps are
    not added.

    :param radius: Cylinder radius.
    :type radius: float
    :param length: Cylinder length along the Z axis.
    :type length: float
    :param resolution: Number of samples around each ring. If ``None``, a value
        derived from ``radius`` is used.
    :type resolution: int or None
    :param split: Number of axial subdivisions. If ``None``, a value derived
        from ``length`` is used.
    :type split: int or None
    :returns: Vertex and triangle index arrays for the cylindrical mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    if resolution is None:
        resolution = int(max(15.0, _utils.remap(radius, 0.0, 2.0, 0.0, 20.0)))

    if split is None:
        split = int(max(1.0, _utils.remap(length, 0.0, 10.0, 0.0, 10.0)))

    count = resolution * (split + 1) + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float32)

    vertices[0] = np.array([0.0, 0.0, length * 0.5], dtype=np.float32)
    vertices[1] = np.array([0.0, 0.0, -length * 0.5], dtype=np.float32)

    step = math.pi * 2.0 / float(resolution)
    h_step = length / float(split)

    for i in range(split + 1):
        for j in range(resolution):
            theta = float(step) * float(j)
            vertices[2 + resolution * i + j] = np.array(
                [math.cos(theta) * radius,
                 math.sin(theta) * radius,
                 length * 0.5 - h_step * i], dtype=np.float32)

    vertices += np.array([0.0, 0.0, length / 2.0], dtype=np.float32)

    faces = []
    for i in range(split):
        base1 = 2 + resolution * i
        base2 = base1 + resolution

        for j in range(resolution):
            j1 = int((j + 1) % resolution)
            faces.append([base2 + j, base1 + j1, base1 + j])
            faces.append([base2 + j, base2 + j1, base1 + j1])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
