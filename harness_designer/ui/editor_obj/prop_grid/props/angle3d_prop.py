import wx

from . import prop_base as _prop_base
from . import float_prop as _float_prop
from .. import events as _events


class Angle3DProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label, orientation=wx.VERTICAL)

        self._angle = None
        self.x_ctrl = _float_prop.FloatProperty(self, 'X', 0.0, min_value=-180.0, max_value=180.0, increment=0.01, units='°')
        self.y_ctrl = _float_prop.FloatProperty(self, 'Y', 0.0, min_value=-180.0, max_value=180.0, increment=0.01, units='°')
        self.z_ctrl = _float_prop.FloatProperty(self, 'Z', 0.0, min_value=-180.0, max_value=180.0, increment=0.01, units='°')

        self.x_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_x)
        self.y_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_y)
        self.z_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_z)

    def SetValue(self, angle):
        self._angle = angle

        self.x_ctrl.SetValue(angle.x)
        self.y_ctrl.SetValue(angle.y)
        self.z_ctrl.SetValue(angle.z)

    def _on_x(self, evt):
        self._angle.x = evt.GetValue()

    def _on_y(self, evt):
        self._angle.y = evt.GetValue()

    def _on_z(self, evt):
        self._angle.z = evt.GetValue()
