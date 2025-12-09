from typing import TYPE_CHECKING, Union


import build123d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from ...database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


def _build_model(diameter: _decimal):
    model = build123d.Sphere(float(diameter / _decimal(2)))

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))

    return model, [corner1, corner2]


class Layout(_Base3D):

    def __init__(self, editor3d: "_Editor3D",
                 layout_db: Union["_pjt_wire3d_layout.PJTWire3DLayout", "_pjt_bundle_layout.PJTBundleLayout"]):

        super().__init__(editor3d)
        self._db_obj = layout_db

        self._center = layout_db.point.point
        # TODO: Add color to wire layout & bundle layout tables
        self._color = layout_db.color
        self._ui_color = self._color.ui

        # TODO: Add diameter to wire layout table
        self._dia = layout_db.diameter

        self._model, self._hit_test_rect = _build_model(self._dia)

        self._triangles = None
        self._normals = None
        self._triangle_count = 0
        self._center.Bind(self._update_center)

        p1, p2 = self._hit_test_rect
        p1 += self._center
        p2 += self._center

    @property
    def diameter(self):
        return self._dia

    @diameter.setter
    def diameter(self, value):
        self._dia = value
        self._db_obj.diameter = value
        self._model, self._hit_test_rect = _build_model(self._dia)
        p1, p2 = self._hit_test_rect
        p1 += self._center
        p2 += self._center

    def recalculate(self):
        self._triangles = None

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._triangles is None:
            self._normals, self._triangles, self._triangle_count = self._get_triangles(self._model)
            self._triangles += self._center.as_numpy

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count, self._ui_color.rgb_scalar)

    def _update_center(self, *_):
        bbox = self._model.bounding_box()
        corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
        corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))
        corner1 += self._center
        corner2 += self._center

        self._hit_test_rect = [corner1, corner2]
        self.recalculate()

    def move(self, point: _point.Point) -> None:
        self._center += point
