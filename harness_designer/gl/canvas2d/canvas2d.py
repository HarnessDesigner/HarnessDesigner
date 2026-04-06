from typing import TYPE_CHECKING

import wx

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas2D(wx.Panel):

    def __init__(self, parent: "_ui.MainFrame", config: "_config.Config.editor2d", size=wx.DefaultSize):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self._ref_count = 0

        self._panel = wx.Panel(self, wx.ID_ANY, pos=(0, 0))

        self._canvas = _canvas.Canvas(self._panel, config, size=size, pos=(0, 0))

        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.config = config

        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_mouse_capture_lost)

    def on_mouse_capture_lost(self, evt: wx.MouseCaptureLostEvent):
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()

        evt.Skip()

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

    def _on_erase_background(self, _):
        pass
