from . import MixinBase

import wx


class Pointer(MixinBase):

    layer_ctrl: wx.Choice = None
    cavity_map = None
    cavity_selected = None
    cavity_rect = [0, 0, 0, 0]
    cavity_handles = []
    cavity_coords = []
    cavity_handle_selected = None

    def _draw_cavity_handles(self):
        x1, y1, x2, y2 = self.cavity_rect

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

        self.cavity_handles = [
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

        for rect, _ in self.cavity_handles:
            gcdc.DrawRectangle(*rect)

        dc.SelectObject(wx.NullBitmap)

        gcdc.Destroy()
        del gcdc

        self._update()

    def _hit_test_cavity_handles(self, x, y):
        for i, _, (x1, y1, x2, y2) in enumerate(self.cavity_handles):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        else:
            x1, y1, x2, y2 = self.cavity_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                return 9

    def on_move(self, evt):
        x1, y1 = evt.GetPosition()

        if self.HasCapture() and self.cavity_handle_selected is not None:
            x2, y2 = self.cavity_coords
            x = x1 - x2
            y = y1 - y2

            self.cavity_coords = [x1, y1]

            if self.cavity_handle_selected == 0:
                self.cavity_rect[0] += x
                self.cavity_rect[1] += y
            elif self.cavity_handle_selected == 1:
                self.cavity_rect[1] += y
            elif self.cavity_handle_selected == 2:
                self.cavity_rect[2] += x
                self.cavity_rect[1] += y
            elif self.cavity_handle_selected == 3:
                self.cavity_rect[2] += x
            elif self.cavity_handle_selected == 4:
                self.cavity_rect[2] += x
                self.cavity_rect[3] += y
            elif self.cavity_handle_selected == 5:
                self.cavity_rect[3] += y
            elif self.cavity_handle_selected == 6:
                self.cavity_rect[0] += x
                self.cavity_rect[3] += y
            elif self.cavity_handle_selected == 7:
                self.cavity_rect[0] += x
            elif self.cavity_handle_selected == 9:
                self.cavity_rect[0] += x
                self.cavity_rect[2] += x
                self.cavity_rect[1] += y
                self.cavity_rect[3] += y

            self._draw_cavity_handles()
            self._update()

        else:
            hit_index = self._hit_test_cavity_handles(x1, y1)
            if hit_index is None:
                self.SetCursor(self.pointer_cursor)

            if hit_index in (0, 4):
                self.SetCursor(self.back_angle_cursor)
            elif hit_index in (1, 5):
                self.SetCursor(self.up_down_cursor)
            elif hit_index in (2, 6):
                self.SetCursor(self.forward_angle_cursor)
            elif hit_index in (3, 7):
                self.SetCursor(self.left_right_cursor)
            elif hit_index == 9:
                self.SetCursor(self.move_cursor)

    def on_left_down(self, evt):
        if self.layer_ctrl.GetStringSelection() == 'overlay':
            x, y = evt.GetPosition()

            if self.cavity_selected is not None:
                self.cavity_handle_selected = self._hit_test_cavity_handles(x, y)

                if self.cavity_handle_selected is None:
                    self.cavity_selected = None
                    self.cavity_rect = [0, 0, 0, 0]
                    self.cavity_handles = []
                    self.cavity_coords = []
                    self.cavity_handle_selected = None
                    self.ReleaseMouse()
                else:
                    return

            for cavity in self.cavity_map.cavities:
                x1 = cavity.x
                y1 = cavity.y
                w = cavity.width
                h = cavity.height
                x2 = x1 + w
                y2 = y1 + h

                if x1 <= x <= x2 and y1 <= y <= y2:
                    break
            else:
                if self.HasCapture():
                    self.cavity_selected = None
                    self.cavity_rect = [0, 0, 0, 0]
                    self.cavity_handles = []
                    self.cavity_coords = []
                    self.cavity_handle_selected = None
                    self.ReleaseMouse()
                return

            self.cavity_rect = [x1, y1, x2, y2]
            self.CaptureMouse()
            self._draw_cavity_handles()

    def on_left_up(self, evt):
        if self.HasCapture():
            if self.cavity_selected is None:
                self.ReleaseMouse()
            elif self.cavity_handle_selected is not None:
                self.cavity_handle_selected = None
                self.cavity_coords = [0, 0]

    def on_pointer(self, evt):
        self.SetCursor(self.pointer_cursor)
        self.mode = self.ID_POINTER_TOOL
        evt.Skip()
