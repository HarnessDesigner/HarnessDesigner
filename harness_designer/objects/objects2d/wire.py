import wx

import math

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal

from .. import wire_info as _wire_info


FIVE_0 = _decimal(5.0)
SIX_0 = _decimal(6.0)


class WireSection:

    def __init__(self, parent, p1: _point.Point, p2: _point.Point):
        self.parent: "Wire" = parent
        self.p1 = p1
        self.p2 = p2

    def update_wire_info(self):
        self.parent.update_wire_info()

    def is_p1_end_grabbed(self, p):
        x, y = self.p1
        x1 = x - FIVE_0
        x2 = x + FIVE_0
        y1 = y - FIVE_0
        y2 = y + FIVE_0
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def is_p2_end_grabbed(self, p):
        x, y = self.p2.x, self.p2.y
        x1 = x - FIVE_0
        x2 = x + FIVE_0
        y1 = y - FIVE_0
        y2 = y + FIVE_0
        x, y = p.x, p.y
        return x1 <= x <= x2 and y1 <= y <= y2

    def __contains__(self, other: _point.Point):
        line1 = _line.Line(self.p1, self.p2)
        half_size = _decimal(self.parent.wire_info.pixel_width) / _decimal(2.0) + _decimal(1)

        line2 = line1.get_parallel_line(half_size)
        line3 = line1.get_parallel_line(-half_size)

        x1, y1, x2, y2 = line2.x1, line2.y1, line3.x2, line3.y2

        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)

        return x1 <= other.x <= x2 and y1 <= other.y <= y2

    def stripe_lines(self):
        line = _line.Line(self.p1, self.p2)
        line_angle = line.get_angle(self.p1).z
        stripe_line = _line.Line(_point.Point(68, 0), _point.Point(68 - 32, 24))
        stripe_angle = line_angle + stripe_line.get_angle(stripe_line.p1).z
        line_len = len(line)
        step = 40

        wire_size = self.parent.wire_info.pixel_width

        curr_dist = 0
        points = []

        while curr_dist < line_len - step:
            curr_dist += step

            p = line.point_from_start(curr_dist)
            s1 = _line.Line(p, None, angle=stripe_angle, length=max(wire_size, 1))
            s2 = _line.Line(p, None, angle=stripe_angle + 180, length=max(wire_size, 1))

            points.append([s1.p2.as_float, s2.p2.as_float])

        return points

    def aslist(self):
        return list(self.p1) + list(self.p2)

    def length(self):
        return _line.Line(self.p1, self.p2).length()

    def get_angle(self):
        return _line.Line(self.p1, self.p2).get_angle(self.p1).z

    @staticmethod
    def _rotate_point(origin, point, angle):
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = _decimal(math.cos(angle))
        sin = _decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return _point.Point(qx, qy)

    def move_p2(self, p):
        line = _line.Line(self.p1, p)
        angle = line.get_angle(self.p1).z
        new_angle = _angle.Angle(
            _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
            _point.Point(_decimal(10.0), _decimal(0.0), _decimal(0.0))
        )

        if 0 <= angle < 45:
            line = _line.Line(self.p1, None, line.length(), new_angle)
        if 45 <= angle < 135:
            new_angle.z = _decimal(90.0)
            line = _line.Line(self.p1, None, line.length(), new_angle)
        elif 135 <= angle < 225:
            new_angle.z = _decimal(180.0)
            line = _line.Line(self.p1, None, line.length(), new_angle)
        elif 225 <= angle <= 315:
            new_angle.z = _decimal(270.0)
            line = _line.Line(self.p1, None, line.length(), new_angle)
        else:
            line = _line.Line(self.p1, None, line.length(), new_angle)

        self.p2 = line.p2

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
            line = _line.Line(p3, p1)
            angle = line.get_angle(p3).z
            new_angle = _angle.Angle(
                _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
                _point.Point(_decimal(10.0), _decimal(0.0), _decimal(0.0))
            )

            if 0 <= angle < 45:
                line = _line.Line(p3, None, line.length(), new_angle)
            if 45 <= angle < 135:
                new_angle.z = _decimal(90.0)
                line = _line.Line(p3, None, line.length(), new_angle)
            elif 135 <= angle < 225:
                new_angle.z = _decimal(180.0)
                line = _line.Line(p3, None, line.length(), new_angle)
            elif 225 <= angle <= 315:
                new_angle.z = _decimal(270.0)
                line = _line.Line(p3, None, line.length(), new_angle)
            else:
                line = _line.Line(p3, None, line.length(), new_angle)

            p1.x = line.p2.x
            p1.y = line.p2.y

        if p4 is not None:
            line = _line.Line(p4, p2)
            angle = line.get_angle(p4).z
            new_angle = _angle.Angle(
                _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
                _point.Point(_decimal(10.0), _decimal(0.0), _decimal(0.0))
            )

            if 0 <= angle < 45:
                line = _line.Line(p4, None, line.length(), new_angle)
            if 45 <= angle < 135:
                new_angle.z = _decimal(90.0)
                line = _line.Line(p4, None, line.length(), new_angle)
            elif 135 <= angle < 225:
                new_angle.z = _decimal(180.0)
                line = _line.Line(p4, None, line.length(), new_angle)
            elif 225 <= angle <= 315:
                new_angle.z = _decimal(270.0)
                line = _line.Line(p4, None, line.length(), new_angle)
            else:
                line = _line.Line(p4, None, line.length(), new_angle)

            p2.x = line.p2.x
            p2.y = line.p2.y

        line = _line.Line(p1, p2)
        angle = line.get_angle(p1).z

        if int(round(angle)) in (0, 90, 180, 270, 360):
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
        path.MoveToPoint(float(round(x1, 1)), float(round(y1, 1)))
        path.AddLineToPoint(float(round(x2, 1)), float(round(y2, 1)))
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

            mask_path.MoveToPoint(float(round(section.p1.x, 1)), float(round(section.p1.y, 1)))
            mask_path.AddLineToPoint(float(round(section.p2.x, 1)), float(round(section.p2.y, 1)))

            path.MoveToPoint(float(round(section.p1.x, 1)), float(round(section.p1.y, 1)))
            path.AddLineToPoint(float(round(section.p2.x, 1)), float(round(section.p2.y, 1)))

            if is_selected:

                if i == 0:
                    mask_gc.DrawEllipse(float(round(section.p1.x - SIX_0, 1)),
                                        float(round(section.p1.y - SIX_0, 1)),
                                        12.0, 12.0)

                mask_gc.DrawEllipse(float(round(section.p2.x - SIX_0, 1)),
                                    float(round(section.p2.y - SIX_0, 1)),
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
                    gc.DrawEllipse(float(round(section.p1.x - SIX_0, 1)),
                                   float(round(section.p1.y - SIX_0, 1)),
                                   12.0, 12.0)

                gc.DrawEllipse(float(round(section.p2.x - SIX_0, 1)),
                               float(round(section.p2.y - SIX_0, 1)),
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
