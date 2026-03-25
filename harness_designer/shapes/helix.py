
import build123d
from .. import utils as _utils

from ..gl import vbo as _vbo_handler

_vbo: _vbo_handler.VBOHandler = None


def create_vbo() -> _vbo_handler.VBOHandler:
    global _vbo

    if _vbo is None:
        vertices, faces = create(0.5, 1.0)

        verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
        edges = _utils.compute_edges(faces)

        _vbo = _vbo_handler.VBOHandler('stripe', verts, edges, nrmls, faces, count)

    return _vbo


def create(radius, length):
    # Create the wire
    model = build123d.Cylinder(radius, length, align=build123d.Align.NONE)

    # Extract the axis of rotation from the wire to create the stripe
    wire_axis = model.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

    # the stripe is actually a separate 3D object and it carries with it a thickness.
    # The the stripe is not thick enough the wire color will show through it. We don't
    # want to use a hard coded thickness because the threshold for for this happpening
    # causes the stripe thickness to increaseto keep the "bleed through" from happening.
    # A remap of the diameter to a thickness range is done to get a thickness where the
    # bleed through will not occur while keeping the stripe from looking like it is not
    # apart of the wire.
    stripe_thickness = _utils.remap(
        radius * 2.0, old_min=0.5, old_max=5.0, new_min=0.005, new_max=0.015)

    edges = model.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(0, radius * 2 / 3.0)

    stripe_arc = build123d.Face(edges.offset_2d(stripe_thickness, side=build123d.Side.RIGHT))

    # Define the twist path to follow the wire
    twist = build123d.Helix(pitch=length / 2.0, height=length, radius=radius,
                            center=wire_axis.position, direction=wire_axis.direction,)

    # Sweep the arc to create the stripe
    s_line = build123d.Line(wire_axis.position, length * wire_axis.direction)
    stripe = build123d.sweep(stripe_arc, s_line, binormal=twist)

    return _utils.convert_model_to_mesh(stripe)
