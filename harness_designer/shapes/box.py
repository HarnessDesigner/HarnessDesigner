# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Box mesh generation helpers.

The functions in this module build axis-aligned cuboid geometry for use by
:class:`harness_designer.gl.vbo.PooledVBOHandler` instances.
"""

import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.PooledVBOHandler = None


def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached unit box VBO.

    The cached mesh is built from :func:`create` using unit dimensions.

    :returns: Cached VBO data for a box with dimensions ``1 x 1 x 1``.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(1.0, 1.0, 1.0)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'box', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(width, height, depth):
    """Create vertex and face arrays for an axis-aligned box.

    The generated box is centered on the origin and uses triangle faces.

    :param width: Overall size along the X axis.
    :type width: float
    :param height: Overall size along the Y axis.
    :type height: float
    :param depth: Overall size along the Z axis.
    :type depth: float
    :returns: Vertex and triangle index arrays for the box mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    depth /= 2.0
    height /= 2.0
    width /= 2.0

    vertices = np.full((8, 3), [0.0, 0.0, 0.0], dtype=np.float32)
    vertices[0] = np.array([width, height, depth], dtype=np.float32)
    vertices[1] = np.array([width, height, -depth], dtype=np.float32)
    vertices[2] = np.array([width, -height, depth], dtype=np.float32)
    vertices[3] = np.array([width, -height, -depth], dtype=np.float32)

    vertices[4] = np.array([-width, height, depth], dtype=np.float32)
    vertices[5] = np.array([-width, height, -depth], dtype=np.float32)
    vertices[6] = np.array([-width, -height, depth], dtype=np.float32)
    vertices[7] = np.array([-width, -height, -depth], dtype=np.float32)

    # Triangles.
    faces = np.array([[4, 7, 5], [4, 6, 7], [0, 2, 4], [2, 6, 4],
                      [0, 1, 2], [1, 3, 2], [1, 5, 7], [1, 7, 3],
                      [2, 3, 7], [2, 7, 6], [0, 4, 1], [1, 4, 5]], dtype=np.int32)

    return vertices, faces
