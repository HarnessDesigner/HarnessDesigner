# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets

from . import float_ctrl as _float_ctrl
from ... import color as _color
from ...geometry import angle as _angle
from ...geometry import point as _point


class TripleFloatCtrl(QtWidgets.QWidget):
    """Represent a triple float ctrl in :mod:`harness_designer.ui.dialogs.housing_editor.triple_float_ctrl`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, position_or_angle: _point.Point | _angle.Angle | None,
                 color: _color.Color | None = None, register_events: bool = True, label=None):
        """Initialise the :class:`TripleFloatCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param position_or_angle: Value for ``position_or_angle``.
        :type position_or_angle: _point.Point | _angle.Angle
        :param color: Value for ``color``.
        :type color: _color.Color | None
        :param register_events: Value for ``register_events``.
        :type register_events: bool
        :param label: set a label to create a boxed group
        :type label: None | str
        """

        super().__init__(parent)

        if isinstance(position_or_angle, _point.Point):
            min_val = -250
            max_val = 250
        else:
            min_val = -180
            max_val = 180

        self.setMaximumHeight(250)

        if label is None:
            group = self
        else:
            group = QtWidgets.QGroupBox(label, self)
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(group)
            self.setLayout(layout)

        sizer = QtWidgets.QVBoxLayout()

        if color is None:
            sizer.addSpacing(5)
        else:
            color_ctrl = QtWidgets.QWidget(group)
            color_ctrl.setFixedHeight(5)
            color_ctrl.setStyleSheet(
                f"background-color: {color.to_qcolor().name()};")

            sizer.addWidget(color_ctrl)

        self.x = _float_ctrl.FloatCtrl(
            group, 'X:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        self.y = _float_ctrl.FloatCtrl(
            group, 'Y:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        self.z = _float_ctrl.FloatCtrl(
            group, 'Z:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        sizer.addSpacing(2)
        sizer.addWidget(self.x)
        sizer.addSpacing(2)
        sizer.addWidget(self.y)
        sizer.addSpacing(2)
        sizer.addWidget(self.z)
        sizer.addSpacing(2)
        group.setLayout(sizer)

        self.position_or_angle = position_or_angle

        if position_or_angle is None:
            self.x.Enable(False)
            self.y.Enable(False)
            self.z.Enable(False)
        else:
            position_or_angle.bind(self.on_position_or_angle)

            self.x.SetValue(position_or_angle.x)
            self.y.SetValue(position_or_angle.y)
            self.z.SetValue(position_or_angle.z)

        if register_events:
            self.x.value_changed.connect(self.on_x)
            self.y.value_changed.connect(self.on_y)
            self.z.value_changed.connect(self.on_z)

    def set_obj(self, position_or_angle):

        if self.position_or_angle is not None:
            self.position_or_angle.unbind(self.on_position_or_angle)

        self.position_or_angle = position_or_angle

        if isinstance(position_or_angle, _point.Point):
            min_val = -250
            max_val = 250
        else:
            min_val = -180
            max_val = 180

        self.x.setRange(min_val, max_val)
        self.y.setRange(min_val, max_val)
        self.z.setRange(min_val, max_val)

        if position_or_angle is None:
            self.x.Enable(False)
            self.y.Enable(False)
            self.z.Enable(False)
        else:
            position_or_angle.bind(self.on_position_or_angle)

            self.x.Enable(True)
            self.y.Enable(True)
            self.z.Enable(True)

            self.x.blockSignals(True)
            self.x.SetValue(position_or_angle.x)
            self.x.blockSignals(False)

            self.y.blockSignals(True)
            self.y.SetValue(position_or_angle.y)
            self.y.blockSignals(False)

            self.z.blockSignals(True)
            self.z.SetValue(position_or_angle.z)
            self.z.blockSignals(False)

    def on_position_or_angle(self, p):
        """Handle the position or angle event.

        UNKNOWN details are inferred from the callable name and signature.

        :param p: Value for ``p``.
        :type p: UNKNOWN
        """
        self.x.SetValue(p.x)
        self.y.SetValue(p.y)
        self.z.SetValue(p.z)

        self.x.update()
        self.y.update()
        self.z.update()

    def on_x(self, value):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.x = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def on_y(self, value):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.y = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def on_z(self, value):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.z = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def setEnabled(self, flag):
        """Execute the set enabled operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: UNKNOWN
        """
        self.x.Enable(flag)
        self.y.Enable(flag)
        self.z.Enable(flag)

    def setToolTip(self, tip):
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param tip: Value for ``tip``.
        :type tip: UNKNOWN
        """
        self.x.SetToolTip(tip)
        self.y.SetToolTip(tip)
        self.z.SetToolTip(tip)
