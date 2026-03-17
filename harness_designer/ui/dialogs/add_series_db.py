from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import text_ctrl as _text_ctrl

if TYPE_CHECKING:
    from ...database.global_db import series as _series


class AddSeriesDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, mfg_name, table: "_series.SeriesTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database', label='Add Series')

        self.name = _text_ctrl.TextCtrl(self.panel, 'Name:', (-1, -1), style=wx.TE_READONLY)
        self.name.SetValue(name)

        self.mfg = _text_ctrl.TextCtrl(self.panel, 'Manufacturer:', (-1, -1), style=wx.TE_READONLY)
        self.mfg.SetValue(mfg_name)

        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:', (-1, -1), style=wx.TE_MULTILINE)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.name, 1, wx.EXPAND)
        vsizer.Add(self.mfg, 1, wx.EXPAND)
        vsizer.Add(self.description, 1, wx.EXPAND)

        self.panel.SetSizer(vsizer)

    def GetValue(self):
        name = self.name.GetValue()
        mfg = self.mfg.GetValue()
        description = self.description.GetValue().strip()
        return name, mfg, description
