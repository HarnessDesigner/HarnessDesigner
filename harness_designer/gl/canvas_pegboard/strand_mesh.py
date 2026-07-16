# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg board strand geometry.

:func:`build_strand_quad` builds a flat-rectangle mesh -- used for
bare-wire strands (``Canvas._render_strand_draws``), which are always a
single straight segment with no bends, so a one-off CPU-built quad per
strand is fine.

:func:`cylinder_placement` is a different kind of helper -- not a mesh
builder at all, but the position/rotation transform that places the
existing shared, pooled unit-cylinder VBO (``shapes.cylinder.create_vbo``)
along one bundle-graph edge. Bundle strands (``Canvas._render_bundle_strands``)
use this instead of a per-edge CPU-built quad: the *same* cylinder mesh is
reused for every edge of every bundle, GPU-instanced purely via
``objectPosition``/``objectRotation``/``objectScale`` uniforms recomputed
fresh each frame from the live, already-current ``PegboardNode.x``/``.z``
-- no per-edge VBO to build, update, or release at all, unlike bare-wire
strands.
"""

import math

import numpy as np

from ...geometry import angle as _angle


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


_IDENTITY_QUAT = (1.0, 0.0, 0.0, 0.0)
_FLIPPED_QUAT = (0.0, 1.0, 0.0, 0.0)
_PARALLEL_DOT_TOLERANCE = 1e-4
_MIN_LENGTH_MM = 0.001


def cylinder_placement(p1_xz: tuple, p2_xz: tuple) -> tuple:
    """Return ``(length, quat)`` placing the shared unit-cylinder VBO
    (``shapes.cylinder.create_vbo`` -- local Z spans ``[0, 1]``, radius
    ``0.5``) from *p1_xz* to *p2_xz*, confined to the peg board's XZ
    plane (world Y always ``0``).

    Mirrors ``objects.objects3d.bundle.Bundle._update_position``/
    ``_rotation_from_direction`` exactly -- same ``wire_vector = p1 - p2``
    direction convention, same axis-angle derivation -- this is the
    identical, already-visually-verified cylinder placement the 3D
    editor's own bundle rendering already uses (a cylinder positioned at
    *p1*, whose local +Z, once rotated by the returned quat, points
    toward *p2* over the returned *length*).

    :param p1_xz: Segment start (the cylinder's own ``objectPosition``),
        ``(x, z)`` world units (mm).
    :type p1_xz: tuple[float, float]
    :param p2_xz: Segment end.
    :type p2_xz: tuple[float, float]
    :returns: ``(length, (qw, qx, qy, qz))``.
    :rtype: tuple[float, tuple[float, float, float, float]]
    """
    x1, z1 = p1_xz
    x2, z2 = p2_xz

    wire_vector = np.array([x1 - x2, 0.0, z1 - z2], dtype=np.float64)
    length = float(np.linalg.norm(wire_vector))

    if length < _MIN_LENGTH_MM:
        return _MIN_LENGTH_MM, _IDENTITY_QUAT

    direction = wire_vector / length

    z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    dot = float(np.dot(z_axis, direction))

    if abs(dot - 1.0) < _PARALLEL_DOT_TOLERANCE:
        return length, _IDENTITY_QUAT
    if abs(dot + 1.0) < _PARALLEL_DOT_TOLERANCE:
        return length, _FLIPPED_QUAT

    axis = np.cross(z_axis, direction)  # NOQA
    axis = axis / np.linalg.norm(axis)
    angle_rad = math.acos(max(-1.0, min(1.0, dot)))

    quat_angle = _angle.Angle.from_axis_angle(axis, angle_rad)
    qw, qx, qy, qz = [float(v) for v in quat_angle.as_quat_float]

    return length, (qw, qx, qy, qz)


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
