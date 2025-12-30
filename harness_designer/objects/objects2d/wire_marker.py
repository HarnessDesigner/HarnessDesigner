from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from ... import editor_2d as _editor_2d
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


class WireMarker:

    def __init__(self, editor_2d: "_editor_2d.Editor2D",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):

        self.editor_2d = editor_2d
        self._db_obj = db_obj
        self._part = db_obj.part
        self._wire = self._db_obj.wire
        self._p1 = db_obj.point_2d.point

        self._wire_p1 = self._wire.start_point2d.point
        self._wire_p2 = self._wire.stop_point2d.point
        self._hit_test_rect = None

        self._dc = wx.MemoryDC()
        self._bitmap = wx.NullBitmap

        self._wire_p1.Bind(self._update_bitmap)
        self._wire_p2.Bind(self._update_bitmap)
        self._p1.Bind(self._update_bitmap)

    def _update_bitmap(self, *_):
        label = self._db_obj.label

        height = rect_h = self._db_obj.wire.info.pixel_width

        angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)

        if label:
            text_w, text_h = self._dc.GetTextExtent(label)

            width = text_w

            if text_h < height:
                offset = (height - text_h) // 2
                text_y = offset
                rect_y = 0

            else:
                height += text_h
                text_y = 0
                rect_y = text_h

            buf = bytearray([0] * (width * height * 4))

            bitmap = wx.Bitmap.FromBufferRGBA(width, height, buf)
            self._dc.SelectObject(bitmap)
            gcdc = wx.GCDC(self._dc)

            gcdc.SetTextForeground(wx.Colour(0, 0, 0, 255))
            gcdc.SetTextBackground(wx.Colour(0, 0, 0, 0))

            gcdc.SetBrush(wx.Brush(self._part.color.ui))
            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255)))

            gcdc.DrawRectangle(0, rect_y, width, rect_h)
            gcdc.DrawText(0, text_y, label)

        else:
            width = height * 2

            buf = bytearray([0] * (width * height * 4))

            bitmap = wx.Bitmap.FromBufferRGBA(width, height, buf)
            self._dc.SelectObject(bitmap)
            gcdc = wx.GCDC(self._dc)

            gcdc.SetBrush(wx.Brush(self._part.color.ui))
            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255)))

            gcdc.DrawRectangle(0, 0, width, rect_h)

        self._dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

        p1 = _point.Point(self._p1.x, self._p1.y - (_decimal(height) / _decimal(2.0)))
        p2 = _point.Point(width, height)
        p2 @= angle
        p2 += p1

        self._hit_test_rect = [p1, p2]

        self._bitmap.Destroy()
        self._bitmap = bitmap

    def hit_test(self, p: _point.Point):
        if self._hit_test_rect is None:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= p <= p2

    def draw(self, gc: wx.GraphicsContext, gcdc: wx.GCDC):
        if not self._bitmap.IsOk():
            return

        width = self._bitmap.GetWidth()
        height = self._bitmap.GetHeight()

        wire_dia = self._wire_info.pixel_width

        offset = -(_decimal(height) / _decimal(2.0))
        offset += _decimal(wire_dia) - _decimal(height)

        angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)
        angle_2d = angle.z

        p1 = _point.Point(_decimal(0.0), offset)
        p1 += self._p1

        gc.PushState()
        gc.Rotate(float(angle_2d))
        gc.DrawBitmap(self._bitmap, float(p1.x), float(p1.y), float(width), float(height))
        gc.PopState()
