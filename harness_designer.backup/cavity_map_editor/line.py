from . import MixinBase

import wx


class Line(MixinBase):

    line_coords = [0, 0]

    def on_move(self, evt):
        if self.HasCapture():
            x1, y1 = self.line_coords
            x2, y2 = evt.GetPosition()

            dc = self.dc
            dc.SelectObject(self.draw_layer)
            dc.SetUserScale(self.scale, self.scale)

            gcdc = wx.GCDC(dc)
            gcdc.Clear()

            gcdc.Destroy()
            del gcdc

            gc = wx.GraphicsContext.Create(dc)

            if not self.antialias:
                gc.SetAntialiasMode(wx.ANTIALIAS_NONE)

            gc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), self.tool_size))
            gc.SetBrush(wx.TRANSPARENT_BRUSH)

            path = gc.CreatePath()
            path.MoveToPoint(x1, y1)
            path.AddLineToPoint(x2, y2)
            path.CloseSubpath()

            gc.StrokePath(path)

            dc.SelectObject(wx.NullBitmap)

            self._update()

    def on_left_down(self, evt):
        if not self.HasCapture():
            x, y = evt.GetPosition()
            self.new_draw_layer()
            self.line_coords = [x, y]
            self.CaptureMouse()

    def on_left_up(self, evt):
        if self.HasCapture():
            self.line_coords = [0, 0]
            self.ReleaseMouse()

    def on_line(self, evt):
        self.SetCursor(self.cross_cursor)
        self.mode = self.ID_LINE_TOOL
        evt.Skip()
