# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import prop_base as _prop_base
from . import float_prop as _float_prop


class Angle3DProperty(_prop_base.Property):

    def __init__(self, parent, label):
        _prop_base.Property.__init__(self, parent, label, orientation='vertical')

        self._angle = None
        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=-180.0, max_value=180.0, increment=0.01, units='°')
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=-180.0, max_value=180.0, increment=0.01, units='°')
        self.z_ctrl = _float_prop.FloatProperty(
            self, 'Z', min_value=-180.0, max_value=180.0, increment=0.01, units='°')

        self._sizer.addWidget(self.x_ctrl)
        self._sizer.addWidget(self.y_ctrl)
        self._sizer.addWidget(self.z_ctrl)

        self.x_ctrl.property_changed.connect(self._on_x)
        self.y_ctrl.property_changed.connect(self._on_y)
        self.z_ctrl.property_changed.connect(self._on_z)

    def SetValue(self, angle):
        self._angle = angle
        enabled = angle is not None
        for ctrl, val in zip(
            (self.x_ctrl, self.y_ctrl, self.z_ctrl),
            (angle.x, angle.y, angle.z) if angle else (0.0, 0.0, 0.0)
        ):
            ctrl.SetValue(val)
            ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        self._angle.x = evt.GetValue()

    def _on_y(self, evt):
        self._angle.y = evt.GetValue()

    def _on_z(self, evt):
        self._angle.z = evt.GetValue()
