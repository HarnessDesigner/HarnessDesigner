# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import prop_base as _prop_base
from . import float_prop as _float_prop


class Scale3DProperty(_prop_base.Property):
    """
    Represent a position 3dproperty in :mod:`harness_designer.ui.prop_ctrls.scale3d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """
        Initialise the :class:`Scale3DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label, orientation='vertical')

        self._scale = None
        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=0.01, max_value=10.0, increment=0.01, units='x')
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=0.01, max_value=10.0, increment=0.01, units='x')
        self.z_ctrl = _float_prop.FloatProperty(
            self, 'Z', min_value=0.01, max_value=10.0, increment=0.01, units='x')

        self._sizer.addWidget(self.x_ctrl)
        self._sizer.addWidget(self.y_ctrl)
        self._sizer.addWidget(self.z_ctrl)

        self.x_ctrl.property_changed.connect(self._on_x)
        self.y_ctrl.property_changed.connect(self._on_y)
        self.z_ctrl.property_changed.connect(self._on_z)

    def SetValue(self, scale):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Position value.
        :type scale: UNKNOWN
        """
        self._scale = scale
        enabled = scale is not None
        self.x_ctrl.SetValue(scale.x if scale else 1.0)
        self.y_ctrl.SetValue(scale.y if scale else 1.0)
        self.z_ctrl.SetValue(scale.z if scale else 1.0)
        self.x_ctrl.setEnabled(enabled)
        self.y_ctrl.setEnabled(enabled)
        self.z_ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        """
        Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._scale.x = evt.GetValue()

    def _on_y(self, evt):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._scale.y = evt.GetValue()

    def _on_z(self, evt):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._scale.z = evt.GetValue()
