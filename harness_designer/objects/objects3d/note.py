from typing import TYPE_CHECKING
import weakref
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin
from ... import gl_materials as _gl_materials


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


build123d.REGULAR
build123d.BOLD
build123d.BOLDITALIC
build123d.ITALIC

build123d.LEFT
build123d.CENTER
build123d.RIGHT

build123d.BOTTOM
build123d.CENTER
build123d.TOP
build123d.TOPFIRSTLINE


class Note(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_note.Note" = None

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)
        
        self._db_obj: "_pjt_note.PJTNote" = db_obj

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle3d
        self._o_angle = self._angle.copy()

        self._color = db_obj.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)

        self._material = _gl_materials.Metallic(self._color.rgba_scalar)

        self._build()

    def _build(self):
        font_size = self._db_obj.size_3d
        text = self._db_obj.note
        h_align = self._db_obj.h_align_3d
        v_align = self._db_obj.v_align_3d
        style = self._db_obj.style_3d

        label = build123d.Text(text, font_size=font_size, font_style=style, text_align=(h_align, v_align))
        model = build123d.extrude(label, amount=0.1)

        vertices, faces = self._convert_model_to_mesh(model)

        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris @= self._angle
        nrmls @= self._angle

        tris += self._position

        p1, p2 = self._compute_rect(tris)
        self._rect = [[p1, p2]]
        bb = self._compute_bb(p1, p2)
        self._bb = [bb]

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

    def _get_triangles(self, vertices, faces):
        return self._compute_vertex_normals(vertices, faces)
