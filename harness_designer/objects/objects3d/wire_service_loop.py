from typing import TYPE_CHECKING


import build123d
import python_utils

from ...geometry import point as _point
from ...geometry import line as _line
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop


def build_model(diameter: _decimal, has_stripe: bool):
    wire_r = diameter / _decimal(2.0)

    # Create the wire
    cyl = build123d.Cylinder(float(wire_r), float(diameter), align=build123d.Align.NONE)

    sphere1 = build123d.Sphere(wire_r)
    sphere1 = sphere1.move(build123d.Location((0.0, 0.0, float(diameter)), (0, 0, 1)))

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(diameter),
        pitch=float(diameter + diameter * _decimal(0.15)),
        height=float(diameter + diameter * _decimal(0.15)),
        cone_angle=0,
        direction=(1, 0, 0)
    )

    loop_profile = build123d.Circle(float(wire_r))

    swept_cylinder = build123d.sweep(path=loop_helix, sections=(loop_helix ^ 0) * loop_profile)

    # rotate and position the loop so it align with the cylinder
    swept_cylinder = swept_cylinder.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 90.0)
    swept_cylinder = swept_cylinder.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 9.35)
    swept_cylinder = swept_cylinder.move(build123d.Location((0.0, float(diameter), 0.0), (0, 1, 0)))

    # add the loop to the cylinder to make the part
    cyl += swept_cylinder
    cyl += sphere1

    cyl2 = build123d.Cylinder(float(wire_r), float(diameter), align=build123d.Align.NONE)
    sphere2 = build123d.Sphere(wire_r)
    sphere2 = sphere2.move(build123d.Location((0.0, 0.0, float(diameter)), (0, 0, 1)))

    if has_stripe:
        wire_axis = cyl2.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

        edges = cyl2.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(0, float(diameter / _decimal(3) * _decimal(build123d.MM)))

        stripe_thickness = python_utils.remap(diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)

        stripe_arc = build123d.Face(edges.offset_2d(float(stripe_thickness * _decimal(build123d.MM)), side=build123d.Side.RIGHT))

        twist = build123d.Helix(
            pitch=20.0,
            height=float(diameter),
            radius=float(wire_r),
            center=wire_axis.position,
            direction=wire_axis.direction,
        )

        stripe2 = build123d.sweep(
            stripe_arc,
            build123d.Line(wire_axis.position, float(diameter) * wire_axis.direction),
            binormal=twist
        )

        stripe2 = stripe2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)
        stripe2 = stripe2.move(build123d.Location((float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))
        stripe2 = stripe2.move(build123d.Location((0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))
        stripe2 = stripe2.move(build123d.Location((0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))
        stripes = [None, stripe2]

    else:
        stripes = []

    cyl2 = cyl2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)
    sphere2 = sphere2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    cyl2 = cyl2.move(build123d.Location((float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))
    sphere2 = sphere2.move(build123d.Location((float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    cyl2 = cyl2.move(build123d.Location((0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))
    sphere2 = sphere2.move(build123d.Location((0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    cyl2 = cyl2.move(build123d.Location((0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))
    sphere2 = sphere2.move(build123d.Location((0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))

    cyl += cyl2
    cyl += sphere2

    if has_stripe:
        wire_axis = cyl.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

        edges = cyl.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(0, float(diameter / _decimal(3) * _decimal(build123d.MM)))

        stripe_thickness = python_utils.remap(diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)
        stripe_arc = build123d.Face(edges.offset_2d(float(stripe_thickness * _decimal(build123d.MM)), side=build123d.Side.RIGHT))

        twist = build123d.Helix(
            pitch=20.0,
            height=float(diameter),
            radius=float(wire_r),
            center=wire_axis.position,
            direction=wire_axis.direction,
        )

        stripe1 = build123d.sweep(
            stripe_arc,
            build123d.Line(wire_axis.position, float(diameter) * wire_axis.direction),
            binormal=twist
        )
        stripes[0] = stripe1

    try:
        bbox = cyl.bounding_box()
        corner1 = _point.Point(*[_decimal(float(item)) for item in bbox.min])
        corner2 = _point.Point(*[_decimal(float(item)) for item in bbox.max])
    except AttributeError:
        bbmin = None
        bbmax = None
        for item in cyl:
            if isinstance(item, build123d.Shape):
                bbox = item.bounding_box()
                corner1 = _point.Point(*[_decimal(float(item)) for item in bbox.min])
                corner2 = _point.Point(*[_decimal(float(item)) for item in bbox.max])
                if bbmin is None or bbmin >= corner1:
                    bbmin = corner1
                if bbmax is None or bbmax <= corner2:
                    bbmax = corner2
        corner1 = bbmin
        corner2 = bbmax

    cn1 = sphere1.center()
    cn2 = sphere2.center()

    cn1 = _point.Point(_decimal(cn1.X), _decimal(cn1.Y), _decimal(cn1.Z))
    cn2 = _point.Point(_decimal(cn2.X), _decimal(cn2.Y), _decimal(cn2.Z))

    return cyl, stripes, [corner1, corner2], cn1, cn2


class WireServiceLoop(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = part = db_obj.part

        angle = db_obj.angle

        self._p1 = db_obj.start_point3d.point
        self._p1_backup = self._p1.copy()

        self._p2 = db_obj.stop_point3d.point

        self._is_visible = db_obj.is_visible
        self._primary_color = part.color
        self._ui_primary_color = self._primary_color.ui

        # TODO: Add stripe_color to global database
        self._stripe_color = part.stripe_color
        if self._stripe_color is None:
            self._ui_stripe_color = None
        else:
            self._ui_stripe_color = self._stripe_color.ui

        self._dia = part.od_mm

        self._model, self._stripe_models, self._hit_test_rect, start_point, stop_point = build_model(self._dia, self._stripe_color is not None)

        stop_point -= start_point

        hp1, hp2 = self._hit_test_rect
        hp1 -= start_point
        hp2 -= start_point

        arr = hp2.as_numpy
        arr @= angle.as_matrix
        x, y, z = arr.to_list()

        hp2.x = _decimal(x)
        hp2.y = _decimal(y)
        hp2.z = _decimal(z)

        hp1 += self._p1
        hp2 += self._p1

        arr = stop_point.as_numpy
        arr @= angle.as_matrix
        x, y, z = arr.to_list()

        stop_point.x = _decimal(x)
        stop_point.y = _decimal(y)
        stop_point.z = _decimal(z)

        stop_point += self._p1

        if self._p2 != stop_point:
            diff = stop_point - self._p2
            self._p2 += diff

        self._stripes = []
        self._stripe_normals = []
        self._triangle_count = 0
        self._stripe_triangle_count = 0

        self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)

        self._triangles -= start_point.as_numpy
        self._triangles @= angle.as_matrix
        self._triangles += self._p1.as_numpy

        if self._stripe_color is not None:
            for stripe in self._stripe_models:
                stripe_normals, stripe_triangles, stripe_triangle_count = self._get_triangles(stripe)
                stripe_triangles -= start_point.as_numpy
                stripe_triangles @= angle.as_matrix
                stripe_triangles += self._p1.as_numpy

                self._stripes.append((stripe_normals, stripe_triangles, stripe_triangle_count))

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
        self._db_obj.is_visible = value

    def hit_test(self, point: _point.Point) -> bool:
        if not self._is_visible:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if not self._is_visible:
            return

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_primary_color.rgba_scalar)

        for stripe_normals, stripe_triangles, stripe_triangle_count in self._stripes:
            renderer.draw_triangles(stripe_normals, stripe_triangles, stripe_triangle_count, self._ui_stripe_color.rgba_scalar)
