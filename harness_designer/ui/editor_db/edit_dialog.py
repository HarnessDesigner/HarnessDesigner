from typing import TYPE_CHECKING

import wx
from ..dialogs import dialog_base as _dialog_base

if TYPE_CHECKING:
    from ... import ui as _ui


class EditDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame", title, db_obj):
        super().__init__(parent, title=title, button_ids=wx.OK)

        control = db_obj.table.control
        control.Reparent(self.panel)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.Add(control, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)

        control.set_obj(db_obj)
        self.control = control
        self.db_obj = db_obj
        self.mainframe = parent

    def Destroy(self):
        self.control.set_obj(None)
        self.control.Reparent(self.mainframe)
        self.control.Show(False)

        super().Destroy()
