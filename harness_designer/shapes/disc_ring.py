# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Flat annulus ("disc ring") mesh generation helpers.

Unlike torus.py's round-tube ring, this is a flat band with a
rectangular cross-section -- outer diameter 1.0, depth 1.0 by default.
Same XY-plane/Z-normal axis convention as torus.create() (Z is the
ring's thickness/normal axis -- see
gl/canvas_base/rotation_mesh.py:build_ring_mesh(), which builds the
existing rotation-ring gizmo directly from torus.create(1.0, ...)), so
this shape composes with that ring without a corrective rotation.

This is a unit reference shape, meant to be scaled non-uniformly per
instance (wide across X/Y, thin along Z) via the render-time scale
uniform -- the GPU does the sizing, same as every other shape in this
package.
"""

import math
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


_vbo: _vbo_handler.NonPooledVBOHandler = None

# Number of samples around the ring -- not exposed as a create()
# parameter (matches gl/canvas_base/rotation_mesh.py's RING_RESOLUTION
# being a fixed constant rather than caller-supplied).
_RESOLUTION = 90


@_check_types.do
def create_vbo() -> _vbo_handler.NonPooledVBOHandler:
    """Create or return the cached disc-ring VBO.

    Standalone (:class:`~harness_designer.gl.vbo.NonPooledVBOHandler`,
    not arena-pooled) like the rotation-rings gizmo's own ring/handle
    VBOs -- this is a UI-overlay shape, not a scene primitive meant to
    be shared across many independent object instances.

    :returns: Cached VBO data for a default disc-ring mesh.
    :rtype: :class:`harness_designer.gl.vbo.NonPooledVBOHandler`
    """
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 0.4, 1.0)

        packed, count = _utils.compute_normals(vertices, faces)

        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.NonPooledVBOHandler(packed, count, aabb=aabb, obb=obb)

    return _vbo


@_check_types.do
def create(outer_radius: float = 0.5, inner_radius: float = 0.4,
          depth: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Create vertices and faces for a flat annulus ("disc ring").

    Lies in the XY plane, extruded along Z -- same axis convention as
    :func:`~harness_designer.shapes.torus.create` (Z is the ring's
    thickness/normal axis).

    :param outer_radius: Outer radius of the band.
    :type outer_radius: float
    :param inner_radius: Inner radius of the band -- must be less than
        *outer_radius*.
    :type inner_radius: float
    :param depth: Full thickness along Z.
    :type depth: float
    :returns: Vertex and triangle index arrays for the disc-ring mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """

    resolution = _RESOLUTION
    half_depth = depth / 2.0

    # Four concentric rings of points, in this fixed row order:
    # 0 = outer/top, 1 = outer/bottom, 2 = inner/top, 3 = inner/bottom.
    rows = (
        (outer_radius, half_depth),
        (outer_radius, -half_depth),
        (inner_radius, half_depth),
        (inner_radius, -half_depth),
    )

    @_check_types.do
    def vert_idx(row: int, seg: int) -> int:
        return row * resolution + (seg % resolution)

    vertices = np.zeros((4 * resolution, 3), dtype=np.float32)

    step = 2.0 * math.pi / float(resolution)
    for seg in range(resolution):
        theta = step * seg
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        for row, (r, z) in enumerate(rows):
            vertices[vert_idx(row, seg)] = np.array(
                [r * cos_t, r * sin_t, z], dtype=np.float32)

    faces = []

    for seg in range(resolution):
        nxt = seg + 1

        # Top face (outer row 0 -> inner row 2), facing +Z.
        a, b, c, d = vert_idx(0, seg), vert_idx(0, nxt), vert_idx(2, nxt), vert_idx(2, seg)
        faces.append([a, b, c])
        faces.append([a, c, d])

        # Bottom face (outer row 1 -> inner row 3), facing -Z --
        # reversed winding relative to the top face.
        a, b, c, d = vert_idx(1, seg), vert_idx(1, nxt), vert_idx(3, nxt), vert_idx(3, seg)
        faces.append([a, c, b])
        faces.append([a, d, c])

        # Outer wall (top row 0 -> bottom row 1), facing outward.
        a, b, c, d = vert_idx(0, seg), vert_idx(0, nxt), vert_idx(1, nxt), vert_idx(1, seg)
        faces.append([a, c, b])
        faces.append([a, d, c])

        # Inner wall (top row 2 -> bottom row 3), facing inward --
        # reversed winding relative to the outer wall.
        a, b, c, d = vert_idx(2, seg), vert_idx(2, nxt), vert_idx(3, nxt), vert_idx(3, seg)
        faces.append([a, b, c])
        faces.append([a, c, d])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
