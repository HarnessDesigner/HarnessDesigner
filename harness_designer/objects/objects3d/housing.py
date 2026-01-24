from typing import TYPE_CHECKING

from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin

if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_housing.Housing" = None

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):

        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)
        self._db_obj: "_pjt_housing.PJTHousing" = db_obj


# import build123d
# import numpy as np
#
# from .mixins import angle as _arrow_angle
# from .mixins import move as _arrow_move
# from . import cavity as _cavity
#
# from ...editor_3d import gl_object as _gl_object
# from ...geometry import point as _point
# from ...geometry import angle as _angle
# from ...wrappers.decimal import Decimal as _decimal
# from ...editor_3d import debug as _debug
#
#
# class Housing(_gl_object.GLObject, _arrow_move.MoveMixin, _arrow_angle.AngleMixin):
#
#     def __init__(self, parent, file, position: _point.Point):
#         super().__init__()
#         self.parent = parent
#         self._detent_update_counter: int = 0
#
#         self.cavities = []
#
#         self._model = self._read_mesh(file)
#
#         tris, normals, count = self.get_mesh_triangles(self._verts, self._faces)
#
#         verts = self._verts.reshape(-1, 3)
#
#         col_min = verts.min(axis=0)  # shape (3,) -> array([-0.7,  0.3, -1. ])
#         col_max = verts.max(axis=0)  # shape (3,) -> array([1.2, 3.1, 4. ])
#
#         p1 = _point.Point(*[_decimal(item) for item in col_min])
#         p2 = _point.Point(*[_decimal(item) for item in col_max])
#
#         self.hit_test_rect = [[p1, p2]]
#         self.adjust_hit_points()
#
#         p1, p2 = self.hit_test_rect[0]
#
#         center = ((p2 - p1) / _decimal(2.0)) + p1
#         c_offset = _point.Point(-center.x, -center.y, -center.z)
#         tris += c_offset
#
#         p1 += c_offset
#         p2 += c_offset
#
#         self._point = position
#         self._o_point = self._point.copy()
#         self._point.bind(self._update_point)
#
#         self._angle = _angle.Angle()
#
#         self._o_angle = self._angle.copy()
#         self._angle.bind(self._update_angle)
#
#         self._colors = [
#             np.full((count, 4), [0.4, 0.4, 0.4, 1.0], dtype=np.float32),
#             np.full((count, 4), [0.5, 0.5, 1.0, 0.40], dtype=np.float32),
#             np.full((count, 4), [0.5, 1.0, 0.5, 0.40], dtype=np.float32)
#         ]
#
#         normals @= self.angle
#         tris @= self.angle
#         tris += position
#
#         p1 @= self.angle
#         p2 @= self.angle
#
#         p1 += position
#         p2 += position
#
#         self.adjust_hit_points()
#         self._triangles = [[tris, normals, count]]
#
#         parent.canvas.add_object(self)
#
#     @staticmethod
#     def get_housing_triangles(model):
#         if Config.modeling.smooth_housings:
#             return model_to_mesh.get_smooth_triangles(model)
#         else:
#             return model_to_mesh.get_triangles(model)
#
#     def release_mouse(self):
#         self._detent_update_counter = 0
#
#     def get_first_points(self):
#         tris = self._triangles[0][0]
#         p = _point.Point(_decimal(tris[0][0][0]), _decimal(tris[0][0][1]), _decimal(tris[0][0][2]))
#         return [p]
#
#     @property
#     def triangles(self):
#         tris, norms, count = self._triangles[0]
#         if self._is_selected and self._detent_update_counter:
#             color = self._colors[2]
#         else:
#             color = self._colors[int(self._is_selected)]
#
#         triangles = [[tris, norms, color, count, color[0][-1] == 1.0]]
#         return triangles
#
#     def get_canvas(self):
#         return self.parent.canvas
#
#     @property
#     def position(self) -> _point.Point:
#         return self._point
#
#     @property
#     def angle(self) -> _angle.Angle:
#         return self._angle
#
#     @_debug.timeit
#     def _update_point(self, point: _point.Point):
#         delta = point - self._o_point
#         self._o_point = point.copy()
#
#         self._triangles[0][0] += delta
#
#         for p in self.hit_test_rect[0]:
#             p += delta
#
#         self.adjust_hit_points()
#
#     @_debug.timeit
#     def _update_angle(self, angle: _angle.Angle):
#         delta = angle - self._o_angle
#         self._o_angle = angle.copy()
#
#         self._triangles[0][0] -= self._point
#
#         self._triangles[0][0] @= delta
#         self._triangles[0][1] @= delta
#
#         # self.triangles[3][0] += self._point
#         self._triangles[0][0] += self._point
#
#         for p in self.hit_test_rect[0]:
#             p -= self._point
#             p @= delta
#             p += self._point
#
#         self.adjust_hit_points()
#
#     def add_cavity(self):
#         if len(self.cavities) < 6:
#             index = len(self.cavities)
#             name = 'ABCDEF'[index]
#
#             pos = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
#             angle = _angle.Angle.from_quat(np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64))
#             length = _decimal(40.0)
#
#             self.cavities.append(_cavity.Cavity(self, index, name, angle=angle, point=pos,
#                                                 length=length, terminal_size=_decimal(1.5)))
#
