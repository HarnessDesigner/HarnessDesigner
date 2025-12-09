
from typing import TYPE_CHECKING

import build123d
from OCP.gp import gp_Trsf, gp_Quaternion

from ...geometry import point as _point
from ...geometry import line as _line
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.project_db import pjt_bundle as _pjt_bundle


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


class Bundle(_Base3D):

    def __init__(self, editor3d: "_Editor3D", bundle_db: "_pjt_bundle.PJTBundle"):
        super().__init__(editor3d)
        self._db_obj = bundle_db
        self._part = bundle_db.part

        self._p1 = bundle_db.start_point.point
        self._p2 = bundle_db.stop_point.point
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

