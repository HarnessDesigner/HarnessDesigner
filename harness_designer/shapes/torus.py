# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Torus mesh generation helpers.

This module creates torus geometry procedurally and converts it into a cached
:class:`harness_designer.gl.vbo.VBOHandler`.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    """Create or return the cached torus VBO.

    :returns: Cached VBO data for a default torus mesh.
    :rtype: :class:`harness_designer.gl.vbo.VBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 0.5, 360, 360)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.VBOHandler(
            'torus', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(torus_radius=1.0, tube_radius=0.5, radial_resolution=20, tubular_resolution=20):
    """Create vertices and faces for a torus mesh.

    :param torus_radius: Distance from the origin to the center of the tube.
    :type torus_radius: float
    :param tube_radius: Radius of the torus tube.
    :type tube_radius: float
    :param radial_resolution: Number of samples around the main torus ring.
    :type radial_resolution: int
    :param tubular_resolution: Number of samples around the tube cross-section.
    :type tubular_resolution: int
    :returns: Vertex and triangle index arrays for the torus mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    count = radial_resolution * tubular_resolution
    vertices = np.full((count, 3), [0.0, 0.0, 0.0], dtype=np.float32)
    faces = np.full((count * 2, 3), [0, 0, 0], dtype=np.int32)

    def vert_idx(uidx_, vidx_):
        """Return the flattened vertex index for torus grid coordinates.

        :param uidx_: Radial ring index.
        :type uidx_: int
        :param vidx_: Tube segment index.
        :type vidx_: int
        :returns: Flattened vertex index into ``vertices``.
        :rtype: int
        """
        return uidx_ * tubular_resolution + vidx_

    u_step = 2.0 * math.pi / float(radial_resolution)
    v_step = 2.0 * math.pi / float(tubular_resolution)
    for uidx in range(radial_resolution):
        u = uidx * u_step
        w = np.array([math.cos(u), math.sin(u), 0.0], dtype=np.float32)
        for vidx in range(tubular_resolution):
            v = vidx * v_step

            vertices[vert_idx(uidx, vidx)] = (
                (torus_radius * w) + ((tube_radius * math.cos(v)) * w) +
                np.array([0, 0, tube_radius * math.sin(v)], dtype=np.float32)
            )

            tri_idx = int((uidx * tubular_resolution + vidx) * 2)
            faces[tri_idx + 0] = np.array([
                    vert_idx((uidx + 1) % radial_resolution, vidx),
                    vert_idx((uidx + 1) % radial_resolution, (vidx + 1) % tubular_resolution),
                    vert_idx(uidx, vidx)], dtype=np.int32)
            faces[tri_idx + 1] = np.array([
                    vert_idx(uidx, vidx),
                    vert_idx((uidx + 1) % radial_resolution, (vidx + 1) % tubular_resolution),
                    vert_idx(uidx, (vidx + 1) % tubular_resolution)], dtype=np.int32)

    return vertices, faces
