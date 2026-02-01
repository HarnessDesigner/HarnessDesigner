from typing import TYPE_CHECKING

import build123d
import numpy as np
import math

from .. import base3d as _base3d

from ....geometry import point as _point
from ....geometry import angle as _angle
from .... import gl_materials as _gl_materials

from ....import debug as _debug
from ....wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from .... import ui as _ui
    from ... import ObjectBase as _ObjectBase


class CurvedArrow:

    @_debug.timeit
    def __init__(self, radius: float, start_angle: float,
                 stop_angle: float, scale: _decimal):

        arc_len = start_angle - stop_angle
        arc = build123d.CenterArc((0.0, 0.0, 0.0),
                                  radius, start_angle, arc_len)

        arc = build123d.Wire(arc.edges())
        arc_angle = arc.tangent_angle_at(1)
        # Create the arrow head
        arrow_head = build123d.ArrowHead(size=1.75 * float(scale), rotation=arc_angle,
                                         head_type=build123d.HeadType.CURVED)

        arrow_head = arrow_head.move(build123d.Location(arc.end_point()))

        # Trim the path so the tip of the arrow isn't lost

        trim_amount = 1.0 - (1.0 / arc.length)
        shaft_path = arc.trim(trim_amount, arc.start_point())

        # Create a perpendicular line to sweep the tail path
        shaft_pen = shaft_path.perpendicular_line(0.25, 0)
        shaft = build123d.sweep(shaft_pen, shaft_path)
        arrow = arrow_head + shaft

        arrow = build123d.extrude(arrow, 0.25, (0, 0, 1))
        arrow = arrow.move(build123d.Location((0, 0, -0.125)))

        self.model = arrow


