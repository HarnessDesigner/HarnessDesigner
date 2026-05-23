
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ...widgets import float_ctrl as _float_ctrl

from .... import color as _color
from ....geometry import angle as _angle
from ....geometry import point as _point


class TripleFloatCtrl(QWidget):

    def __init__(self, parent, position_or_angle: _point.Point | _angle.Angle,
                 color: _color.Color | None = None, register_events: bool = True):

        super().__init__(parent)

        if isinstance(position_or_angle, _point.Point):
            min_val = -250
            max_val = 250
        else:
            min_val = -180
            max_val = 180

        self.setMaximumHeight(250)

        sizer = QVBoxLayout(self)

        if color is None:
            sizer.addSpacing(5)
        else:
            color_ctrl = QWidget(self)
            color_ctrl.setFixedHeight(5)
            color_ctrl.setStyleSheet(
                f"background-color: {color.to_qcolor().name()};")

            sizer.addWidget(color_ctrl)

        self.x = _float_ctrl.FloatCtrl(
            self, 'X:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        self.y = _float_ctrl.FloatCtrl(
            self, 'Y:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        self.z = _float_ctrl.FloatCtrl(
            self, 'Z:', min_val=min_val,
            max_val=max_val, inc=0.01, slider=True)

        sizer.addSpacing(2)
        sizer.addWidget(self.x)
        sizer.addSpacing(2)
        sizer.addWidget(self.y)
        sizer.addSpacing(2)
        sizer.addWidget(self.z)
        sizer.addSpacing(2)

        self.position_or_angle = position_or_angle
        position_or_angle.bind(self.on_position_or_angle)

        self.x.SetValue(position_or_angle.x)
        self.y.SetValue(position_or_angle.y)
        self.z.SetValue(position_or_angle.z)

        if register_events:
            self.x.value_changed.connect(self.on_x)
            self.y.value_changed.connect(self.on_y)
            self.z.value_changed.connect(self.on_z)

    def on_position_or_angle(self, p):
        self.x.SetValue(p.x)
        self.y.SetValue(p.y)
        self.z.SetValue(p.z)

        self.x.update()
        self.y.update()
        self.z.update()

    def on_x(self, value):
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.x = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def on_y(self, value):
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.y = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def on_z(self, value):
        self.position_or_angle.unbind(self.on_position_or_angle)
        self.position_or_angle.z = value
        self.position_or_angle.bind(self.on_position_or_angle)

    def setEnabled(self, flag):
        self.x.Enable(flag)
        self.y.Enable(flag)
        self.z.Enable(flag)

    def setToolTip(self, tip):
        self.x.SetToolTip(tip)
        self.y.SetToolTip(tip)
        self.z.SetToolTip(tip)
