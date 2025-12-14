from typing import TYPE_CHECKING

import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_bundle as _pjt_bundle


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0)

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, (corner1, corner2)


class Wire(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_bundle.PJTBundle"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = db_obj.part

        self._p1 = db_obj.start_point.point
        self._p2 = db_obj.stop_point.point

        self._model = None
        self._hit_test_rect = None

        self._triangles = []

        self._p1.Bind(self.recalculate)
        self._p2.Bind(self.recalculate)

    def recalculate(self, *_):
        (
            self._model,
            self._hit_test_rect
        ) = _build_model(self._p1, self._p2, self._part.od_mm)

        angle = _angle.Angle(self._p1, self._p2)
        p1, p2 = self._hit_test_rect
        p2 @= angle

        p1 += self._p1
        p2 += self._p1

    def hit_test(self, point: _point.Point) -> bool:
        if self._hit_test_rect is None:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):

        if not self._triangles:
            angle = _angle.Angle(self._p1, self._p2)
            normals, verts, count = renderer.build_mesh(self._model)

            verts @= angle
            verts += self._p1

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            renderer.model(normals, verts, count, None, self._part.color.ui.rgb_scalar, self.is_selected)
