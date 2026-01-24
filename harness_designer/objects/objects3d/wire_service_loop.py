from typing import TYPE_CHECKING


import build123d
import python_utils

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin
from ... import gl_materials as _gl_materials
from ... import Config

if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from .. import wire_service_loop as _wire_service_loop


Config = Config.editor3d


def _build_model(diameter: _decimal, has_stripe: bool):
    wire_r = diameter / _decimal(2.0)

    # Create the wire
    cyl = build123d.Cylinder(
        float(wire_r), float(diameter), align=build123d.Align.NONE)

    # sphere1 = build123d.Sphere(wire_r)
    # sphere1 = sphere1.move(
    #     build123d.Location((0.0, 0.0, float(diameter)), (0, 0, 1)))

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(diameter),
        pitch=float(diameter + diameter * _decimal(0.15)),
        height=float(diameter + diameter * _decimal(0.15)),
        cone_angle=0,
        direction=(1, 0, 0)
    )

    loop_profile = build123d.Circle(float(wire_r))

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

    cyl2 = build123d.Cylinder(
        float(wire_r), float(diameter), align=build123d.Align.NONE)

    # this sphere is not used in the rendering, it is only used to track where
    # the second connection point should be, the first point being at 0, 0, 0
    sphere2 = build123d.Sphere(wire_r)
    sphere2 = sphere2.move(
        build123d.Location((0.0, 0.0, float(diameter)), (0, 0, 1)))

    if has_stripe:
        wire_axis = cyl2.faces().filter_by(
            build123d.GeomType.CYLINDER)[0].axis_of_rotation

        edges = cyl2.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(
            0, float(diameter / _decimal(3) * _decimal(build123d.MM)))

        stripe_thickness = python_utils.remap(
            diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)

        stripe_arc = build123d.Face(edges.offset2d(
            float(stripe_thickness * _decimal(build123d.MM)),
            side=build123d.Side.RIGHT))

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

        stripe2 = stripe2.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

        stripe2 = stripe2.move(build123d.Location(
            (float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

        stripe2 = stripe2.move(build123d.Location(
            (0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

        stripe2 = stripe2.move(build123d.Location(
            (0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))

        stripe2 = stripe2.move(build123d.Location(
            (0.0, 0.0, -float(diameter)), (0, 0, 1)))

        stripes = [None, stripe2]

    else:
        stripes = []

    cyl2 = cyl2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    sphere2 = sphere2.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    cyl2 = cyl2.move(build123d.Location(
        (float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    sphere2 = sphere2.move(build123d.Location(
        (float(diameter + diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, -float(diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -float(diameter * _decimal(0.15))), (0, 0, 1)))

    cyl += cyl2
    # cyl += sphere2

    if has_stripe:
        wire_axis = cyl.faces().filter_by(
            build123d.GeomType.CYLINDER)[0].axis_of_rotation

        edges = cyl.edges().filter_by(build123d.GeomType.CIRCLE)
        edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
        edges = edges.trim_to_length(
            0, float(diameter / _decimal(3) * _decimal(build123d.MM)))

        stripe_thickness = python_utils.remap(
            diameter, old_min=1.25, old_max=5.0, new_min=0.010, new_max=0.025)
        stripe_arc = build123d.Face(edges.offset2d(
            float(stripe_thickness * _decimal(build123d.MM)), side=build123d.Side.RIGHT))

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

        stripe1 = stripe1.move(build123d.Location(
            (0.0, 0.0, -float(diameter)), (0, 0, 1)))

        stripes[0] = stripe1

    cyl = cyl.move(build123d.Location(
        (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    # sphere1 = sphere1.move(build123d.Location(
    #     (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -float(diameter)), (0, 0, 1)))

    cn = sphere2.center()

    cn = _point.Point(_decimal(cn.X), _decimal(cn.Y), _decimal(cn.Z))

    return cyl, stripes, cn


class WireServiceLoop(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_wire_service_loop.WireServiceLoop" = None

    def __init__(self, parent: "_wire_service_loop.WireServiceLoop",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):

        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)
        _base3d.Base3D.__init__(self, parent)
        self._db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = db_obj

        self._part = part = db_obj.part
        self._color = self._part.color.ui
        self._stripe_color = self._part.stripe_color
        self._material = _gl_materials.Plastic(self._color.rgba_scalar)

        if self._stripe_color is None:
            self._stripe_material = None
        else:
            self._stripe_material = _gl_materials.Plastic(self._stripe_color.ui.rgba_scalar)

        self._position = db_obj.start_point3d.point
        self._o_position = self._position.copy()

        self._position2 = db_obj.stop_point3d.point
        self._is_visible = db_obj.is_visible

        self._angle = _angle.Angle.from_points(self._position, self._position2)
        self._o_angle = self._angle.copy()

        model, stripe_models, stop_point = _build_model(part.od_mm, self._stripe_color is not None)

        vertices, faces = self._convert_model_to_mesh(model)
        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris @= self._angle
        tris += self._position

        nrmls @= self._angle

        stop_point @= self._angle
        stop_point += self._position

        if self._position2 != stop_point:
            diff = stop_point - self._position2
            self._position2 += diff

        p1, p2 = self._compute_rect(tris)
        bb = self._compute_bb(p1, p2)

        self._rect.append([p1, p2])
        self._bb.append(bb)

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

        for i, stripe in enumerate(stripe_models):
            vertices, faces = self._convert_model_to_mesh(model)
            tris, nrmls, count = self._get_triangles(vertices, faces)

            tris @= self._angle
            tris += self._position

            nrmls @= self._angle

            stripe_models[i] = [tris, nrmls, count]

        if stripe_models:
            self._triangles.append(_base3d.TriangleRenderer(stripe_models, self._stripe_material))

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_wires:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
        self._db_obj.is_visible = value
