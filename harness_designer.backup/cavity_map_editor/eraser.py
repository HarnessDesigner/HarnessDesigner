from . import MixinBase

import wx


class Eraser(MixinBase):

    def _draw(self, evt):
        if self.HasCapture():
            dc = self.dc
            x, y = evt.GetPosition()

            dc.SelectObject(self.draw_layer)
            gcdc = wx.GCDC(dc)
            gcdc.Clear()

            gcdc.Destroy()
            del gcdc

            gc = wx.GraphicsContext.Create(dc)

            if not self.antialias:
                gc.SetAntialiasMode(wx.ANTIALIAS_NONE)

            gc.SetPen(wx.TRANSPARENT_PEN)
            gc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 255)))

            size = self.tool_size * self.scale
            x -= size / 2
            y -= size / 2

            gc.DrawEllipse(x, y, size, size)
            dc.SelectObject(wx.NullBitmap)

    def on_move(self, evt):
        x, y = evt.GetPosition()

        dc = self.dc
        dc.SelectObject(self.tool_layer)

        gcdc = wx.GCDC(dc)
        gcdc.Clear()

        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

        gcdc.DrawCircle(x, y, int(self.tool_size * self.scale / 2))

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        Eraser._draw(self, evt)

        self._update()

    def on_left_down(self, evt):
        if not self.HasCapture():
            self.new_draw_layer()
            self.CaptureMouse()
            Eraser._draw(self, evt)

    def on_left_up(self, evt):
        if self.HasCapture():
            self.ReleaseMouse()

    def on_eraser(self, evt):
        self.SetCursor(self.cross_cursor)
        self.mode = self.ID_ERASER_TOOL
        evt.Skip()
