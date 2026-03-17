
from typing import TYPE_CHECKING

import wx
from ...widgets import float_ctrl as _float_ctrl

if TYPE_CHECKING:
    from ....database.global_db.mixins import dimension as _dimension


class ScaleMixin:
    db_obj: "_dimension.DimensionMixin" = None

    def __init__(self, panel, db_obj: "_dimension.DimensionMixin"):
        self.db_obj = db_obj
        
        self.scale3d = db_obj.scale

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Scale 3D")
        sb = sz.GetStaticBox()
        
        self.scale3d_x = _float_ctrl.FloatCtrl(sb, 'X:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.scale3d_y = _float_ctrl.FloatCtrl(sb, 'Y:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.scale3d_z = _float_ctrl.FloatCtrl(sb, 'Z:', min_val=-9999.9, max_val=9999.9, inc=0.01)

        x, y, z = [round(item, 2) for item in self.scale3d.as_float]

        self.scale3d_x.SetValue(x)
        self.scale3d_y.SetValue(y)
        self.scale3d_z.SetValue(z)

        sz.Add(self.scale3d_x, 1, wx.EXPAND)
        sz.Add(self.scale3d_y, 1, wx.EXPAND)
        sz.Add(self.scale3d_z, 1, wx.EXPAND)

        self.scale3d_x.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_scale3d_x)
        self.scale3d_y.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_scale3d_y)
        self.scale3d_z.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_scale3d_z)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_scale3d_x(self, evt):
        value = self.scale3d_x.GetValue()
        self.scale3d.x = value
        evt.Skip()

    def _on_scale3d_y(self, evt):
        value = self.scale3d_y.GetValue()
        self.scale3d.y = value
        evt.Skip()

    def _on_scale3d_z(self, evt):
        value = self.scale3d_y.GetValue()
        self.scale3d.y = value
        evt.Skip()
