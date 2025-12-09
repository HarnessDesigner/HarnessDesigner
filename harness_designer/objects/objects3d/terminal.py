from typing import TYPE_CHECKING


import build123d

from ... import gl_materials as _gl_materials
from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import angle as _angle
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from .. import Editor3D as _Editor3D
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from ...wrappers import color as _color


def _build_model(length: _decimal, width: _decimal, height: _decimal, blade_size: _decimal, gender: str):
    if gender == 'Female':
        model = build123d.Box(float(length), float(width), float(height))
    else:

        wire_end = length * _decimal(0.66)
        connection_end = length * _decimal(0.33)

        model = build123d.Box(float(wire_end), float(width), float(height))

        blade_height = height * _decimal(0.1)

        x = (width - blade_size) / _decimal(2.0)
        y = (height - blade_height) / _decimal(2.0)
        z = connection_end

        box = build123d.Box(float(connection_end), float(blade_size), float(blade_height))
        box.move(build123d.Location((float(x), float(y), float(z))))
        model += box

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))

    return model, [corner1, corner2]


class Terminal(_Base3D):

    def __init__(self, editor3d: "_Editor3D",
                 terminal_db: "_pjt_terminal.PJTTerminal"):

        super().__init__(editor3d)

        self._db_obj = terminal_db
        self._part = part = terminal_db.part

        model3d = part.model3d

        if model3d is not None:
            model, hit_test_rect = model3d.model

            if model is None:
                is_model3d = False
                model, hit_test_rect = _build_model(part.length, part.width,
                                                    part.height, part.blade_size,
                                                    part.gender)
            else:
                is_model3d = True
        else:
            model, hit_test_rect = _build_model(part.length, part.width,
                                                part.height, part.blade_size,
                                                part.gender)
            is_model3d = False

        self._is_model3d = is_model3d
        self._model = model
        self._hit_test_rect = hit_test_rect
        self._o_hit_test_rect = hit_test_rect

        self._triangles = None
        self._normals = None
        self._triangle_count = 0

        symbol = part.plating.symbol

        if symbol.startswith('Sn'):
            color = 'Tin'
        elif symbol.startswith('Cu'):
            color = 'Copper'
        elif symbol.startswith('Al'):
            color = 'Aluminum'
        elif symbol.startswith('Ti'):
            color = 'Titanium'
        elif symbol.startswith('Zn'):
            color = 'Zinc'
        elif symbol.startswith('Au'):
            color = 'Gold'
        elif symbol.startswith('Ag'):
            color = 'Silver'
        elif symbol.startswith('Ni'):
            color = 'Nickel'
        else:
            color = 'Tin'

        color = self._part._table.db.colors_table[color]
        self._ui_color = color.ui
        self._material = _gl_materials.Polished(color.ui.rgba_scalar)

    def recalculate(self, *_):
        self._triangles = None

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._triangles is None:
            self._hit_test_rect = [item.copy() for item in self._o_hit_test_rect]
            (
                self._normals,
                self._triangles,
                self._triangle_count
            ) = self._get_triangles(self._model)

            if self._is_model3d:
                model3d = self._part.model3d

                offset = model3d.offset
                angle = model3d.angle

                self._triangles @= angle
                self._triangles += offset

                for p in self._hit_test_rect:
                    p @= angle
                    p += offset.as_numpy

            angle = self._db_obj.angle
            point = self._db_obj.point3d.point

            for p in self._hit_test_rect:
                p @= angle
                p += point

            self._triangles @= angle
            self._triangles += point.as_numpy

        renderer.draw_triangles(self._normals, self._triangles, self._triangle_count,
                                self._ui_color.rgba_scalar, self._material)

    @property
    def color(self) -> "_color.Color":
        return self._ui_color

    @property
    def angle(self) -> _angle.Angle:
        return self._db_obj.angle

    @angle.setter
    def angle(self, value: _angle.Angle):
        angle = self._db_obj.angle

        angle_diff = value - angle

        self._db_obj.angle += angle_diff
        self.recalculate(None)

    def move(self, point: _point.Point) -> None:
        p = self._db_obj.point3d.point
        p += point
        self.recalculate(None)



