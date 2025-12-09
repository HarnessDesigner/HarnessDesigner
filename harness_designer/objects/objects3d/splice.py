
from typing import TYPE_CHECKING

import build123d
from OCP.gp import gp_Trsf, gp_Quaternion

from ...geometry import point as _point
from ...geometry import line as _line
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_splice as _pjt_splice


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0)

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    angle = line.get_angle(p1)

    transformation = gp_Trsf()
    quaternion = gp_Quaternion(*angle.quat)
    transformation.SetRotation(quaternion)

    model = model._apply_transform(transformation)  # NOQA

    model.move(build123d.Location(p1.as_float))

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, (corner1, corner2)


class Splice(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_splice.PJTSplice"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = part = db_obj.part

        model3d = part.model3d

        if model3d is not None:
            model, hit_test_rect = model3d.model

            if model is None:
                is_model3d = False
                model, hit_test_rect = _build_model(part.length, part.width, part.height, part.blade_size, part.gender)
            else:
                is_model3d = True
        else:
            model, hit_test_rect = _build_model(part.length, part.width, part.height, part.blade_size, part.gender)
            is_model3d = False

        self._is_model3d = is_model3d
        self._model = model
        self._hit_test_rect = hit_test_rect
        self._o_hit_test_rect = hit_test_rect

        self._triangles = None
        self._normals = None
        self._triangle_count = 0



        self._p1 = db_obj.start_point.point
        self._p2 = db_obj.stop_point.point
        self._color = self._part.color
        self._ui_color = self._color.ui

        # TODO: Add diameter to the bundle table
        self._dia = bundle_db.diameter

        self._model, self._hit_test_rect = _build_model(self._p1, self._p2, self._dia)

        self._triangles = None
        self._normals = None
        self._triangle_count = 0

        p1, p2 = self._hit_test_rect
        p1 += self._p1
        p2 += self._p1

        self._p1.Bind(self.recalculate)
        self._p2.Bind(self.recalculate)

    @property
    def diameter(self) -> _decimal:
        return self._dia

    @diameter.setter
    def diameter(self, value: _decimal):
        self._dia = value
        self._db_obj.diameter = value
        self.recalculate()

    def recalculate(self, *_):
        self._model, self._hit_test_rect = _build_model(self._p1, self._p2, self._dia)

        p1, p2 = self._hit_test_rect
        p1 += self._p1
        p2 += self._p1

        self._triangles = None

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_color.rgb_scalar)

    @classmethod
    def new(cls, mouse_point: _point.Point, world_point: _point.Point):



