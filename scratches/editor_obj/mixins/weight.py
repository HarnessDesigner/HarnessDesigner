from typing import TYPE_CHECKING

import wx

from ...widgets import float_ctrl as _float_ctrl

if TYPE_CHECKING:
    from ....database.global_db.mixins import weight as _weight


class WeightMixin:

    def __init__(self, panel, db_obj: "_weight.WeightMixin"):
        self._weight_obj = db_obj

        weight = round(db_obj.weight, 2)

        self.weight = _float_ctrl.FloatCtrl(panel, 'Weight:', min_val=-9999.9, max_val=9999.9, inc=0.01)

        self.weight.SetValue(weight)

        self.weight.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_weight)

        vsizer = panel.GetSizer()
        vsizer.Add(self.weight, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

    def _on_weight(self, evt):
        value = self.weight.GetValue()
        self._weight_obj.weight = value
        evt.Skip()
