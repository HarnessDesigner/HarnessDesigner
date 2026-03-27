from typing import TYPE_CHECKING

import wx


if TYPE_CHECKING:
    from ... import ui as _ui


class ViewMenu(wx.Menu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        wx.Menu.__init__(self)