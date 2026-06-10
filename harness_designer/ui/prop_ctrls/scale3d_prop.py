# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from . import float_prop as _float_prop


class Scale3DProperty(QtWidgets.QGroupBox):
    """
    Represent a position 3dproperty in
    :mod:`harness_designer.ui.prop_ctrls.scale3d_prop`.
    """

    def __init__(self, parent, label: str):
        """
        Initialise the :class:`Scale3DProperty` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """

        super().__init__(label, parent)

        self._scale = None
        self._label = label

        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=0.01, max_value=10.0, increment=0.01, units='x')
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=0.01, max_value=10.0, increment=0.01, units='x')
        self.z_ctrl = _float_prop.FloatProperty(
            self, 'Z', min_value=0.01, max_value=10.0, increment=0.01, units='x')

        sizer = QtWidgets.QVBoxLayout()

        sizer.addWidget(self.x_ctrl)
        sizer.addWidget(self.y_ctrl)
        sizer.addWidget(self.z_ctrl)

        self.setLayout(sizer)

        self.x_ctrl.propertyChanged.connect(self._on_x)
        self.y_ctrl.propertyChanged.connect(self._on_y)
        self.z_ctrl.propertyChanged.connect(self._on_z)

    def SetValue(self, scale):
        """
        Execute the set value operation.

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

        :param evt: Event object.
        :type evt: UNKNOWN
        """

        self._scale.x = evt.GetValue()

    def _on_y(self, evt):
        """
        Handle the y event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """

        self._scale.y = evt.GetValue()

    def _on_z(self, evt):
        """
        Handle the z event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """

        self._scale.z = evt.GetValue()

    def SetLabel(self, value: str):
        self._label = value
        self.setTitle(value)

    def GetLabel(self) -> str:
        return self._label
