
from typing import TYPE_CHECKING

import wx
from ...widgets import checkbox_ctrl as _checkbox_ctrl

if TYPE_CHECKING:
    from ....database.project_db.mixins import visible2d as _visible2d
    from ....database.project_db.mixins import visible3d as _visible3d


class Visible3DMixin:

    def __init__(self, panel, db_obj: "_visible3d.Visible3DMixin"):
        self._visible3d_obj = db_obj

        self.visible3d = _checkbox_ctrl.CheckboxCtrl(panel, 'Visible 3D:')
        self.visible3d.SetValue(db_obj.is_visible3d)
        v_sizer = panel.GetSizer()
        v_sizer.Add(self.visible3d, 1, wx.EXPAND)

        self.visible3d.Bind(wx.EVT_CHECKBOX, self._on_visible3d)

    def _on_visible3d(self, evt):
        value = self.visible3d.GetValue()
        self._visible3d_obj.is_visible3d = value
        evt.Skip()


class Visible2DMixin:

    def __init__(self, panel, db_obj: "_visible2d.Visible2DMixin"):
        self._visible2d_obj = db_obj

        self.visible2d = _checkbox_ctrl.CheckboxCtrl(panel, 'Visible 2D:')
        self.visible2d.SetValue(db_obj.is_visible2d)
        v_sizer = panel.GetSizer()
        v_sizer.Add(self.visible2d, 1, wx.EXPAND)

        self.visible2d.Bind(wx.EVT_CHECKBOX, self._on_visible2d)

    def _on_visible2d(self, evt):
        value = self.visible2d.GetValue()
        self._visible2d_obj.is_visible2d = value
        evt.Skip()
