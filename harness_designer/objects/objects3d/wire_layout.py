from typing import TYPE_CHECKING, Union


import build123d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


def _build_model(diameter: _decimal):
    model = build123d.Sphere(float(diameter / _decimal(2)))

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))

    return model, [corner1, corner2]


class WireLayout(_Base3D):

    def __init__(self, editor3d: "_editor_3d.Editor3D",
                 db_obj: "_pjt_wire3d_layout.PJTWire3DLayout"):

        super().__init__(editor3d)
        self._db_obj = db_obj

        self._center = db_obj.point.point
        self._o_center = self._center.copy()
        self._model = None
        self._hit_test_rect = None
        self._triangles = []

        self._center.Bind(self._update_center)

    def _update_center(self, *_):
        if self._is_deleted:
            return

        if self._triangles:
            verts = self._triangles[0][1]
            center_diff = self._center - self._o_center
            verts += center_diff

        if self._hit_test_rect is not None:
            p1, p2 = self._hit_test_rect

            center_diff = self._center - self._o_center
            p1 += center_diff
            p2 += center_diff

        self._o_center = self._center.copy()

    def recalculate(self, *_):
        if self._is_deleted:
            return

        if self._model is None:
            self._model, self._hit_test_rect = _build_model(self._db_obj.diameter)

            p1, p2 = self._hit_test_rect
            p1 += self._center
            p2 += self._center

        self._triangles = []

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
            verts += self._center

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            color = (0.2, 0.2, 0.2, 1.0)
            for obj in self._db_obj.attached_objects:
                color = obj.part.color.ui.rgba_scalar
                break

            renderer.model(normals, verts, count, None, color, self.is_selected)
