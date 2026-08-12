# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Composite cylinder-and-helix mesh generation helpers.

This module builds a more complex part from :mod:`build123d` primitives and
stores the result in a cached :class:`harness_designer.gl.vbo.PooledVBOHandler`.
"""

import math

import build123d
import numpy as np

from .. import utils as _utils
from ..geometry import point as _point
from ..gl import vbo as _vbo_handler
from .. import check_types as _check_types


_vbo: _vbo_handler.PooledVBOHandler = None
_stripe_vbo: _vbo_handler.PooledVBOHandler = None

# Visual tuning for the decorative twist stripe -- pitch kept in sync with
# shapes.helix.PITCH_MM so straight wire segments and this part's stripe
# spiral at the same real-world rate.
_STRIPE_PITCH_MM = 60.0
_STRIPE_THICKNESS_MM = 0.075
# Fraction of the wire's own circumference trimmed off to build the
# stripe's profile -- see _stripe_profile.
_STRIPE_ARC_FRACTION = 2.0 / 3.0
_STRIPE_ARC_WIDTH_DEG = math.degrees(_STRIPE_ARC_FRACTION)

# Extra starting rotation (about the wire's own centerline) applied to each
# straight segment's stripe so its arc picks up where the loop's stripe
# left off at their shared joint, one arc-width further around than a
# naive "outward-facing" match alone would land it. Segment 2 gets the
# opposite sign of segment 1 -- it sits behind an extra Y-axis rotate(180)
# in create_vbo that segment 1 doesn't, which flips which way "one
# arc-width further around" means.
_SEGMENT1_STRIPE_OFFSET_DEG = -90.0 - _STRIPE_ARC_WIDTH_DEG
# Plus a small hand-tuned nudge -- the arc-width match above gets segment 2
# close, but not pixel-perfect, at its joint with the loop stripe.
_SEGMENT2_STRIPE_OFFSET_DEG = -90.0 + _STRIPE_ARC_WIDTH_DEG + 1.0
# The loop's stripe starts on the inside face of the loop by default (the
# path's Frenet normal points toward the loop's own axis there) -- this
# flips it to the outside, visible face.
_LOOP_STRIPE_OFFSET_DEG = 180.0


def _stripe_profile(radius, extra_deg=0.0):
    """Small offset-arc cross-section for the decorative twist stripe,
    riding a diameter straddling ``radius`` (half embedded in the wire,
    half protruding) rather than sitting flush against its surface.

    :param radius: Radius of the wire the stripe rides on.
    :type radius: float
    :param extra_deg: Extra starting rotation about the profile's own
        center, before it's swept.
    :type extra_deg: float
    :returns: Flat stripe cross-section, centered at the local origin.
    :rtype: :class:`build123d.Face`
    """
    ride_radius = radius - _STRIPE_THICKNESS_MM / 2.0
    edge = build123d.Circle(ride_radius).edges()[0]
    arc = edge.trim_to_length(0, ride_radius * _STRIPE_ARC_FRACTION)
    face = build123d.Face(arc.offset_2d(_STRIPE_THICKNESS_MM, side=build123d.Side.RIGHT))

    if extra_deg:
        face = build123d.Rotation(Z=extra_deg) * face

    return face


def _straight_stripe(radius, length, start_deg=0.0):
    """Twist stripe for a straight wire segment running along +Z from the
    origin -- same offset-arc + binormal-helix technique as
    :func:`harness_designer.shapes.helix.create`'s stripe, sized and
    positioned to match this module's own straight cylinders.

    :param radius: Radius of the wire.
    :type radius: float
    :param length: Length of the segment.
    :type length: float
    :param start_deg: Starting rotation of the stripe about the wire's
        centerline.
    :type start_deg: float
    :returns: Swept stripe solid.
    :rtype: :class:`build123d.Part`
    """
    profile = _stripe_profile(radius, start_deg)
    ride_radius = radius - _STRIPE_THICKNESS_MM / 2.0
    twist = build123d.Helix(pitch=_STRIPE_PITCH_MM, height=length, radius=ride_radius,
                             center=(0, 0, 0), direction=(0, 0, 1))
    s_line = build123d.Line((0, 0, 0), (0, 0, length))
    return build123d.sweep(profile, s_line, binormal=twist)


def _loop_stripe_guide(path, radius, start_deg=0.0, n_samples=40):
    """Sampled twist-reference curve for the loop's stripe.

    A straight wire's stripe gets its twist from a ``binormal=`` Helix
    reference curve (see :func:`_straight_stripe`), but a Helix can only be
    built around a straight axis, so it can't itself follow ``path`` (which
    is already curved). This stands in for that reference curve by tracing
    the same growing-twist point a Helix would, at ``n_samples`` stations
    along ``path`` -- close enough together that the resulting stripe (only
    ~1/10 turn of extra twist over one loop, at this pitch/length) comes out
    smooth.

    :param path: Loop path the stripe follows.
    :type path: :class:`build123d.Helix`
    :param radius: Radius the stripe rides on.
    :type radius: float
    :param start_deg: Starting rotation of the stripe about the wire's
        centerline.
    :type start_deg: float
    :param n_samples: Number of stations sampled along ``path``.
    :type n_samples: int
    :returns: Reference curve for ``sweep``'s ``binormal`` argument.
    :rtype: :class:`build123d.Spline`
    """
    path_length = path.length
    points = []

    for i in range(n_samples + 1):
        t = i / n_samples
        dist = t * path_length
        twist_deg = start_deg + (dist / _STRIPE_PITCH_MM) * 360.0
        loc = path.location_at(t)
        ref_loc = loc * build123d.Rotation(Z=twist_deg) * build123d.Location((radius, 0, 0))
        points.append(ref_loc.position)

    return build123d.Spline(*points)


def _loop_stripe(path, radius, start_deg=0.0):
    """Twist stripe following the loop's own helical path, riding the same
    diameter as the loop's swept tube.

    :param path: Loop path the stripe follows.
    :type path: :class:`build123d.Helix`
    :param radius: Radius of the wire.
    :type radius: float
    :param start_deg: Starting rotation of the stripe about the wire's
        centerline.
    :type start_deg: float
    :returns: Swept stripe solid.
    :rtype: :class:`build123d.Part`
    """
    profile = _stripe_profile(radius)
    guide = _loop_stripe_guide(path, radius, start_deg)
    initial_section = path.location_at(0) * build123d.Rotation(Z=start_deg) * profile
    return build123d.sweep(sections=initial_section, path=path, binormal=guide)


@_check_types.do
def create_vbo():
    """Create or return the cached cylinder-helix VBO.

    The generated part combines two cylinders with a swept helix loop, each
    with its own decorative twist stripe. The returned VBO also stores a
    secondary connection point derived from the internal tracking sphere.

    :returns: Cached VBO for the composite cylinder/helix part.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo

    if _vbo is not None:
        return _vbo

    wire_r = 0.5
    diameter = 1.0

    # Create the wire
    cyl = build123d.Cylinder(wire_r, diameter, align=build123d.Align.NONE)

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(diameter),
        pitch=float(diameter + diameter * 0.15),
        height=float(diameter + diameter * 0.15),
        cone_angle=0,
        direction=(1, 0, 0)
    )

    loop_profile = build123d.Circle(wire_r)

    swept_cylinder = build123d.sweep(
        path=loop_helix, sections=(loop_helix ^ 0) * loop_profile)

    # rotate and position the loop so it align with the cylinder
    swept_cylinder = swept_cylinder.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 90.0)
    swept_cylinder = swept_cylinder.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 9.35)
    swept_cylinder = swept_cylinder.move(
        build123d.Location((0.0, float(diameter), 0.0), (0, 1, 0)))

    # add the loop to the cylinder to make the part
    cyl += swept_cylinder

    cyl2 = build123d.Cylinder(wire_r, diameter, align=build123d.Align.NONE)

    # this sphere is not used in the rendering, it is only used to track where
    # the second connection point should be, the first point being at 0, 0, 0
    sphere2 = build123d.Sphere(wire_r)
    sphere2 = sphere2.move(
        build123d.Location((0.0, 0.0, diameter), (0, 0, 1)))

    cyl2 = cyl2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)
    sphere2 = sphere2.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    cyl2 = cyl2.move(build123d.Location(
        (diameter + diameter * 0.133, 0.0, 0.0), (1, 0, 0)))
    sphere2 = sphere2.move(build123d.Location(
        (diameter + diameter * 0.133, 0.0, 0.0), (1, 0, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, -(diameter * 0.0195), 0.0), (0, 1, 0)))
    sphere2 = sphere2.move(build123d.Location(
        (0.0, -(diameter * 0.0195), 0.0), (0, 1, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, 0.0, -(diameter * 0.15)), (0, 0, 1)))
    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -(diameter * 0.15)), (0, 0, 1)))

    cyl += cyl2

    cyl = cyl.move(build123d.Location(
        (0.0, 0.0, -diameter), (0, 0, 1)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    cn = sphere2.center()

    cn = _point.Point(cn.X, cn.Y, cn.Z)

    vertices, faces = _utils.convert_model_to_mesh(cyl)

    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    _vbo = _vbo_handler.PooledVBOHandler(
        'cylinder_helix', packed, count, aabb=aabb, obb=obb,
        arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE, endpoint=cn)

    return _vbo


@_check_types.do
def create_stripe_vbo():
    """Create or return the cached cylinder-helix stripe VBO -- the
    decorative twist stripe rendered as its own mesh, overlaid on top of
    the plain body from :func:`create_vbo` (see
    ``objects_3d.wire_service_loop.WireServiceLoopStripe``).

    :returns: Cached VBO for the stripe part.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _stripe_vbo

    if _stripe_vbo is not None:
        return _stripe_vbo

    wire_r = 0.5
    diameter = 1.0

    stripe1 = _straight_stripe(wire_r, diameter, _SEGMENT1_STRIPE_OFFSET_DEG)

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(diameter),
        pitch=float(diameter + diameter * 0.15),
        height=float(diameter + diameter * 0.15),
        cone_angle=0,
        direction=(1, 0, 0)
    )

    loop_stripe = _loop_stripe(loop_helix, wire_r, _LOOP_STRIPE_OFFSET_DEG)

    loop_stripe = loop_stripe.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 90.0)
    loop_stripe = loop_stripe.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 9.35)
    loop_stripe = loop_stripe.move(build123d.Location((0.0, float(diameter), 0.0), (0, 1, 0)))

    stripe2 = _straight_stripe(wire_r, diameter, _SEGMENT2_STRIPE_OFFSET_DEG)
    stripe2 = stripe2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)
    stripe2 = stripe2.move(build123d.Location((diameter + diameter * 0.133, 0.0, 0.0), (1, 0, 0)))

    stripe2 = stripe2.move(build123d.Location((0.0, -(diameter * 0.0195), 0.0), (0, 1, 0)))
    stripe2 = stripe2.move(build123d.Location((0.0, 0.0, -(diameter * 0.15)), (0, 0, 1)))

    stripe = stripe1 + loop_stripe + stripe2
    stripe = stripe.move(build123d.Location((0.0, 0.0, -diameter), (0, 0, 1)))

    vertices, faces = _utils.convert_model_to_mesh(stripe)

    packed, count = _utils.compute_normals(vertices, faces)

    unpacked_verts = packed[:count * 3].reshape(-1, 3)
    aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
    aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
    obb = _utils.compute_obb(aabb1, aabb2)

    _stripe_vbo = _vbo_handler.PooledVBOHandler(
        'stripe_cylinder_helix', packed, count, aabb=aabb, obb=obb,
        arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)

    return _stripe_vbo



