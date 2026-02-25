from . import MixinBase
from ..geometry import line as _line
from ..wrappers.decimal import Decimal as _decimal
import wx


class Circle(MixinBase):
    circle_pos = [0, 0]
    circle_handles = []
    circle_using_handle = False
    circle_handle_selected = None
    circle_rect = []
    circle_last_coords = [0, 0]

    def _hit_test_circle_handles(self, x, y):
        for i, _, (x1, y1, x2, y2) in enumerate(self.circle_handles):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        else:
            x1, y1, x2, y2 = self.circle_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                return 9

    def _draw_circle_handles(self):
        x1, y1, x2, y2 = self.circle_rect

        w = x2 - x1
        h = y2 - y1

        dc = self.dc
        dc.SelectObject(self.tool_layer)
        gcdc = wx.GCDC(dc)
        gcdc.Clear()

        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2, wx.PENSTYLE_LONG_DASH))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)
        gcdc.DrawRectangle(x1, y1, w, h)

        mid_x = x1 + int(w / 2)
        mid_y = y1 + int(h / 2)

        self.circle_handles = [
            ((x1, y1, 6, 6), (x1 - 3, y1 - 3, x1 + 3, y1 + 3)),
            ((mid_x, y1, 6, 6), (mid_x - 3, y1 - 3, mid_x + 3, y1 + 3)),
            ((x2, y1, 6, 6), (x2 - 3, y1 - 3, x2 + 3, y1 + 3)),
            ((x2, mid_y, 6, 6), (x2 - 3, mid_y - 3, x2 + 3, mid_y + 3)),
            ((x2, y2, 6, 6), (x2 - 3, y2 - 3, x2 + 3, y2 + 3)),
            ((mid_x, y2, 6, 6), (mid_x - 3, y2 - 3, mid_x + 3, y2 + 3)),
            ((x1, y2, 6, 6), (x1 - 3, y2 - 3, x1 + 3, y2 + 3)),
            ((x1, mid_y, 6, 6), (x1 - 3, mid_y - 3, x1 + 3, mid_y + 3))
        ]

        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 1))

        for rect, _ in self.circle_handles:
            gcdc.DrawRectangle(*rect)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self._update()

    def on_move(self, evt):
        if self.HasCapture():
            if self.circle_using_handle:
                x, y = evt.GetPosition()

                if self.circle_handle_selected is None:
                    sel = self._hit_test_circle_handles(x, y)

                    if sel in (0, 4):
                        self.SetCursor(self.back_angle_cursor)
                    elif sel in (1, 5):
                        self.SetCursor(self.up_down_cursor)
                    elif sel in (2, 6):
                        self.SetCursor(self.forward_angle_cursor)
                    elif sel in (3, 7):
                        self.SetCursor(self.left_right_cursor)
                    elif sel == 9:
                        self.SetCursor(self.move_cursor)
                    else:
                        self.SetCursor(self.pointer_cursor)
                else:
                    x1, y1 = x, y
                    x2, y2 = self.circle_last_coords
                    x = x1 - x2
                    y = y1 - y2

                    self.circle_last_coords = [x1, y1]

                    sel = self.circle_handle_selected
                    if sel == 0:
                        self.circle_rect[0] += x
                        self.circle_rect[1] += y
                    elif sel == 1:
                        self.circle_rect[1] += y
                    elif sel == 2:
                        self.circle_rect[2] += x
                        self.circle_rect[1] += y
                    elif sel == 3:
                        self.circle_rect[2] += x
                    elif sel == 4:
                        self.circle_rect[2] += x
                        self.circle_rect[3] += y
                    elif sel == 5:
                        self.circle_rect[3] += y
                    elif sel == 6:
                        self.circle_rect[0] += x
                        self.circle_rect[3] += y
                    elif sel == 7:
                        self.circle_rect[0] += x
                    elif sel == 9:
                        self.circle_rect[0] += x
                        self.circle_rect[2] += x
                        self.circle_rect[1] += y
                        self.circle_rect[3] += y

                    dc = self.dc
                    dc.SelectObject(self.draw_layer)
                    gcdc = wx.GCDC(dc)
                    gcdc.Clear()

                    gcdc.Destroy()
                    del gcdc

                    gc = wx.GraphicsContext(dc)

                    gc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), self.tool_size))
                    gc.SetBrush(wx.TRANSPARENT_BRUSH)

                    if not self.antialias:
                        gc.SetAntialiasMode(wx.ANTIALIAS_NONE)

                    gc.DrawEllipse(self.circle_rect[0], self.circle_rect[1],
                                   self.circle_rect[2] - self.circle_rect[0],
                                   self.circle_rect[3] - self.circle_rect[1])

                    dc.SelectObject(wx.NullBitmap)

                    self._draw_circle_handles()
            else:
                x1, y1 = self.circle_pos
                x2, y2 = evt.GetPosition()

                line = _line.Line(_decimal(x1), _decimal(y1), _decimal(0),
                                  _decimal(x2), _decimal(y2), _decimal(0))

                radius = len(line)
                x1 -= radius
                y1 -= radius

                dc = self.dc
                dc.SelectObject(self.draw_layer)

                gcdc = wx.GCDC(dc)
                gcdc.Clear()

                gcdc.Destroy()
                del gcdc

                gc = wx.GraphicsContext(dc)
                gc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), self.tool_size))
                gc.SetBrush(wx.TRANSPARENT_BRUSH)
                gc.DrawEllipse(x1, y1, radius * 2, radius * 2)

                dc.SelectObject(wx.NullBitmap)
                self._update()

    def on_left_down(self, evt):
        if self.HasCapture() and self.circle_using_handle:
            x, y = evt.GetPosition()
            self.circle_handle_selected = self._hit_test_circle_handles(x, y)
            if self.circle_handle_selected is None:
                self.circle_last_coords = [0, 0]
            else:
                self.circle_last_coords = [x, y]

        elif not self.HasCapture():
            x, y = evt.GetPosition()
            self.new_draw_layer()
            self.circle_pos = [x, y]
            self.CaptureMouse()

    def on_left_up(self, evt):
        if self.HasCapture():

            dc = self.dc

            x1, y1 = self.circle_pos
            x2, y2 = evt.GetPosition()

            if x1 == x2 and y1 == y2 and self.circle_using_handle:
                if self.circle_handle_selected:
                    self.circle_handle_selected = None
                else:
                    self.ReleaseMouse()
                    self.circle_pos = [0, 0]
                    self.circle_handles = []
                    self.circle_using_handle = False
                    self.circle_handle_selected = None
                    self.circle_rect = []
                    self.circle_last_coords = [0, 0]

                    dc.SelectObject(self.tool_layer)
                    gcdc = wx.GCDC(dc)
                    gcdc.Clear()

                    dc.SelectObject(wx.NullBitmap)

                    gcdc.Destroy()
                    del gcdc

                    self._update()

                evt.Skip()
                return

            line = _line.Line(_decimal(x1), _decimal(y1), _decimal(0),
                              _decimal(x2), _decimal(y2), _decimal(0))

            radius = len(line)
            x1 -= radius
            y1 -= radius

            w = h = radius * 2

            self.circle_rect = [x1, y1, x1 + w, y1 + h]

            self._draw_circle_handles()

        evt.Skip()

    def on_circle(self, evt):
        self.SetCursor(self.cross_cursor)
        self.mode = self.ID_CIRCLE_TOOL
        evt.Skip()

    def on_char(self, evt):
        if self.HasCapture():
            if evt.GetKeycode() == wx.WXK_ESCAPE:
                if (
                    self.circle_using_handle and
                    self.circle_handle_selected is not None
                ):
                    self.circle_handle_selected = None
                    self.circle_last_coords = [0, 0]
                elif not self.circle_using_handle:
                    self.circle_pos = [0, 0]
                    self.circle_handles = []
                    self.circle_using_handle = False
                    self.circle_handle_selected = None
                    self.circle_rect = []
                    self.circle_last_coords = [0, 0]

                    self.draw_layer.Destroy()
                    self.draw_layer = self.undo_layers.pop(-1)

                    self._update()
