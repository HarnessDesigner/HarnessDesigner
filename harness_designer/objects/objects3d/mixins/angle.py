from typing import TYPE_CHECKING

import build123d
import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle

from ...editor_3d import gl_object as _gl_object
from ...editor_3d import debug as _debug
from ...editor_3d import helpers
from ...wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from ...editor_3d import mainframe as _mainframe


class CurvedArrow:
    _arrow: tuple[np.ndarray, np.ndarray, int] = None
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    @_debug.timeit
    def __init__(self, parent: "ArrowRing", center: _point.Point, radius: float,
                 start_angle: float, stop_angle: float, angle: _angle.Angle, scale: _decimal):

        self.parent = parent

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

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), float(angle.x))

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), float(angle.y))

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (0, 0, 1)), float(angle.z))

        # c = arrow.center()

        # arrow = arrow.move(build123d.Location((-c.X, -c.Y, -c.Z)))
        # arrow = arrow.scale(float(scale))
        #
        # arrow = arrow.move(build123d.Location(c))

        arrow = arrow.move(build123d.Location(
                (float(center.x), float(center.y), float(center.z))))

        normals, triangles, count = parent.get_housing_triangles(arrow)
        self.models = [arrow]

        self.triangles = [[triangles, normals, count]]

        bb = arrow.bounding_box()

        p1 = _point.Point(
            _decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z))

        p2 = _point.Point(
            _decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))

        self.hit_test_rect = [[p1, p2]]


