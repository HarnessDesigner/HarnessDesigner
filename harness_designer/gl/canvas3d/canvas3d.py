from typing import TYPE_CHECKING

import wx

from . import canvas as _canvas
from ...geometry import point as _point
from . import mouse_handler as _mouse_handler


if TYPE_CHECKING:
    from ... import ui as _ui

EVT_GL_OBJECT_SELECTED = _mouse_handler.EVT_GL_OBJECT_SELECTED
EVT_GL_OBJECT_UNSELECTED = _mouse_handler.EVT_GL_OBJECT_UNSELECTED
EVT_GL_OBJECT_ACTIVATED = _mouse_handler.EVT_GL_OBJECT_ACTIVATED
EVT_GL_OBJECT_RIGHT_CLICK = _mouse_handler.EVT_GL_OBJECT_RIGHT_CLICK
EVT_GL_OBJECT_RIGHT_DCLICK = _mouse_handler.EVT_GL_OBJECT_RIGHT_DCLICK
EVT_GL_OBJECT_MIDDLE_CLICK = _mouse_handler.EVT_GL_OBJECT_MIDDLE_CLICK
EVT_GL_OBJECT_MIDDLE_DCLICK = _mouse_handler.EVT_GL_OBJECT_MIDDLE_DCLICK
EVT_GL_OBJECT_AUX1_CLICK = _mouse_handler.EVT_GL_OBJECT_AUX1_CLICK
EVT_GL_OBJECT_AUX1_DCLICK = _mouse_handler.EVT_GL_OBJECT_AUX1_DCLICK
EVT_GL_OBJECT_AUX2_CLICK = _mouse_handler.EVT_GL_OBJECT_AUX2_CLICK
EVT_GL_OBJECT_AUX2_DCLICK = _mouse_handler.EVT_GL_OBJECT_AUX2_DCLICK
EVT_GL_OBJECT_DRAG = _mouse_handler.EVT_GL_OBJECT_DRAG
EVT_GL_LEFT_DOWN = _mouse_handler.EVT_GL_LEFT_DOWN
EVT_GL_LEFT_UP = _mouse_handler.EVT_GL_LEFT_UP
EVT_GL_LEFT_DCLICK = _mouse_handler.EVT_GL_LEFT_DCLICK
EVT_GL_RIGHT_DOWN = _mouse_handler.EVT_GL_RIGHT_DOWN
EVT_GL_RIGHT_UP = _mouse_handler.EVT_GL_RIGHT_UP
EVT_GL_RIGHT_DCLICK = _mouse_handler.EVT_GL_RIGHT_DCLICK
EVT_GL_MIDDLE_DOWN = _mouse_handler.EVT_GL_MIDDLE_DOWN
EVT_GL_MIDDLE_UP = _mouse_handler.EVT_GL_MIDDLE_UP
EVT_GL_MIDDLE_DCLICK = _mouse_handler.EVT_GL_MIDDLE_DCLICK
EVT_GL_AUX1_DOWN = _mouse_handler.EVT_GL_AUX1_DOWN
EVT_GL_AUX1_UP = _mouse_handler.EVT_GL_AUX1_UP
EVT_GL_AUX1_DCLICK = _mouse_handler.EVT_GL_AUX1_DCLICK
EVT_GL_AUX2_DOWN = _mouse_handler.EVT_GL_AUX2_DOWN
EVT_GL_AUX2_UP = _mouse_handler.EVT_GL_AUX2_UP
EVT_GL_AUX2_DCLICK = _mouse_handler.EVT_GL_AUX2_DCLICK

GLEvent = _mouse_handler.GLEvent
GLObjectEvent = _mouse_handler.GLObjectEvent


class Canvas3D(wx.Panel):

    def __init__(self, parent, config, size=wx.DefaultSize, axis_overlay=False):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self._ref_count = 0

        self._panel = wx.Panel(self, wx.ID_ANY, pos=(0, 0))

        self._canvas = _canvas.Canvas(self._panel, config, size=size, pos=(0, 0), axis_overlay=axis_overlay)

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)

    @property
    def context(self):
        return self._canvas.context

    @property
    def camera(self):
        return self._canvas.camera

    def _on_size(self, evt):
        w, h = evt.GetSize()
        self._panel.SetSize((w, h))
        cw, ch = self._canvas.GetSize()

        x = (w - cw) // 2
        y = (h - ch) // 2

        self._canvas.Move(x, y)

    def set_selected(self, obj):
        self._canvas.set_selected(obj)

    def set_mode(self, mode: int) -> None:
        self._canvas.set_mode(mode)

    def add_object(self, obj):
        self._canvas.add_object(obj)

    def remove_object(self, obj):
        self._canvas.remove_object(obj)

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

    def _on_erase_background(self, _):
        pass
