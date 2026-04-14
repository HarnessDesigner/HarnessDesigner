import wx

from . import prop_base as _prop_base
from . import float_prop as _float_prop
from .. import events as _events


class Position2DProperty(_prop_base.Property):

    def __init__(self, parent, label, position):
        _prop_base.Property.__init__(self, parent, label, orientation=wx.VERTICAL)

        self._position = position
        self.x_ctrl = _float_prop.FloatProperty(self, 'X', position.x, min_value=-9999.0, max_value=9999.0, increment=0.01)
        self.y_ctrl = _float_prop.FloatProperty(self, 'Y', position.y, min_value=-9999.0, max_value=9999.0, increment=0.01)

        self.x_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_x)
        self.y_ctrl.Bind(_events.EVT_PROPERTY_CHANGED, self._on_y)

    def update(self):
        self.x_ctrl.SetValue(self._position.x)
        self.y_ctrl.SetValue(self._position.y)

    def _on_x(self, evt):
        self._position.x = evt.GetValue()

    def _on_y(self, evt):
        self._position.y = evt.GetValue()
