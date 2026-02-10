from typing import TYPE_CHECKING

import wx

from . import canvas as _canvas
from ...geometry import point as _point

if TYPE_CHECKING:
    from ... import ui as _ui


class Editor3D(wx.Panel):

    def __init__(self, parent, mainframe: "_ui.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = mainframe
        view_size = _canvas.Canvas.GetViewSize()
        self._ref_count = 0

        self._panel = wx.Panel(self, wx.ID_ANY, pos=(0, 0))
        self._canvas = _canvas.Canvas(self._panel, size=view_size.as_int[:-1], pos=(0, 0))

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def _on_size(self, evt):
        w, h = evt.GetSize()
        self._panel.SetSize((w, h))
        cw, ch = self._canvas.GetSize()

        x = (w - cw) // 2
        y = (h - ch) // 2

        self._canvas.Move(x, y)

    @staticmethod
    def GetViewSize() -> _point.Point:
        return _canvas.Canvas.GetViewSize()

    def AddObject(self, obj):
        self._canvas.AddObject(obj)

    def RemoveObject(self, obj):
        self._canvas.RemoveObject(obj)

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        if self._ref_count:
            return

        self._canvas.Refresh(*args, **kwargs)

    def Truck(self, delta) -> None:
        self._canvas.TruckPedestal(delta, 0.0)

    def Pedestal(self, delta) -> None:
        self._canvas.TruckPedestal(0.0, delta)

    def TruckPedestal(self, truck_delta, pedestal_delta) -> None:
        self._canvas.TruckPedestal(truck_delta, pedestal_delta)

    def Zoom(self, delta):
        self._canvas.Zoom(delta, None)

    def RotateAbout(self, delta_x, delta_y) -> None:
        self._canvas.Rotate(delta_x, delta_y)

    def Dolly(self, delta):
        self._canvas.Walk(delta, 0.0)

    def Walk(self, delta_z, delta_x) -> None:
        self._canvas.Walk(delta_z, delta_x)

    def Pan(self, delta):
        self._canvas.PanTilt(delta, 0.0)

    def Tilt(self, delta) -> None:
        self._canvas.PanTilt(0.0, delta)

    def PanTilt(self, pan_delta, tilt_delta):
        self._canvas.PanTilt(pan_delta, tilt_delta)

    # def _on_size(self, evt):
    #     w, h = evt.GetSize()
    #     view_size = _canvas.Canvas.get_view_size()
    #     size = _point.Point(w, h)
    #     pos = (size - view_size) / 2.0
    #
    #     self._canvas.Move(pos.as_int[:-1])
    #
    #     evt.Skip()

    def _on_erase_background(self, _):
        pass
