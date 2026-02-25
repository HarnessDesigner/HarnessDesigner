from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import search_db as _search_db

if TYPE_CHECKING:
    from ...database.global_db import tpa_lock as _tpa_lock
    from ...database.project_db import pjt_housing as _pjt_housing


class AddTPALockDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, housing: "_pjt_housing.PJTHousing",
                 table: "_tpa_lock.TPALocksTable"):

        self._table = table
        self._housing = housing
        _dialog_base.BaseDialog.__init__(self, parent, 'Object Search', label='Add TPA Lock')

        compat_tpas = housing.part.compat_tpas

        self.search = _search_db.SearchPanel(self.panel, table, *compat_tpas)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.search, 0, wx.EXPAND)
        vsizer.Add(hsizer, 0, wx.EXPAND)
        self.panel.SetSizer(vsizer)

    def GetValue(self):
        return self.search.GetValue()
