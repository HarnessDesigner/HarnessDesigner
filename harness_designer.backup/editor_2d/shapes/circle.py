from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ...wrappers import color as _color


if TYPE_CHECKING:
    from .. import Editor2D


class Circle:

    def __init__(self, center: _point.Point, diameter: _decimal,
                 color: _color.Color):
        self._center = center
        self._diameter = diameter
        self._color = color
        self._bmp = wx.NullBitmap
        self._dc = wx.MemoryDC()
        self._dc.SelectObject(wx.NullBitmap)
        self.artist = None

        center.Bind(self._update_artist)

    @property
    def diameter(self) -> _decimal:
        return self._diameter

    @diameter.setter
    def diameter(self, value: _decimal):
        self._diameter = value
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
    def center(self) -> _point.Point:
        return self._center

    @center.setter
    def center(self, value: _point.Point):
        self._center.Unbind(self._update_artist)
        value.Bind(self._update_artist)
        self._center = value

        self._bmp.Destroy()
        self._update_artist()

    def _get_bmp(self):
        if not self._bmp.IsOk():

            dia = self._diameter

            buf = bytearray([0] * (int(dia) * int(dia) * 4))
            bmp = wx.Bitmap.FromBufferRGBA(dia, dia, buf)
            self._dc.SelectObject(bmp)
            gcdc = wx.GCDC(self._dc)
            gc = gcdc.GetGraphicsContext()

            gc.SetPen(wx.Pen(wx.TRANSPARENT_PEN))
            gc.SetBrush(wx.Brush(wx.Colour(self._color)))

            x, y = self._center.as_float[:-1]

            x -= dia / _decimal(2.0)
            y -= dia / _decimal(2.0)

            gc.DrawEllipse(int(x), int(y), int(dia), int(dia))

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