class ArrowRing(_gl_object.GLObject):

    @_debug.timeit
    def __init__(self, parent, center: _point.Point, radius: _decimal,
                 angle: _angle.Angle, scale: _decimal, color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        super().__init__()
        self.parent = parent

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

        top_arrow_1 = CurvedArrow(
            parent, center, float(radius) - 0.075, start_angle,
            start_angle + float(radius) / 2.0, angle, scale)

        top_arrow_2 = CurvedArrow(
            parent, center, float(radius) - 0.075, start_angle,
            start_angle - float(radius) / 2.0, angle, scale)

        ring = build123d.Circle(float(radius))
        hole = build123d.Circle(float(radius) - 0.1)
        ring -= hole

        ring = build123d.extrude(ring, 0.1, (0, 0, 1))
        ring = ring.move(build123d.Location((0.0, 0.0, -0.05), (0.0, 0.0, 1)))

        (
            ring_normals,
            ring_triangles,
            ring_count
        ) = self.get_housing_triangles(ring)

        ring_normals @= angle
        ring_triangles @= angle
        ring_triangles += center

        angle.bind(self.on_angle)
        self._angle = angle
        self._o_angle = angle.copy()

        self.hit_test_rect = [
            [top_arrow_1.hit_test_rect[0][0], top_arrow_2.hit_test_rect[0][1]]
        ]

        self.__arrows = [top_arrow_1, top_arrow_2]

        self.adjust_hit_points()
        self._triangles = [top_arrow_1.triangles[0],
                           top_arrow_2.triangles[0],
                           [ring_triangles, ring_normals, ring_count]]

        self.models = [ring]  # , plane]
        self._color = color
        self._press_color = press_color
        self.center = center

        self.parent.get_canvas().add_object(self)

        self._color_arr = [
            [
                np.full((top_arrow_1.triangles[0][-1], 4),
                        color, dtype=np.float32),

                np.full((top_arrow_1.triangles[0][-1], 4),
                        press_color, dtype=np.float32)
            ],
            np.full((ring_count, 4), color[:-1] + [1.0], dtype=np.float32),
        ]

    @_debug.timeit
    def update_angle(self, angle: _angle.Angle):
        self._angle.unbind(self.on_angle)
        inverse = self._angle.inverse
        self._angle += angle
        self._o_angle = self._angle.copy()
        self._angle.bind(self.on_angle)

        ta1_tris, ta1_nrmls, ta1_count = self._triangles[0]
        ta2_tris, ta2_nrmls, ta2_count = self._triangles[1]
        r_tris, r_nrmls, r_count = self._triangles[2]

        ta1_tris -= self.center
        ta2_tris -= self.center
        r_tris -= self.center

        ta1_tris @= inverse
        ta2_tris @= inverse
        r_tris @= inverse

        ta1_nrmls @= inverse
        ta2_nrmls @= inverse
        r_nrmls @= inverse

        ta1_tris @= self._angle
        ta2_tris @= self._angle
        r_tris @= self._angle

        ta1_nrmls @= self._angle
        ta2_nrmls @= self._angle
        r_nrmls @= self._angle

        ta1_tris += self.center
        ta2_tris += self.center
        r_tris += self.center

        self._triangles = [
            [ta1_tris, ta1_nrmls, ta1_count],
            [ta2_tris, ta2_nrmls, ta2_count],
            [r_tris, r_nrmls, r_count]
        ]

        for p in self.hit_test_rect[0]:
            p -= self.center
            p @= inverse
            p @= self._angle
            p += self.center

        self.adjust_hit_points()

    @_debug.timeit
    def on_angle(self, angle: _angle.Angle):
        inverse = self._o_angle.inverse
        self._o_angle = angle.copy()

        for i, (tris, normls, count) in enumerate(self._triangles):
            tris -= self.center

            tris @= inverse
            normls @= inverse

            tris @= angle
            normls @= angle

            tris += self.center
            self._triangles[i] = [tris, normls, count]

        for p in self.hit_test_rect[0]:
            p -= self.center
            p @= inverse
            p @= angle
            p += self.center

        self.adjust_hit_points()

    def get_first_points(self):
        points = []
        for i in range(1):
            tris = self._triangles[i][0]
            p = _point.Point(_decimal(tris[0][0]), _decimal(tris[0][1]),
                             _decimal(tris[0][2]))
            points.append(p)

        return points

    @property
    def triangles(self):
        triangles = []
        for tris, norms, count in self._triangles[:-1]:
            color = self._color_arr[0][int(self._is_selected)]
            triangles.append([tris, norms, color, count, color[0][-1] >= 1.0])

        tris, norms, count = self._triangles[-1]
        triangles.append([tris, norms, self._color_arr[1], count,
                          self._color_arr[1][0][-1] >= 1.0])

        return triangles

    @property
    def position(self) -> _point.Point:
        return self.parent.position

    def delete(self):
        self.parent.get_canvas().remove_object(self)

    def hit_test(self, point: _point.Point) -> bool:
        (p1, p2), (p3, p4) = self.hit_test_rect

        return p1 <= point <= p2 or p3 <= point <= p4

    def get_parent_object(self) -> "AngleMixin":
        return self.parent


class AngleMixin:
    parent: "_mainframe.MainFrame" = None

    hit_test_rect: list[list[_point.Point, _point.Point]] = []

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

    @_debug.timeit
    def rotate(self, quat: np.ndarray):
        if self._detent_update_counter:
            self._detent_update_counter -= 1
            return

        # quaternion multiplication (q * orient)
        angle = self.angle

        x1, y1, z1, w1 = quat
        x2, y2, z2, w2 = angle.as_quat

        q = np.array(
            [
                w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
            ], dtype=np.float64
        )

        quat = helpers.quat_normalize(q)
        new_angle = _angle.Angle.from_quat(quat)
        delta = new_angle - angle

        detent_setting = _decimal(self.parent.cp.detent)

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

            print(self._last_detent_counts, (new_cx, new_cy, new_cz))

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
    def on_x_plane(self, angle):
        delta = angle - self._o_x_plane_angle
        self._o_x_plane_angle = angle.copy()

        self._z_plane_angle.unbind(self.on_z_plane)
        self._z_plane_angle @= delta
        self._o_z_plane_angle = self._z_plane_angle.copy()
        self._z_plane_angle.bind(self.on_z_plane)

        obj_angle = self.angle
        obj_angle @= delta

    @_debug.timeit
    def on_y_plane(self, angle):
        delta = angle - self._o_y_plane_angle
        self._o_y_plane_angle = angle.copy()

        self._x_plane_angle.unbind(self.on_x_plane)
        self._x_plane_angle @= delta
        self._o_x_plane_angle = self._x_plane_angle.copy()
        self._x_plane_angle.bind(self.on_x_plane)

        self._z_plane_angle.unbind(self.on_z_plane)
        self._z_plane_angle @= delta
        self._o_z_plane_angle = self._z_plane_angle.copy()
        self._z_plane_angle.bind(self.on_z_plane)

        obj_angle = self.angle
        obj_angle @= delta

    @_debug.timeit
    def on_z_plane(self, angle):
        delta = angle - self._o_z_plane_angle
        self._o_z_plane_angle = angle.copy()

        obj_angle = self.angle
        obj_angle @= delta

    @_debug.timeit
    def start_angle(self):
        p1, p2 = self.hit_test_rect[0]
        offset = p2 - p1

        diameter = max(offset.x, offset.y, offset.z)
        scale = diameter / _decimal(30.0)

        center = self.position
        radius = diameter / _decimal(2.0) * _decimal(1.1)

        angle = self.angle

        if self._x_plane_angle is None:
            self._x_plane_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0, 'YXZ')
            self._o_x_plane_angle = self._x_plane_angle.copy()
            self._x_plane_angle.bind(self.on_x_plane)
            new_xplane = True
        else:
            new_xplane = False

        if self._y_plane_angle is None:
            self._y_plane_angle = _angle.Angle.from_euler(90.0, 0.0, 0.0, 'YXZ')
            self._o_y_plane_angle = self._y_plane_angle.copy()
            self._y_plane_angle.bind(self.on_y_plane)

        if self._z_plane_angle is None:
            self._z_plane_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0, 'YXZ')
            self._o_z_plane_angle = self._z_plane_angle.copy()
            self._z_plane_angle.bind(self.on_z_plane)
            new_zplane = True
        else:
            new_zplane = False

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

            if new_xplane:
                self._x_angle.update_angle(angle)

            if new_zplane:
                self._z_angle.update_angle(angle)
