import wx

from . import prop_base as _prop_base
from . import float_prop as _float_prop
from .. import events as _events


class Position3DProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label, orientation=wx.VERTICAL)

        self._position = None
        self.x_ctrl = _float_prop.FloatProperty(self, 'X', 0.0, min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')
        self.y_ctrl = _float_prop.FloatProperty(self, 'Y', 0.0, min_value=0.0, max_value=9999.0, increment=0.01, units='mm')
        self.z_ctrl = _float_prop.FloatProperty(self, 'Z', 0.0, min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')

        self.x_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_x)
        self.y_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_y)
        self.z_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_z)

    def SetValue(self, position):
        self._position = position
        if position is None:
            self.x_ctrl.SetValue(0.0)
            self.y_ctrl.SetValue(0.0)
            self.z_ctrl.SetValue(0.0)

            self.x_ctrl.Enable(False)
            self.y_ctrl.Enable(False)
            self.z_ctrl.Enable(False)
        else:
            self.x_ctrl.SetValue(position.x)
            self.y_ctrl.SetValue(position.y)
            self.z_ctrl.SetValue(position.z)

            self.x_ctrl.Enable(True)
            self.y_ctrl.Enable(True)
            self.z_ctrl.Enable(True)

    def _on_x(self, evt):
        self._position.x = evt.GetValue()

    def _on_y(self, evt):
        self._position.y = evt.GetValue()

    def _on_z(self, evt):
        self._position.z = evt.GetValue()
