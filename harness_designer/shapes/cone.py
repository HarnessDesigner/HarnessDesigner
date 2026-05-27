# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cone mesh generation helpers.

These helpers build triangle meshes suitable for smooth normal generation by
:func:`harness_designer.utils.compute_smooth_normals`.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    """Create or return the cached cone VBO.

    :returns: Cached VBO data for a default cone mesh.
    :rtype: :class:`harness_designer.gl.vbo.VBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 1.0, 360, 1)

        vertices, smooth_normals, face_normals, count = _utils.compute_normals(vertices, faces)

        _vbo = _vbo_handler.VBOHandler(
            'cone', vertices, smooth_normals, face_normals, count,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(radius=1.0, height=2.0, resolution=None, split=None):
    """Create vertices and faces for a cone surface.

    The current implementation generates the conical side surface and apex,
    while the bottom surface code remains commented out.

    :param radius: Radius of the cone base.
    :type radius: float
    :param height: Height of the cone along the positive Z axis.
    :type height: float
    :param resolution: Number of points used around each ring. If ``None``, a
        value derived from ``radius`` is used.
    :type resolution: int or None
    :param split: Number of axial segments used to tessellate the side wall. If
        ``None``, a value derived from ``height`` is used.
    :type split: int or None
    :returns: Vertex and triangle index arrays for the cone mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    if resolution is None:
        resolution = int(max(20.0, _utils.remap(radius, 0.0, 1.0, 0.0, 20.0)))

    if split is None:
        split = int(max(3.0, _utils.remap(height, 0.0, 2.0, 0.0, 10.0)))

    count = resolution * split + 2
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float32)

    vertices[0] = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    vertices[1] = np.array([0.0, 0.0, height], dtype=np.float32)

    step = math.pi * 2.0 / float(resolution)
    h_step = height / float(split)
    r_step = radius / float(split)

    for i in range(split):
        base = 2 + resolution * i
        r = r_step * (split - i)
        for j in range(resolution):
            theta = step * j
            vertices[base + j] = np.array(
                [math.cos(theta) * r,
                 math.sin(theta) * r,
                 h_step * i], dtype=np.float32)

    faces = []
    for j in range(resolution):
        j1 = int((j + 1) % resolution)
        # Triangles for bottom surface.
        # int base = 2;
        # mesh->triangles_.push_back(Eigen::Vector3i(0, base + j1, base + j));

        # Triangles for top segment of conical surface.
        base = 2 + resolution * (split - 1)
        faces.append([1, base + j, base + j1])

    # Triangles for conical surface other than top-segment.
    for i in range(split - 1):
        base1 = 2 + resolution * i
        base2 = base1 + resolution
        for j in range(resolution):
            j1 = int((j + 1) % resolution)
            faces.append([base2 + j1, base1 + j, base1 + j1])
            faces.append([base2 + j1, base2 + j, base1 + j])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
