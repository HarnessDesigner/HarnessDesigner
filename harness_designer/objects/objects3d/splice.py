
from typing import TYPE_CHECKING

import build123d
from OCP.gp import gp_Trsf, gp_Quaternion

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_splice as _pjt_splice


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0) + _decimal(0.1)

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, (corner1, corner2)


class Splice(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_splice.PJTSplice"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = part = db_obj.part

        self._p1 = db_obj.point1_3d.point
        self._p2 = db_obj.point2_3d.point
        self._p3 = db_obj.point3_3d.point

        self._o_p1 = self._p1.copy()
        self._o_p3 = self._p3.copy()

        self._model = None
        self._hit_test_rect = None

        self._triangles = []

        model3d = part.model3d

        if model3d is None:
            self._is_model3d = False
        else:
            self._is_model3d = True

        self._p1.Bind(self.recalculate)
        self._p2.Bind(self.recalculate)

    def recalculate(self, *_):
        if self._is_deleted:
            return

        if self._is_model3d and self._model is None:
            self._model, self._hit_test_rect = self._part.model3d.model

            if self._model is None:
                self._is_model3d = False
                self._model, self._hit_test_rect = _build_model(self._p1, self._p3, self._db_obj.wire.part.od_mm)
            else:
                p1, p2 = self._hit_test_rect

                angle = _angle.Angle.from_points(self._p1, self._p3)
                p2 @= angle

                p1 += self._p1
                p2 += self._p1

        elif not self._is_model3d and self._model is None:
            self._model, self._hit_test_rect = _build_model(self._p1, self._p3, self._db_obj.wire.part.od_mm)

            p1, p2 = self._hit_test_rect
            angle = _angle.Angle.from_points(self._p1, self._p3)
            p2 @= angle

            p1 += self._p1
            p2 += self._p1

        else:
            p1, p2 = self._hit_test_rect

            p1 -= self._o_p1
            p2 -= self._o_p1

            angle1 = _angle.Angle.from_points(self._p1, self._p3)
            angle2 = _angle.Angle.from_points(self._o_p1, self._o_p3)

            angle = angle2 - angle1
            p2 @= angle
            p1 += self._p1
            p2 += self._p1

            verts = self._triangles[0][1]

            verts -= self._o_p1
            verts @= angle
            verts += self._p1

            self._o_p1 = self._p1.copy()
            self._o_p3 = self._p3.copy()

    def hit_test(self, point: _point.Point) -> bool:
        if self._is_deleted:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._is_deleted:
            return

        if not self._triangles:
            normals, verts, count = renderer.build_mesh(self._model)
            angle = _angle.Angle(self._p1, self._p3)

            verts @= angle
            verts += self._p1

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            renderer.model(normals, verts, count, None, self._part.color.ui.rgb_scalar, self.is_selected)