class ArrowRing(_base3d.Base3D):

    @_debug.timeit
    def __init__(self, parent: "AngleMixin", center: _point.Point, radius: _decimal,
                 angle: _angle.Angle, scale: _decimal, color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        super().__init__(parent.mainframe)
        self._real_parent = parent

        opposite_angle = angle.copy()
        if angle.y:
            opposite_angle.y += _decimal(90.0)
            start_angle = 180.0
        elif angle.x:
            opposite_angle.y += _decimal(180.0)
            start_angle = 180.0
        else:
            opposite_angle.y = _decimal(180.0)
            start_angle = 0.0

        arrow1 = CurvedArrow(float(radius) - 0.075, start_angle,
                             start_angle + float(radius) / 2.0, scale)

        arrow2 = CurvedArrow(float(radius) - 0.075, start_angle,
                             start_angle - float(radius) / 2.0, scale)

        ring = build123d.Circle(float(radius))
        hole = build123d.Circle(float(radius) - 0.1)
        ring -= hole

        ring = build123d.extrude(ring, 0.1, (0, 0, 1))
        ring = ring.move(build123d.Location((0.0, 0.0, -0.05), (0.0, 0.0, 1)))

        ring_verts, ring_faces = self._convert_model_to_mesh(ring)
        arrow1_verts, arrow1_faces = self._convert_model_to_mesh(arrow1.model)
        arrow2_verts, arrow2_faces = self._convert_model_to_mesh(arrow2.model)

        arrow1_tris, arrow1_nrmls, arrow1_count = self._compute_smoothed_vertex_normals(arrow1_verts, arrow1_faces)
        arrow2_tris, arrow2_nrmls, arrow2_count = self._compute_smoothed_vertex_normals(arrow2_verts, arrow2_faces)

        arrow_tris = np.array([arrow1_tris, arrow2_tris], dtype=np.float64).reshape(-1, 3, 3)
        arrow_nrmls = np.array([arrow1_nrmls, arrow2_nrmls], dtype=np.float64).reshape(-1, 3)
        arrow_count = arrow1_count + arrow2_count
        ring_tris, ring_nrmls, ring_count = self._compute_smoothed_vertex_normals(ring_verts, ring_faces)

        ring_nrmls @= angle
        ring_tris @= angle
        ring_tris += center

        arrow_nrmls @= angle
        arrow_tris @= angle
        arrow_tris += center

        p1, p2 = self._compute_rect(arrow_tris)
        bb = self._compute_bb(p1, p2)

        self._rect.append([p1, p2])
        self._bb.append(bb)

        angle.bind(self._update_angle)

        self._angle = angle
        self._o_angle = angle.copy()

        self._position = center

        self._material = _gl_materials.Metallic(color)
        self._press_material = _gl_materials.Metallic(press_color)

        self._triangles = [
            _base3d.TriangleRenderer([[arrow_tris, arrow_nrmls, arrow_count]], self._material),
            _base3d.TriangleRenderer([[ring_tris, ring_nrmls, ring_count]], self._material)]

        self._color = color
        self._press_color = press_color

        self.canvas.add_object(self)

    @_debug.timeit
    def _update_angle(self, angle: _angle.Angle):
        delta = angle - self._o_angle
        self._o_angle = angle.copy()

        for renderer in self._triangles:
            tris, nrmls, count = renderer.data
            tris -= self._position
            tris @= delta
            nrmls @= delta
            tris += self._position
            renderer.data = [tris, nrmls, count]

        self._bb = []

        for p1, p2 in self._rect:
            p1 -= self._position
            p2 -= self._position

            p1 @= delta
            p2 @= delta

            p1 += self._position
            p2 += self._position

            self._bb.append(self._compute_bb(p1, p2))

    def rotate(self, quat: np.ndarray):
        self._real_parent.rotate(quat)

    def delete(self):
        self.canvas.remove_object(self)


class AngleMixin:
    mainframe: _ui.MainFrame = None

    parent: "_ObjectBase" = None
    _rect = []

    _x_angle: "ArrowRing" = None
    _y_angle: "ArrowRing" = None
    _z_angle: "ArrowRing" = None

    _x_plane_angle: _angle.Angle = None
    _y_plane_angle: _angle.Angle = None
    _z_plane_angle: _angle.Angle = None

    _o_x_plane_angle: _angle.Angle = None
    _o_y_plane_angle: _angle.Angle = None
    _o_z_plane_angle: _angle.Angle = None

    _last_detent_counts: list = None
    _detent_update_counter: int = 0

    _o_angle: _angle.Angle = None
    _position: _point.Point = None
    _triangles: list = []
    _bb: list = []

    @staticmethod
    def _compute_bb(p1, p2):
        raise RuntimeError

    @_debug.timeit
    def rotate(self, quat: np.ndarray):
        if self._detent_update_counter:
            self._detent_update_counter -= 1
            return

        # quaternion multiplication (q * orient)
        angle = self.angle

        x1, y1, z1, w1 = quat
        x2, y2, z2, w2 = angle.as_quat

        q = np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                     w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2], dtype=np.float64)

        n = math.sqrt((q * q).sum())

        if n == 0.0:
            quat = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)
        else:
            quat = (q / n).astype(np.float64)

        new_angle = _angle.Angle.from_quat(quat)
        delta = new_angle - angle

        detent_setting = _decimal(self.mainframe.editor3d.cp.detent)

        if detent_setting == 0:
            self._last_detent_counts = None
        else:
            if self._last_detent_counts is None:
                self._last_detent_counts = [_decimal(int(angle.x / detent_setting)),
                                            _decimal(int(angle.y / detent_setting)),
                                            _decimal(int(angle.z / detent_setting))]

            cx, cy, cz = self._last_detent_counts
            new_angle = angle + delta

            new_cx = _decimal(int(new_angle.x / detent_setting))
            new_cy = _decimal(int(new_angle.y / detent_setting))
            new_cz = _decimal(int(new_angle.z / detent_setting))

            if new_cx != cx:
                new_angle.x = new_cx * detent_setting
                self._last_detent_counts[0] = new_cx
                self._detent_update_counter = 10
            if new_cy != cy:
                new_angle.y = new_cy * detent_setting
                self._last_detent_counts[1] = new_cy
                self._detent_update_counter = 10
            if new_cz != cz:
                new_angle.z = new_cz * detent_setting
                self._last_detent_counts[2] = new_cz
                self._detent_update_counter = 10

            delta = new_angle - angle

        angle += delta

        if None not in (self._x_plane_angle, self._y_plane_angle, self._z_plane_angle):
            if delta.x or delta.y:
                x_plane_delta = _angle.Angle(delta.x, delta.y, _decimal(0.0))
                self._x_plane_angle += x_plane_delta

            if delta.x or delta.y or delta.z:
                self._z_plane_angle += delta

            if delta.y:
                self._y_plane_angle.y += delta.y

    def _update_angle(self, angle: _angle.Angle):
        delta = angle - self._o_angle
        self._o_angle = angle.copy()

        for i, renderer in enumerate(self._triangles):

            tris, nrmls, count = renderer.data

            tris -= self._position
            tris @= delta
            tris += self._position

            nrmls @= delta

        self._bb = []

        for p1, p2 in self._rect:
            p1 -= self._position
            p2 -= self._position

            p1 @= delta
            p2 @= delta
            p1 += self._position
            p2 += self._position

            self._bb.append(self._compute_bb(p1, p2))

    @property
    def is_angle_shown(self) -> bool:
        return self._x_angle is not None

    @property
    def angle(self) -> _angle.Angle:
        raise NotImplementedError

    @property
    def position(self) -> _point.Point:
        raise NotImplementedError

    def stop_angle(self):
        self._x_angle.delete()
        self._y_angle.delete()
        self._z_angle.delete()

        self._x_angle = None
        self._y_angle = None
        self._z_angle = None

    def get_canvas(self):
        raise NotImplementedError

    @_debug.timeit
    def start_angle(self):
        p1, p2 = self._rect[0]
        offset = p2 - p1

        diameter = max(offset.x, offset.y, offset.z)
        scale = diameter / _decimal(30.0)

        center = self.position
        radius = diameter / _decimal(2.0) * _decimal(1.1)

        angle = self.angle

        if None in (self._x_plane_angle, self._y_plane_angle, self._z_plane_angle):
            self._x_plane_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)
            self._y_plane_angle = _angle.Angle.from_euler(90.0, 0.0, 0.0)
            self._z_plane_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
            new_angles = True
        else:
            new_angles = False

        with self.get_canvas():
            self._x_angle = ArrowRing(self, center, radius, self._x_plane_angle, scale,
                                      [1.0, 0.1, 0.1, 0.9],
                                      [1.0, 0.6, 0.6, 1.0])

            self._y_angle = ArrowRing(self, center, radius, self._y_plane_angle, scale,
                                      [0.1, 1.0, 0.1, 0.9],
                                      [1.0, 0.6, 0.6, 1.0])

            self._z_angle = ArrowRing(self, center, radius, self._z_plane_angle, scale,
                                      [0.1, 0.1, 1.0, 0.9],
                                      [1.0, 0.6, 0.6, 1.0])

            if new_angles:
                plane_angle = self._x_plane_angle + self._y_plane_angle + self._z_plane_angle
                delta = angle - plane_angle

                if delta.x or delta.y:
                    x_plane_delta = _angle.Angle(delta.x, delta.y, _decimal(0.0))
                    self._x_plane_angle += x_plane_delta

                if delta.x or delta.y or delta.z:
                    self._z_plane_angle += delta

                if delta.y:
                    self._y_plane_angle.y += delta.y
