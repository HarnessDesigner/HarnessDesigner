# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ... import utils as _utils
from ...geometry.decimal import Decimal as _d
from . import events as _events


class FloatProperty(QtWidgets.QWidget):
    """Represent a float property in :mod:`harness_designer.ui.prop_ctrls.float_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label: str, min_value: float, max_value: float,
                 increment: float, units: str | None = None):
        """Initialise the :class:`FloatProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: `str`
        :param min_value: Value for ``min_value``.
        :type min_value: `float`
        :param max_value: Value for ``max_value``.
        :type max_value: `float`
        :param increment: Value for ``increment``.
        :type increment: `float`
        :param units: Value for ``units``.
        :type units: `str | None`
        """
        super().__init__(parent)

        self._min_val = min_value
        self._max_val = max_value
        self._value = min_value
        self._inc = increment
        self._label = label

        precision = 0
        inc = _d(increment)
        while inc < 1:
            precision += 1
            inc *= _d(10.0)
        self._precision = precision

        s_inc = _d(10) * _d(precision)
        slider_max = _d(100) * s_inc
        self._s_max = max(1, int(slider_max))

        self._st = QtWidgets.QLabel(label + ':', self)
        self._ctrl = QtWidgets.QDoubleSpinBox(self)
        self._ctrl.setRange(min_value, max_value)
        self._ctrl.setSingleStep(increment)
        self._ctrl.setDecimals(precision)
        self._ctrl.setValue(min_value)

        self._units_st = None
        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        slider_value = _utils.remap(
            min_value, min_value, max_value, 0, self._s_max)

        self._slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._slider.setRange(0, self._s_max)
        self._slider.setValue(int(slider_value))

        # layout
        left_col = QtWidgets.QVBoxLayout()
        left_col.setContentsMargins(0, 5, 0, 0)
        left_col.addWidget(self._st)

        spin_row = QtWidgets.QHBoxLayout()
        spin_row.addWidget(self._ctrl, stretch=1)

        if self._units_st:
            spin_row.addWidget(self._units_st)

        right_col = QtWidgets.QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.addLayout(spin_row)
        right_col.addWidget(self._slider)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addLayout(left_col)
        sizer.addLayout(right_col, stretch=1)
        self.setLayout(sizer)

        self._slider.valueChanged.connect(self._on_slider_scroll)
        self._ctrl.valueChanged.connect(self._on_spin_changed)

    def SetValue(self, value: float) -> None:
        """
        Execute the set value operation.

        :param value: Value to store or process.
        :type value: `float`
        """

        value = round(value, self._precision)
        value = _d(value)
        inc = _d(self._inc)

        remaining = value % inc
        if remaining:
            value += inc - remaining
        if value > self._max_val:
            value = self._max_val
        if value < self._min_val:
            value = self._min_val

        self._value = float(value)

        self._ctrl.blockSignals(True)
        self._slider.blockSignals(True)

        self._ctrl.setValue(self._value)

        sv = _utils.remap(
            value, self._min_val, self._max_val, 0, self._s_max)

        self._slider.setValue(int(sv))

        self._ctrl.blockSignals(False)
        self._slider.blockSignals(False)

    def GetValue(self) -> float:
        """
        Execute the get value operation.

        :returns: Return value. UNKNOWN details.
        :rtype: `float`
        """

        return self._value

    def _on_slider_scroll(self, _) -> None:
        """
        Handle the slider scroll event.
        """
        sv = self._slider.value()

        spin_value = _utils.remap(
            sv, 0, self._s_max, self._min_val, self._max_val)

        inc = _d(self._inc)

        remaining = spin_value % inc
        if remaining:
            spin_value += inc - remaining

        self._value = float(spin_value)

        self._ctrl.blockSignals(True)
        self._ctrl.setValue(self._value)
        self._ctrl.blockSignals(False)

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(float)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def _on_spin_changed(self, spin_value: float) -> None:
        """
        Handle the spin changed event.

        :param spin_value: Value for ``spin_value``.
        :type spin_value: `float`
        """

        sv = _utils.remap(
            spin_value, self._min_val, self._max_val, 0, self._s_max)

        self._value = spin_value

        self._slider.blockSignals(True)
        self._slider.setValue(int(sv))
        self._slider.blockSignals(False)

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(float)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetLabel(self, value: str):
        self._label = value
        self._st.setText(value)

    def GetLabel(self) -> str:
        return self._label
