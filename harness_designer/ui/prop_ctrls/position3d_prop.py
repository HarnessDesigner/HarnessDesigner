# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from . import float_prop as _float_prop


class Position3DProperty(QtWidgets.QGroupBox):
    """
    Represent a position 3dproperty in
    :mod:`harness_designer.ui.prop_ctrls.position3d_prop`.
    """

    def __init__(self, parent, label: str):
        """
        Initialise the :class:`Position3DProperty` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """

        super().__init__(label, parent)

        self._position = None
        self._label = label

        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=0.0, max_value=9999.0, increment=0.01, units='mm')
        self.z_ctrl = _float_prop.FloatProperty(
            self, 'Z', min_value=-9999.0, max_value=9999.0, increment=0.01, units='mm')

        sizer = QtWidgets.QVBoxLayout()
        sizer.addWidget(self.x_ctrl)
        sizer.addWidget(self.y_ctrl)
        sizer.addWidget(self.z_ctrl)

        self.setLayout(sizer)

        self.x_ctrl.propertyChanged.connect(self._on_x)
        self.y_ctrl.propertyChanged.connect(self._on_y)
        self.z_ctrl.propertyChanged.connect(self._on_z)

    def SetValue(self, position):
        """
        Execute the set value operation.

        :param position: Position value.
        :type position: UNKNOWN
        """

        if self._position is not None:
            self._position.unbind(self._on_position)

        self._position = position
        enabled = position is not None
        self.x_ctrl.SetValue(position.x if position else 0.0)
        self.y_ctrl.SetValue(position.y if position else 0.0)
        self.z_ctrl.SetValue(position.z if position else 0.0)
        self.x_ctrl.setEnabled(enabled)
        self.y_ctrl.setEnabled(enabled)
        self.z_ctrl.setEnabled(enabled)

        if position is not None:
            position.bind(self._on_position)

    def _on_position(self, position):
        x, y, z = position.as_float
        self.x_ctrl.SetValue(x)
        self.y_ctrl.SetValue(y)
        self.z_ctrl.SetValue(z)

    def _on_x(self, evt):
        """
        Handle the x event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._position.unbind(self._on_position)
        self._position.x = evt.GetValue()
        self._position.bind(self._on_position)

    def _on_y(self, evt):
        """
        Handle the y event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._position.unbind(self._on_position)
        self._position.y = evt.GetValue()
        self._position.bind(self._on_position)

    def _on_z(self, evt):
        """
        Handle the z event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._position.unbind(self._on_position)
        self._position.z = evt.GetValue()
        self._position.bind(self._on_position)

    def SetLabel(self, value: str):
        self._label = value
        self.setTitle(value)

    def GetLabel(self) -> str:
        return self._label

