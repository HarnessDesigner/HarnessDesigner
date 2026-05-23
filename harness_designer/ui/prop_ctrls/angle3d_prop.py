# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import prop_base as _prop_base
from . import float_prop as _float_prop


class Angle3DProperty(_prop_base.Property):
    """Represent an angle 3dproperty in :mod:`harness_designer.ui.prop_ctrls.angle3d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`Angle3DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
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
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: UNKNOWN
        """
        self._angle = angle
        enabled = angle is not None
        for ctrl, val in zip(
            (self.x_ctrl, self.y_ctrl, self.z_ctrl),
            (angle.x, angle.y, angle.z) if angle else (0.0, 0.0, 0.0)
        ):
            ctrl.SetValue(val)
            ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.x = evt.GetValue()

    def _on_y(self, evt):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.y = evt.GetValue()

    def _on_z(self, evt):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.z = evt.GetValue()
