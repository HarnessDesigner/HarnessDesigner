# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from . import float_prop as _float_prop


class Position2DProperty(QtWidgets.QGroupBox):
    """
    Represent a position 2dproperty in
    :mod:`harness_designer.ui.prop_ctrls.position2d_prop`.
    """

    def __init__(self, parent, label: str):
        """Initialise the :class:`Position2DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        """

        super().__init__(label, parent)

        self._position = None
        self._label = label

        self.x_ctrl = _float_prop.FloatProperty(
            self, 'X', min_value=-9999.0, max_value=9999.0, increment=0.01)
        self.y_ctrl = _float_prop.FloatProperty(
            self, 'Y', min_value=-9999.0, max_value=9999.0, increment=0.01)

        sizer = QtWidgets.QVBoxLayout()
        sizer.addWidget(self.x_ctrl)
        sizer.addWidget(self.y_ctrl)
        self.setLayout(sizer)

        self.x_ctrl.propertyChanged.connect(self._on_x)
        self.y_ctrl.propertyChanged.connect(self._on_y)

    def SetValue(self, position):
        """
        Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: UNKNOWN
        """

        self._position = position
        enabled = position is not None
        self.x_ctrl.SetValue(position.x if position else 0.0)
        self.y_ctrl.SetValue(position.y if position else 0.0)
        self.x_ctrl.setEnabled(enabled)
        self.y_ctrl.setEnabled(enabled)

    def _on_x(self, evt):
        """
        Handle the x event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """

        self._position.x = evt.GetValue()

    def _on_y(self, evt):
        """
        Handle the y event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """

        self._position.y = evt.GetValue()

    def SetLabel(self, value: str):
        self._label = value
        self.setTitle(value)

    def GetLabel(self) -> str:
        return self._label
