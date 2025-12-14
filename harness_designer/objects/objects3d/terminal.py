from typing import TYPE_CHECKING


import build123d

from ... import gl_materials as _gl_materials
from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...geometry import angle as _angle
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
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

    def __init__(self, editor3d: "_editor_3d.Editor3D",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = part = db_obj.part
        self._p1 = db_obj.point3d

        if part.model3d is not None:
            self._is_model3d = True
        else:
            self._is_model3d = False

        self._model = None
        self._hit_test_rect = None
        self._triangles = []

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

        color = self._db_obj.table.db.global_db.colors_table[color]
        self._color = color.ui
        self._material = _gl_materials.Polished(color.ui.rgba_scalar)

    def recalculate(self, *_):
        model3d = self._part.model3d

        if self._is_model3d:
            self._model, self._hit_test_rect = model3d.model

            if self._model is None:
                self._is_model3d = False
                self._model, self._hit_test_rect = _build_model(self._part.length, self._part.width,
                                                                self._part.height, self._part.blade_size,
                                                                self._part.gender.name)
        else:
            self._model, self._hit_test_rect = _build_model(self._part.length, self._part.width,
                                                            self._part.height, self._part.blade_size,
                                                            self._part.gender.name)

        self._triangles = []

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
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
            angle = self._db_obj.angle3d
            p2 @= angle

            p1 += self._p1
            p2 += self._p1

            verts @= angle
            verts += self._p1

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            renderer.model(normals, verts, count, self._material, self._color.rgba_scalar, self.is_selected)
