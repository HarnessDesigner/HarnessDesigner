from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import search_db as _search_db

if TYPE_CHECKING:
    from ...database.global_db import seal as _seal
    from ...database.project_db import pjt_housing as _pjt_housing


class AddHousingSealDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, housing: "_pjt_housing.PJTHousing",
                 table: "_seal.SealsTable"):

        self._table = table
        self._housing = housing
        _dialog_base.BaseDialog.__init__(self, parent, 'Object Search', label='Add Housing Seal')

        compat_seals = housing.part.compat_seals

        self.search = _search_db.SearchPanel(self.panel, table, *compat_seals)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.search, 0, wx.EXPAND)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.panel.SetSizer(vsizer)

    def GetValue(self):
        return self.search.GetValue()
