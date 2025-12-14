from typing import TYPE_CHECKING

import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal, label):
    line = _line.Line(p1, p2)
    length = line.length()
    radius = diameter / _decimal(2.0)

    # Create the wire
    model = build123d.Cylinder(float(radius), float(length), align=build123d.Align.NONE)

    if label:
        text = None
    else:
        text = None

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, text, (corner1, corner2)


class WireMarker(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_wire_marker.PJTWireMarker"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = db_obj.part
        self._p1 = db_obj.point_3d.point
        self.wire = db_obj.wire
        self.wire_p1 = self.wire.start_point3d.point
        self.wire_p2 = self.wire.stop_point3d.point

        self._model = None
        self._label = None
        self._hit_test_rect = None

        self._triangles = []
        self._label_triangles = []

        self._p1.Bind(self.recalculate)
        self.wire_p1.Bind(self.recalculate)
        self.wire_p2.Bind(self.recalculate)

    def recalculate(self, *_):
        angle = _angle.Angle.from_points(self.wire_p1, self.wire_p2)
        line = _line.Line(self._p1, None, self._part.length, angle)

        (
            self._model,
            self._label,
            self._hit_test_rect
        ) = _build_model(self._p1, line.p2, self.wire.part.od_mm, self._db_obj.label)

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
            angle = _angle.Angle.from_points(self.wire_p1, self.wire_p2)

            normals, verts, count = renderer.build_mesh(self._model)
            verts @= angle
            verts += self._p1

            self._triangles = [[normals, verts, count]]
            if self._label is not None:
                normals, verts, count = renderer.build_mesh(self._label)

                verts @= angle
                verts += self._p1

                self._label_triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            renderer.model(normals, verts, count, None, self._part.color.ui.rgb_scalar, self.is_selected)

        for normals, verts, count in self._label_triangles:
            renderer.model(normals, verts, count, None, (0.2, 0.2, 0.2, 1.0), self.is_selected)
