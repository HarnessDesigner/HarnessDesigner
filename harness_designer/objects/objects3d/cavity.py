# from typing import TYPE_CHECKING
#
# import build123d
# import numpy as np
#
# from .mixins import angle as _arrow_angle
# from .mixins import move as _arrow_move
#
#
# from ...geometry import point as _point
# from ...geometry import angle as _angle
# from ...wrappers.decimal import Decimal as _decimal
#
# if TYPE_CHECKING:
#     from . import housing as _housing
#
#
# class Cavity(_gl_object.GLObject, _arrow_move.MoveMixin, _arrow_angle.AngleMixin):
#
#     def __init__(self, parent: "_housing.Housing", index: int,
#                  name: str, angle: _angle.Angle, point: _point.Point,
#                  length: _decimal, terminal_size: _decimal, model3d: str = None):
#
#         super().__init__()
#
#         self.parent: "_housing.Housing" = parent
#         self.index = index
#         self.name = name
#         self._rel_angle = angle
#         self._o_rel_angle = angle.copy()
#         self._rel_point = point
#         self._o_rel_point = point.copy()
#         self._test_point = point.copy()
#         self._test_point.z -= _decimal(20)
#         self._test_point @= angle
#
#         self._detent_update_counter = 0
#
#         self._triangles = []
#         self._colors = []
#
#         a_angle = parent.angle + angle
#         a_point = parent.position + point
#
#         self._abs_angle = a_angle
#         self._o_abs_angle = a_angle.copy()
#
#         self._abs_point = a_point
#         self._o_abs_point = a_point.copy()
#
#         self._rel_point.bind(self._update_rel_position)
#         self._abs_point.bind(self._update_abs_position)
#
#         self._rel_angle.bind(self._update_rel_angle)
#         self._abs_angle.bind(self._update_abs_angle)
#
#         self.length = length
#         self.height = terminal_size
#         self.width = terminal_size
#         self.terminal_size = terminal_size
#         self._use_cylinder = False
#
#         point = parent.position
#         self._h_point = point.copy()
#         point.bind(self._update_h_position)
#
#         angle = parent.angle
#         self._h_angle = angle.copy()
#         angle.bind(self._update_h_angle)
#         self.model3d = model3d
#         self.build_model()
#
#         self._verts = None
#         self._faces = None
#
#         parent.parent.canvas.add_object(self)
#
#     def release_mouse(self):
#         self._detent_update_counter = 0
#
#     def get_first_points(self):
#         tris = self._triangles[0][0]
#         p = _point.Point(_decimal(tris[0][0]),
#                          _decimal(tris[0][1]), _decimal(tris[0][2]))
#         return [p]
#
#     @property
#     def position(self) -> _point.Point:
#         return self._abs_point
#
#     @property
#     def rel_position(self) -> _point.Point:
#         return self._rel_point
#
#     @property
#     def angle(self) -> _angle.Angle:
#         return self._abs_angle
#
#     @property
#     def rel_angle(self) -> _angle.Angle:
#         return self._rel_angle
#
#     def _update_rel_angle(self, angle: _angle.Angle):
#         inverse = self._o_rel_angle.inverse
#
#         test_point = self._test_point.copy()
#         test_point -= self._rel_point
#         test_point @= inverse
#         test_point @= angle
#         test_point += self._rel_point
#
#         delta = test_point - self._test_point
#         self._test_point += delta
#
#         delta = angle - self._o_rel_angle
#         self._o_rel_angle += delta
#
#         test_point += self._h_point
#
#         new_angle = _angle.Angle.from_points(self._h_point, test_point)
#
#         delta = new_angle - self._abs_angle
#
#         inverse = self._abs_angle
#
#         # self.triangles[0][0] -= self._h_point
#         self._triangles[0][0] -= self._h_point
#
#         self._triangles[0][0] @= inverse
#         self._triangles[0][1] @= inverse
#
#         self._triangles[0][0] @= new_angle
#         self._triangles[0][1] @= new_angle
#
#         # self.triangles[0][0] += self._h_point
#         self._triangles[0][0] += self._h_point
#
#         for p in self.hit_test_rect[0]:
#             p -= self._h_point
#             p @= inverse
#             p @= new_angle
#             p += self._h_point
#
#         self._abs_angle.unbind(self._update_abs_angle)
#         self._abs_angle += delta
#         self._o_abs_angle += delta
#         self._abs_angle.bind(self._update_abs_angle)
#
#     def _update_abs_angle(self, angle: _angle.Angle):
#         inverse = self._h_angle.inverse
#         rel_inverse = self._rel_angle.inverse
#         abs_inverse = self._abs_angle.inverse
#
#         p1 = self._rel_point.copy()
#         p2 = self._test_point.copy()
#
#         p2 -= p1
#         p2 @= rel_inverse
#         p2 += p1
#         p1 @= inverse
#         p2 @= inverse
#         p1 @= angle
#         p2 @= angle
#         p2 -= p1
#         p2 @= self._rel_angle
#
#         new_rel_angle = _angle.Angle.from_points(p1, p2)
#
#         rel_angle_delta = new_rel_angle - self._rel_angle
#         rel_point_delta = p1 - self._rel_point
#
#         self._rel_angle.unbind(self._update_rel_angle)
#         self._rel_point.unbind(self._update_rel_position)
#         self._rel_angle += rel_angle_delta
#         self._rel_point += rel_point_delta
#         self._test_point += rel_point_delta
#         self._rel_angle.bind(self._update_rel_angle)
#         self._rel_point.bind(self._update_rel_position)
#
#         normals = self._triangles[0][1]
#
#         # normals -= self._h_point
#         normals @= abs_inverse
#         normals @= angle
#         # normals += self._h_point
#
#         triangles = self._triangles[0][0]
#         triangles -= self._h_point
#         triangles @= abs_inverse
#         triangles @= angle
#         triangles += self._h_point
#
#         for p in self.hit_test_rect[0]:
#             p -= self._h_point
#             p @= abs_inverse
#             p @= angle
#             p += self._h_point
#
#         self.adjust_hit_points()
#         self._o_abs_angle = angle.copy()
#
#         abs_point = self._abs_point.copy()
#         abs_point -= self._h_point
#         abs_point @= abs_inverse
#         abs_point @= angle
#         abs_point += self._h_point
#
#         abs_point_delta = abs_point - self._abs_point
#         self._abs_point += abs_point_delta
#         self._o_abs_point += abs_point_delta
#
#         self._triangles[0][0] = triangles
#         self._triangles[0][1] = normals
#
#     def _update_abs_position(self, point: _point.Point):
#         delta = point - self._o_abs_point
#         self._o_abs_point = point.copy()
#
#         self._rel_point.unbind(self._update_rel_position)
#         self._rel_point += delta
#         self._o_rel_point += delta
#         self._rel_point.bind(self._update_rel_position)
#
#         self.triangles[0][0] += delta
#         # self.triangles[0][0] += delta
#
#         for p in self.hit_test_rect[0]:
#             p += delta
#
#         self.adjust_hit_points()
#
#     def _update_rel_position(self, point: _point.Point):
#         delta = point - self._o_rel_point
#         self._o_rel_point = point.copy()
#
#         self._abs_point.unbind(self._update_abs_position)
#         self._abs_point += delta
#         self._o_abs_point += delta
#         self._abs_point.bind(self._update_abs_position)
#
#         self._triangles[0][0] += delta
#         # self.triangles[0][0] += delta
#
#         for p in self.hit_test_rect[0]:
#             p += delta
#
#         self.adjust_hit_points()
#
#     def _update_h_position(self, point: _point.Point):
#         delta = point - self._h_point
#         self._h_point = point.copy()
#         self._abs_point += delta
#
#     def _update_h_angle(self, angle: _angle.Angle):
#         delta = angle - self._h_angle
#         self._h_angle = angle.copy()
#         self._abs_angle += delta
#
#     def get_canvas(self):
#         return self.parent.parent.canvas
#
#     def set_terminal_size(self, size):
#         size = _decimal(size)
#
#         self.terminal_size = size
#         self.height = size
#         self.width = size
#         self.build_model()
#         self.get_canvas().Refresh()
#
#     def get_terminal_size(self):
#         return float(self.terminal_size)
#
#     def use_cylinder(self, flag):
#         self._use_cylinder = flag
#         self.build_model()
#         self.get_canvas().Refresh()
#
#     def build_model(self):
#         if self.model3d is not None:
#             if self._verts is None:
#                 if self.model3d.endswith('.step') or self.model3d.endswith('.stp'):
#                     verts, faces = _stp_loader.load_from_stp(self.model3d)
#
#                 elif self.model3d.endswith('.stl'):
#                     verts, faces = _stl_loader.load_from_stl(self.model3d)
#
#                 elif self.model3d.endswith('obj'):
#                     verts, faces = _obj_loader.load_from_obj(self.model3d)
#
#                 elif self.model3d.endswith('3mf'):
#                     raise NotImplementedError
#                 else:
#                     raise NotImplementedError
#
#                 self._verts = verts
#                 self._faces = faces
#
#             normals, triangles, count = self.get_mesh_triangles(self._verts, self._faces)
#
#             verts = self._verts.reshape(-1, 3)
#
#             col_min = verts.min(axis=0)  # shape (3,) -> array([-0.7,  0.3, -1. ])
#             col_max = verts.max(axis=0)  # shape (3,) -> array([1.2, 3.1, 4. ])
#         else:
#             if self._use_cylinder:
#                 model = build123d.Cylinder(
#                     float(self.height) / 2, float(self.length))
#             else:
#                 model = build123d.Box(
#                     float(self.height), float(self.width), float(self.length))
#
#             model = model.move(
#                 build123d.Location((0, 0, float(self.length) / 2), (0, 0, 1)))
#
#             normals, triangles, count = self.get_terminal_triangles(model)
#
#             self.models = [model]
#
#             bb = model.bounding_box()
#
#             col_min = bb.min
#             col_max = bb.max
#
#         p1 = _point.Point(*[_decimal(item) for item in col_min])
#         p2 = _point.Point(*[_decimal(item) for item in col_max])
#
#         normals @= self.angle
#         triangles @= self.angle
#         triangles += self.position
#
#         self._colors = [
#             np.full((count, 4),
#                     [1.0, 0.4, 0.4, 1.0], dtype=np.float32),
#             np.full((count, 4),
#                     [1.0, 0.4, 0.4, 0.45], dtype=np.float32),
#             np.full((count, 4),
#                     [0.4, 1.0, 0.4, 0.45], dtype=np.float32)
#         ]
#
#         self._triangles = [[triangles, normals, count]]
#
#         p1 *= _decimal(0.75)
#         p2 *= _decimal(1.25)
#
#         p1 @= self.angle
#         p2 @= self.angle
#         p1 += self.position
#         p2 += self.position
#
#         self.hit_test_rect = [[p1, p2]]
#
#         self.adjust_hit_points()
#
#     @property
#     def triangles(self):
#
#         if self._detent_update_counter:
#             color = self._colors[2]
#         else:
#             color = self._colors[int(self._is_selected)]
#
#         tris, norms, count = self._triangles[0]
#         triangles = [[tris, norms, color, count, color[0][-1] == 1.0]]
#         return triangles
#
#     def get_length(self):
#         return float(self.length)
#
#     def set_length(self, value):
#         self.length = _decimal(value)
#         self.build_model()
#         self.get_canvas().Refresh(False)
