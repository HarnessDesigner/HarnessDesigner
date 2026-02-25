from typing import TYPE_CHECKING

import wx

from . import canvas as _canvas


if TYPE_CHECKING:
    from .. import ui as _ui


class Editor2D(wx.Panel):

    def __init__(self, parent, mainframe: "_ui.MainFrame"):

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.mainframe: "_ui.MainFrame" = mainframe
        self.canvas = _canvas.Canvas(self)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.canvas, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)
        self.SetSizer(vsizer)
