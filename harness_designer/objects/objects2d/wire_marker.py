# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


# from ...geometry import point as _point
# from ...geometry import angle as _angle
from PySide6.QtWidgets import QMenu
from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


class WireMarker(_base2d.Base2D):
    """Represent a wire marker in :mod:`harness_designer.objects.objects2d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker"

    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """

        _base2d.Base2D.__init__(self, parent, db_obj)

        self._part = db_obj.part
        self._wire = self.db_obj.wire
        self._p1 = db_obj.position2d

        self._wire_p1 = self._wire.start_point2d.point
        self._wire_p2 = self._wire.stop_point2d.point
        self._hit_test_rect = None

        #
        # self._wire_p1.bind(self._update_bitmap)
        # self._wire_p2.bind(self._update_bitmap)
        # self._p1.bind(self._update_bitmap)

    # def _update_bitmap(self, *_):
    #     label = self.db_obj.label
    #
    #     height = rect_h = self.db_obj.wire.info.pixel_width
    #
    #     angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)
    #
    #     if label:
    #         text_w, text_h = self._dc.GetTextExtent(label)
    #
    #         width = text_w
    #
    #         if text_h < height:
    #             offset = (height - text_h) // 2
    #             text_y = offset
    #             rect_y = 0
    #
    #         else:
    #             height += text_h
    #             text_y = 0
    #             rect_y = text_h
    #
    #         buf = bytearray([0] * (width * height * 4))
    #
    #         bitmap = wx.Bitmap.FromBufferRGBA(width, height, buf)
    #         self._dc.SelectObject(bitmap)
    #         gcdc = wx.GCDC(self._dc)
    #
    #         gcdc.SetTextForeground(wx.Colour(0, 0, 0, 255))
    #         gcdc.SetTextBackground(wx.Colour(0, 0, 0, 0))
    #
    #         gcdc.SetBrush(wx.Brush(self._part.color.ui))
    #         gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255)))
    #
    #         gcdc.DrawRectangle(0, rect_y, width, rect_h)
    #         gcdc.DrawText(0, text_y, label)
    #
    #     else:
    #         width = height * 2
    #
    #         buf = bytearray([0] * (width * height * 4))
    #
    #         bitmap = wx.Bitmap.FromBufferRGBA(width, height, buf)
    #         self._dc.SelectObject(bitmap)
    #         gcdc = wx.GCDC(self._dc)
    #
    #         gcdc.SetBrush(wx.Brush(self._part.color.ui))
    #         gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255)))
    #
    #         gcdc.DrawRectangle(0, 0, width, rect_h)
    #
    #     self._dc.SelectObject(wx.NullBitmap)
    #     gcdc.Destroy()
    #     del gcdc
    #
    #     p1 = _point.Point(self._p1.x, self._p1.y - (_d(height) / _d(2.0)))
    #     p2 = _point.Point(width, height)
    #     p2 @= angle
    #     p2 += p1
    #
    #     self._hit_test_rect = [p1, p2]
    #
    #     self._bitmap.Destroy()
    #     self._bitmap = bitmap
    #
    # def hit_test(self, p: _point.Point):
    #     if self._hit_test_rect is None:
    #         return False
    #
    #     p1, p2 = self._hit_test_rect
    #     return p1 <= p <= p2
    #
    # def draw(self, gc: wx.GraphicsContext, gcdc: wx.GCDC):
    #     if not self._bitmap.IsOk():
    #         return
    #
    #     width = self._bitmap.GetWidth()
    #     height = self._bitmap.GetHeight()
    #
    #     wire_dia = self._wire_info.pixel_width
    #
    #     offset = -(_d(height) / _d(2.0))
    #     offset += _d(wire_dia) - _d(height)
    #
    #     angle = _angle.Angle.from_points(self._wire_p1, self._wire_p2)
    #     angle2d = angle.z
    #
    #     p1 = _point.Point(_d(0.0), offset)
    #     p1 += self._p1
    #
    #     gc.PushState()
    #     gc.Rotate(float(angle2d))
    #     gc.DrawBitmap(self._bitmap, float(p1.x), float(p1.y), float(width), float(height))
    #     gc.PopState()


class WireMarkerMenu(QMenu):
    """Represent a wire marker menu in :mod:`harness_designer.objects.objects2d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`WireMarkerMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Set Label')
        action.triggered.connect(self.on_set_label)

        action = self.addAction('Flip Label')
        action.triggered.connect(self.on_flip_label)

        self.addSeparator()

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_set_label(self):
        """Handle the set label event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_flip_label(self):
        """Handle the flip label event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
