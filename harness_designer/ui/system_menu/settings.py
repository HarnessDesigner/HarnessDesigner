from typing import TYPE_CHECKING

import wx

from ..dialogs import debug_settings as _debug_settings

if TYPE_CHECKING:
    from ... import ui as _ui


class SettingsMenu(wx.Menu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        wx.Menu.__init__(self)

        item = self.Append(wx.ID_ANY, 'Debug Settings')
        mainframe.Bind(wx.EVT_MENU, self.on_debug_settings, id=item.GetId())

    def on_debug_settings(self, evt):
        dlg = _debug_settings.DebugSettingsDialog(self.mainframe)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.SetValues()
            self.mainframe.Refresh(False)

        dlg.Destroy()

        evt.Skip()


