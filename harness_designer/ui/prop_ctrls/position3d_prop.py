# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import prop_base as _prop_base
from . import float_prop as _float_prop


class Position3DProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label, orientation='vertical')

        self._position = None
        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=0.0, max_value=9999.0, increment=0.01, units='mm')
        self.z_ctrl = _float_prop.FloatProperty(
            self, 'Z', min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')

        self._sizer.addWidget(self.x_ctrl)
        self._sizer.addWidget(self.y_ctrl)
        self._sizer.addWidget(self.z_ctrl)

        self.x_ctrl.property_changed.connect(self._on_x)
        self.y_ctrl.property_changed.connect(self._on_y)
        self.z_ctrl.property_changed.connect(self._on_z)

    def SetValue(self, position):
        self._position = position
        enabled = position is not None
        self.x_ctrl.SetValue(position.x if position else 0.0)
        self.y_ctrl.SetValue(position.y if position else 0.0)
        self.z_ctrl.SetValue(position.z if position else 0.0)
        self.x_ctrl.setEnabled(enabled)
        self.y_ctrl.setEnabled(enabled)
        self.z_ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        self._position.x = evt.GetValue()

    def _on_y(self, evt):
        self._position.y = evt.GetValue()

    def _on_z(self, evt):
        self._position.z = evt.GetValue()
