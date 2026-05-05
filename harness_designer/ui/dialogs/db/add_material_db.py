
from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import text_ctrl as _text_ctrl

if TYPE_CHECKING:
    from ...database.global_db import material as _material


class AddMaterialDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, table: "_material.MaterialsTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database', label='Add Material')

        self.name = _text_ctrl.TextCtrl(self.panel, 'Name:', (-1, -1), style=wx.TE_READONLY)
        self.name.SetValue(name)

        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:', (-1, -1), style=wx.TE_MULTILINE)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)

    def GetValue(self):
        name = self.name.GetValue()
        description = self.description.GetValue().strip()
        return name, description
