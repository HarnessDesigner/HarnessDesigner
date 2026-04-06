
from typing import TYPE_CHECKING

import wx

from ...widgets import float_ctrl as _float_ctrl

if TYPE_CHECKING:
    from ....database.global_db.mixins import dimension as _dimension


class DimensionMixin:

    def __init__(self, panel, db_obj: "_dimension.DimensionMixin"):
        self._dimension_obj = db_obj

        length = round(db_obj.length, 2)
        height = round(db_obj.height, 2)
        width = round(db_obj.width, 2)

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Dimensions")
        sb = sz.GetStaticBox()

        self.length = _float_ctrl.FloatCtrl(sb, 'Length:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.width = _float_ctrl.FloatCtrl(sb, 'Width:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.height = _float_ctrl.FloatCtrl(sb, 'Height:', min_val=-9999.9, max_val=9999.9, inc=0.01)

        self.length.SetValue(length)
        self.width.SetValue(width)
        self.height.SetValue(height)

        self.length.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_length)
        self.width.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_width)
        self.height.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_height)

        sz.Add(self.length, 1, wx.EXPAND)
        sz.Add(self.width, 1, wx.EXPAND)
        sz.Add(self.height, 1, wx.EXPAND)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_length(self, evt):
        value = self.length.GetValue()
        self._dimension_obj.length = value
        evt.Skip()

    def _on_width(self, evt):
        value = self.width.GetValue()
        self._dimension_obj.width = value
        evt.Skip()

    def _on_height(self, evt):
        value = self.height.GetValue()
        self._dimension_obj.height = value
        evt.Skip()
