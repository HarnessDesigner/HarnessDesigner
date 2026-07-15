# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg board bundle-strand geometry.

Phase 1 stub: a single flat-rectangle "strand" mesh builder for bundles
laid across the peg board. Not wired into
``gl.canvas_pegboard.canvas.Canvas._render_objects`` yet -- Phase 1's
static render only covers housings/splices/transitions/bare terminals
(see :mod:`harness_designer.gl.canvas_pegboard.layout_graph`). Bundle
strands and bare-wire visibility filtering are Phase 2's job; this
function exists now so that work has a home to land in without touching
this module's shape later.
"""

import math

import numpy as np


# Packed VBO layout used throughout this codebase: 9 floats per vertex --
# [position(3), smooth normal(3), face normal(3)], stored as three
# contiguous blocks (all positions, then all smooth normals, then all face
# normals) rather than interleaved per-vertex. See gl.vbo.FLOATS_PER_VERTEX.
_FLOATS_PER_VERTEX = 9


def build_strand_quad(
        p1_xz: tuple[float, float],
        p2_xz: tuple[float, float],
        width: float) -> tuple[np.ndarray, int]:
    """Build a flat rectangular strand mesh from *p1_xz* to *p2_xz*.

    The rectangle lies flat in the peg board XZ plane at ``y=0``, centered
    on the ``p1 -> p2`` segment, *width* wide. Both normals (smooth and
    face) are the constant ``(0, 1, 0)`` -- a flat rectangle's smooth
    normal trivially equals its face normal, so there is no need to run
    the general ``utils.mesh_normals.compute_normals`` path for this
    hardcoded shape.

    :param p1_xz: Segment start, ``(x, z)`` world units (mm).
    :type p1_xz: tuple[float, float]
    :param p2_xz: Segment end, ``(x, z)`` world units (mm).
    :type p2_xz: tuple[float, float]
    :param width: Strand width, world units (mm).
    :type width: float
    :returns: ``(packed_vertex_array, vertex_count)`` -- a flat float32
        array laid out ``[positions | smooth normals | face normals]``
        (:data:`_FLOATS_PER_VERTEX` floats/vertex total) and its vertex
        count (always 6 -- two triangles covering the rectangle).
    :rtype: tuple[numpy.ndarray, int]
    """
    x1, z1 = p1_xz
    x2, z2 = p2_xz

    dx = x2 - x1
    dz = z2 - z1
    length = math.hypot(dx, dz)

    if length < 1e-9:
        # Degenerate (zero-length) segment -- fall back to +X so the
        # rectangle still has a well-defined width direction instead of
        # dividing by zero.
        dir_x, dir_z = 1.0, 0.0
    else:
        dir_x, dir_z = dx / length, dz / length

    # Perpendicular to the segment direction, in the XZ plane (rotate 90
    # degrees): (dir_x, dir_z) -> (-dir_z, dir_x).
    perp_x, perp_z = -dir_z, dir_x
    half_w = width / 2.0

    off_x = perp_x * half_w
    off_z = perp_z * half_w

    # Four rectangle corners, walked around the perimeter.
    a = (x1 - off_x, 0.0, z1 - off_z)  # start, left
    b = (x1 + off_x, 0.0, z1 + off_z)  # start, right
    c = (x2 + off_x, 0.0, z2 + off_z)  # end, right
    d = (x2 - off_x, 0.0, z2 - off_z)  # end, left

    # Two triangles, consistent winding: a -> b -> c and a -> c -> d.
    positions = (a, b, c, a, c, d)
    normal = (0.0, 1.0, 0.0)
    normals = (normal,) * 6

    packed = np.array(
        [coord for vertex in positions for coord in vertex] +
        [coord for vertex in normals for coord in vertex] +
        [coord for vertex in normals for coord in vertex],
        dtype=np.float32
    )

    return packed, 6


if __name__ == '__main__':
    # Sanity check: a 10mm-wide strand from (0, 0) to (100, 0) should be a
    # 100 x 10 rectangle straddling the X axis, flat at y=0.
    _packed, _count = build_strand_quad((0.0, 0.0), (100.0, 0.0), 10.0)
    assert _count == 6
    assert _packed.shape == (6 * _FLOATS_PER_VERTEX,)

    _verts = _packed[:6 * 3].reshape(6, 3)
    assert np.allclose(_verts[:, 1], 0.0)

    _xz = _verts[:, [0, 2]]
    assert np.isclose(float(_xz[:, 0].min()), 0.0)
    assert np.isclose(float(_xz[:, 0].max()), 100.0)
    assert np.isclose(float(_xz[:, 1].min()), -5.0)
    assert np.isclose(float(_xz[:, 1].max()), 5.0)

    print('build_strand_quad sanity check passed:', _packed.shape)
