from typing import TYPE_CHECKING

import wx

import math

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from ...editor_2d import Config


if TYPE_CHECKING:
    from .. import wire_info as _wire_info
    from ... import editor_2d as _editor_2d
    from ...database.project_db import pjt_wire as _pjt_wire

FIVE_0 = _decimal(5.0)
SIX_0 = _decimal(6.0)




class Wire:

    def __init__(self, editor2d: "_editor_2d.Editor2D", db_obj: "_pjt_wire.PJTWire", wire_info: "_wire_info.WireInfo"):
        self.editor2d = editor2d
        self._db_obj = db_obj
        self._wire_info = wire_info
        self._part = db_obj.part
        self._p1 = db_obj.start_point2d.point
        self._p2 = db_obj.stop_point2d.point

        self._p1.Bind(self._reset_hit_test)
        self._p2.Bind(self._reset_hit_test)

        self._p1.add_object(self)
        self._p2.add_object(self)

        self._hit_test_rect = None

    def _reset_hit_test(self, *_):
        dia = self._wire_info.pixel_width
        length = _line.Line(self._p1, self._p2).length()
        angle = _angle.Angle.from_points(self._p1, self._p2)

        p1 = _point.Point(_decimal(0.0), _decimal(0.0))
        p2 = _point.Point(_decimal(dia), length)

        p2 @= angle

        p1 += self._p1
        p2 += self._p2

        self._hit_test_rect = [p1, p2]

    def get_rect(self):
        if self._hit_test_rect is None:
            dia = self._wire_info.pixel_width
            length = _line.Line(self._p1, self._p2).length()
            angle = _angle.Angle.from_points(self._p1, self._p2)

            p1 = _point.Point(_decimal(0.0), _decimal(0.0))
            p2 = _point.Point(_decimal(dia), length)

            p2 @= angle

            p1 += self._p1
            p2 += self._p2

            self._hit_test_rect = [p1, p2]
        return self._hit_test_rect

    def stripe_lines(self) -> list[list[tuple[float, float], tuple[float, float]]]:
        line = _line.Line(self._p1, self._p2)
        line_angle = _angle.Angle.from_points(self._p1, self._p2)

        stripe_angle1 = _angle.Angle.from_points(_point.Point(68, 0), _point.Point(68 - 32, 24))
        stripe_angle1 += line_angle

        stripe_angle2 = stripe_angle1.copy()
        stripe_angle2.z += _decimal(180.0)

        line_len = len(line)
        step = 40

        wire_size = self._wire_info.pixel_width

        curr_dist = 0
        points = []

        while curr_dist < line_len - step:
            curr_dist += step

            p = line.point_from_start(curr_dist)
            s1 = _line.Line(p, None, angle=stripe_angle1, length=max(wire_size, 1))
            s2 = _line.Line(p, None, angle=stripe_angle2, length=max(wire_size, 1))

            points.append([s1.p2.as_float[:-1], s2.p2.as_float[:-1]])

        return points

    def draw_selected(self, gc, selected):
        x1 = selected.p1.x
        y1 = selected.p1.y
        x2 = selected.p2.x
        y2 = selected.p2.y

        path = gc.CreatePath()
        path.MoveToPoint(float(x1), float(y1))
        path.AddLineToPoint(float(x2), float(y2))
        path.CloseSubpath()
        gc.StrokePath(path)

    def draw(self, gc, mask_gc):
        p1 = self._p1
        p2 = self._p2

        pixel_width = self._wire_info.pixel_width
        color = self._part.color.ui

        pen1 = wx.Pen(color, pixel_width)
        pen1.SetJoin(wx.JOIN_MITER)

        mask_pen = wx.Pen(wx.BLACK, pixel_width)
        mask_pen.SetJoin(wx.JOIN_MITER)

        stripe_color = self._part.stripe_color

        if stripe_color is not None:
            stripe_pen = wx.Pen(stripe_color.ui,
                                max(int(self._wire_info.pixel_width / 3.0), 2))
        else:
            stripe_pen = None

        handle_pen = wx.Pen(wx.Colour(0, 0, 0, 255), 3.0)

        path = gc.CreatePath()
        mask_path = mask_gc.CreatePath()

        is_selected = self.is_selected
        mask_gc.SetPen(wx.TRANSPARENT_PEN)

        mask_path.MoveToPoint(float(p1.x), float(p1.y))
        mask_path.AddLineToPoint(float(p2.x), float(p2.y))

        path.MoveToPoint(float(p1.x), float(p1.y))
        path.AddLineToPoint(float(p2.x), float(p2.y))

        if is_selected:
            for obj in p1.objects:
                if obj != self and isinstance(obj, Wire):
                    mask_path.drawEllipse(float(p1.x - SIX_0),
                                          float(p1.y - SIX_0),
                                          12.0, 12.0)
                    break

            for obj in p2.objects:
                if obj != self and isinstance(obj, Wire):
                    mask_path.DrawEllipse(float(p2.x - SIX_0),
                                          float(p2.y - SIX_0),
                                          12.0, 12.0)
                    break

        mask_path.CloseSubpath()
        mask_gc.SetPen(mask_pen)
        mask_gc.StrokePath(path)

        gc.SetPen(pen1)
        path.CloseSubpath()
        gc.StrokePath(path)

        gc.SetPen(wx.TRANSPARENT_PEN)

        if stripe_color is not None:
            path = gc.CreatePath()
            for start, stop in self.stripe_lines():
                path.MoveToPoint(*start)
                path.AddLineToPoint(*stop)

            path.CloseSubpath()

            gc.SetPen(stripe_pen)
            gc.StrokePath(path)

        path = gc.CreatePath()

        if is_selected:
            for obj in self._p1.objects:
                if obj != self and isinstance(obj, Wire):
                    path.DrawEllipse(float(self._p1.x - SIX_0),
                                     float(self._p1.y - SIX_0),
                                     12.0, 12.0)
                    break

            for obj in self._p2.objects:
                if obj != self and isinstance(obj, Wire):
                    path.DrawEllipse(float(self._p2.x - SIX_0),
                                     float(self._p2.y - SIX_0),
                                     12.0, 12.0)
                    break

        path.CloseSubpath()

        gc.SetPen(handle_pen)
        gc.StrokePath(path)

    def hit_test(self, p: _point.Point) -> bool:
        if self._hit_test_rect is None:
            return False
        p1, p2 = self._hit_test_rect

        if not Config.lock_90:
            p1 = p1.copy()
            p2 = p2.copy()
            p = p.copy()

            angle = _angle.Angle.from_points(p1, p2)
            angle.z = -angle.z
            p2 -= p1
            p2 @= angle
            p -= p1
            p @= angle

        return p1 <= p <= p2



