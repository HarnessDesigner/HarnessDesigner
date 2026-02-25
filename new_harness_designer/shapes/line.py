from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...geometry import line as _line
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color


if TYPE_CHECKING:
    from .. import Editor2D


class Line:

    def __init__(self, p1: _point.Point, p2: _point.Point, width: _decimal,
                 color: _color.Color, stripe_color: _color.Color | None):
        self._p1 = p1
        self._p2 = p2
        self._width = width
        self._color = color
        self._stripe_color = stripe_color
        self._bmp = wx.NullBitmap
        self._dc = wx.MemoryDC()
        self._dc.SelectObject(wx.NullBitmap)
        self.artist = None

        p1.Bind(self._update_artist)
        p2.Bind(self._update_artist)

    @property
    def width(self) -> _decimal:
        return self._width

    @width.setter
    def width(self, value: _decimal):
        self._width = value
        self._bmp.Destroy()
        self._update_artist()

    @property
    def color(self) -> _color.Color:
        return self._color

    @color.setter
    def color(self, value: _color.Color):
        self._color = value
        self._bmp.Destroy()
        self._update_artist()

    @property
    def stripe_color(self) -> _color.Color:
        return self._stripe_color

    @stripe_color.setter
    def stripe_color(self, value: _color.Color):
        self._stripe_color = value
        self._bmp.Destroy()
        self._update_artist()

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @p1.setter
    def p1(self, value: _point.Point):
        self._p1.Unbind(self._update_artist)
        value.Bind(self._update_artist)
        self._p1 = value

        self._bmp.Destroy()
        self._update_artist()

    @property
    def p2(self) -> _point.Point:
        return self._p2

    @p2.setter
    def p2(self, value: _point.Point):
        self._p2.Unbind(self._update_artist)
        value.Bind(self._update_artist)
        self._p2 = value

        self._bmp.Destroy()
        self._update_artist()

    def _get_bmp(self):
        if not self._bmp.IsOk():
            p2 = self._p2 - self._p1
            p2 = p2.as_int[:-1]

            width = p2[0] + 11
            height = p2[1] + 11
            p2[0] += 5
            p2[1] += 5
            p1 = [5, 5]

            buf = bytearray([0] * (int(width) * int(height) * 4))
            bmp = wx.Bitmap.FromBufferRGBA(width, height, buf)
            self._dc.SelectObject(bmp)
            gcdc = wx.GCDC(self._dc)
            gc = gcdc.GetGraphicsContext()

            gc.SetPen(wx.Pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)

            line = _line.Line(self._p1, self._p2)
            line_angle = line.get_z_angle()

            stripe_line = _line.Line(_point.Point(_decimal(68), _decimal(0), _decimal(0)),
                                     _point.Point(_decimal(68 - 32), _decimal(24), _decimal(0)))

            stripe_angle = line_angle + stripe_line.get_z_angle()
            line_len = line.length()
            step = 25

            wire_size = self._width

            pen = wx.Pen(self._color, self._width)
            pen.SetCap(wx.CAP_BUTT)

            gc.SetPen(pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            gc.StrokeLine(*(line.p1.as_float[:-1] + line.p2.as_float[:-1]))

            if self._stripe_color is not None:
                curr_dist = 3

                gc.SetPen(wx.Pen(self._stripe_color, 3))

                while curr_dist < line_len - step - 10:
                    curr_dist += step

                    p = line.point_from_start(curr_dist)
                    s1 = _line.Line(p, None, max(wire_size - 2, 1), _decimal(0.0), _decimal(0.0), stripe_angle)
                    s2 = _line.Line(p, None, max(wire_size - 2, 1), _decimal(0.0), _decimal(0.0), stripe_angle + _decimal(180.0))

                    gc.StrokeLine(*(s1.p2.as_float[:-1] + s2.p2.as_float[:-1]))

            self._dc.SelectObject(wx.NullBitmap)

            gcdc.Destroy()
            del gcdc

            self._bmp = bmp

        return self._bmp

    @property
    def is_added(self):
        return self.artist is not None

    def _update_artist(self, p: _point.Point | None = None):
        if not self.is_added:
            return

        if p is not None:
            self._bmp.Destroy()

        bmp = self._get_bmp()
        self.artist.update((5, 5), bmp)

    def add_to_plot(self, axes: "Editor2D") -> None:
        self.artist = axes.add_line(self)
        self._update_artist()


