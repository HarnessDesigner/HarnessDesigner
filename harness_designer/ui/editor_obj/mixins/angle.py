
from typing import TYPE_CHECKING

import wx
from ...widgets import float_ctrl as _float_ctrl

if TYPE_CHECKING:
    from ....database.project_db.mixins import angle3d as _angle3d
    from ....database.project_db.mixins import angle2d as _angle2d


class Angle3DMixin:

    def __init__(self, panel, db_obj: "_angle3d.Angle3DMixin"):
        self.angle3d_obj = db_obj
        
        self.angle3d = db_obj.angle3d

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Angle 3D")
        sb = sz.GetStaticBox()
        
        self.angle3d_x = _float_ctrl.FloatCtrl(sb, 'X:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.angle3d_y = _float_ctrl.FloatCtrl(sb, 'Y:', min_val=-9999.9, max_val=9999.9, inc=0.01)
        self.angle3d_z = _float_ctrl.FloatCtrl(sb, 'Z:', min_val=-9999.9, max_val=9999.9, inc=0.01)

        x, y, z = [round(item, 2) for item in self.angle3d.as_euler_float]

        self.angle3d_x.SetValue(x)
        self.angle3d_y.SetValue(y)
        self.angle3d_z.SetValue(z)

        sz.Add(self.angle3d_x, 1, wx.EXPAND)
        sz.Add(self.angle3d_y, 1, wx.EXPAND)
        sz.Add(self.angle3d_z, 1, wx.EXPAND)

        self.angle3d_x.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_angle3d_x)
        self.angle3d_y.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_angle3d_y)
        self.angle3d_z.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_angle3d_z)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_angle3d_x(self, evt):
        value = self.angle3d_x.GetValue()
        self.angle3d.x = value
        evt.Skip()

    def _on_angle3d_y(self, evt):
        value = self.angle3d_y.GetValue()
        self.angle3d.y = value
        evt.Skip()

    def _on_angle3d_z(self, evt):
        value = self.angle3d_y.GetValue()
        self.angle3d.y = value
        evt.Skip()


class Angle2DMixin:

    def __init__(self, panel, db_obj: "_angle2d.Angle2DMixin"):
        self._angle2d_obj = db_obj

        sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Angle 2D")
        sb = sz.GetStaticBox()
        
        self.angle2d = db_obj.angle2d

        self.angle2d_z = _float_ctrl.FloatCtrl(sb, 'Angle:', min_val=-9999.9, max_val=9999.9, inc=0.01)

        z = round(self.angle2d.as_euler_float[-1], 2)

        self.angle2d_z.SetValue(z)

        sz.Add(self.angle2d_z, 1, wx.EXPAND)

        self.angle2d_z.Bind(wx.EVT_SPINCTRL, self._on_angle2d_z)

        vsizer = panel.GetSizer()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(sb, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND)

    def _on_angle2d_z(self, evt):
        value = self.angle2d_z.GetValue()
        self.angle2d.z = value
        evt.Skip()
