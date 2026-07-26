# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Flat circle mesh generation helpers.

The functions in this module build a flat (Y=0), N-gon-fan circle for use by
:class:`harness_designer.gl.vbo.PooledVBOHandler` instances -- the 2D-editor
counterpart to :mod:`harness_designer.shapes.box`. The generated circle lies
in the XZ plane, matching every other flat/ground-plane mesh in this
codebase (floor, grid, Peg Board strands). Used for cavity/pin markers.
"""

import math

import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


_SEGMENTS = 359

_vbo: _vbo_handler.PooledVBOHandler = None


def create_vbo() -> _vbo_handler.PooledVBOHandler:
    """Create or return the cached unit circle VBO.

    The cached mesh is built from :func:`create` using a unit diameter.

    :returns: Cached VBO data for a circle with diameter ``1``, flat
        (``height=0``), with :data:`_SEGMENTS` segments.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(1.0, 0.0, _SEGMENTS)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'circle', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _vbo


def create(diameter, height, segments=_SEGMENTS):
    """Create vertex and face arrays for a flat circle (N-gon fan).

    The generated circle is centered on the origin and lies flat on the
    Y=0 plane (``height`` offsets the flat plane along Y -- 0 keeps it at
    the origin) and uses triangle faces.

    :param diameter: Overall diameter in the XZ plane.
    :type diameter: float
    :param height: Y-offset of the flat circle plane.
    :type height: float
    :param segments: Number of perimeter segments.
    :type segments: int
    :returns: Vertex and triangle index arrays for the circle mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    radius = diameter / 2.0

    center = np.array([[0.0, height, 0.0]], dtype=np.float32)

    angles = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    rim = np.stack([
        radius * np.cos(angles),
        np.full(segments, height, dtype=np.float32),
        radius * np.sin(angles),
    ], axis=1).astype(np.float32)

    vertices = np.concatenate([center, rim], axis=0)

    # Wound (0, i+1, i) rather than (0, i, i+1) so the face normal points
    # +Y -- same winding rule shapes/rectangle.py and shapes/triangle.py
    # follow, verified against _process_verts_for_normals' cross(v1-v0,
    # v2-v0) convention.
    faces = []
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append([0, next_i + 1, i + 1])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