class WireSection:

    def __init__(self, parent, p1: _point.Point, p2: _point.Point):
        self.parent: "Wire" = parent
        self.p1 = p1
        self.p2 = p2

    def update_wire_info(self) -> None:
        self.parent.update_wire_info()

    def is_p1_end_grabbed(self, p: _point.Point) -> bool:
        x, y = self.p1
        x1 = x - FIVE_0
        x2 = x + FIVE_0
        y1 = y - FIVE_0
        y2 = y + FIVE_0
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def is_p2_end_grabbed(self, p: _point.Point) -> bool:
        x, y = self.p2.x, self.p2.y
        x1 = x - FIVE_0
        x2 = x + FIVE_0
        y1 = y - FIVE_0
        y2 = y + FIVE_0
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def __contains__(self, other: _point.Point) -> bool:
        line1 = _line.Line(self.p1, self.p2)
        half_size = _decimal(self.parent.wire_info.pixel_width) / _decimal(2.0) + _decimal(1)

        line2 = line1.get_parallel_line(half_size)
        line3 = line1.get_parallel_line(-half_size)

        x1, y1, x2, y2 = line2.p1.x, line2.p1.y, line3.p2.x, line3.p2.y

        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        return x1 <= other.x <= x2 and y1 <= other.y <= y2

    def stripe_lines(self) -> list[list[tuple[float, float], tuple[float, float]]]:
        line = _line.Line(self.p1, self.p2)
        line_angle = _angle.Angle.from_points(self.p1, self.p2)

        stripe_angle1 = _angle.Angle.from_points(_point.Point(68, 0), _point.Point(68 - 32, 24))
        stripe_angle1 += line_angle

        stripe_angle2 = stripe_angle1.copy()
        stripe_angle2.z += _decimal(180.0)

        line_len = len(line)
        step = 40

        wire_size = self.parent.wire_info.pixel_width

        curr_dist = 0
        points = []

        while curr_dist < line_len - step:
            curr_dist += step

            p = line.point_from_start(curr_dist)
            s1 = _line.Line(p, None, angle=stripe_angle1, length=max(wire_size, 1))
            s2 = _line.Line(p, None, angle=stripe_angle2, length=max(wire_size, 1))

            points.append([s1.p2.as_float[:-1], s2.p2.as_float[:-1]])

        return points

    def aslist(self) -> list[_decimal, _decimal, _decimal, _decimal]:
        return list(self.p1) + list(self.p2)

    def length(self) -> _decimal:
        return _line.Line(self.p1, self.p2).length()

    def get_angle(self) -> _angle.Angle:
        return _angle.Angle.from_points(self.p1, self.p2)

    @staticmethod
    def _rotate_point(origin: _point.Point, point: _point.Point, angle: _angle.Angle):
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        z_angle = angle.z

        cos = _decimal(math.cos(z_angle))
        sin = _decimal(math.sin(z_angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return _point.Point(qx, qy)

    def move_p2(self, p: _point.Point):
        angle = _angle.Angle.from_points(self.p1, p)
        z_angle = angle.z

        if z_angle > 315:
            offset = 360
        elif z_angle > 225:
            offset = 270
        elif z_angle > 135:
            offset = 180
        elif z_angle > 45:
            offset = 90
        else:
            offset = 0

        angle.z = _decimal(offset) - z_angle
        self.p2 -= p
        self.p2 @= angle
        self.p2 += p

    def move(self, p):
        p1 = self.p1.copy()
        p2 = self.p2.copy()

        p1 += p
        p2 += p

        p3 = None
        p4 = None

        for section in self.parent._sections:  # NOQA
            if section == self:
                continue

            if section.p2 == self.p1:
                p3 = section.p1

            if section.p1 == self.p2:
                p4 = section.p2

        if p3 is not None:
            angle = _angle.Angle.from_points(p3, p1)
            z_angle = angle.z

            if z_angle > 315:
                offset = 360
            elif z_angle > 225:
                offset = 270
            elif z_angle > 135:
                offset = 180
            elif z_angle > 45:
                offset = 90
            else:
                offset = 0

            angle.z = _decimal(offset) - z_angle
            p1 -= p3
            p1 @= angle
            p1 += p3

        if p4 is not None:
            angle = _angle.Angle.from_points(p4, p2)
            z_angle = angle.z

            if z_angle > 315:
                offset = 360
            elif z_angle > 225:
                offset = 270
            elif z_angle > 135:
                offset = 180
            elif z_angle > 45:
                offset = 90
            else:
                offset = 0

            angle.z = _decimal(offset) - z_angle
            p2 -= p4
            p2 @= angle
            p2 += p4

        angle = _angle.Angle.from_points(p1, p2).z

        if angle in (0, 90, 180, 270, 360):
            self.p1.x = p1.x
            self.p1.y = p1.y
            self.p2.x = p2.x
            self.p2.y = p2.y
        else:
            print(angle)


class Wire:

    def __init__(self, parent, db_obj):
        self.parent = parent
        self.wire_info = _wire_info.WireInfo(db_obj)
        self._sections: list[WireSection] = []
        self._is_selected = False

    def new_section(self, p):
        if self._sections:
            section = self._sections[-1]
            new_section = WireSection(self, section.p2, p)
        else:
            new_section = WireSection(self, p.copy(), p)

        self._sections.append(new_section)
        return new_section

    def remove_last_section(self):
        self._sections.pop(-1)

    def draw_selected(self, gc, selected):
        x1 = selected.p1.x
        y1 = selected.p1.y
        x2 = selected.p2.x
        y2 = selected.p2.y

        path = gc.CreatePath()
        path.MoveToPoint(float(x1), float(y1))
        path.AddLineToPoint(float(x2), float(y2))
        path.CloseSubpath()
        gc.StrokePath(path)

    def draw(self, gc, mask_gc, selected):
        pen1 = wx.Pen(self.wire_info.color, self.wire_info.pixel_width)
        pen1.SetJoin(wx.JOIN_MITER)

        mask_pen = wx.Pen(wx.BLACK, self.wire_info.pixel_width)
        mask_pen.SetJoin(wx.JOIN_MITER)

        pen2 = wx.Pen(self.wire_info.stripe_color, max(int(self.wire_info.pixel_width / 3.0), 2))

        path = gc.CreatePath()
        mask_path = mask_gc.CreatePath()

        is_selected = self.is_selected()
        mask_gc.SetPen(wx.TRANSPARENT_PEN)

        for i, section in enumerate(self._sections):
            if section == selected:
                continue

            mask_path.MoveToPoint(float(section.p1.x), float(section.p1.y))
            mask_path.AddLineToPoint(float(section.p2.x), float(section.p2.y))

            path.MoveToPoint(float(section.p1.x), float(section.p1.y))
            path.AddLineToPoint(float(section.p2.x), float(section.p2.y))

            if is_selected:

                if i == 0:
                    mask_gc.DrawEllipse(float(section.p1.x - SIX_0),
                                        float(section.p1.y - SIX_0),
                                        12.0, 12.0)

                mask_gc.DrawEllipse(float(section.p2.x - SIX_0),
                                    float(section.p2.y - SIX_0),
                                    12.0, 12.0)

        mask_path.CloseSubpath()
        mask_gc.SetPen(mask_pen)
        mask_gc.StrokePath(path)

        gc.SetPen(pen1)
        path.CloseSubpath()
        gc.StrokePath(path)

        path = gc.CreatePath()

        gc.SetPen(wx.TRANSPARENT_PEN)

        for i, section in enumerate(self._sections):
            if section == selected:
                continue

            for start, stop in section.stripe_lines():
                path.MoveToPoint(*start)
                path.AddLineToPoint(*stop)

            if is_selected:
                if i == 0:
                    gc.DrawEllipse(float(section.p1.x - SIX_0),
                                   float(section.p1.y - SIX_0),
                                   12.0, 12.0)

                gc.DrawEllipse(float(section.p2.x - SIX_0),
                               float(section.p2.y - SIX_0),
                               12.0, 12.0)

        path.CloseSubpath()
        gc.SetPen(pen2)
        gc.StrokePath(path)

    def is_selected(self, flag=None):
        if flag is None:
            return self._is_selected

        self._is_selected = flag

    def update_wire_info(self):
        self.parent.wire_info_ctrl.update_wire_length()

    def get_section(self, p):
        for section in self._sections:
            if p in section:
                return section

    def __len__(self):
        return len(self._sections)
