from typing import TYPE_CHECKING


import build123d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor_3d as editor_3d
    from ...database.global_db import housing as _housing
    from ...database.project_db import pjt_housing as _pjt_housing


def _build_model(h_data: "_housing.Housing"):
    length = h_data.length
    width = h_data.width
    height = h_data.height
    centerline = h_data.centerline
    num_pins = h_data.num_pins
    num_rows = h_data.rows
    gender = h_data.gender
    terminal_sizes = h_data.terminal_sizes

    if not length:
        if num_pins:
            if not centerline and terminal_sizes:
                centerline = terminal_sizes[0] * _decimal(1.20)

            if centerline and num_rows:
                pin_count = num_pins / num_rows
                length = pin_count * centerline + centerline
            elif centerline:
                length = num_pins * centerline + centerline

    if not width:
        if num_rows:
            width = _decimal(8) * num_rows
        else:
            width = _decimal(8)

    if not length:
        length = width * _decimal(2.0)

    if not height:
        height = width / length * width

    model = build123d.Box(float(length), float(width), float(height))
    box = build123d.Box(float(length), float(width * _decimal(0.90)), float(height * _decimal(0.90)))
    # z_axis = height
    # y_axis = width
    # x_axis = length
    box.move(build123d.Location((float(length / _decimal(3) / _decimal(2)), 0.0, 0.0)))
    model -= box

    if gender == 'Female':
        box = build123d.Box(float(length * _decimal(0.90)), float(width * _decimal(0.75)), float(height * _decimal(0.75)))
        box.move(build123d.Location((float((length - (length * _decimal(0.90))) / _decimal(2)), 0.0, 0.0)))
        model += box

    bb = model.bounding_box()
    corner1 = _point.Point(*[_decimal(float(item)) for item in bb.min])
    corner2 = _point.Point(*[_decimal(float(item)) for item in bb.max])

    return model, (corner1, corner2)


class Housing(_Base3D):

    _db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, editor3d: "editor_3d.Editor3D", db_obj: "_pjt_housing.PJTHousing"):
        super().__init__(editor3d)

        self._part = part = db_obj.part

        self._center = db_obj.point3d.point
        self._center.Bind(self.recalculate)
        self._center.add_object(self)

        self._o_center = None
        self._o_angle = None

        self._db_obj = db_obj

        if part.model3d is not None:
            self._is_model3d = True
        else:
            self._is_model3d = False

        self._model = None
        self._hit_test_rect = None

        self._triangles = []

    def recalculate(self, *_):
        if self._is_deleted:
            return

        if self._model is None:
            if self._is_model3d:
                self._model, self._hit_test_rect = self._part.model3d.model

                if self._model is None:
                    self._is_model3d = False
                    self._model, self._hit_test_rect = _build_model(self._part)
            else:
                self._model, self._hit_test_rect = _build_model(self._part)

            self._o_center = self._center.copy()
            self._o_angle = self._db_obj.angle_3d.copy()

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

            if self._is_model3d:
                model3d = self._part.model3d

                offset = model3d.offset
                angle = model3d.angle

                verts @= angle
                verts += offset

                p1, p2 = self._hit_test_rect

                p1 += offset
                p2 @= angle
                p2 += offset

            p1, p2 = self._hit_test_rect
            angle = self._db_obj.angle_3d

            p2 @= angle
            p1 += self._center
            p2 += self._center

            verts @= angle
            verts += self._center
            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:

            renderer.model(normals, verts, count, None, self._part.color.ui.rgba_scalar, self.is_selected)
