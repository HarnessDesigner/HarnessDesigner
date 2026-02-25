from . import MixinBase

import wx


class Pencil(MixinBase):

    def on_move(self, evt):
        if self.HasCapture():
            dc = self.dc
            dc.SelectObject(self.draw_layer)
            dc.SetUserScale(self.scale, self.scale)
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))

            dc.DrawPoint(evt.GetPosition())
            dc.SelectObject(wx.NullBitmap)

            self._update()

    def on_left_down(self, evt):
        self.new_draw_layer()

        dc = self.dc
        dc.SelectObject(self.draw_layer)
        dc.SetUserScale(self.scale, self.scale)
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))

        dc.DrawPoint(evt.GetPosition())
        dc.SelectObject(wx.NullBitmap)

        self._update()

        if not self.HasCapture():
            self.CaptureMouse()

    def on_left_up(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()

    def on_pencil(self, evt):
        self.SetCursor(self.pencil_cursor)
        self.mode = self.ID_PENCIL_TOOL
        evt.Skip()
