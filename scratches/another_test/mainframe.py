import wx

import canvas as _canvas
import control_panel as _control_panel
import axis_indicators as _axis_indicators

from geometry import point as _point
from wrappers.wrap_decimal import Decimal as _decimal

from objects import housing as _housing


female_terminal_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\12191818_3D_STP.stp'
seal_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15326864_3D_STP.stp'
plug_path = r''
female_housing_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15326864_3D_STP.stp'
male_housing_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15326868_3D_STP.stp'
stl_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15326864_3D_STP.stp'



class MainFrame(wx.Frame):

    def __init__(self):
        w, h = wx.GetDisplaySize()
        w = (w // 3) * 2
        h = (h // 3) * 2

        wx.Frame.__init__(self, None, wx.ID_ANY, size=(w, h))
        self.CenterOnScreen()

        w, h = self.GetClientSize()

        w //= 6

        self.canvas_panel = _canvas.CanvasPanel(self, size=(w * 5, h))
        self.canvas = self.canvas_panel.canvas

        self.cp = _control_panel.ControlPanel(self, size=(w, h))
        self.toolbar = wx.ToolBar(self, wx.ID_ANY)

        move_icon = wx.Bitmap('../../harness_designer/image/icons/move.png')
        rotate_icon = wx.Bitmap('../../harness_designer/image/icons/rotate.png')

        move_icon = move_icon.ConvertToImage().Scale(
            32, 32).ConvertToBitmap()

        rotate_icon = rotate_icon.ConvertToImage().Scale(
            32, 32).ConvertToBitmap()

        self.move_tool = self.toolbar.AddCheckTool(
            wx.ID_ANY, 'Move', move_icon)

        self.rotate_tool = self.toolbar.AddCheckTool(
            wx.ID_ANY, 'Rotate', rotate_icon)

        self.rotate_tool_state = False
        self.move_tool_state = False

        self.Bind(wx.EVT_TOOL, self.on_move_tool, id=self.move_tool.GetId())
        self.Bind(wx.EVT_TOOL, self.on_rotate_tool, id=self.rotate_tool.GetId())
        self.Bind(wx.EVT_MOVE, self.on_move)

        self.toolbar.Realize()

        self.SetToolBar(self.toolbar)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.canvas_panel, 6, wx.EXPAND)
        hsizer.Add(self.cp, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.housing = None
        self.housings = []
        self.rotate_object = None
        self.move_object = None
        self._last_frame_screen_pos = None
        self._last_size = self.GetSize()

        wx.CallAfter(self.on_move)

    def on_move(self, evt=None):
        if evt is not None:
            evt.Skip()

        # Container client size (logical coords)
        cw, ch = self.canvas_panel.GetClientSize()
        csize = _point.Point(_decimal(cw), _decimal(ch))
        view_size = self.canvas.get_view_size()

        offset = (csize - view_size) / _decimal(2.0)

        # On initial placement we just center and record the frame pos
        cur_frame_pos = self.GetScreenPosition()
        if self._last_frame_screen_pos is None:
            self._last_frame_screen_pos = cur_frame_pos
            # self.canvas_panel.panel.SetSize(view_size.as_int[:-1])
            self.canvas_panel.panel.SetPosition(offset.as_int[:-1])
            return

        # compute how much left/top moved outward
        # (positive only when left/top moved outward)
        last_x = self._last_frame_screen_pos.x
        last_y = self._last_frame_screen_pos.y

        cur_x, cur_y = cur_frame_pos.x, cur_frame_pos.y

        if last_x != cur_x or last_y != cur_y:
            offset += _point.Point(_decimal(cur_x - last_x),
                                   _decimal(cur_y - last_y))

            self._last_frame_screen_pos = cur_frame_pos

        self.canvas_panel.panel.SetPosition(offset.as_int[:-1])

        size = self.GetSize()
        if size != self._last_size:
            self._last_size = size
        else:
            self.SendSizeEvent()
        return

    def get_rotate_tool_state(self):
        return self.rotate_tool_state

    def get_move_tool_state(self):
        return self.move_tool_state

    def on_rotate_tool(self, evt: wx.MenuEvent):
        if self.move_tool_state:
            self.move_tool.SetToggle(False)
            self.move_tool_state = False

        self.rotate_tool_state = not self.rotate_tool_state

        if self.rotate_tool_state:
            self.rotate_tool.SetToggle(True)
        else:
            self.rotate_tool.SetToggle(False)

        if self.rotate_tool_state:
            if self.move_object is not None:
                self.move_object.stop_move()
                self.move_object = None

            if self.canvas.selected is not None:
                self.rotate_object = self.canvas.selected
                self.rotate_object.start_angle()
                self.canvas.Refresh(False)

        elif self.rotate_object is not None:
            self.rotate_object.stop_angle()
            self.rotate_object = None

            self.canvas.Refresh(False)

        evt.Skip()

    def on_move_tool(self, evt: wx.MenuEvent):
        if self.rotate_tool_state:
            self.rotate_tool.SetToggle(False)
            self.rotate_tool_state = False

        self.move_tool_state = not self.move_tool_state
        if self.move_tool_state:
            self.move_tool.SetToggle(True)
        else:
            self.move_tool.SetToggle(False)

        if self.move_tool_state:
            if self.rotate_object is not None:
                self.rotate_object.stop_angle()
                self.rotate_object = None

            if self.canvas.selected is not None:
                self.move_object = self.canvas.selected
                self.move_object.start_move()
                self.canvas.Refresh(False)

        elif self.move_object is not None:
            self.move_object.stop_move()
            self.move_object = None

            self.canvas.Refresh(False)

        evt.Skip()

    def Show(self, flag=True):
        p = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self.housing = _housing.Housing(self, stl_path, p.copy())

        # for _ in range(9):
        #     p.x += _decimal(60)
        #
        #     if p.x >= 400:
        #         p.x = _decimal(-400.0)
        #         p.z += _decimal(60.0)
        #
        #     housing = Housing(self, p.copy())
        #     self.housings.append(housing)

        wx.Frame.Show(self, flag)


class App(wx.App):
    _frame = None

    def OnInit(self):
        self._frame = MainFrame()
        self._frame.Show()
        return True


if __name__ == '__main__':
    app = App()
    app.MainLoop()
