
import build123d

from .. import utils as _utils
from ..geometry import point as _point
from ..gl import vbo as _vbo_handler


_vbo: _vbo_handler.VBOHandler = None


def create_vbo():
    global _vbo

    if _vbo is not None:
        return _vbo

    wire_r = 0.5
    diameter = 1.0

    # Create the wire
    cyl = build123d.Cylinder(wire_r, diameter, align=build123d.Align.NONE)

    # sphere1 = build123d.Sphere(wire_r)
    # sphere1 = sphere1.move(
    #     build123d.Location((0.0, 0.0, float(diameter)), (0, 0, 1)))

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
    # cyl += sphere1

    cyl2 = build123d.Cylinder(wire_r, diameter, align=build123d.Align.NONE)

    # this sphere is not used in the rendering, it is only used to track where
    # the second connection point should be, the first point being at 0, 0, 0
    sphere2 = build123d.Sphere(wire_r)
    sphere2 = sphere2.move(
        build123d.Location((0.0, 0.0, diameter), (0, 0, 1)))

    # if has_stripe:
    #     wire_axis = cyl2.faces().filter_by(
    #         build123d.GeomType.CYLINDER)[0].axis_of_rotation
    #
    #     edges = cyl2.edges().filter_by(build123d.GeomType.CIRCLE)
    #     edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    #     edges = edges.trim_to_length(
    #         0, float(diameter / _decimal(3) * _decimal(build123d.MM)))
    #
    #     stripe_thickness = python_utils.remap(
    #         diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)
    #
    #     stripe_arc = build123d.Face(edges.offset2d(
    #         float(stripe_thickness * _decimal(build123d.MM)),
    #         side=build123d.Side.RIGHT))
    #
    #     twist = build123d.Helix(
    #         pitch=20.0,
    #         height=float(diameter),
    #         radius=float(wire_r),
    #         center=wire_axis.position,
    #         direction=wire_axis.direction,
    #     )
    #
    #     stripe2 = build123d.sweep(
    #         stripe_arc,
    #         build123d.Line(wire_axis.position, float(diameter) * wire_axis.direction),
    #         binormal=twist
    #     )
    #
    #     stripe2 = stripe2.rotate(
    #         build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)
    #
    #     stripe2 = stripe2.move(build123d.Location(
    #         (float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))
    #
    #     stripe2 = stripe2.move(build123d.Location(
    #         (0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))
    #
    #     stripe2 = stripe2.move(build123d.Location(
    #         (0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))
    #
    #     stripe2 = stripe2.move(build123d.Location(
    #         (0.0, 0.0, -float(diameter)), (0, 0, 1)))
    #
    #     stripes = [None, stripe2]
    # else:
    #     stripes = []

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
    # cyl += sphere2
    #
    # if has_stripe:
    #     wire_axis = cyl.faces().filter_by(
    #         build123d.GeomType.CYLINDER)[0].axis_of_rotation
    #
    #     edges = cyl.edges().filter_by(build123d.GeomType.CIRCLE)
    #     edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    #     edges = edges.trim_to_length(
    #         0, float(diameter / _decimal(3) * _decimal(build123d.MM)))
    #
    #     stripe_thickness = python_utils.remap(
    #         diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)
    #     stripe_arc = build123d.Face(edges.offset2d(
    #         float(stripe_thickness * _decimal(build123d.MM)), side=build123d.Side.RIGHT))
    #
    #     twist = build123d.Helix(
    #         pitch=20.0,
    #         height=float(diameter),
    #         radius=float(wire_r),
    #         center=wire_axis.position,
    #         direction=wire_axis.direction,
    #     )
    #
    #     stripe1 = build123d.sweep(
    #         stripe_arc,
    #         build123d.Line(wire_axis.position, float(diameter) * wire_axis.direction),
    #         binormal=twist
    #     )
    #
    #     stripe1 = stripe1.move(build123d.Location(
    #         (0.0, 0.0, -float(diameter)), (0, 0, 1)))
    #
    #     stripes[0] = stripe1

    cyl = cyl.move(build123d.Location(
        (0.0, 0.0, -diameter), (0, 0, 1)))

    # sphere1 = sphere1.move(build123d.Location(
    #     (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    cn = sphere2.center()

    cn = _point.Point(cn.X, cn.Y, cn.Z)

    vertices, faces = _utils.convert_model_to_mesh(cyl)
    vertices, normals, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
    edges = _utils.compute_edges(faces)

    _vbo = _vbo_handler.VBOHandler('cylinder_helix', vertices, edges, normals, faces, count, cn)

    return _vbo
