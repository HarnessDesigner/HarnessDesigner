from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import search_db as _search_db

if TYPE_CHECKING:
    from ...database.global_db import splice as _splice


class AddSpliceDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, table: "_splice.SplicesTable"):

        self._table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Object Search', label='Add Splice')

        self.search = _search_db.SearchPanel(self.panel, table)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.search, 0, wx.EXPAND)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.panel.SetSizer(vsizer)

    def GetValue(self):
        return self.search.GetValue()

