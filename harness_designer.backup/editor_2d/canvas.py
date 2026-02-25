from typing import TYPE_CHECKING

import wx

from ..geometry import point as _point
from ..geometry import line as _line
from ..geometry import angle as _angle
from ..wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from .. import objects as _objects
    from . import Editor2D as _Editor2D
    from .. import ui as _ui


class Canvas(wx.Panel):

    def __init__(self, parent: "_Editor2D"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.mainframe: "_ui.MainFrame" = parent.mainframe

        buf = bytearray([0] * (3000 * 2000 * 4))
        self.bmp = wx.Bitmap.FromBufferRGBA(3000, 2000, buf)

        self.scale = 1.0
        self.last_scale = 1.0

        # self.wires: list[_wire.Wire] = []
        # self._selected: _wire.WireSection = None
        self.last_pos: _point.Point = None
        self._offset = _point.Point(_decimal(0.0), _decimal(0.0))
        self._grabbed_point = None
        self._o_grab_point = None
        self._continue_wire = False
        self._selected_obj: "_objects.ObjectBase" = None
        self.global_db: "_global_db.GLBTables" = None
        self.project_db: "_project_db.PJTTables" = None

        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.points = []
        self.point_list = []

        for x in range(0, self.bmp.GetWidth() + 20, 20):
            for y in range(0, self.bmp.GetHeight() + 20, 20):
                self.points.append(_point.Point(_decimal(x), _decimal(y)))
                self.point_list.append([x, y])

        cursor = wx.Cursor(wx.CURSOR_BLANK)
        self.SetCursor(cursor)
        self.mouse_pos = None

        self.update_bitmap()

    def set_selected_object(self, obj: "_objects.ObjectBase"):
        self._selected_obj = obj

    def get_selected_obj(self) -> "_objects.ObjectBase":
        return self._selected_obj

    def update(self):

        def _do():
            self.Update()
            self.Refresh()

        wx.CallAfter(_do)

    def on_mousewheel(self, evt: wx.MouseEvent):
        rotation = evt.GetWheelRotation() / 3000

        self.scale += rotation

        if self.scale < 0.2:
            self.scale = 0.2
        elif self.scale > 10.0:
            self.scale = 10.0

        x, y = evt.GetPosition()

        self._offset.x -= _decimal(x) * _decimal(rotation) / _decimal(self.scale)
        self._offset.y -= _decimal(y) * _decimal(rotation) / _decimal(self.scale)
        # if self._offset.x > 0:
        #     self._offset.x = _decimal(0)
        # if self._offset.y > 0:
        #     self._offset.y = _decimal(0)
        #
        # cw, ch = self.panel.GetSize()
        # bw, bh = self.bmp.GetSize()
        # w = cw - bw
        # h = ch - bh
        #
        # if self._offset.x < w:
        #     self._offset.x = _decimal(w)
        # if self._offset.y < h:
        #     self._offset.y = _decimal(h)

        self.update()
        evt.Skip()

    def load_databases(self, global_db: "_global_db.GLBTables", project_db: "_project_db.PJTTables"):
        self.global_db = global_db
        self.project_db = project_db

        from ..database.project_db import pjt_wire as _pjt_wire
        from ..database.project_db import pjt_splice as _pjt_splice
        from ..database.project_db import pjt_housing as _pjt_housing
        from ..database.project_db import pjt_terminal as _pjt_terminal
        from ..database.project_db import pjt_wire2d_layout as _pjt_wire2d_layout

        self.db_wires: list[_pjt_wire.PJTWire] = list(project_db.pjt_wires_table)
        self.db_splices: list[_pjt_splice.PJTSplice] = list(project_db.pjt_splices_table)
        self.db_housings: list[_pjt_housing.PJTHousing] = list(project_db.pjt_housings_table)
        self.db_terminals: list[_pjt_terminal.PJTTerminal] = list(project_db.pjt_terminals_table)
        self.db_layouts: list[_pjt_wire2d_layout.PJTWire2DLayout] = list(project_db.pjt_wire2d_layouts_table)

        for wire in self.db_wires:
            start_point = wire.start_point2d.point
            end_point = wire.stop_point2d.point
            part = wire.part

            color = part.color
            stripe = part.stripe_color
            awg = part.size_awg
            mm2 = part.size_mm2
            diameter = part.od_mm

            wire.Bind(self._update_wire)

    def update_bitmap(self):
        w, h = self.bmp.GetSize()
        mask_dc = wx.MemoryDC()
        buf = bytearray([0] * (w * h * 4))
        mask_bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)
        mask_dc.SelectObject(mask_bmp)
        mask_gc = wx.GraphicsContext.Create(mask_dc)
        mask_gc.SetBrush(wx.Brush(wx.BLACK))

        dc = wx.MemoryDC()
        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)
        dc.SelectObject(bmp)
        gc = wx.GraphicsContext.Create(dc)

        # for wire in self.wires:
        #     wire.draw(gc, mask_gc, self._selected)

        mask_dc.SelectObject(wx.NullBitmap)
        mask = wx.Mask(mask_bmp, wx.BLACK)

        dc.SelectObject(wx.NullBitmap)
        bmp.SetMask(mask)

        buf = bytearray([0] * (w * h * 4))
        new_bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)
        dc.SelectObject(new_bmp)
        gcdc = wx.GCDC(dc)
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
        gcdc.SetPen(wx.Pen(wx.BLACK, 2))
        gcdc.DrawPointList(self.point_list)
        gcdc.DrawBitmap(bmp, 0, 0, useMask=True)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self.bmp.Destroy()
        self.bmp = new_bmp

    def on_paint(self, evt):
        pdc = wx.BufferedPaintDC(self)
        gcdc = wx.GCDC(pdc)
        gcdc.Clear()
        gcdc.SetUserScale(self.scale, self.scale)
        gcdc.DrawBitmap(self.bmp, int(self._offset.x * _decimal(self.scale)), int(self._offset.y * _decimal(self.scale)))

        if self._selected is not None:
            gcdc.SetPen(wx.Pen(wx.BLACK, width=3, style=wx.PENSTYLE_SHORT_DASH))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

            gc = gcdc.GetGraphicsContext()
            self._selected.parent.draw_selected(gc, self._selected)

        gcdc.SetUserScale(1.0, 1.0)

        if self.mouse_pos is not None:
            x, y = self.mouse_pos
            w, h = self.GetSize()

            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 40), 1))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
            gcdc.DrawLine(0, y, w, y)
            gcdc.DrawLine(x, 0, x, h)

            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))
            gcdc.DrawLine(x - 10, y, x + 10, y)
            gcdc.DrawLine(x, y - 10, x, y + 10)

        gcdc.Destroy()
        del gcdc

        evt.Skip()

    def on_erase_background(self, _):
        pass

    def on_left_down(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()

        p = _point.Point(_decimal(x) * _decimal(self.scale) + self._offset.x,
                         _decimal(y) * _decimal(self.scale) + self._offset.y)

        if self._selected is not None and self._grabbed_point is not None:
            self._continue_wire = True
            wire = self.wires[-1]
            self._selected = wire.new_section(p)
            self._grabbed_point = self._selected.p2
            self._o_grab_point = self._selected.p2.copy()
            self.last_pos = p
            self.update_bitmap()
            self.update()

        elif self._selected is None:
            for wire in self.wires:
                section = wire.get_section(p)
                if section is not None:
                    wire.is_selected(True)
                    self._selected = section
                    self.last_pos = p
                    if section.is_p1_end_grabbed(p):
                        self._grabbed_point = section.p1
                        self._o_grab_point = section.p1.copy()
                    elif section.is_p2_end_grabbed(p):
                        self._grabbed_point = section.p2
                        self._o_grab_point = section.p2.copy()
                    else:
                        self._grabbed_point = None

                    def _do():
                        self.update_bitmap()
                        self.update()

                    wx.CallAfter(_do)
                    break

        evt.Skip()

    def on_left_up(self, evt):
        if self._selected is None:
            x, y = evt.GetPosition()

            p = _point.Point(_decimal(x) * _decimal(self.scale) + self._offset.x,
                             _decimal(y) * _decimal(self.scale) + self._offset.y)

            wire = _wire.Wire(self, )
            self.wire_info_ctrl.set_wire(wire.wire_info)
            self._selected = wire.new_section(p)
            self._grabbed_point = self._selected.p2
            self._o_grab_point = self._selected.p2.copy()
            self.last_pos = p
            self.wires.append(wire)
            self.update_bitmap()
            self.update()

        elif not self._continue_wire and self._grabbed_point is not None:
            self._selected.parent.is_selected(False)
            self._selected = None
            self._grabbed_point = None

        def _do():
            self.update_bitmap()
            self.update()

        wx.CallAfter(_do)
        evt.Skip()

    def on_right_down(self, evt):
        if self._selected is not None:
            self._selected = None
            self._grabbed_point = None
            self._continue_wire = False

            if self._grabbed_point is not None:
                self.wires[-1].remove_last_section()

            if len(self.wires[-1]) == 0:
                self.wires.pop(-1)

            def _do():
                self.update_bitmap()
                self.update()

            wx.CallAfter(_do)

        x, y = evt.GetPosition()
        self.last_pos = _point.Point(_decimal(x), _decimal(y))

        evt.Skip()

    def on_right_up(self, evt):
        evt.Skip()

    def on_motion(self, evt: wx.MouseEvent):
        x, y = evt.GetPosition()
        self.mouse_pos = (x, y)

        p = _point.Point(_decimal(x) * _decimal(self.scale) + self._offset.x, _decimal(y) * _decimal(self.scale) + self._offset.y)
        if evt.RightIsDown():
            diff = p - self.last_pos
            self._offset += diff
            if self._offset.x > 0:
                self._offset.x = _decimal(0)
            if self._offset.y > 0:
                self._offset.y = _decimal(0)

            cw, ch = self.GetSize()
            bw, bh = self.bmp.GetSize()
            w = cw - bw
            h = ch - bh

            if self._offset.x < w:
                self._offset.x = _decimal(w)
            if self._offset.y < h:
                self._offset.y = _decimal(h)

            self.last_pos = p
            self.update()
        elif self._selected is not None and self._grabbed_point is not None:
            self._selected.move_p2(p)

            def _do():
                self._selected.update_wire_info()
            wx.CallAfter(_do)

            self.last_pos = p
            self.update()

        elif self._selected is not None and evt.LeftIsDown():
            diff = p - self.last_pos
            self._selected.move(diff)
            self.last_pos = p

            def _do():
                self.update_bitmap()
                self.update()

            wx.CallAfter(_do)

        else:
            self.update()

        evt.Skip()


