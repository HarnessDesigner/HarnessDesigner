from . import MixinBase

import wx


class Crop(MixinBase):
    crop_coords = [0, 0]
    crop_grab_pos: int = 0
    crop_view_coords = [0, 0, 0, 0]
    crop_handles = []
    render_objs = []

    def _hit_test_view(self, x, y):
        for i, handle in enumerate(self.crop_handles):
            x1, y1, x2, y2 = handle[1]

            if x1 <= x <= x2 and y1 <= y <= y2:
                return i

        x1, y1, x2, y2 = self.crop_view_coords
        if x1 <= x <= x2 and y1 <= y <= y2:
            return 9

    def on_move(self, evt):
        x1, y1 = evt.GetPosition()

        if self.HasCapture():
            x2, y2 = self.crop_coords
            x = x1 - x2
            y = y1 - y2

            self.crop_coords = [x1, y1]

            if self.crop_grab_pos == 0:
                self.crop_view_coords[0] += x
                self.crop_view_coords[1] += y
            elif self.crop_grab_pos == 1:
                self.crop_view_coords[1] += y
            elif self.crop_grab_pos == 2:
                self.crop_view_coords[2] += x
                self.crop_view_coords[1] += y
            elif self.crop_grab_pos == 3:
                self.crop_view_coords[2] += x
            elif self.crop_grab_pos == 4:
                self.crop_view_coords[2] += x
                self.crop_view_coords[3] += y
            elif self.crop_grab_pos == 5:
                self.crop_view_coords[3] += y
            elif self.crop_grab_pos == 6:
                self.crop_view_coords[0] += x
                self.crop_view_coords[3] += y
            elif self.crop_grab_pos == 7:
                self.crop_view_coords[0] += x
            elif self.crop_grab_pos == 9:
                self.crop_view_coords[0] += x
                self.crop_view_coords[2] += x
                self.crop_view_coords[1] += y
                self.crop_view_coords[3] += y

            Crop._draw(self)
            self._update()

        else:
            hit_index = self._hit_test_view(x1, y1)
            if hit_index is None:
                self.SetCursor(self.pointer_cursor)

            if hit_index in (0, 4):
                self.SetCursor(self.back_angle_cursor)
            elif hit_index in (2, 6):
                self.SetCursor(self.forward_angle_cursor)
            elif hit_index in (1, 5):
                self.SetCursor(self.up_down_cursor)
            elif hit_index in (3, 7):
                self.SetCursor(self.left_right_cursor)
            elif hit_index == 9:
                self.SetCursor(self.move_cursor)

    def on_left_down(self, evt):
        x, y = evt.GetPosition()
        pos = self._hit_test_view(x, y)
        if pos is not None:
            self.crop_grab_pos = pos
            self.crop_coords = [x, y]
            self.CaptureMouse()

    def on_left_up(self, evt):
        self.crop_grab_pos = None
        self.crop_coords = [0, 0]

        if self.HasCapture():
            self.ReleaseMouse()

    def on_undo_crop(self, evt):
        self.crop_view_coords = [0, 0, self.max_x, self.max_y]
        Crop.commit(self)
        evt.Skip()

    def commit(self):
        x1, y1, x2, y2 = self.crop_view_coords

        w = x2 - x1
        h = y2 - y1
        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)

        dc = self.dc
        dc.SelectObject(bmp)

        gcdc = wx.GCDC(dc)
        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
        gcdc.SetUserScale(self.scale, self.scale)

        x1 = int(x1 / self.scale)
        y1 = int(y1 / self.scale)
        x2 = int(x2 / self.scale)
        y2 = int(y2 / self.scale)

        for obj in self.render_objs:
            obj.draw(gcdc, x1, y1, x2, y2)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self.background = bmp
        self.scale = 1.0
        self._update()

    def _draw(self):
        dc = self.dc
        dc.SelectObject(self.tool_layer)
        gcdc = wx.GCDC(dc)
        gcdc.Clear()
        gcdc.SetUserScale(self.scale, self.scale)
        gcdc.SetPen(wx.TRANSPARENT_PEN)
        gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 125)))

        w, h = self.tool_layer.GetSize()

        if self.crop_view_coords is None:
            x1 = int(w * 0.25)
            y1 = int(h * 0.25)
            x2 = w - x1
            y2 = h - y1

            self.crop_view_coords = [x1, y1, x2, y2]

        x1, y1, x2, y2 = self.crop_view_coords

        gcdc.DrawRectangle(0, 0, x1, h)
        gcdc.DrawRectangle(x2, 0, abs(x2 - w), h)
        gcdc.DrawRectangle(x1, 0, x2 - x1, y1)
        gcdc.DrawRectangle(x1, y2, x2 - x1, abs(y2 - h))

        gcdc.SetPen(wx.Pen(wx.Colour(255, 0, 0, 200), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

        gcdc.DrawRectangle(x1, y1, x2 - x1, y2 - y1)

        hbw = int((x2 - x1) / 2)
        hbh = int((y2 - y1) / 2)
        x1m = x1 - 6
        x1p = x1 + 6
        y1m = y1 - 6
        y1p = y1 + 6
        x2m = x2 - 6
        x2p = x2 + 6
        y2m = y2 - 6
        y2p = y2 + 6

        self.handles = [
            ((x1, y1), (x1m, y1m, x1p, y1p)),
            ((x1 + hbw, y1), (x1m + hbw, y1m, x1p + hbw, y1p)),
            ((x2, y1), (x2m, y1m, x2p, y1p)),
            ((x2, y1 + hbh), (x2m, y1m + hbh, x2p, y1p + hbh)),
            ((x2, y2), (x2m, y2m, x2p, y2p)),
            ((x1 + hbw, y2), (x1m + hbw, y2m, x1p + hbw, y2p)),
            ((x1, y2), (x1m, y2m, x1p, y2p)),
            ((x1, y1 + hbh), (x1m, y1m + hbh, x1p, y1p + hbh))
        ]

        for line in self.handles:
            handle = line[0]
            gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))
            gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
            gcdc.DrawCircle(handle[0], handle[1], 5)

            gcdc.SetPen(wx.TRANSPARENT_PEN)
            gcdc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 255)))
            gcdc.DrawCircle(handle[0], handle[1], 3)

        dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

    def on_crop_tool(self, evt):
        self.SetCursor(self.pointer_cursor)
        self.mode = self.ID_CROP_TOOL

        Crop._draw(self)
        self._update()
        evt.Skip()
