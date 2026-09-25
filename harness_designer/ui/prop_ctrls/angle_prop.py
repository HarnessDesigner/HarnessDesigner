# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets


from . import float_prop as _float_prop
from ... import check_types as _check_types


class AngleProperty(QtWidgets.QGroupBox):
    """
    Represent an angle 3dproperty in :mod:`harness_designer.ui.prop_ctrls.angle3d_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent, label: str, axes: str = 'xyz'):
        """Initialise the :class:`Angle3DProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN

        :param label: Value for ``label``.
        :type label: str

        :param axes: Value for ``axes``.
        :type axes: str
        """

        super().__init__(label, parent)

        self._angle = None
        self._label = label

        sizer = QtWidgets.QVBoxLayout()

        axes = axes.lower()

        if 'x' in axes:
            self.x_ctrl = _float_prop.FloatProperty(
                self, 'X', min_value=-180.0, max_value=180.0, increment=0.01, units='°')

            sizer.addWidget(self.x_ctrl)
            self.x_ctrl.propertyChanged.connect(self._on_x)
        else:
            self.x_ctrl = None

        if 'y' in axes:
            self.y_ctrl = _float_prop.FloatProperty(
                self, 'Y', min_value=-180.0, max_value=180.0, increment=0.01, units='°')

            sizer.addWidget(self.y_ctrl)
            self.y_ctrl.propertyChanged.connect(self._on_y)
        else:
            self.y_ctrl = None

        if 'z' in axes:
            self.z_ctrl = _float_prop.FloatProperty(
                self, 'Z', min_value=-180.0, max_value=180.0, increment=0.01, units='°')

            sizer.addWidget(self.z_ctrl)
            self.z_ctrl.propertyChanged.connect(self._on_z)

        else:
            self.z_ctrl = None

        self.setLayout(sizer)

    @_check_types.do
    def _on_angle(self, angle):
        x, y, z = angle.as_euler_float
        if self.x_ctrl is not None:
            self.x_ctrl.SetValue(x)

        if self.y_ctrl is not None:
            self.y_ctrl.SetValue(y)

        if self.z_ctrl is not  None:
            self.z_ctrl.SetValue(z)

    @_check_types.do
    def SetValue(self, angle):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: UNKNOWN
        """

        if self._angle is not None:
            self._angle.unbind(self._on_angle)

        self._angle = angle
        enabled = angle is not None
        for ctrl, val in zip(
            (self.x_ctrl, self.y_ctrl, self.z_ctrl),
            (angle.x, angle.y, angle.z) if angle else (0.0, 0.0, 0.0)
        ):
            if ctrl is not None:
                ctrl.SetValue(val)
                ctrl.setEnabled(enabled)

        if angle is not None:
            angle.bind(self._on_angle)

    @_check_types.do
    def _on_x(self, evt):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.unbind(self._on_angle)
        self._angle.x = evt.GetValue()
        self._angle.bind(self._on_angle)

    @_check_types.do
    def _on_y(self, evt):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.unbind(self._on_angle)
        self._angle.y = evt.GetValue()
        self._angle.bind(self._on_angle)

    @_check_types.do
    def _on_z(self, evt):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self._angle.unbind(self._on_angle)
        self._angle.z = evt.GetValue()
        self._angle.bind(self._on_angle)

    @_check_types.do
    def SetLabel(self, value: str):
        self._label = value
        self.setTitle(value)

    @_check_types.do
    def GetLabel(self) -> str:
        return self._label
