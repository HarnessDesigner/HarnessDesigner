# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Flat annulus ("disc ring") mesh generation helpers.

Unlike torus.py's round-tube ring, this is a flat band with a
rectangular cross-section -- outer diameter 1.0, depth 1.0 by default.
Same XY-plane/Z-normal axis convention as torus.create() (Z is the
ring's thickness/normal axis -- see
rotation_handlers/rotation_mesh.py:build_ring_mesh(), which builds the
existing rotation-ring gizmo directly from torus.create(1.0, ...)), so
this shape composes with that ring without a corrective rotation.

This is a unit reference shape, meant to be scaled non-uniformly per
instance (wide across X/Y, thin along Z) via the render-time scale
uniform -- the GPU does the sizing, same as every other shape in this
package.
"""

import math
import numpy as np
import build123d

from .. import utils as _utils
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


_vbo: _vbo_handler.NonPooledVBOHandler = None

# Number of samples around the ring -- not exposed as a create()
# parameter (matches rotation_handlers/rotation_mesh.py's RING_RESOLUTION
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

    # Eight concentric rings of points -- each of the washer's 4 physical
    # rim circles (outer/top, outer/bottom, inner/top, inner/bottom) gets
    # TWO vertex copies at the same position: one used only by the flat
    # cap face it belongs to, one used only by the curved wall face it
    # belongs to. The two faces meeting at a rim are a genuine hard edge
    # (a cap's near-axial normal has nothing to do with a wall's radial
    # one), but utils.mesh_normals.compute_normals averages face normals
    # per *vertex index* with no concept of hard edges -- sharing one
    # vertex between a cap and a wall face there would blend the two into
    # a wrong, visibly seamed normal right at the rim. Splitting the
    # index (not the position -- this introduces no actual gap, see the
    # module's own watertightness note below) keeps each face group's
    # normal averaging confined to itself.
    CAP_OUTER_TOP, CAP_OUTER_BOTTOM, CAP_INNER_TOP, CAP_INNER_BOTTOM, \
        WALL_OUTER_TOP, WALL_OUTER_BOTTOM, WALL_INNER_TOP, WALL_INNER_BOTTOM = range(8)

    rows = (
        (outer_radius, half_depth),   # CAP_OUTER_TOP
        (outer_radius, -half_depth),  # CAP_OUTER_BOTTOM
        (inner_radius, half_depth),   # CAP_INNER_TOP
        (inner_radius, -half_depth),  # CAP_INNER_BOTTOM
        (outer_radius, half_depth),   # WALL_OUTER_TOP
        (outer_radius, -half_depth),  # WALL_OUTER_BOTTOM
        (inner_radius, half_depth),   # WALL_INNER_TOP
        (inner_radius, -half_depth),  # WALL_INNER_BOTTOM
    )

    @_check_types.do
    def vert_idx(row: int, seg: int) -> int:
        return row * resolution + (seg % resolution)

    vertices = np.zeros((len(rows) * resolution, 3), dtype=np.float32)

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

        # Top cap (outer -> inner), facing +Z.
        a, b, c, d = (vert_idx(CAP_OUTER_TOP, seg), vert_idx(CAP_OUTER_TOP, nxt),
                      vert_idx(CAP_INNER_TOP, nxt), vert_idx(CAP_INNER_TOP, seg))
        faces.append([a, b, c])
        faces.append([a, c, d])

        # Bottom cap (outer -> inner), facing -Z -- reversed winding
        # relative to the top cap.
        a, b, c, d = (vert_idx(CAP_OUTER_BOTTOM, seg), vert_idx(CAP_OUTER_BOTTOM, nxt),
                      vert_idx(CAP_INNER_BOTTOM, nxt), vert_idx(CAP_INNER_BOTTOM, seg))
        faces.append([a, c, b])
        faces.append([a, d, c])

        # Outer wall (top -> bottom), facing outward.
        a, b, c, d = (vert_idx(WALL_OUTER_TOP, seg), vert_idx(WALL_OUTER_TOP, nxt),
                      vert_idx(WALL_OUTER_BOTTOM, nxt), vert_idx(WALL_OUTER_BOTTOM, seg))
        faces.append([a, c, b])
        faces.append([a, d, c])

        # Inner wall (top -> bottom), facing inward -- reversed winding
        # relative to the outer wall.
        a, b, c, d = (vert_idx(WALL_INNER_TOP, seg), vert_idx(WALL_INNER_TOP, nxt),
                      vert_idx(WALL_INNER_BOTTOM, nxt), vert_idx(WALL_INNER_BOTTOM, seg))
        faces.append([a, b, c])
        faces.append([a, c, d])

    faces = np.array(faces, dtype=np.int32)

    return vertices, faces
