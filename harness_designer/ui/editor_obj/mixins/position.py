from typing import TYPE_CHECKING

import wx
from ...widgets import float_ctrl as _float_ctrl
from ...widgets import int_ctrl as _int_ctrl

if TYPE_CHECKING:
    from ....database.project_db.mixins import position3d as _position3d
    from ....database.project_db.mixins import position2d as _position2d


class Position3DMixin:

    def __init__(self, panel, db_obj: "_position3d.Position3DMixin"):
        self._position3d_obj = db_obj

        self.position3d = db_obj.position3d

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Position 3D")
        sb = sz.GetStaticBox()

        self.position3d_x = _float_ctrl.FloatCtrl(sb, 'X:', min_val=-9999.9, max_val=9999.9, inc=0.001)
        self.position3d_y = _float_ctrl.FloatCtrl(sb, 'Y:', min_val=-9999.9, max_val=9999.9, inc=0.001)
        self.position3d_z = _float_ctrl.FloatCtrl(sb, 'Z:', min_val=-9999.9, max_val=9999.9, inc=0.001)

        x, y, z = [round(item, 3) for item in self.position3d.as_float]

        self.position3d_x.SetValue(x)
        self.position3d_y.SetValue(y)
        self.position3d_z.SetValue(z)

        sz.Add(self.position3d_x, 1, wx.EXPAND)
        sz.Add(self.position3d_y, 1, wx.EXPAND)
        sz.Add(self.position3d_z, 1, wx.EXPAND)

        self.position3d_x.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_position3d_x)
        self.position3d_y.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_position3d_y)
        self.position3d_z.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_position3d_z)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_position3d_x(self, evt):
        value = self.position3d_x.GetValue()
        self.position3d.x = value
        evt.Skip()

    def _on_position3d_y(self, evt):
        value = self.position3d_y.GetValue()
        self.position3d.y = value
        evt.Skip()

    def _on_position3d_z(self, evt):
        value = self.position3d_y.GetValue()
        self.position3d.y = value
        evt.Skip()


class Position2DMixin:

    def __init__(self, panel, db_obj: "_position2d.Position2DMixin"):
        self.db_obj = db_obj

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Position 2D")
        sb = sz.GetStaticBox()

        self.position2d = db_obj.position2d

        self.position2d_x = _int_ctrl.IntCtrl(sb, 'X:', min_val=-99999, max_val=99999)
        self.position2d_y = _int_ctrl.IntCtrl(sb, 'Y:', min_val=-99999, max_val=99999)

        x, y = [int(item) for item in self.position2d.as_float[:-1]]

        self.position2d_x.SetValue(x)
        self.position2d_y.SetValue(y)

        sz.Add(self.position2d_x, 1, wx.EXPAND)
        sz.Add(self.position2d_y, 1, wx.EXPAND)

        self.position2d_x.Bind(wx.EVT_SPINCTRL, self._on_position2d_x)
        self.position2d_y.Bind(wx.EVT_SPINCTRL, self._on_position2d_y)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_position2d_x(self, evt):
        value = self.position2d_x.GetValue()
        self.position2d.x = value
        evt.Skip()

    def _on_position2d_y(self, evt):
        value = self.position2d_y.GetValue()
        self.position2d.y = value
        evt.Skip()
