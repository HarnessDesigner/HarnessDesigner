# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Helical stripe mesh generation helpers.

The stripe is modeled as a swept solid around a cylinder and converted into a
mesh for use by the OpenGL renderer.
"""

import build123d
import numpy as np

from .. import utils as _utils
from ..gl import vbo as _vbo_handler


# Real-world mm per full helix turn. Fixed regardless of wire diameter or
# segment length -- this is the whole point of the shared, fixed-pitch
# canonical mesh + per-instance GPU clip (see objects3d.wire.WireStripe):
# every wire segment shows the same turn spacing no matter how long or
# short it is. Purely a visual-tuning constant -- adjust to taste.
PITCH_MM = 60.0

# The canonical mesh is always generated at this fixed radius -- create_vbo
# always calls create(0.5, ...) below. Larger-diameter wires don't get their
# own, more finely tessellated mesh: the GPU shader scales this one fixed
# mesh up per-instance instead. So the triangle count baked in here has to
# be high enough that the facets stay invisible once magnified for the
# largest wire diameters -- an absolute chordal tolerance sized off
# `radius` alone would under-tessellate for that purpose. But this sweep
# spans the *entire* shared mesh length (grown to the longest wire in the
# project, potentially meters), so going too fine makes generation very
# slow -- these are a balance between the two, not the finest tolerance
# that looks good in isolation.
_LIN_DEFLECTION_MM = 0.05
_ANG_DEFLECTION_RAD = 0.15

# Radial protrusion of the stripe above the wire's surface. This used to be
# remapped from wire diameter to fight z-fighting bleed-through (the wire's
# color showing through the coincident stripe surface) -- radius is always
# 0.5 here (create_vbo always calls create(0.5, ...); larger diameters are a
# GPU-side scale, see create_vbo), so that remap always produced the same
# constant anyway. Bleed-through is now handled by rendering the stripe with
# a polygon offset (see objects3d.wire.WireStripe.render), so this only
# needs to be large enough for OCCT to build a non-degenerate solid -- kept
# small to keep the stripe visually flush with the wire.
_STRIPE_THICKNESS_MM = 0.01

_vbo: _vbo_handler.PooledVBOHandler = None
_current_length: float = 0.0


def create_vbo(min_length: float) -> _vbo_handler.PooledVBOHandler:
    """Return the shared helix stripe VBO, growing it in place (never
    shrinking) so its mesh covers at least ``min_length`` mm.

    Every :class:`~harness_designer.objects.objects3d.wire.WireStripe`
    instance shares this single mesh and shows only the portion of it up to
    its own wire segment's length -- clipped per-instance in the shader --
    instead of stretching a fixed-turn-count mesh to fit, which is what
    used to make the stripe's pitch vary with segment length.

    :param min_length: Minimum length (mm) the mesh must cover.
    :returns: The shared stripe VBO.
    :rtype: :class:`harness_designer.gl.vbo.PooledVBOHandler`
    """
    global _vbo, _current_length

    if _vbo is not None and min_length <= _current_length:
        return _vbo

    new_length = max(min_length, _current_length)
    vertices, faces = create(0.5, new_length, PITCH_MM)

    packed, count = _utils.compute_normals(vertices, faces)

    if _vbo is None:
        unpacked_verts = packed[:count * 3].reshape(-1, 3)
        aabb1, aabb2 = _utils.compute_aabb(unpacked_verts)
        aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
        obb = _utils.compute_obb(aabb1, aabb2)

        _vbo = _vbo_handler.PooledVBOHandler(
            'helix', packed, count, aabb=aabb, obb=obb,
            arena_kind=_vbo_handler.VBO_TYPE_PRIMITIVE)
    else:
        _vbo.update(packed, count)

    _current_length = new_length

    return _vbo


def create(radius, length, pitch):
    """Create a mesh for a helical stripe wrapped around a cylinder.

    :param radius: Radius of the underlying wire or cylinder.
    :type radius: float
    :param length: Length of the stripe sweep.
    :type length: float
    :param pitch: Real-world distance (mm) per full helix turn.
    :type pitch: float
    :returns: Vertex and face arrays for the stripe mesh.
    :rtype: tuple[:class:`numpy.ndarray`, :class:`numpy.ndarray`]
    """
    # Create the wire
    model = build123d.Cylinder(radius, length, align=build123d.Align.NONE)

    # Extract the axis of rotation from the wire to create the stripe
    wire_axis = model.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

    edges = model.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(0, radius * 2 / 3.0)

    stripe_arc = build123d.Face(edges.offset_2d(_STRIPE_THICKNESS_MM, side=build123d.Side.RIGHT))

    # Define the twist path to follow the wire
    twist = build123d.Helix(pitch=pitch, height=length, radius=radius,
                            center=wire_axis.position, direction=wire_axis.direction)

    # Sweep the arc to create the stripe
    s_line = build123d.Line(wire_axis.position, length * wire_axis.direction)
    stripe = build123d.sweep(stripe_arc, s_line, binormal=twist)

    # The stripe is a shared mesh grown to cover the longest wire in the
    # project (see create_vbo), so its bounding box is dominated by length,
    # not by the small-radius curvature that actually needs tessellating
    # smoothly. A relative deflection (the default) scales off that
    # bounding box and ends up far coarser than the stripe itself -- use a
    # fixed absolute deflection instead (see _LIN_DEFLECTION_MM above).
    return _utils.convert_model_to_mesh(
        stripe, lin_deflection=_LIN_DEFLECTION_MM,
        ang_deflection=_ANG_DEFLECTION_RAD, is_relative=False)
