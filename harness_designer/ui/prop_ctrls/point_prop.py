# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from . import float_prop as _float_prop
from ... import check_types as _check_types


class PointProperty(QtWidgets.QGroupBox):

    # Range and step applied to every axis control. Subclasses override
    # these instead of touching __init__ (see ScaleProperty).
    MIN_VALUE: float = -9999.0
    MAX_VALUE: float = 9999.0
    INCREMENT: float = 0.01

    @_check_types.do
    def __init__(self, parent, label: str, units: str, axes: str = 'xyz'):
        """
        Initialise the :class:`PointProperty` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN

        :param label: Value for ``label``.
        :type label: `str`

        :param axes: Value for ``axes``.
        :type axes: `str`
        """

        super().__init__(label, parent)

        self._point = None
        self._label = label

        sizer = QtWidgets.QVBoxLayout()

        axes = axes.lower()

        if 'x' in axes:
            self.x_ctrl = _float_prop.FloatProperty(
                self, 'X', min_value=self.MIN_VALUE, max_value=self.MAX_VALUE,
                increment=self.INCREMENT, units=units)

            sizer.addWidget(self.x_ctrl)
            self.x_ctrl.propertyChanged.connect(self._on_x)
        else:
            self.x_ctrl = None

        if 'y' in axes:
            self.y_ctrl = _float_prop.FloatProperty(
                self, 'Y', min_value=self.MIN_VALUE, max_value=self.MAX_VALUE,
                increment=self.INCREMENT, units=units)

            sizer.addWidget(self.y_ctrl)
            self.y_ctrl.propertyChanged.connect(self._on_y)
        else:
            self.y_ctrl = None

        if 'z' in axes:
            self.z_ctrl = _float_prop.FloatProperty(
                self, 'Z', min_value=self.MIN_VALUE, max_value=self.MAX_VALUE,
                increment=self.INCREMENT, units=units)

            sizer.addWidget(self.z_ctrl)
            self.z_ctrl.propertyChanged.connect(self._on_z)
        else:
            self.z_ctrl = None

        self.setLayout(sizer)

    @_check_types.do
    def SetValue(self, point):
        """
        Execute the set value operation.

        :param point: Position value.
        :type point: UNKNOWN
        """

        if self._point is not None:
            self._point.unbind(self._on_point)

        self._point = point
        enabled = point is not None

        if self.x_ctrl is not None:
            self.x_ctrl.SetValue(point.x if point else 0.0)
            self.x_ctrl.setEnabled(enabled)

        if self.y_ctrl is not None:
            self.y_ctrl.SetValue(point.y if point else 0.0)
            self.y_ctrl.setEnabled(enabled)

        if self.z_ctrl is not None:
            self.z_ctrl.SetValue(point.z if point else 0.0)
            self.z_ctrl.setEnabled(enabled)

        if point is not None:
            point.bind(self._on_point)

    @_check_types.do
    def _on_point(self, point):
        x, y, z = point.as_float

        if self.x_ctrl is not None:
            self.x_ctrl.SetValue(x)

        if self.y_ctrl is not None:
            self.y_ctrl.SetValue(y)

        if self.z_ctrl is not None:
            self.z_ctrl.SetValue(z)

    @_check_types.do
    def _on_x(self, evt):
        """
        Handle the x event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._point.unbind(self._on_point)
        self._point.x = evt.GetValue()
        self._point.bind(self._on_point)

    @_check_types.do
    def _on_y(self, evt):
        """
        Handle the y event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._point.unbind(self._on_point)
        self._point.y = evt.GetValue()
        self._point.bind(self._on_point)

    @_check_types.do
    def _on_z(self, evt):
        """
        Handle the z event.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._point.unbind(self._on_point)
        self._point.z = evt.GetValue()
        self._point.bind(self._on_point)

    @_check_types.do
    def SetLabel(self, value: str):
        self._label = value
        self.setTitle(value)

    @_check_types.do
    def GetLabel(self) -> str:
        return self._label

