from typing import TYPE_CHECKING
import weakref

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_cover as _pjt_cover

from ... import Config
from ... import gl_materials as _gl_materials

Config = Config.editor3d


class Cover(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):

    def __init__(self, parent, db_obj: "_pjt_cover.PJTCover"):
        super().__init__(parent)

        self._db_obj = db_obj
        self._part = db_obj.part

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle3d
        self._o_angle = self._angle.copy()

        self._color = self._part.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)

        model = self._part.model3d

        self._material = _gl_materials.Plastic(self._color.rgba_scalar)

        triangles = []

        if model is None:
            self._model = None
        else:
            self._model = model.model
            for verts, faces in self._model:
                tris, nrmls, count = self._get_triangles(verts, faces)
                tris @= self._angle
                nrmls @= self._angle
                tris += self._position

                p1, p2 = self._compute_rect(tris)
                # self._adjust_hit_points(p1, p2)
                bb = self._compute_bb(p1, p2)

                self._rect.append([p1, p2])
                self._bb.append(bb)
                triangles.append([tris, nrmls, count])

        self._triangles = [_base3d.TriangleRenderer(triangles, self._material)]

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_covers:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)
